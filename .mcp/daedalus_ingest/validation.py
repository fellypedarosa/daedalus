"""Validate a bounded additive proposal; semantic sufficiency remains a review."""
from __future__ import annotations

import difflib
import json
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

from daedalus_search.documents import Resolver, parse_document, scan_paths
from daedalus_validation.credentials import MARKER_START, _scan_text
from .sources import MAX_SOURCE_BYTES, archive_path, path_for, read_bytes
from .storage import IngestError, sha

ADMIN = {"wiki/index.md", "wiki/log.md", "wiki/Ingestion_Tracker.md"}
MAX_FILES = 20
MAX_PROPOSAL_BYTES = 500_000


def require(condition, message, **details):
    if not condition:
        raise IngestError("needs_review", message, **details)


def check_credentials(before, after, path):
    old, new = before.decode(), after.decode()
    old_markers = Counter(line for line in old.splitlines() if MARKER_START.match(line))
    new_markers = Counter(line for line in new.splitlines() if MARKER_START.match(line))
    require(not (new_markers - old_markers), "New scanner exceptions require separate human triage", path=path)
    def findings(text):
        lines = text.splitlines()
        return Counter((rule, lines[line - 1]) for line, rule in _scan_text(text))
    added = findings(new) - findings(old)
    require(not added, "Possible credentials require user review", path=path,
            findings=[{"rule": rule, "line_content": line} for rule, line in added])


def check_source(data, path):
    findings = _scan_text(data.decode())
    lines = data.decode().splitlines()
    require(not findings, "Source contains possible credentials; ask the user before proceeding", path=path,
            findings=[{"line": n, "rule": rule, "line_content": lines[n - 1]} for n, rule in findings])


def check_evidence(items, source):
    require(isinstance(items, list) and 0 < len(items) <= 100, "Changes require literal source evidence")
    lines = source.decode().splitlines(keepends=True)
    for item in items:
        require(isinstance(item, dict), "Invalid evidence")
        start, end, quote = item.get("start_line"), item.get("end_line"), item.get("quote")
        require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines),
                "Evidence line range is invalid")
        require(isinstance(quote, str) and bool(quote.strip()) and quote in "".join(lines[start - 1:end]),
                "Evidence quote does not match the source", start_line=start, end_line=end)


def check_metadata(data, path, *, new=False):
    text = data.decode()
    lines = text.splitlines()
    require(bool(lines) and lines[0] == "---", "Wiki node requires YAML frontmatter", path=path)
    end = next((n for n in range(1, len(lines)) if lines[n] == "---"), None)
    require(end is not None, "Unclosed frontmatter", path=path)
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
        require(isinstance(meta, dict), "Frontmatter must be a mapping", path=path)
        require(isinstance(meta.get("tags"), list) and bool(meta["tags"])
                and all(isinstance(v, str) and v.strip() for v in meta["tags"]), "Tags must be a nonempty list", path=path)
        date.fromisoformat(str(meta["date_created"]))
        require(isinstance(meta.get("sources"), list) and bool(meta["sources"])
                and all(isinstance(v, str) and v.strip() for v in meta["sources"]), "Sources must be a nonempty list", path=path)
    except (yaml.YAMLError, ValueError, KeyError, TypeError):
        raise IngestError("needs_review", "Frontmatter needs human review; it will not be rewritten", path=path) from None
    if new:
        require("Autor: [[LLM]]" in lines[end + 1:], "New nodes require Autor: [[LLM]] in their body", path=path)
        require(any(line.startswith("# ") for line in lines[end + 1:]), "New nodes require a title", path=path)


def materialize(root, operation, proposal, base_directory):
    require(isinstance(proposal, dict), "Proposal must be an object")
    require(len(json.dumps(proposal, ensure_ascii=False).encode()) <= MAX_PROPOSAL_BYTES,
            "Proposal exceeds 500 KB")
    require(isinstance(proposal.get("summary"), str) and proposal["summary"].strip(), "A review summary is required")
    require(type(proposal.get("archive")) is bool, "Choose archive=true or false explicitly")
    source_path = operation["source"]["path"]
    source = read_bytes(root, source_path)
    require(sha(source) == operation["source"]["sha256"], "Source changed after preparation")
    check_source(source, source_path)
    coverage = proposal.get("coverage")
    require(isinstance(coverage, list) and bool(coverage), "A complete source coverage assessment is required")
    count = len(source.decode().splitlines())
    next_line = 1
    deferred = False
    for unit in coverage:
        require(isinstance(unit, dict), "Invalid coverage unit")
        start, end = unit.get("start_line"), unit.get("end_line")
        require(type(start) is int and type(end) is int and start == next_line and start <= end <= count,
                "Coverage must cover every source line once, in order")
        require(unit.get("decision") in {"create", "expand", "covered", "defer", "omit"}
                and isinstance(unit.get("reason"), str) and bool(unit["reason"].strip()),
                "Each coverage decision requires a reason")
        deferred |= unit["decision"] == "defer"
        next_line = end + 1
    require(next_line == count + 1, "Source coverage is incomplete")
    require(not (deferred and proposal["archive"]), "Sources with deferred content cannot be archived")
    changes = proposal.get("changes", [])
    require(isinstance(changes, list) and len(changes) <= MAX_FILES, "At most 20 change entries per source")
    before, after, descriptions = {}, {}, {}
    for change in changes:
        require(isinstance(change, dict), "Invalid change entry")
        path = change.get("path")
        target = path_for(root, path, area="wiki")
        require(path not in ADMIN and path.count("/") >= 2, "Administrative files are managed by finalization", path=path)
        require(path not in after, "Combine insertions for a node into one change", path=path)
        action = change.get("action")
        if action == "create":
            require(not target.exists(), "New node already exists", path=path)
            require(isinstance(change.get("content"), str) and bool(change["content"].strip()), "New content is required")
            old, new = b"", change["content"].encode()
            require(isinstance(change.get("description"), str) and bool(change["description"].strip())
                    and "\n" not in change["description"] and "\r" not in change["description"],
                    "New nodes require a single-line index description")
            descriptions[path] = change["description"]
        elif action == "insert":
            expected = operation["base_documents"].get(path)
            require(expected is not None, "Prepare this target before proposing an expansion", path=path)
            old = read_bytes(root, path)
            require(sha(old) == expected, "Target changed after preparation", path=path)
            require((base_directory / sha(path)).read_bytes() == old, "Base snapshot mismatch", path=path)
            edits = change.get("insertions")
            require(isinstance(edits, list) and bool(edits), "An expansion requires insertions")
            require(all(isinstance(e, dict) and type(e.get("offset_utf8")) is int for e in edits),
                    "Insertions require integer UTF-8 byte offsets")
            new = old
            previous = len(old) + 1
            for edit in sorted(edits, key=lambda e: e.get("offset_utf8", -1), reverse=True):
                offset, content = edit.get("offset_utf8"), edit.get("text")
                require(type(offset) is int and 0 <= offset <= len(old) and offset < previous,
                        "Invalid or repeated UTF-8 byte insertion offset", path=path)
                require(isinstance(content, str) and bool(content), "Insertion text is required")
                try:
                    old[:offset].decode("utf-8")
                except UnicodeError:
                    raise IngestError("needs_review", "Insertion splits a UTF-8 character", path=path) from None
                new = new[:offset] + content.encode() + new[offset:]
                previous = offset
        else:
            raise IngestError("needs_review", "Only create and insert actions are permitted")
        require(len(new) <= MAX_SOURCE_BYTES, "Node exceeds 2 MB", path=path)
        check_metadata(new, path, new=action == "create")
        check_credentials(old, new, path)
        check_evidence(change.get("evidence"), source)
        before[path] = old if action == "insert" else None
        after[path] = new
    require(sum(len(v) for v in after.values()) <= 4_000_000, "Materialized proposal exceeds 4 MB")
    # Validate relations on the proposed tree, using the existing parser/resolver.
    # Existing unrelated defects remain outside the delta.
    documents = {p: parse_document(root, p) for p in scan_paths(root)}
    original = dict(documents)
    with tempfile.TemporaryDirectory(prefix="preview-") as temporary:
        staging = Path(temporary)
        for path, data in after.items():
            file = staging / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            documents[path] = parse_document(staging, path)
    resolver = Resolver(root, documents)
    resolver.resolve_relations()
    for path in after:
        old_relations = Counter((r.reference, r.kind) for r in original[path].relations) if path in original else Counter()
        additions = Counter((r.reference, r.kind) for r in documents[path].relations) - old_relations
        for relation in documents[path].relations:
            if additions[(relation.reference, relation.kind)] and relation.kind != "authorship":
                require(relation.status not in {"unresolved", "ambiguous"},
                        "New reference must resolve unambiguously", path=path, reference=relation.reference)
        require(any(r.kind == "source" and r.target == source_path for r in documents[path].relations),
                "Changed nodes must reference the ingested source", path=path)
    for unit in coverage:
        targets = unit.get("targets", [])
        require(isinstance(targets, list), "Coverage targets must be a list")
        if unit["decision"] in {"create", "expand", "covered"}:
            require(bool(targets), "Coverage decisions require target nodes")
        for target in targets:
            require(isinstance(target, str), "Coverage targets must be canonical path strings")
            require(target in documents and target.startswith("wiki/"), "Unknown coverage target", path=target)
            if unit["decision"] in {"create", "expand"}:
                require(target in after, "Coverage claims a change missing from the proposal", path=target)
    archive = archive_path(source_path) if proposal["archive"] else None
    if archive:
        require(not path_for(root, archive).exists(), "Archive destination already exists", path=archive)
    diff = "".join("".join(difflib.unified_diff(
        (before[path] or b"").decode().splitlines(keepends=True), data.decode().splitlines(keepends=True),
        fromfile=path if before[path] is not None else "/dev/null", tofile=path)) for path, data in after.items())
    if archive:
        diff += f"\nArchive (unchanged sha256={sha(source)}): {source_path} -> {archive}\n"
    return before, after, descriptions, archive, diff
