$ErrorActionPreference = "Stop"

Write-Host "[hooks] configuring core.hooksPath=.githooks"
git config core.hooksPath .githooks

Write-Host "[hooks] done"
