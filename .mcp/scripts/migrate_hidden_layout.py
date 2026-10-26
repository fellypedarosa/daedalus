#!/usr/bin/env python3
"""One-time host migration after the tracked .mcp layout has been received.

Default: inspect. --apply: move private files/state, without Git, cron or Docker
mutations. Pause the Daedalus workflow/cron and stop its container first.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
from contextlib import ExitStack
from pathlib import Path


PRIVATE = {"tokens.json", "mcp.json", "tmp", ".gemini_worker_context.md",
           ".mcp_access_audit.jsonl", ".mcp_test_audit.jsonl",
           ".task_instruction.txt", ".worker_output.md", ".worker_err.log"}


def present(path):
    return path.exists() or path.is_symlink()


def checked(path, root):
    """Never follow a source or destination symlink during this migration."""
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError("Link simbólico exige revisão: " + str(item.relative_to(root)))


def fingerprint(path):
    if path.is_symlink():
        return {"symlink": os.readlink(path)}
    if path.is_dir():
        return {str(p.relative_to(path)): fingerprint(p) for p in sorted(path.iterdir())}
    if not path.is_file():
        raise ValueError("Tipo de arquivo inesperado: " + path.name)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(root):
    root = Path(root).resolve()
    app = root / ".mcp"
    if not (app / "docker-compose.yml").is_file():
        raise ValueError("Receba primeiro o código versionado em .mcp; não renomeie MCP manualmente.")
    moves = []

    def collect(source, target):
        checked(source, root)
        checked(target, root)
        if present(target):
            if source.is_dir() and target.is_dir():
                for child in sorted(source.iterdir()):
                    collect(child, target / child.name)
                return
            raise ValueError("Destino já existe; nenhuma mesclagem automática: " + str(target.relative_to(root)))
        moves.append((source, target))

    old = root / "MCP"
    if present(old):
        checked(old, root)
        for item in sorted(old.iterdir()):
            if item.name in PRIVATE or item.name.startswith(".env"):
                collect(item, app / item.name)
            else:
                # Preserve old venvs/caches as archives; never execute them.
                cache = item.name == ".venv" or all(
                    p.is_dir() or (p.suffix == ".pyc" and p.parent.name == "__pycache__")
                    for p in ([item] if item.is_file() else item.rglob("*")))
                if not cache or item.is_symlink():
                    raise ValueError("Arquivo antigo exige revisão: " + str(item.relative_to(root)))
                collect(item, app / "tmp/migracao-layout/MCP" / item.name)

    legacy, current = root / ".daedalus-sync", app / ".daedalus-sync"
    if present(legacy):
        checked(legacy, root)
        if present(current):
            raise ValueError("Há dois diretórios de sincronização; preserve ambos e revise antes de continuar.")
        checked(current, root)
        moves.append((legacy, current))
    elif not current.is_dir():
        raise ValueError("Estado de sincronização existente não encontrado; não será criado um estado vazio.")
    else:
        checked(current, root)

    state = legacy if legacy.exists() else current
    for item in state.rglob("*"):
        checked(item, root)
    for request in (state / "operations").glob("*/request.json"):
        checked(request, root)
        data = json.loads(request.read_text())
        if data.get("state") != "pending":
            raise ValueError("Operação incompleta: " + request.parent.name + "; retome-a pelo MCP antes de migrar.")
    # Validate every byte/tree now, before the first move.
    for source, _ in moves:
        fingerprint(source)
    # Detect collisions inside a private directory that is also being moved.
    for source, target in moves:
        for other_source, other_target in moves:
            if source != other_source and target.is_relative_to(other_target):
                future = other_source / target.relative_to(other_target)
                if present(future):
                    raise ValueError("Destino já existe no conteúdo a migrar: " + str(target.relative_to(root)))
    # Move a private tmp tree before placing archived caches underneath it.
    return sorted(moves, key=lambda pair: len(pair[1].parts))


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs).stdout


def assert_quiet(root):
    actual = Path(run("git", "-C", str(root), "rev-parse", "--show-toplevel").strip()).resolve()
    if actual != root:
        raise ValueError("Execute na raiz do checkout Daedalus.")
    if run("git", "-C", str(root), "ls-files", "--", "MCP").strip():
        raise ValueError("O checkout ainda contém código versionado em MCP; atualize-o primeiro.")
    container = json.loads(run("docker", "inspect", "daedalus-mcp"))[0]
    mounts = {m["Destination"]: m["Source"] for m in container["Mounts"]}
    if Path(mounts.get("/vault/wiki", "")).resolve() != root / "wiki":
        raise ValueError("O container pertence a outro checkout.")
    if container["State"]["Running"]:
        raise ValueError("Pare o container daedalus-mcp antes de migrar.")
    cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                          env={**os.environ, "LC_ALL": "C"})
    if cron.returncode not in (0, 1) or (cron.returncode == 1 and "no crontab" not in cron.stderr.lower()):
        raise ValueError("Não foi possível conferir o cron.")
    for line in cron.stdout.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            if "daedalus-ingest-publisher" in line or (str(root) in line and "auto_backup.sh" in line):
                raise ValueError("Pause somente o agendamento do Daedalus antes de migrar.")


def migrate(root):
    root = Path(root).resolve()
    # All callers (including tests) must hold the same old/new state locks.
    with ExitStack() as stack:
        paths = [root / run("git", "-C", str(root), "rev-parse", "--git-path", "daedalus-deploy.lock").strip()]
        state = root / ".daedalus-sync"
        if not state.exists():
            state = root / ".mcp/.daedalus-sync"
        for name in ("deploy.lock", "writer.lock"):
            if (state / name).exists():
                paths.append(state / name)
        for path in paths:
            checked(path, root)
            stream = stack.enter_context(path.open("rb" if path.exists() else "ab+"))
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        moves = plan(root)
        for source, target in moves:
            expected = fingerprint(source)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if present(target):
                raise ValueError("Destino apareceu durante a migração: " + str(target.relative_to(root)))
            source.rename(target)
            if fingerprint(target) != expected:
                raise ValueError("Falha na conferência do conteúdo: " + str(target.relative_to(root)))
            print("Movido e conferido: " + str(source.relative_to(root)) + " -> " + str(target.relative_to(root)))
        old = root / "MCP"
        if old.exists():
            for directory in sorted((p for p in old.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                directory.rmdir()
            old.rmdir()
    return len(moves)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="Mover somente após todas as conferências")
    args = parser.parse_args()
    root = args.repo.resolve()
    try:
        assert_quiet(root)
        moves = plan(root)
        print(f"Conferência concluída: {len(moves)} movimentações; nenhum destino será sobrescrito.")
        if args.apply:
            migrate(root)
            print("Migração concluída. Revise a operação independente conforme deploy/deploy.md antes de reativar qualquer automação.")
        else:
            for source, target in moves:
                print(str(source.relative_to(root)) + " -> " + str(target.relative_to(root)))
            print("Somente inspeção. Use --apply para executar.")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, ValueError):
            message = str(exc)
        elif isinstance(exc, OSError):
            message = f"{type(exc).__name__}: {exc.filename or 'bloqueio/arquivo'}: {exc.strerror}"
        else:
            message = type(exc).__name__
        print("Migração interrompida: " + message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
