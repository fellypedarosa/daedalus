"""Application files live in .mcp; knowledge and Git keep their original root."""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parent
POLICY_PATH = APP_DIR / "INGEST.md"


def vault_dir():
    return Path(os.environ.get("DAEDALUS_VAULT_DIR") or REPO_DIR).resolve()
