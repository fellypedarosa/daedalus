"""Durable, portable publication requests; no Git or credentials in the MCP."""
from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from .sources import path_for
from .storage import IngestError, durable_write, sha, sync_dir, write_json


def sync_root(root):
    root = Path(root).resolve()
    configured = os.environ.get("DAEDALUS_SYNC_DIR")
    legacy = root / ".daedalus-sync"
    if not configured and (legacy.exists() or legacy.is_symlink()):
        raise IngestError("migration_required", "Move the existing publication state to .mcp/.daedalus-sync before starting the publisher")
    directory = Path(configured or root / ".mcp/.daedalus-sync").resolve()
    if directory == root or any(directory.is_relative_to(root / p) for p in ("wiki", "raw")):
        raise IngestError("invalid", "Publication state must be outside knowledge directories")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Docker creates a new bind source as root. Let the owner of the mounted
    # wiki operate the host publisher without mounting Git/SSH in the MCP or
    # introducing host UID/GID environment variables. Existing non-root
    # ownership is respected; snapshots remain inside this private directory.
    wiki = root / "wiki"
    if os.geteuid() == 0 and wiki.is_dir():
        if directory.stat().st_uid == 0:
            owner = wiki.stat()
            os.chown(directory, owner.st_uid, owner.st_gid)
            directory.chmod(0o700)
        owner = directory.stat()
        for name in ("receipts", "operations"):
            child = directory / name
            if child.is_symlink():
                raise IngestError("invalid", "Publication directories cannot be symbolic links")
            child.mkdir(exist_ok=True, mode=0o700)
            if child.stat().st_uid == 0:
                os.chown(child, owner.st_uid, owner.st_gid)
    return directory


@contextmanager
def file_lock(path, *, exclusive=True, nonblocking=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # A read descriptor also supports flock on Linux and lets the host lock a
    # file created by the container without changing its owner or permissions.
    try:
        stream = path.open("rb")
    except FileNotFoundError:
        stream = path.open("ab+")
    with stream:
        try:
            fcntl.flock(stream, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                        | (fcntl.LOCK_NB if nonblocking else 0))
        except BlockingIOError:
            raise IngestError("busy", "Deployment/publication is using the knowledge files") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def coordination(root, *, nonblocking=False, indexing=False, maintenance=False):
    directory = sync_root(root)
    # Index startup is allowed during container recreation. Its short writer
    # lock still prevents it from scanning a checkout while Git changes files.
    if indexing or maintenance:
        with file_lock(directory / "writer.lock", nonblocking=nonblocking):
            yield
    else:
        with file_lock(directory / "deploy.lock", exclusive=False, nonblocking=True):
            with file_lock(directory / "writer.lock", nonblocking=nonblocking):
                yield


def ensure_request(root, directory, op):
    """Write intent and copies before the first note changes; safe on retries."""
    destination = sync_root(root) / "operations" / op["operation_id"]
    manifest = destination / "request.json"
    if manifest.exists():
        existing = json.loads(manifest.read_text())
        if existing["proposal_digest"] != op["proposal_digest"]:
            raise IngestError("conflict", "Publication request belongs to another proposal")
        return
    for folder in (destination, destination / "blobs"):
        if folder.is_symlink():
            raise IngestError("invalid", "Publication directories cannot be symbolic links")
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.geteuid() == 0:
            owner = sync_root(root).stat()
            os.chown(folder, owner.st_uid, owner.st_gid)
    changes = {}
    for step in op["steps"]:
        content = (directory / "blobs" / step["blob"]).read_bytes()
        if sha(content) != step["after"]:
            raise IngestError("conflict", "Publication snapshot checksum mismatch")
        durable_write(destination / "blobs" / step["after"], content)
        changes[step["path"]] = {"before": step["before"], "after": step["after"]}
    if op.get("kind") != "raw_note":
        source = op["source"]
        content = (directory / "source.md").read_bytes()
        if sha(content) != source["sha256"]:
            raise IngestError("conflict", "Publication source snapshot checksum mismatch")
        durable_write(destination / "blobs" / source["sha256"], content)
        changes[source["path"]] = {"before": source["sha256"],
                                   "after": None if op["archive"] else source["sha256"],
                                   "allow_untracked": True}
        if op["archive"]:
            changes[op["archive"]] = {"before": None, "after": source["sha256"]}
    for path in changes:
        path_for(root, path)
    write_json(manifest, {"schema_version": 1, "operation_id": op["operation_id"],
                         "proposal_digest": op["proposal_digest"], "sequence": time.time_ns(),
                         "state": "applying", "changes": changes,
                         "dependencies": op.get("dependencies", {})})
    sync_dir(destination.parent)
    sync_dir(destination.parent.parent)


def finish_request(root, op):
    path = sync_root(root) / "operations" / op["operation_id"] / "request.json"
    request = json.loads(path.read_text())
    if request["state"] != "pending":
        request["state"] = "pending"
        write_json(path, request)


def publication_status(root, operation_id):
    base = sync_root(root)
    request = base / "operations" / operation_id / "request.json"
    if not request.exists():
        return {"state": "not_requested"}
    receipt = base / "receipts" / (operation_id + ".json")
    if receipt.exists():
        return json.loads(receipt.read_text())
    return {"state": json.loads(request.read_text())["state"]}
