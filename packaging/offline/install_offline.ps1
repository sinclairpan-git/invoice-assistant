$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

& $Python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
& $Python -m venv (Join-Path $Root ".venv")
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPython -m pip install --no-index --find-links (Join-Path $Root "wheels") -r (Join-Path $Root "runtime-requirements.txt")
Write-Host "Invoice Assistant offline runtime installed: $(Join-Path $Root '.venv')"
