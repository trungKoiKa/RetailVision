# Đánh giá

Kịch bản kiểm thử, cách gán nhãn và cách tính chỉ số. Ngưỡng đạt xem [1-requirements.md](../docs/1-requirements.md).

| Thư mục | Nội dung |
| --- | --- |
| `scenarios/` | Mô tả điều kiện từng clip/kịch bản |
| `ground_truth/` | Nhãn tay: ghi clip, buổi thu, người gán, phiên bản quy tắc gán nhãn |
| `benchmarks/` | Script và cấu hình đo |
| `results/` | Kết quả; chỉ commit bảng tổng hợp đã kiểm, gắn commit, model, `config_version` |

## Kịch bản kiểm thử

| ID | Kịch bản | Mong đợi |
| --- | --- | --- |
| T01 | Một người vào rồi ra | +1 vào, +1 ra |
| T02 | Đứng sát vạch, dao động | Không tăng liên tục |
| T03 | Hai người cùng chiều sát nhau | Ghi sai số thực tế |
| T04 | Hai người ngược chiều | Hai lượt đúng hướng hoặc ghi lỗi |
| T05 | Đi ngang vùng chờ dưới dwell | Không được tính |
| T06 | 5 người đủ dwell, giữ 59 giây | Không mở OVERLOAD |
| T07 | 5 người đủ dwell, giữ ≥60 giây | Mở một alert, đỏ + còi |
| T08 | Giảm còn 4 người | Vẫn OVERLOAD |
| T09 | ≤3 người liên tục ≥10 giây | END, xanh |
| T10 | Bấm ACK khi OVERLOAD | Lưu ACK, còi tắt, đỏ giữ |
| T11 | Rút webcam | UNKNOWN, không ghi queue = 0 |
| T12 | Dừng broker | Edge vẫn phân tích; ESP32 vàng |
| T13 | Tắt WAN, giữ LAN | Mọi chức năng chạy |
| T14 | Restart edge | Session mới, không lẫn ID cũ |
| T15 | Phát trùng sự kiện / settings request | Không ghi hoặc áp dụng hai lần |
| T16 | Gửi `off_count >= on_count` | Từ chối, giữ cấu hình cũ |
| T17 | Cắm lại camera / khởi động lại broker | Tự phục hồi hoặc log rõ |
| T18 | Chạy dài + refresh dashboard nhiều lần | Không mở thêm camera/model, RAM không tăng mãi |
| T19 | Người qua cửa khi vùng chờ đông | Cả hai nhánh chạy, sai số ghi riêng |
| T20 | Người xa, xe đẩy, thu ngân, lối đi ngang | Đo bỏ sót và báo nhầm |
| T21 | Qua ranh giới giờ/ngày, restart, gap, bản tin lặp | Báo cáo không trùng, gap rõ |
| T22 | Nhân viên ở vị trí khác bấm ACK rồi tới quầy | ACK đúng alert, không coi là hết đông |
| T23 | Vượt ngưỡng 59 giây, tụt, rồi vượt lại | Timer reset, không cộng dồn |
| T24 | Chặn bản tin ACK đầu tiên của ESP32 | Node gửi lại, Pi ghi một ACK |
| T25 | Tắt backend 5 phút, restart broker khi còn hàng đợi | Nhận đủ, không trùng |
| T26 | Reboot Pi không Internet | Giờ đồng bộ từ LAN hoặc `clock_synced=false` |

T01–T10, T14, T16, T23 có unit test bằng tọa độ/clock giả. Các test camera, mạng, mạch phải chạy tích hợp thật. Kết quả ghi CSV: `test_id, ngày, phiên bản, người kiểm, đầu vào, mong đợi, thực tế, pass/fail, đường dẫn bằng chứng`.

## Dữ liệu

- Chỉ quay người đã đồng ý; video không commit, giữ trong `data/raw/`.
- Tách dev (chỉnh tham số) và test (chỉ dùng một lần) **theo buổi/clip**, không trộn frame gần nhau.
- Mục tiêu: ≥24 clip (12 dev / 12 test); test có ≥100 lượt qua cửa, đủ tình huống âm tính (cảnh trống, đi ngang).
- Clip cảnh báo dài hơn dwell + hold và có cả đoạn kết thúc.
- Nhãn: lượt qua vạch (timestamp, hướng); số người vùng chờ theo mốc cố định, cùng quy tắc dwell; khoảng OVERLOAD suy ra từ nhãn đếm với cùng ngưỡng.

## Cách tính

| Chỉ số | Cách tính |
| --- | --- |
| Sai số đếm | Σ\|đếm − nhãn\| theo clip / tổng lượt thật, tính riêng từng hướng; clip 0 lượt báo số lượt đếm giả riêng |
| Queue MAE | Trung bình \|đoán − nhãn\| tại các mốc lấy mẫu |
| Precision / recall cảnh báo | Ghép mỗi alert dự đoán với tối đa một alert thật nếu thời điểm mở lệch ≤3 giây; thừa là FP, thiếu là FN. Chạy state machine trên chuỗi queue-count có nhãn và trên clip live profile demo; ghi rõ nguồn và cỡ mẫu |
| FPS | Số frame xử lý / thời gian thực, tách FPS model và FPS toàn luồng |
| Độ trễ | p95 ảnh → state và state → LED, đo bằng clock đã đồng bộ; không tính dwell/hold |

Mọi kết quả ghi kèm phần cứng, model, input size, `config_version`, ánh sáng, mật độ, nguồn live hay replay. Không dùng số đo laptop làm số đo Pi. Không đạt thì ghi số thật và phân tích nguyên nhân.

## Kịch bản demo (7–10 phút)

1. Nêu hai nhu cầu và phạm vi một cửa, một vùng chờ.
2. Chỉ camera, Pi + broker, ESP32, máy chủ.
3. Người qua vạch trong khi người khác đứng vùng chờ: hai chỉ số cùng cập nhật.
4. Tạo OVERLOAD (profile demo), đèn đỏ + còi; bấm ACK, còi tắt, đỏ giữ; giảm người → xanh.
5. Rút camera → UNKNOWN; tắt máy chủ → cảnh báo vẫn chạy; bật lại → dữ liệu được bù.
6. Mở báo cáo, coverage và bảng kết quả đo trên Pi. Video phát lại phải ghi rõ là phát lại.
