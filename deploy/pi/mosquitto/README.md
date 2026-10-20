# Mosquitto trên Pi

Cấu hình broker (`retailvision.conf`) và ACL mẫu (`acl.example`) theo [contracts/mqtt/README.md](../../../contracts/mqtt/README.md).

**Trạng thái kiểm chứng:** `acl.example` đã được thử bằng `deploy/pi/scripts/check_acl.py` với Mosquitto 2.1.2 trên Windows (9/9 ca đúng). Chưa chạy trên Raspberry Pi OS; các bước cài dưới đây chưa được kiểm trên Pi.

## Cài (chưa kiểm trên Pi)

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo cp deploy/pi/mosquitto/retailvision.conf /etc/mosquitto/conf.d/
sudo cp deploy/pi/mosquitto/acl.example /etc/mosquitto/acl     # đổi site01 nếu cần
sudo mosquitto_passwd -c /etc/mosquitto/passwd edge01          # hỏi mật khẩu
sudo mosquitto_passwd /etc/mosquitto/passwd node01
sudo mosquitto_passwd /etc/mosquitto/passwd backend01
sudo systemctl restart mosquitto && systemctl status mosquitto
```

Mật khẩu chỉ nhập khi chạy lệnh, không ghi vào repo. Dùng cùng mật khẩu đó cho `RV_MQTT_PASS` của edge, `secrets.h` của ESP32 và biến môi trường của backend.

## Kiểm ACL

```bash
RV_MQTT_PASS=... RV_MQTT_NODE_PASS=... RV_MQTT_BACKEND_PASS=... python deploy/pi/scripts/check_acl.py --site site01
```

Mọi dòng phải là `OK` và kết thúc bằng `PASS`.
