#!/usr/bin/env bash
# Khôi phục bản sao lưu PostgreSQL.
#   bash deploy/server/scripts/restore.sh <file.dump> [--target-db <tên>] [--force]
#
# Mặc định khôi phục vào một CSDL MỚI tên "retailvision_restore" để kiểm tra bản sao lưu mà không đụng dữ liệu đang chạy.
# Muốn ghi đè CSDL đang dùng ("retailvision") phải thêm --force VÀ dừng backend trước:
#   docker compose -p retailvision stop backend web
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash trên Windows không được đổi /tmp/... trong lệnh docker

FILE=""
TARGET="retailvision_restore"
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-db) TARGET="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -*) echo "Tùy chọn lạ: $1" >&2; exit 2 ;;
    *) FILE="$1"; shift ;;
  esac
done
[[ -n "$FILE" && -s "$FILE" ]] || { echo "Cần file sao lưu hợp lệ." >&2; exit 2; }
[[ "$TARGET" =~ ^[a-z0-9_]+$ ]] || { echo "Tên CSDL chỉ gồm a-z, 0-9, _" >&2; exit 2; }
if [[ "$TARGET" == "retailvision" && $FORCE -ne 1 ]]; then
  echo "Từ chối ghi đè CSDL đang dùng 'retailvision' khi thiếu --force." >&2
  exit 2
fi
COMPOSE=(docker compose -p retailvision)

"${COMPOSE[@]}" cp "$FILE" postgres:/tmp/restore.dump
if [[ "$TARGET" != "retailvision" ]]; then
  "${COMPOSE[@]}" exec -T postgres dropdb -U retailvision --if-exists "$TARGET"
  "${COMPOSE[@]}" exec -T postgres createdb -U retailvision "$TARGET"
  "${COMPOSE[@]}" exec -T postgres pg_restore -U retailvision -d "$TARGET" --no-owner /tmp/restore.dump
else
  "${COMPOSE[@]}" exec -T postgres pg_restore -U retailvision -d retailvision --clean --if-exists --no-owner /tmp/restore.dump
fi
"${COMPOSE[@]}" exec -T postgres rm -f /tmp/restore.dump
echo "Đã khôi phục vào CSDL '${TARGET}'."
