# RetailVision

Repository hiện là bộ khung thư mục cho nguyên mẫu IoT giám sát lưu lượng khách tại
biên. Chưa có mã ứng dụng hoặc cấu hình triển khai hoàn chỉnh.

## Thành phần

- `edge/`: Python chạy trên Raspberry Pi.
- `firmware/`: firmware ESP32.
- `backend/`: Spring Boot, MQTT consumer, REST API và PostgreSQL.
- `frontend/`: React + TypeScript + Vite.
- `contracts/`: nơi dự kiến đặt hợp đồng MQTT và OpenAPI dùng chung.
- `configs/`: cấu hình mẫu, không chứa bí mật.
- `evaluation/`: ground truth, benchmark và kết quả đánh giá.
- `deploy/`: cấu hình triển khai Pi và máy chủ LAN.
- `docs/`: đặc tả, kế hoạch và hướng dẫn triển khai.

Đọc [kế hoạch khởi tạo](docs/KE_HOACH_KHOI_TAO.md) trước khi bắt đầu lập trình.

## Nguyên tắc khi bắt đầu hiện thực

- Virtual environment của Python luôn đặt tại `edge/.venv`.
- Đường dẫn trong YAML được phân giải tương đối với chính file YAML.
- Model lớn, dữ liệu thô, bí mật và dữ liệu runtime không được commit.
- Pi, backend và ESP32 sẽ trao đổi theo schema được chốt trong `contracts/mqtt/`.
