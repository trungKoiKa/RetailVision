"""Vòng xử lý chính: khung hình → tracks → đếm vạch, vùng chờ, cảnh báo → sự kiện.

Lớp `Pipeline` không biết nguồn khung hình hay detector cụ thể, nên test được
bằng dữ liệu tổng hợp.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Protocol, TextIO

from retailvision.analytics.alert_state import AlertSettings, AlertStateMachine
from retailvision.analytics.crossing import LineCounter
from retailvision.analytics.geometry import to_pixels
from retailvision.analytics.queue import QueueZone
from retailvision.config.loader import EdgeConfig
from retailvision.core.types import AlertTransition, CrossingEvent, Track
from retailvision.pipeline.capture import Frame

if TYPE_CHECKING:
    from retailvision.messaging.bridge import EdgeMessenger


class Detector(Protocol):
    def process(self, image) -> list[Track]: ...


class Pipeline:
    def __init__(self, config: EdgeConfig, frame_size: tuple[int, int]) -> None:
        w, h = frame_size
        line = to_pixels(config.counting.line, w, h)
        self.line_px = (line[0], line[1])
        self.polygon_px = to_pixels(config.queue.polygon, w, h)
        self.counter = LineCounter(
            line_px=(line[0], line[1]),
            deadband_px=config.counting.deadband_px,
            min_stable_observations=config.counting.min_stable_observations,
            a_to_b_direction=config.counting.a_to_b_direction,
        )
        self.zone = QueueZone(self.polygon_px, config.queue.dwell_seconds)
        a = config.alert
        self.alert = AlertStateMachine(
            AlertSettings(
                on_count=a.on_count,
                on_hold_seconds=a.on_hold_seconds,
                off_count=a.off_count,
                off_hold_seconds=a.off_hold_seconds,
            )
        )
        self._last_sample_second: Optional[int] = None
        # tổng hợp để hiển thị; không ghi ra file
        self.in_count = 0
        self.out_count = 0
        self.last_queue_count = 0

    def step(self, tracks: list[Track], ts: float) -> list[dict]:
        """Xử lý một khung hình, trả về các sự kiện dạng dict để ghi ra.

        Số người vùng chờ chỉ ghi mỗi giây một lần, không ghi theo từng khung.
        """
        events: list[dict] = []
        for crossing in self.counter.update(tracks, ts):
            events.append(_crossing_event(crossing))
            if crossing.direction == "IN":
                self.in_count += 1
            else:
                self.out_count += 1
        count = self.zone.update(tracks, ts)
        self.last_queue_count = count
        second = int(ts)
        if second != self._last_sample_second:
            self._last_sample_second = second
            events.append({"type": "queue", "ts": round(ts, 3), "count": count})
        for transition in self.alert.on_observation(count, ts):
            events.append(_alert_event(transition))
        return events

    def handle_ack(self, alert_id: str, ack_id: str, device_id: str, ts: float) -> list[dict]:
        """ACK của nhân viên: chỉ ghi nhận cho đúng alert đang mở, lần đầu. Không đóng OVERLOAD."""
        return [_alert_event(t) for t in self.alert.on_ack(alert_id, ack_id, device_id, ts)]

    def stale(self, ts: float) -> list[dict]:
        """Không có khung hình mới đủ lâu: vào UNKNOWN, alert đang mở kết thúc."""
        return [_alert_event(t) for t in self.alert.on_stale(ts)]


def _crossing_event(e: CrossingEvent) -> dict:
    return {"type": "crossing", "ts": round(e.ts, 3), "track_id": e.track_id, "direction": e.direction}


def _alert_event(t: AlertTransition) -> dict:
    return {"type": "alert", **{k: v for k, v in asdict(t).items() if v is not None}}


class JsonlSink:
    """Ghi mỗi sự kiện một dòng JSON, dùng cho chấm điểm đánh giá sau này."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write(self, events: Iterable[dict]) -> None:
        for event in events:
            self._stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._stream.flush()


def apply_acks(pipeline: Pipeline, messenger: "Optional[EdgeMessenger]", sink: JsonlSink, ts: float) -> None:
    """Đưa ACK nhận từ ESP32 vào máy trạng thái; ACK được chấp nhận thì ghi và gửi đi một sự kiện alert."""
    if messenger is None:
        return
    for ack in messenger.poll_acks():
        events = pipeline.handle_ack(ack["alert_id"], ack["ack_id"], ack["device_id"], ts)
        if events:
            sink.write(events)
            messenger.publish_events(ts, events)


def process_frame(
    pipeline: Pipeline,
    detector: Detector,
    sink: JsonlSink,
    messenger: "Optional[EdgeMessenger]",
    frame: Frame,
    frame_age_ms: Callable[[Frame], int] = lambda frame: 0,
) -> list[Track]:
    """Xử lý một khung hình: ACK đang chờ → phát hiện + theo dõi → phân tích → ghi/gửi sự kiện."""
    apply_acks(pipeline, messenger, sink, frame.ts)
    tracks = detector.process(frame.image)
    events = pipeline.step(tracks, frame.ts)
    sink.write(events)
    if messenger is not None:
        messenger.on_step(frame.ts, events, pipeline, frame_age_ms(frame))
    return tracks


def run_pipeline(
    pipeline: Pipeline,
    read_frame: Callable[[], Optional[Frame]],
    detector: Detector,
    sink: JsonlSink,
    observer: Optional[Callable[[Frame, list[Track], Pipeline], None]] = None,
    messenger: "Optional[EdgeMessenger]" = None,
) -> int:
    """Lặp đến khi nguồn hết khung hình (video) hoặc dừng (camera). Trả về số khung đã xử lý.

    `observer` được gọi sau mỗi khung với khung ảnh, các track và pipeline (để vẽ hình minh hoạ).
    `messenger`, nếu có, gửi sự kiện/state/telemetry qua MQTT và nhận ACK.
    """
    processed = 0
    while True:
        frame = read_frame()
        if frame is None:
            break
        tracks = process_frame(pipeline, detector, sink, messenger, frame)
        processed += 1
        if observer:
            observer(frame, tracks, pipeline)
    return processed


def open_events_file(path: Optional[Path]) -> TextIO:
    if path is None:
        return sys.stdout
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("w", encoding="utf-8")
