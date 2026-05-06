$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root "windows_path_alias.ps1")
$RuntimeRoot = Resolve-InvoiceAssistantWindowsRuntimeRoot -Root $Root
$PythonExe = Join-Path $RuntimeRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonExe)) {
  Write-Error "Missing offline runtime. Run install_offline.bat first."
  exit 1
}

& $PythonExe (Join-Path $RuntimeRoot "app\bootstrap\start_server.py") --portable-root $RuntimeRoot --host 127.0.0.1 --port 18080
exit $LASTEXITCODE
