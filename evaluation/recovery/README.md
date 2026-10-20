# Kiểm thử phục hồi lỗi (Phần 9)

Mỗi kịch bản T11–T26 trong [../README.md](../README.md) ghi rõ **đã kiểm tự động ở mức nào** và **còn gì phải làm trên phần cứng**. Kết quả tự động ở [automated_results.csv](automated_results.csv) (máy phát triển Windows, không phải Pi). Chưa có kết quả nào trên Pi thật.

| ID | Kịch bản | Đã kiểm tự động (laptop) | Còn phải làm trên phần cứng |
| --- | --- | --- | --- |
| T11 | Rút webcam | `test_camera_recovery.py`: alert mở bị kết thúc INTERRUPTED, state UNKNOWN với `queue_count = null` mỗi giây, không xen số đo 0, tự phục hồi khi có khung hình, tracker reset; camera chưa cắm lúc khởi động vẫn báo UNKNOWN; `CameraSource` tự mở lại sau lỗi đọc liên tiếp (camera giả) | Rút/cắm webcam thật; xem ESP32 vàng nháy |
| T12 | Dừng broker | `test_broker_recovery.py` (Mosquitto thật): edge vẫn phân tích không chậm; bản QoS 1 phát lúc mất broker được gửi sau khi nối lại | ESP32 chuyển vàng sau 5 s (firmware: test `AlertModel` timeout) |
| T13 | Tắt WAN, giữ LAN | `evaluation/tools/offline_check.py`: edge xử lý khung hình khi mọi kết nối ra ngoài bị chặn, không có lần nào cố gọi ra ngoài; web không nạp tài nguyên ngoài (`offline.test.ts`) | Rút cáp WAN trên Pi và máy chủ thật, chạy ≥ 10 phút |
| T14 | Restart edge | `test_t14_each_start_is_a_new_session`: mỗi lần chạy là session mới | Restart service thật, xem backend có session mới |
| T15 | Phát trùng sự kiện | `IngestionIT` và `MqttBrokerIT`: cùng `event_id` nhiều lần chỉ một dòng | (settings request thuộc Phần 10) |
| T17 | Cắm lại camera / restart broker | Như T11 và T12; backend: `BrokerRestartIT` (broker Docker restart khi backend chạy: tự nối lại, đăng ký lại, nhận tiếp), `LateBrokerIT` (backend chạy trước broker: DEGRADED rồi tự nối) | Thử với camera và broker thật trên Pi |
| T18 | Chạy dài + làm mới dashboard | `RefreshStressIT`: 1800 request song song không vượt hồ kết nối, không tăng luồng; `evaluation/tools/soak.py`: 150 s, 7225 khung, RAM phẳng (+0,2 MB), luồng không đổi | Soak ≥ 2 giờ rồi ≥ 4 giờ trên Pi (`soak.py`), có kèm dashboard mở |
| T22/T24 | ACK từ vị trí khác; mất ACK đầu | Firmware: `AckSender` gửi lặp cùng `ack_id`, dừng khi `acked`/đổi `alert_id`; edge: ACK chỉ nhận một lần cho đúng alert và không đóng OVERLOAD (`test_bridge.py`) | Bấm nút thật; chặn bản ACK đầu bằng ACL tạm (T24) |
| T25 | Tắt backend 5 phút, restart broker khi còn hàng đợi | `BrokerRestartIT` (Docker Mosquitto, persistence, SIGTERM): backend tắt, phát 5 bản, restart broker, backend bật lại nhận đủ 5, không trùng; `MqttOfflineIT`; `DbOutageIT`: DB sập thật, không ack, broker gửi lại, đủ và không trùng | Tắt backend 5 phút thật với dữ liệu thật từ Pi; đo giới hạn hàng đợi (OQ-04) |
| T26 | Reboot Pi không Internet | `test_health.py`: `clock_synced` đọc đúng, chưa đồng bộ thì báo `false` và schema hợp lệ | Reboot Pi thật không Internet với chrony; `deploy/pi/scripts/check_clock.sh` |

## Phát hiện trong quá trình kiểm (đã sửa)

1. **Camera chưa cắm lúc khởi động làm edge thoát** sau 10 giây và không bao giờ báo UNKNOWN. Nay vòng chạy camera (`run_camera_loop`) chịu được: báo UNKNOWN mỗi giây, tự bắt đầu khi có khung hình, dựng lại pipeline nếu độ phân giải thật khác cấu hình, reset tracker sau gián đoạn.
2. **Ultralytics gọi DNS ra Cloudflare/Google và gửi số liệu ẩn danh khi thấy mạng**, trái NFR-08/NFR-10. Nay `YOLO_OFFLINE=true` được đặt trong code và trong service systemd.
3. **Backend phục hồi chậm khi DB sập**: luồng nhận bản tin bị chặn nhiều giây trên từng bản tin nên ngắt/nối lại và gửi lại mất hàng chục giây. Nay có "cầu dao" (bản QoS 1 đến lúc đang chờ nối lại bị bỏ qua không ack, broker gửi lại), `socketTimeout` DB 10 s, `connectTimeout` 5 s.

## Chạy lại

```bash
cd edge && python -m pytest                      # gồm test_camera_recovery, test_broker_recovery, test_health
cd backend && mvn test                           # cần Docker; test MQTT cần mosquitto cục bộ
cd frontend && npm test
python evaluation/tools/offline_check.py --config configs/examples/site01-video.yaml --source <clip>
python evaluation/tools/soak.py --config configs/examples/site01-video.yaml --source <clip> --seconds 7200
```
