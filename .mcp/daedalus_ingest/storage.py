"""Durable operation records and a vault-wide writer/indexer lock."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path


class IngestError(ValueError):
    def __init__(self, code, message, **details):
        self.code, self.details = code, details
        super().__init__(message)

    def result(self):
        return {"schema_version": 1, "state": self.code, "error": str(self), **self.details}


def sha(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def state_dir(root):
    root = Path(root).resolve()
    base = Path(os.environ.get("DAEDALUS_INGEST_DIR") or
                Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "daedalus-ingest").resolve()
    if base == root or any(base.is_relative_to(root / area) for area in ("wiki", "raw")):
        raise IngestError("invalid", "Ingestion state must be outside knowledge directories")
    return base / sha(str(root))[:16]


def durable_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, data):
    durable_write(path, (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())


@contextmanager
def vault_lock(root, operation=None, *, nonblocking=False, indexing=False):
    from .publication import coordination
    directory = state_dir(root)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with coordination(root, nonblocking=nonblocking, indexing=indexing):
        marker = directory / "pending.json"
        if marker.exists():
            pending = json.loads(marker.read_text())
            if pending["operation_id"] != operation:
                raise IngestError("conflict", "An incomplete operation must be resumed first",
                                  operation_id=pending["operation_id"])
        yield directory


def load_operation(root, operation_id):
    if (not isinstance(operation_id, str) or len(operation_id) != 32
            or any(c not in "0123456789abcdef" for c in operation_id)):
        raise IngestError("invalid", "Invalid operation id")
    directory = state_dir(root) / "operations" / operation_id
    try:
        value = json.loads((directory / "operation.json").read_text())
    except FileNotFoundError:
        raise IngestError("not_found", "Operation not found") from None
    if value.get("vault") != str(Path(root).resolve()):
        raise IngestError("conflict", "Operation belongs to another vault")
    return directory, value


def save_operation(directory, value):
    write_json(directory / "operation.json", value)
