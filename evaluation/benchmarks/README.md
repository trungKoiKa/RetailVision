# Benchmark

`bench.py` chạy pipeline edge thật trên **cùng một clip** cho nhiều biến thể model (`.pt`, NCNN) và ghi mỗi biến thể một dòng CSV: FPS toàn luồng, FPS model, thời gian đọc/detect/phân tích (trung bình, p95), RAM, nhiệt CPU và cờ throttling. Clip ngắn hơn thời gian đo thì được lặp lại; 10 khung đầu bị bỏ (khởi động).

Nhiệt, throttling và RAM đọc từ `/sys`, `vcgencmd`, `/proc` nên chỉ có trên Pi; máy khác để trống (không bịa số). Luôn ghi `--note` (máy, OS, nguồn điện, nhiệt phòng).

## Trên Pi

```bash
# xuất model một lần (có thể trên laptop rồi chép sang)
python edge/experiments/export_ncnn.py --weights models/source/yolov8n.pt --imgsz 320
python edge/experiments/export_ncnn.py --weights models/source/yolov8n.pt --imgsz 416

sudo systemctl stop retail-edge
python evaluation/benchmarks/bench.py --config configs/examples/site01-video.yaml \
  --source data/raw/clip.mp4 --seconds 60 --out evaluation/results/bench.csv \
  --note "Pi4 4GB, Bookworm 64-bit, nguon chinh hang" \
  --variant pt320=models/source/yolov8n.pt:320 \
  --variant ncnn320=models/exported/yolov8n_ncnn_320/yolov8n_ncnn_model:320 \
  --variant ncnn416=models/exported/yolov8n_ncnn_416/yolov8n_ncnn_model:416
```

`evaluation/results/` không commit; chép số liệu cuối vào báo cáo kèm `config_version`.

## Cách đọc

- `fps_pipeline` là con số nghiệm thu NFR-01 (≥ 3 FPS toàn luồng). `fps_model` chỉ là phần suy luận.
- `loop_ms_p95` cho biết độ trễ xấu nhất của một khung; `throttled_any = True` thì số đo không còn đại diện (thiếu nguồn hoặc quá nhiệt).
- Cùng một clip, cùng `config_version` thì mới so sánh được giữa các biến thể.

## Chưa có số đo trên Pi

Chưa có dòng nào đo trên Raspberry Pi thật. Số liệu laptop chỉ dùng để kiểm công cụ, không đưa vào báo cáo.
