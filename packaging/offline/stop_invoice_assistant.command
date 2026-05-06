#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Invoice Assistant is not running."
  exit 0
fi

exec "${PYTHON}" "${ROOT}/app/bootstrap/stop_portable.py" --portable-root "${ROOT}"
