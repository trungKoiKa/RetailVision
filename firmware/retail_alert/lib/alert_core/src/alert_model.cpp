#include "alert_model.h"

#include <ArduinoJson.h>
#include <string.h>

namespace rv {

namespace {

bool isUuidShape(const char* s) {
  if (s == nullptr || strlen(s) != kUuidLen) return false;
  for (size_t i = 0; i < kUuidLen; i++) {
    const bool dash = (i == 8 || i == 13 || i == 18 || i == 23);
    const char c = s[i];
    if (dash ? c != '-' : !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) return false;
  }
  return true;
}

}  // namespace

bool AlertModel::onStatePayload(const char* json, size_t len, uint32_t nowMs) {
  if (json == nullptr || len == 0 || len > kMaxStatePayload) return false;
  JsonDocument doc;
  if (deserializeJson(doc, json, len)) return false;
  if (!doc.is<JsonObject>()) return false;
  if (!doc["schema_version"].is<int>() || doc["schema_version"].as<int>() != 1) return false;
  if (!doc["state"].is<const char*>() || !doc["acked"].is<bool>()) return false;

  const char* name = doc["state"].as<const char*>();
  State next;
  if (strcmp(name, "NORMAL") == 0) {
    next = State::Normal;
  } else if (strcmp(name, "OVERLOAD") == 0) {
    next = State::Overload;
  } else if (strcmp(name, "UNKNOWN") == 0) {
    next = State::Unknown;
  } else {
    return false;
  }

  char id[kUuidLen + 1] = "";
  if (next == State::Overload) {
    // OVERLOAD không có alert_id hợp lệ thì không thể ACK đúng cảnh báo: coi là payload sai
    if (!doc["alert_id"].is<const char*>()) return false;
    const char* raw = doc["alert_id"].as<const char*>();
    if (!isUuidShape(raw)) return false;
    memcpy(id, raw, kUuidLen);
    id[kUuidLen] = '\0';
  }

  // "mới" nếu đổi trạng thái, đổi cảnh báo, hoặc state trước đó đã quá timeout (tức đã UNKNOWN)
  const bool wasLive = state(nowMs) != State::Unknown;
  const bool sameState = wasLive && state_ == next && strcmp(alertId_, id) == 0;
  if (!sameState) sinceMs_ = nowMs;
  hasCount_ = doc["queue_count"].is<int>() && doc["queue_count"].as<int>() >= 0 && doc["queue_count"].as<int>() <= 1000;
  count_ = hasCount_ ? static_cast<uint16_t>(doc["queue_count"].as<int>()) : 0;
  state_ = next;
  acked_ = (next == State::Overload) && doc["acked"].as<bool>();
  memcpy(alertId_, id, sizeof(alertId_));
  hasValid_ = true;
  lastValidMs_ = nowMs;
  hasSeq_ = doc["seq"].is<uint32_t>();
  seq_ = hasSeq_ ? doc["seq"].as<uint32_t>() : 0;
  return true;
}

State AlertModel::state(uint32_t nowMs) const {
  if (!hasValid_) return State::Unknown;
  if (static_cast<uint32_t>(nowMs - lastValidMs_) > timeoutMs_) return State::Unknown;
  return state_;
}

bool AlertModel::acked(uint32_t nowMs) const { return state(nowMs) == State::Overload && acked_; }

const char* AlertModel::alertId(uint32_t nowMs) const {
  return state(nowMs) == State::Overload ? alertId_ : "";
}

bool AlertModel::queueCount(uint32_t nowMs, uint16_t& out) const {
  if (state(nowMs) == State::Unknown || !hasCount_) return false;
  out = count_;
  return true;
}

uint32_t AlertModel::stateAgeMs(uint32_t nowMs) const {
  if (state(nowMs) == State::Unknown) return 0;
  return static_cast<uint32_t>(nowMs - sinceMs_);
}

bool AlertModel::lastSeq(uint32_t& out) const {
  if (!hasValid_ || !hasSeq_) return false;
  out = seq_;
  return true;
}

}  // namespace rv
