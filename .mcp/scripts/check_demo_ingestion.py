#!/usr/bin/env python3
"""Validate the public fictional corpus through the service API, without MCP/network.

Creates only disposable notes, Git commits and a local bare remote. The versioned
example is read-only. This does not prove STDIO/HTTP transport connectivity.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daedalus_paths import APP_DIR, REPO_DIR
from daedalus_ingest.service import IngestService
from daedalus_ingest.git_sync import Publisher
from daedalus_ingest.publication import publication_status
from daedalus_ingest.sources import archive_path
from daedalus_search.engine import SearchEngine


def snapshot(root):
    paths = sorted(root.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("The synthetic example must not contain symbolic links")
    return {str(p.relative_to(root)): p.read_bytes() for p in paths if p.is_file()}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check():
    example = REPO_DIR / "examples/vault"
    require(example.is_dir(), "Run from a source checkout containing examples/vault")
    original = snapshot(example)
    # No inherited Git credentials, configuration, hooks or alternate Git dirs.
    git_environment = {"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1",
                       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}
    with tempfile.TemporaryDirectory(prefix="daedalus-demo-check-") as directory:
        base = Path(directory)
        vault = base / "vault"
        shutil.copytree(example, vault)
        os.environ["DAEDALUS_INGEST_DIR"] = str(base / "ingest")
        os.environ["DAEDALUS_SYNC_DIR"] = str(vault / ".mcp/.daedalus-sync")
        # Publisher invokes Git itself: isolate its inherited environment too.
        for name in list(os.environ):
            if name.startswith("GIT_"):
                del os.environ[name]
        os.environ.update(git_environment)

        def git(at, *args):
            return subprocess.run(["git", "-c", "core.hooksPath=/dev/null",
                "-c", "user.name=Synthetic demonstration", "-c", "user.email=demo@example.invalid",
                "-C", str(at), *args], env=git_environment, check=True, capture_output=True).stdout

        remote = base / "remote.git"
        git(base, "init", "--template=", "--bare", "--initial-branch=main", str(remote))
        git(vault, "init", "--template=", "--initial-branch=main")
        (vault / ".gitignore").write_text(".mcp/\n")
        git(vault, "add", "raw", "wiki", ".gitignore")
        git(vault, "commit", "-m", "Synthetic test base")
        git(vault, "remote", "add", "origin", str(remote))
        git(vault, "push", "origin", "main")
        engine = SearchEngine(vault, base / "index", interval=0)
        try:
            engine.reindex(semantic=False)
            # Explicit synchronous reindexing keeps this check deterministic;
            # background indexing/recovery has separate integration tests.
            service = IngestService(vault)
            captured_text = ("# Fonte de teste fictícia\n\nAutor: [[LLM]]\n\n"
                             "O simulador não controla dispositivos.\n")
            wiki_before = snapshot(vault / "wiki")
            captured = service.create_raw_note("local", "Captura.md", captured_text)
            require(captured["state"] == "saved" and not captured["ingestion_requested"], "Capture failed")
            require((vault / captured["path"]).read_bytes() == captured_text.encode(), "Capture changed bytes")
            require(snapshot(vault / "wiki") == wiki_before, "Capture changed wiki")
            Publisher(vault).run()
            require(publication_status(vault, captured["operation_id"])["state"] == "published", "Capture publication failed")

            source = "raw/local/Sensores.md"
            source_bytes = (vault / source).read_bytes()
            text = source_bytes.decode()
            prepared = service.prepare(source, "public-demo-check")
            require(prepared["text"] == text, "Preparation changed source")
            target = "wiki/Laboratorio/Alertas.md"
            lines = text.splitlines()
            line = next(i for i, value in enumerate(lines, 1) if "30 por cento" in value)
            content = ('---\ntags: [demonstracao, ficticio]\ndate_created: 2026-10-25\n'
                'sources:\n  - "[[raw/local/Sensores]]"\n---\n# Alerta de umidade\n\nAutor: [[LLM]]\n\n'
                'No laboratório fictício Jardim Aurora, o limiar é 30 por cento. '
                'O alerta pede conferência manual antes de irrigação.\n')
            proposal = {"summary": "Check the fictional alert threshold", "archive": True,
                "coverage": [{"start_line": 1, "end_line": len(lines), "decision": "create", "targets": [target],
                    "reason": "Preserve the fictional context and manual confirmation"}],
                "changes": [{"action": "create", "path": target, "description": "Fictional alert threshold",
                    "content": content, "evidence": [{"start_line": line, "end_line": line, "quote": lines[line - 1]}]}]}
            before = {str(p.relative_to(vault)): p.read_bytes() for p in vault.rglob("*.md")}
            preview = service.preview(prepared["operation_id"], proposal)
            require(preview["state"] == "validated", "Preview failed")
            require(before == {str(p.relative_to(vault)): p.read_bytes() for p in vault.rglob("*.md")}, "Preview changed notes")
            applied = service.apply(prepared["operation_id"], preview["proposal_digest"])
            require(applied["state"] == "committed", "Application failed")
            require((vault / archive_path(source)).read_bytes() == source_bytes, "Archive changed source bytes")
            engine.reindex(semantic=False)
            service.engine = engine
            require(service.status(prepared["operation_id"])["search_state"] == "search_ready", "Search not ready")
            service.engine = None
            paths = [r["path"] for r in engine.search("30 por cento", scope="wiki", mode="exact")["results"]]
            require(target in paths, "Applied note missing from search")
            replay = service.apply(prepared["operation_id"], preview["proposal_digest"])
            require(replay["state"] == "committed", "Replay failed")
            require(Publisher(vault).run()["state"] == "published", "Ingestion publication failed")
            require(git(remote, "show", "main:" + target).decode() == content, "Published note differs")
            require(git(remote, "show", "main:" + archive_path(source)) == source_bytes, "Published source differs")
            require(Publisher(vault).run()["state"] == "idle", "Publication was not idempotent")
        finally:
            engine.close()
    require(snapshot(example) == original, "Versioned example changed")
    return {"transport": "direct service API; not MCP proof", "capture": "saved_without_ingestion",
        "preview_notes_unchanged": True, "source_bytes_preserved": True, "apply": "committed",
        "search": "search_ready", "replay": "idempotent",
        "publication": "published_to_disposable_local_remote", "example_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=APP_DIR / "tmp/demo-ingestion-check.json")
    args = parser.parse_args()
    result = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
