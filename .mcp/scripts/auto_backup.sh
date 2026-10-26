#!/usr/bin/env bash
################################################################################
# auto_backup.sh — Publish only completed, recorded Daedalus ingestions
#
# Cron entry point: .mcp/scripts/auto_backup.sh. No generic git add.
################################################################################
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

exec python3 .mcp/scripts/sync_ingest.py publish
