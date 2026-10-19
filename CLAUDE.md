# RetailVision — hướng dẫn cho AI

Đồ án IoT: một camera USB trên Raspberry Pi 4 đếm lượt vào/ra qua một cửa và phát hiện vùng chờ đông kéo dài; ESP32 (LED, còi, nút ACK) báo nhân viên; Spring Boot + PostgreSQL + React trên máy chủ LAN lưu và hiển thị báo cáo.

## Đọc trước khi làm

1. `docs/1-requirements.md`: làm gì, thế nào là đạt.
2. `docs/2-design.md`: hệ thống hoạt động thế nào.
3. `docs/3-plan.md`: đang ở phần nào, bước tiếp theo.
4. `docs/decisions/`: lý do chọn phương án, chỉ đọc khi cần.

Chỉ sửa trong phạm vi được giao. Nếu cần đổi `contracts/` hoặc đổi kiến trúc đã chốt: dừng lại và hỏi.

## Quy tắc bắt buộc

- `contracts/` là nguồn sự thật cho mọi bản tin MQTT. Code bám schema, không tự thêm trường.
- Mất dữ liệu thì trả `UNKNOWN` hoặc `null`, **không bao giờ** trả 0.
- ACK của nhân viên không đóng OVERLOAD. ACK chỉ có tác dụng với đúng `alert_id` đang mở.
- Thời gian lưu và truyền là ISO 8601 UTC. `Asia/Ho_Chi_Minh` chỉ dùng khi hiển thị và tổng hợp báo cáo.
- Bản tin QoS 1 có thể giao trùng: chống trùng bằng khóa unique `event_id`. Backend chỉ PUBACK sau khi commit.
- `settings` là ngưỡng sửa từ web, có trạng thái PENDING/APPLIED/REJECTED. `config_version` là profile kỹ thuật của edge. Không lẫn hai khái niệm.
- Không lưu hay truyền video ở chế độ vận hành. Track ID chỉ tồn tại trong RAM.
- Không commit `.env`, `secrets.h`, model, video, dữ liệu thô. Cấu hình mẫu đặt ở `configs/examples/`.
- Không dùng số liệu giả trong nghiệm thu. Không bịa số đo FPS, độ chính xác hay độ trễ.

## Kiểm tra trước khi commit

- JSON: `npx prettier@3 --check "**/*.json"`. Định dạng lại bằng `--write`.
- Contract: `python contracts/validate.py`.
- Edge: `cd edge && python -m pytest`.

Mỗi module có thể có `CLAUDE.md` riêng khi có quy ước riêng (ví dụ firmware).
