#!/bin/bash
set -euo pipefail

main() {
  local project_dir
  project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
  cd -- "$project_dir"

  # A trava fica nos metadados locais do Git, fora dos arquivos versionados.
  exec 9>"$(git rev-parse --git-path daedalus-deploy.lock)"
  if ! flock -n 9; then
    echo "Erro: já existe um deploy em execução." >&2
    exit 1
  fi

  # The host guard coordinates Git with ingestion and releases the data lock
  # before /ready, while holding the maintenance gate through recreation.
  python3 .mcp/scripts/sync_ingest.py deploy
}

# Tudo dentro de main + exit: o bash lê o script aos poucos, e o git pull
# pode alterar este próprio arquivo enquanto ele roda.
main "$@"
exit
