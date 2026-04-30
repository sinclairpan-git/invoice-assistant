$ErrorActionPreference = "Stop"

$BundleRoot = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
$WorkspaceRoot = Join-Path $BundleRoot "workspace"

if (-not (Test-Path $WorkspaceRoot)) {
    throw "Missing workspace directory: $WorkspaceRoot"
}

function Assert-CommandExists {
    param([string]$Name, [string]$Hint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is not available on PATH. $Hint"
    }
}

function Resolve-BootstrapPython {
    param([string]$WorkspaceRoot)

    $candidates = @(
        [PSCustomObject]@{ Command = (Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"); Arguments = @() },
        [PSCustomObject]@{ Command = "python"; Arguments = @() },
        [PSCustomObject]@{ Command = "py"; Arguments = @("-3.11") }
    )

    foreach ($candidate in $candidates) {
        $command = $candidate.Command
        if ($command -like "*.exe") {
            if (-not (Test-Path $command)) {
                continue
            }
        }
        elseif (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            continue
        }

        try {
            & $command @($candidate.Arguments + @("--version")) *> $null
            return $candidate
        }
        catch {
            continue
        }
    }

    throw "No usable Python 3.11+ command found. Install Python or prepare workspace\.venv first."
}

function Invoke-Python {
    param(
        [pscustomobject]$Python,
        [string[]]$Arguments
    )

    & $Python.Command @($Python.Arguments + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Python.Command) $($Arguments -join ' ')"
    }
}

function Ensure-VenvPip {
    param([pscustomobject]$Python)
    Invoke-Python -Python $Python -Arguments @("-m", "ensurepip", "--upgrade")
}

function Assert-LastExitCode {
    param([string]$CommandLabel)
    if ($LASTEXITCODE -ne 0) {
        throw "$CommandLabel failed with exit code $LASTEXITCODE"
    }
}

Assert-CommandExists -Name "git" -Hint "Install Git for Windows first."
Assert-CommandExists -Name "node" -Hint "Install Node.js 20+ first."
Assert-CommandExists -Name "corepack" -Hint "Enable corepack in the Node.js installation first."

Set-Location $WorkspaceRoot

$env:COREPACK_HOME = Join-Path $WorkspaceRoot ".cache\corepack"
New-Item -ItemType Directory -Force -Path $env:COREPACK_HOME | Out-Null

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "==> Using uv for Python environment setup"

    Write-Host "==> Syncing workspace Python environment"
    uv sync
    Assert-LastExitCode -CommandLabel "uv sync"

    Write-Host "==> Syncing backend Python environment"
    uv sync --project backend --extra dev
    Assert-LastExitCode -CommandLabel "uv sync --project backend --extra dev"
}
else {
    $BootstrapPython = Resolve-BootstrapPython -WorkspaceRoot $WorkspaceRoot

    Write-Host "==> uv not found, falling back to Python venv + pip"

    if (-not (Test-Path (Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"))) {
        Write-Host "==> Creating workspace virtual environment"
        Invoke-Python -Python $BootstrapPython -Arguments @("-m", "venv", ".venv")
    }

    $WorkspacePython = [PSCustomObject]@{
        Command = (Join-Path $WorkspaceRoot ".venv\Scripts\python.exe")
        Arguments = @()
    }

    Ensure-VenvPip -Python $WorkspacePython

    Write-Host "==> Installing workspace Python dependencies"
    Invoke-Python -Python $WorkspacePython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Python -Python $WorkspacePython -Arguments @("-m", "pip", "install", "-e", ".")

    if (-not (Test-Path (Join-Path $WorkspaceRoot "backend\.venv\Scripts\python.exe"))) {
        Write-Host "==> Creating backend virtual environment"
        Invoke-Python -Python $BootstrapPython -Arguments @("-m", "venv", "backend\.venv")
    }

    $BackendPython = [PSCustomObject]@{
        Command = (Join-Path $WorkspaceRoot "backend\.venv\Scripts\python.exe")
        Arguments = @()
    }

    Ensure-VenvPip -Python $BackendPython

    Write-Host "==> Installing backend Python dependencies"
    Invoke-Python -Python $BackendPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Push-Location (Join-Path $WorkspaceRoot "backend")
    try {
        Invoke-Python -Python $BackendPython -Arguments @("-m", "pip", "install", "-e", ".[dev]")
    }
    finally {
        Pop-Location
    }
}

Write-Host "==> Installing frontend Node dependencies"
$env:CI = "true"
corepack pnpm --dir frontend install --frozen-lockfile
Assert-LastExitCode -CommandLabel "corepack pnpm --dir frontend install --frozen-lockfile"

Write-Host ""
Write-Host "Done."
Write-Host "Windows development scripts are ready under windows-dev/."
