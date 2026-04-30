$ErrorActionPreference = "Stop"

$BundleRoot = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
$WorkspaceRoot = Join-Path $BundleRoot "workspace"

Set-Location $WorkspaceRoot

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    uv run --project backend uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000
    exit $LASTEXITCODE
}

$BackendPython = Join-Path $WorkspaceRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $BackendPython)) {
    throw "Missing backend\.venv\Scripts\python.exe. Run the Windows environment setup script first."
}

& $BackendPython -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
