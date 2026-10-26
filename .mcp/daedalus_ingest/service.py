"""Transport-independent ingestion API. One source and one reviewed plan per operation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from daedalus_search.documents import Resolver, parse_document, scan_paths
from daedalus_paths import POLICY_PATH
from .apply import apply_operation
from .sources import (archive_path, memory_filename, path_for, read_bytes, resolve_source,
                      source_info, source_paths)
from .storage import (IngestError, durable_write, load_operation, save_operation,
                      sha, state_dir, vault_lock, write_json)
from .validation import check_credentials, materialize, require

class IngestService:
    def __init__(self, root, *, owner="local", engine=None):
        self.root = Path(root).resolve()
        self.owner = owner
        self.engine = engine

    def sources(self, cursor=0, limit=20):
        require(type(cursor) is int and cursor >= 0 and type(limit) is int and 1 <= limit <= 100,
                "Invalid pagination")
        paths = source_paths(self.root)
        page = paths[cursor:cursor + limit]
        return {"schema_version": 1, "sources": [source_info(self.root, p) for p in page],
                "next_cursor": cursor + limit if cursor + limit < len(paths) else None}

    def prepare(self, source_path, request_id, *, target_paths=None, start_offset=0, max_chars=16000):
        require(isinstance(request_id, str) and 0 < len(request_id) <= 200, "A stable request_id is required")
        require(type(start_offset) is int and start_offset >= 0 and type(max_chars) is int
                and 1 <= max_chars <= 24000, "Invalid source page")
        targets = target_paths or []
        require(isinstance(targets, list) and len(targets) <= 20, "At most 20 targets can be prepared")
        with vault_lock(self.root):
            source = resolve_source(self.root, source_path)
            info = source_info(self.root, source)
            key = sha(self.owner + "\0" + request_id)
            request_file = state_dir(self.root) / "requests" / (key + ".json")
            if request_file.exists():
                directory, op = load_operation(self.root, json.loads(request_file.read_text())["operation_id"])
                require(op["source"] == info, "Request id belongs to another source version; use a new request_id")
                require(op["state"] in {"prepared", "validated"}, "Operation already applied or interrupted")
            else:
                operation_id = uuid.uuid4().hex
                directory = state_dir(self.root) / "operations" / operation_id
                op = {"schema_version": 1, "operation_id": operation_id, "request_id": request_id,
                      "vault": str(self.root), "owner": self.owner, "state": "prepared", "source": info,
                      "base_documents": {}, "created_at": datetime.now(timezone.utc).isoformat()}
                durable_write(directory / "source.md", read_bytes(self.root, source))
                save_operation(directory, op)
                write_json(request_file, {"operation_id": operation_id})
            base = directory / "base"
            for path in targets:
                path_for(self.root, path, area="wiki")
                data = read_bytes(self.root, path)
                expected = op["base_documents"].get(path)
                require(expected is None or expected == sha(data), "Prepared target changed", path=path)
                if expected is None:
                    durable_write(base / sha(path), data)
                    op["base_documents"][path] = sha(data)
                    op["state"] = "prepared"
                    op.pop("proposal_digest", None)
            save_operation(directory, op)
            text = (directory / "source.md").read_bytes().decode()
            require(start_offset <= len(text), "Source page starts after the end")
            page = text[start_offset:start_offset + max_chars]
            policy = POLICY_PATH.read_text(encoding="utf-8")
            return {"schema_version": 1, "operation_id": op["operation_id"], "state": op["state"],
                    "source": info, "text": page, "start_offset": start_offset,
                    "offset_unit": "Unicode code points (source paging); UTF-8 bytes (insertions)",
                    "next_offset": start_offset + len(page) if start_offset + len(page) < len(text) else None,
                    "base_documents": op["base_documents"],
                    "target_bytes": {p: (base / sha(p)).stat().st_size for p in targets},
                    "targets": {p: (base / sha(p)).read_bytes().decode() for p in targets},
                    "policy_version": sha(policy), "policy": policy}

    def preview(self, operation_id, proposal):
        with vault_lock(self.root):
            directory, op = load_operation(self.root, operation_id)
            self._owner(op)
            require(op.get("kind") != "raw_note", "Raw creation is independent of ingestion; use ingest_prepare")
            require(op["state"] in {"prepared", "validated"}, "Cannot replace an applied/interrupted proposal")
            # Every preview invalidates the previous review, even when validation fails.
            op["state"] = "prepared"
            op.pop("proposal_digest", None)
            save_operation(directory, op)
            before, after, descriptions, archive, diff = materialize(self.root, op, proposal, directory / "base")
            dependencies = dict(op["base_documents"])
            for unit in proposal["coverage"]:
                for path in unit.get("targets", []):
                    if path not in after:
                        dependencies.setdefault(path, sha(read_bytes(self.root, path)))
            for path, checksum in dependencies.items():
                require(sha(read_bytes(self.root, path)) == checksum, "A reviewed dependency changed", path=path)
            dependencies = {p: checksum for p, checksum in dependencies.items() if p not in after}
            for path in ("wiki/index.md", "wiki/log.md", "wiki/Ingestion_Tracker.md"):
                require(path_for(self.root, path).is_file(), "Required administrative file is missing", path=path)
                before[path] = read_bytes(self.root, path)
            after["wiki/index.md"] = self._index(before["wiki/index.md"], descriptions)
            stamp = op["created_at"][:10]
            marker = f"<!-- ingest:{operation_id} -->"
            source = op["source"]["path"]
            state = "processed" if archive else "reviewed; source retained"
            tracker = f"- [{'x' if archive else ' '}] {source} ({state} {stamp}) {marker}"
            log = f"## [{stamp}] ingest | {proposal['summary']} | source: {source} | {state} {marker}"
            for path, line in (("wiki/Ingestion_Tracker.md", tracker), ("wiki/log.md", log)):
                require("\n" not in proposal["summary"] and "\r" not in proposal["summary"], "Summary must be one line")
                eol = b"\r\n" if b"\r\n" in before[path] else b"\n"
                after[path] = before[path] + (b"" if not before[path] or before[path].endswith(b"\n") else eol) + line.encode() + eol
            import difflib
            for path in sorted(before.keys() & {"wiki/index.md", "wiki/log.md", "wiki/Ingestion_Tracker.md"}):
                check_credentials(before[path], after[path], path)
                diff += "".join(difflib.unified_diff(before[path].decode().splitlines(keepends=True),
                    after[path].decode().splitlines(keepends=True), fromfile=path, tofile=path))
            steps = []
            for path, data in after.items():
                if before[path] == data:
                    continue
                blob = sha(path)
                durable_write(directory / "blobs" / blob, data)
                steps.append({"path": path, "before": sha(before[path]) if before[path] is not None else None,
                              "after": sha(data), "blob": blob, "done": False})
            op.update({"state": "validated", "proposal": proposal, "steps": steps, "archive": archive,
                       "policy_version": sha(POLICY_PATH.read_bytes()), "diff": diff, "dependencies": dependencies})
            op["proposal_digest"] = sha(json.dumps({"proposal": proposal, "steps": steps,
                "source": op["source"], "dependencies": dependencies, "policy": op["policy_version"]}, sort_keys=True, ensure_ascii=False))
            save_operation(directory, op)
            return {"schema_version": 1, "operation_id": operation_id, "state": "validated",
                    "proposal_digest": op["proposal_digest"], "summary": proposal["summary"], "diff": diff,
                    "archive": archive, "warnings": ["Evidence existence is verified; semantic sufficiency requires review.",
                    "The digest identifies this proposal; approval must come from the user through the client."]}

    def apply(self, operation_id, proposal_digest):
        directory, op = load_operation(self.root, operation_id)
        self._owner(op)
        require(op.get("kind") != "raw_note", "Resume raw creation with create_raw_note")
        require(op["state"] == "committed" or op.get("policy_version") == sha(POLICY_PATH.read_bytes()),
                "Ingestion policy changed; prepare a new proposal")
        op = apply_operation(self.root, operation_id, proposal_digest, self.owner)
        if self.engine:
            self.engine.request_update()
        return self.status(operation_id)

    def status(self, operation_id):
        from .publication import publication_status
        _, op = load_operation(self.root, operation_id)
        self._owner(op)
        if op.get("kind") == "raw_note":
            from .capture import result
            return result(self.root, op)
        search_state = op.get("search_state", "not_requested")
        if op["state"] == "committed" and self.engine:
            try:
                docs = self.engine.catalog()
                expected = {s["path"]: s["after"] for s in op["steps"] if s["path"] not in
                            {"wiki/index.md", "wiki/log.md", "wiki/Ingestion_Tracker.md"}}
                expected[op["archive"] or op["source"]["path"]] = op["source"]["sha256"]
                if all(p in docs and docs[p].hash == checksum for p, checksum in expected.items()) and (
                        not op["archive"] or op["source"]["path"] not in docs):
                    search_state = "search_ready"
            except Exception:
                search_state = "search_pending"
        return {"schema_version": 1, "operation_id": operation_id, "state": op["state"],
                "source": op["source"], "archive": op.get("archive"), "search_state": search_state,
                "steps": [{"path": s["path"], "done": s["done"]} for s in op.get("steps", [])],
                "publication": publication_status(self.root, operation_id),
                "last_error": op.get("last_error")}

    def capture(self, title, content):
        return self.create_raw_note("ai", memory_filename(title), content)

    def create_raw_note(self, category, filename, content):
        from .capture import create
        reply = create(self.root, self.owner, category, filename, content)
        if self.engine:
            try:
                self.engine.request_update()
            except Exception:
                pass  # A rebuildable index must not turn a saved note into a failed upload.
        return reply

    def register_node(self, path, description):
        with vault_lock(self.root):
            path_for(self.root, path, area="wiki")
            require(path not in {"wiki/index.md", "wiki/log.md", "wiki/Ingestion_Tracker.md"}, "Expected a thematic node")
            require(path_for(self.root, path).is_file(), "Node does not exist", path=path)
            require(isinstance(description, str) and bool(description.strip()) and not any(c in description for c in "\r\n"),
                    "Description must be a nonempty single line")
            target = "wiki/index.md"
            old = read_bytes(self.root, target)
            docs = {p: parse_document(self.root, p) for p in scan_paths(self.root)}
            from daedalus_search.documents import WIKILINK
            resolver = Resolver(self.root, docs)
            if any(resolver.candidates(m[1]) == [path] for m in WIKILINK.finditer(old.decode())):
                return "Node is already registered in wiki/index.md"
            new = self._index(old, {path: description})
            check_credentials(old, new, target)
            from .apply import publish
            publish(self.root, target, new, sha(old))
            return f"Successfully added node to wiki/index.md: {path}"

    def finalize_legacy(self, reference, nodes_created, nodes_expanded):
        """Archive only after verifying the nodes and actual source references.

        Legacy callers already edited the files themselves. They cannot use this
        compatibility path to submit arbitrary content changes to the server.
        """
        require(isinstance(nodes_created, list) and isinstance(nodes_expanded, list)
                and 0 < len(nodes_created) + len(nodes_expanded) <= 20, "Verified target nodes are required")
        try:
            source = resolve_source(self.root, reference)
        except IngestError as exc:
            if exc.code != "not_found":
                raise
            # Retry only when the requested source is no longer pending. Other
            # unrelated pending files must not prevent idempotent finalization.
            for file in sorted((state_dir(self.root) / "operations").glob("*/operation.json")):
                op = json.loads(file.read_text())
                if (op.get("legacy_reference") == reference and op["owner"] == self.owner
                        and op["state"] == "committed"):
                    return self.status(op["operation_id"])
            raise
        info = source_info(self.root, source)
        docs = {p: parse_document(self.root, p) for p in scan_paths(self.root)}
        resolver = Resolver(self.root, docs)
        resolver.resolve_relations()
        targets = []
        for name in nodes_created + nodes_expanded:
            target = resolver.resolve(name)
            require(target.startswith("wiki/") and target not in {"wiki/index.md", "wiki/log.md", "wiki/Ingestion_Tracker.md"},
                    "Expected thematic wiki nodes")
            require(any(r.kind == "source" and r.target == source for r in docs[target].relations),
                    "Declared node does not actually cite this source", path=target)
            targets.append(target)
        request_id = "legacy-" + sha(json.dumps([info, sorted(targets)]))
        prepared = self.prepare(source, request_id)
        proposal = {"summary": "Finalize verified legacy ingestion", "archive": True,
                    "changes": [], "coverage": [{"start_line": 1, "end_line": info["lines"],
                    "decision": "covered", "targets": targets, "reason": "Existing nodes reference this source; synthesis was performed by the authorized client"}]}
        preview = self.preview(prepared["operation_id"], proposal)
        with vault_lock(self.root):
            directory, op = load_operation(self.root, prepared["operation_id"])
            op["legacy_reference"] = reference
            save_operation(directory, op)
        return self.apply(prepared["operation_id"], preview["proposal_digest"])

    def _owner(self, op):
        if op["owner"] != self.owner:
            raise IngestError("forbidden", "Operation belongs to another client")

    @staticmethod
    def _index(data, descriptions):
        if not descriptions:
            return data
        lines = data.splitlines(keepends=True)
        start = next((n for n, line in enumerate(lines) if line.strip() == b"## Pages"), None)
        require(start is not None, "wiki/index.md requires a ## Pages section")
        end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith(b"## ")), len(lines))
        eol = b"\r\n" if b"\r\n" in data else b"\n"
        insert = b"".join((f"- [[{p.removeprefix('wiki/').removesuffix('.md')}|{Path(p).stem.replace('_', ' ')}]]: {d}.".encode() + eol)
                          for p, d in sorted(descriptions.items()))
        prefix, suffix = b"".join(lines[:end]), b"".join(lines[end:])
        return prefix + (b"" if prefix.endswith(b"\n") else eol) + insert + suffix
