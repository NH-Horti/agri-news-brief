param(
    [string]$OutputDir = ".local-builds\\admin-dashboard",
    [string]$SearchIndex = "docs\\search_index.json",
    [int]$Days = 120,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-PythonCommand([string]$RepoRoot) {
    $venvPython = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Resolve-EnvFile([string]$RepoRoot) {
    if ($env:AGRI_ENV_FILE) {
        return $env:AGRI_ENV_FILE
    }
    $candidates = @(
        (Join-Path $RepoRoot ".env.final.local"),
        (Join-Path $RepoRoot ".env.local")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return ""
}

$repoRoot = Get-RepoRoot
$pythonCmd = Get-PythonCommand $repoRoot
$envFile = Resolve-EnvFile $repoRoot
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$searchIndexPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $SearchIndex))

if ($envFile) {
    $env:AGRI_ENV_FILE = $envFile
}

$args = @(
    "scripts/build_admin_analytics.py",
    "--output-dir", $outputPath,
    "--search-index", $searchIndexPath,
    "--days", [string]$Days
)
if ($Strict) {
    $args += "--strict"
}

Push-Location $repoRoot
try {
    & $pythonCmd @args
    if ($envFile) {
        Write-Host "[local-admin-dashboard] env file: $envFile"
    }
    Write-Host "[local-admin-dashboard] search index: $searchIndexPath"
    Write-Host "[local-admin-dashboard] output: $outputPath"
}
finally {
    Pop-Location
}
