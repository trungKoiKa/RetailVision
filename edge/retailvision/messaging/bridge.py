"""Nối pipeline với MQTT: đổi sự kiện nội bộ thành bản tin đúng contract và gửi đi; nhận ACK từ ESP32.

Thời gian trong pipeline là `ts` (giây: monotonic khi chạy camera, timestamp video khi replay).
`EdgeMessenger` neo `ts` đầu tiên vào đồng hồ UTC của máy rồi suy ra `occurred_at` cho mọi bản tin.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from retailvision.messaging.mqtt_client import Link
from retailvision.messaging.payloads import EnvelopeFactory, Message
from retailvision.messaging.topics import Topics
from retailvision.resilience.telemetry import MinuteAggregator, MinuteSummary

STATE_QOS = 0
EVENT_QOS = 1


def _is_uuid(value: object) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return False
    return isinstance(value, str)


def parse_operator_ack(raw: bytes, expected_device: str) -> Optional[dict]:
    """Trả về {ack_id, alert_id, device_id} nếu bản tin đúng contract, ngược lại None."""
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or set(data) != {"ack_id", "alert_id", "device_id"}:
        return None
    if not (_is_uuid(data["ack_id"]) and _is_uuid(data["alert_id"]) and data["device_id"] == expected_device):
        return None
    return data


class EdgeMessenger:
    def __init__(
        self,
        link: Optional[Link],
        factory: EnvelopeFactory,
        topics: Topics,
        profile: str,
        version: str,
        line_id: str = "main",
        clock_synced: Callable[[], bool] = lambda: True,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._link = link
        self._factory = factory
        self._topics = topics
        self._profile = profile
        self._version = version
        self._line_id = line_id
        self._clock_synced = clock_synced
        self._now = now
        self._anchor: Optional[tuple[datetime, float]] = None
        self._last_state_second: Optional[int] = None
        self._last_observed_ts: Optional[float] = None
        self._telemetry = MinuteAggregator()

    def attach(self, link: Link) -> None:
        """Gắn kết nối sau khi tạo (kết nối cần will/hello do messenger dựng)."""
        self._link = link

    # --- đồng hồ ---------------------------------------------------------

    def wall(self, ts: float) -> datetime:
        if self._anchor is None:
            self._anchor = (self._now(), ts)
        wall0, ts0 = self._anchor
        return wall0 + timedelta(seconds=ts - ts0)

    # --- kết nối ---------------------------------------------------------

    def _status(self, status: str) -> Message:
        payload = self._factory.status(self._now(), status, self._version, self._clock_synced())
        return Message(self._topics.edge_status, payload, qos=EVENT_QOS, retain=True)

    def will(self) -> Message:
        """Bản tin Last Will: broker tự gửi khi edge mất kết nối đột ngột."""
        return self._status("OFFLINE")

    def hello(self) -> list[Message]:
        """Gửi mỗi lần nối (hoặc nối lại) thành công."""
        return [self._status("ONLINE")]

    def close(self) -> None:
        self._link.close(final=self._status("OFFLINE"))

    # --- gửi -------------------------------------------------------------

    def on_step(self, ts: float, events: list[dict], pipeline, frame_age_ms: int = 0) -> None:
        """Gọi sau mỗi khung hình đã phân tích."""
        self._last_observed_ts = ts
        for event in events:
            message = self._event_message(event)
            if message is not None:
                self._link.publish(message)
        for summary in self._telemetry.add(self.wall(ts), pipeline.last_queue_count, frame_age_ms):
            self._publish_telemetry(summary)
        self._maybe_state(ts, pipeline)

    def on_idle(self, ts: float, pipeline) -> None:
        """Gọi khi chưa có khung hình mới (kể cả lúc mất dữ liệu): vẫn báo state và đóng phút telemetry."""
        for summary in self._telemetry.advance(self.wall(ts)):
            self._publish_telemetry(summary)
        self._maybe_state(ts, pipeline)

    def publish_events(self, ts: float, events: list[dict]) -> None:
        """Gửi sự kiện phát sinh ngoài vòng khung hình (ví dụ ACK, mất dữ liệu)."""
        self._last_observed_ts = self._last_observed_ts if self._last_observed_ts is not None else ts
        for event in events:
            message = self._event_message(event)
            if message is not None:
                self._link.publish(message)

    def _event_message(self, event: dict) -> Optional[Message]:
        kind = event["type"]
        if kind == "crossing":
            payload = self._factory.crossing(
                self.wall(event["ts"]), event["direction"], event["track_id"], self._line_id, self._profile
            )
            return Message(self._topics.crossing, payload, qos=EVENT_QOS)
        if kind == "alert":
            payload = self._factory.alert(
                self.wall(event["ts"]),
                alert_id=event["alert_id"],
                transition=event["kind"],
                queue_count=event.get("queue_count"),
                reason=event.get("reason"),
                ack_id=event.get("ack_id"),
                ack_device_id=event.get("ack_device_id"),
            )
            return Message(self._topics.alert, payload, qos=EVENT_QOS)
        return None  # "queue" chỉ dùng nội bộ/đánh giá, không gửi

    def _publish_telemetry(self, s: MinuteSummary) -> None:
        payload = self._factory.telemetry(
            self._now(), s.minute_start, s.valid_seconds, s.queue_avg, s.queue_max, s.fps, s.frame_age_ms
        )
        self._link.publish(Message(self._topics.telemetry, payload, qos=EVENT_QOS))

    def _maybe_state(self, ts: float, pipeline) -> None:
        second = int(ts)
        if second == self._last_state_second:
            return
        self._last_state_second = second
        observed = self._last_observed_ts if self._last_observed_ts is not None else ts
        alert = pipeline.alert
        payload = self._factory.state(
            occurred_at=self.wall(ts),
            observed_at=self.wall(observed),
            state=alert.state.value,
            queue_count=pipeline.last_queue_count,
            alert_id=alert.alert_id,
            acked=alert.acked,
        )
        self._link.publish(Message(self._topics.state, payload, qos=STATE_QOS))

    # --- nhận ------------------------------------------------------------

    def poll_acks(self) -> list[dict]:
        """ACK hợp lệ từ ESP32 đã nhận kể từ lần gọi trước. Bản tin sai bị bỏ và ghi log."""
        acks: list[dict] = []
        while not self._link.inbox.empty():
            topic, raw = self._link.inbox.get_nowait()
            if topic != self._topics.operator_ack:
                continue
            ack = parse_operator_ack(raw, self._topics.node_id)
            if ack is None:
                print(f"MQTT: bỏ operator-ack không hợp lệ: {raw[:120]!r}", file=sys.stderr)
                continue
            acks.append(ack)
        return acks
