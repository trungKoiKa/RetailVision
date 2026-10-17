# RetailVision — Checklist triển khai từng phần

Cập nhật: 2026-10-17 theo [ADR-0001](decisions/0001-hop-nhat-quyet-dinh-ky-thuat.md). Nhật ký tiến độ và mốc thời gian: [personal-project-roadmap.md](personal-project-roadmap.md). Tất cả mục dưới đây **chưa được nghiệm thu**, trừ phần 0.

Thứ tự theo ADR-0001 D10: làm trước vòng **Camera → Pi → ESP32** (chạy được không cần máy chủ), sau đó mới tới backend/frontend. Tận dụng skeleton, không tạo class rỗng cho đủ cây. Chỉ đánh dấu khi có bằng chứng.

## Cách sử dụng

1. Chọn một task ở phần hiện tại, khoảng 1–3 giờ.
2. Triển khai, kiểm tra, ghi log/test/video hoặc kết quả đo.
3. Đánh dấu nếu đạt; ghi blocker nếu chưa đạt.
4. Chỉ chuyển phần sau khi đạt gate. Phần 1 (Pi) có thể chạy song song với phần 2–4 trên laptop.

Ước lượng giờ chỉ để tham khảo; ghi từng buổi trong [nhật ký roadmap](personal-project-roadmap.md#7-nhật-ký-tiến-độ).

## Phần 0 — Chốt quyết định

- [x] ADR-0001 hợp nhất firmware, auth, bù dữ liệu, topic, lược đồ DB, đồng bộ giờ, ngưỡng nghiệm thu.
- [x] PRD 0.2, `TrienKhai.md` và checklist này sửa theo ADR.
- [ ] Hỏi giảng viên: ngưỡng FPS/độ đúng nghiệm thu, đồ án nhóm hay cá nhân, hạn nộp (PRD OQ-03, OQ-07).

**Gate:** chỉ còn một đặc tả cho mỗi giao diện.

## Phần 1 — Smoke test Pi (~4 giờ, song song)

- [ ] Ghi Pi/OS/Python/camera/nguồn/tản nhiệt thực tế.
- [ ] Đọc frame thật bằng OpenCV qua SSH (không `imshow`).
- [ ] Tạo `edge/.venv`; YOLOv8n detect class person; `model.track(..., persist=True)` trên stream liên tục.
- [ ] Đo FPS inference, RAM, nhiệt, `vcgencmd get_throttled`; lưu vào `evaluation/benchmarks/`.
- [ ] Cài chrony, trỏ NTP về máy chủ LAN; `chronyc tracking` báo đồng bộ khi không có Internet.
- [ ] Nếu dependency chặn >2 giờ: fallback Bookworm 64-bit trên thẻ khác, ghi quyết định.

**Gate:** model + tracking chạy trên Pi thật, có số đo; chưa cần tốc độ cuối.

## Phần 2 — Contract (~4 giờ)

- [ ] `docs/architecture/mqtt-topics.md` theo bảng ADR-0001 D4 (topic, publisher/subscriber, QoS/retain, ACL).
- [ ] JSON Schema trong `contracts/mqtt/`: envelope chung, `state`, `events/crossing`, `events/alert`, `telemetry`, `status`, `operator-ack`, `settings/set`, `settings/result`.
- [ ] Ví dụ hợp lệ/sai/trùng trong `contracts/examples/`; script validate chạy được.
- [ ] Quy ước UTC, `Asia/Ho_Chi_Minh` khi hiển thị, `queue_count=null` khi UNKNOWN, `seq` chỉ so trong cùng session.

**Gate:** mọi ví dụ hợp lệ qua schema, ví dụ sai bị từ chối.

## Phần 3 — Analytics thuần (~8 giờ, laptop)

- [ ] `core/types.py`, `core/clock.py` (clock thay thế được).
- [ ] `analytics/geometry.py`: tọa độ chuẩn hóa → pixel, đoạn vạch hữu hạn, point-in-polygon.
- [ ] `analytics/crossing.py`: bottom-center, deadband, `min_stable_observations`, IN/OUT, xóa track hết hạn.
- [ ] `analytics/queue.py`: dwell, chỉ đếm track có quan sát mới.
- [ ] `analytics/alert_state.py`: NORMAL/OVERLOAD/UNKNOWN, on/off count, hold, reset timer, `alert_id`, END reason NORMALIZED/INTERRUPTED/CONFIG_CHANGED, xử lý ACK theo `alert_id`.
- [ ] Unit test bằng chuỗi tọa độ/clock giả cho T01–T10, T14, T16, T23 (không cần camera/YOLO).

**Gate:** `pytest edge/tests/unit` xanh; analytics không import OpenCV/Ultralytics.

## Phần 4 — Pipeline edge và công cụ (~8 giờ)

- [ ] `config/loader.py` + `validation.py`: đường dẫn tương đối theo file YAML, kiểm `off_count < on_count`.
- [ ] `pipeline/capture.py`: camera hoặc file video; giữ frame mới nhất; timestamp video khi replay; reconnect.
- [ ] `pipeline/detector.py`, `tracker.py`, `runner.py`: một lần suy luận mỗi frame, tọa độ về frame gốc.
- [ ] `tools/calibrate.py`: click vạch/đa giác trên frame, xuất YAML chuẩn hóa.
- [ ] Preview MJPEG có công tắc, chỉ dùng hiệu chuẩn/demo.
- [ ] Log FPS capture/xử lý và tuổi frame.
- [ ] Cùng một clip chạy hai lần cho cùng kết quả đếm (FR-13).

**Gate:** đếm IN/OUT và queue đúng trên video quay sẵn, chạy được trên laptop và Pi.

## Phần 5 — MQTT và ESP32: demo lõi (~10 giờ)

- [ ] Mosquitto trên Pi: tài khoản `edge01`/`node01`/`backend01`, ACL, `persistence true`, giới hạn hàng đợi; mẫu tại `deploy/pi/mosquitto/`.
- [ ] `messaging/`: publish `state` 1 Hz (QoS 0), sự kiện QoS 1, `status` retained + Last Will; subscribe `node01/events/operator-ack`.
- [ ] `tools/fake_publisher.py` phát state/sự kiện theo contract.
- [ ] Firmware PlatformIO + Arduino-ESP32 + PubSubClient + ArduinoJson; `secrets.h` không commit.
- [ ] Đấu LED đỏ/xanh/vàng, còi qua transistor, nút; bảng chân trong `docs/operations/hardware-setup.md`.
- [ ] Máy trạng thái UNKNOWN/NORMAL/OVERLOAD_UNACKED/OVERLOAD_ACKED theo `state` + `acked`; timeout 5 giây.
- [ ] Debounce; ACK theo `alert_id`, gửi lại cùng `ack_id` mỗi 1 giây tới khi `acked=true` (tối đa 10 lần).
- [ ] Pi bỏ ACK lặp/sai alert; ACK không đóng OVERLOAD; còi tắt sau ACK.
- [ ] Test mất Wi-Fi/broker và reconnect không chặn LED/nút (T12, T17, T24).

**Gate:** camera → OVERLOAD → đèn đỏ + còi → bấm ACK → còi tắt, đỏ giữ → giảm người → END, **không cần máy chủ**.

## Phần 6 — Backend lát cắt (~8 giờ)

- [ ] Spring Boot 3.5 / Java 21 / Maven Wrapper: Web, Validation, JPA, PostgreSQL, Flyway, Paho.
- [ ] `V001__crossing.sql`, `V002__alerts.sql`, `V003__monitoring.sql`; `ddl-auto=validate`; test migration từ DB rỗng.
- [ ] MQTT client `cleanSession=false`, client-id `backend01`, `setManualAcks(true)`.
- [ ] Ingestion: validate → dedupe theo `event_id` → commit → `messageArrivedComplete`; payload sai không lưu; trùng vẫn ack.
- [ ] Lưu `server_received_at`; cập nhật `device_status` từ `status`.
- [ ] `GET /api/overview`, `/api/alerts`, `/api/devices`, `/api/health`.
- [ ] Test: bản tin trùng → một bản ghi (T15); lỗi DB → không ack, broker gửi lại.

**Gate:** crossing/alert thật từ Pi vào DB đúng một lần.

## Phần 7 — Frontend lát cắt (~6 giờ)

- [ ] Vite + React + TypeScript, dev proxy `/api` (cùng origin).
- [ ] Trang Overview polling 2 giây: IN/OUT hôm nay, queue/state, tuổi dữ liệu, alert gần nhất, trạng thái thiết bị.
- [ ] UNKNOWN/stale hiển thị rõ, không hiện 0.

**Gate:** web hiển thị dữ liệu thật từ Pi qua Spring/PostgreSQL. Đây là MVP `v0.1.0` (chưa login/báo cáo/settings).

## Phần 8 — Triển khai Pi và benchmark (~8 giờ)

- [ ] So `.pt` 320, NCNN 320, NCNN 416 trên cùng clip và cùng Pi (A1–A3).
- [ ] File tracker FPS thấp: chỉnh `track_buffer`, ngưỡng ghép theo FPS đo được (ADR-0001 D11).
- [ ] Đo FPS toàn luồng, tuổi frame, RAM/swap, nhiệt, throttling khi chạy kèm broker.
- [ ] systemd `retail-edge.service`; reboot Pi tự chạy lại.

**Gate:** có bảng benchmark tái hiện được; chọn cấu hình theo cả độ đúng và tài nguyên.

## Phần 9 — Phục hồi lỗi (~6 giờ)

- [ ] Tắt backend 5 phút, phát sự kiện, bật lại: không mất, không trùng (T25, MET-07).
- [ ] Restart Mosquitto khi còn hàng đợi; kiểm persistence.
- [ ] Rút camera → UNKNOWN, `queue_count=null`, alert END INTERRUPTED (T11).
- [ ] Reboot Pi không Internet: giờ đúng hoặc `clock_synced=false` rõ (T26).
- [ ] Chạy ≥2 giờ không crash, RAM không tăng bất thường (T18).
- [ ] Nếu mất/nhân đôi dữ liệu: ghi kết quả, viết ADR bổ sung SQLite outbox (ADR-0001 điều kiện xem xét lại D3).

**Gate:** phục hồi hoặc báo lỗi rõ trong mọi kịch bản trên.

## Phần 10 — Nghiệp vụ web (~10 giờ)

- [ ] `V004__auth.sql`; Spring Security session, BCrypt, CSRF cho request ghi, ADMIN/MANAGER kiểm ở API.
- [ ] Trang Login; route guard; xử lý 401/403/session hết hạn.
- [ ] Báo cáo giờ/ngày theo giờ Việt Nam, coverage từ `telemetry_minute`, phút thiếu là gap (T21).
- [ ] Alerts phân trang: opened/acked/ended, độ trễ ACK, end_reason.
- [ ] CSV export.
- [ ] (P1) `V005__settings.sql`; `PUT /api/settings` → `settings/set` → `settings/result`; PENDING/APPLIED/REJECTED; revision cũ không ghi đè; END CONFIG_CHANGED.
- [ ] (P1) OLED trên ESP32.

**Gate:** báo cáo không biến thiếu dữ liệu thành 0; auth đúng khi gọi thẳng API.

## Phần 11 — Đánh giá (~12 giờ)

- [ ] Clip có đồng ý người tham gia; tách dev/test theo buổi, không trộn frame.
- [ ] Ground truth crossing (timestamp/hướng), queue count sau dwell, alert interval theo profile.
- [ ] Crossing: sai số mỗi hướng ≤10% (≤5% mục tiêu mở rộng), có clip zero-count.
- [ ] Queue MAE ≤1 người.
- [ ] Alert precision/recall ≥0,90: state machine chạy trên chuỗi queue-count có nhãn + clip live profile demo; ghi rõ nguồn và cỡ mẫu.
- [ ] p95 quyết định edge → LED ≤1 giây, không tính hold, đo bằng clock hợp lệ.

**Gate:** dữ liệu test độc lập; số liệu thật được ghi kể cả khi không đạt.

## Phần 12 — Đóng gói (~8 giờ)

- [ ] `deploy/server/compose.yaml` cho PostgreSQL/backend/frontend cùng origin.
- [ ] DB/broker không public Internet; secret ngoài source.
- [ ] Backup/restore PostgreSQL đã thử thật.
- [ ] CI: unit edge, contract validate, build backend/frontend; Testcontainers integration nếu kịp.
- [ ] README quickstart từ clone sạch; người không có Pi chạy được bằng replay video + fake publisher.
- [ ] Video demo 3–5 phút; tài liệu kiến trúc, benchmark, giới hạn; release theo kết quả thực.

**Gate:** tái hiện được, số liệu có bằng chứng; không tuyên bố production-ready.

## Khi thiếu thời gian

Cắt theo thứ tự (ADR-0001 D10): settings web → CSV → vai trò MANAGER → NCNN 416 → OLED. **Không cắt:** UNKNOWN, chống trùng, đo trên Pi thật, test offline.

## Bằng chứng

Kết quả trong `evaluation/`, quyết định trong `docs/decisions/`, vận hành trong `docs/operations/`. Không commit model lớn, clip riêng tư, secret/runtime DB. Chỉ ghi command vào README khi đã chạy thành công.

**Việc tiếp theo:** phần 1 (Pi) song song với phần 2 (contract).
