#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Missing offline runtime. Run ./install_offline.sh first." >&2
  exit 1
fi

exec "${PYTHON}" "${ROOT}/app/bootstrap/start_server.py" --portable-root "${ROOT}" --host 127.0.0.1 --port 18080
