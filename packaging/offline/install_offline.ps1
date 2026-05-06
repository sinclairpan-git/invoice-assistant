$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
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
Invoke-CheckedNative -Command $Python -Arguments @("-m", "venv", (Join-Path $Root ".venv"))
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
Invoke-CheckedNative -Command $VenvPython -Arguments @("-m", "pip", "install", "--no-index", "--find-links", (Join-Path $Root "wheels"), "-r", (Join-Path $Root "runtime-requirements.txt"))
Write-Host "Invoice Assistant offline runtime installed: $(Join-Path $Root '.venv')"
