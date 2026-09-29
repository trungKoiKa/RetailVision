# Kế hoạch khởi tạo RetailVision

Kế hoạch này ưu tiên một lát cắt chạy được qua toàn hệ thống trước khi mở rộng giao diện
hoặc tối ưu model. Mỗi giai đoạn chỉ hoàn thành khi có bằng chứng kiểm thử tương ứng.

## Giai đoạn 1 - Edge

Mục tiêu: một tiến trình đọc camera/video, chạy detector/tracker một lần và tạo đầu ra dùng
chung cho đếm cửa lẫn vùng chờ.

1. Hoàn thiện parser và validation cho cấu hình camera, model, ROI, MQTT và spool.
2. Hiện thực capture giữ frame mới nhất, timestamp và reconnect.
3. Tạo adapter vision trả bbox/track ID theo tọa độ frame gốc.
4. Hiện thực crossing, queue dwell, alert hysteresis và UNKNOWN thành các state machine
   có unit test, không phụ thuộc camera.
5. Publish event có UUID/sequence; spool bounded và chỉ xóa sau storage ACK.
6. Đo `.pt` và NCNN trên Pi bằng cùng clip gán nhãn.

Điều kiện hoàn thành: chạy headless trên Pi; hai chức năng dùng chung camera/model/tracker;
test mốc biên đạt; log được FPS, freshness và lỗi; ngắt backend không làm mất cảnh báo.

## Giai đoạn 2 - Firmware

1. Chốt chân LED/nút và tạo bảng đấu nối.
2. Kết nối Wi-Fi/MQTT bằng tài khoản `node01` có ACL tối thiểu.
3. Hiện thực bốn trạng thái LED và timeout về UNKNOWN.
4. Chống dội nút; ACK chứa `ack_id`, `event_id`, `device_id` và timestamp.
5. Test reconnect, bản tin lặp, ACK sai event và mất broker.

Điều kiện hoàn thành: LED phản ánh đúng state; ACK lặp không gây hiệu ứng lặp; mất dữ liệu
quá hạn chuyển UNKNOWN trong thời gian đã cấu hình.

## Giai đoạn 3 - Backend

1. Mở rộng Flyway cho site, camera, session, queue sample, alert, ACK và config.
2. Validate payload theo `contracts/mqtt`, ghi idempotent trong transaction.
3. Phát storage ACK sau commit; không ACK dữ liệu bị từ chối.
4. Thêm login/JWT và kiểm quyền ADMIN/MANAGER tại API.
5. Tạo API overview, footfall, alerts, devices, config và CSV.
6. Test timezone `Asia/Ho_Chi_Minh`, replay, QoS 1 duplicate và coverage gap.

Điều kiện hoàn thành: migration chạy từ database rỗng; restart không nhân đôi dữ liệu;
API trái quyền bị từ chối; báo cáo giữ UNKNOWN/gap thay vì đổi thành 0.

## Giai đoạn 4 - Frontend

1. Tạo login và lớp API/auth dùng chung.
2. Xây Overview với freshness của camera/Pi/ESP32/backend.
3. Xây Footfall theo giờ/ngày kèm coverage và CSV.
4. Xây Alerts với vòng đời OPEN/ACK/END/INTERRUPTED.
5. Xây Settings/Devices; thay cấu hình hiển thị PENDING/APPLIED/REJECTED.
6. Bổ sung loading, empty, error, stale và unauthorized state.

Điều kiện hoàn thành: không còn dữ liệu mock trong nghiệm thu; frontend không truy cập
MQTT/PostgreSQL; refresh và token hết hạn được xử lý rõ ràng.

## Giai đoạn 5 - Tích hợp và triển khai

1. Kiểm tra JSON Schema và OpenAPI trong CI.
2. Tự động hóa integration test với Mosquitto/PostgreSQL tạm thời.
3. Hoàn thiện systemd, Mosquitto ACL, Dockerfile/Compose và backup/restore.
4. Chạy thử tắt backend, broker, camera, ESP32 và reboot Pi.
5. Chạy bench 30 phút rồi 2-4 giờ; lưu FPS, p95 latency, RAM, nhiệt và coverage.
6. Đóng băng phiên bản Pi, Java, Node, database, model và cấu hình dùng cho demo.

Điều kiện hoàn thành: máy mới có thể triển khai theo tài liệu; reboot tự phục hồi; dữ liệu
replay không trùng; mọi yêu cầu nghiệm thu có log, bảng đo hoặc video làm bằng chứng.

## Thứ tự pull request/commit đề xuất

1. `edge/config-capture`
2. `edge/vision-state-machines`
3. `firmware/mqtt-alert-ack`
4. `backend/schema-mqtt-ingestion`
5. `backend/auth-reporting-api`
6. `frontend/auth-overview`
7. `frontend/reports-alerts-settings`
8. `integration/replay-failure-tests`
9. `deploy/pi-server-pilot`

