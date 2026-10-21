"""Vòng xử lý chính: khung hình → tracks → đếm vạch, vùng chờ, cảnh báo → sự kiện.

Lớp `Pipeline` không biết nguồn khung hình hay detector cụ thể, nên test được
bằng dữ liệu tổng hợp.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Protocol, TextIO

from retailvision.analytics.alert_state import AlertSettings, AlertStateMachine
from retailvision.analytics.crossing import LineCounter
from retailvision.analytics.geometry import to_pixels
from retailvision.analytics.queue import QueueZone
from retailvision.config.loader import EdgeConfig
from retailvision.config.settings import OperatingSettings
from retailvision.core.types import AlertTransition, CrossingEvent, Track
from retailvision.pipeline.capture import Frame

if TYPE_CHECKING:
    from retailvision.messaging.bridge import EdgeMessenger
    from retailvision.pipeline.settings_service import SettingsService


class Detector(Protocol):
    def process(self, image) -> list[Track]: ...


class Pipeline:
    def __init__(
        self,
        config: EdgeConfig,
        frame_size: tuple[int, int],
        settings: Optional[OperatingSettings] = None,
        settings_revision: int = 0,
    ) -> None:
        self.frame_size = frame_size
        self.settings_revision = settings_revision
        s = settings or OperatingSettings.from_config(config)
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
        self.zone = QueueZone(self.polygon_px, s.dwell_seconds)
        self.alert = AlertStateMachine(self._alert_settings(s))
        self._last_sample_second: Optional[int] = None
        # tổng hợp để hiển thị; không ghi ra file
        self.in_count = 0
        self.out_count = 0
        self.last_queue_count = 0

    @staticmethod
    def _alert_settings(s: OperatingSettings) -> AlertSettings:
        return AlertSettings(
            on_count=s.on_count,
            on_hold_seconds=s.on_hold_seconds,
            off_count=s.off_count,
            off_hold_seconds=s.off_hold_seconds,
        )

    def apply_settings(self, s: OperatingSettings, ts: float) -> list[dict]:
        """Áp dụng nguyên bộ ngưỡng mới. Cảnh báo đang mở kết thúc CONFIG_CHANGED, timer tính lại."""
        self.zone.set_dwell(s.dwell_seconds)
        return [_alert_event(t) for t in self.alert.apply_settings(self._alert_settings(s), ts)]

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


def apply_settings_commands(
    pipeline: Pipeline,
    messenger: "Optional[EdgeMessenger]",
    sink: JsonlSink,
    settings: "Optional[SettingsService]",
    ts: float,
) -> None:
    """Áp dụng lệnh đổi ngưỡng từ backend và trả kết quả (APPLIED/REJECTED) qua settings/result."""
    if messenger is None or settings is None:
        return
    for command in messenger.poll_settings():
        events, result = settings.handle(command, pipeline, ts)
        if result is None:
            continue
        if events:
            sink.write(events)
            messenger.publish_events(ts, events)
        messenger.publish_settings_result(ts, result.request_id, result.result, result.revision, result.reason)


def process_frame(
    pipeline: Pipeline,
    detector: Detector,
    sink: JsonlSink,
    messenger: "Optional[EdgeMessenger]",
    frame: Frame,
    frame_age_ms: Callable[[Frame], int] = lambda frame: 0,
    settings: "Optional[SettingsService]" = None,
) -> list[Track]:
    """Xử lý một khung hình: ACK và lệnh đổi ngưỡng đang chờ → phát hiện + theo dõi → phân tích → ghi/gửi sự kiện."""
    apply_acks(pipeline, messenger, sink, frame.ts)
    apply_settings_commands(pipeline, messenger, sink, settings, frame.ts)
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
    settings: "Optional[SettingsService]" = None,
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
        tracks = process_frame(pipeline, detector, sink, messenger, frame, settings=settings)
        processed += 1
        if observer:
            observer(frame, tracks, pipeline)
    return processed


def open_events_file(path: Optional[Path]) -> TextIO:
    if path is None:
        return sys.stdout
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("w", encoding="utf-8")


CAMERA_POLL_S = 0.01


def run_camera_loop(
    config: EdgeConfig,
    read: Callable[[], Optional[Frame]],
    detector: Detector,
    sink: JsonlSink,
    messenger: "Optional[EdgeMessenger]" = None,
    settings: "Optional[SettingsService]" = None,
    *,
    latency_ms: Optional[list] = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] = lambda: False,
    observer: Optional[Callable[[Frame, list[Track], Pipeline], None]] = None,
) -> int:
    """Vòng chạy camera trực tiếp. Trả về số khung đã xử lý khi `should_stop()` (mặc định: không bao giờ).

    - Chưa có khung nào hoặc quá `health.stale_seconds` không có khung mới: đưa máy trạng thái về UNKNOWN
      (alert đang mở kết thúc INTERRUPTED), vẫn gửi state mỗi giây với queue_count = null. Không bao giờ
      ghi 0 người cho dữ liệu không có.
    - Khung hình trở lại: tự phục hồi, bộ theo dõi được reset để không nối ID cũ qua khoảng gián đoạn.
    - Độ phân giải thật của camera có thể khác cấu hình: dựng lại pipeline theo kích thước khung hình.
    `clock` phải cùng miền thời gian với `Frame.ts` (CameraSource dùng time.monotonic).
    `latency_ms`, nếu có, nhận độ trễ từ lúc camera trả khung tới lúc phân tích và phát state xong (ms) của từng khung.
    """
    def build(size):
        return Pipeline(config, size, settings.current if settings else None, settings.revision if settings else 0)

    pipeline = build((config.source.width, config.source.height))
    stale_s = config.health.stale_seconds
    last_frame_at = clock()
    is_stale = False
    processed = 0
    while not should_stop():
        now = clock()
        frame = read()
        if frame is not None:
            height, width = frame.image.shape[:2]
            if (width, height) != pipeline.frame_size:
                print(f"Độ phân giải thật {width}x{height}; dựng lại vạch và vùng chờ theo kích thước này", file=sys.stderr)
                pipeline = build((width, height))
            if is_stale:
                reset = getattr(detector, "reset", None)
                if reset is not None:
                    reset()
            last_frame_at = now
            is_stale = False
            def age(f: Frame) -> int:
                value = max(0, int((clock() - f.ts) * 1000))
                if latency_ms is not None:
                    latency_ms.append(value)
                return value

            tracks = process_frame(pipeline, detector, sink, messenger, frame, frame_age_ms=age, settings=settings)
            processed += 1
            if observer:
                observer(frame, tracks, pipeline)
        else:
            if not is_stale and now - last_frame_at > stale_s:
                is_stale = True
                events = pipeline.stale(now)
                sink.write(events)
                if messenger is not None:
                    messenger.publish_events(now, events)
            if messenger is not None:
                apply_acks(pipeline, messenger, sink, now)
                apply_settings_commands(pipeline, messenger, sink, settings, now)
                messenger.on_idle(now, pipeline)
        sleep(CAMERA_POLL_S)
    return processed
