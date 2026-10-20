#include "network.h"

#include <PubSubClient.h>
#include <WiFi.h>
#include <sys/time.h>
#include <time.h>

#include "ack_sender.h"
#include "config.h"
#include "payloads.h"
#include "secrets.h"

namespace {

constexpr time_t kMinSyncedEpoch = 1700000000;  // trước mốc này coi là đồng hồ chưa đồng bộ
constexpr int kAckQueueLen = 4;

struct AckMessage {
  char ackId[rv::kUuidLen + 1];
  char alertId[rv::kUuidLen + 1];
};

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
QueueHandle_t ackQueue;
rv::AlertModel* sharedModel = nullptr;
SemaphoreHandle_t sharedMutex = nullptr;

char topicState[96];
char topicAck[96];
char topicStatus[96];
char sessionId[rv::kUuidLen + 1];
uint32_t statusSeq = 0;

void currentIso(char out[rv::kIsoLen + 1], bool& synced) {
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  synced = tv.tv_sec > kMinSyncedEpoch;
  if (synced) {
    rv::formatIsoUtc(tv.tv_sec, static_cast<uint16_t>(tv.tv_usec / 1000), out);
  } else {
    rv::formatIsoUtc(0, 0, out);  // chưa có giờ: ghi mốc 0 kèm clock_synced=false
  }
}

size_t buildStatus(char* out, size_t cap, const char* status) {
  char eventId[rv::kUuidLen + 1];
  char iso[rv::kIsoLen + 1];
  bool synced;
  randomUuid(eventId);
  currentIso(iso, synced);
  rv::StatusFields f = {SITE_ID, NODE_ID, sessionId, FIRMWARE_VERSION, FIRMWARE_VERSION, status, eventId, statusSeq++, iso, synced};
  return rv::buildStatusJson(out, cap, f);
}

void onMessage(char* topic, uint8_t* payload, unsigned int length) {
  if (strcmp(topic, topicState) != 0) return;
  xSemaphoreTake(sharedMutex, portMAX_DELAY);
  sharedModel->onStatePayload(reinterpret_cast<const char*>(payload), length, millis());
  xSemaphoreGive(sharedMutex);
}

void connectMqtt() {
  char will[400];
  if (buildStatus(will, sizeof(will), "OFFLINE") == 0) return;
  // Last Will QoS 1, retained: broker báo OFFLINE khi ESP32 rớt mạng đột ngột
  if (!mqtt.connect(NODE_ID, MQTT_USER, MQTT_PASSWORD, topicStatus, 1, true, will)) {
    Serial.printf("MQTT: nối lỗi rc=%d\n", mqtt.state());
    return;
  }
  mqtt.subscribe(topicState, 0);
  char online[400];
  if (buildStatus(online, sizeof(online), "ONLINE") != 0) mqtt.publish(topicStatus, online, true);
  Serial.println("MQTT: đã nối");
}

void drainAckQueue() {
  AckMessage msg;
  while (xQueueReceive(ackQueue, &msg, 0) == pdTRUE) {
    char json[160];
    if (rv::buildAckJson(json, sizeof(json), msg.ackId, msg.alertId, NODE_ID) != 0) mqtt.publish(topicAck, json);
  }
}

void networkTask(void*) {
  uint32_t lastWifiAttempt = 0;
  uint32_t lastMqttAttempt = 0;
  bool wifiStarted = false;
  bool timeConfigured = false;
  for (;;) {
    const uint32_t now = millis();
    if (WiFi.status() != WL_CONNECTED) {
      xQueueReset(ackQueue);  // đang mất mạng: ACK cũ vô nghĩa, AckSender sẽ gửi lại
      if (!wifiStarted || now - lastWifiAttempt >= WIFI_RETRY_MS) {
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        wifiStarted = true;
        lastWifiAttempt = now;
      }
    } else {
      if (!timeConfigured) {
        configTime(0, 0, NTP_SERVER);
        timeConfigured = true;
      }
      if (!mqtt.connected()) {
        xQueueReset(ackQueue);
        if (now - lastMqttAttempt >= RECONNECT_MS) {
          lastMqttAttempt = now;
          connectMqtt();
        }
      } else {
        mqtt.loop();
        drainAckQueue();
      }
    }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

}  // namespace

void randomUuid(char out[rv::kUuidLen + 1]) {
  uint8_t bytes[16];
  for (int i = 0; i < 16; i += 4) {
    const uint32_t r = esp_random();
    memcpy(bytes + i, &r, 4);
  }
  rv::formatUuidV4(bytes, out);
}

void networkStart(rv::AlertModel* model, SemaphoreHandle_t mutex) {
  sharedModel = model;
  sharedMutex = mutex;
  snprintf(topicState, sizeof(topicState), "retailvision/v1/%s/%s/state", SITE_ID, EDGE_ID);
  snprintf(topicAck, sizeof(topicAck), "retailvision/v1/%s/%s/events/operator-ack", SITE_ID, NODE_ID);
  snprintf(topicStatus, sizeof(topicStatus), "retailvision/v1/%s/%s/status", SITE_ID, NODE_ID);
  randomUuid(sessionId);
  ackQueue = xQueueCreate(kAckQueueLen, sizeof(AckMessage));

  WiFi.mode(WIFI_STA);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(MQTT_BUFFER_BYTES);
  mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
  mqtt.setSocketTimeout(2);  // connect/đọc không chặn quá 2 giây
  mqtt.setCallback(onMessage);
  xTaskCreatePinnedToCore(networkTask, "network", 6144, nullptr, 1, nullptr, 0);
}

bool networkSendAck(const char* ackId, const char* alertId) {
  AckMessage msg;
  strncpy(msg.ackId, ackId, sizeof(msg.ackId));
  msg.ackId[rv::kUuidLen] = '\0';
  strncpy(msg.alertId, alertId, sizeof(msg.alertId));
  msg.alertId[rv::kUuidLen] = '\0';
  return xQueueSend(ackQueue, &msg, 0) == pdTRUE;
}
