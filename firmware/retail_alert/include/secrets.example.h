// Sao chép thành include/secrets.h (đã bị .gitignore) và điền giá trị thật. KHÔNG commit secrets.h.
#pragma once

#define WIFI_SSID "ten-wifi"
#define WIFI_PASSWORD "mat-khau-wifi"

// Broker Mosquitto trên Pi
#define MQTT_HOST "192.168.1.50"
#define MQTT_PORT 1883
#define MQTT_USER "node01"
#define MQTT_PASSWORD "mat-khau-node01"

// Máy chủ giờ (NTP) trong LAN, nếu có. Không đồng bộ được thì status ghi clock_synced=false.
#define NTP_SERVER "pool.ntp.org"
