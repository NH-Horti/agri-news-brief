param(
    [string]$RedirectUri = "",
    [string]$Code = "",
    [string[]]$EnvFile = @(".env.local", ".env.final.local", ".env.dev.local"),
    [string]$Repo = "NH-Horti/agri-news-brief",
    [string]$Scope = "talk_message",
    [switch]$OpenBrowser,
    [switch]$PromptLogin,
    [switch]$UpdateEnvFiles,
    [switch]$UpdateGitHubSecret
)

$ErrorActionPreference = "Stop"

function Select-FirstText {
    param([object[]]$Values)

    foreach ($value in $Values) {
        if ($null -eq $value) {
            continue
        }
        $text = ([string]$value).Trim()
        if ($text) {
            return $text
        }
    }
    return ""
}

function Read-EnvFiles {
    param([string[]]$Paths)

    $map = @{}
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }
        Get-Content -LiteralPath $path | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
                return
            }
            $idx = $line.IndexOf("=")
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
            if (-not $map.ContainsKey($key)) {
                $map[$key] = $val
            }
        }
    }
    return $map
}

function Set-EnvFileValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = @(Get-Content -LiteralPath $Path)
    }

    $updated = $false
    $next = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            "$Key=$Value"
            $updated = $true
        } else {
            $line
        }
    }
    if (-not $updated) {
        $next += "$Key=$Value"
    }
    Set-Content -LiteralPath $Path -Value $next -Encoding UTF8
}

function Get-CodeFromInput {
    param([string]$InputValue)

    $value = Select-FirstText @($InputValue)
    if (-not $value) {
        return ""
    }
    if ($value -match "^https?://") {
        $uri = [Uri]$value
        $queryText = $uri.Query.TrimStart("?")
        foreach ($part in ($queryText -split "&")) {
            if (-not $part) {
                continue
            }
            $pieces = $part -split "=", 2
            $name = [Uri]::UnescapeDataString($pieces[0])
            if ($name -eq "code") {
                if ($pieces.Count -lt 2) {
                    return ""
                }
                return [Uri]::UnescapeDataString($pieces[1])
            }
        }
        return ""
    }
    return $value
}

$envMap = Read-EnvFiles -Paths $EnvFile

$restKey = Select-FirstText @($env:KAKAO_REST_API_KEY, $envMap["KAKAO_REST_API_KEY"])
$clientSecret = Select-FirstText @($env:KAKAO_CLIENT_SECRET, $envMap["KAKAO_CLIENT_SECRET"])
if (-not $RedirectUri) {
    $RedirectUri = Select-FirstText @($env:KAKAO_REDIRECT_URI, $envMap["KAKAO_REDIRECT_URI"])
}

if (-not $restKey) {
    throw "KAKAO_REST_API_KEY was not found in environment or env files."
}
if (-not $RedirectUri) {
    throw "RedirectUri is required. It must exactly match a redirect URI registered in Kakao Developers."
}

$authParams = @{
    response_type = "code"
    client_id = $restKey
    redirect_uri = $RedirectUri
}
if ($Scope) {
    $authParams["scope"] = $Scope
}
if ($PromptLogin) {
    $authParams["prompt"] = "login"
}

$authQuery = ($authParams.GetEnumerator() | ForEach-Object {
    "$([Uri]::EscapeDataString($_.Key))=$([Uri]::EscapeDataString([string]$_.Value))"
}) -join "&"
$authUrl = "https://kauth.kakao.com/oauth/authorize?$authQuery"

$authCode = Get-CodeFromInput -InputValue $Code
if (-not $authCode) {
    Write-Host "Open this Kakao authorization URL, approve, then copy the redirected URL or the code parameter:"
    Write-Host $authUrl
    if ($OpenBrowser) {
        Start-Process $authUrl
    }
    exit 2
}

$body = @{
    grant_type = "authorization_code"
    client_id = $restKey
    redirect_uri = $RedirectUri
    code = $authCode
}
if ($clientSecret) {
    $body["client_secret"] = $clientSecret
}

try {
    $resp = Invoke-RestMethod `
        -Uri "https://kauth.kakao.com/oauth/token" `
        -Method Post `
        -Body $body `
        -ContentType "application/x-www-form-urlencoded;charset=utf-8" `
        -TimeoutSec 30
} catch {
    throw "Kakao token issuance failed. $($_.Exception.Message)"
}

$refreshToken = Select-FirstText @($resp.refresh_token)
if (-not $refreshToken) {
    throw "Kakao token response did not include refresh_token."
}

if ($UpdateEnvFiles) {
    foreach ($path in $EnvFile) {
        if (Test-Path -LiteralPath $path) {
            Set-EnvFileValue -Path $path -Key "KAKAO_REFRESH_TOKEN" -Value $refreshToken
            Write-Host "Updated $path"
        }
    }
}

if ($UpdateGitHubSecret) {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) {
        throw "GitHub CLI (gh) was not found."
    }
    $refreshToken | gh secret set KAKAO_REFRESH_TOKEN --repo $Repo
    if ($LASTEXITCODE -ne 0) {
        throw "gh secret set failed."
    }
    Write-Host "Updated GitHub secret KAKAO_REFRESH_TOKEN in $Repo"
}

Write-Host "Kakao refresh token was reissued successfully. Token value was not printed."
