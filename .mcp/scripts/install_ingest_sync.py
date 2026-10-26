#!/usr/bin/env python3
"""Install/update this checkout's single publication cron job (run on the host)."""
import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKER = "# daedalus-ingest-publisher"


def main():
    if (ROOT / ".daedalus-sync").exists() or (ROOT / ".daedalus-sync").is_symlink():
        raise SystemExit("Migre .daedalus-sync para .mcp/.daedalus-sync antes de instalar o cron.")
    base = ROOT / ".mcp/.daedalus-sync"
    if base.is_symlink():
        raise SystemExit(".daedalus-sync não pode ser um link simbólico.")
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not os.access(base, os.W_OK):
        raise SystemExit(".daedalus-sync precisa pertencer ao usuário do deploy. Ajuste a propriedade antes de instalar.")
    for name in ("operations", "receipts"):
        (base / name).mkdir(exist_ok=True)
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                             env={**os.environ, "LC_ALL": "C"})
    if current.returncode not in (0, 1) or (current.returncode == 1 and "no crontab" not in current.stderr.lower()):
        raise SystemExit("Não foi possível consultar o crontab; nenhuma alteração aplicada.")
    backup = base / "crontab.before"
    backup.write_text(current.stdout)
    backup.chmod(0o600)
    script = ROOT / ".mcp/scripts/auto_backup.sh"
    legacy_scripts = {ROOT / "scripts/auto_backup.sh", ROOT / "MCP/scripts/auto_backup.sh"}
    kept = []
    for line in current.stdout.splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "auto_backup.sh" in line:
            tokens = shlex.split(line)
            paths = [Path(t).expanduser().resolve() for t in tokens if t.endswith("auto_backup.sh")]
            if not paths or any(path not in {script, *legacy_scripts} for path in paths):
                raise SystemExit("Há outro agendamento auto_backup.sh; revise-o antes de instalar este executor.")
            continue
        kept.append(line)
    command = "/bin/bash " + shlex.quote(str(script)) + " >>" + shlex.quote(str(base / "worker.log")) + " 2>&1"
    kept.append("* * * * * " + command.replace("%", "\\%") + " " + MARKER)
    subprocess.run(["crontab", "-"], input="\n".join(kept) + "\n", text=True, check=True)
    print("Publicação de ingestões agendada a cada minuto. Agendamento anterior salvo em .mcp/.daedalus-sync/crontab.before.")


if __name__ == "__main__":
    main()
