// Firmware ESP32: nhận state từ Pi qua MQTT, điều khiển LED/còi, gửi ACK khi nhân viên nhấn nút.
// loop() không bao giờ chặn vì mạng chạy ở task riêng (network.cpp).
#include <Arduino.h>
#include <string.h>

#include "ack_sender.h"
#include "alert_model.h"
#include "config.h"
#include "debounce.h"
#include "network.h"
#include "outputs.h"

static rv::AlertModel model(STATE_TIMEOUT_MS);
static rv::AckSender ackSender(ACK_REPEAT_MS, ACK_MAX_SENDS, randomUuid);
static rv::Debouncer button(BUTTON_DEBOUNCE_MS);
static SemaphoreHandle_t modelMutex;

static rv::State lastLoggedState = rv::State::Unknown;
static bool lastLoggedAcked = false;
static bool logged = false;

static const char* stateName(rv::State s) {
  switch (s) {
    case rv::State::Normal:
      return "NORMAL";
    case rv::State::Overload:
      return "OVERLOAD";
    default:
      return "UNKNOWN";
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  modelMutex = xSemaphoreCreateMutex();
  networkStart(&model, modelMutex);
  Serial.println("retail_alert " FIRMWARE_VERSION " khởi động");
}

void loop() {
  const uint32_t now = millis();

  rv::State state;
  bool acked;
  char alertId[rv::kUuidLen + 1];
  xSemaphoreTake(modelMutex, portMAX_DELAY);
  state = model.state(now);
  acked = model.acked(now);
  strncpy(alertId, model.alertId(now), sizeof(alertId));
  alertId[rv::kUuidLen] = '\0';
  xSemaphoreGive(modelMutex);

  if (button.pressed(digitalRead(PIN_BUTTON) == LOW, now)) ackSender.onButton(state, acked, alertId, now);
  rv::AckRequest request;
  if (ackSender.poll(state, acked, alertId, now, request)) networkSendAck(request.ackId, request.alertId);

  const rv::Outputs out = rv::outputsFor(state, acked);
  digitalWrite(PIN_LED_RED, rv::ledLevel(out.red, now, LED_BLINK_HALF_MS));
  digitalWrite(PIN_LED_GREEN, rv::ledLevel(out.green, now, LED_BLINK_HALF_MS));
  digitalWrite(PIN_LED_YELLOW, rv::ledLevel(out.yellow, now, LED_BLINK_HALF_MS));
  digitalWrite(PIN_BUZZER, rv::buzzerLevel(out.buzzer, now, BUZZER_ON_MS, BUZZER_OFF_MS));

  if (!logged || state != lastLoggedState || acked != lastLoggedAcked) {
    Serial.printf("state=%s acked=%d\n", stateName(state), acked);
    lastLoggedState = state;
    lastLoggedAcked = acked;
    logged = true;
  }
  delay(5);
}
