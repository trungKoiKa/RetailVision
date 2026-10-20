#include "ack_sender.h"

#include <string.h>

namespace rv {

void AckSender::onButton(State state, bool acked, const char* alertId, uint32_t nowMs) {
  if (state != State::Overload || acked || alertId == nullptr || alertId[0] == '\0') return;
  if (active_ && strcmp(alertId_, alertId) == 0) return;
  strncpy(alertId_, alertId, kUuidLen);
  alertId_[kUuidLen] = '\0';
  newUuid_(ackId_);
  sends_ = 0;
  nextMs_ = nowMs;  // gửi ngay lần đầu
  active_ = true;
}

bool AckSender::poll(State state, bool acked, const char* alertId, uint32_t nowMs, AckRequest& out) {
  if (!active_) return false;
  if (state != State::Overload || acked || alertId == nullptr || strcmp(alertId_, alertId) != 0 || sends_ >= maxSends_) {
    active_ = false;
    return false;
  }
  if (static_cast<int32_t>(nowMs - nextMs_) < 0) return false;
  sends_++;
  nextMs_ = nowMs + repeatMs_;
  memcpy(out.ackId, ackId_, sizeof(out.ackId));
  memcpy(out.alertId, alertId_, sizeof(out.alertId));
  return true;
}

}  // namespace rv
