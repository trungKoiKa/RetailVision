#include "outputs.h"

namespace rv {

Outputs outputsFor(State state, bool acked) {
  switch (state) {
    case State::Normal:
      return {LedMode::Off, LedMode::On, LedMode::Off, false};
    case State::Overload:
      if (acked) return {LedMode::On, LedMode::Off, LedMode::Off, false};
      return {LedMode::Blink, LedMode::Off, LedMode::Off, true};
    case State::Unknown:
    default:
      return {LedMode::Off, LedMode::Off, LedMode::Blink, false};
  }
}

bool ledLevel(LedMode mode, uint32_t nowMs, uint32_t halfPeriodMs) {
  switch (mode) {
    case LedMode::On:
      return true;
    case LedMode::Blink:
      return halfPeriodMs != 0 && (nowMs / halfPeriodMs) % 2 == 0;
    case LedMode::Off:
    default:
      return false;
  }
}

bool buzzerLevel(bool active, uint32_t nowMs, uint32_t onMs, uint32_t offMs) {
  if (!active || onMs + offMs == 0) return false;
  return (nowMs % (onMs + offMs)) < onMs;
}

}  // namespace rv
