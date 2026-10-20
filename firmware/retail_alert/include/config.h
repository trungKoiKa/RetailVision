// Cấu hình cố định của firmware: chân, thời gian, định danh. Bí mật đặt trong secrets.h.
#pragma once

#include <stdint.h>

// --- Chân GPIO (tránh chân strapping 0/2/12/15 và chân chỉ-vào 34-39) ---
// LED: GPIO -> 330 ohm -> LED -> GND (mức HIGH = sáng)
constexpr uint8_t PIN_LED_RED = 25;
constexpr uint8_t PIN_LED_GREEN = 26;
constexpr uint8_t PIN_LED_YELLOW = 27;
// Còi: GPIO -> 1 kohm -> base NPN (S8050/2N2222); còi giữa 5 V và collector; emitter -> GND (mức HIGH = kêu)
constexpr uint8_t PIN_BUZZER = 14;
// Nút ACK: INPUT_PULLUP, nút nối GND (nhấn = LOW)
constexpr uint8_t PIN_BUTTON = 33;

// --- Định danh (khớp contracts/mqtt) ---
#define SITE_ID "site01"
#define EDGE_ID "edge01"
#define NODE_ID "node01"
#define FIRMWARE_VERSION "0.1.0"

// --- Thời gian (ms) ---
constexpr uint32_t STATE_TIMEOUT_MS = 5000;   // quá lâu không có state hợp lệ -> UNKNOWN
constexpr uint32_t LED_BLINK_HALF_MS = 250;   // nháy 2 Hz
constexpr uint32_t BUZZER_ON_MS = 200;        // kêu 200 ms, nghỉ 800 ms
constexpr uint32_t BUZZER_OFF_MS = 800;
constexpr uint32_t BUTTON_DEBOUNCE_MS = 30;
constexpr uint32_t ACK_REPEAT_MS = 1000;      // gửi lại cùng ack_id mỗi giây
constexpr uint8_t ACK_MAX_SENDS = 10;
constexpr uint32_t RECONNECT_MS = 3000;        // nối lại MQTT
constexpr uint32_t WIFI_RETRY_MS = 10000;     // thử lại Wi-Fi (mỗi lần kết nối mất vài giây)
constexpr uint16_t MQTT_KEEPALIVE_S = 15;
constexpr uint16_t MQTT_BUFFER_BYTES = 768;   // state ~400 byte; mặc định 256 của PubSubClient không đủ
