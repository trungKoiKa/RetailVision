"""Thử với Mosquitto thật (tự khởi động trên cổng ngẫu nhiên, không tài khoản). Bỏ qua nếu không có mosquitto.

Tìm mosquitto theo thứ tự: biến RV_MOSQUITTO_BIN, PATH, thư mục cài mặc định trên Windows.
Kiểm tra ACL/tài khoản không nằm ở đây mà ở deploy/pi/scripts/check_acl.py.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import MqttLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))
from schema_helper import errors  # noqa: E402
from test_pipeline import make_pipeline  # noqa: E402

TOPICS = Topics("site01")


def find_mosquitto():
    candidates = [os.environ.get("RV_MOSQUITTO_BIN"), shutil.which("mosquitto"), r"C:\Program Files\mosquitto\mosquitto.exe"]
    return next((c for c in candidates if c and Path(c).is_file()), None)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def broker(tmp_path):
    exe = find_mosquitto()
    if exe is None:
        pytest.skip("không tìm thấy mosquitto")
    port = free_port()
    conf = tmp_path / "test.conf"
    conf.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n", encoding="utf-8")
    proc = subprocess.Popen([exe, "-c", str(conf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("mosquitto không khởi động được")
    yield port
    proc.terminate()
    proc.wait(timeout=5)


class Listener:
    def __init__(self, port, *topics):
        import paho.mqtt.client as mqtt

        self.received = []
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test-{uuid.uuid4()}", protocol=mqtt.MQTTv311)
        self.client.on_message = lambda c, u, m: self.received.append((m.topic, json.loads(m.payload), m.retain))
        self.client.connect("127.0.0.1", port, 15)
        self.client.loop_start()
        for t in topics:
            self.client.subscribe(t, qos=1)
        time.sleep(0.3)

    def wait_for(self, predicate, timeout=4.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            hits = [r for r in self.received if predicate(r)]
            if hits:
                return hits[0]
            time.sleep(0.05)
        raise AssertionError(f"không nhận được bản tin mong đợi; đã nhận: {[r[0] for r in self.received]}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


def make_edge(port):
    messenger = EdgeMessenger(None, EnvelopeFactory("site01", "edge01", "v1"), TOPICS, profile="pilot", version="0.1.0")
    link = MqttLink(
        "127.0.0.1", port, "edge01-test", None, None,
        will=messenger.will(),
        on_connect_messages=messenger.hello,
        subscriptions=[(TOPICS.operator_ack, 0)],
    )
    messenger.attach(link)
    return messenger, link


def test_online_is_retained_state_flows_and_close_publishes_offline(broker, tmp_path):
    messenger, _ = make_edge(broker)
    time.sleep(0.5)
    late = Listener(broker, f"retailvision/v1/site01/edge01/#")  # đăng ký sau khi edge đã nối
    topic, body, retained = late.wait_for(lambda r: r[0] == TOPICS.edge_status)
    assert retained and body["status"] == "ONLINE" and errors("status", body) == []

    pipeline = make_pipeline(tmp_path)
    messenger.on_idle(0.0, pipeline)
    _, state, retained = late.wait_for(lambda r: r[0] == TOPICS.state)
    assert not retained and state["state"] == "UNKNOWN" and state["queue_count"] is None
    assert errors("state", state) == []

    messenger.close()
    late.wait_for(lambda r: r[0] == TOPICS.edge_status and r[1]["status"] == "OFFLINE")
    late.stop()


def test_operator_ack_from_node_reaches_edge(broker):
    messenger, _ = make_edge(broker)
    node = Listener(broker)
    ack = {"ack_id": str(uuid.uuid4()), "alert_id": str(uuid.uuid4()), "device_id": "node01"}
    time.sleep(0.5)
    node.client.publish(TOPICS.operator_ack, json.dumps(ack), qos=0)
    deadline = time.time() + 4
    got = []
    while time.time() < deadline and not got:
        got = messenger.poll_acks()
        time.sleep(0.05)
    assert got == [ack]
    node.stop()
    messenger.close()


def test_abrupt_disconnect_triggers_last_will_offline(broker):
    watcher = Listener(broker, TOPICS.edge_status)
    _, link = make_edge(broker)
    watcher.wait_for(lambda r: r[1]["status"] == "ONLINE")
    link._client.loop_stop()
    link._client._sock.close()  # rớt mạng đột ngột, không gửi DISCONNECT
    _, body, _ = watcher.wait_for(lambda r: r[1]["status"] == "OFFLINE")
    assert errors("status", body) == []
    watcher.stop()
    # cờ retain chỉ hiện với client đăng ký sau: bản OFFLINE phải còn trong broker
    late = Listener(broker, TOPICS.edge_status)
    _, body, retained = late.wait_for(lambda r: True)
    assert retained and body["status"] == "OFFLINE"
    late.stop()
