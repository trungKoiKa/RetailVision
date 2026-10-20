# Triển khai trên Raspberry Pi

**Trạng thái kiểm chứng:** các file ở đây đã được kiểm cú pháp và nội dung bằng test trên laptop (`edge/tests/unit/test_deploy_files.py`). **Chưa chạy trên Pi thật.** Khi một bước lỗi, dán log lại thay vì sửa tay nhiều chỗ.

Thành phần: Mosquitto (xem [mosquitto/README.md](mosquitto/README.md)), edge Python chạy bằng systemd, chrony đồng bộ giờ từ máy chủ LAN.

## 1. Cài edge

```bash
git clone https://github.com/trungKoiKa/RetailVision.git && cd RetailVision
sudo bash deploy/pi/scripts/install_edge.sh
```

Script tạo người dùng `rv`, chép mã tới `/opt/retailvision`, tạo venv và cài `edge/requirements.txt` (kéo theo torch, mất vài phút), chép `edge.yaml` và `edge.env` mẫu (không ghi đè nếu đã có), đăng ký `retail-edge.service`.

Sau đó:

1. Đưa model NCNN vào `/opt/retailvision/models/` (xuất bằng `edge/experiments/export_ncnn.py` trên laptop hoặc trên Pi, rồi chép thư mục `yolov8n_ncnn_320/`). Đường dẫn trong `/etc/retailvision/edge.yaml` phải trỏ tới thư mục đó, và `model.image_size` phải bằng kích thước lúc xuất.
2. Sửa `/etc/retailvision/edge.env` (mật khẩu `edge01`), `chmod 600`.
3. Vẽ lại vạch và vùng chờ trong `edge.yaml` cho đúng khung hình camera thật.
4. `sudo systemctl start retail-edge` rồi `journalctl -u retail-edge -f`.

Kiểm cấu hình trước khi chạy: `/opt/retailvision/edge/.venv/bin/python -m retailvision.app --config /etc/retailvision/edge.yaml --check-config` (chạy trong `/opt/retailvision/edge`).

Nếu dịch vụ không khởi động được vì các dòng bảo vệ hệ thống (`ProtectSystem`, `ProtectHome`) trong `retail-edge.service`, bỏ các dòng đó và ghi lại lý do vào nhật ký.

## 2. Đồng bộ giờ (NFR-11, T26)

Pi không có đồng hồ phần cứng nên sau khi bật nguồn giờ có thể lệch xa. Cho Pi lấy giờ từ máy chủ LAN:

```bash
sudo apt install chrony
sudo cp deploy/pi/chrony/retailvision.conf /etc/chrony/conf.d/   # sửa <IP-MAY-CHU>
sudo systemctl restart chrony
bash deploy/pi/scripts/check_clock.sh                           # thoát 0 khi đã đồng bộ
```

Máy chủ LAN (laptop Windows) phải phục vụ NTP: bật Windows Time làm máy chủ và mở UDP 123 trong firewall. Đây là thay đổi cấu hình hệ thống nên bạn tự làm; mình chưa viết hướng dẫn từng bước vì chưa kiểm trên máy của bạn.

Khi chưa đồng bộ, edge báo `clock_synced=false` trong `status`.

## 3. Benchmark

Xem [evaluation/benchmarks/README.md](../../evaluation/benchmarks/README.md). Chạy sau khi dịch vụ đã dừng (`sudo systemctl stop retail-edge`) để không tranh CPU với camera thật.
