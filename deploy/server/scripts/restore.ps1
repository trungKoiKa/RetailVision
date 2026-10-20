# Khôi phục bản sao lưu PostgreSQL trên máy chủ Windows (cùng quy tắc với restore.sh).
#   powershell -File deploy\server\scripts\restore.ps1 -File .\backups\retailvision_xxx.dump [-TargetDb retailvision_restore] [-Force]
# Mặc định khôi phục vào CSDL mới 'retailvision_restore'. Ghi đè 'retailvision' cần -Force và dừng backend trước.
param(
    [Parameter(Mandatory = $true)][string]$File,
    [string]$TargetDb = "retailvision_restore",
    [switch]$Force
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $File) -or (Get-Item $File).Length -eq 0) { throw "Cần file sao lưu hợp lệ." }
if ($TargetDb -notmatch '^[a-z0-9_]+$') { throw "Tên CSDL chỉ gồm a-z, 0-9, _" }
if ($TargetDb -eq "retailvision" -and -not $Force) { throw "Từ chối ghi đè CSDL đang dùng 'retailvision' khi thiếu -Force." }

function Compose { docker compose -p retailvision @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $args thất bại" } }

Compose cp (Resolve-Path $File) "postgres:/tmp/restore.dump"
if ($TargetDb -ne "retailvision") {
    Compose exec -T postgres dropdb -U retailvision --if-exists $TargetDb
    Compose exec -T postgres createdb -U retailvision $TargetDb
    Compose exec -T postgres pg_restore -U retailvision -d $TargetDb --no-owner /tmp/restore.dump
} else {
    Compose exec -T postgres pg_restore -U retailvision -d retailvision --clean --if-exists --no-owner /tmp/restore.dump
}
Compose exec -T postgres rm -f /tmp/restore.dump
Write-Host "Đã khôi phục vào CSDL '$TargetDb'."
