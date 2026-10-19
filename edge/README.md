# Edge (Python trên Raspberry Pi)

Pipeline: khung hình → YOLOv8n + ByteTrack → đếm vạch, vùng chờ, cảnh báo → sự kiện JSONL.

## Cài môi trường (Windows, đã kiểm chứng)

```bash
cd edge
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-dev.txt
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

Tọa độ vạch và vùng trong file cấu hình là 0–1 theo khung hình. Phải chỉnh lại theo đúng video trước khi đọc số đếm.

## Kiểm thử

```bash
cd edge
.venv/Scripts/python.exe -m pytest
```

## Số đo (laptop, không phải Pi)

- Trên đoạn 60 giây (1798 khung, 1920×1080), YOLOv8n `imgsz=320`, CPU: khoảng 30 khung/giây cho toàn pipeline.
