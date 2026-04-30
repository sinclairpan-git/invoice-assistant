$ErrorActionPreference = "Stop"

$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Join-Path $BundleRoot "workspace"

Set-Location $WorkspaceRoot
$env:COREPACK_HOME = Join-Path $WorkspaceRoot ".cache\corepack"
New-Item -ItemType Directory -Force -Path $env:COREPACK_HOME | Out-Null
corepack pnpm --dir frontend dev -- --host 127.0.0.1 --port 5173
