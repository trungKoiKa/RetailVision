"""NFR-04: đo độ trễ. Dữ liệu dựng tay để kiểm công thức, không phải số đo."""

import sys
from pathlib import Path

import pytest

from retailvision.app import _write_latency
from retailvision.config.loader import load_config
from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import ListLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.pipeline.runner import JsonlSink, run_camera_loop
from test_camera_recovery import CONFIG, World

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation" / "tools"))
import latency_echo  # noqa: E402
import metrics  # noqa: E402


def test_percentile_and_summary():
    assert metrics.percentile([], 0.95) is None
    values = list(range(1, 101))  # 1..100
    assert metrics.percentile(values, 0.95) == 95
    assert metrics.percentile(values, 0.5) == 50
    assert metrics.percentile([7], 0.95) == 7
    s = metrics.latency_summary([10, 20, 30, 40])
    assert (s["n"], s["p50_ms"], s["max_ms"]) == (4, 20, 40)
    empty = metrics.latency_summary([])
    assert empty["n"] == 0 and empty["p95_ms"] is None and empty["max_ms"] is None  # không có mẫu: không phải 0


def test_echo_matcher_measures_each_state_once_and_counts_losses():
    m = latency_echo.EchoMatcher(timeout_s=2.0)
    m.on_state(1, 100.000)
    m.on_state(2, 101.000)
    m.on_state(3, 102.000)
    assert m.on_echo(1, 100.120) == pytest.approx(120.0)
    assert m.on_echo(1, 100.500) is None  # echo trùng không tính hai lần
    assert m.on_echo(2, 101.300) == pytest.approx(300.0)
    assert m.on_echo(99, 101.0) is None  # echo của state không biết
    assert m.expire(103.0) == 0  # state 3 mới 1 s
    assert m.expire(104.5) == 1  # state 3 quá 2 s chưa có echo: mất
    s = m.summary()
    assert (s["n"], s["states"], s["lost"]) == (2, 3, 1)
    assert s["loss_rate"] == pytest.approx(1 / 3)
    assert s["p95_ms"] == pytest.approx(300.0)


def test_echo_matcher_with_nothing_has_no_numbers():
    s = latency_echo.EchoMatcher().summary()
    assert s["n"] == 0 and s["p95_ms"] is None and s["loss_rate"] is None


def test_parse_utc_handles_z_suffix_and_milliseconds():
    assert latency_echo.parse_utc("2026-11-02T10:15:03.120Z") == pytest.approx(1793614503.12)


def test_camera_loop_records_per_frame_latency(tmp_path):
    class SlowWorld(World):
        def process(self, image):
            self.t += 0.12  # suy luận mất 120 ms
            return []

    cfg = tmp_path / "site.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    config = load_config(cfg)
    world = SlowWorld()
    link = ListLink()
    messenger = EdgeMessenger(link, EnvelopeFactory("site01", "edge01", "v1"), Topics("site01"), profile="pilot", version="0.1.0")
    ages: list = []
    start = world.t
    run_camera_loop(config, world.read, world, JsonlSink(__import__("io").StringIO()), messenger, None, latency_ms=ages,
                    clock=world.clock, sleep=world.sleep, should_stop=lambda: world.t - start > 2)
    assert len(ages) >= 5 and all(a == 120 for a in ages)  # chính là thời gian suy luận


def test_write_latency_file_and_summary(tmp_path, capsys):
    out = tmp_path / "lat" / "l.csv"
    _write_latency(out, [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "age_ms" and len(lines) == 11
    err = capsys.readouterr().err
    assert "n=10" in err and "p95=1000 ms" in err and "max=1000 ms" in err


def test_bench_account_in_the_acl_can_only_read():
    acl = (Path(__file__).resolve().parents[3] / "deploy" / "pi" / "mosquitto" / "acl.example").read_text(encoding="utf-8")
    users: dict = {}
    current = None
    for line in acl.splitlines():
        line = line.strip()
        if line.startswith("user "):
            current = line.split()[1]
            users[current] = []
        elif line.startswith("topic ") and current:
            _, mode, topic = line.split()
            users[current].append((mode, topic))
    assert set(users) == {"edge01", "node01", "backend01", "bench01"}
    assert all(mode == "read" for mode, _ in users["bench01"])  # công cụ đo không được ghi gì
    assert ("write", "retailvision/v1/site01/edge01/settings/set") in users["backend01"]
    assert ("write", "retailvision/v1/site01/edge01/settings/set") not in users["edge01"]
