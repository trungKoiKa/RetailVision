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
  // `seq` của state hợp lệ gần nhất (dùng cho bản tin echo đo độ trễ). false nếu chưa có.
  bool lastSeq(uint32_t& out) const;
  // Số người ở vùng chờ theo state hợp lệ gần nhất. false khi UNKNOWN/quá timeout hoặc Pi gửi null: KHÔNG bao giờ trả 0 thay cho "không biết".
  bool queueCount(uint32_t nowMs, uint16_t& out) const;
  // Thời gian (ms, đồng hồ ESP32) kể từ khi ESP32 thấy trạng thái/cảnh báo hiện tại. 0 khi UNKNOWN.
  uint32_t stateAgeMs(uint32_t nowMs) const;

 private:
  uint32_t timeoutMs_;
  bool hasValid_ = false;
  uint32_t lastValidMs_ = 0;
  bool hasSeq_ = false;
  uint32_t seq_ = 0;
  State state_ = State::Unknown;
  bool acked_ = false;
  char alertId_[kUuidLen + 1] = "";
  bool hasCount_ = false;
  uint16_t count_ = 0;
  uint32_t sinceMs_ = 0;
};

}  // namespace rv
