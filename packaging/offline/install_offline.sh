#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
VENV="${ROOT}/.venv"

"${PYTHON}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
"${PYTHON}" -m venv "${VENV}"
"${VENV}/bin/python" -m pip install --no-index --find-links "${ROOT}/wheels" -r "${ROOT}/runtime-requirements.txt"

echo "Invoice Assistant offline runtime installed: ${VENV}"
