# Backend (Spring Boot)

Nhận sự kiện từ Mosquitto, lưu PostgreSQL, cung cấp REST API. Java 21, Spring Boot 3.5, Flyway, Eclipse Paho, PostgreSQL 17.

**Trạng thái:** Phần 6 (nhận MQTT, lưu DB) và Phần 10a (đăng nhập, phân quyền, báo cáo giờ/ngày, CSV). 84 test xanh với PostgreSQL, Mosquitto thật (và Docker cho các ca phục hồi lỗi). Chưa có đổi ngưỡng từ web (Phần 10b). Chưa chạy với Pi thật.

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
| `GET /api/health` | Sức khoẻ của backend: DB và kết nối MQTT (công khai) |
| `GET/PUT /api/settings` | Xem và đổi ngưỡng vận hành (P1). PUT trả 202; kết quả APPLIED/REJECTED đến sau từ edge |
| `GET /api/footfall?from=&to=&granularity=hour\|day` | Lượt vào/ra theo giờ hoặc ngày (giờ Việt Nam) kèm `coverage`, `gap`, số cảnh báo, phút OVERLOAD, số người trung bình/lớn nhất |
| `GET /api/reports/export.csv?from=&to=&granularity=` | CSV cùng số liệu; ô không có dữ liệu để trống |
| `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `POST /api/auth/password` | Đăng nhập/đăng xuất, thông tin tài khoản, đổi mật khẩu |
| `GET/POST /api/users`, `PATCH /api/users/{id}` | Quản lý tài khoản (chỉ ADMIN): tạo, đổi vai trò, vô hiệu hóa, đặt lại mật khẩu |

Dữ liệu cũ hoặc chưa có thì trả `UNKNOWN` và `null`, không trả 0: `live` chuyển UNKNOWN, `queue_count = null`, `stale = true` khi quá 5 giây chưa nhận `state` (tính theo giờ máy chủ lúc nhận, không tin đồng hồ Pi).

## Đăng nhập và phân quyền

- Session cookie `RVSESSION` (HttpOnly, SameSite=Lax), hết hạn sau 8 giờ. CSRF bằng cookie `XSRF-TOKEN` + header `X-XSRF-TOKEN` cho mọi request ghi (cookie được gửi ngay cả ở phản hồi 401: SPA gọi `GET /api/auth/me` trước khi đăng nhập).
- Vai trò `ADMIN` và `MANAGER` kiểm ở API (không chỉ ẩn nút trên web). Chưa đăng nhập: 401 JSON; sai quyền: 403 JSON. Chỉ `/api/health` công khai.
- Mật khẩu lưu BCrypt; thông báo lỗi đăng nhập giống nhau cho tên không tồn tại và sai mật khẩu; sai 5 lần trong 10 phút khoá tên đó 5 phút (RAM, mất khi restart). Đăng nhập đổi session id (chống fixation).
- Tài khoản ADMIN đầu tiên tạo từ `RV_ADMIN_USER` / `RV_ADMIN_PASS` khi bảng `app_user` rỗng. Không có tài khoản nào thì backend ghi cảnh báo vào log.
- Không xóa tài khoản, chỉ vô hiệu hóa. Luôn còn ít nhất một ADMIN đang hoạt động; không tự vô hiệu hóa chính mình.
- Cookie chưa bật `Secure` vì LAN dùng HTTP; bật khi phục vụ HTTPS (`server.servlet.session.cookie.secure`).

## Đổi ngưỡng (P1)

`PUT /api/settings` lưu yêu cầu PENDING rồi gửi `settings/set` kèm `expected_settings_revision` (lấy từ state mới nhất của edge) và giữ PENDING tới khi edge trả `settings/result`. Backend không tự coi ngưỡng đã có hiệu lực: chỉ edge xác nhận.

- Chỉ gửi được khi có state mới (không cũ) của edge và không có yêu cầu nào đang chờ (409 nếu không); MQTT tắt thì 503; giá trị sai thì 400 (`off_count < on_count`, các khoảng theo contract).
- Quá `retailvision.settings-timeout-seconds` (30 s) chưa có trả lời: hiện `UNCONFIRMED`, không coi là đã áp dụng; câu trả lời đến muộn vẫn cập nhật đúng yêu cầu đó. Kết quả trùng không ghi đè.
- `current` là ngưỡng của lần APPLIED gần nhất; `null` nghĩa là chưa từng đổi từ web (edge dùng giá trị trong file cấu hình của nó).

## Báo cáo

Bucket theo giờ (≤ 7 ngày) hoặc ngày (≤ 366 ngày), mốc theo `Asia/Ho_Chi_Minh`. Thiếu dữ liệu không thành 0:

- `gap = true`: bucket đã qua hoặc đang diễn ra mà không có telemetry nào; `in`/`out` là `null` nếu cũng không có lượt qua vạch nào (có lượt thì vẫn báo số đó, vì đó là cận dưới).
- `future = true`: chưa tới giờ đó, mọi số liệu `null`.
- `coverage` = giây quan sát hợp lệ / giây đáng ra có (bucket đang diễn ra chỉ tính phần đã trôi qua). `queue_avg` có trọng số theo giây hợp lệ, bỏ phút không có số người.
- Phút OVERLOAD chia theo giờ; cảnh báo còn mở tính tới hiện tại. Edge restart (session mới, `seq` bắt đầu lại) vẫn cộng đúng.

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

- `today.in/out` trong `/api/overview` đếm theo sự kiện đã nhận, chưa kèm độ phủ; xem độ phủ ở `/api/footfall`.
- `profile` trong overview lấy từ lượt qua vạch gần nhất (contract `state` không có trường này); chưa có lượt nào thì null.
- Chưa nhận topic `settings/result` và chưa gửi `settings/set` (đổi ngưỡng từ web, mức P1).
