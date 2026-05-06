$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root "windows_path_alias.ps1")
$RuntimeRoot = Resolve-InvoiceAssistantWindowsRuntimeRoot -Root $Root
$PythonExe = Join-Path $RuntimeRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonExe)) {
  Write-Host "Invoice Assistant is not running."
  exit 0
}

& $PythonExe (Join-Path $RuntimeRoot "app\bootstrap\stop_portable.py") --portable-root $RuntimeRoot
exit $LASTEXITCODE
