import csv
import sys
from pathlib import Path

import numpy as np
import pytest

from retailvision.config.loader import load_config
from retailvision.core.types import Track
from retailvision.pipeline.capture import Frame
from test_pipeline import CONFIG

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation" / "benchmarks"))
import bench  # noqa: E402


class FakeClock:
    """Mỗi lần gọi tăng 10 ms, nên mỗi giai đoạn (đọc, detect, phân tích) đúng 10 ms."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.01
        return self.t


class FakeSource:
    """Clip 25 khung; hết thì read() trả None (bench phải mở lại)."""

    opened = 0

    def __init__(self):
        FakeSource.opened += 1
        self._i = 0

    def read(self):
        if self._i >= 25:
            return None
        self._i += 1
        return Frame(np.zeros((100, 100, 3), dtype=np.uint8), ts=self._i / 25.0, index=self._i)

    def close(self):
        pass


class FakeDetector:
    def process(self, image):
        return [Track(1, (70.0, 50.0), (0, 0, 0, 0), 0.9), Track(2, (80.0, 50.0), (0, 0, 0, 0), 0.9)]


@pytest.fixture
def config(tmp_path):
    p = tmp_path / "site.yaml"
    p.write_text(CONFIG, encoding="utf-8")
    return load_config(p)


def test_parse_variant_handles_windows_paths_and_rejects_bad_input():
    v = bench.parse_variant("pt320=models/source/yolov8n.pt:320")
    assert (v.name, v.weights, v.imgsz) == ("pt320", Path("models/source/yolov8n.pt"), 320)
    w = bench.parse_variant(r"x=C:\models\m.pt:416")
    assert (w.weights, w.imgsz) == (Path(r"C:\models\m.pt"), 416)
    for bad in ["", "noequals", "a=path", "a=path:abc", "a=path:0", "=p:320", "a=:320"]:
        with pytest.raises(ValueError):
            bench.parse_variant(bad)


def test_run_variant_measures_each_stage_and_loops_the_clip(config):
    FakeSource.opened = 0
    row = bench.run_variant(
        bench.VariantSpec("fake", Path("m.pt"), 320),
        config,
        source_factory=FakeSource,
        detector_factory=lambda spec: FakeDetector(),
        seconds=100.0,
        clock=FakeClock(),
        note="thử",
        max_frames=60,  # lớn hơn clip 25 khung - 10 khung khởi động
    )
    assert FakeSource.opened >= 3  # clip ngắn nên phải được mở lại
    assert row["frames"] == 60
    assert row["read_ms_mean"] == 10.0
    assert row["detect_ms_mean"] == 10.0
    assert row["fps_model"] == 100.0  # 1000 / 10 ms
    assert row["people_mean"] == 2.0
    assert row["variant"] == "fake" and row["imgsz"] == 320 and row["note"] == "thử"
    assert row["config_version"] == "v1"
    assert set(row) == set(bench.COLUMNS)


def test_warmup_frames_are_excluded(config):
    row = bench.run_variant(
        bench.VariantSpec("fake", Path("m.pt"), 320),
        config,
        source_factory=FakeSource,
        detector_factory=lambda spec: FakeDetector(),
        seconds=100.0,
        clock=FakeClock(),
        max_frames=5,
    )
    assert row["frames"] == 5


def test_clip_shorter_than_warmup_is_still_measured_by_looping(config):
    class TinySource(FakeSource):
        def read(self):
            if self._i >= 3:
                return None
            self._i += 1
            return Frame(np.zeros((100, 100, 3), dtype=np.uint8), ts=self._i / 25.0, index=self._i)

    row = bench.run_variant(
        bench.VariantSpec("tiny", Path("m.pt"), 320),
        config,
        source_factory=TinySource,
        detector_factory=lambda spec: FakeDetector(),
        seconds=100.0,
        clock=FakeClock(),
        max_frames=4,
    )
    assert row["frames"] == 4


def test_csv_has_one_header_and_appends(tmp_path, config):
    out = tmp_path / "res" / "bench.csv"
    for name in ("a", "b"):
        row = bench.run_variant(
            bench.VariantSpec(name, Path("m.pt"), 320),
            config,
            source_factory=FakeSource,
            detector_factory=lambda spec: FakeDetector(),
            seconds=100.0,
            clock=FakeClock(),
            max_frames=3,
        )
        bench.append_csv(out, row)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["variant"] for r in rows] == ["a", "b"]
    assert list(rows[0].keys()) == bench.COLUMNS
    assert out.read_text(encoding="utf-8").count("timestamp_utc") == 1


def test_missing_pi_readings_are_blank_not_zero(config, monkeypatch):
    monkeypatch.setattr(bench.sysmetrics, "cpu_temp_c", lambda: None)
    monkeypatch.setattr(bench.sysmetrics, "throttled_flags", lambda: None)
    monkeypatch.setattr(bench.sysmetrics, "process_rss_mb", lambda: None)
    row = bench.run_variant(
        bench.VariantSpec("x", Path("m.pt"), 320),
        config,
        source_factory=FakeSource,
        detector_factory=lambda spec: FakeDetector(),
        seconds=100.0,
        clock=FakeClock(),
        max_frames=3,
    )
    assert row["cpu_temp_c_max"] == "" and row["throttled_any"] == "" and row["rss_mb_peak"] == ""


def test_throttling_flag_is_recorded_when_present(config, monkeypatch):
    monkeypatch.setattr(bench.sysmetrics, "cpu_temp_c", lambda: 71.5)
    monkeypatch.setattr(bench.sysmetrics, "throttled_flags", lambda: {"raw": "0x50000", "throttled_occurred": True, "throttled_now": False})
    row = bench.run_variant(
        bench.VariantSpec("x", Path("m.pt"), 320),
        config,
        source_factory=FakeSource,
        detector_factory=lambda spec: FakeDetector(),
        seconds=100.0,
        clock=FakeClock(),
        max_frames=3,
    )
    assert row["throttled_any"] is True and row["cpu_temp_c_max"] == 71.5
