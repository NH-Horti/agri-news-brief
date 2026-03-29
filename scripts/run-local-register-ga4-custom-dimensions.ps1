param(
    [string]$PropertyId = "",
    [switch]$DryRun,
    [switch]$ListOnly
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

if ($envFile) {
    $env:AGRI_ENV_FILE = $envFile
}

$args = @("scripts/register_ga4_custom_dimensions.py")
if ($PropertyId) {
    $args += @("--property-id", $PropertyId)
}
if ($DryRun) {
    $args += "--dry-run"
}
if ($ListOnly) {
    $args += "--list-only"
}

Push-Location $repoRoot
try {
    & $pythonCmd @args
    if ($envFile) {
        Write-Host "[local-ga4-custom-dimensions] env file: $envFile"
    }
}
finally {
    Pop-Location
}
