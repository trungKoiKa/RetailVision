# RetailVision — Roadmap project cá nhân IoT / Computer Vision

Ngày lập: 2026-10-03. Trạng thái: **kế hoạch, chưa triển khai**.

> **Cập nhật 2026-10-17:** [ADR-0001](decisions/0001-hop-nhat-quyet-dinh-ky-thuat.md) thay thế các điểm sau trong roadmap này: firmware dùng Arduino-ESP32 + PubSubClient (không ESP-IDF); bù dữ liệu bằng Mosquitto persistent session + manual ack (không SQLite outbox/`storage/ack` ở baseline); ESP32 nhận `state` (không `commands/alert`); auth session với hai vai trò ADMIN/MANAGER (không phải một admin); bảng DB theo ADR D6; sai số nghiệm thu ≤10% (≤5% là mục tiêu mở rộng); thứ tự giai đoạn theo [checklist](implementation-checklist.md). Roadmap giữ vai trò mốc thời gian và nhật ký tiến độ.

## 1. Cách sử dụng và mục tiêu

Kế hoạch dành cho RetailVision gốc: đếm lượt vào/ra và giám sát vùng chờ, không chuyển sang hệ thống xâm nhập vùng cấm. Mục tiêu là portfolio ứng tuyển IoT / Computer Vision có thiết bị thật, số liệu đánh giá và hướng dẫn tái hiện.

- Đọc roadmap để hiểu toàn bộ mục tiêu và kiến trúc.
- Làm từng phần trong [implementation-checklist.md](implementation-checklist.md).
- Mỗi buổi chọn một task 1–3 giờ; ghi kết quả và blocker.
- Chỉ sang phần sau khi phần trước đạt gate bằng kiểm thử, không phải vì tạo đủ thư mục.
- Tận dụng skeleton hiện tại; không tạo lại cây thư mục hoặc hàng loạt class rỗng.

| Mốc tham khảo | Kết quả |
|---|---|
| Cuối tuần 3 | MVP: camera thật, crossing, queue, ESP32 và web tối thiểu |
| Cuối tuần 12 | Prototype: đánh giá, phục hồi lỗi, đóng gói và hồ sơ ứng tuyển |

Quỹ thời gian 8–10 giờ/tuần, tổng 96–120 giờ. Ba tuần MVP cần khoảng 10 giờ/tuần và vẫn rất căng với người mới. Ưu tiên **hoàn thành từng phần**; nếu chậm, điều chỉnh lịch, không bỏ kiểm thử hoặc gọi dữ liệu giả là demo camera thật. Prototype không đồng nghĩa sản phẩm thương mại đã kiểm chứng tại mọi cửa hàng.

### Phạm vi

- Pi 4 RAM 4 GB, một ESP32, một camera USB UVC cố định, khu vực dàn dựng tại nhà.
- Một camera nhìn cả cửa và vùng chờ, một detector/tracker dùng chung.
- Pi xử lý ảnh; ESP32 cảnh báo/ACK; Spring/PostgreSQL/React hỗ trợ lưu và quan sát.
- Không làm: nhận diện danh tính/khuôn mặt, nhiều camera/cửa hàng, POS, mobile, cloud/Kubernetes, OTA, heatmap, nhiều vai trò, huấn luyện từ đầu, lưu video liên tục.

IN/OUT là **số lượt vượt vạch**, không phải khách duy nhất hoặc occupancy chính xác. Người ngoài vạch/ROI không tự làm bộ đếm tăng/giảm.

### Quan hệ với tài liệu hiện có

Roadmap này thay đổi thứ tự và phạm vi triển khai cá nhân, không xác nhận tính năng đã tồn tại. ESP-IDF, session auth, SQLite outbox và tên topic/API là thiết kế đề xuất. Ở phần chốt contract, đối chiếu PRD/TrienKhai, ghi ADR và đồng bộ quyết định trước khi viết integration. Không dùng song song hai đặc tả cho cùng một thông điệp. Các tài liệu còn lại chưa được viết lại trong lần lưu kế hoạch này.

## 2. Kiến trúc, công nghệ và hợp đồng

```text
Camera → Pi: capture → detector → tracker dùng chung
                      ├─ crossing analytics
                      └─ queue / alert analytics
                                  ↓
                             Mosquitto trên Pi
                             ├─ ESP32: LED / còi / nút ACK
                             └─ Spring Boot trên máy LAN
                                  → PostgreSQL → REST → React
```

Pi/ESP32 tiếp tục hoạt động khi backend tắt. React không truy cập MQTT/database. MVP chưa bảo đảm khôi phục mọi sự kiện khi backend offline; bổ sung outbox sau.

### 2.1. Baseline

| Thành phần | Lựa chọn |
|---|---|
| Edge | Python, OpenCV, YOLOv8n pretrained class person, ByteTrack |
| Tối ưu Pi | NCNN sau khi bản tham chiếu chạy được |
| Firmware | ESP-IDF dòng 5.5, ESP-MQTT, cJSON |
| Backend | JDK 21, Spring Boot 3.5.16, Maven Wrapper |
| Database | PostgreSQL 17, Flyway + module PostgreSQL |
| Frontend | Node 24 LTS, React 19.2, Vite 7, TypeScript |
| Messaging | Mosquitto, MQTT 3.1.1 |
| Test | pytest, JUnit, Testcontainers, Vitest |

JDK 21 nằm trong phạm vi Spring Boot 3.5; Vite 7 yêu cầu Node 20.19+ hoặc 22.12+, nên Node 24 đáp ứng nền tảng. Tham khảo [Spring Boot](https://docs.spring.io/spring-boot/3.5/system-requirements.html), [Vite 7](https://vite.dev/blog/announcing-vite7).

Pi OS/Python cần smoke test:

1. Thử Pi OS Lite 64-bit Trixie/Python 3.13 trong `edge/.venv`.
2. Giới hạn gỡ lỗi dependency ban đầu trong 2 giờ.
3. Nếu không chạy được pipeline, dùng thẻ khác với Bookworm 64-bit và Python đi kèm OS. Không ghi đè thẻ hiện tại khi chưa sao lưu/xác nhận.
4. Ghi phiên bản chạy thật và khóa dependencies sau test.

Ultralytics đã kiểm thử Pi 4/5 với Bookworm và khuyến nghị NCNN cho ARM; không coi đó là chứng nhận stack Trixie/Python 3.13 hoặc cam kết FPS trên Pi này. Tham khảo [Pi guide](https://docs.ultralytics.com/guides/raspberry-pi), [NCNN](https://docs.ultralytics.com/integrations/ncnn).

Patch version cụ thể được chốt sau smoke test, ghi vào manifest/lockfile. Không build Mosquitto từ source chỉ để khớp patch đề xuất. Firmware dùng [ESP-MQTT](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32/api-reference/protocols/mqtt.html), không trộn Arduino/PubSubClient.

### 2.2. MQTT

Namespace đề xuất: `retailvision/v1/{site_id}/{device_id}/...`. Chốt bảng publisher/subscriber trước code; topic lệnh dùng device ID ESP32 nhận lệnh.

| Topic cuối | Nội dung | QoS / retained |
|---|---|---|
| `events/crossing` | Một lượt IN/OUT | 1 / false |
| `events/alert` | Transition OPEN/ACK/END | 1 / false |
| `state` | Snapshot tối đa 1 lần/giây | 0 / false |
| `status` | ONLINE/OFFLINE + Last Will | 1 / true |
| `commands/alert` | Điều khiển trạng thái ESP32 | 1 / false |
| `events/operator-ack` | Nút xác nhận | 1 / false |
| `acks/storage` | DB đã commit, bổ sung cùng outbox | 1 / false |

Envelope: `schema_version`, `event_id` UUID, `site_id`, `device_id`, `camera_id` khi liên quan camera, `session_id`, `sequence`, `occurred_at` UTC, `config_version`.

- Crossing có `direction`, `track_id`, `line_id`; track không phải danh tính, chỉ có ý nghĩa trong session.
- Alert có `alert_id`, `transition`, `queue_count`, `reason`. Mỗi transition có event ID riêng; alert ID liên kết vòng đời.
- Operator ACK có event ID riêng, alert ID và ID ESP32; edge quyết định ACK hợp lệ rồi phát transition ACK.
- State có count session, queue/state, thời điểm quan sát; UNKNOWN dùng queue null, không dùng 0.
- Lệnh ESP32 có alert ID, trạng thái và thông tin độ mới; bản tin cũ không bật lại còi sau reconnect.

Sequence chỉ so trong cùng session; không sắp UUID để suy ra session mới. Replay session cũ chỉ cập nhật lịch sử, không ghi đè state hiện hành. JSON Schema, ví dụ hợp lệ/sai/trùng và OpenAPI nằm trong `contracts/`.

### 2.3. Analytics và failure semantics

Crossing: bottom-center bbox, vạch hữu hạn có hai đầu mút, deadband và chuyển phía ổn định. Xuất hiện trên vạch chưa tính; rung quanh vạch không tăng nhiều lượt; vào rồi quay ra là IN rồi OUT. Mất track/đổi ID không tự bù lượt.

Queue: polygon chuẩn hóa, dwell trước khi tính; đạt on-count đủ on-hold thì mở cảnh báo, xuống off-count đủ off-hold thì kết thúc. Timer reset khi điều kiện tương ứng không còn đúng. ACK chỉ xác nhận/tắt còi, không xóa quá tải.

| Tham số | Demo | Nghiệp vụ ban đầu |
|---|---|---|
| dwell | 2 giây | 2 giây |
| on-count / on-hold | 2 người / 10 giây | 5 người / 60 giây |
| off-count / off-hold | 1 người / 5 giây | 3 người / 10 giây |

Profile nghiệp vụ là giả định, chưa phải ngưỡng khảo sát tại cửa hàng.

Không có kết quả hợp lệ 3 giây → edge UNKNOWN; ESP32 không nhận trạng thái 5 giây → UNKNOWN. Cảnh báo đang mở END với reason INTERRUPTED khi mất quan sát; phục hồi phải tính lại timer, không nối bằng chứng qua gap.

Dùng monotonic trực tiếp, timestamp video khi replay. Tracker nối tiếp một stream, không khởi tạo lại mỗi frame; tham khảo [Tracking](https://docs.ultralytics.com/modes/track).

### 2.4. Database/REST MVP

Flyway tạo bốn bảng nghiệp vụ: `crossing_event`, `camera_state`, `alert_event`, `operator_ack`. Unique event ID trên event; snapshot lưu freshness. Không lưu ảnh/video trong DB. Dùng `ddl-auto=validate`, migration nhỏ; không tạo toàn bộ schema tương lai.

REST: `GET /api/overview`, `GET /api/alerts?limit=20`, `GET /api/devices`, `GET /api/health`.

Overview tính tổng ngày từ event đã lưu, trả queue/state và freshness. Count session trên Pi dùng chẩn đoán. Trước outbox, web ghi rõ có thể thiếu sự kiện lúc backend offline. Lưu UTC, nhóm ngày theo `Asia/Ho_Chi_Minh`.

MVP không login, chỉ dùng LAN tin cậy, không public Internet; React qua dev proxy. Bản đóng gói thêm session auth và same-origin.

## 3. MVP ba tuần — từng buổi

### Tuần 1 — phần cứng và crossing giả, 10 giờ

**Buổi 1, 3 giờ:** kiểm tra Pi/nguồn/thẻ/tản nhiệt/camera; đọc frame, detection, tracking clip ngắn; ghi version/latency/RAM/nhiệt. Dùng script trong `edge/experiments`, chưa framework nhiều lớp.

**Buổi 2, 3 giờ:** chốt payload; tạo Spring Web/Validation/JPA/PostgreSQL/Flyway và module PostgreSQL; migration, unique ID, MQTT ingestion, overview. Chứng minh crossing giả tới DB/REST. DB có thể chạy container, backend trực tiếp.

**Buổi 3, 3 giờ:** React một trang IN/OUT, queue/state/freshness, alert gần nhất, polling 2 giây. ESP-IDF từ ví dụ Wi-Fi/MQTT, nhận lệnh giả đổi LED. Chưa UI đẹp/login/WebSocket.

**1 giờ:** kiểm tra và ghi hướng dẫn. Gate: Pi chạy model thật, crossing giả lên web, ESP32 nhận lệnh giả.

### Tuần 2 — hai chức năng CV, 10 giờ

**Buổi 1, 3 giờ:** capture frame mới nhất, một detector/tracker class person; log FPS/tuổi frame, YAML vạch/ROI và ảnh minh họa. Khởi đầu input 320, xử lý khoảng 3 FPS để đo, không bảo đảm.

**Buổi 2, 3 giờ:** hình học crossing, state track, deadband, emit một event/lần hợp lệ. Unit test tọa độ: IN, OUT, đứng vạch, đầu mút, quay đầu, hai người.

**Buổi 3, 3 giờ:** point-in-polygon, dwell/hysteresis/hold, UNKNOWN và MQTT state/alert, dùng chung tracking.

**1 giờ:** đối chiếu Pi thật với quan sát. Gate: event thật thay publisher giả, không đổi contract backend/frontend.

### Tuần 3 — ESP32, nghiệm thu, 10 giờ

**Buổi 1, 3 giờ:** NORMAL/OVERLOAD_UNACKED/OVERLOAD_ACKED/UNKNOWN; LED/còi, nút debounce, ACK theo alert, chống bản tin lặp bật lại còi, timeout.

**Buổi 2, 3 giờ:** camera → DB/web; đủ hold → ESP32; ACK không xóa quá tải; count giảm → END; camera mất → UNKNOWN; duplicate crossing không tăng tổng.

**Buổi 3, 3 giờ:** ≥20 IN/20 OUT đi lần lượt; dựng queue hai người, ACK, một người rời ROI, ngắt camera. Lưu ground truth/config/kết quả, quay 2–3 phút.

**1 giờ:** quickstart, lỗi đã biết, release dự kiến `v0.1.0` khi đạt gate.

### Gate MVP

- Hai chức năng chạy trên Pi/camera thật, sai số từng hướng ≤10% trong bài thử trên.
- Dwell/hold đúng, không cảnh báo ngay frame đầu; ESP32/ACK và web thật hoạt động.
- Duplicate không nhân đôi; UNKNOWN khác queue bằng 0; chạy ≥30 phút không crash.
- Chưa cam kết login, reports đầy đủ, settings web, auto-reboot, replay hoặc accuracy ở cửa hàng thật.

## 4. Tuần 4–12 — portfolio, mỗi tuần 8–10 giờ

### Tuần 4 — analytics chắc và code dễ test

Tách capture/inference/tracking khỏi analytics; track type chung, analytics không gọi model. Unit test hình học/dwell/hysteresis/timeout, log session/event/latency không secret. Đầu ra: test không cần camera/YOLO.

### Tuần 5 — dữ liệu đánh giá

≥24 clip: 12 phát triển, 12 test giữ riêng. Tổng hướng tới ≥200 crossing/20 overload; test ≥100 crossing/10 overload và tình huống âm tính. Có nhiều người, hai hướng, nhanh/chậm, dừng vạch, che khuất, ánh sáng, sát ROI, đi ngang ROI, cảnh trống. Ground truth timestamp/hướng/queue sau dwell/alert theo profile. Không cần bbox mọi frame; thêm subset khi phân tích detector. Xin đồng ý người tham gia, không public clip riêng tư; test không dùng chỉnh ngưỡng.

### Tuần 6 — benchmark Pi

So sánh bản tham chiếu/NCNN, input 320/416, resolution/inference interval trên cùng clip. Đo toàn pipeline: FPS, tuổi frame, RAM/nhiệt/throttling, crossing, queue MAE, alert precision/recall. Chọn theo accuracy/tài nguyên, không chỉ FPS. Mục tiêu thử khoảng ≥3 FPS; không đạt thì báo giới hạn, không dùng số liệu laptop như Pi.

### Tuần 7 — outbox và delivery

SQLite outbox trên edge: ghi trước publish → backend commit → storage ACK → đánh dấu đã giao. Reconnect replay thứ tự; duplicate đã lưu vẫn ACK. PUBACK không thay DB ACK; heartbeat không spool. Giới hạn 100 MB, đầy báo rõ không âm thầm xóa chưa giao. Replay không ghi đè state/bật còi từ alert cũ. Gate: backend offline 5 phút rồi bật lại không mất/nhân đôi trong bài thử.

### Tuần 8 — vận hành thiết bị

Reconnect backoff, ACK retry cùng event ID, heartbeat/Last Will; systemd edge; thử reboot Pi/ESP32/broker; GPIO/Wi-Fi/broker config ngoài source, secret không commit. Đầu ra: tự phục hồi sau reboot, có lệnh xem service/log.

### Tuần 9 — auth và báo cáo gọn

Một admin, hash mật khẩu, HTTP session, same-origin, CSRF cho API ghi; không JWT/refresh token/nhiều vai trò. Báo cáo ngày/khoảng thời gian/CSV, alert phân trang, thời gian quá tải/ACK, coverage gap. Migration mới, không sửa migration đã áp dụng. Khoảng thiếu dữ liệu không hiển thị như 0 khách.

### Tuần 10 — settings web

Chỉ dwell/on/off count/hold; ROI/model/camera bằng file. React → backend → `settings/set`; edge → `settings/result`. Request ID/revision và pending/applied/rejected; validate off-count < on-count, thời gian không âm, revision cũ không ghi đè mới, áp dụng nguyên bộ hợp lệ. Đổi settings reset timer và END alert cũ reason CONFIG_CHANGED. Offline không giả applied.

### Tuần 11 — đóng gói và thử lỗi

`deploy/server/compose.yaml` cho DB/backend/frontend cùng origin; Pi systemd. MQTT auth/ACL, DB/broker không public Internet. CI unit/contract/build, Testcontainers integration; fresh clone; soak 2 giờ; thử camera/broker/Wi-Fi/backend/DB/outbox đầy. Backup/restore và thử restore, health check/rollback.

### Tuần 12 — hồ sơ ứng tuyển

README tiếng Anh và bổ sung Việt, kiến trúc, video 3–5 phút, benchmark Pi, giới hạn, quickstart. Ba ADR: NCNN, delivery/idempotency, giới hạn đếm. Simulation cho web/backend khác replay video có nhãn qua CV; simulation không chứng minh accuracy. `v1.0.0` mô tả đúng kết quả; người không có Pi có thể thử replay.

## 5. Kiểm thử và mục tiêu hoàn thành

| Nhóm | Tình huống |
|---|---|
| Crossing | IN/OUT, đứng vạch, quay đầu, đầu mút, nhiều người, mất track |
| Queue | Dwell, đi ngang ROI, hold/hysteresis, UNKNOWN |
| Dữ liệu | Duplicate, sai schema, replay cũ, revision cũ, rollback |
| Thiết bị | Nút dội, ACK lặp/sai alert, Wi-Fi mất, reboot |
| Hệ thống | Camera/backend/DB/broker lỗi, Pi reboot, outbox đầy |
| Báo cáo | Qua nửa đêm, timezone Việt Nam, coverage gap |

Timer test bằng clock giả/timestamp video, không sleep dài.

Mục tiêu test giữ riêng ở tuần 12:

- Crossing sai số tổng từng hướng ≤5%; đối chiếu từng event bằng timestamp/hướng để không che lỗi thừa/thiếu triệt tiêu nhau.
- Queue MAE ≤1 người sau dwell; alert precision/recall ≥90%.
- p95 quyết định edge → LED ≤1 giây LAN, không tính hold. Đồng bộ clock hoặc dùng thiết bị đo phù hợp, không trừ hai clock chưa đồng bộ.
- Backend offline 5 phút không mất/nhân đôi trong thử nghiệm; soak 2 giờ không crash/tăng RAM bất thường; UNKNOWN đúng.

Đây là mục tiêu, chưa phải kết quả. Ghi kết quả thật, cỡ mẫu và giới hạn; không đạt thì phân tích và thu hẹp điều kiện hỗ trợ.

## 6. Nhịp làm việc, rủi ro và bước đầu

Mỗi tuần khoảng 1 giờ học đúng phần sắp dùng, 6–8 giờ triển khai, 1 giờ test/ghi kết quả. Không học toàn bộ stack rồi mới bắt đầu.

Task có input/output/test và commit nhỏ sau khi đạt. Ví dụ: crossing hai lần cùng event ID → DB một record → overview tăng một lượt. Cuối tuần ghi chạy được gì, đo được gì, lỗi còn lại, việc đầu tiên tuần sau.

Nếu chậm: dừng trang trí UI/ngoài MVP trước; không ngầm bỏ hai chức năng hoặc chuyển sang mock. Sau tuần 6 không đổi model tùy hứng. Tuần 12 chưa đạt thì phát hành prototype với hạn chế, không tuyên bố production-ready.

Buổi đầu tiên: **Pi nhận camera → frame thật → detection → tracking → ghi latency/RAM/nhiệt/version**. Tiếp theo: contract → crossing giả xuyên suốt → crossing thật → queue → ESP32 ACK → đánh giá → resilience → portfolio.

## 7. Nhật ký tiến độ

Chưa có mục nào được nghiệm thu tại thời điểm lập. Kết quả đo đặt trong `evaluation/`, quyết định trong `docs/decisions/`, vận hành trong `docs/operations/`; không commit model lớn, clip riêng tư, secret/runtime DB.

| Ngày | Phần/task | Kết quả/bằng chứng | Blocker | Việc tiếp theo |
|---|---|---|---|---|
| — | Chưa bắt đầu | — | — | Phần 0: Pi/camera/model |
