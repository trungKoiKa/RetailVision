"""P1 qua broker thật: lệnh settings/set đi vào edge, kết quả settings/result đi ra đúng contract."""

import io
import json
import sys
import time
import uuid
from pathlib import Path

import numpy as np

from retailvision.config.loader import load_config
from retailvision.config.settings import OperatingSettings, SettingsStore
from retailvision.core.types import Track
from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import MqttLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.pipeline.capture import Frame
from retailvision.pipeline.runner import JsonlSink, Pipeline, process_frame
from retailvision.pipeline.settings_service import SettingsService

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))
from test_mqtt_broker import Listener, broker  # noqa: E402,F401  (fixture `broker`)
from test_pipeline import CONFIG  # noqa: E402
from schema_helper import errors  # noqa: E402

TOPICS = Topics("site01")
IMAGE = np.zeros((100, 100, 3), dtype=np.uint8)


class Idle:
    def process(self, image):
        return []


def test_command_over_a_real_broker_is_applied_and_answered(broker, tmp_path):
    cfg = tmp_path / "site.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    config = load_config(cfg)
    store = SettingsStore(tmp_path / "s.json")
    service = SettingsService.start(OperatingSettings.from_config(config), store)
    pipeline = Pipeline(config, (100, 100), service.current, service.revision)
    messenger = EdgeMessenger(None, EnvelopeFactory("site01", "edge01", "v1"), TOPICS, profile="pilot", version="0.1.0")
    link = MqttLink("127.0.0.1", broker, "edge01-settings", None, None, will=messenger.will(),
                    on_connect_messages=messenger.hello,
                    subscriptions=[(TOPICS.operator_ack, 0), (TOPICS.settings_set, 1)])
    messenger.attach(link)
    watcher = Listener(broker, TOPICS.settings_result, TOPICS.alert)
    sender = Listener(broker)
    deadline = time.time() + 10
    while not link._client.is_connected() and time.time() < deadline:
        time.sleep(0.1)
    time.sleep(0.5)

    request_id = str(uuid.uuid4())
    command = {
        "schema_version": 1, "event_id": str(uuid.uuid4()), "site_id": "site01", "device_id": "edge01",
        "session_id": str(uuid.uuid4()), "seq": 0, "occurred_at": "2026-11-02T10:40:00.000Z", "config_version": "backend",
        "request_id": request_id, "expected_settings_revision": 0, "dwell_seconds": 3, "on_count": 4,
        "on_hold_seconds": 30, "off_count": 2, "off_hold_seconds": 5,
    }
    assert errors("settings-set", command) == []
    sender.client.publish(TOPICS.settings_set, json.dumps(command), qos=1)

    for second in range(0, 40):  # vòng khung hình của edge
        process_frame(pipeline, Idle(), JsonlSink(io.StringIO()), messenger, Frame(IMAGE, float(second), 0), settings=service)
        if any(r[0] == TOPICS.settings_result for r in watcher.received):
            break
        time.sleep(0.1)

    _, result, _ = watcher.wait_for(lambda r: r[0] == TOPICS.settings_result, timeout=5)
    assert errors("settings-result", result) == []
    assert (result["request_id"], result["result"], result["settings_revision"]) == (request_id, "APPLIED", 1)
    assert pipeline.alert.settings.on_count == 4 and store.load()[0] == 1

    # gửi lại cùng lệnh (broker giao trùng): chỉ trả lời, không áp dụng lần hai
    watcher.received.clear()
    sender.client.publish(TOPICS.settings_set, json.dumps(command), qos=1)
    for second in range(40, 80):
        process_frame(pipeline, Idle(), JsonlSink(io.StringIO()), messenger, Frame(IMAGE, float(second), 0), settings=service)
        if watcher.received:
            break
        time.sleep(0.1)
    _, again, _ = watcher.wait_for(lambda r: r[0] == TOPICS.settings_result, timeout=5)
    assert again["result"] == "APPLIED" and again["settings_revision"] == 1 and service.revision == 1

    watcher.stop()
    sender.stop()
    messenger.close()
