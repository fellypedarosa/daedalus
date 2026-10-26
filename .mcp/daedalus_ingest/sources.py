"""Canonical source identities and exclusive creation; raw originals stay intact."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .storage import IngestError, sha

CATEGORIES = {"ai", "local", "clipper", "youtube"}
MAX_SOURCE_BYTES = 2_000_000


def path_for(root, relative, *, area=None):
    """Writing is stricter than reading: no symlink components are accepted."""
    root = Path(root).resolve()
    if (not isinstance(relative, str) or "\\" in relative
            or any(ord(c) < 32 or c in "[]|#" for c in relative)):
        raise IngestError("invalid", "Expected a canonical Markdown path")
    parts = relative.split("/")
    if (len(parts) < 2 or any(p in {"", ".", ".."} for p in parts)
            or parts[0] not in {"wiki", "raw"} or (area and parts[0] != area)
            or Path(relative).suffix != ".md"):
        raise IngestError("invalid", "Expected a vault-relative wiki/raw Markdown path", path=relative)
    path = root
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink():
            raise IngestError("invalid", "Symlinks are not permitted for ingestion", path=relative)
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            raise IngestError("invalid", "Parent is not a directory", path=relative)
    if path.exists() and not path.is_file():
        raise IngestError("invalid", "Knowledge target is not a file", path=relative)
    return path


def read_bytes(root, relative):
    path = path_for(root, relative)
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise IngestError("conflict", "File changed during read", path=relative)
    try:
        data.decode("utf-8")
    except UnicodeError:
        raise IngestError("invalid", "Only valid UTF-8 Markdown is accepted", path=relative) from None
    return data


def source_paths(root, *, cataloged=False):
    paths = []
    for category in sorted(CATEGORIES):
        folder = Path(root) / "raw" / category
        if not folder.is_dir() or folder.is_symlink():
            continue
        for path in sorted(folder.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            if ("cataloged" in path.relative_to(folder).parts) != cataloged:
                continue
            try:
                path_for(root, relative, area="raw")
                if path.is_file():
                    paths.append(relative)
            except IngestError:
                continue
    return sorted(paths)


def resolve_source(root, reference, *, cataloged=False):
    candidates = source_paths(root, cataloged=cataloged)
    if reference in candidates:
        return reference
    if not isinstance(reference, str) or "/" in reference or "\\" in reference or reference in {"", ".", ".."}:
        raise IngestError("not_found", "Pending source not found", path=reference)
    matches = [p for p in candidates if reference in {Path(p).name, Path(p).stem}]
    if len(matches) != 1:
        raise IngestError("ambiguous" if matches else "not_found", "Use the canonical source path",
                          candidates=matches)
    return matches[0]


def archive_path(source):
    parts = source.split("/")
    return "/".join(parts[:2] + ["cataloged"] + parts[2:])


def source_info(root, source):
    data = read_bytes(root, source)
    if not data.decode().strip():
        raise IngestError("invalid", "Source is empty", path=source)
    if len(data) > MAX_SOURCE_BYTES:
        raise IngestError("invalid", "Source exceeds 2 MB; split it explicitly before ingestion", path=source)
    return {"id": sha(source), "path": source, "sha256": sha(data), "bytes": len(data),
            "lines": len(data.decode().splitlines()), "kind": source.split("/")[1]}


def memory_filename(title):
    """Keep the legacy title-to-filename convention for existing clients."""
    if not isinstance(title, str):
        raise IngestError("invalid", "A title is required")
    slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^\w\s-]", "", slug.lower())
    slug = re.sub(r"[-\s]+", "_", slug).strip("_")
    if not slug or len(slug) > 150:
        raise IngestError("invalid", "Title must produce a nonempty filename of at most 150 characters")
    return f"{slug}.md"
