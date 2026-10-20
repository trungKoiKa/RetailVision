// Ánh xạ trạng thái -> đèn và còi (docs/2-design.md mục 2.7) và mức chân theo thời gian.
#pragma once

#include <stdint.h>

#include "alert_model.h"

namespace rv {

enum class LedMode : uint8_t { Off, On, Blink };

struct Outputs {
  LedMode red;
  LedMode green;
  LedMode yellow;
  bool buzzer;
};

// UNKNOWN: vàng nháy. NORMAL: xanh sáng. OVERLOAD chưa ACK: đỏ nháy + còi. OVERLOAD đã ACK: đỏ sáng.
Outputs outputsFor(State state, bool acked);

// Mức chân của LED ở thời điểm nowMs (nháy đều theo nửa chu kỳ halfPeriodMs).
bool ledLevel(LedMode mode, uint32_t nowMs, uint32_t halfPeriodMs);

// Mức chân còi: kêu onMs rồi nghỉ offMs, lặp lại.
bool buzzerLevel(bool active, uint32_t nowMs, uint32_t onMs, uint32_t offMs);

}  // namespace rv
