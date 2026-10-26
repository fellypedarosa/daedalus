"""Markdown documents, literal line ranges and bounded local link resolution."""
from __future__ import annotations

import posixpath
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from .models import ADMIN_FILES, AmbiguousReference, Document, Passage, Relation, digest

WIKILINK = re.compile(r"\[\[([^\]\n]+)\]\]")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\((<[^>]+>|(?:[^()\n]|\([^()\n]*\))+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(c)).replace("_", " ").strip()


def text_tokens(text: str) -> int:
    """Conservative non-model fallback for lexical-only segmentation."""
    return max(1, (len(text.encode("utf-8")) + 2) // 3)


def safe_path(root: Path, relative: str) -> Path:
    """Both the named path and its symlink target must be knowledge files."""
    root = root.resolve()
    path = Path(relative)
    if path.is_absolute() or not path.parts or path.parts[0] not in {"wiki", "raw"}:
        raise ValueError("Only vault-relative wiki/ and raw/ paths are accepted")
    if ".." in path.parts or path.suffix.lower() != ".md":
        raise ValueError("Expected a Markdown knowledge path without traversal")
    resolved = (root / path).resolve()
    if not any(resolved.is_relative_to(root / area) for area in ("wiki", "raw")):
        raise ValueError("Knowledge path escapes wiki/raw")
    return resolved


def scan_paths(root: Path) -> list[str]:
    paths = []
    for area in ("wiki", "raw"):
        for path in sorted((root / area).rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            if area == "wiki" and relative in {f"wiki/{name}" for name in ADMIN_FILES}:
                continue
            try:
                safe_path(root, relative)
            except ValueError:
                continue
            if path.is_file():
                paths.append(relative)
    return paths


def stable_read(root: Path, relative: str) -> tuple[bytes, str]:
    path = safe_path(root, relative)
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_mtime_ns, before.st_size, before.st_ino) != (
            after.st_mtime_ns, after.st_size, after.st_ino):
        raise OSError(f"Document changed while reading: {relative}")
    return data, data.decode("utf-8", errors="replace")


def _list(value) -> list[str]:
    if value is None:
        return []
    return [str(v) for v in (value if isinstance(value, list) else [value])]


def parse_document(root: Path, relative: str, *, max_tokens: int = 256,
                   count_tokens=text_tokens, overlap_lines: int = 2) -> Document:
    if max_tokens < 16:
        raise ValueError("max_tokens must be at least 16")
    data, text = stable_read(root, relative)
    lines = text.splitlines(keepends=True)
    metadata, start = {}, 0
    has_frontmatter = bool(lines and lines[0].strip() == "---")
    if has_frontmatter:
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            try:
                value = yaml.safe_load("".join(lines[1:end]))
                metadata = value if isinstance(value, dict) else {}
            except yaml.YAMLError:
                metadata = {"parse_warning": "invalid_frontmatter"}
            start = end + 1
    title = Path(relative).stem.replace("_", " ")
    for line in lines[start:]:
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            title = match[1]
            break
    doc = Document(relative, relative.split("/")[0], title,
                   relative.split("/")[1] if len(relative.split("/")) > 2 else "_root",
                   digest(data), text, _list(metadata.get("aliases", metadata.get("alias"))),
                   _list(metadata.get("tags")), metadata, has_frontmatter)

    # Extract links outside fenced code and inline code. Source fields retain links.
    fence = None
    source_section = False
    for i, line in enumerate(lines):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if fence:
            continue
        heading = HEADING.match(line.rstrip("\r\n"))
        if heading:
            source_section = normalized(heading[2]) in {
                "sources", "source", "references", "referencias", "fontes", "metadata"}
        cleaned = re.sub(r"`[^`\n]*`", "", line)
        refs = [m[1].split("|", 1)[0].strip() for m in WIKILINK.finditer(cleaned)]
        refs += [m[1].strip("<>") for m in MARKDOWN_LINK.finditer(cleaned)]
        for reference in refs:
            kind = "authorship" if re.match(r"^\s*(?:autor|author):", line, re.I) else (
                "source" if i < start or source_section or "raw/" in reference else "topic")
            doc.relations.append(Relation(relative, reference, kind, i + 1))
    for key in ("source", "sources"):
        for source in _list(metadata.get(key)):
            if source.lower() in {"none", "null", ""} or "[[" in source or "](" in source:
                continue
            doc.relations.append(Relation(relative, source, "source", 1))

    # Headings establish context. Paragraphs, fences, lists and tables stay intact
    # when they fit. Oversized blocks split on literal lines, never by rewriting.
    sections = []
    stack: list[tuple[int, str]] = []
    section_start, fence = start, None
    for i in range(start, len(lines)):
        marker = re.match(r"^\s*(`{3,}|~{3,})", lines[i])
        if marker:
            fence = marker[1][0] if fence is None else (None if fence == marker[1][0] else fence)
        heading = None if fence else HEADING.match(lines[i].rstrip("\r\n"))
        if heading:
            if i > section_start:
                sections.append((section_start, i, " / ".join(v for _, v in stack)))
            level, value = len(heading[1]), heading[2]
            stack = [(n, v) for n, v in stack if n < level] + [(level, value)]
            section_start = i
    if section_start < len(lines):
        sections.append((section_start, len(lines), " / ".join(v for _, v in stack)))

    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    for first, last, section in sections:
        if normalized(section.rsplit(" / ", 1)[-1]) in {
                "sources", "source", "references", "referencias", "fontes", "metadata"}:
            continue
        blocks, block_start, fenced = [], first, False
        for i in range(first, last):
            if re.match(r"^\s*(`{3,}|~{3,})", lines[i]):
                fenced = not fenced
            if not lines[i].strip() and not fenced and i + 1 > block_start:
                blocks.append((block_start, i + 1))
                block_start = i + 1
        if block_start < last:
            blocks.append((block_start, last))
        ranges, a, b = [], None, None
        for block_a, block_b in blocks:
            if a is not None and count_tokens("".join(lines[a:block_b])) <= max_tokens:
                b = block_b
                continue
            if a is not None:
                ranges.append((a, b))
                a, b = None, None
            if count_tokens("".join(lines[block_a:block_b])) <= max_tokens:
                a, b = block_a, block_b
            else:
                x = block_a
                while x < block_b:
                    y = x + 1
                    while y < block_b and count_tokens("".join(lines[x:y + 1])) <= max_tokens:
                        y += 1
                    ranges.append((x, y))
                    x = max(x + 1, y - min(overlap_lines, y - x - 1)) if y < block_b else y
        if a is not None:
            ranges.append((a, b))
        for a, b in ranges:
            value = "".join(lines[a:b])
            if not value.strip() or re.fullmatch(r"\s*(?:Autor|Author):\s*\[\[.*?\]\]\s*", value, re.I):
                continue
            if not any(line.strip() and not HEADING.match(line) for line in value.splitlines()):
                # Titles/headings are retrieval context for real passages, not
                # standalone factual evidence.
                continue
            # A single long paragraph can occupy one original line. Retain
            # character offsets as well as line numbers when dividing it.
            x = 0
            while x < len(value):
                lo, hi = x + 1, len(value)
                while lo < hi:
                    middle = (lo + hi + 1) // 2
                    if count_tokens(value[x:middle]) <= max_tokens:
                        lo = middle
                    else:
                        hi = middle - 1
                y = lo
                if y < len(value):
                    space = value.rfind(" ", x + max(1, (y - x) // 2), y)
                    if space > x:
                        y = space + 1
                part = value[x:y]
                absolute_start, absolute_end = offsets[a] + x, offsets[a] + y
                line_start = text.count("\n", 0, absolute_start) + 1
                line_end = text.count("\n", 0, max(absolute_start, absolute_end - 1)) + 1
                pid = digest(f"{relative}\0{absolute_start}\0{absolute_end}\0{part}")
                doc.passages.append(Passage(pid, relative, section, line_start, line_end,
                                            part, digest(part), absolute_start, absolute_end))
                x = y
    return doc


class Resolver:
    def __init__(self, root: Path, documents: dict[str, Document]):
        self.root = root.resolve()
        self.documents = documents
        self.names: dict[str, set[str]] = {}
        for path, doc in documents.items():
            for name in [Path(path).stem, doc.title, *doc.aliases]:
                self.names.setdefault(normalized(name), set()).add(path)

    def candidates(self, reference: str, source: str | None = None) -> list[str]:
        ref = reference.strip().removeprefix("[[").removesuffix("]]").split("|", 1)[0]
        if ref.startswith("#"):
            return [source] if source in self.documents else []
        if ref.startswith("file:"):
            parsed = urlsplit(ref)
            if parsed.netloc not in {"", "localhost"}:
                return []
            ref = unquote(parsed.path)
        else:
            ref = unquote(ref.split("#", 1)[0])
        ref = ref.split("#", 1)[0].strip().replace("\\", "/")
        if not ref or (urlsplit(ref).scheme and not Path(ref).is_absolute()):
            return []
        if Path(ref).is_absolute():
            try:
                ref = Path(ref).resolve().relative_to(self.root).as_posix()
            except ValueError:
                # Old file:// paths can survive moves of the vault. Match only
                # a complete knowledge-layer suffix, with a unique existing path.
                matches = [path for path in self.documents if ref.endswith("/" + path)]
                if matches:
                    return sorted(matches)
                if "/raw/" in ref:
                    ref = "raw/" + ref.rsplit("/raw/", 1)[1]
                else:
                    return []
        options = [ref]
        if source and not ref.startswith(("wiki/", "raw/")):
            options.insert(0, posixpath.normpath(posixpath.join(posixpath.dirname(source), ref)))
        options += ["wiki/" + ref, "raw/" + ref]
        for option in options:
            for path in (option, option + ".md"):
                if path in self.documents:
                    return [path]
        relocated = set()
        for option in options:
            parts = Path(option).parts
            if len(parts) >= 3 and parts[0] == "raw" and ".." not in parts and "cataloged" not in parts:
                candidate = "/".join((parts[0], parts[1], "cataloged", *parts[2:]))
                for path in (candidate, candidate + ".md"):
                    if path in self.documents:
                        relocated.add(path)
        if relocated:
            return sorted(relocated)
        if "/" in ref or ".." in Path(ref).parts:
            return []
        return sorted(self.names.get(normalized(Path(ref).stem), set()))

    def resolve(self, reference: str, source: str | None = None) -> str:
        candidates = self.candidates(reference, source)
        if len(candidates) > 1:
            raise AmbiguousReference(reference, candidates)
        if not candidates:
            raise FileNotFoundError(f"Knowledge document not found: {reference}")
        return candidates[0]

    def resolve_relations(self) -> None:
        for doc in self.documents.values():
            for relation in doc.relations:
                parsed = urlsplit(relation.reference)
                if parsed.scheme in {"http", "https", "mailto"}:
                    relation.status, relation.target, relation.candidates = "external", None, []
                    continue
                if Path(parsed.path).suffix.casefold() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".webp"}:
                    relation.status, relation.target, relation.candidates = "attachment", None, []
                    continue
                relation.candidates = self.candidates(relation.reference, doc.path)
                relation.status = "resolved" if len(relation.candidates) == 1 else (
                    "ambiguous" if relation.candidates else "unresolved")
                relation.target = relation.candidates[0] if relation.status == "resolved" else None
                if relation.target and relation.target.startswith("raw/") and relation.kind != "authorship":
                    relation.kind = "source"


def add_catalog_aliases(root: Path, documents: dict[str, Document]) -> None:
    catalog = root / "wiki/index.md"
    if not catalog.exists():
        return
    try:
        _, text = stable_read(root, "wiki/index.md")
    except (OSError, ValueError):
        return
    resolver = Resolver(root, documents)
    for match in WIKILINK.finditer(text):
        target, separator, alias = match[1].partition("|")
        paths = resolver.candidates(target)
        if separator and len(paths) == 1 and alias not in documents[paths[0]].aliases:
            documents[paths[0]].aliases.append(alias)
