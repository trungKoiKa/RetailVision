# Checklist khởi tạo RetailVision

Tài liệu này quy định thứ tự triển khai và điều kiện hoàn thành của từng giai đoạn. Mục tiêu là khóa sớm các giao diện giữa các tiến trình, chứng minh một lát cắt xuyên suốt bằng dữ liệu giả, rồi mới mở rộng lần lượt edge, firmware, backend và frontend. Không chuyển sang giai đoạn kế tiếp chỉ vì đã tạo đủ thư mục; phải có bằng chứng chạy hoặc kiểm thử tương ứng.

## Giai đoạn 0 — Chốt hợp đồng và baseline công nghệ

Mục tiêu: Python edge, ESP32, Spring Boot và React cùng dựa trên một ngôn ngữ dữ liệu trước khi viết nghiệp vụ.

- [ ] Chốt topic MQTT, chiều publish/subscribe, QoS, retain, ACL và quy tắc wildcard.
- [ ] Chốt envelope chung: `schema_version`, `event_id`, `session_id`, `seq`, `occurred_at`, `site_id`, `camera_id`.
- [ ] Viết JSON Schema cho `crossing`, `queue_state`, `alert`, `alert_ack`, `storage_ack`, `heartbeat`, `settings_set` và `settings_result` trong `contracts/mqtt/`.
- [ ] Tạo payload hợp lệ, payload sai schema và payload trùng ID trong `contracts/examples/`.
- [ ] Chốt OpenAPI tối thiểu cho login và API đọc một crossing trong `contracts/api/`.
- [ ] Chốt mô hình dữ liệu ban đầu và quy tắc idempotency: unique `event_id` hoặc khóa nghiệp vụ đã định nghĩa rõ.
- [ ] Chốt UTC ở dữ liệu gốc, `Asia/Ho_Chi_Minh` chỉ dùng khi hiển thị/tổng hợp.
- [ ] Ghi baseline phiên bản tại mục 7.1 của `TrienKhai.md`; sinh lockfile hoặc wrapper khi khởi tạo từng module.

Điều kiện hoàn thành: schema có phiên bản; ví dụ payload qua validation; quy tắc tương thích ngược và xử lý trường không biết đã được ghi; không còn tên trường cùng nghĩa nhưng khác nhau giữa tài liệu.

## Giai đoạn 1 — Nền backend: PostgreSQL và Flyway

Mục tiêu: tạo đường ghi dữ liệu nhỏ nhất trước khi xây toàn bộ API.

- [ ] Khởi tạo Maven Wrapper và Spring Boot theo cây backend tại mục 8.2 của `TrienKhai.md`.
- [ ] Tạo `V001__baseline.sql` cho site, camera, session và crossing; chưa tạo toàn bộ schema tương lai trong một migration lớn.
- [ ] Cấu hình PostgreSQL và Flyway; dùng `ddl-auto=validate`, không dùng Hibernate tự tạo schema.
- [ ] Thêm unique constraint phục vụ QoS 1/replay và index cho truy vấn crossing theo camera/thời gian.
- [ ] Viết test migration từ database rỗng và test insert trùng `event_id`.
- [ ] Đưa PostgreSQL vào `deploy/server/compose.yaml`; backend có thể chạy ngoài container trong giai đoạn này.

Điều kiện hoàn thành: một lệnh dựng được PostgreSQL rỗng, Flyway áp migration thành công và chạy lại không làm thay đổi schema ngoài dự kiến.

## Giai đoạn 2 — Lát cắt crossing end-to-end

Mục tiêu: chứng minh sớm đường tích hợp quan trọng nhất bằng đúng hợp đồng thật, chưa phụ thuộc camera hoặc model.

```text
Bản tin crossing giả
→ Mosquitto
→ Spring Boot
→ PostgreSQL
→ REST API
→ React hiển thị một lượt vào
```

- [ ] Chạy Mosquitto và publish payload `crossing` mẫu từ `contracts/examples/`.
- [ ] Spring subscribe, validate schema, chống trùng và commit crossing trong transaction.
- [ ] Chỉ publish `storage_ack` sau khi transaction đã commit.
- [ ] Cung cấp `GET /api/footfall/recent` hoặc endpoint tối thiểu tương đương theo OpenAPI.
- [ ] React gọi API thật và hiển thị một lượt `IN`; không dùng mock sau khi lát cắt đã nối xong.
- [ ] Tạo integration test cho broker → backend → PostgreSQL → API.

Điều kiện hoàn thành: một payload hợp lệ xuất hiện đúng một lần trên React; phát lại cùng `event_id` không tăng dữ liệu; payload sai schema không được ghi và không nhận storage ACK.

## Giai đoạn 3 — Edge và bằng chứng khả thi trên Pi

Mục tiêu: thay bản tin giả bằng crossing thật từ một pipeline camera/model/tracker chạy được trên Pi.

- [ ] Hoàn thiện parser và validation cho camera, model, ROI, MQTT và spool.
- [ ] Capture giữ frame mới nhất, timestamp và reconnect; không tích lũy hàng chờ video.
- [ ] Adapter vision trả bbox/track ID theo tọa độ frame gốc.
- [ ] Crossing, queue dwell, alert hysteresis và UNKNOWN là state machine có unit test, không phụ thuộc camera.
- [ ] Publish event theo contract; spool có giới hạn và chỉ xóa sau storage ACK.
- [ ] Đo `.pt` và NCNN bằng cùng clip gán nhãn trên đúng Pi 4.

Điều kiện hoàn thành: edge chạy headless trên Pi; một pipeline dùng chung cho cửa và vùng chờ; bản tin crossing thật thay được publisher giả mà backend/frontend không phải đổi contract; có log FPS, freshness, RAM và nhiệt độ.

## Giai đoạn 4 — Firmware ESP32

Mục tiêu: thiết bị vật lý nhận đúng trạng thái và xác nhận đúng sự kiện qua contract đã khóa.

- [ ] Chốt chân LED/nút và tạo bảng đấu nối.
- [ ] Kết nối Wi-Fi/MQTT bằng tài khoản `node01` có ACL tối thiểu.
- [ ] Hiện thực UNKNOWN/NORMAL/OVERLOAD_UNACKED/ACKED và timeout về UNKNOWN.
- [ ] Chống dội nút; ACK chứa `ack_id`, `event_id`, `device_id` và timestamp.
- [ ] Test reconnect, bản tin lặp, ACK sai event và mất broker.

Điều kiện hoàn thành: LED phản ánh đúng state; ACK lặp không gây hiệu ứng lặp; dữ liệu quá hạn chuyển UNKNOWN trong thời gian cấu hình.

## Giai đoạn 5 — Hoàn thiện backend theo nghiệp vụ

Mục tiêu: mở rộng lát cắt crossing thành backend MVP, không phá hợp đồng đã chạy.

- [ ] Mở rộng Flyway theo migration nhỏ cho device status, queue sample, alert, ACK và settings.
- [ ] Hoàn thiện ingestion cho mọi payload MQTT và storage ACK sau commit.
- [ ] Thêm login/JWT và kiểm quyền ADMIN/MANAGER tại API.
- [ ] Tạo API overview, footfall, alerts, devices, settings và CSV.
- [ ] Xử lý vòng đời settings PENDING/APPLIED/REJECTED bằng `request_id`.
- [ ] Test timezone, replay, QoS 1 duplicate, coverage gap và transaction rollback.

Điều kiện hoàn thành: migration chạy từ database rỗng; restart/replay không nhân đôi dữ liệu; API trái quyền bị từ chối; báo cáo giữ UNKNOWN/gap thay vì đổi thành 0.

## Giai đoạn 6 — Hoàn thiện frontend

Mục tiêu: thay màn hình lát cắt bằng giao diện MVP sử dụng toàn bộ API thật.

- [ ] Tạo login và lớp API/auth dùng chung.
- [ ] Overview hiển thị freshness của camera, Pi, ESP32 và backend.
- [ ] Footfall theo giờ/ngày kèm coverage và CSV.
- [ ] Alerts hiển thị OPEN/ACK/END/INTERRUPTED.
- [ ] Devices/Settings hiển thị PENDING/APPLIED/REJECTED.
- [ ] Bổ sung loading, empty, error, stale và unauthorized state.

Điều kiện hoàn thành: không còn dữ liệu mock trong nghiệm thu; frontend không truy cập MQTT/PostgreSQL; refresh và token hết hạn được xử lý rõ ràng.

## Giai đoạn 7 — Replay, phục hồi và kiểm thử xuyên hệ thống

- [ ] Kiểm JSON Schema và OpenAPI trong CI.
- [ ] Chạy integration test với Mosquitto/PostgreSQL tạm thời.
- [ ] Tắt lần lượt backend, broker, camera, ESP32 và reboot Pi.
- [ ] Kiểm tra ACK trùng, replay ngược thứ tự, spool đầy và database rollback.
- [ ] Chạy bench 30 phút rồi 2–4 giờ; lưu FPS, p95 latency, RAM, nhiệt và coverage.

Điều kiện hoàn thành: lỗi không bị biến thành số 0; dữ liệu replay không trùng; trạng thái tự phục hồi hoặc báo rõ nguyên nhân cần can thiệp.

## Giai đoạn 8 — Đóng gói và triển khai

- [ ] Hoàn thiện systemd, Mosquitto ACL, Dockerfile và `deploy/server/compose.yaml`.
- [ ] Viết backup/restore PostgreSQL và kiểm thử restore thật.
- [ ] Viết hướng dẫn máy sạch, health check và rollback.
- [ ] Đóng băng phiên bản Pi OS, Python, model, Java, Node, database và cấu hình demo.
- [ ] Liên kết mỗi tiêu chí nghiệm thu với log, CSV, ảnh hoặc video bằng chứng.

Điều kiện hoàn thành: máy mới có thể triển khai theo tài liệu; reboot tự phục hồi; profile demo và profile đánh giá được phân biệt rõ.

## Thứ tự pull request/commit đề xuất

1. `contracts/mqtt-api-v1`
2. `backend/flyway-crossing-schema`
3. `integration/crossing-vertical-slice`
4. `edge/config-capture-vision`
5. `edge/crossing-queue-state-machines`
6. `firmware/mqtt-alert-ack`
7. `backend/mvp-services-api`
8. `frontend/mvp-dashboard`
9. `integration/replay-failure-tests`
10. `deploy/pi-server-pilot`
