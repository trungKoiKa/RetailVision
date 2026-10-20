#include "payloads.h"

#include <stdio.h>

namespace rv {

void formatUuidV4(const uint8_t bytes[16], char out[kUuidLen + 1]) {
  uint8_t b[16];
  for (int i = 0; i < 16; i++) b[i] = bytes[i];
  b[6] = (b[6] & 0x0F) | 0x40;  // version 4
  b[8] = (b[8] & 0x3F) | 0x80;  // variant RFC 4122
  snprintf(out, kUuidLen + 1, "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x", b[0], b[1], b[2],
           b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
}

void formatIsoUtc(int64_t epochSeconds, uint16_t millis, char out[kIsoLen + 1]) {
  // ngày dân sự từ số ngày kể từ 1970-01-01 (thuật toán của Howard Hinnant)
  int64_t days = epochSeconds / 86400;
  int64_t secs = epochSeconds % 86400;
  if (secs < 0) {
    secs += 86400;
    days -= 1;
  }
  const int64_t z = days + 719468;
  const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  const int64_t doe = z - era * 146097;
  const int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  int64_t year = yoe + era * 400;
  const int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const int64_t mp = (5 * doy + 2) / 153;
  const int day = static_cast<int>(doy - (153 * mp + 2) / 5 + 1);
  const int month = static_cast<int>(mp < 10 ? mp + 3 : mp - 9);
  if (month <= 2) year += 1;
  snprintf(out, kIsoLen + 1, "%04d-%02d-%02dT%02d:%02d:%02d.%03uZ", static_cast<int>(year), month, day,
           static_cast<int>(secs / 3600), static_cast<int>((secs % 3600) / 60), static_cast<int>(secs % 60),
           static_cast<unsigned>(millis % 1000));
}

size_t buildAckJson(char* out, size_t cap, const char* ackId, const char* alertId, const char* deviceId) {
  const int n = snprintf(out, cap, "{\"ack_id\":\"%s\",\"alert_id\":\"%s\",\"device_id\":\"%s\"}", ackId, alertId, deviceId);
  return (n > 0 && static_cast<size_t>(n) < cap) ? static_cast<size_t>(n) : 0;
}

size_t buildStatusJson(char* out, size_t cap, const StatusFields& f) {
  const int n = snprintf(out, cap,
                         "{\"schema_version\":1,\"event_id\":\"%s\",\"site_id\":\"%s\",\"device_id\":\"%s\","
                         "\"session_id\":\"%s\",\"seq\":%lu,\"occurred_at\":\"%s\",\"config_version\":\"%s\","
                         "\"status\":\"%s\",\"version\":\"%s\",\"clock_synced\":%s}",
                         f.eventId, f.siteId, f.deviceId, f.sessionId, static_cast<unsigned long>(f.seq), f.occurredAt,
                         f.configVersion, f.status, f.version, f.clockSynced ? "true" : "false");
  return (n > 0 && static_cast<size_t>(n) < cap) ? static_cast<size_t>(n) : 0;
}

}  // namespace rv
