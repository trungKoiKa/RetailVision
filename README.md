# RetailVision

Nguyên mẫu IoT xử lý tại biên: một camera trên Raspberry Pi 4 đếm lượt vào/ra ở một cửa và phát hiện vùng chờ thanh toán đông kéo dài; ESP32 báo nhân viên bằng đèn/còi và nhận xác nhận; Spring Boot + PostgreSQL + React lưu và hiển thị báo cáo trong LAN.

**Trạng thái:** mã đã viết và kiểm bằng test tự động và chạy thử liên thông trên laptop (edge Python + Mosquitto + backend + PostgreSQL + web). **Chưa có số đo nào trên Pi, camera hay ESP32 thật**; xem mục Giới hạn. Tiến độ chi tiết ở [docs/3-plan.md](docs/3-plan.md).

```text
Camera → Pi 4 (YOLO + ByteTrack, đếm, cảnh báo, Mosquitto) ⇄ ESP32 (LED, còi, nút ACK)
                         ⇅ MQTT
              Spring Boot → PostgreSQL → React   (máy chủ LAN)
```

## Chạy thử không cần phần cứng

Cần Docker. Chạy cả máy chủ với broker và edge **giả lập** (kịch bản NORMAL → OVERLOAD → NORMAL):

```bash
cp deploy/server/.env.example deploy/server/.env
docker compose --env-file deploy/server/.env -f deploy/server/compose.yaml -f deploy/server/compose.demo.yaml up -d --build
```

Mở `http://localhost:8088`, đăng nhập `admin` / `change-me-admin` (giá trị mẫu trong `.env`). Số liệu trong chế độ này là giả lập, không phải đo từ camera. Dừng: `docker compose -p retailvision down -v`. Chi tiết, vận hành thật, sao lưu và khôi phục: [deploy/server/README.md](deploy/server/README.md).

Chạy từng thành phần để phát triển: [edge/](edge/README.md), [backend/](backend/README.md), [frontend/](frontend/README.md), [firmware/retail_alert/](firmware/retail_alert/README.md). Triển khai trên Pi: [deploy/pi/README.md](deploy/pi/README.md). CI (GitHub Actions) chạy test cả năm thành phần và kiểm Compose.

## Đọc theo thứ tự

| # | Tài liệu | Trả lời câu hỏi |
| --- | --- | --- |
| 1 | [docs/1-requirements.md](docs/1-requirements.md) | Làm gì, cho ai, thế nào là đạt |
| 2 | [docs/2-design.md](docs/2-design.md) | Hệ thống hoạt động thế nào |
| 3 | [docs/3-plan.md](docs/3-plan.md) | Làm gì trước, đang ở đâu |
| — | [docs/decisions/](docs/decisions/) | Vì sao chọn phương án này (đọc khi cần) |
| — | [contracts/mqtt/README.md](contracts/mqtt/README.md) | Topic và payload MQTT (khi viết code giao tiếp) |
| — | [evaluation/README.md](evaluation/README.md) | Kịch bản test và cách đo (khi kiểm thử) |
| — | [docs/report/](docs/report/) | Tài liệu viết báo cáo đồ án, không cần cho lập trình |

## Thư mục

| Thư mục | Nội dung |
| --- | --- |
| `edge/` | Python trên Pi: camera, phát hiện, tracking, đếm, cảnh báo, MQTT |
| `firmware/retail_alert/` | ESP32 (PlatformIO, Arduino) |
| `backend/` | Spring Boot, Flyway, REST |
| `frontend/` | React + TypeScript + Vite |
| `contracts/` | JSON Schema MQTT dùng chung |
| `configs/` | Cấu hình mẫu, không chứa bí mật |
| `deploy/` | Mosquitto, chrony, systemd cho Pi; Compose cho máy chủ |
| `evaluation/`, `data/`, `models/` | Đánh giá, dữ liệu nghiên cứu, trọng số (không commit file lớn) |

## Giới hạn

- Chưa đo trên Raspberry Pi 4 thật: FPS, độ chính xác đếm, độ trễ cảnh báo và các bài test phục hồi với camera/ESP32 thật vẫn là việc phải làm; không có con số nào được suy từ laptop.
- Chưa có tập clip và nhãn chính thức; `evaluation/` chỉ cung cấp công cụ.
- Màn hình OLED và xem trước MJPEG (P1) đã viết và test trên máy, chưa thử trên mạch/Pi thật. Web chạy HTTP trong LAN, chưa có HTTPS.
- Chỉ một cửa, một camera, một vùng chờ; không nhận diện danh tính, không lưu hay truyền video khi vận hành.

## Dữ liệu nghiên cứu

Một số clip VIRAT dùng để thử công cụ chỉ nhằm mục đích nghiên cứu, không được commit hay phân phối lại; xem điều khoản của bộ dữ liệu gốc.

## Quy ước chung

- Python venv đặt tại `edge/.venv`; đường dẫn trong YAML tính theo vị trí file YAML.
- Không commit `.env`, `secrets.h`, model, video, dữ liệu runtime.
- Lệnh chạy của từng thành phần được ghi vào README của thành phần đó khi đã chạy được.
