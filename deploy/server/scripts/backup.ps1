# Sao lưu PostgreSQL của RetailVision trên máy chủ Windows (cùng quy trình với backup.sh).
#   powershell -File deploy\server\scripts\backup.ps1 [-Dest .\backups] [-KeepDays 14]
param(
    [string]$Dest = ".\backups",
    [int]$KeepDays = 14
)
$ErrorActionPreference = "Stop"

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$file = "retailvision_$stamp.dump"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$target = Join-Path (Resolve-Path $Dest) $file

function Compose { docker compose -p retailvision @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $args thất bại" } }

Compose exec -T postgres pg_dump -U retailvision -d retailvision -Fc -f "/tmp/$file"
Compose cp "postgres:/tmp/$file" $target
Compose exec -T postgres rm -f "/tmp/$file"

if (-not (Test-Path $target) -or (Get-Item $target).Length -eq 0) { throw "File sao lưu rỗng" }
Compose cp $target "postgres:/tmp/check.dump"
Compose exec -T postgres pg_restore --list /tmp/check.dump | Out-Null
Compose exec -T postgres rm -f /tmp/check.dump

Get-ChildItem $Dest -Filter "retailvision_*.dump" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } | Remove-Item -Force
Write-Host "Đã sao lưu: $target ($((Get-Item $target).Length) byte)"
