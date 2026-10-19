# MQTT contract

Nguồn sự thật cho bản tin giữa Pi, ESP32 và Spring. JSON Schema đặt trong `events/`, `commands/`, `common/`; ví dụ hợp lệ/sai/trùng trong `../examples/`. Đổi contract thì tăng `schema_version`.

## Topic

Tiền tố: `retailvision/v1/{site_id}/`. Demo: `site01`, Pi `edge01`, ESP32 `node01`.

| Topic | Publisher → Subscriber | QoS / retain | Trường riêng |
| --- | --- | --- | --- |
| `edge01/state` | Pi → ESP32, Spring | 0 / false | `observed_at`, `state` (NORMAL/OVERLOAD/UNKNOWN), `queue_count` hoặc null, `alert_id` hoặc null, `acked`, `settings_revision` |
| `edge01/events/crossing` | Pi → Spring | 1 / false | `direction` (IN/OUT), `track_id`, `line_id`, `profile` |
| `edge01/events/alert` | Pi → Spring | 1 / false | `alert_id`, `transition` (OPEN/ACK/END), `queue_count`, `reason` (END: NORMALIZED/INTERRUPTED/CONFIG_CHANGED), `ack_id` + `ack_device_id` (ACK) |
| `edge01/telemetry` | Pi → Spring | 1 / false | Mỗi 60 giây: `valid_seconds`, `queue_avg`, `queue_max`, `fps`, `frame_age_ms` |
| `edge01/status` | Pi → Spring | 1 / true | `status` (ONLINE/OFFLINE, Last Will), `version`, `clock_synced` |
| `edge01/settings/set` | Spring → Pi | 1 / false | `request_id`, `expected_settings_revision`, `dwell_seconds`, `on_count`, `on_hold_seconds`, `off_count`, `off_hold_seconds` (P1) |
| `edge01/settings/result` | Pi → Spring | 1 / false | `request_id`, `result` (APPLIED/REJECTED), `settings_revision`, `reason` (P1) |
| `node01/events/operator-ack` | ESP32 → Pi | 0 / false | `ack_id`, `alert_id`, `device_id` |
| `node01/status` | ESP32 → Pi, Spring | 1 / true | `status` (ONLINE/OFFLINE, Last Will), `firmware_version` |

## Envelope

Mọi bản tin (trừ `operator-ack` gửi từ ESP32) có:

| Trường | Kiểu | Ghi chú |
| --- | --- | --- |
| `schema_version` | int | Bắt đầu từ 1 |
| `event_id` | UUID | Khóa chống trùng |
| `site_id`, `device_id` | string | |
| `session_id` | UUID | Mới sau mỗi lần edge khởi động |
| `seq` | int | Tăng trong session; chỉ so trong cùng session |
| `occurred_at` | ISO 8601 UTC | Theo đồng hồ Pi |
| `config_version` | string | Phiên bản profile edge |

## Quy tắc

- `queue_count = null` khi UNKNOWN, không dùng 0.
- `track_id` chỉ có nghĩa trong một session, không phải danh tính.
- Spring dedupe theo `event_id`; ack broker chỉ sau khi commit.
- ESP32 gửi lại cùng `ack_id` tới khi `state.acked = true`; Pi chỉ nhận ACK đúng alert đang mở, lần đầu.
- Không retain `state`.
- Bên nhận kiểm kiểu, trường bắt buộc, độ dài; payload sai bị bỏ và ghi log.

## ACL

| Tài khoản | Publish | Subscribe |
| --- | --- | --- |
| `edge01` | `edge01/#` trừ `settings/set` | `edge01/settings/set`, `node01/events/operator-ack` |
| `node01` | `node01/#` | `edge01/state` |
| `backend01` | `edge01/settings/set` | `edge01/#`, `node01/status` |
