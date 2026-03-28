param(
    [Parameter(Mandatory = $true)]
    [string]$ReportDate,
    [string]$SnapshotDate = "",
    [string]$SnapshotRoot = ".local-builds\\dryrun",
    [string]$OutputDir = ".local-builds\\replay",
    [switch]$DebugReport,
    [switch]$AllowOpenAI
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-RepoSlug {
    try {
        $remote = (git remote get-url origin).Trim()
    }
    catch {
        return "NH-Horti/agri-news-brief"
    }

    if ($remote -match 'github\.com[:/](.+?/.+?)(?:\.git)?$') {
        return $matches[1]
    }
    return "NH-Horti/agri-news-brief"
}

function Get-PythonCommand([string]$RepoRoot) {
    $venvPython = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py"
    }
    throw "Neither python nor py was found on PATH."
}

function Resolve-EnvFile([string]$RepoRoot) {
    if ($env:AGRI_ENV_FILE) {
        return $env:AGRI_ENV_FILE
    }
    $candidates = @(
        (Join-Path $RepoRoot ".env.dev.local"),
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
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$snapshotRootPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $SnapshotRoot))
$envFile = Resolve-EnvFile $repoRoot

if (-not $SnapshotDate) {
    $SnapshotDate = $ReportDate
}

$snapshotPath = Join-Path (Join-Path (Join-Path $snapshotRootPath "main") ".agri_replay") "$SnapshotDate.snapshot.json"
if (-not (Test-Path $snapshotPath)) {
    throw "Replay snapshot not found: $snapshotPath"
}

$env:GITHUB_REPO = Get-RepoSlug
$env:GITHUB_REPOSITORY = $env:GITHUB_REPO
$env:AGRI_ENV_FILE = $envFile
$env:LOCAL_DRY_RUN = "true"
$env:LOCAL_OUTPUT_DIR = $outputPath
$env:MAINTENANCE_TASK = "replay_date"
$env:FORCE_REPORT_DATE = $ReportDate
$env:FORCE_RUN_ANYDAY = "true"
$env:MAINTENANCE_SEND_KAKAO = "false"
$env:WINDOW_MIN_HOURS = "0"
$env:CROSSDAY_DEDUPE_ENABLED = "false"
$env:UX_PATCH_DAYS = "0"
$env:REPLAY_SNAPSHOT_PATH = $snapshotPath
$env:REPLAY_WRITE_SNAPSHOT = "false"
$env:REPLAY_ALLOW_OPENAI = $(if ($AllowOpenAI) { "true" } else { "false" })
$env:BUILD_TAG = "local-replay-$($ReportDate -replace '-', '')"
$env:KAKAO_STATUS_FILE = Join-Path $env:TEMP "agri-news-brief-kakao-local.txt"

if ($DebugReport) {
    $env:DEBUG_REPORT = "1"
    $env:DEBUG_REPORT_WRITE_JSON = "1"
    $env:DEBUG_REPORT_MAX_CANDIDATES = "200"
    $env:DEBUG_REPORT_MAX_REJECTS = "2000"
} else {
    $env:DEBUG_REPORT = "0"
    $env:DEBUG_REPORT_WRITE_JSON = "0"
}

Push-Location $repoRoot
try {
    & $pythonCmd main.py
    if ($envFile) {
        Write-Host "[local-replay] env file: $envFile"
    }
    Write-Host "[local-replay] snapshot: $snapshotPath"
    Write-Host "[local-replay] output root: $outputPath"
}
finally {
    Pop-Location
}
