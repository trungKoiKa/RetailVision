"""T12 và T17 phía edge: dừng/khởi động lại broker thật. Edge vẫn phân tích, tự nối lại, gửi lại ONLINE và sự kiện QoS 1."""

import io
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from retailvision.config.loader import load_config
from retailvision.core.types import Track
from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import MqttLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.pipeline.capture import Frame
from retailvision.pipeline.runner import JsonlSink, Pipeline, process_frame

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))
from test_mqtt_broker import Listener, find_mosquitto, free_port  # noqa: E402
from test_pipeline import CONFIG  # noqa: E402

TOPICS = Topics("site01")
IMAGE = np.zeros((100, 100, 3), dtype=np.uint8)


class Broker:
    """Mosquitto có thể dừng và bật lại trên cùng một cổng."""

    def __init__(self, tmp_path):
        self.exe = find_mosquitto()
        if self.exe is None:
            pytest.skip("không tìm thấy mosquitto")
        self.port = free_port()
        self.conf = tmp_path / "b.conf"
        self.conf.write_text(f"listener {self.port} 127.0.0.1\nallow_anonymous true\npersistence false\n", encoding="utf-8")
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen([self.exe, "-c", str(self.conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import socket

        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close()
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("mosquitto không lên")

    def stop(self):
        if self.proc is not None:
            self.proc.kill()
            self.proc.wait(timeout=5)
            self.proc = None


@pytest.fixture
def broker(tmp_path):
    b = Broker(tmp_path)
    b.start()
    yield b
    b.stop()


def make_edge(port, tmp_path):
    cfg = tmp_path / "site.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    config = load_config(cfg)
    messenger = EdgeMessenger(None, EnvelopeFactory("site01", "edge01", "v1"), TOPICS, profile="pilot", version="0.1.0")
    link = MqttLink("127.0.0.1", port, "edge01-recovery", None, None, will=messenger.will(),
                    on_connect_messages=messenger.hello, subscriptions=[(TOPICS.operator_ack, 0)])
    messenger.attach(link)
    return messenger, Pipeline(config, (100, 100)), link


class Detector:
    def __init__(self):
        self.tracks = []

    def process(self, image):
        return self.tracks


def step(pipeline, detector, messenger, ts):
    return process_frame(pipeline, detector, JsonlSink(io.StringIO()), messenger, Frame(IMAGE, ts, 0))


def wait_connected(link, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if link._client.is_connected():
            return
        time.sleep(0.1)
    raise AssertionError("edge không nối lại được broker")


def test_t12_t17_broker_stop_and_restart(broker, tmp_path):
    messenger, pipeline, link = make_edge(broker.port, tmp_path)
    detector = Detector()
    wait_connected(link)
    watcher = Listener(broker.port, "retailvision/v1/site01/edge01/#")
    for second in range(3):
        step(pipeline, detector, messenger, float(second))
        time.sleep(0.05)
    watcher.wait_for(lambda r: r[0] == TOPICS.state)

    # --- T12: dừng broker; edge vẫn phân tích, không lỗi, không treo ---
    watcher.stop()
    broker.stop()
    time.sleep(0.5)
    started = time.time()
    for second in range(3, 12):
        detector.tracks = [Track(1, (60.0, 50.0), (0, 0, 0, 0), 0.9), Track(1, (55.0, 50.0), (0, 0, 0, 0), 0.9)] if second == 5 else []
        step(pipeline, detector, messenger, float(second))
    assert time.time() - started < 3, "mất broker không được làm chậm vòng phân tích"
    # một lượt qua vạch xảy ra trong lúc mất broker (QoS 1: paho giữ trong RAM)
    detector.tracks = [Track(9, (60.0, 50.0), (0, 0, 0, 0), 0.9)]
    step(pipeline, detector, messenger, 12.0)
    step(pipeline, detector, messenger, 12.5)
    detector.tracks = [Track(9, (40.0, 50.0), (0, 0, 0, 0), 0.9)]
    step(pipeline, detector, messenger, 13.0)
    step(pipeline, detector, messenger, 13.5)

    # --- T17: broker bật lại; edge tự nối lại ---
    broker.start()
    # đăng ký trước khi edge nối lại: bản tin QoS 1 đang chờ được gửi ngay khi nối lại và không retain
    late = Listener(broker.port, "retailvision/v1/site01/edge01/#")
    wait_connected(link)
    _, online, _ = late.wait_for(lambda r: r[0] == TOPICS.edge_status, timeout=10)
    assert online["status"] == "ONLINE"  # nối lại thì gửi lại ONLINE
    crossing = late.wait_for(lambda r: r[0] == TOPICS.crossing, timeout=10)  # gửi lại từ hàng đợi RAM
    assert crossing[1]["direction"] == "IN"
    step(pipeline, Detector(), messenger, 15.0)
    late.wait_for(lambda r: r[0] == TOPICS.state, timeout=10)  # state lại chảy
    late.stop()
    # broker mới không còn gì từ phiên trước; ONLINE gửi lại phải được giữ (retained) cho client đến sau
    fresh = Listener(broker.port, TOPICS.edge_status)
    _, online, retained = fresh.wait_for(lambda r: True)
    assert retained and online["status"] == "ONLINE"
    fresh.stop()
    messenger.close()
