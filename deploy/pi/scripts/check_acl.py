"""Kiểm tra ACL của Mosquitto: mỗi tài khoản chỉ được publish đúng topic của mình.

Backend01 đóng vai quan sát vì nó đọc được hầu hết topic. Bản tin bị ACL chặn sẽ không tới nó.
Biến môi trường: RV_MQTT_HOST, RV_MQTT_PORT, RV_MQTT_PASS (edge01), RV_MQTT_NODE_PASS (node01),
RV_MQTT_BACKEND_PASS (backend01). Tuỳ chọn --site (mặc định site01).

Chạy:
    python check_acl.py --site site01
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import paho.mqtt.client as mqtt

WAIT_S = 1.5


def connect(host: str, port: int, user: str, password: str) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"acl-{user}", protocol=mqtt.MQTTv311)
    client.username_pw_set(user, password)
    client.connect(host, port, keepalive=15)
    client.loop_start()
    return client


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="site01")
    args = parser.parse_args()
    host = os.environ.get("RV_MQTT_HOST", "127.0.0.1")
    port = int(os.environ.get("RV_MQTT_PORT", "1883"))
    p = f"retailvision/v1/{args.site}"

    seen: list[str] = []
    backend = connect(host, port, "backend01", os.environ["RV_MQTT_BACKEND_PASS"])
    backend.on_message = lambda c, u, m: seen.append(m.topic)
    backend.subscribe(f"{p}/edge01/#")
    backend.subscribe(f"{p}/node01/#")  # chỉ nhận được node01/status; phần còn lại bị ACL chặn đọc
    time.sleep(0.5)

    clients = {
        "edge01": connect(host, port, "edge01", os.environ["RV_MQTT_PASS"]),
        "node01": connect(host, port, "node01", os.environ["RV_MQTT_NODE_PASS"]),
        "backend01": backend,
    }
    # (tài khoản, topic, backend có phải nhận được không)
    cases = [
        ("edge01", f"{p}/edge01/state", True),
        ("edge01", f"{p}/edge01/events/crossing", True),
        ("edge01", f"{p}/edge01/settings/set", False),  # edge không được tự ra lệnh đổi ngưỡng
        ("edge01", f"{p}/node01/status", False),  # edge không được giả mạo trạng thái ESP32
        ("node01", f"{p}/node01/status", True),
        ("node01", f"{p}/edge01/state", False),  # ESP32 không được giả mạo state
        ("node01", f"{p}/edge01/events/alert", False),
        ("backend01", f"{p}/edge01/settings/set", True),
        ("backend01", f"{p}/edge01/events/alert", False),  # backend không được tự tạo sự kiện
    ]
    failures = 0
    for user, topic, allowed in cases:
        seen.clear()
        clients[user].publish(topic, b"{}", qos=0)
        time.sleep(WAIT_S)
        arrived = topic in seen
        ok = arrived == allowed
        failures += not ok
        print(f"{'OK ' if ok else 'LỖI'} {user:10s} publish {topic.removeprefix(p + '/'):28s} "
              f"{'đến được' if arrived else 'bị chặn'} (mong đợi: {'đến được' if allowed else 'bị chặn'})")
    for c in clients.values():
        c.loop_stop()
        c.disconnect()
    print("PASS" if failures == 0 else f"{failures} ca sai")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
