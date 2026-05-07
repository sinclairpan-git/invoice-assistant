#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "首次启动：正在安装离线运行环境，请稍等..."
  "${ROOT}/install_offline.sh"
fi

exec "${ROOT}/start_invoice_assistant.command"
