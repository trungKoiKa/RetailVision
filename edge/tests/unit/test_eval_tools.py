"""Kiểm các công cụ quay clip, hiệu chuẩn và gán nhãn vùng chờ (phần logic, không cần màn hình hay camera thật)."""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from retailvision.config.loader import load_config
from retailvision.tools import calibrate, record
from test_pipeline import CONFIG

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation" / "tools"))
import label_queue  # noqa: E402


# --- QueueLabeler ----------------------------------------------------------------------------


def test_queue_labeler_marks_and_typing():
    lab = label_queue.QueueLabeler(duration_s=22, step_s=5)
    assert lab.marks == [0, 5, 10, 15, 20]
    for d in "12":
        lab.type_digit(d)
    assert lab.buffer == "12"
    lab.type_digit("x")  # không phải chữ số: bỏ qua
    lab.type_digit("345")  # 12345 > 99: các chữ số làm vượt giới hạn bị bỏ
    assert lab.buffer == "12"
    assert lab.confirm() and lab.values == {0: 12} and lab.index == 1


def test_confirm_without_typing_does_not_record_a_zero():
    lab = label_queue.QueueLabeler(10, 5)
    assert lab.confirm() is False and lab.values == {} and lab.index == 0
    lab.type_digit("0")
    assert lab.confirm() and lab.values == {0: 0}  # 0 gõ rõ ràng thì mới là 0


def test_backspace_skip_back_and_finish():
    lab = label_queue.QueueLabeler(10, 5)
    lab.type_digit("7")
    lab.backspace()
    assert lab.buffer == ""
    lab.type_digit("3")
    lab.confirm()
    lab.skip()  # mốc 5 bỏ qua: không có giá trị
    lab.type_digit("1")
    lab.confirm()
    assert lab.values == {0: 3, 10: 1} and lab.finished
    lab.back()  # quay lại mốc 10, nạp sẵn giá trị cũ để sửa
    assert lab.mark == 10 and lab.buffer == "1"
    assert [r for r in lab.rows()] == [(0, 3), (10, 1)]


def test_leading_zeros_are_normalised():
    lab = label_queue.QueueLabeler(5, 5)
    lab.type_digit("0")
    lab.type_digit("4")
    assert lab.buffer == "4"


def test_csv_round_trip_and_resume(tmp_path):
    lab = label_queue.QueueLabeler(20, 5)
    for value in ("2", "5", "5"):
        lab.type_digit(value)
        lab.confirm()
    path = tmp_path / "q.csv"
    lab.to_csv(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "ts,count"
    assert [(float(t), int(c)) for t, c in (l.split(",") for l in lines[1:])] == [(0.0, 2), (5.0, 5), (10.0, 5)]
    resumed = label_queue.QueueLabeler.resume(path, 20, 5)
    assert resumed.mark == 15 and resumed.values == {0: 2, 5: 5, 10: 5}  # tiếp tục từ mốc chưa gán


def test_invalid_labeler_arguments():
    with pytest.raises(ValueError):
        label_queue.QueueLabeler(0, 5)
    with pytest.raises(ValueError):
        label_queue.QueueLabeler(10, 0)


# --- Calibration -----------------------------------------------------------------------------


def test_calibration_yaml_is_normalised_and_loadable_by_the_edge_loader(tmp_path):
    cal = calibrate.Calibration(width=200, height=100)
    cal.add_point(90, 10)
    cal.add_point(90, 90)
    cal.mode = "polygon"
    for p in [(120, 20), (190, 20), (190, 90), (120, 90)]:
        cal.add_point(*p)
    cal.flip_direction()
    snippet = yaml.safe_load(cal.to_yaml())
    assert snippet["counting"]["line"] == [[0.45, 0.1], [0.45, 0.9]]
    assert snippet["counting"]["a_to_b_direction"] == "OUT"
    assert snippet["queue"]["polygon"][0] == [0.6, 0.2]

    # ghép vào cấu hình thật: edge phải đọc được
    base = yaml.safe_load(CONFIG)
    base["counting"].update(snippet["counting"])
    base["queue"].update(snippet["queue"])
    path = tmp_path / "site.yaml"
    path.write_text(yaml.safe_dump(base), encoding="utf-8")
    cfg = load_config(path)
    assert cfg.counting.a_to_b_direction == "OUT" and len(cfg.queue.polygon) == 4


def test_calibration_refuses_incomplete_shapes():
    cal = calibrate.Calibration(100, 100)
    with pytest.raises(ValueError, match="Vạch cần đúng 2 điểm"):
        cal.to_yaml()
    cal.add_point(10, 10)
    cal.add_point(10, 10)
    assert any("trùng" in p for p in cal.problems())
    cal.mode = "polygon"
    cal.add_point(1, 1)
    cal.add_point(2, 2)
    assert any("3 đỉnh" in p for p in cal.problems())


def test_points_are_clamped_and_a_third_line_click_starts_a_new_line():
    cal = calibrate.Calibration(100, 50)
    cal.add_point(-5, 999)
    assert cal.line == [(0.0, 49.0)]
    cal.add_point(10, 10)
    cal.add_point(20, 20)  # vạch đã đủ 2 điểm: bắt đầu vạch mới
    assert cal.line == [(20.0, 20.0)]
    cal.undo()
    assert cal.line == []
    cal.mode = "polygon"
    cal.add_point(1, 1)
    cal.clear()
    assert cal.polygon == []


def test_direction_arrow_points_towards_the_negative_to_positive_side():
    # vạch đứng A(0,0.1) B(0,0.9) ở x=100: phía dương của signed_distance là bên trái (x nhỏ hơn)
    from retailvision.analytics.geometry import signed_distance

    cal = calibrate.Calibration(200, 100)
    cal.add_point(100, 10)
    cal.add_point(100, 90)
    (x0, y0), (x1, y1) = cal.direction_arrow()
    assert x1 < x0  # đi từ phải sang trái, đúng với cấu hình mẫu ("phải→trái = IN")
    a, b = cal.line
    assert signed_distance((x0, y0), a, b) < 0 < signed_distance((x1, y1), a, b)
    assert calibrate.Calibration(100, 100).direction_arrow() is None


def test_calibration_can_start_from_an_existing_config(tmp_path):
    path = tmp_path / "site.yaml"
    path.write_text(CONFIG, encoding="utf-8")
    cal = calibrate.from_config(path, 200, 100)
    assert cal.line == [(100.0, 0.0), (100.0, 100.0)] and cal.direction == "IN" and len(cal.polygon) == 4


# --- record ----------------------------------------------------------------------------------


class FakeCamera:
    """Camera giả chậm hơn fps yêu cầu; đồng hồ giả tăng theo từng lần đọc."""

    def __init__(self, clock, per_read=0.2, size=(64, 48)):
        self.clock = clock
        self.per_read = per_read
        self.size = size
        self.reads = 0
        self.released = False
        self.set_calls = []

    def isOpened(self):
        return True

    def set(self, prop, value):
        self.set_calls.append((prop, value))
        return True

    def read(self):
        self.reads += 1
        self.clock.t += self.per_read
        w, h = self.size
        return True, np.full((h, w, 3), self.reads % 255, dtype=np.uint8)

    def release(self):
        self.released = True


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_resampler_keeps_real_time_when_the_source_is_slower():
    r = record.Resampler(fps=10, start=0.0)
    assert r.due(0.0) == 1  # khung đầu tại t=0
    r.wrote(1)
    assert r.due(0.05) == 0
    assert r.due(0.35) == 3  # chậm: phải bù để video không ngắn hơn thực tế
    r.wrote(3)
    assert r.due(0.35) == 0
    with pytest.raises(ValueError):
        record.Resampler(0, 0)


def test_record_writes_a_real_time_video_with_metadata_and_no_personal_data(tmp_path):
    clock = Clock()
    cam = FakeCamera(clock, per_read=0.2)  # 5 fps thực tế dù yêu cầu 10
    out = tmp_path / "clips" / "buoi1_clip01.avi"
    meta = record.record(out, seconds=3.0, camera=0, width=640, height=480, fps=10.0,
                         capture_factory=lambda idx: cam, clock=clock,
                         now_utc=lambda: __import__("datetime").datetime(2026, 11, 2, 3, 0, 0, tzinfo=__import__("datetime").timezone.utc))
    if not out.exists() or out.stat().st_size == 0:
        pytest.skip("OpenCV không ghi được video MJPG trên máy này")
    assert cam.released
    assert meta["actual_size"] == [64, 48] and meta["requested_size"] == [640, 480]
    assert meta["fps_captured_measured"] == pytest.approx(5.0, abs=0.6)
    assert 29 <= meta["frames_written"] <= 32  # ~3 s × 10 fps dù camera chỉ 5 fps
    cap = cv2.VideoCapture(str(out))
    assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == meta["frames_written"]
    cap.release()
    on_disk = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert on_disk["started_at"] == "2026-11-02T03:00:00Z"
    assert set(on_disk) == {"clip", "started_at", "seconds", "camera_index", "requested_size", "actual_size", "fps_written",
                            "fps_captured_measured", "frames_written", "frames_captured", "codec", "host"}


def test_record_fails_clearly_when_the_camera_is_missing(tmp_path):
    class Dead:
        def isOpened(self):
            return False

    with pytest.raises(RuntimeError, match="Không mở được camera"):
        record.record(tmp_path / "x.avi", 1, 0, 64, 48, 10, capture_factory=lambda i: Dead())
    with pytest.raises(RuntimeError, match="Không mở được camera"):
        record.snapshot(tmp_path / "x.jpg", 0, 64, 48, capture_factory=lambda i: Dead())


def test_snapshot_skips_warmup_frames_and_reports_the_real_size(tmp_path):
    clock = Clock()
    cam = FakeCamera(clock, per_read=0.0, size=(80, 60))
    w, h = record.snapshot(tmp_path / "shots" / "f.jpg", 0, 1280, 720, capture_factory=lambda i: cam, warmup_frames=5)
    assert (w, h) == (80, 60) and cam.reads == 5 and cam.released
    assert (tmp_path / "shots" / "f.jpg").stat().st_size > 0
