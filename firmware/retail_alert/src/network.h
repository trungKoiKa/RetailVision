// Wi-Fi + MQTT chạy trên một task riêng (core 0) để việc nối lại, vốn có thể chặn vài giây,
// không làm đứng LED, còi và nút ở loop() (core 1).
#pragma once

#include <Arduino.h>

#include "alert_model.h"

// Bắt đầu task mạng. `model` được cập nhật từ task này, mọi truy cập phải giữ `mutex`.
void networkStart(rv::AlertModel* model, SemaphoreHandle_t mutex);

// Xếp một ACK vào hàng đợi gửi. Không chặn; hàng đợi đầy hoặc đang mất kết nối thì bỏ
// (AckSender sẽ gửi lại cùng ack_id sau 1 giây). Trả false nếu bị bỏ.
bool networkSendAck(const char* ackId, const char* alertId);

// UUID v4 từ bộ tạo số ngẫu nhiên phần cứng.
void randomUuid(char out[rv::kUuidLen + 1]);
