#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "首次启动：正在安装离线运行环境，请稍等..."
  "${ROOT}/install_offline.sh"
fi

exec "${PYTHON}" "${ROOT}/app/bootstrap/start_server.py" --portable-root "${ROOT}" --host 127.0.0.1 --port 18080
