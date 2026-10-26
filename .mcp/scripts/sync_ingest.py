#!/usr/bin/env python3
"""Host entry point: publish reviewed ingestions or guard the ordinary deploy."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daedalus_paths import REPO_DIR

from daedalus_ingest.git_sync import Publisher
from daedalus_ingest.publication import coordination, file_lock, sync_root
from daedalus_ingest.storage import IngestError

VERIFIED = "refs/heads/ci/verified-main"


def deploy(root):
    publisher = Publisher(root)
    with file_lock(sync_root(root) / "deploy.lock", nonblocking=True):
        result = publisher.run(maintenance=True)
        if result["pushed"]:
            print("Ingestões publicadas. Deploy adiado para o workflow do novo commit.")
            return 75
        with coordination(root, maintenance=True):
            # Unknown manual edits are never auto-staged or discarded to deploy.
            if publisher.git("status", "--porcelain", "--untracked-files=all").stdout.strip():
                raise IngestError("conflict", "Checkout has changes outside completed ingestions; deploy stopped")
            remote = publisher.fetch()
            publisher.git("fetch", "--no-tags", "origin",
                          VERIFIED + ":refs/remotes/origin/ci/verified-main")
            verified = publisher.oid("refs/remotes/origin/ci/verified-main")
            if remote != verified:
                raise IngestError("busy", "Latest main has not completed Verify; deploy stopped")
            print("==> Atualizando código (" + verified[:12] + ")", flush=True)
            # Keep the SSH command argument-free. Fetch the verified commit of
            # main rather than a moving branch tip between verification/pull.
            publisher.git("pull", "--ff-only", "origin", verified)
            if publisher.oid("HEAD") != verified:
                raise IngestError("conflict", "Checkout did not reach the verified commit")
        # The write lock is released so /ready can build its index. The deploy
        # gate remains exclusive, rejecting new ingestion until recreation ends.
        print("==> Construindo imagem do MCP", flush=True)
        compose = ["docker", "compose", "-f", str(root / ".mcp/docker-compose.yml")]
        subprocess.run([*compose, "build", "daedalus-mcp"], cwd=root, check=True)
        print("==> Recriando container e aguardando healthcheck", flush=True)
        subprocess.run([*compose, "up", "-d", "--force-recreate", "--wait",
                        "--wait-timeout", "180", "daedalus-mcp"], cwd=root, check=True)
        print("==> Deploy concluído", flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("publish", "deploy"))
    parser.add_argument("--repo", type=Path, default=REPO_DIR)
    args = parser.parse_args()
    root = args.repo.resolve()
    try:
        if args.command == "deploy":
            return deploy(root)
        result = Publisher(root).run()
        if result["state"] != "idle":
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except IngestError as exc:
        print(json.dumps(exc.result(), ensure_ascii=False), file=sys.stderr)
        return 75
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"state": "failed_recoverable", "error": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
