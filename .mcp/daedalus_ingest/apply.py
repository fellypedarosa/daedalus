"""Recoverable publication of reviewed bytes, without automatic note rollback."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from .sources import path_for, read_bytes
from .publication import ensure_request, finish_request, sync_root
from .storage import (IngestError, load_operation, save_operation, sha,
                      state_dir, sync_dir, vault_lock, write_json)


def publish(root, path, data, expected):
    target = path_for(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(".ingest-" + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck after staging. External editors do not honor our lock; users
        # must avoid concurrent edits during publication (documented limitation).
        current = sha(read_bytes(root, path)) if target.exists() else None
        if current != expected:
            raise IngestError("conflict", "Target changed during publication", path=path)
        if expected is None:
            os.link(temporary, target)  # Exclusive atomic creation, same filesystem.
        else:
            os.replace(temporary, target)
        sync_dir(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def apply_operation(root, operation_id, digest, owner):
    with vault_lock(root, operation_id):
        directory, op = load_operation(root, operation_id)
        if op["owner"] != owner:
            raise IngestError("forbidden", "Operation belongs to another client")
        if not digest or digest != op.get("proposal_digest"):
            raise IngestError("conflict", "Preview digest is missing or no longer current")
        if op["state"] == "committed":
            # Resume an existing intent, but never retroactively publish an
            # operation approved before automatic publication was introduced.
            if (sync_root(root) / "operations" / operation_id / "request.json").exists():
                finish_request(root, op)
            marker = state_dir(root) / "pending.json"
            if marker.exists():
                marker.unlink()
                sync_dir(marker.parent)
            return op
        if op["state"] not in {"validated", "applying", "failed_recoverable", "conflict"} or not op.get("steps"):
            raise IngestError("needs_review", "A validated preview is required")
        source, archive = op["source"]["path"], op["archive"]
        source_file = path_for(root, source)
        if source_file.exists():
            if sha(read_bytes(root, source)) != op["source"]["sha256"]:
                raise IngestError("conflict", "Source changed after preview", path=source)
        elif not (archive and op.get("archive_started") and path_for(root, archive).exists()
                  and sha(read_bytes(root, archive)) == op["source"]["sha256"]):
            raise IngestError("conflict", "Source disappeared after preview", path=source)
        for path, checksum in op.get("dependencies", {}).items():
            if not path_for(root, path).exists() or sha(read_bytes(root, path)) != checksum:
                raise IngestError("conflict", "A reviewed dependency changed", path=path)
        # Validate every target before starting/resuming any further publication.
        for step in op["steps"]:
            path = step["path"]
            target = path_for(root, path)
            current = sha(read_bytes(root, path)) if target.exists() else None
            allowed = {step["after"]} if step["done"] else {step["before"]}
            if step.get("started"):
                allowed.add(step["after"])
            if current not in allowed:
                raise IngestError("conflict", "Target changed since preview or interruption", path=path)
            if sha((directory / "blobs" / step["blob"]).read_bytes()) != step["after"]:
                raise IngestError("conflict", "Staged result checksum mismatch", path=path)
        if archive and path_for(root, archive).exists() and not op.get("archive_started"):
            raise IngestError("conflict", "Archive destination appeared after preview", path=archive)
        ensure_request(root, directory, op)
        op["state"] = "applying"
        save_operation(directory, op)
        write_json(state_dir(root) / "pending.json", {"operation_id": operation_id})
        try:
            for step in op["steps"]:
                if step["done"]:
                    continue
                path = step["path"]
                target = path_for(root, path)
                current = sha(read_bytes(root, path)) if target.exists() else None
                if current == step["after"] and step.get("started"):
                    step["done"] = True
                    save_operation(directory, op)
                    continue
                step["started"] = True
                save_operation(directory, op)
                publish(root, path, (directory / "blobs" / step["blob"]).read_bytes(), step["before"])
                step["done"] = True
                save_operation(directory, op)
            if archive:
                op["archive_started"] = True
                save_operation(directory, op)
                destination = path_for(root, archive)
                if not destination.exists():
                    publish(root, archive, (directory / "source.md").read_bytes(), None)
                if sha(read_bytes(root, archive)) != op["source"]["sha256"]:
                    raise IngestError("conflict", "Archive differs from the approved source", path=archive)
                if source_file.exists():
                    if sha(read_bytes(root, source)) != op["source"]["sha256"]:
                        raise IngestError("conflict", "Source changed before archival", path=source)
                    source_file.unlink()
                    sync_dir(source_file.parent)
            op["state"] = "committed"
            op["search_state"] = "search_pending"
            op.pop("last_error", None)
            save_operation(directory, op)
            finish_request(root, op)
            (state_dir(root) / "pending.json").unlink()
            sync_dir(state_dir(root))
            return op
        except Exception as exc:
            op["state"] = "conflict" if isinstance(exc, IngestError) else "failed_recoverable"
            op["last_error"] = str(exc) if isinstance(exc, IngestError) else type(exc).__name__
            save_operation(directory, op)
            raise IngestError(op["state"], "Application interrupted; resume this operation after resolving the cause",
                              operation_id=operation_id, reason=op["last_error"]) from None
