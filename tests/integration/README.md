# Integration tests

Các kịch bản ưu tiên:

1. Crossing lặp do MQTT QoS 1 chỉ tạo một bản ghi.
2. Spring chỉ gửi storage ACK sau khi transaction commit.
3. Edge replay spool sau khi server phục hồi mà không nhân đôi dữ liệu.
4. ACK sai hoặc lặp `event_id` không đóng trạng thái OVERLOAD.
5. Camera/broker mất kết nối tạo UNKNOWN thay vì queue count bằng 0.

