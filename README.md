# RetailVision

Nguyên mẫu IoT xử lý tại biên: một camera trên Raspberry Pi 4 đếm lượt vào/ra ở một cửa và phát hiện vùng chờ thanh toán đông kéo dài; ESP32 báo nhân viên bằng đèn/còi và nhận xác nhận; Spring Boot + PostgreSQL + React lưu và hiển thị báo cáo trong LAN.

**Trạng thái:** đã chốt thiết kế, chưa có mã ứng dụng. Tiến độ xem [docs/3-plan.md](docs/3-plan.md).

```text
Camera → Pi 4 (YOLO + ByteTrack, đếm, cảnh báo, Mosquitto) ⇄ ESP32 (LED, còi, nút ACK)
                         ⇅ MQTT
              Spring Boot → PostgreSQL → React   (máy chủ LAN)
```

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

## Quy ước chung

- Python venv đặt tại `edge/.venv`; đường dẫn trong YAML tính theo vị trí file YAML.
- Không commit `.env`, `secrets.h`, model, video, dữ liệu runtime.
- Lệnh chạy của từng thành phần được ghi vào README của thành phần đó khi đã chạy được.
