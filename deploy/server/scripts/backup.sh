#!/usr/bin/env bash
# Sao lưu PostgreSQL của RetailVision (định dạng custom của pg_dump, có thể khôi phục chọn lọc).
#   bash deploy/server/scripts/backup.sh [thư_mục_đích] [số_ngày_giữ]
# Mặc định: ./backups, giữ 14 ngày. Chạy trên máy chủ đang chạy Compose (project "retailvision").
# Dùng file tạm trong container rồi `docker compose cp` để không phụ thuộc cách shell xử lý dữ liệu nhị phân.
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash trên Windows không được đổi /tmp/... trong lệnh docker

DEST="${1:-./backups}"
KEEP_DAYS="${2:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="retailvision_${STAMP}.dump"
COMPOSE=(docker compose -p retailvision)

mkdir -p "$DEST"
"${COMPOSE[@]}" exec -T postgres pg_dump -U retailvision -d retailvision -Fc -f "/tmp/${FILE}"
"${COMPOSE[@]}" cp "postgres:/tmp/${FILE}" "${DEST}/${FILE}"
"${COMPOSE[@]}" exec -T postgres rm -f "/tmp/${FILE}"

# Kiểm file đọc được: bản sao hỏng thì báo ngay thay vì phát hiện lúc cần khôi phục
if [[ ! -s "${DEST}/${FILE}" ]]; then
  echo "LỖI: file sao lưu rỗng" >&2
  exit 1
fi
"${COMPOSE[@]}" cp "${DEST}/${FILE}" "postgres:/tmp/check.dump"
if ! "${COMPOSE[@]}" exec -T postgres pg_restore --list /tmp/check.dump >/dev/null; then
  echo "LỖI: file sao lưu không đọc được bằng pg_restore" >&2
  exit 1
fi
"${COMPOSE[@]}" exec -T postgres rm -f /tmp/check.dump

find "$DEST" -name 'retailvision_*.dump' -mtime +"$KEEP_DAYS" -delete
echo "Đã sao lưu: ${DEST}/${FILE} ($(wc -c <"${DEST}/${FILE}") byte)"
