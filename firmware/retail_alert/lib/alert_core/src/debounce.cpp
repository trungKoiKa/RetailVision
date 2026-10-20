#include "debounce.h"

namespace rv {

bool Debouncer::pressed(bool rawDown, uint32_t nowMs) {
  if (rawDown != raw_) {
    raw_ = rawDown;
    since_ = nowMs;
    return false;
  }
  if (raw_ != stable_ && static_cast<uint32_t>(nowMs - since_) >= stableMs_) {
    stable_ = raw_;
    return stable_;  // chỉ cạnh nhấn, không phát khi nhả
  }
  return false;
}

}  // namespace rv
