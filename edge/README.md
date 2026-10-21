# Edge (Python trên Raspberry Pi)

Pipeline: khung hình → YOLOv8n + ByteTrack → đếm vạch, vùng chờ, cảnh báo → sự kiện JSONL.

## Cài môi trường (Windows, đã kiểm chứng)

```bash
cd edge
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt   # chạy test (không cần ultralytics)
.venv/Scripts/python.exe -m pip install "ultralytics==8.3.*"
```

Trọng số `yolov8n.pt` đặt ở `models/source/` (không commit). Tải bằng:

```bash
cd ../models/source
../../edge/.venv/Scripts/python.exe -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

## Kiểm tra cấu hình

```bash
cd edge
.venv/Scripts/python.exe -m retailvision.app --config ../configs/examples/site01-video.yaml --check-config
```

## Chạy trên video và xem tracking

```bash
cd edge
.venv/Scripts/python.exe -m retailvision.app --config <file-cau-hinh.yaml> --source <video.mp4> \
    --events-out <ket-qua.jsonl> --video-out <video-da-ve.mp4>
```

- `--video-out`: video có vạch (vàng), vùng chờ (xanh dương), khung người và ID tracking (xanh lá), cùng dòng trạng thái ở góc trên.
- `--events-out`: sự kiện JSONL (lượt IN/OUT, số người vùng chờ mỗi giây, cảnh báo).

- `--preview-port N`: xem trước MJPEG (`http://127.0.0.1:N/`, ảnh tĩnh ở `/snapshot.jpg`) khi chạy file hoặc camera; mặc định tắt, không có cổng nào mở. Chỉ nghe máy này; xem từ máy khác trong LAN cần `--preview-host 0.0.0.0` (ai trong LAN cũng thấy hình). Chỉ mã hoá JPEG khi có người xem, ảnh không ghi đĩa. Dùng để hiệu chuẩn/demo, không bật khi vận hành.

Tọa độ vạch và vùng trong file cấu hình là 0–1 theo khung hình. Phải chỉnh lại theo đúng video trước khi đọc số đếm.

## Kiểm thử

```bash
cd edge
.venv/Scripts/python.exe -m pytest
```

## Số đo (laptop, không phải Pi)

- Trên đoạn 60 giây (1798 khung, 1920×1080), YOLOv8n `imgsz=320`, CPU: khoảng 30 khung/giây cho toàn pipeline.

## Cấu hình hiện tại cho video thử (`site01-video.yaml`)

- `imgsz: 1280`: 640 và 320 bỏ sót người nhỏ gần vạch.
- Tracker `configs/edge/bytetrack-tuned.yaml`: `track_buffer: 90`, `match_thresh: 0.9`. Lưu ý: `match_thresh` là khoảng cách tối đa (1 − IoU) để ghép, giá trị cao hơn nghĩa là ghép dễ hơn.
- Đếm qua vạch có ghép ID: track mất gần vạch rồi xuất hiện ở phía bên kia trong 2 giây được tính một lượt (`reassoc_px=80`, `reassoc_window_s=2`).

Số đo trên đoạn 60 giây (1798 khung), laptop CPU, không có nhãn đúng sai nên chỉ là chỉ số gián tiếp:

| Cấu hình | ID khác nhau | ID mới gần vạch | ID mất gần vạch |
|---|---|---|---|
| 1280, tracker mặc định | 41 | 5 | 4 |
| 1280, tracker đã chỉnh (`match_thresh` 0.7, sai hướng) | 75 | 15 | 16 |
| 1280, tracker đã chỉnh (`match_thresh` 0.9) | 13 | 1 | 1 |

Kết quả đếm cuối cùng trên đoạn này: 3 lượt IN, 0 OUT. Chưa đối chiếu với nhãn tay nên chưa biết đúng bao nhiêu.

## Gửi MQTT

Thêm mục `mqtt:` (host, port) vào file cấu hình; không có mục này thì edge chạy không gửi gì. Tài khoản lấy từ `RV_MQTT_USER`, `RV_MQTT_PASS`. Tắt tạm bằng `--no-mqtt`.

```bash
RV_MQTT_USER=edge01 RV_MQTT_PASS=... python -m retailvision.app --config <file.yaml> --source <video.mp4>
```

Edge gửi `state` (QoS 0, mỗi giây), `events/crossing`, `events/alert`, `telemetry` (mỗi phút) và `status` (retained, kèm Last Will); nhận `operator-ack` từ ESP32. Đã kiểm trên Windows với Mosquitto 2.1.2 thật; chưa chạy trên Pi.

Khi nối lại sau mất mạng, paho giữ tối đa 5000 bản tin QoS 1 trong RAM; edge tắt đột ngột thì phần chưa gửi bị mất.

### Đổi ngưỡng từ web (P1)

Edge nghe `settings/set` (QoS 1) và trả `settings/result`. Quy tắc: áp dụng nguyên bộ hoặc từ chối; lệnh dựa trên revision cũ bị từ chối; cùng `request_id` giao lại thì trả lại đúng kết quả cũ và không áp dụng lần hai; giá trị sai (ví dụ `off_count >= on_count`) thì giữ cấu hình hiện tại. Cảnh báo đang mở kết thúc với `CONFIG_CHANGED`. Ngưỡng và revision đã áp dụng được lưu ở `settings_file` trong file cấu hình và nạp lại khi khởi động (file hỏng thì dùng giá trị trong cấu hình). `state` luôn báo `settings_revision` hiện tại.

### Giả lập edge (thử ESP32/backend khi chưa có camera)

```bash
python -m retailvision.tools.fake_publisher --scenario overload --hold 30 --period 60
python -m retailvision.tools.fake_publisher --scenario overload --dry-run --seconds 12   # chỉ in, không kết nối
```

Kịch bản: `normal`, `crossings`, `overload`, `unknown`. Đang OVERLOAD mà nhận `operator-ack` đúng `alert_id` thì đặt `acked=true` và gửi sự kiện ACK; cảnh báo vẫn kéo dài hết `--hold`.

### Test

`python -m pytest` chạy cả `tests/integration/test_mqtt_broker.py`, tự bật Mosquitto cục bộ (cổng ngẫu nhiên, không tài khoản) và bỏ qua nếu không tìm thấy `mosquitto`. Đặt `RV_MOSQUITTO_BIN` nếu cài ở chỗ khác.
