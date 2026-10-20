# ESP32 retail alert

Firmware nhận `state` của Pi qua MQTT, bật LED/còi theo [docs/2-design.md](../../docs/2-design.md) mục 2.7, và gửi `operator-ack` khi nhân viên nhấn nút. PlatformIO + Arduino-ESP32 + PubSubClient + ArduinoJson (ADR-0001).

**Trạng thái:** logic thuần đã có test chạy trên máy (25 test). Phần cứng/mạng mới được biên dịch, chưa nạp lên ESP32 thật và chưa thử với broker.

## Đấu nối (GPIO gợi ý, đổi trong `include/config.h`)

| Chức năng | GPIO | Đấu |
| --- | --- | --- |
| LED đỏ / xanh / vàng | 25 / 26 / 27 | GPIO → 330 Ω → LED (anode) → GND |
| Còi | 14 | GPIO → 1 kΩ → base NPN (S8050/2N2222); còi giữa 5 V và collector; emitter → GND |
| Nút ACK | 33 | `INPUT_PULLUP`, một chân nút nối GND |

Tránh GPIO 0/2/12/15 (strapping) và 34–39 (chỉ vào). Mức HIGH = LED sáng / còi kêu.

## Bảng trạng thái

| Điều kiện | Đỏ | Xanh | Vàng | Còi |
| --- | --- | --- | --- | --- |
| Chưa có state / quá 5 giây / UNKNOWN | Tắt | Tắt | Nháy | Tắt |
| NORMAL | Tắt | Sáng | Tắt | Tắt |
| OVERLOAD, `acked=false` | Nháy | Tắt | Tắt | Kêu |
| OVERLOAD, `acked=true` | Sáng | Tắt | Tắt | Tắt |

## Cấu trúc

```text
platformio.ini
include/config.h            chân, thời gian, định danh
include/secrets.example.h   mẫu Wi-Fi/MQTT (sao chép thành secrets.h, không commit)
lib/alert_core/             logic thuần, không phụ thuộc Arduino
  alert_model   parse state, timeout 5 s, payload sai không thành NORMAL
  outputs       trạng thái -> LED/còi, nháy và nhịp còi
  debounce      một lần phát mỗi lần nhấn
  ack_sender    gửi lặp cùng ack_id mỗi 1 s, tối đa 10 lần
  payloads      UUID v4, ISO 8601 UTC, JSON operator-ack và status
src/main.cpp                loop(): đọc nút, điều khiển chân (không chặn)
src/network.cpp             Wi-Fi + MQTT ở task riêng trên core 0
test/test_core/             Unity, chạy trên máy
```

Mạng chạy ở task riêng vì `connect()` có thể chặn vài giây khi mất broker; nếu để trong `loop()` thì LED và nút bị đứng.

## Cài và build

```bash
pip install platformio
cd firmware/retail_alert
cp include/secrets.example.h include/secrets.h    # rồi sửa Wi-Fi, IP broker, mật khẩu node01
pio test -e native      # test logic, cần g++ trong PATH
pio run                 # biên dịch
pio run -t upload       # nạp
pio device monitor      # xem log, 115200
```

Trên Windows, `g++` của MSYS2 (thư mục `ucrt64\bin`) chạy được từ PowerShell; trong shell kiểu Bash nó báo lỗi im lặng, nên chạy `pio test -e native` từ PowerShell.

## Giới hạn đã biết

- PubSubClient chỉ publish QoS 0: `operator-ack` đúng QoS 0 theo contract, nhưng `status` ONLINE gửi QoS 0 (contract ghi QoS 1). Last Will vẫn QoS 1.
- ESP32 không có giờ UTC nếu LAN không có máy chủ NTP (`NTP_SERVER` trong `secrets.h`). Khi đó `status` ghi `occurred_at` = `1970-01-01T00:00:00.000Z` và `clock_synced=false`. Backend không nên dùng `occurred_at` của `node01/status` khi `clock_synced=false`.
