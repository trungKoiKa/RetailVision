"""Đo độ trễ state → ESP32 (NFR-04) bằng bản tin echo của firmware bật cờ `RV_DEBUG_ECHO`.

Firmware debug (`pio run -e esp32dev_debug`) cứ nhận một `state` hợp lệ là gửi lại `{"seq": N}` lên
`retailvision/v1/<site>/node01/debug/latency`. Công cụ này CHẠY TRÊN PI (cùng đồng hồ với `occurred_at` của state):
độ trễ = giờ nhận echo − `occurred_at` của state có cùng `seq`.

Đây là cận TRÊN của độ trễ một chiều: nó gồm cả chiều về (ESP32 → broker → công cụ) và thời gian xử lý trong ESP32.
Không bao gồm thời gian LED đổi trạng thái sau khi nhận (chỉ vài ms, không đo được bằng phương pháp này).
Cần tài khoản MQTT chỉ-đọc (ví dụ `bench01` trong deploy/pi/mosquitto/acl.example) qua RV_MQTT_USER, RV_MQTT_PASS.

    python evaluation/tools/latency_echo.py --host 127.0.0.1 --seconds 120 --out evaluation/results/latency_echo.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metrics  # noqa: E402


class EchoMatcher:
    """Ghép state với echo cùng seq. Hàm thuần theo thời gian truyền vào, nên kiểm được bằng test."""

    def __init__(self, timeout_s: float = 2.0) -> None:
        self._timeout = timeout_s
        self._pending: dict[int, float] = {}
        self.latencies_ms: list[float] = []
        self.states = 0
        self.lost = 0

    def on_state(self, seq: int, published_at: float) -> None:
        self.states += 1
        self._pending[seq] = published_at

    def on_echo(self, seq: int, received_at: float) -> Optional[float]:
        published = self._pending.pop(seq, None)
        if published is None:
            return None  # echo của state đã quá hạn hoặc không biết
        ms = (received_at - published) * 1000.0
        self.latencies_ms.append(ms)
        return ms

    def expire(self, now: float) -> int:
        """Đánh dấu mất các state quá `timeout_s` chưa có echo."""
        old = [s for s, t in self._pending.items() if now - t > self._timeout]
        for s in old:
            del self._pending[s]
        self.lost += len(old)
        return len(old)

    def summary(self) -> dict:
        s = metrics.latency_summary(self.latencies_ms)
        answered = len(self.latencies_ms)
        s.update({"states": self.states, "lost": self.lost,
                  "loss_rate": (self.lost / (answered + self.lost)) if (answered + self.lost) else None})
        return s


def parse_utc(text: str) -> float:
    """ISO 8601 có hậu tố Z -> giây epoch."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def main(argv: Optional[list[str]] = None) -> int:
    import paho.mqtt.client as mqtt

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", default=os.environ.get("RV_MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("RV_MQTT_PORT", "1883")))
    parser.add_argument("--site", default="site01")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    prefix = f"retailvision/v1/{args.site}"
    state_topic, echo_topic = f"{prefix}/edge01/state", f"{prefix}/node01/debug/latency"
    matcher = EchoMatcher()

    def on_message(client, userdata, msg):
        now = time.time()
        try:
            data = json.loads(msg.payload)
            if msg.topic == state_topic:
                matcher.on_state(int(data["seq"]), parse_utc(data["occurred_at"]))
            elif msg.topic == echo_topic:
                matcher.on_echo(int(data["seq"]), now)
        except (ValueError, KeyError, TypeError):
            pass  # bản tin lạ: bỏ qua

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="latency-echo", protocol=mqtt.MQTTv311)
    if os.environ.get("RV_MQTT_USER"):
        client.username_pw_set(os.environ["RV_MQTT_USER"], os.environ.get("RV_MQTT_PASS"))
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=15)
    client.subscribe([(state_topic, 0), (echo_topic, 0)])
    client.loop_start()
    deadline = time.time() + args.seconds
    while time.time() < deadline:
        time.sleep(0.5)
        matcher.expire(time.time())
    client.loop_stop()
    client.disconnect()

    summary = matcher.summary()
    print(json.dumps(summary, indent=2))
    if summary["n"] == 0:
        print("Không nhận được echo nào: firmware đã nạp bản esp32dev_debug chưa, ACL có cho đọc node01/debug chưa?", file=sys.stderr)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["latency_ms"])
            w.writerows([[round(x, 1)] for x in matcher.latencies_ms])
    return 0 if summary["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
