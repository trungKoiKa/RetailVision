#!/usr/bin/env bash
# Cài edge lên Raspberry Pi OS: tạo người dùng, venv, dịch vụ systemd.
# Chạy từ thư mục gốc repo đã clone về Pi:  sudo bash deploy/pi/scripts/install_edge.sh
# Chưa kiểm trên Pi thật: nếu một bước lỗi, dừng lại và gửi log thay vì sửa tay nhiều chỗ.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Cần chạy bằng sudo." >&2
  exit 1
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST=/opt/retailvision
CONF=/etc/retailvision

echo "== Người dùng rv và thư mục"
id rv >/dev/null 2>&1 || useradd --system --home-dir "$DEST" --shell /usr/sbin/nologin rv
usermod -aG video rv
mkdir -p "$DEST" "$CONF"

echo "== Chép mã nguồn tới $DEST"
mkdir -p "$DEST/edge" "$DEST/configs" "$DEST/models"
cp -r "$REPO/edge/retailvision" "$REPO/edge/requirements.txt" "$DEST/edge/"
cp -r "$REPO/configs/." "$DEST/configs/"

echo "== Môi trường Python (mất vài phút)"
python3 -m venv "$DEST/edge/.venv"
"$DEST/edge/.venv/bin/pip" install --upgrade pip
"$DEST/edge/.venv/bin/pip" install -r "$DEST/edge/requirements.txt"

echo "== Cấu hình (không ghi đè nếu đã có)"
[[ -f $CONF/edge.yaml ]] || cp "$REPO/configs/examples/site01-camera.yaml" "$CONF/edge.yaml"
if [[ ! -f $CONF/edge.env ]]; then
  cp "$REPO/deploy/pi/edge.env.example" "$CONF/edge.env"
  echo "   -> Sửa mật khẩu trong $CONF/edge.env"
fi
chown -R root:rv "$CONF"
chmod 750 "$CONF"
chmod 640 "$CONF/edge.yaml"
chmod 640 "$CONF/edge.env"
chown -R rv:rv "$DEST"

echo "== Dịch vụ systemd"
cp "$REPO/deploy/pi/systemd/retail-edge.service" /etc/systemd/system/retail-edge.service
systemctl daemon-reload
systemctl enable retail-edge.service

cat <<EOF

Xong. Còn lại:
  1. Đặt model NCNN vào $DEST/models (xem deploy/pi/README.md) và sửa đường dẫn trong $CONF/edge.yaml.
  2. Vẽ lại vạch/vùng chờ cho đúng camera, đặt mật khẩu MQTT trong $CONF/edge.env.
  3. sudo systemctl start retail-edge && journalctl -u retail-edge -f
EOF
