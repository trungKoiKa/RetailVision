// Nội dung màn hình OLED (SSD1306 128x64). Thuần: chỉ định dạng chữ, không đụng phần cứng.
#pragma once

#include <stdint.h>

#include "alert_model.h"

namespace rv {

constexpr int kDisplayLineLen = 22;  // 21 ký tự + '\0' (font 6x8 trên 128 px)

struct DisplayText {
  char title[kDisplayLineLen];   // trạng thái
  char people[kDisplayLineLen];  // số người chờ; "--" khi không biết, không bao giờ "0" thay cho thiếu dữ liệu
  char detail[kDisplayLineLen];  // thời lượng / trạng thái ACK; rỗng nếu không có gì để nói
};

// ageMs: thời gian ESP32 đã thấy trạng thái/cảnh báo hiện tại (AlertModel::stateAgeMs).
void formatDisplay(State state, bool acked, bool hasCount, uint16_t count, uint32_t ageMs, DisplayText& out);

bool operator==(const DisplayText& a, const DisplayText& b);

}  // namespace rv
