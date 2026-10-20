// Dựng bản tin gửi đi theo contracts/mqtt. Các chuỗi truyền vào là hằng của firmware nên không escape JSON.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "alert_model.h"

namespace rv {

// UUID v4 từ 16 byte ngẫu nhiên (đặt bit version/variant). out có kUuidLen + 1 byte.
void formatUuidV4(const uint8_t bytes[16], char out[kUuidLen + 1]);

// "YYYY-MM-DDTHH:MM:SS.mmmZ" (UTC). out có 25 byte.
constexpr size_t kIsoLen = 24;
void formatIsoUtc(int64_t epochSeconds, uint16_t millis, char out[kIsoLen + 1]);

// {"ack_id","alert_id","device_id"} cho node01/events/operator-ack (không có envelope). Trả 0 nếu cap không đủ.
size_t buildAckJson(char* out, size_t cap, const char* ackId, const char* alertId, const char* deviceId);

struct StatusFields {
  const char* siteId;
  const char* deviceId;
  const char* sessionId;
  const char* configVersion;
  const char* version;
  const char* status;      // "ONLINE" | "OFFLINE"
  const char* eventId;
  uint32_t seq;
  const char* occurredAt;  // kết quả formatIsoUtc
  bool clockSynced;
};

// Bản tin node01/status có envelope đầy đủ. Trả 0 nếu cap không đủ.
size_t buildStatusJson(char* out, size_t cap, const StatusFields& f);

}  // namespace rv
