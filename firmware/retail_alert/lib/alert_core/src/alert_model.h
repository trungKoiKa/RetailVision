// Mô hình trạng thái nhận từ topic `state` của Pi. Thuần: thời gian đi vào qua nowMs.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace rv {

enum class State : uint8_t { Unknown, Normal, Overload };

constexpr size_t kUuidLen = 36;
constexpr size_t kMaxStatePayload = 1024;

class AlertModel {
 public:
  explicit AlertModel(uint32_t timeoutMs) : timeoutMs_(timeoutMs) {}

  // Trả true nếu payload hợp lệ và đã áp dụng. Payload sai bị bỏ, KHÔNG bao giờ được coi là NORMAL:
  // trạng thái cũ giữ nguyên cho tới khi hết timeout rồi thành UNKNOWN.
  bool onStatePayload(const char* json, size_t len, uint32_t nowMs);

  // UNKNOWN khi chưa có state hợp lệ nào hoặc đã quá timeout kể từ state hợp lệ cuối.
  State state(uint32_t nowMs) const;
  // Chỉ có nghĩa khi OVERLOAD; ngoài ra trả false / chuỗi rỗng.
  bool acked(uint32_t nowMs) const;
  const char* alertId(uint32_t nowMs) const;

 private:
  uint32_t timeoutMs_;
  bool hasValid_ = false;
  uint32_t lastValidMs_ = 0;
  State state_ = State::Unknown;
  bool acked_ = false;
  char alertId_[kUuidLen + 1] = "";
};

}  // namespace rv
