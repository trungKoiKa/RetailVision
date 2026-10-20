# Backend (Spring Boot)

Nhận sự kiện từ Mosquitto, lưu PostgreSQL, cung cấp REST API. Java 21, Spring Boot 3.5, Flyway, Eclipse Paho, PostgreSQL 17.

**Trạng thái:** lát cắt Phần 6 (chưa đăng nhập, chưa báo cáo theo giờ, chưa đổi ngưỡng). 54 test xanh với PostgreSQL và Mosquitto thật; đã chạy thử cả chuỗi edge giả → Mosquitto → backend → PostgreSQL → API. Chưa chạy với Pi thật.

## Chạy

```bash
# PostgreSQL (ví dụ bằng Docker)
docker run -d --name rv-pg -e POSTGRES_DB=retailvision -e POSTGRES_USER=retailvision \
  -e POSTGRES_PASSWORD=<mat-khau> -p 5432:5432 postgres:17-alpine

cd backend
SPRING_DATASOURCE_PASSWORD=<mat-khau> RV_MQTT_HOST=<ip-broker> RV_MQTT_BACKEND_PASS=<mat-khau-backend01> \
  mvn spring-boot:run
```

Biến môi trường (mẫu ở `.env.example`): `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `RV_MQTT_HOST`, `RV_MQTT_PORT`, `RV_MQTT_BACKEND_USER`, `RV_MQTT_BACKEND_PASS`. Đổi cổng web bằng `SERVER_PORT` (mặc định 8080; nếu máy đã có gì dùng cổng này, backend báo "Port 8080 was already in use").

Flyway tạo bảng khi khởi động (V001–V003); Hibernate chỉ kiểm khớp schema (`ddl-auto=validate`).

## API

| Endpoint | Nội dung |
| --- | --- |
| `GET /api/overview` | Lượt vào/ra hôm nay (giờ Việt Nam), trạng thái hiện tại, cảnh báo gần nhất, thiết bị |
| `GET /api/alerts?page=&size=` | Cảnh báo mới nhất trước; `size` ≤ 100; có `ack_latency_seconds` |
| `GET /api/devices` | `edge01` và `node01`; chưa từng báo thì `status = UNKNOWN` |
| `GET /api/health` | Sức khoẻ của backend: DB và kết nối MQTT |

Dữ liệu cũ hoặc chưa có thì trả `UNKNOWN` và `null`, không trả 0: `live` chuyển UNKNOWN, `queue_count = null`, `stale = true` khi quá 5 giây chưa nhận `state` (tính theo giờ máy chủ lúc nhận, không tin đồng hồ Pi).

## Luồng nhận MQTT

```text
messageArrived → parse + kiểm contract → ghi DB (transaction) → commit → ack broker
```

- **Chống trùng:** `INSERT ... ON CONFLICT (event_id) DO NOTHING`; bản QoS 1 giao lại không tạo bản ghi mới. Telemetry còn chặn theo `(session_id, seq)`.
- **Bản tin sai** (không đúng contract, `site_id`/`device_id` không khớp topic): bỏ, ghi log, vẫn ack để không bị gửi lại mãi.
- **Lỗi hạ tầng tạm thời** (DB tắt...): không ack, ngắt kết nối rồi nối lại sau 5 giây để broker gửi lại. Paho chỉ gửi lại bản tin chưa ack khi nối lại.
- **Lỗi lặp lại vô ích** (ví dụ vi phạm ràng buộc DB): ghi log lỗi và ack, tránh vòng lặp vô hạn. Hệ quả: bản tin đó bị bỏ, phải đọc log để biết.
- **Backend tắt:** phiên `cleanSession=false` với client-id cố định `backend01`, broker giữ bản tin QoS 1 và giao khi nối lại (đã kiểm bằng test).
- `state` (QoS 0) chỉ vào bộ nhớ, không vào DB.
- Alert: mọi transition lưu ở `alert_transition`; `alert_event` gộp mỗi cảnh báo một dòng. ACK không đóng cảnh báo. ACK/END đến trước OPEN vẫn gộp đúng.

## Test

```bash
cd backend
mvn test
```

Cần Docker (PostgreSQL qua Testcontainers). Test MQTT tự bật Mosquitto cục bộ và bị bỏ qua nếu không tìm thấy; đặt `RV_MOSQUITTO_BIN` nếu cài ở chỗ khác. Ví dụ trong `contracts/examples` được dùng làm dữ liệu test.

Trong Git Bash trên Windows, `./mvnw` có thể lỗi khi tải Maven; dùng `mvn` đã cài, hoặc `mvnw.cmd` từ cmd/PowerShell.

## Giới hạn hiện tại

- Chưa có đăng nhập và phân quyền (Phần 10): chỉ dùng trong LAN tin cậy.
- `today.in/out` đếm theo sự kiện đã nhận; chưa kèm độ phủ quan sát nên chưa phân biệt "không có ai" với "edge tắt". Báo cáo theo giờ có `coverage` và `gap` thuộc Phần 10.
- `profile` trong overview lấy từ lượt qua vạch gần nhất (contract `state` không có trường này); chưa có lượt nào thì null.
- Chưa nhận topic `settings/result` và chưa gửi `settings/set` (đổi ngưỡng từ web, mức P1).
