$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$ReportDate,
    [string]$OutputDir = ".local-builds\\dryrun",
    [switch]$DebugReport,
    [switch]$SkipOpenAI
)

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
    return "python"
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
$envFile = Resolve-EnvFile $repoRoot

$env:GITHUB_REPO = Get-RepoSlug
$env:GITHUB_REPOSITORY = $env:GITHUB_REPO
$env:AGRI_ENV_FILE = $envFile
$env:LOCAL_DRY_RUN = "true"
$env:LOCAL_OUTPUT_DIR = $outputPath
$env:MAINTENANCE_TASK = "rebuild_date"
$env:FORCE_REPORT_DATE = $ReportDate
$env:FORCE_RUN_ANYDAY = "true"
$env:MAINTENANCE_SEND_KAKAO = "false"
$env:WINDOW_MIN_HOURS = "0"
$env:CROSSDAY_DEDUPE_ENABLED = "false"
$env:UX_PATCH_DAYS = "0"
$env:NAVER_MAX_WORKERS = "1"
$env:NAVER_MIN_INTERVAL_SEC = "0.6"
$env:BUILD_TAG = "local-dryrun-$($ReportDate -replace '-', '')"
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

if ($SkipOpenAI) {
    $env:OPENAI_API_KEY = ""
}

Push-Location $repoRoot
try {
    & $pythonCmd main.py
    if ($envFile) {
        Write-Host "[local-dryrun] env file: $envFile"
    }
    Write-Host "[local-dryrun] output root: $outputPath"
}
finally {
    Pop-Location
}
