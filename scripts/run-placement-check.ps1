param(
    [Parameter(Mandatory = $true)]
    [string]$ReportDate,
    [string]$SnapshotDate = "",
    [string]$SnapshotRoot = ".agri_replay",
    [string]$OutputFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-PythonCommand([string]$RepoRoot) {
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
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
$envFile = Resolve-EnvFile $repoRoot

if (-not $SnapshotDate) {
    $SnapshotDate = $ReportDate
}

# 스냅샷 경로 탐색 (.agri_replay/ 우선, 없으면 .local-builds/dryrun/main/.agri_replay/)
$snapshotCandidates = @(
    (Join-Path $repoRoot (Join-Path $SnapshotRoot "$SnapshotDate.snapshot.json")),
    (Join-Path $repoRoot ".local-builds\dryrun\main\.agri_replay\$SnapshotDate.snapshot.json")
)
$snapshotPath = $null
foreach ($candidate in $snapshotCandidates) {
    if (Test-Path $candidate) {
        $snapshotPath = $candidate
        break
    }
}
if (-not $snapshotPath) {
    throw "Replay snapshot not found. Tried: $($snapshotCandidates -join '; ')"
}

if (-not $OutputFile) {
    $OutputFile = Join-Path $repoRoot ".local-debug\placement\$ReportDate.json"
}
$outputDir = Split-Path -Parent $OutputFile
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$env:AGRI_ENV_FILE = $envFile
$env:LOCAL_DRY_RUN = "true"
$env:MAINTENANCE_TASK = "replay_date"
$env:FORCE_REPORT_DATE = $ReportDate
$env:FORCE_RUN_ANYDAY = "true"
$env:MAINTENANCE_SEND_KAKAO = "false"
$env:WINDOW_MIN_HOURS = "0"
$env:CROSSDAY_DEDUPE_ENABLED = "false"
$env:UX_PATCH_DAYS = "0"
$env:REPLAY_SNAPSHOT_PATH = $snapshotPath
$env:REPLAY_WRITE_SNAPSHOT = "false"
$env:REPLAY_ALLOW_OPENAI = "false"
$env:BUILD_TAG = "placement-check-$($ReportDate -replace '-', '')"
$env:KAKAO_STATUS_FILE = Join-Path $env:TEMP "agri-news-brief-kakao-placement.txt"
$env:PLACEMENT_ONLY = "1"
$env:PLACEMENT_ONLY_OUTPUT = $OutputFile
$env:DEBUG_REPORT = "1"
$env:DEBUG_REPORT_WRITE_JSON = "0"
$env:DEBUG_REPORT_MAX_CANDIDATES = "200"
$env:DEBUG_REPORT_MAX_REJECTS = "2000"
# 더미 GitHub 토큰으로 load_summary_cache 스킵 (PLACEMENT_ONLY 경로는 이를 건너뜀)
if (-not $env:GITHUB_TOKEN) { $env:GITHUB_TOKEN = "placeholder" }
if (-not $env:GH_TOKEN) { $env:GH_TOKEN = "placeholder" }
if (-not $env:GITHUB_REPO) { $env:GITHUB_REPO = "NH-Horti/agri-news-brief" }
if (-not $env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY = $env:GITHUB_REPO }

Push-Location $repoRoot
try {
    Write-Host "[placement-check] snapshot: $snapshotPath"
    Write-Host "[placement-check] output:   $OutputFile"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $pythonCmd main.py
    $sw.Stop()
    Write-Host "[placement-check] elapsed: $([math]::Round($sw.Elapsed.TotalSeconds, 1))s"
    if (Test-Path $OutputFile) {
        Write-Host "[placement-check] success: $OutputFile"
    } else {
        Write-Warning "[placement-check] output file not written: $OutputFile"
    }
}
finally {
    Pop-Location
}
