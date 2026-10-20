# Quy trình thu clip đánh giá

**Trạng thái:** chưa có clip nào thuộc tập đánh giá. Công cụ đã sẵn sàng và được kiểm bằng dữ liệu dựng tay; số đo thật cần clip quay trên Pi. Clip VIRAT (`data/raw/clip2.mp4`) chỉ dùng để thử công cụ vì là cảnh ngoài trời, không phải cửa + vùng chờ.

## Trước khi quay

1. **Người tham gia đồng ý** bằng lời hoặc văn bản và biết video chỉ dùng cho đồ án; không quay người ngoài nhóm khi chưa có sự đồng ý (OQ-06). Video không commit, giữ ở `data/raw/`, xóa theo thời hạn đã chốt (OQ-04).
2. **Bố trí mặt bằng:** dán băng keo đánh dấu "cửa" (vạch đếm) và "vùng chờ" trên sàn trong cùng một góc nhìn của camera. Chụp một ảnh bằng `python -m retailvision.tools.record --snapshot data/raw/khung.jpg` ở đúng độ phân giải vận hành rồi vẽ vạch/vùng bằng `python -m retailvision.tools.calibrate --image data/raw/khung.jpg --config <cấu hình>` và dán đoạn YAML vào cấu hình. **Không đổi vị trí camera** giữa các clip của một buổi; đổi thì chụp và hiệu chuẩn lại, ghi thành buổi mới.
3. **Số người:** profile pilot cần ≥ 5 người cùng vùng chờ; profile demo cần 3. Chia vai trước để mỗi clip có kịch bản ghi sẵn.

## Quay

```bash
python -m retailvision.tools.record --out data/raw/buoi1_clip01.avi --seconds 120 --fps 15
```

Tên clip `buoiN_clipMM`. Video luôn đúng thời gian thực (khung được lặp khi camera chậm), kèm `buoiN_clipMM.json` (giờ bắt đầu UTC, độ phân giải thật, fps đo được). Ghi vào bảng bên dưới điều kiện từng clip.

## Chia tập dev/test

- Chia **theo buổi**, không theo clip: toàn bộ clip của một buổi nằm trong cùng một tập, để khung hình gần nhau không rơi vào cả hai tập.
- Tập **dev** dùng để chỉnh tham số (dwell, deadband, tracker, kích thước ảnh). Tập **test** chỉ chạy một lần sau khi đã chốt cấu hình; chỉnh lại theo kết quả test thì tập test hết giá trị.
- Mục tiêu: ≥ 24 clip (12 dev / 12 test); test có ≥ 100 lượt qua cửa; có cảnh trống và cảnh đi ngang để đo báo nhầm.

## Danh sách kịch bản cần quay

| Nhóm | Kịch bản | Số clip tối thiểu mỗi tập | Đo gì |
| --- | --- | --- | --- |
| Đếm | Một người vào/ra (T01), đứng sát vạch dao động (T02), hai người cùng chiều sát nhau (T03), ngược chiều (T04), quay đầu giữa chừng | 3 | Sai số đếm từng hướng, precision/recall theo thời gian |
| Âm tính | Cảnh trống; người đi ngang vùng chờ dưới dwell (T05); người đứng xa/ngoài vạch | 2 | Đếm nhầm ở clip trống |
| Vùng chờ | 0–8 người, thay đổi dần (T20); xe đẩy, thu ngân, lối đi ngang | 3 | MAE số người |
| Cảnh báo | Đủ người giữ < 60 s (T06), ≥ 60 s (T07), giảm còn 4 (T08), ≤ 3 đủ 10 s (T09), tụt rồi vượt lại (T23) — mỗi clip dài hơn dwell + hold và có đoạn kết thúc | 3 | Precision/recall cảnh báo |
| Hỗn hợp | Người qua cửa khi vùng chờ đông (T19) | 1 | Hai nhánh cùng lúc |

## Điều kiện từng clip (điền khi quay)

| Clip | Buổi | Tập | Ánh sáng | Mật độ (số người) | Nguồn (live/replay) | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

Nguồn **live** = chạy hệ thống trực tiếp trên camera; **replay** = chạy lại trên video đã quay. Đánh giá độ đúng thường dùng replay để lặp lại được; độ trễ và FPS phải đo **live** trên Pi.
