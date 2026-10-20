"""Giả lập edge: phát bản tin đúng contract để thử ESP32 và backend khi chưa có camera/Pi.

Kịch bản:
  normal     NORMAL, 0–1 người, không sự kiện
  crossings  NORMAL, cứ 2 giây một lượt IN rồi OUT xen kẽ
  overload   chu kỳ: NORMAL 5 s → OVERLOAD (5 người) --hold s → NORMAL; lặp theo --period
  unknown    UNKNOWN liên tục (queue_count = null)

Nhận `operator-ack` từ ESP32: ACK đúng alert đang mở, lần đầu thì đặt acked=true và gửi sự kiện ACK.
ACK không làm cảnh báo kết thúc sớm (đúng quy tắc hệ thống).

Ví dụ (broker chạy trên máy này, không tài khoản):
    python -m retailvision.tools.fake_publisher --scenario overload --hold 30
In bản tin ra màn hình mà không kết nối:
    python -m retailvision.tools.fake_publisher --scenario overload --dry-run --seconds 12
Tài khoản broker lấy từ RV_MQTT_USER, RV_MQTT_PASS.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from retailvision import __version__
from retailvision.messaging.bridge import parse_operator_ack
from retailvision.messaging.mqtt_client import Link, ListLink, MqttLink
from retailvision.messaging.payloads import EnvelopeFactory, Message
from retailvision.messaging.topics import Topics

SCENARIOS = ("normal", "crossings", "overload", "unknown")
LEAD_IN_S = 5.0
OVERLOAD_COUNT = 5


class FakeEdge:
    def __init__(
        self,
        link: Link,
        factory: EnvelopeFactory,
        topics: Topics,
        scenario: str,
        hold: float = 30.0,
        period: float = 60.0,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        new_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"kịch bản không có: {scenario}")
        if scenario == "overload" and period < LEAD_IN_S + hold:
            raise ValueError("--period phải lớn hơn 5 + --hold")
        self._link = link
        self._factory = factory
        self._topics = topics
        self._scenario = scenario
        self._hold = hold
        self._period = period
        self._now = now
        self._new_id = new_id
        self._alert_id: Optional[str] = None
        self._acked = False
        self._crossing_count = 0

    def hello(self) -> list[Message]:
        payload = self._factory.status(self._now(), "ONLINE", __version__, True)
        return [Message(self._topics.edge_status, payload, qos=1, retain=True)]

    def will(self) -> Message:
        payload = self._factory.status(self._now(), "OFFLINE", __version__, True)
        return Message(self._topics.edge_status, payload, qos=1, retain=True)

    def poll_acks(self) -> None:
        while not self._link.inbox.empty():
            topic, raw = self._link.inbox.get_nowait()
            if topic != self._topics.operator_ack:
                continue
            ack = parse_operator_ack(raw, self._topics.node_id)
            if ack is None or self._alert_id is None or ack["alert_id"] != self._alert_id or self._acked:
                continue
            self._acked = True
            self._publish_alert("ACK", ack_id=ack["ack_id"], ack_device_id=ack["device_id"], queue_count=None)

    def step(self, elapsed: float) -> None:
        """Phát bản tin của giây thứ `elapsed` (tính từ lúc bắt đầu)."""
        now = self._now()
        state, count = self._state_at(elapsed)
        if self._scenario == "overload":
            self._sync_alert(state, now)
        if self._scenario == "crossings" and int(elapsed) % 2 == 0:
            direction = "IN" if self._crossing_count % 2 == 0 else "OUT"
            self._crossing_count += 1
            payload = self._factory.crossing(now, direction, self._crossing_count, "main", "demo")
            self._link.publish(Message(self._topics.crossing, payload, qos=1))
        payload = self._factory.state(now, now, state, count, self._alert_id, self._acked)
        self._link.publish(Message(self._topics.state, payload, qos=0))

    def _state_at(self, elapsed: float) -> tuple[str, Optional[int]]:
        if self._scenario == "unknown":
            return "UNKNOWN", None
        if self._scenario == "overload":
            phase = elapsed % self._period
            if LEAD_IN_S <= phase < LEAD_IN_S + self._hold:
                return "OVERLOAD", OVERLOAD_COUNT
        return "NORMAL", int(elapsed) % 2

    def _sync_alert(self, state: str, now: datetime) -> None:
        if state == "OVERLOAD" and self._alert_id is None:
            self._alert_id = self._new_id()
            self._acked = False
            self._publish_alert("OPEN", queue_count=OVERLOAD_COUNT)
        elif state != "OVERLOAD" and self._alert_id is not None:
            self._publish_alert("END", reason="NORMALIZED", queue_count=1)
            self._alert_id = None
            self._acked = False

    def _publish_alert(self, transition: str, **fields) -> None:
        payload = self._factory.alert(self._now(), self._alert_id, transition, **fields)
        self._link.publish(Message(self._topics.alert, payload, qos=1))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fake_publisher", description=__doc__.split("\n")[0])
    p.add_argument("--scenario", choices=SCENARIOS, default="normal")
    p.add_argument("--site", default="site01")
    p.add_argument("--device", default="edge01")
    p.add_argument("--node", default="node01")
    p.add_argument("--host", default=os.environ.get("RV_MQTT_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("RV_MQTT_PORT", "1883")))
    p.add_argument("--hold", type=float, default=30.0, help="overload: số giây giữ OVERLOAD")
    p.add_argument("--period", type=float, default=60.0, help="overload: độ dài một chu kỳ")
    p.add_argument("--seconds", type=float, help="dừng sau ngần này giây (mặc định: chạy đến Ctrl+C)")
    p.add_argument("--dry-run", action="store_true", help="in bản tin ra stdout, không kết nối MQTT")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    topics = Topics(args.site, args.device, args.node)
    factory = EnvelopeFactory(args.site, args.device, "fake-publisher")
    link: Link = ListLink() if args.dry_run else None  # type: ignore[assignment]
    edge = FakeEdge(link, factory, topics, args.scenario, hold=args.hold, period=args.period)
    if not args.dry_run:
        link = MqttLink(
            host=args.host,
            port=args.port,
            client_id=f"{args.device}-fake",
            username=os.environ.get("RV_MQTT_USER"),
            password=os.environ.get("RV_MQTT_PASS"),
            will=edge.will(),
            on_connect_messages=edge.hello,
            subscriptions=[(topics.operator_ack, 0)],
        )
        edge._link = link
    start = time.monotonic()
    sent_so_far = 0
    try:
        while True:
            elapsed = time.monotonic() - start
            if args.seconds is not None and elapsed >= args.seconds:
                break
            edge.poll_acks()
            edge.step(elapsed)
            if args.dry_run:
                for m in link.sent[sent_so_far:]:
                    print(json.dumps({"topic": m.topic, "qos": m.qos, "retain": m.retain, "payload": m.payload}, ensure_ascii=False))
                sent_so_far = len(link.sent)
            time.sleep(max(0.0, 1.0 - ((time.monotonic() - start) % 1.0)))
    except KeyboardInterrupt:
        pass
    finally:
        if not args.dry_run:
            link.close(final=edge.will())
    return 0


if __name__ == "__main__":
    sys.exit(main())
