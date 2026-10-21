# 3. Kế hoạch và tiến độ

Tài liệu trả lời: làm gì trước, đang ở đâu. Mỗi phần chỉ đánh dấu khi có bằng chứng (log, test, video, số đo) và chỉ chuyển phần khi đạt gate. Mã test T01–T26 xem [evaluation/README.md](../evaluation/README.md).

**Nguyên tắc thứ tự:** làm trước vòng Camera → Pi → ESP32 vì nó chạy được không cần máy chủ và là trọng tâm của đồ án nhúng; backend/frontend làm sau. Phần 1 chạy song song với phần 2–4.

**Quỹ thời gian tham khảo:** ~110 giờ (8–10 giờ/tuần). MVP = hết phần 7.

## Phần 0 — Chốt quyết định

- [x] ADR-0001; tài liệu gộp còn 3 file.
- [ ] Hỏi giảng viên ngưỡng nghiệm thu, nhóm/cá nhân, hạn nộp (OQ-03, OQ-07).

## Phần 1 — Smoke test Pi (~4 giờ)

- [ ] Ghi Pi/OS/Python/camera/nguồn thực tế.
- [ ] Đọc frame qua SSH; YOLOv8n detect person; `track(persist=True)` trên stream liên tục.
- [ ] Đo FPS, RAM, nhiệt, throttling → `evaluation/benchmarks/`.
- [ ] chrony đồng bộ với máy chủ LAN khi không có Internet.
- [ ] Dependency chặn >2 giờ → thử Bookworm trên thẻ khác, ghi lại.

**Gate:** model + tracking chạy trên Pi thật, có số đo.

## Phần 2 — Contract (~4 giờ)

- [x] JSON Schema trong `contracts/mqtt/` theo [bảng topic](../contracts/mqtt/README.md).
- [x] Ví dụ hợp lệ/sai/trùng trong `contracts/examples/`, script validate.

**Gate:** ví dụ hợp lệ qua, ví dụ sai bị từ chối.

## Phần 3 — Analytics thuần (~8 giờ)

- [x] `core/clock.py`, `geometry.py`, `crossing.py`, `queue.py`, `alert_state.py`.
- [x] Unit test bằng tọa độ/clock giả: T01–T10, T14, T16, T23.

**Gate:** `pytest` xanh; analytics không import OpenCV/Ultralytics.

## Phần 4 — Pipeline edge và công cụ (~8 giờ)

- [x] Loader YAML + validation.
- [x] Capture camera/file video, frame mới nhất, timestamp video khi replay, reconnect.
- [x] Detector/tracker/runner, tọa độ về frame gốc.
- [x] `tools/calibrate.py`; preview MJPEG có công tắc. *(`--preview-port`, đã thử trên clip thật; chưa thử trên Pi)*
- [ ] Log FPS và tuổi frame; cùng clip chạy hai lần cùng kết quả.

**Gate:** đếm cửa và vùng chờ đúng trên video quay sẵn.

*Trạng thái:* chưa đạt. Mới thử trên một đoạn VIRAT 60 s (3 lượt IN, nhãn tay do AI ước lượng, chưa kiểm độc lập), chưa phải cảnh cửa hàng; vùng chờ và cảnh báo chưa được thử với video có người. Cần clip quay thật.

## Phần 5 — MQTT và ESP32: demo lõi (~10 giờ)

- [x] Mosquitto: tài khoản, ACL, persistence, giới hạn hàng đợi (`deploy/pi/mosquitto/`) — ACL đã kiểm bằng Mosquitto trên Windows, chưa cài trên Pi.
- [x] Edge publish `state`/sự kiện/`status`, nhận `operator-ack`; `tools/fake_publisher.py`.
- [ ] Firmware: LED, còi, nút debounce, 4 trạng thái, timeout 5 giây, gửi lại ACK. *(đã viết, 25 test logic xanh, biên dịch được; chưa nạp lên ESP32)*
- [x] Bảng chân GPIO trong `firmware/retail_alert/README.md`.
- [ ] T12, T17, T24.

**Gate:** camera → đỏ + còi → ACK → còi tắt, đỏ giữ → giảm người → xanh, **không cần máy chủ**.

## Phần 6 — Backend lát cắt (~8 giờ)

- [x] Spring Boot + Flyway V001–V003, `ddl-auto=validate`.
- [x] Paho `cleanSession=false`, manual ack sau commit; dedupe `event_id`.
- [x] `GET /api/overview`, `/alerts`, `/devices`, `/health`.
- [x] T15; lỗi DB → không ack, broker gửi lại.

**Gate:** sự kiện thật từ Pi vào DB đúng một lần.

*Trạng thái:* chưa đạt với Pi thật. Đã chạy chuỗi edge giả → Mosquitto → backend → PostgreSQL → API và 54 test (PostgreSQL, Mosquitto thật).

## Phần 7 — Frontend lát cắt (~6 giờ)

- [x] Vite + React + TS, proxy `/api`.
- [x] Overview polling 2 giây: IN/OUT, queue/state, tuổi dữ liệu, alert, thiết bị; UNKNOWN không hiện 0.

**Gate:** web hiện dữ liệu thật. **MVP `v0.1.0`.**

*Trạng thái:* đã hiện dữ liệu thật từ chuỗi edge giả → Mosquitto → backend → PostgreSQL; chưa có dữ liệu từ Pi thật.

## Phần 8 — Triển khai Pi và benchmark (~8 giờ)

- [ ] `.pt` 320, NCNN 320, NCNN 416 trên cùng clip/Pi. *(công cụ `evaluation/benchmarks/bench.py` và `export_ncnn.py` đã có, chạy được cả `.pt` và NCNN trên laptop; chưa đo trên Pi)*
- [ ] Chỉnh tracker theo FPS thật.
- [ ] FPS toàn luồng, tuổi frame, RAM, nhiệt khi chạy kèm broker.
- [ ] systemd; reboot tự chạy lại. *(`retail-edge.service`, `install_edge.sh`, chrony đã viết và kiểm cú pháp; chưa chạy trên Pi)*

**Gate:** bảng benchmark tái hiện được.

## Phần 9 — Phục hồi lỗi (~6 giờ)

- [x] T11, T13, T18, T25, T26. *(phần kiểm tự động được trên laptop; phần phần cứng còn lại ghi trong `evaluation/recovery/README.md`)*
- [ ] Mất/nhân đôi dữ liệu ở T25 → ghi kết quả, viết ADR bổ sung outbox trên edge.

**Gate:** mọi kịch bản phục hồi được hoặc báo lỗi rõ.

*Trạng thái:* đạt ở mức tự động trên laptop (Mosquitto, PostgreSQL thật); chưa thử trên Pi, camera, ESP32 thật.

## Phần 10 — Nghiệp vụ web (~10 giờ)

- [x] V004, đăng nhập session, CSRF, ADMIN/MANAGER kiểm ở API.
- [x] Báo cáo giờ/ngày, coverage, gap; alerts phân trang; CSV (T21). *(backend; trang web Footfall/Alerts/Devices ở lát 10c)*
- [x] (P1) Settings: V005, PENDING/APPLIED/REJECTED, revision cũ không ghi đè. *(backend + edge; trang web ở lát 10c)*
- [x] (P1) OLED. *(logic chữ có test; build được; chưa thử trên màn hình thật)*

**Gate:** báo cáo không biến thiếu dữ liệu thành 0; gọi thẳng API sai quyền bị chặn.

*Trạng thái:* đạt ở mức tự động và trên Chrome với hệ thống thật (backend + PostgreSQL + Mosquitto + edge Python thật); chưa có dữ liệu từ Pi/camera thật. OLED (P1) làm ở bước 13 (chưa thử trên màn hình thật).

## Phần 11 — Đánh giá (~12 giờ)

- [ ] Thu clip có đồng ý, tách dev/test theo buổi; gán nhãn. *(công cụ `record`, `calibrate`, `label`, `label_queue` và quy trình ở `evaluation/scenarios/` đã có; chưa có clip nào)*
- [ ] Đo theo [evaluation/README.md](../evaluation/README.md); ghi số thật kể cả khi không đạt. *(công cụ `evaluate.py`, `latency_echo.py`, `--latency-out` đã có và được kiểm bằng dữ liệu dựng tay; chưa có số đo thật)*

**Gate:** kết quả trên tập test độc lập.

## Phần 12 — Đóng gói (~8 giờ)

- [x] Compose máy chủ, secret ngoài source, backup/restore đã thử. *(thử trên Windows + Docker Desktop, cả script sh và ps1)*
- [x] CI: unit edge, validate contract, build backend/frontend, firmware, Compose. *(workflow đã qua actionlint; chưa chạy trên GitHub cho đến khi PR mở)*
- [x] README quickstart; chạy thử bằng broker + edge giả khi không có Pi. *(chạy từ cây làm việc, chưa phải clone sạch trên máy khác)*
- [ ] Video demo 3–5 phút.

**Gate:** người khác tái hiện được.

## Khi thiếu thời gian

Cắt theo thứ tự: settings web → CSV → vai trò MANAGER → NCNN 416 → OLED. Không cắt: UNKNOWN, chống trùng, đo trên Pi thật, test offline.

## Nhật ký

| Ngày | Phần/task | Kết quả, bằng chứng | Blocker | Tiếp theo |
| --- | --- | --- | --- | --- |
| 2026-10-17 | 0 | ADR-0001, gộp tài liệu | — | Phần 1 + 2 |
| 2026-10-19 | 2, 3, 4 | Contract + validate; analytics 34 test; pipeline, CLI, công cụ gán nhãn và chấm điểm; `pytest` 55 xanh | Chưa có clip cảnh cửa hàng | Sửa độ lệch thời điểm đếm |
| 2026-10-20 | 4 | Ghi thời điểm lượt qua vạch bằng nội suy; đoạn VIRAT 60 s: 3 TP/0 FP/0 FN ở tol 1,0 s, 2 TP/1 FP/1 FN ở tol 0,5 s (trước: 2/1/1 và 0/3/3); `pytest` 57 xanh | Một clip, 3 nhãn; lệch ~0,8 s ở người giữa nhóm do bbox bị che | Phần 1: smoke test trên Pi |
| 2026-10-20 | 5 | Edge gửi MQTT (state, crossing, alert, telemetry, status+LWT), nhận ACK; `fake_publisher`; Mosquitto conf + ACL; `check_acl.py` 9/9; luồng edge giả → broker → ESP32 giả → ACK chạy đúng; `pytest` 87 xanh (gồm test broker thật) | Chưa có firmware, chưa thử trên Pi | Firmware ESP32 |
| 2026-10-21 | 5 | Khung firmware PlatformIO: logic thuần `lib/alert_core` (25 test native xanh), task mạng, `main.cpp`; biên dịch `esp32dev` thành công (RAM 13,9%, Flash 59%, không cảnh báo); bản tin C++ `operator-ack`/`status` qua JSON Schema thật | Chưa nạp lên ESP32, chưa thử với broker; `node01/status` cần giờ UTC (xem README firmware) | Bạn đấu mạch, nạp, thử với `fake_publisher` |
| 2026-10-21 | 6 | Backend Spring: Flyway V001–V003, nhận MQTT (cleanSession=false, ack sau commit, chống trùng event_id), API overview/alerts/devices/health; 54 test xanh (PostgreSQL + Mosquitto thật: trùng event_id, DB lỗi → gửi lại, backend tắt rồi bật vẫn nhận đủ); chạy thử edge giả → backend → DB → API | Chưa thử với Pi thật; chưa đăng nhập | Phần 7: frontend Overview |
| 2026-10-21 | 7 | Frontend Vite/React: trang Tổng quan; 16 test (vitest), typecheck và build sạch; kiểm trên Chrome với backend thật: hiện OVERLOAD 5 người, tắt backend thì banner lỗi và mọi số liệu thành "—" | Chưa có Login/Footfall/Alerts/Devices (Phần 10) | Phần 8-9 |
| 2026-10-21 | 8 | Công cụ benchmark (`bench.py`, `export_ncnn.py`, `sysmetrics`), `retail-edge.service`, chrony, `install_edge.sh`, cấu hình camera mẫu; 109 test edge xanh; NCNN 320/416 xuất được và chạy trong pipeline thật trên laptop (320 chỉ thấy 1/3 lượt trên clip VIRAT: cần kiểm kích thước với cảnh thật) | Chưa có số đo Pi, chưa cài thử trên Pi | Phần 9 |
| 2026-10-21 | 9 | Phục hồi lỗi: camera mất/chưa cắm (UNKNOWN, tự phục hồi), broker dừng/restart, backend tắt, DB sập thật, broker lên muộn; sửa 3 lỗi thật (edge thoát khi chưa có camera, Ultralytics gọi ra Internet, backend phục hồi chậm khi DB sập); edge 127 test, backend 59 test, frontend 18 test xanh | Chưa thử trên Pi/camera/ESP32 thật | Phần 10 |
| 2026-10-21 | 10b | Đổi ngưỡng từ web (FR-09, P1): backend `PUT /api/settings` (PENDING/APPLIED/REJECTED/UNCONFIRMED), edge áp dụng nguyên bộ, revision cũ bị từ chối, lệnh trùng không áp dụng hai lần, lưu qua restart; edge 164 test, backend 99 test; kiểm chéo ngôn ngữ thật: edge Python thật ↔ Mosquitto ↔ backend Java thật, đổi hai lần qua API đều APPLIED, file lưu và `settings_revision` trong state khớp | Chưa có trang web (10c) | 10c |
| 2026-10-21 | 10c | Trang web: Đăng nhập, Lượt vào/ra (biểu đồ, bảng, gap xám, CSV), Cảnh báo, Thiết bị + đổi ngưỡng, Tài khoản; 59 test vitest; kiểm trên Chrome với hệ thống thật: đăng nhập, báo cáo có 6 khung xám và không có cột 0, đổi ngưỡng được edge thật áp dụng (revision 1). Test phát hiện và sửa một lỗi thật: `queryClient.clear()` làm giao diện không cập nhật sau đăng nhập/đăng xuất | OLED (P1) chưa làm; chưa có Pi thật | Phần 11 |
| 2026-10-21 | 11 | Công cụ đánh giá: `metrics.py` (sai số đếm từng hướng, MAE vùng chờ, precision/recall cảnh báo ±3 s bằng chính máy trạng thái của edge, khoảng tin cậy Wilson, p50/p95), `evaluate.py` (manifest dev/test → báo cáo, cảnh báo cỡ mẫu nhỏ, không kết luận khi thiếu dữ liệu), `label_queue.py`, `record.py` (video đúng thời gian thực), `calibrate.py` (vạch/vùng → YAML, mũi tên chiều vào), đo độ trễ (`--latency-out`, firmware echo + `latency_echo.py`); edge 210 test, firmware 26 test và build `esp32dev_debug`; chạy thử `evaluate.py` trên kết quả thật của clip VIRAT (3 lượt IN, ghi rõ mẫu nhỏ) | Chưa có clip và nhãn chính thức, chưa có số đo trên Pi; nhãn VIRAT do AI ước lượng | Phần 12 |
| 2026-10-21 | 12 | Đóng gói: Dockerfile backend/web, nginx cùng origin, `deploy/server/compose.yaml` + `compose.demo.yaml` (broker và edge giả), `backup`/`restore` sh và ps1 (kiểm `pg_restore --list`, khôi phục vào CSDL riêng), CI GitHub Actions, README gốc; đã dựng và đăng nhập qua nginx, thấy dữ liệu edge giả, sao lưu và khôi phục 5 migration | Chưa thử trên Linux/clone sạch ở máy khác; chưa có video demo; chưa có HTTPS | Hoàn thiện bằng phần cứng thật |
| 2026-10-21 | 13 | Hai mục P1: xem trước MJPEG (`--preview-port`, mặc định tắt, nghe 127.0.0.1, chỉ mã hoá khi có người xem; 7 test, thử với clip thật) và OLED SSD1306 (số người `--` khi không biết, thời lượng cảnh báo, 4 test mới; build esp32dev và esp32dev_debug); edge 217 test, firmware 30 test | Chưa thử trên Pi, mạch OLED thật | Hoàn thiện bằng phần cứng thật |
| 2026-10-21 | 14 | Thiết kế lại giao diện: token màu sáng/tối, sidebar chữ (không icon) thu thành thanh dưới trên điện thoại, dòng trạng thái hệ thống cố định, thẻ vùng chờ đổi màu theo trạng thái, phông Fira nhúng trong bản build (chạy offline), biểu đồ theo token; 59 test vitest, kiểm bằng mắt trên Chrome (rộng/hẹp, sáng/tối, OVERLOAD) | Chưa kiểm tay bàn phím từng trang; chưa đo tương phản bằng công cụ | — |
| 2026-10-21 | 15 | Giao diện v2 cho quản lý trên laptop: sidebar tối có icon (lucide), thanh tiêu đề từng trang kèm trạng thái hệ thống và tài khoản, ô KPI màu (vùng chờ, vào, ra, thiết bị), biểu đồ vào/ra hôm nay ngay ở Tổng quan, nhãn trạng thái/ACK ở bảng cảnh báo, trang đăng nhập mới; 59 test; kiểm bằng mắt trên Chrome | Chưa kiểm chế độ tối ở v2, chưa thử trên điện thoại thật | — |
