import json

import cv2
import numpy as np
import pytest

from retailvision import app
from retailvision.core.types import Track

CONFIG = """
site_id: site01
config_version: v1
source: {type: video, path: clip.avi}
model: {weights: m.pt}
counting:
  line: [[0.5, 0.0], [0.5, 1.0]]
  a_to_b_direction: IN
queue:
  polygon: [[0.6, 0.2], [0.95, 0.2], [0.95, 0.9], [0.6, 0.9]]
"""


class FakeDetector:
    def __init__(self, *args, **kwargs):
        pass

    def process(self, image):
        return [Track(1, (80.0, 50.0), (0, 0, 0, 0), 0.9)]


def make_clip(path, frames=5):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    if not writer.isOpened():
        pytest.skip("OpenCV không ghi được MJPG")
    for _ in range(frames):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()


def test_check_config_prints_summary_and_exits_zero(tmp_path, capsys):
    cfg = tmp_path / "site.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    assert app.main(["--config", str(cfg), "--check-config"]) == 0
    assert "site=site01" in capsys.readouterr().out


def test_invalid_config_exits_with_code_2(tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("site_id: x\n", encoding="utf-8")
    assert app.main(["--config", str(cfg), "--check-config"]) == 2


def test_video_run_writes_jsonl_events(tmp_path, monkeypatch):
    import retailvision.pipeline.vision as vision

    monkeypatch.setattr(vision, "YoloTracker", FakeDetector)
    cfg = tmp_path / "site.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    clip = tmp_path / "clip.avi"
    make_clip(clip)
    out = tmp_path / "results" / "run.jsonl"

    assert app.main(["--config", str(cfg), "--source", str(clip), "--events-out", str(out)]) == 0

    lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert lines, "phải có ít nhất một sự kiện"
    assert all("type" in e and "ts" in e for e in lines)
    assert any(e["type"] == "queue" and e["count"] == 0 for e in lines)
