$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root "windows_path_alias.ps1")
$RuntimeRoot = Resolve-InvoiceAssistantWindowsRuntimeRoot -Root $Root
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory = $true)][string]$Command,
    [string[]]$Arguments = @()
  )
  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$Command failed with exit code $LASTEXITCODE"
  }
}

Invoke-CheckedNative -Command $Python -Arguments @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)")
Invoke-CheckedNative -Command $Python -Arguments @("-m", "venv", (Join-Path $RuntimeRoot ".venv"))
$VenvPython = Join-Path $RuntimeRoot ".venv\Scripts\python.exe"
Invoke-CheckedNative -Command $VenvPython -Arguments @("-m", "pip", "install", "--no-index", "--find-links", (Join-Path $RuntimeRoot "wheels"), "-r", (Join-Path $RuntimeRoot "runtime-requirements.txt"))
Write-Host "Invoice Assistant offline runtime installed: $(Join-Path $Root '.venv')"
if ($RuntimeRoot -ne $Root) {
  Write-Host "Windows short path alias used: $RuntimeRoot"
}
