# ADR-0001: Hợp nhất quyết định kỹ thuật trước khi lập trình

- **Trạng thái:** Đã chốt; D3 cần xác nhận bằng bài thử T25.
- **Ngày:** 2026-10-17

## Bối cảnh

Các bản kế hoạch trước mâu thuẫn nhau về firmware, xác thực, cơ chế bù dữ liệu, topic MQTT, lược đồ DB và ngưỡng nghiệm thu. Ràng buộc: ~110 giờ công, đồ án môn Hệ thống nhúng IoT (trọng tâm là edge, firmware, độ tin cậy MQTT), Pi 4 không có RTC, demo trong LAN có thể không có Internet.

Chi tiết hiện thực nằm ở [2-design.md](../2-design.md); ADR này chỉ ghi lựa chọn và lý do.

## Quyết định

| # | Chọn | Thay cho | Lý do |
| --- | --- | --- | --- |
| D1 | Firmware Arduino-ESP32 + PubSubClient + ArduinoJson (PlatformIO) | ESP-IDF + ESP-MQTT | Nhanh hơn nhiều cho người làm một mình; PubSubClient chỉ publish QoS 0 nhưng ACK được gửi lại ở cấp ứng dụng (D5) |
| D2 | Spring Security session, hai vai trò ADMIN/MANAGER | JWT; hoặc một admin | Cùng origin trong LAN nên JWT không có lợi; thêm role thứ hai rẻ và đáp ứng phân quyền |
| D3 | Mosquitto persistence + Spring `cleanSession=false` + ack thủ công sau commit | Spool JSONL + topic `storage/ack`; SQLite outbox | Broker chạy cùng máy với edge nên rủi ro mất giữa hai bên thấp; persistent session giải quyết phần backend offline với ít code |
| D4 | Namespace `retailvision/v1/{site}/{device}/...` | `retail/site01/cam01/...` | Có phiên bản, phân quyền ACL theo device |
| D5 | ESP32 nghe `state` 1 Hz, Pi quyết định ACK | ESP32 nhận `commands/alert` | `state` vừa là heartbeat vừa tự đè bản tin cũ, không cần cơ chế chống lệnh cũ |
| D6 | Bảng: crossing, alert + transition, telemetry phút, device, user, settings; thêm dần theo giai đoạn | Lưu queue sample 1 Hz; tạo trước toàn bộ schema | Báo cáo chỉ cần mức phút; migration nhỏ dễ kiểm |
| D7 | chrony trên Pi lấy giờ từ NTP máy chủ LAN; lưu thêm `server_received_at` | Dựa vào Internet | Pi 4 không có RTC, offline sẽ sai giờ |
| D8 | Nghiệm thu sai số ≤10% mỗi hướng; ≤5% là mục tiêu mở rộng | ≤5% bắt buộc | Thống nhất với PRD gốc |
| D9 | Thêm còi; OLED là P1 | Chỉ LED | Tăng phần nhúng với chi phí thấp |
| D10 | Làm vòng Camera → Pi → ESP32 trước, backend/frontend sau; đổi ngưỡng qua web xuống P1 | Lát cắt backend trước | Nếu thiếu thời gian vẫn còn hệ thống nhúng hoàn chỉnh |
| D11 | Điều kiện ổn định khi đếm vạch tính theo số lần quan sát; tracker chỉnh theo FPS thật | Tính theo giây, tham số mặc định 30 FPS | Ở ~3 FPS, 0,3 giây nhỏ hơn khoảng cách hai frame |

## Hệ quả

- Edge không có module spool; phải commit mẫu cấu hình Mosquitto.
- Backend xử lý bản tin đồng bộ để bảo đảm commit trước ack.
- Cần dựng NTP trên máy chủ LAN trước khi thử offline.

## Điều kiện xem xét lại

- **D3:** T25 (tắt backend 5 phút, restart broker khi còn hàng đợi) mất hoặc nhân đôi dữ liệu → thêm SQLite outbox trên edge, viết ADR mới.
- **D1:** ACK mất dù đã gửi lại → chuyển sang ESP-MQTT trong Arduino core.
- **D8:** giảng viên yêu cầu ngưỡng khác → sửa ADR và `1-requirements.md` cùng lúc.
