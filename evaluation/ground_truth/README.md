# Nhãn tay và manifest

Nhãn là sự thật chuẩn để chấm hệ thống. Ghi rõ **ai gán, ngày nào, theo quy tắc phiên bản nào**; nhãn do một người gán nên nên có người thứ hai kiểm một phần (ghi tỷ lệ bất đồng nếu có).

## Quy tắc gán nhãn (phiên bản 1)

- **Lượt qua vạch:** ghi thời điểm chân người chạm vạch và hướng (`IN` = đi theo chiều mũi tên trong `calibrate` / `a_to_b_direction`). Người chỉ chạm vạch rồi quay lại phía cũ không tính. Hai người đi sát nhau là hai lượt.
- **Số người vùng chờ:** tại mỗi mốc cố định (mặc định mỗi 5 giây; clip dùng để chấm cảnh báo nên dùng 2 giây), đếm người có chân trong đa giác vùng chờ **và đã ở đó ≥ dwell** (mặc định 2 giây). Người đi ngang chưa đủ dwell không được đếm. Số người chưa chắc chắn thì xem lại video, không đoán.
- **Cảnh báo thật** không gán tay: suy ra từ nhãn số người bằng chính máy trạng thái của edge và cùng ngưỡng (hai bên cùng một quy tắc).

## Công cụ

```bash
# lượt qua vạch (phím i/o, u hoàn tác, q lưu)
python evaluation/tools/label.py --video data/raw/buoi1_clip01.avi --out evaluation/ground_truth/buoi1_clip01_cross.csv --config <cấu hình>
# số người vùng chờ theo mốc (gõ số + Enter)
python evaluation/tools/label_queue.py --video data/raw/buoi1_clip01.avi --out evaluation/ground_truth/buoi1_clip01_queue.csv --config <cấu hình> --step 5
# chạy hệ thống trên clip, ghi sự kiện
python -m retailvision.app --config <cấu hình> --source data/raw/buoi1_clip01.avi --no-mqtt --events-out evaluation/results/buoi1_clip01.jsonl
```

Định dạng: `*_cross.csv` có cột `ts,direction` (giây từ đầu clip, `IN`/`OUT`); `*_queue.csv` có cột `ts,count`; `*.jsonl` là sự kiện của `retailvision.app` (crossing, queue mỗi giây, alert).

## Manifest

`evaluation/ground_truth/manifest.csv` liệt kê clip để `evaluation/evaluate.py` tổng hợp. Đường dẫn tính từ thư mục chứa manifest. Không commit manifest chứa clip chưa có sự đồng ý; manifest và nhãn không chứa hình ảnh nên commit được.

| Cột | Ý nghĩa |
| --- | --- |
| `clip_id` | Duy nhất, ví dụ `buoi1_clip01` |
| `split` | `dev` hoặc `test` (chia theo buổi) |
| `events` | File JSONL kết quả chạy hệ thống |
| `gt_crossings` | Nhãn lượt qua vạch (để trống nếu clip không gán) |
| `gt_queue` | Nhãn số người vùng chờ (để trống nếu không gán) |
| `hardware`, `model`, `imgsz`, `config_version` | Điều kiện chạy; luôn điền |
| `lighting`, `density` | Ánh sáng, mật độ người |
| `source` | `live` hoặc `replay` |
| `alert_on_count`, `alert_on_hold`, `alert_off_count`, `alert_off_hold` | Ngưỡng cảnh báo dùng khi suy ra cảnh báo thật (mặc định 5 / 60 / 3 / 10) |

```bash
python evaluation/evaluate.py --manifest evaluation/ground_truth/manifest.csv \
  --out evaluation/results/report.md --csv evaluation/results/summary.csv
```

## Nhãn hiện có

[virat_60s.csv](virat_60s.csv) (xem [virat_60s.md](virat_60s.md)): 3 lượt IN trên đoạn VIRAT 60 s, **do AI ước lượng, chưa kiểm độc lập**, chỉ dùng để thử công cụ. Chưa có nhãn nào cho tập đánh giá chính thức.
