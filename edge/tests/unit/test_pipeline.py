import io
import json

import numpy as np

from retailvision.config.loader import load_config
from retailvision.core.types import Track
from retailvision.pipeline.capture import Frame
from retailvision.pipeline.runner import JsonlSink, Pipeline, run_pipeline

# khung 100×100; vạch x=50; đa giác vùng chờ x∈[60,95], y∈[20,90]
CONFIG = """
site_id: site01
config_version: v1
source: {type: video, path: clip.mp4}
model: {weights: m.pt}
counting:
  line: [[0.5, 0.0], [0.5, 1.0]]
  deadband_px: 2
  min_stable_observations: 2
  a_to_b_direction: IN
queue:
  polygon: [[0.6, 0.2], [0.95, 0.2], [0.95, 0.9], [0.6, 0.9]]
  dwell_seconds: 2.0
alert: {on_count: 5, on_hold_seconds: 60, off_count: 3, off_hold_seconds: 10}
"""


def make_pipeline(tmp_path):
    p = tmp_path / "site.yaml"
    p.write_text(CONFIG, encoding="utf-8")
    return Pipeline(load_config(p), frame_size=(100, 100))


class ScriptedDetector:
    """Trả về danh sách track đã định sẵn theo thứ tự khung hình."""

    def __init__(self, script):
        self._script = list(script)

    def process(self, image):
        return self._script.pop(0)


def frames(timestamps):
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    it = iter([Frame(image=image, ts=t, index=i) for i, t in enumerate(timestamps)])
    return lambda: next(it, None)


def person(track_id, x, y=50.0):
    return Track(track_id, (x, y), (0, 0, 0, 0), 0.9)


def run(pipeline, tracks_per_frame, timestamps):
    buf = io.StringIO()
    run_pipeline(pipeline, frames(timestamps), ScriptedDetector(tracks_per_frame), JsonlSink(buf))
    return [json.loads(line) for line in buf.getvalue().splitlines()]


def test_crossing_is_written_as_event(tmp_path):
    pipeline = make_pipeline(tmp_path)
    # đi từ phải (x>50) sang trái (x<50): phía -1 → +1 = A→B = IN
    xs = [60, 55, 45, 40]
    events = run(pipeline, [[person(1, x)] for x in xs], [i * 0.5 for i in range(4)])
    crossings = [e for e in events if e["type"] == "crossing"]
    assert [(c["track_id"], c["direction"]) for c in crossings] == [(1, "IN")]


def test_queue_sample_written_once_per_second(tmp_path):
    pipeline = make_pipeline(tmp_path)
    ts = [i * 0.2 for i in range(15)]  # 0.0 … 2.8 giây → 3 giây khác nhau
    events = run(pipeline, [[] for _ in ts], ts)
    samples = [e for e in events if e["type"] == "queue"]
    assert len(samples) == 3
    assert all(s["count"] == 0 for s in samples)


def test_overload_alert_opens_after_dwell_plus_hold(tmp_path):
    pipeline = make_pipeline(tmp_path)
    crowd = [person(i, 80) for i in range(1, 6)]  # 5 người trong vùng chờ
    ts = [float(t) for t in range(0, 70)]
    events = run(pipeline, [crowd for _ in ts], ts)
    alerts = [e for e in events if e["type"] == "alert"]
    assert [a["kind"] for a in alerts] == ["OPEN"]
    assert alerts[0]["queue_count"] == 5
    # dwell 2 giây (người đủ điều kiện từ ts=2) + hold 60 giây = mở lúc ts=62
    assert alerts[0]["ts"] == 62.0


def test_dwell_not_met_produces_no_queue_count(tmp_path):
    pipeline = make_pipeline(tmp_path)
    events = run(pipeline, [[person(1, 80)], []], [0.0, 1.0])
    samples = [e for e in events if e["type"] == "queue"]
    assert samples  # có mẫu theo giây
    assert all(s["count"] == 0 for s in samples)


def test_run_pipeline_returns_processed_count(tmp_path):
    pipeline = make_pipeline(tmp_path)
    buf = io.StringIO()
    n = run_pipeline(pipeline, frames([0.0, 1.0, 2.0]), ScriptedDetector([[], [], []]), JsonlSink(buf))
    assert n == 3
