// Gửi ACK của nhân viên. PubSubClient chỉ publish QoS 0 nên ACK được gửi lặp CÙNG ack_id.
#pragma once

#include <stdint.h>

#include "alert_model.h"

namespace rv {

typedef void (*UuidFn)(char out[kUuidLen + 1]);

struct AckRequest {
  char ackId[kUuidLen + 1];
  char alertId[kUuidLen + 1];
};

class AckSender {
 public:
  AckSender(uint32_t repeatMs, uint8_t maxSends, UuidFn newUuid)
      : repeatMs_(repeatMs), maxSends_(maxSends), newUuid_(newUuid) {}

  // Nhấn nút. Chỉ có tác dụng khi OVERLOAD chưa ACK; nhấn tiếp khi đang gửi cho cùng alert thì bỏ qua
  // (giữ nguyên ack_id). Sau khi hết số lần mà chưa được ACK, nhấn lại sẽ tạo ack_id mới.
  void onButton(State state, bool acked, const char* alertId, uint32_t nowMs);

  // Gọi mỗi vòng lặp. Trả true khi tới lúc gửi (out đã điền). Tự dừng khi state báo acked, alert_id đổi,
  // không còn OVERLOAD hoặc đủ số lần.
  bool poll(State state, bool acked, const char* alertId, uint32_t nowMs, AckRequest& out);

  bool active() const { return active_; }

 private:
  uint32_t repeatMs_;
  uint8_t maxSends_;
  UuidFn newUuid_;
  bool active_ = false;
  uint8_t sends_ = 0;
  uint32_t nextMs_ = 0;
  char ackId_[kUuidLen + 1] = "";
  char alertId_[kUuidLen + 1] = "";
};

}  // namespace rv
