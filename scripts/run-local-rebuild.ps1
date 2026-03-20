$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$ReportDate,
    [ValidateSet("dev", "prod")]
    [string]$Target = "dev",
    [switch]$SendKakao,
    [switch]$DebugReport,
    [int]$MaxPerSection = 5,
    [int]$UxPatchDays = 0
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

function Ensure-GitHubToken {
    if ($env:GH_TOKEN) {
        return $env:GH_TOKEN
    }
    if ($env:GITHUB_TOKEN) {
        $env:GH_TOKEN = $env:GITHUB_TOKEN
        return $env:GH_TOKEN
    }
    try {
        $token = (& gh auth token).Trim()
    }
    catch {
        $token = ""
    }
    if (-not $token) {
        throw "GH_TOKEN/GITHUB_TOKEN is not set and `gh auth token` was unavailable."
    }
    $env:GH_TOKEN = $token
    $env:GITHUB_TOKEN = $token
    return $token
}

function Resolve-EnvFile([string]$RepoRoot, [string]$TargetName) {
    if ($env:AGRI_ENV_FILE) {
        return $env:AGRI_ENV_FILE
    }
    $candidates = @()
    if ($TargetName -eq "dev") {
        $candidates += (Join-Path $RepoRoot ".env.dev.local")
    } else {
        $candidates += (Join-Path $RepoRoot ".env.final.local")
    }
    $candidates += (Join-Path $RepoRoot ".env.local")
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return ""
}

$repoRoot = Get-RepoRoot
$pythonCmd = Get-PythonCommand $repoRoot
$repoSlug = Get-RepoSlug
$envFile = Resolve-EnvFile $repoRoot $Target

$env:GITHUB_REPO = $repoSlug
$env:GITHUB_REPOSITORY = $repoSlug
$env:AGRI_ENV_FILE = $envFile
$null = Ensure-GitHubToken

$env:LOCAL_DRY_RUN = "false"
$env:MAINTENANCE_TASK = "rebuild_date"
$env:FORCE_REPORT_DATE = $ReportDate
$env:MAINTENANCE_SEND_KAKAO = $(if ($SendKakao) { "true" } else { "false" })
$env:MAX_PER_SECTION = [string]$MaxPerSection
$env:UX_PATCH_DAYS = [string]$UxPatchDays
$env:WINDOW_MIN_HOURS = "0"
$env:CROSSDAY_DEDUPE_ENABLED = "false"
$env:NAVER_MAX_WORKERS = "1"
$env:NAVER_MIN_INTERVAL_SEC = "0.6"
$env:KAKAO_STATUS_FILE = Join-Path $env:TEMP "agri-news-brief-kakao-local.txt"
$env:PUBLISH_MODE = "github_pages"

if ($DebugReport) {
    $env:DEBUG_REPORT = "1"
    $env:DEBUG_REPORT_WRITE_JSON = "1"
    $env:DEBUG_REPORT_MAX_CANDIDATES = "200"
    $env:DEBUG_REPORT_MAX_REJECTS = "2000"
} else {
    $env:DEBUG_REPORT = "0"
    $env:DEBUG_REPORT_WRITE_JSON = "0"
}

if ($Target -eq "dev") {
    $env:BUILD_TAG = "local-dev-$($ReportDate -replace '-', '')"
    $env:GH_CONTENT_REF = "dev"
    $env:GH_CONTENT_BRANCH = "codex/dev-preview"
    $env:FORCE_RUN_ANYDAY = "true"

    $env:PAGES_BRANCH = "codex/dev-preview"
    $env:PAGES_FILE_PATH = "docs/dev/index.html"
    $env:PAGES_BASE_URL = "https://nh-horti.github.io/agri-news-brief/dev/"
    $env:BRIEF_VIEW_URL = "https://nh-horti.github.io/agri-news-brief/dev/"
    $env:DEV_PREVIEW_ASSET_BASE_URL = "https://raw.githubusercontent.com/$repoSlug/codex/dev-preview/docs/dev"
    $env:DEV_SINGLE_PAGE_MODE = "true"
    $env:DEV_SINGLE_PAGE_PATH = "docs/dev/index.html"
    $env:DEV_SINGLE_PAGE_URL_PATH = "index.html"
} else {
    $env:BUILD_TAG = "local-prod-$($ReportDate -replace '-', '')"
    $env:GH_CONTENT_REF = "main"
    $env:GH_CONTENT_BRANCH = "main"
    $env:FORCE_RUN_ANYDAY = "false"

    $env:PAGES_BRANCH = "main"
    $env:PAGES_FILE_PATH = "docs/index.html"
    $env:BRIEF_VIEW_URL = "https://nh-horti.github.io/agri-news-brief/"
    $env:PAGES_BASE_URL = ""
    $env:DEV_PREVIEW_ASSET_BASE_URL = ""
    $env:DEV_SINGLE_PAGE_MODE = "false"
    $env:DEV_SINGLE_PAGE_PATH = ""
    $env:DEV_SINGLE_PAGE_URL_PATH = ""
}

Push-Location $repoRoot
try {
    & $pythonCmd main.py
    if ($envFile) {
        Write-Host "[local-rebuild] env file: $envFile"
    }
    Write-Host "[local-rebuild] target: $Target  date: $ReportDate"
}
finally {
    Pop-Location
}
