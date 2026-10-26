"""Create raw Markdown independently of ingestion; journal only the new file."""
from __future__ import annotations

import json

from . import apply as application
from .publication import ensure_request, finish_request, publication_status
from .sources import CATEGORIES, MAX_SOURCE_BYTES, archive_path, path_for, read_bytes
from .storage import (IngestError, durable_write, load_operation, save_operation,
                      sha, state_dir, sync_dir, vault_lock, write_json)
from .validation import check_credentials, check_source, require


def result(root, op, *, reused=False):
    source = op["source"]
    return {"schema_version": 1, "operation_id": op["operation_id"], "kind": "raw_note",
            "state": "saved" if op["state"] == "committed" else op["state"],
            "path": source["path"], "sha256": source["sha256"], "bytes": source["bytes"],
            "reused": reused, "ingestion_requested": False,
            "publication": publication_status(root, op["operation_id"]),
            "last_error": op.get("last_error")}


def create(root, owner, category, filename, content):
    require(isinstance(category, str) and category in CATEGORIES, "Unknown raw category")
    require(isinstance(filename, str) and filename not in {"", ".md"}
            and "/" not in filename and "\\" not in filename
            and len(filename.encode("utf-8")) <= 240, "Expected a Markdown filename without directories")
    relative = f"raw/{category}/{filename}"
    path_for(root, relative, area="raw")
    require(isinstance(content, str) and bool(content.strip()), "Nonempty Markdown content is required")
    data = content.encode("utf-8")
    require(len(data) <= MAX_SOURCE_BYTES, "Raw note exceeds 2 MB")
    check_credentials(b"", data, relative)
    check_source(data, relative)
    checksum = sha(data)
    # A deterministic identity lets the client recover a lost response simply
    # by repeating the same call, without a second upload/session protocol.
    operation = sha(json.dumps(["raw_note", owner, relative, checksum], ensure_ascii=False))[:32]
    with vault_lock(root, operation):
        directory = state_dir(root) / "operations" / operation
        marker = state_dir(root) / "pending.json"
        if (directory / "operation.json").exists():
            directory, op = load_operation(root, operation)
            if op["state"] == "committed":
                # Never re-create a source that was subsequently archived or
                # removed by an authorized action. The journal remains historical.
                for existing in (relative, archive_path(relative)):
                    if path_for(root, existing).exists():
                        require(read_bytes(root, existing) == data, "Existing raw note differs", path=existing)
                        reply = result(root, op, reused=True)
                        reply.update(path=existing, cataloged=existing != relative)
                        if marker.exists():
                            marker.unlink()
                            sync_dir(marker.parent)
                        return reply
                raise IngestError("conflict", "Previously saved note is no longer present", operation_id=operation)
        else:
            # Existing notes are never silently enrolled for Git publication.
            for existing in (relative, archive_path(relative)):
                if path_for(root, existing).exists():
                    require(read_bytes(root, existing) == data, "Existing raw note differs", path=existing)
                    return {"schema_version": 1, "kind": "raw_note", "state": "saved", "operation_id": None,
                            "path": existing, "sha256": checksum, "bytes": len(data), "reused": True,
                            "ingestion_requested": False, "cataloged": existing != relative,
                            "publication": {"state": "not_requested"}}
            op = {"schema_version": 1, "kind": "raw_note", "operation_id": operation,
                  "vault": str(root), "owner": owner, "state": "applying", "archive": None,
                  "source": {"path": relative, "sha256": checksum, "bytes": len(data)},
                  "proposal_digest": sha(json.dumps([relative, checksum])),
                  "steps": [{"path": relative, "before": None, "after": checksum,
                             "blob": checksum, "done": False}]}
            durable_write(directory / "blobs" / checksum, data)
            save_operation(directory, op)
        try:
            write_json(marker, {"operation_id": operation})
            ensure_request(root, directory, op)
            target = path_for(root, relative)
            if target.exists():
                require(read_bytes(root, relative) == data, "Raw note changed during recovery", path=relative)
            else:
                application.publish(root, relative, data, None)
            op["steps"][0]["done"] = True
            op["state"] = "committed"
            op.pop("last_error", None)
            # Mark the request pending before saving committed state. A crash
            # can then always be resumed by the same deterministic call.
            finish_request(root, op)
            save_operation(directory, op)
            marker.unlink(missing_ok=True)
            sync_dir(marker.parent)
        except (OSError, ValueError) as exc:
            op["state"] = "failed_recoverable"
            op["last_error"] = type(exc).__name__
            save_operation(directory, op)
            raise IngestError("failed_recoverable", "Repeat the same create_raw_note call to resume",
                              operation_id=operation) from exc
        return result(root, op)
