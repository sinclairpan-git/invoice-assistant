param(
    [string]$Version = "0.1.0-dev",
    [string]$PythonVersion = "3.11.9"
)

$ErrorActionPreference = "Stop"

$BundleRoot = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
$WorkspaceRoot = Join-Path $BundleRoot "workspace"

function Resolve-BuildPython {
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

    throw "No usable Python 3.11+ command found. Run the Windows environment setup script first or install Python."
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

function Assert-LastExitCode {
    param([string]$CommandLabel)
    if ($LASTEXITCODE -ne 0) {
        throw "$CommandLabel failed with exit code $LASTEXITCODE"
    }
}

$RuntimeRoot = Join-Path $WorkspaceRoot ".tmp\windows-runtime\python-$PythonVersion-pip"

Set-Location $WorkspaceRoot
$Python = Resolve-BuildPython -WorkspaceRoot $WorkspaceRoot
$env:COREPACK_HOME = Join-Path $WorkspaceRoot ".cache\corepack"
New-Item -ItemType Directory -Force -Path $env:COREPACK_HOME | Out-Null

Write-Host "==> Building frontend production assets"
corepack pnpm --dir frontend build
Assert-LastExitCode -CommandLabel "corepack pnpm --dir frontend build"

Write-Host "==> Preparing the Windows portable runtime"
Invoke-Python -Python $Python -Arguments @("scripts/prepare_windows_portable_runtime.py", "--runtime-root", $RuntimeRoot, "--python-version", $PythonVersion)

Write-Host "==> Building the Windows portable bundle"
Invoke-Python -Python $Python -Arguments @("scripts/build_windows_portable.py", "--version", $Version, "--python-runtime-root", $RuntimeRoot)

Write-Host ""
Write-Host "Done. Artifacts are available under workspace\dist\."
