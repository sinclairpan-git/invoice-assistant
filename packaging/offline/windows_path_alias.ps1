$ErrorActionPreference = "Stop"

function Get-InvoiceAssistantPathHash {
  param(
    [Parameter(Mandatory = $true)][string]$Path
  )

  $sha256 = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Path.ToLowerInvariant())
    $hashBytes = $sha256.ComputeHash($bytes)
    $builder = [System.Text.StringBuilder]::new()
    foreach ($byte in $hashBytes) {
      [void]$builder.Append($byte.ToString("x2"))
    }
    return $builder.ToString().Substring(0, 16)
  } finally {
    $sha256.Dispose()
  }
}

function Resolve-InvoiceAssistantAliasBase {
  $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
  if (-not [string]::IsNullOrWhiteSpace($localAppData)) {
    return Join-Path $localAppData "InvoiceAssistant\aliases"
  }
  return Join-Path ([System.IO.Path]::GetTempPath()) "InvoiceAssistant\aliases"
}

function Resolve-InvoiceAssistantWindowsRuntimeRoot {
  param(
    [Parameter(Mandatory = $true)][string]$Root
  )

  $resolvedRoot = [System.IO.Path]::GetFullPath($Root)
  if ($env:INVOICE_ASSISTANT_DISABLE_SHORT_PATH_ALIAS -eq "1") {
    return $resolvedRoot
  }

  $aliasBase = Resolve-InvoiceAssistantAliasBase
  New-Item -ItemType Directory -Force -Path $aliasBase | Out-Null

  $aliasName = "ia-$(Get-InvoiceAssistantPathHash -Path $resolvedRoot)"
  $aliasRoot = Join-Path $aliasBase $aliasName

  if (Test-Path -LiteralPath $aliasRoot) {
    $aliasItem = Get-Item -LiteralPath $aliasRoot -Force
    if (-not ($aliasItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
      throw "Windows short path alias exists but is not a junction: $aliasRoot"
    }
  } else {
    New-Item -ItemType Junction -Path $aliasRoot -Target $resolvedRoot | Out-Null
  }

  $runtimeDir = Join-Path $resolvedRoot "runtime"
  New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
  Set-Content -Path (Join-Path $runtimeDir "short-root.txt") -Value $aliasRoot -Encoding UTF8

  return $aliasRoot
}
