# ADR-0001: Hợp nhất quyết định kỹ thuật trước khi lập trình

- **Trạng thái:** Đã chốt. Riêng D3 cần bài thử xác nhận ở giai đoạn 9 của checklist; nếu không đạt thì quay lại phương án outbox (mục "Điều kiện xem xét lại").
- **Ngày:** 2026-10-17
- **Phạm vi:** edge | backend | firmware | frontend | contracts | deploy

## Bối cảnh

PRD, `TrienKhai.md`, `implementation-checklist.md` và `personal-project-roadmap.md` được viết ở các thời điểm khác nhau và mâu thuẫn ở nhiều điểm: firmware (Arduino/PubSubClient hay ESP-IDF), xác thực (JWT hai vai trò hay session một admin), cơ chế bù dữ liệu (spool JSONL, SQLite outbox hay storage ACK), cây topic MQTT, ESP32 nhận `state` hay `commands`, lược đồ bảng, ngưỡng sai số (10% hay 5%) và việc có còi hay không. Viết code theo một tài liệu sẽ lệch tài liệu khác.

Ràng buộc: quỹ thời gian khoảng 96–120 giờ; đồ án thuộc môn Hệ thống nhúng IoT nên trọng tâm chấm là edge, firmware và độ tin cậy MQTT; Pi 4 4 GB không có RTC; demo chạy trong LAN có thể không có Internet.

ADR này là **nguồn sự thật duy nhất** cho các điểm dưới đây. Tài liệu khác mâu thuẫn với ADR này thì theo ADR này.

## Quyết định

### D1. Firmware ESP32: Arduino-ESP32 + PubSubClient + ArduinoJson

- Dùng Arduino-ESP32 core 3.x, build bằng PlatformIO (khuyến nghị) hoặc Arduino IDE; thư viện PubSubClient 2.8.x và ArduinoJson 7.x.
- PubSubClient **chỉ publish QoS 0**. Vì vậy độ tin cậy của ACK được bảo đảm ở cấp ứng dụng (D5), không dựa vào QoS.
- Không dùng ESP-IDF thuần ở bản này. Có thể chuyển sang ESP-MQTT trong Arduino core sau MVP nếu cần QoS 1, không đổi contract.

### D2. Xác thực web: Spring Security session, hai vai trò ADMIN/MANAGER

- Đăng nhập bằng HTTP session (cookie `HttpOnly`, `SameSite=Lax`), mật khẩu BCrypt, frontend cùng origin với API (dev proxy của Vite, production qua cùng host).
- CSRF bật cho request ghi (`POST/PUT/DELETE`).
- Hai vai trò ADMIN/MANAGER kiểm ở API bằng `@PreAuthorize`/cấu hình `SecurityFilterChain`, không chỉ ẩn nút trên React.
- **Không dùng JWT** ở bản này. Lát cắt đầu (giai đoạn 6–7) chạy không đăng nhập trong LAN tin cậy; đăng nhập được thêm ở giai đoạn 10.

### D3. Bù dữ liệu khi máy chủ tắt: Mosquitto persistent session + manual ack sau commit

- Mosquitto trên Pi bật `persistence true`; giới hạn hàng đợi bằng `max_queued_messages` và `max_queued_bytes` (giá trị khởi đầu: 100 000 bản tin / 100 MiB, chỉnh sau bài thử).
- Spring kết nối với `cleanSession=false`, client-id cố định `backend01`, subscribe QoS 1 các topic sự kiện. Khi backend offline, broker giữ bản tin QoS 1 cho nó.
- Spring bật Paho `setManualAcks(true)`: xử lý bản tin trong transaction, **commit xong mới gọi `messageArrivedComplete`** (PUBACK). Lỗi DB thì không ack, broker gửi lại.
- DB có khóa unique theo `event_id`; bản tin trùng vẫn được ack sau khi xác định đã lưu.
- **Bỏ** topic `storage/ack`, spool JSONL và SQLite outbox khỏi baseline. Python edge publish tới broker `127.0.0.1` QoS 1; paho giữ in-flight khi broker khởi động lại trong thời gian ngắn.
- Hàng đợi đầy hoặc broker mất dữ liệu: báo trong log broker và trong báo cáo là coverage gap, không xóa im lặng.

### D4. Cây topic MQTT

Namespace `retailvision/v1/{site_id}/{device_id}/...`; giá trị demo `site01`, Pi là `edge01` (camera `cam01` nằm trong payload), ESP32 là `node01`.

| Topic (sau `retailvision/v1/site01/`) | Publisher → Subscriber | QoS / retain | Nội dung |
| --- | --- | --- | --- |
| `edge01/state` | Pi → ESP32, Spring | 0 / false | Snapshot 1 Hz: `session_id`, `seq`, `observed_at`, `state`, `queue_count` hoặc `null`, `alert_id` hoặc `null`, `acked`, `config_version`, `settings_revision` |
| `edge01/events/crossing` | Pi → Spring | 1 / false | Một lượt IN/OUT |
| `edge01/events/alert` | Pi → Spring | 1 / false | Transition `OPEN`/`ACK`/`END` của một alert |
| `edge01/telemetry` | Pi → Spring | 1 / false | Tổng hợp mỗi 60 giây: `valid_seconds`, `queue_avg`, `queue_max`, FPS, tuổi frame |
| `edge01/status` | Pi → Spring | 1 / true | `ONLINE`/`OFFLINE` + Last Will, phiên bản, `clock_synced` |
| `edge01/settings/set` | Spring → Pi | 1 / false | `request_id`, `expected_settings_revision`, bộ ngưỡng mới |
| `edge01/settings/result` | Pi → Spring | 1 / false | `request_id`, `APPLIED`/`REJECTED`, `settings_revision`, `reason` |
| `node01/events/operator-ack` | ESP32 → Pi | 0 / false | `ack_id`, `alert_id`, `device_id` |
| `node01/status` | ESP32 → Pi, Spring | 1 / true | `ONLINE`/`OFFLINE` + Last Will, phiên bản firmware |

Envelope chung cho mọi bản tin sự kiện: `schema_version`, `event_id` (UUID), `site_id`, `device_id`, `session_id`, `seq` (tăng trong session), `occurred_at` (ISO 8601 UTC), `config_version`. JSON dùng `snake_case`. Schema có phiên bản nằm trong `contracts/mqtt/`; bảng chi tiết tại `docs/architecture/mqtt-topics.md`.

Tài khoản MQTT: `edge01`, `node01`, `backend01`, mỗi tài khoản một ACL chỉ cấp các topic ở bảng trên.

### D5. ESP32 nhận trạng thái (`state`), không nhận lệnh

- ESP32 chỉ subscribe `edge01/state`. Màu LED/còi suy ra từ `state` + `acked`. Bản tin 1 Hz đồng thời là heartbeat: không nhận state hợp lệ trong 5 giây (đo bằng `millis()` của node) → UNKNOWN.
- Bấm nút khi `state=OVERLOAD` và `acked=false`: tạo `ack_id` mới, publish `operator-ack`, **gửi lại cùng `ack_id` mỗi 1 giây** cho đến khi state báo `acked=true`, `alert_id` đổi, hoặc quá 10 lần.
- Pi là bên quyết định: chỉ chấp nhận ACK có `alert_id` trùng alert đang mở; ACK lặp bị bỏ qua; chấp nhận lần đầu thì đặt `acked=true` và phát transition `ACK` (kèm `ack_id`, `device_id`) lên `events/alert`.
- Spring **không** subscribe topic ACK của node; lịch sử ACK lấy từ transition `ACK` của Pi.
- Bỏ topic `commands/alert`. Vì luôn có state mới đè lên, bản tin cũ sau reconnect không bật lại còi.

### D6. Vòng đời cảnh báo và lược đồ DB baseline

- Mỗi lần quá tải có một `alert_id`. Mỗi transition (`OPEN`, `ACK`, `END`) có `event_id` riêng. `END` có `reason`: `NORMALIZED`, `INTERRUPTED` (mất camera/analysis), `CONFIG_CHANGED`.
- ACK không đóng cảnh báo.
- Bảng Flyway, thêm dần theo giai đoạn (không tạo trước toàn bộ):

| Migration | Bảng |
| --- | --- |
| `V001__crossing.sql` | `edge_session`, `crossing_event` (unique `event_id`, index `occurred_at`) |
| `V002__alerts.sql` | `alert_event` (một dòng mỗi `alert_id`: `opened_at`, `acked_at`, `ack_device_id`, `ended_at`, `end_reason`), `alert_transition` (unique `event_id`) |
| `V003__monitoring.sql` | `telemetry_minute` (unique `session_id` + `seq`), `device_status` |
| `V004__auth.sql` | `app_user` (role ADMIN/MANAGER, BCrypt) |
| `V005__settings.sql` | `settings_revision` (`request_id` unique, trạng thái PENDING/APPLIED/REJECTED) |

- Mọi bảng sự kiện có `occurred_at` (đồng hồ Pi, UTC) và `server_received_at` (đồng hồ server).
- Coverage tính từ `telemetry_minute.valid_seconds`; phút không có bản ghi là gap, không phải 0 khách. Không lưu queue sample 1 Hz.

### D7. Đồng bộ thời gian

- Pi 4 không có RTC. Máy chủ LAN chạy dịch vụ NTP (Windows Time hoặc chrony); Pi chạy `chrony` trỏ về máy chủ LAN, sau đó về pool Internet nếu có.
- Edge đọc trạng thái đồng bộ và gửi `clock_synced` trong `status`. Session bắt đầu khi đồng hồ chưa đồng bộ thì báo cáo đánh dấu, dùng `server_received_at` để đối chiếu.
- Timer nghiệp vụ (dwell, hold, stale) vẫn dùng clock đơn điệu, không phụ thuộc NTP.

### D8. Ngưỡng nghiệm thu độ đúng

- Nghiệm thu: sai số tổng tuyệt đối mỗi hướng / tổng lượt thật **≤10%**; queue MAE ≤1 người; precision/recall cảnh báo ≥0,90.
- ≤5% mỗi hướng là **mục tiêu mở rộng**, không phải điều kiện nghiệm thu.
- Do khó tập hợp 5 người giữ 60 giây nhiều lần, precision/recall cảnh báo được đánh giá bằng cách chạy state machine trên chuỗi queue-count đã gán nhãn từ clip thật, kèm một số clip live với profile demo. Báo cáo ghi rõ hai nguồn.

### D9. Phần cứng node: thêm còi, OLED tùy chọn

- BOM thêm một còi chủ động (qua transistor NPN nếu dòng vượt giới hạn GPIO) — kêu khi `OVERLOAD` chưa ACK, tắt sau ACK.
- OLED SSD1306 I2C 0,96" là P1: hiện trạng thái, số người vùng chờ và thời lượng sự kiện.

### D10. Thứ tự triển khai và mức ưu tiên

Làm trước vòng **Camera → Pi → ESP32** (chạy được không cần server), sau đó mới tới backend/frontend:

0. ADR này → 1. Smoke test Pi → 2. Contract → 3. Analytics thuần có unit test → 4. Pipeline edge, replay video, công cụ hiệu chuẩn → 5. MQTT + ESP32 → 6. Backend lát cắt → 7. Frontend lát cắt → 8. Triển khai Pi + benchmark → 9. Phục hồi lỗi → 10. Nghiệp vụ web → 11. Đánh giá → 12. Đóng gói.

Thay đổi mức ưu tiên trong PRD:
- FR-09 (đổi ngưỡng qua web có xác nhận từ Pi) chuyển **P0 → P1**.
- FR-11 (bù dữ liệu) giữ P0, hiện thực theo D3.
- Bổ sung công cụ bắt buộc cho edge: chế độ replay video theo timestamp video, script vẽ vạch/đa giác xuất YAML, publisher giả cho backend.
- Khi thiếu thời gian, cắt theo thứ tự: settings web → CSV → vai trò MANAGER (giữ ADMIN) → NCNN 416 → OLED. Không cắt UNKNOWN, chống trùng, đo trên Pi thật, test offline.

### D11. Lưu ý tracking ở FPS thấp

- Tham số ByteTrack (`track_buffer`, ngưỡng ghép) tính theo **frame**, Ultralytics mặc định coi 30 FPS. Phải chỉnh theo FPS đo được trên Pi (giai đoạn 8).
- Điều kiện "chuyển phía ổn định" khi đếm qua vạch biểu diễn bằng **số lần quan sát liên tiếp** (`min_stable_observations`, mặc định 2), không bằng giây, vì ở 3 FPS 0,3 giây nhỏ hơn khoảng cách giữa hai frame.

## Phương án đã cân nhắc

- **ESP-IDF + ESP-MQTT (roadmap):** hỗ trợ QoS 1, phù hợp portfolio, nhưng tốn thời gian học/cấu hình hơn đáng kể; độ tin cậy ACK đã đạt được ở cấp ứng dụng theo D5.
- **JWT (PRD 0.1):** cần xử lý lưu token, hết hạn, refresh; không đem lại lợi ích trong LAN cùng origin.
- **Một admin, không vai trò (roadmap):** không đáp ứng US-06; thêm role thứ hai trong Spring Security tốn ít công.
- **Spool JSONL + topic `storage/ack` (TrienKhai) / SQLite outbox (roadmap):** đúng về nguyên lý nhưng phải tự viết ghi nguyên tử, replay, xóa theo ACK, xử lý đầy. Broker trên Pi chạy cùng máy với edge nên rủi ro mất giữa edge và broker thấp; persistent session của Mosquitto giải quyết phần mất phía backend với ít code hơn.
- **ESP32 nhận `commands/alert` (roadmap):** cần thêm heartbeat riêng và cơ chế chống lệnh cũ; mô hình state-based đơn giản và tự phục hồi hơn.
- **Lưu queue sample 1 Hz (PRD 0.1):** khoảng 86 400 dòng/ngày nhưng báo cáo chỉ cần mức phút; tổng hợp phút trên Pi đủ cho coverage và queue trung bình/lớn nhất.

## Hệ quả

- PRD nâng lên 0.2; `TrienKhai.md`, `implementation-checklist.md` sửa theo ADR này. `personal-project-roadmap.md` giữ làm nhật ký và mốc thời gian; phần mâu thuẫn (ESP-IDF, SQLite outbox, một admin, `commands/alert`, bảng DB, ≤5%) được thay bởi ADR này.
- Backend phải xử lý bản tin MQTT đồng bộ trong callback (hoặc hàng đợi có ack thủ công) để bảo đảm commit trước PUBACK.
- Ít code edge hơn (không có module spool), nhưng phụ thuộc cấu hình Mosquitto; cấu hình phải được commit mẫu trong `deploy/pi/mosquitto/`.
- Phải chuẩn bị NTP trên máy chủ LAN trước buổi thử offline.

### Điều kiện xem xét lại

- **D3:** bài thử giai đoạn 9 (tắt backend 5 phút, phát sự kiện, khởi động lại cả broker trong lúc có hàng đợi) mất hoặc nhân đôi dữ liệu → bổ sung SQLite outbox trên edge kèm topic `storage/ack`, viết ADR mới.
- **D1:** ACK mất vượt mức chấp nhận dù có gửi lại → chuyển sang ESP-MQTT.
- **D8:** giảng viên yêu cầu ngưỡng khác → cập nhật ADR và PRD cùng lúc.
