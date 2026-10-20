// Test logic thuần của firmware, chạy trên máy: pio test -e native
#include <ArduinoJson.h>
#include <string.h>
#include <unity.h>

#include "ack_sender.h"
#include "alert_model.h"
#include "debounce.h"
#include "outputs.h"
#include "payloads.h"

using namespace rv;

constexpr uint32_t TIMEOUT = 5000;
const char* ALERT = "5b8e2f10-1c3d-4e5f-8a6b-7c8d9e0f1a2b";
const char* OTHER_ALERT = "11111111-2222-4333-8444-555555555555";

void setUp() {}
void tearDown() {}

static bool feed(AlertModel& m, const char* json, uint32_t now) { return m.onStatePayload(json, strlen(json), now); }

// payload giống state__overload.json trong contracts/examples/valid
static const char* overloadJson(bool acked, const char* alertId) {
  static char buf[600];
  snprintf(buf, sizeof(buf),
           "{\"schema_version\":1,\"event_id\":\"c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f\",\"site_id\":\"site01\","
           "\"device_id\":\"edge01\",\"session_id\":\"a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d\",\"seq\":1532,"
           "\"occurred_at\":\"2026-11-02T10:15:03.120Z\",\"config_version\":\"pilot-2026-11-01\","
           "\"observed_at\":\"2026-11-02T10:15:03.050Z\",\"state\":\"OVERLOAD\",\"queue_count\":5,"
           "\"alert_id\":\"%s\",\"acked\":%s,\"settings_revision\":3}",
           alertId, acked ? "true" : "false");
  return buf;
}

static const char* NORMAL_JSON =
    "{\"schema_version\":1,\"state\":\"NORMAL\",\"queue_count\":1,\"alert_id\":null,\"acked\":false}";
static const char* UNKNOWN_JSON =
    "{\"schema_version\":1,\"state\":\"UNKNOWN\",\"queue_count\":null,\"alert_id\":null,\"acked\":false}";

// ---------------------------------------------------------------- AlertModel

void test_model_is_unknown_before_any_state() {
  AlertModel m(TIMEOUT);
  TEST_ASSERT_EQUAL(State::Unknown, m.state(0));
  TEST_ASSERT_EQUAL(State::Unknown, m.state(123456));
}

void test_model_applies_normal_and_times_out_to_unknown() {
  AlertModel m(TIMEOUT);
  TEST_ASSERT_TRUE(feed(m, NORMAL_JSON, 1000));
  TEST_ASSERT_EQUAL(State::Normal, m.state(1000));
  TEST_ASSERT_EQUAL(State::Normal, m.state(1000 + TIMEOUT));      // đúng ngưỡng vẫn còn hiệu lực
  TEST_ASSERT_EQUAL(State::Unknown, m.state(1000 + TIMEOUT + 1));  // quá ngưỡng 1 ms
}

void test_model_overload_exposes_alert_id_and_acked() {
  AlertModel m(TIMEOUT);
  TEST_ASSERT_TRUE(feed(m, overloadJson(false, ALERT), 0));
  TEST_ASSERT_EQUAL(State::Overload, m.state(0));
  TEST_ASSERT_FALSE(m.acked(0));
  TEST_ASSERT_EQUAL_STRING(ALERT, m.alertId(0));
  TEST_ASSERT_TRUE(feed(m, overloadJson(true, ALERT), 1000));
  TEST_ASSERT_TRUE(m.acked(1000));
}

void test_model_hides_alert_details_outside_overload() {
  AlertModel m(TIMEOUT);
  feed(m, overloadJson(true, ALERT), 0);
  feed(m, NORMAL_JSON, 1000);
  TEST_ASSERT_FALSE(m.acked(1000));
  TEST_ASSERT_EQUAL_STRING("", m.alertId(1000));
}

void test_model_rejects_bad_payloads_and_never_becomes_normal() {
  const char* bad[] = {
      "not json",
      "[1,2,3]",
      "{}",
      "{\"schema_version\":2,\"state\":\"NORMAL\",\"acked\":false}",
      "{\"schema_version\":1,\"state\":\"normal\",\"acked\":false}",
      "{\"schema_version\":1,\"state\":\"BUSY\",\"acked\":false}",
      "{\"schema_version\":1,\"state\":\"NORMAL\"}",
      "{\"schema_version\":1,\"state\":\"NORMAL\",\"acked\":\"no\"}",
      "{\"schema_version\":1,\"state\":7,\"acked\":false}",
      // OVERLOAD không có alert_id hợp lệ thì không ACK đúng được
      "{\"schema_version\":1,\"state\":\"OVERLOAD\",\"acked\":false,\"alert_id\":null}",
      "{\"schema_version\":1,\"state\":\"OVERLOAD\",\"acked\":false,\"alert_id\":\"abc\"}",
      "{\"schema_version\":1,\"state\":\"OVERLOAD\",\"acked\":false}",
  };
  for (const char* payload : bad) {
    AlertModel m(TIMEOUT);
    TEST_ASSERT_FALSE_MESSAGE(feed(m, payload, 100), payload);
    TEST_ASSERT_EQUAL_MESSAGE(State::Unknown, m.state(100), payload);
  }
}

void test_model_bad_payload_does_not_refresh_timeout() {
  AlertModel m(TIMEOUT);
  feed(m, NORMAL_JSON, 0);
  TEST_ASSERT_FALSE(feed(m, "garbage", 4000));
  TEST_ASSERT_EQUAL(State::Unknown, m.state(5001));  // vẫn tính từ state hợp lệ cuối
}

void test_model_rejects_empty_and_oversized() {
  AlertModel m(TIMEOUT);
  TEST_ASSERT_FALSE(m.onStatePayload("", 0, 0));
  TEST_ASSERT_FALSE(m.onStatePayload(nullptr, 5, 0));
  static char big[kMaxStatePayload + 10];
  memset(big, ' ', sizeof(big));
  TEST_ASSERT_FALSE(m.onStatePayload(big, sizeof(big), 0));
}

void test_model_valid_unknown_payload_is_unknown() {
  AlertModel m(TIMEOUT);
  feed(m, NORMAL_JSON, 0);
  TEST_ASSERT_TRUE(feed(m, UNKNOWN_JSON, 500));
  TEST_ASSERT_EQUAL(State::Unknown, m.state(500));
}

void test_model_remembers_the_state_seq_for_latency_echo() {
  AlertModel m(TIMEOUT);
  uint32_t seq = 0;
  TEST_ASSERT_FALSE(m.lastSeq(seq));
  feed(m, "{\"schema_version\":1,\"state\":\"NORMAL\",\"acked\":false,\"seq\":1532}", 0);
  TEST_ASSERT_TRUE(m.lastSeq(seq));
  TEST_ASSERT_EQUAL_UINT32(1532, seq);
  // payload sai không đổi seq
  feed(m, "{\"schema_version\":1,\"state\":\"BUSY\",\"acked\":false,\"seq\":9}", 10);
  TEST_ASSERT_TRUE(m.lastSeq(seq));
  TEST_ASSERT_EQUAL_UINT32(1532, seq);
  // state hợp lệ không có seq: không báo seq (không bịa số)
  feed(m, NORMAL_JSON, 20);
  TEST_ASSERT_FALSE(m.lastSeq(seq));
}

void test_model_timeout_survives_millis_wraparound() {
  AlertModel m(TIMEOUT);
  const uint32_t t0 = 0xFFFFFFFFu - 1000;  // 1 s trước khi millis() tràn
  feed(m, NORMAL_JSON, t0);
  TEST_ASSERT_EQUAL(State::Normal, m.state(t0 + 3000));      // đã tràn, mới qua 3 s
  TEST_ASSERT_EQUAL(State::Unknown, m.state(t0 + 5001));
}

// ------------------------------------------------------------------- Outputs

static void assertOutputs(State s, bool acked, LedMode red, LedMode green, LedMode yellow, bool buzzer) {
  const Outputs o = outputsFor(s, acked);
  TEST_ASSERT_EQUAL(red, o.red);
  TEST_ASSERT_EQUAL(green, o.green);
  TEST_ASSERT_EQUAL(yellow, o.yellow);
  TEST_ASSERT_EQUAL(buzzer, o.buzzer);
}

void test_outputs_follow_the_design_table() {
  assertOutputs(State::Unknown, false, LedMode::Off, LedMode::Off, LedMode::Blink, false);
  assertOutputs(State::Normal, false, LedMode::Off, LedMode::On, LedMode::Off, false);
  assertOutputs(State::Overload, false, LedMode::Blink, LedMode::Off, LedMode::Off, true);
  assertOutputs(State::Overload, true, LedMode::On, LedMode::Off, LedMode::Off, false);
}

void test_led_and_buzzer_levels() {
  TEST_ASSERT_FALSE(ledLevel(LedMode::Off, 0, 250));
  TEST_ASSERT_TRUE(ledLevel(LedMode::On, 999, 250));
  TEST_ASSERT_TRUE(ledLevel(LedMode::Blink, 0, 250));
  TEST_ASSERT_TRUE(ledLevel(LedMode::Blink, 249, 250));
  TEST_ASSERT_FALSE(ledLevel(LedMode::Blink, 250, 250));
  TEST_ASSERT_TRUE(ledLevel(LedMode::Blink, 500, 250));
  TEST_ASSERT_TRUE(buzzerLevel(true, 0, 200, 800));
  TEST_ASSERT_TRUE(buzzerLevel(true, 199, 200, 800));
  TEST_ASSERT_FALSE(buzzerLevel(true, 200, 200, 800));
  TEST_ASSERT_FALSE(buzzerLevel(true, 999, 200, 800));
  TEST_ASSERT_TRUE(buzzerLevel(true, 1000, 200, 800));
  TEST_ASSERT_FALSE(buzzerLevel(false, 0, 200, 800));
}

// ------------------------------------------------------------------ Debouncer

void test_debounce_ignores_bounce_and_fires_once_per_press() {
  Debouncer d(30);
  TEST_ASSERT_FALSE(d.pressed(false, 0));
  // dội trong 20 ms
  TEST_ASSERT_FALSE(d.pressed(true, 100));
  TEST_ASSERT_FALSE(d.pressed(false, 105));
  TEST_ASSERT_FALSE(d.pressed(true, 110));
  TEST_ASSERT_FALSE(d.pressed(true, 125));
  TEST_ASSERT_TRUE(d.pressed(true, 140));   // ổn định đủ 30 ms: phát một lần
  TEST_ASSERT_FALSE(d.pressed(true, 200));  // giữ nút không phát thêm
  TEST_ASSERT_FALSE(d.pressed(true, 5000));
  TEST_ASSERT_FALSE(d.pressed(false, 5100));  // nhả không phát
  TEST_ASSERT_FALSE(d.pressed(false, 5200));
  TEST_ASSERT_FALSE(d.pressed(true, 6000));
  TEST_ASSERT_TRUE(d.pressed(true, 6030));  // nhấn lần hai
}

void test_debounce_shorter_than_threshold_is_not_a_press() {
  Debouncer d(30);
  d.pressed(true, 0);
  TEST_ASSERT_FALSE(d.pressed(false, 20));
  TEST_ASSERT_FALSE(d.pressed(false, 100));
}

// ------------------------------------------------------------------ AckSender

static int uuidCounter = 0;
static void fakeUuid(char out[kUuidLen + 1]) {
  uuidCounter++;
  uint8_t b[16] = {0};
  b[0] = static_cast<uint8_t>(uuidCounter);
  formatUuidV4(b, out);
}

static AckSender makeSender() {
  uuidCounter = 0;
  return AckSender(1000, 10, fakeUuid);
}

void test_ack_button_ignored_unless_overload_and_not_acked() {
  AckSender s = makeSender();
  AckRequest r;
  s.onButton(State::Normal, false, "", 0);
  s.onButton(State::Unknown, false, "", 0);
  s.onButton(State::Overload, true, ALERT, 0);
  TEST_ASSERT_FALSE(s.active());
  TEST_ASSERT_FALSE(s.poll(State::Overload, false, ALERT, 0, r));
  TEST_ASSERT_EQUAL(0, uuidCounter);
}

void test_ack_sends_immediately_then_every_second_with_same_ack_id() {
  AckSender s = makeSender();
  AckRequest first, again;
  s.onButton(State::Overload, false, ALERT, 5000);
  TEST_ASSERT_TRUE(s.poll(State::Overload, false, ALERT, 5000, first));
  TEST_ASSERT_EQUAL_STRING(ALERT, first.alertId);
  TEST_ASSERT_FALSE(s.poll(State::Overload, false, ALERT, 5500, again));
  TEST_ASSERT_FALSE(s.poll(State::Overload, false, ALERT, 5999, again));
  TEST_ASSERT_TRUE(s.poll(State::Overload, false, ALERT, 6000, again));
  TEST_ASSERT_EQUAL_STRING(first.ackId, again.ackId);
}

void test_ack_stops_when_state_reports_acked() {
  AckSender s = makeSender();
  AckRequest r;
  s.onButton(State::Overload, false, ALERT, 0);
  TEST_ASSERT_TRUE(s.poll(State::Overload, false, ALERT, 0, r));
  TEST_ASSERT_FALSE(s.poll(State::Overload, true, ALERT, 1000, r));
  TEST_ASSERT_FALSE(s.active());
}

void test_ack_stops_when_alert_changes_or_ends() {
  AckSender a = makeSender();
  AckRequest r;
  a.onButton(State::Overload, false, ALERT, 0);
  TEST_ASSERT_FALSE(a.poll(State::Overload, false, OTHER_ALERT, 0, r));  // alert_id đổi: không gửi nhầm ACK
  TEST_ASSERT_FALSE(a.active());

  AckSender b = makeSender();
  b.onButton(State::Overload, false, ALERT, 0);
  TEST_ASSERT_FALSE(b.poll(State::Normal, false, "", 0, r));
  TEST_ASSERT_FALSE(b.active());
}

void test_ack_gives_up_after_max_sends_and_new_press_uses_new_ack_id() {
  AckSender s = makeSender();
  AckRequest r, last;
  s.onButton(State::Overload, false, ALERT, 0);
  int sent = 0;
  for (uint32_t t = 0; t < 30000; t += 100) {
    if (s.poll(State::Overload, false, ALERT, t, r)) {
      sent++;
      last = r;
    }
  }
  TEST_ASSERT_EQUAL(10, sent);
  TEST_ASSERT_FALSE(s.active());
  s.onButton(State::Overload, false, ALERT, 40000);
  TEST_ASSERT_TRUE(s.poll(State::Overload, false, ALERT, 40000, r));
  TEST_ASSERT_NOT_EQUAL(0, strcmp(last.ackId, r.ackId));
}

void test_ack_second_press_while_sending_keeps_ack_id() {
  AckSender s = makeSender();
  AckRequest a, b;
  s.onButton(State::Overload, false, ALERT, 0);
  s.poll(State::Overload, false, ALERT, 0, a);
  s.onButton(State::Overload, false, ALERT, 300);
  TEST_ASSERT_TRUE(s.poll(State::Overload, false, ALERT, 1000, b));
  TEST_ASSERT_EQUAL_STRING(a.ackId, b.ackId);
  TEST_ASSERT_EQUAL(1, uuidCounter);
}

void test_ack_new_alert_after_previous_one_ended() {
  AckSender s = makeSender();
  AckRequest r;
  s.onButton(State::Overload, false, ALERT, 0);
  s.poll(State::Overload, false, ALERT, 0, r);
  s.poll(State::Normal, false, "", 500, r);  // cảnh báo cũ kết thúc
  s.onButton(State::Overload, false, OTHER_ALERT, 600);
  TEST_ASSERT_TRUE(s.poll(State::Overload, false, OTHER_ALERT, 600, r));
  TEST_ASSERT_EQUAL_STRING(OTHER_ALERT, r.alertId);
}

// ------------------------------------------------------------------- Payloads

void test_uuid_v4_format() {
  uint8_t bytes[16];
  for (int i = 0; i < 16; i++) bytes[i] = 0xFF;
  char out[kUuidLen + 1];
  formatUuidV4(bytes, out);
  TEST_ASSERT_EQUAL_STRING("ffffffff-ffff-4fff-bfff-ffffffffffff", out);
  for (int i = 0; i < 16; i++) bytes[i] = 0x00;
  formatUuidV4(bytes, out);
  TEST_ASSERT_EQUAL_STRING("00000000-0000-4000-8000-000000000000", out);
}

void test_iso_utc_known_instants() {
  char s[kIsoLen + 1];
  formatIsoUtc(0, 0, s);
  TEST_ASSERT_EQUAL_STRING("1970-01-01T00:00:00.000Z", s);
  formatIsoUtc(1793614503, 120, s);
  TEST_ASSERT_EQUAL_STRING("2026-11-02T10:15:03.120Z", s);
  formatIsoUtc(1709208000, 5, s);  // ngày nhuận
  TEST_ASSERT_EQUAL_STRING("2024-02-29T12:00:00.005Z", s);
  formatIsoUtc(946684799, 999, s);
  TEST_ASSERT_EQUAL_STRING("1999-12-31T23:59:59.999Z", s);
  formatIsoUtc(951868800, 0, s);
  TEST_ASSERT_EQUAL_STRING("2000-03-01T00:00:00.000Z", s);
}

void test_ack_json_has_exactly_the_contract_fields() {
  char out[160];
  const size_t n = buildAckJson(out, sizeof(out), "9d0c1b2a-3e4f-4a5b-9c6d-7e8f9a0b1c2d", ALERT, "node01");
  TEST_ASSERT_GREATER_THAN(0, n);
  JsonDocument doc;
  TEST_ASSERT_FALSE(deserializeJson(doc, out, n));
  TEST_ASSERT_EQUAL(3, doc.as<JsonObject>().size());
  TEST_ASSERT_EQUAL_STRING("9d0c1b2a-3e4f-4a5b-9c6d-7e8f9a0b1c2d", doc["ack_id"].as<const char*>());
  TEST_ASSERT_EQUAL_STRING(ALERT, doc["alert_id"].as<const char*>());
  TEST_ASSERT_EQUAL_STRING("node01", doc["device_id"].as<const char*>());
}

void test_status_json_has_envelope_and_status_fields() {
  StatusFields f = {"site01", "node01", "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", "0.1.0", "0.1.0", "ONLINE",
                    "d5e7f9a1-4b6c-4d8e-9f0a-1b2c3d4e5f60", 7, "2026-11-02T10:00:00.000Z", false};
  char out[400];
  const size_t n = buildStatusJson(out, sizeof(out), f);
  TEST_ASSERT_GREATER_THAN(0, n);
  JsonDocument doc;
  TEST_ASSERT_FALSE(deserializeJson(doc, out, n));
  TEST_ASSERT_EQUAL(1, doc["schema_version"].as<int>());
  TEST_ASSERT_EQUAL(7, doc["seq"].as<int>());
  TEST_ASSERT_EQUAL_STRING("ONLINE", doc["status"].as<const char*>());
  TEST_ASSERT_EQUAL_STRING("node01", doc["device_id"].as<const char*>());
  TEST_ASSERT_FALSE(doc["clock_synced"].as<bool>());
  TEST_ASSERT_EQUAL(11, doc.as<JsonObject>().size());  // 8 trường envelope + status, version, clock_synced
}

void test_builders_return_zero_when_buffer_too_small() {
  char tiny[10];
  TEST_ASSERT_EQUAL(0, buildAckJson(tiny, sizeof(tiny), "a", "b", "c"));
  StatusFields f = {"s", "d", "x", "c", "v", "ONLINE", "e", 0, "t", true};
  TEST_ASSERT_EQUAL(0, buildStatusJson(tiny, sizeof(tiny), f));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_model_is_unknown_before_any_state);
  RUN_TEST(test_model_applies_normal_and_times_out_to_unknown);
  RUN_TEST(test_model_overload_exposes_alert_id_and_acked);
  RUN_TEST(test_model_hides_alert_details_outside_overload);
  RUN_TEST(test_model_rejects_bad_payloads_and_never_becomes_normal);
  RUN_TEST(test_model_bad_payload_does_not_refresh_timeout);
  RUN_TEST(test_model_rejects_empty_and_oversized);
  RUN_TEST(test_model_valid_unknown_payload_is_unknown);
  RUN_TEST(test_model_remembers_the_state_seq_for_latency_echo);
  RUN_TEST(test_model_timeout_survives_millis_wraparound);
  RUN_TEST(test_outputs_follow_the_design_table);
  RUN_TEST(test_led_and_buzzer_levels);
  RUN_TEST(test_debounce_ignores_bounce_and_fires_once_per_press);
  RUN_TEST(test_debounce_shorter_than_threshold_is_not_a_press);
  RUN_TEST(test_ack_button_ignored_unless_overload_and_not_acked);
  RUN_TEST(test_ack_sends_immediately_then_every_second_with_same_ack_id);
  RUN_TEST(test_ack_stops_when_state_reports_acked);
  RUN_TEST(test_ack_stops_when_alert_changes_or_ends);
  RUN_TEST(test_ack_gives_up_after_max_sends_and_new_press_uses_new_ack_id);
  RUN_TEST(test_ack_second_press_while_sending_keeps_ack_id);
  RUN_TEST(test_ack_new_alert_after_previous_one_ended);
  RUN_TEST(test_uuid_v4_format);
  RUN_TEST(test_iso_utc_known_instants);
  RUN_TEST(test_ack_json_has_exactly_the_contract_fields);
  RUN_TEST(test_status_json_has_envelope_and_status_fields);
  RUN_TEST(test_builders_return_zero_when_buffer_too_small);
  return UNITY_END();
}
