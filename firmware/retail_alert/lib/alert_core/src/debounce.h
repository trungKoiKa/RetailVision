// Chống dội nút: phát một lần cho mỗi lần nhấn (cạnh xuống đã ổn định).
#pragma once

#include <stdint.h>

namespace rv {

class Debouncer {
 public:
  explicit Debouncer(uint32_t stableMs) : stableMs_(stableMs) {}

  // rawDown: trạng thái đọc thô (true = đang nhấn). Trả true đúng một lần khi nhấn ổn định.
  bool pressed(bool rawDown, uint32_t nowMs);

 private:
  uint32_t stableMs_;
  bool raw_ = false;
  bool stable_ = false;
  uint32_t since_ = 0;
};

}  // namespace rv
