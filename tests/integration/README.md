# Integration tests

Các kịch bản ưu tiên:

1. Crossing lặp do MQTT QoS 1 chỉ tạo một bản ghi.
2. Spring chỉ PUBACK (manual ack) sau khi transaction commit.
3. Backend offline 5 phút rồi bật lại nhận đủ hàng đợi persistent session từ broker, không nhân đôi.
4. ACK sai hoặc lặp `alert_id` không đóng trạng thái OVERLOAD.
5. Camera/broker mất kết nối tạo UNKNOWN thay vì queue count bằng 0.

