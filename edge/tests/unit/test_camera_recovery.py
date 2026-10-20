"""Phục hồi lỗi camera: T11 (rút camera), T14 (restart), T17 (cắm lại). Dùng đồng hồ giả và camera giả."""

import io
import json
import threading
import time

import numpy as np
import pytest

from retailvision.config.loader import load_config
from retailvision.core.types import Track
from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import ListLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.pipeline import capture
from retailvision.pipeline.capture import CameraSource, Frame
from retailvision.pipeline.runner import JsonlSink, run_camera_loop
from schema_helper import errors

TOPICS = Topics("site01")

# Hold ngắn để test nhanh: 2 người đủ 1 giây là OVERLOAD; stale sau 3 giây không có khung
CONFIG = """
site_id: site01
config_version: v1
source: {type: camera, index: 0, width: 100, height: 100}
model: {weights: m.pt}
counting:
  line: [[0.5, 0.0], [0.5, 1.0]]
  deadband_px: 2
  min_stable_observations: 2
  a_to_b_direction: IN
queue:
  polygon: [[0.6, 0.2], [0.95, 0.2], [0.95, 0.9], [0.6, 0.9]]
  dwell_seconds: 0
alert: {on_count: 2, on_hold_seconds: 1, off_count: 1, off_hold_seconds: 1}
health: {stale_seconds: 3}
"""

CROWD = [Track(1, (70.0, 50.0), (0, 0, 0, 0), 0.9), Track(2, (80.0, 50.0), (0, 0, 0, 0), 0.9)]


class World:
    """Đồng hồ giả + camera giả: bật/tắt khung hình theo thời gian."""

    def __init__(self, size=(100, 100)):
        self.t = 1000.0
        self.camera_on = True
        self.size = size
        self.tracks = CROWD
        self.resets = 0
        self.end = None

    def clock(self):
        return self.t

    def sleep(self, dt):
        self.t += max(dt, 0.0) or 0.001

    def read(self):
        if not self.camera_on:
            return None
        w, h = self.size
        return Frame(np.zeros((h, w, 3), dtype=np.uint8), ts=self.t, index=0)

    # Detector
    def process(self, image):
        return self.tracks

    def reset(self):
        self.resets += 1


def run(tmp_path, world, plan):
    """plan: danh sách (giây_từ_đầu, hành_động) thực hiện khi đồng hồ giả tới mốc đó."""
    cfg = tmp_path / "site.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    config = load_config(cfg)
    link = ListLink()
    messenger = EdgeMessenger(
        link, EnvelopeFactory("site01", "edge01", "v1"), TOPICS, profile="pilot", version="0.1.0",
        now=lambda: __import__("datetime").datetime(2026, 11, 2, 10, 0, 0, tzinfo=__import__("datetime").timezone.utc),
    )
    start = world.t
    pending = sorted(plan, key=lambda x: x[0])
    sink_stream = io.StringIO()

    def should_stop():
        while pending and world.t - start >= pending[0][0]:
            _, action = pending.pop(0)
            action()
        return not pending

    # hành động cuối cùng đánh dấu kết thúc
    run_camera_loop(config, world.read, world, JsonlSink(sink_stream), messenger,
                    clock=world.clock, sleep=world.sleep, should_stop=should_stop)
    events = [json.loads(l) for l in sink_stream.getvalue().splitlines()]
    return link, events


def of(link, topic):
    return [m.payload for m in link.sent if m.topic == topic]


def test_t11_unplugging_the_camera_interrupts_the_alert_and_reports_unknown_not_zero(tmp_path):
    world = World()
    unplug = lambda: setattr(world, "camera_on", False)
    def replug():
        world.camera_on = True
        world.tracks = []  # lúc cắm lại vùng chờ đã vắng

    link, events = run(tmp_path, world, [(5, unplug), (12, replug), (16, lambda: None)])

    alerts = of(link, TOPICS.alert)
    assert [a["transition"] for a in alerts] == ["OPEN", "END"]
    assert alerts[1]["reason"] == "INTERRUPTED" and alerts[1]["alert_id"] == alerts[0]["alert_id"]
    assert [e["kind"] for e in events if e["type"] == "alert"] == ["OPEN", "END"]

    states = of(link, TOPICS.state)
    unknown = [s for s in states if s["state"] == "UNKNOWN"]
    assert unknown, "phải báo UNKNOWN khi mất camera"
    assert all(s["queue_count"] is None for s in unknown)  # không phải 0
    first = next(i for i, s in enumerate(states) if s["state"] == "UNKNOWN")
    last = max(i for i, s in enumerate(states) if s["state"] == "UNKNOWN")
    assert all(s["state"] == "UNKNOWN" for s in states[first : last + 1]), "trong lúc mất camera không được xen số đo (nhất là 0 người)"
    assert all(errors("state", s) == [] for s in states)
    # sau khi cắm lại thì quay về trạng thái có dữ liệu (0 người lúc này là số đo thật), tracker reset một lần
    assert states[-1]["state"] == "NORMAL" and states[-1]["queue_count"] == 0
    assert world.resets == 1


def test_unknown_state_is_published_every_second_during_the_outage(tmp_path):
    world = World()
    link, _ = run(tmp_path, world, [(2, lambda: setattr(world, "camera_on", False)), (20, lambda: None)])
    during = [s for s in of(link, TOPICS.state) if s["state"] == "UNKNOWN"]
    assert len(during) >= 14  # ~1 bản mỗi giây trong ~17 giây mất camera, kể cả sau khi đã vào UNKNOWN


def test_camera_missing_at_boot_publishes_unknown_and_never_crashes(tmp_path):
    world = World()
    world.camera_on = False
    link, events = run(tmp_path, world, [(10, lambda: None)])
    states = of(link, TOPICS.state)
    assert len(states) >= 9
    assert all(s["state"] == "UNKNOWN" and s["queue_count"] is None for s in states)
    assert not of(link, TOPICS.alert) and not [e for e in events if e["type"] == "alert"]


def test_camera_appearing_late_starts_normally(tmp_path):
    world = World()
    world.camera_on = False
    world.tracks = []
    link, _ = run(tmp_path, world, [(5, lambda: setattr(world, "camera_on", True)), (9, lambda: None)])
    states = of(link, TOPICS.state)
    assert states[0]["state"] == "UNKNOWN"
    assert states[-1]["state"] == "NORMAL" and states[-1]["queue_count"] == 0  # có dữ liệu thật: 0 người là đúng


def test_recovered_overload_opens_a_new_alert_with_a_new_id(tmp_path):
    world = World()
    link, _ = run(tmp_path, world, [
        (4, lambda: setattr(world, "camera_on", False)),
        (10, lambda: setattr(world, "camera_on", True)),
        (16, lambda: None),
    ])
    opens = [a for a in of(link, TOPICS.alert) if a["transition"] == "OPEN"]
    assert len(opens) == 2 and opens[0]["alert_id"] != opens[1]["alert_id"]


def test_real_resolution_differs_from_config_pipeline_is_rebuilt(tmp_path):
    """Camera cho 640x480 dù cấu hình xin 100x100: vạch (x = 0,5 chiều rộng) phải tính theo 640."""
    world = World(size=(640, 480))
    scripted = iter([
        [Track(7, (400.0, 240.0), (0, 0, 0, 0), 0.9)],   # phải vạch x=320
        [Track(7, (390.0, 240.0), (0, 0, 0, 0), 0.9)],
        [Track(7, (250.0, 240.0), (0, 0, 0, 0), 0.9)],   # qua vạch sang trái
        [Track(7, (240.0, 240.0), (0, 0, 0, 0), 0.9)],
    ])
    world.process = lambda image: next(scripted, [])
    link, events = run(tmp_path, world, [(1, lambda: None)])
    crossings = [e for e in events if e["type"] == "crossing"]
    assert [c["direction"] for c in crossings] == ["IN"]
    assert len(of(link, TOPICS.crossing)) == 1


def test_t14_each_start_is_a_new_session():
    a = EnvelopeFactory("site01", "edge01", "v1")
    b = EnvelopeFactory("site01", "edge01", "v1")
    assert a.session_id != b.session_id


# --- CameraSource tự mở lại sau lỗi đọc liên tiếp (T17) -------------------------------------


class FakeCap:
    """Camera giả: trả `good` khung rồi lỗi mãi (như bị rút)."""

    instances = []

    def __init__(self, index, good):
        self.good = good
        self.released = False
        FakeCap.instances.append(self)

    def set(self, *_):
        return True

    def read(self):
        if self.good > 0:
            self.good -= 1
            return True, np.zeros((48, 64, 3), dtype=np.uint8)
        time.sleep(0.001)
        return False, None

    def release(self):
        self.released = True


def test_t17_camera_source_reopens_after_consecutive_read_failures(monkeypatch):
    FakeCap.instances = []
    goods = iter([3, 5])  # lần mở đầu có 3 khung rồi bị rút; lần mở lại có 5 khung
    monkeypatch.setattr(capture.cv2, "VideoCapture", lambda idx: FakeCap(idx, next(goods, 0)))
    monkeypatch.setattr(capture.time, "sleep", lambda s: None)  # bỏ nghỉ 2 giây
    source = CameraSource(0, 64, 48)
    try:
        deadline = time.time() + 5
        while time.time() < deadline and len(FakeCap.instances) < 2:
            source.read()
            time.sleep(0.001)
        assert len(FakeCap.instances) >= 2, "phải mở lại camera sau lỗi đọc liên tiếp"
        assert FakeCap.instances[0].released  # đóng thiết bị cũ trước khi mở lại
        # khung từ lần mở lại cũng đọc được
        got_after = False
        deadline = time.time() + 5
        while time.time() < deadline and not got_after:
            got_after = source.read() is not None
            time.sleep(0.001)
        assert got_after, "phải đọc được khung từ camera sau khi mở lại"
    finally:
        source.close()


def test_camera_source_read_returns_none_without_new_frame_not_a_stale_one(monkeypatch):
    FakeCap.instances = []
    monkeypatch.setattr(capture.cv2, "VideoCapture", lambda idx: FakeCap(idx, 1))
    source = CameraSource(0, 64, 48)
    try:
        deadline = time.time() + 3
        first = None
        while time.time() < deadline and first is None:
            first = source.read()
            time.sleep(0.001)
        assert first is not None
        assert source.read() is None  # không trả lại khung cũ: tuổi khung phải phản ánh thật
    finally:
        source.close()
