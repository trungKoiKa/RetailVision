#include "display.h"

#include <stdio.h>
#include <string.h>

namespace rv {

void formatDisplay(State state, bool acked, bool hasCount, uint16_t count, uint32_t ageMs, DisplayText& out) {
  out.title[0] = out.people[0] = out.detail[0] = '\0';
  const uint32_t sec = ageMs / 1000;
  const unsigned mm = static_cast<unsigned>((sec / 60) % 100);
  const unsigned ss = static_cast<unsigned>(sec % 60);

  switch (state) {
    case State::Overload:
      snprintf(out.title, kDisplayLineLen, "%s", acked ? "DONG - DA ACK" : "DONG KHACH");
      snprintf(out.detail, kDisplayLineLen, "Keo dai %02u:%02u", mm, ss);
      break;
    case State::Normal:
      snprintf(out.title, kDisplayLineLen, "BINH THUONG");
      break;
    default:
      snprintf(out.title, kDisplayLineLen, "KHONG CO DU LIEU");
      snprintf(out.detail, kDisplayLineLen, "Dang cho Pi...");
      break;
  }

  if (state != State::Unknown && hasCount) {
    snprintf(out.people, kDisplayLineLen, "Nguoi cho: %u", static_cast<unsigned>(count));
  } else {
    snprintf(out.people, kDisplayLineLen, "Nguoi cho: --");
  }
}

bool operator==(const DisplayText& a, const DisplayText& b) {
  return strcmp(a.title, b.title) == 0 && strcmp(a.people, b.people) == 0 && strcmp(a.detail, b.detail) == 0;
}

}  // namespace rv
