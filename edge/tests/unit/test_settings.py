"""P1: đổi ngưỡng từ web. T15 (lệnh trùng), T16 (off_count >= on_count bị từ chối, giữ cấu hình cũ)."""

import io
import json
import uuid
from datetime import datetime, timezone

import numpy as np
import pytest

from retailvision.config.loader import load_config
from retailvision.config.settings import OperatingSettings, SettingsStore
from retailvision.core.types import Track
from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import ListLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.pipeline.capture import Frame
from retailvision.pipeline.runner import JsonlSink, Pipeline, process_frame
from retailvision.pipeline.settings_service import REMEMBER_REQUESTS, SettingsService
from schema_helper import errors
from test_pipeline import CONFIG

TOPICS = Topics("site01")
DEFAULTS = OperatingSettings(dwell_seconds=2.0, on_count=5, on_hold_seconds=60.0, off_count=3, off_hold_seconds=10.0)
CROWD = [Track(i, (65.0 + i * 5, 50.0), (0, 0, 0, 0), 0.9) for i in range(5)]
IMAGE = np.zeros((100, 100, 3), dtype=np.uint8)


def command(revision=0, **overrides):
    body = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "site_id": "site01",
        "device_id": "edge01",
        "session_id": str(uuid.uuid4()),
        "seq": 0,
        "occurred_at": "2026-11-02T10:40:00.000Z",
        "config_version": "backend",
        "request_id": str(uuid.uuid4()),
        "expected_settings_revision": revision,
        "dwell_seconds": 3,
        "on_count": 4,
        "on_hold_seconds": 30,
        "off_count": 2,
        "off_hold_seconds": 5,
    }
    body.update(overrides)
    return body


@pytest.fixture
def config(tmp_path):
    p = tmp_path / "site.yaml"
    p.write_text(CONFIG, encoding="utf-8")
    return load_config(p)


@pytest.fixture
def store(tmp_path):
    return SettingsStore(tmp_path / "state" / "settings.json")


def make(config, store):
    service = SettingsService.start(OperatingSettings.from_config(config), store)
    pipeline = Pipeline(config, (100, 100), service.current, service.revision)
    return service, pipeline


# --- OperatingSettings ---------------------------------------------------------------------


def test_defaults_come_from_config(config):
    assert OperatingSettings.from_config(config) == DEFAULTS
    assert DEFAULTS.problems() == []


@pytest.mark.parametrize(
    "field,value",
    [("dwell_seconds", -1), ("dwell_seconds", 61), ("on_count", 0), ("on_count", 101), ("on_hold_seconds", 3601),
     ("off_count", -1), ("off_hold_seconds", -0.1), ("on_count", 2.5), ("dwell_seconds", "2"), ("on_count", True),
     ("dwell_seconds", float("nan"))],
)
def test_out_of_range_or_wrongly_typed_values_are_reported(field, value):
    s = OperatingSettings(**{**DEFAULTS.__dict__, field: value})
    assert s.problems(), (field, value)


def test_off_count_must_be_below_on_count():
    assert OperatingSettings(2.0, 3, 60.0, 3, 10.0).problems() == ["off_count phải nhỏ hơn on_count"]
    assert OperatingSettings(2.0, 3, 60.0, 4, 10.0).problems()
    assert OperatingSettings(2.0, 3, 60.0, 2, 10.0).problems() == []


# --- SettingsStore -------------------------------------------------------------------------


def test_store_round_trip_and_atomic_write(store):
    store.save(3, DEFAULTS)
    assert store.load() == (3, DEFAULTS)
    assert not list(store._path.parent.glob("*.tmp"))  # không để lại file tạm


def test_store_ignores_missing_corrupt_or_invalid_files(tmp_path):
    assert SettingsStore(None).load() is None
    SettingsStore(None).save(1, DEFAULTS)  # không lưu gì, không lỗi
    path = tmp_path / "s.json"
    assert SettingsStore(path).load() is None
    path.write_text("{khong phai json", encoding="utf-8")
    assert SettingsStore(path).load() is None
    path.write_text(json.dumps({"revision": 1, "dwell_seconds": 2, "on_count": 2, "on_hold_seconds": 1, "off_count": 5, "off_hold_seconds": 1}))
    assert SettingsStore(path).load() is None  # off_count >= on_count: không tin file này
    path.write_text(json.dumps({"revision": -1, "dwell_seconds": 2, "on_count": 5, "on_hold_seconds": 1, "off_count": 1, "off_hold_seconds": 1}))
    assert SettingsStore(path).load() is None


# --- SettingsService -----------------------------------------------------------------------


def test_valid_command_is_applied_as_a_whole_and_persisted(config, store):
    service, pipeline = make(config, store)
    events, result = service.handle(command(), pipeline, 10.0)
    assert (result.result, result.revision, result.reason) == ("APPLIED", 1, None)
    assert service.revision == 1 and pipeline.settings_revision == 1
    a = pipeline.alert.settings
    assert (a.on_count, a.on_hold_seconds, a.off_count, a.off_hold_seconds) == (4, 30, 2, 5)
    assert pipeline.zone._dwell == 3
    assert store.load() == (1, OperatingSettings(3.0, 4, 30.0, 2, 5.0))
    assert events == []  # không có cảnh báo đang mở


def test_t16_off_count_not_below_on_count_is_rejected_and_old_config_kept(config, store):
    service, pipeline = make(config, store)
    _, result = service.handle(command(on_count=3, off_count=3), pipeline, 1.0)
    assert result.result == "REJECTED" and "off_count" in result.reason
    assert result.revision == 0 and service.current == DEFAULTS
    assert pipeline.alert.settings.on_count == 5 and pipeline.zone._dwell == 2.0
    assert store.load() is None  # không ghi gì


def test_zero_on_count_example_from_the_contract_is_rejected(config, store):
    from schema_helper import CONTRACTS

    invalid = json.loads((CONTRACTS / "examples" / "invalid" / "settings-set__zero_on_count.json").read_text(encoding="utf-8"))
    service, pipeline = make(config, store)
    _, result = service.handle(invalid, pipeline, 1.0)
    assert result.result == "REJECTED" and service.revision == 0


def test_stale_revision_never_overwrites(config, store):
    service, pipeline = make(config, store)
    service.handle(command(0), pipeline, 1.0)  # lên revision 1
    _, result = service.handle(command(0, on_count=9, off_count=1), pipeline, 2.0)  # dựa trên revision cũ
    assert result.result == "REJECTED" and "revision cũ" in result.reason
    assert result.revision == 1 and pipeline.alert.settings.on_count == 4


def test_t15_duplicate_request_applies_once_and_repeats_the_same_answer(config, store):
    service, pipeline = make(config, store)
    cmd = command(0)
    _, first = service.handle(cmd, pipeline, 1.0)
    _, again = service.handle(cmd, pipeline, 2.0)  # QoS 1 giao lại
    assert first == again and service.revision == 1
    _, third = service.handle(cmd, pipeline, 3.0)
    assert third == first and service.revision == 1


def test_duplicate_of_a_rejected_request_stays_rejected(config, store):
    service, pipeline = make(config, store)
    cmd = command(5)  # revision sai
    _, first = service.handle(cmd, pipeline, 1.0)
    _, again = service.handle(cmd, pipeline, 2.0)
    assert first.result == again.result == "REJECTED" and first == again


def test_identical_settings_are_a_no_op_without_a_new_revision(config, store):
    service, pipeline = make(config, store)
    _, result = service.handle(command(0, dwell_seconds=2, on_count=5, on_hold_seconds=60, off_count=3, off_hold_seconds=10), pipeline, 1.0)
    assert (result.result, result.revision) == ("APPLIED", 0)
    assert store.load() is None


def test_missing_or_mistyped_fields_are_rejected(config, store):
    service, pipeline = make(config, store)
    missing = command()
    del missing["on_hold_seconds"]
    _, r1 = service.handle(missing, pipeline, 1.0)
    assert r1.result == "REJECTED" and "on_hold_seconds" in r1.reason
    _, r2 = service.handle(command(on_count="five"), pipeline, 1.0)
    assert r2.result == "REJECTED"
    _, r3 = service.handle(command(expected_settings_revision="0"), pipeline, 1.0)
    assert r3.result == "REJECTED"
    assert service.revision == 0


def test_command_without_a_valid_request_id_gets_no_reply(config, store):
    service, pipeline = make(config, store)
    assert service.handle(command(request_id="not-a-uuid"), pipeline, 1.0) == ([], None)
    cmd = command()
    del cmd["request_id"]
    assert service.handle(cmd, pipeline, 1.0) == ([], None)


def test_open_alert_ends_with_config_changed_and_timers_restart(config, store):
    service, pipeline = make(config, store)
    for t in range(0, 65):
        pipeline.step(CROWD, float(t))
    assert pipeline.alert.state.value == "OVERLOAD"
    alert_id = pipeline.alert.alert_id
    events, result = service.handle(command(0), pipeline, 65.0)
    ends = [e for e in events if e["type"] == "alert"]
    assert len(ends) == 1 and ends[0]["kind"] == "END" and ends[0]["reason"] == "CONFIG_CHANGED" and ends[0]["alert_id"] == alert_id
    assert pipeline.alert.state.value == "NORMAL"
    assert result.result == "APPLIED"


def test_only_recent_request_ids_are_remembered(config, store):
    service, pipeline = make(config, store)
    first = command(0)
    service.handle(first, pipeline, 0.0)
    for i in range(REMEMBER_REQUESTS + 5):
        service.handle(command(service.revision, on_count=10 + (i % 80), off_count=1), pipeline, float(i))
    assert len(service._seen) == REMEMBER_REQUESTS
    assert first["request_id"] not in service._seen


def test_service_restores_saved_settings_after_restart(config, store):
    service, pipeline = make(config, store)
    service.handle(command(0), pipeline, 1.0)
    # restart: dựng lại từ file
    service2, pipeline2 = make(config, store)
    assert service2.revision == 1 and service2.current == OperatingSettings(3.0, 4, 30.0, 2, 5.0)
    assert pipeline2.alert.settings.on_count == 4 and pipeline2.settings_revision == 1


def test_corrupt_store_falls_back_to_config_instead_of_refusing_to_start(config, tmp_path):
    path = tmp_path / "s.json"
    path.write_text("garbage", encoding="utf-8")
    service = SettingsService.start(OperatingSettings.from_config(config), SettingsStore(path))
    assert service.current == DEFAULTS and service.revision == 0


# --- hợp đồng bản tin ----------------------------------------------------------------------


def test_settings_result_payloads_match_the_schema():
    f = EnvelopeFactory("site01", "edge01", "v1")
    now = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    rid = str(uuid.uuid4())
    assert errors("settings-result", f.settings_result(now, rid, "APPLIED", 1, None)) == []
    assert errors("settings-result", f.settings_result(now, rid, "REJECTED", 0, "revision cũ")) == []


def test_the_valid_contract_example_command_is_accepted_by_the_service(config, store):
    from schema_helper import CONTRACTS

    example = json.loads((CONTRACTS / "examples" / "valid" / "settings-set__ok.json").read_text(encoding="utf-8"))
    assert errors("settings-set", example) == []
    service, pipeline = make(config, store)
    _, result = service.handle(example, pipeline, 1.0)
    assert result.result == "APPLIED"  # giống giá trị mặc định nên không đổi revision
    assert result.revision == 0


# --- messenger + runner --------------------------------------------------------------------


def make_messenger():
    link = ListLink()
    messenger = EdgeMessenger(
        link, EnvelopeFactory("site01", "edge01", "v1"), TOPICS, profile="pilot", version="0.1.0",
        now=lambda: datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
    )
    return link, messenger


def test_polling_acks_does_not_swallow_settings_commands_and_vice_versa():
    link, messenger = make_messenger()
    ack = {"ack_id": str(uuid.uuid4()), "alert_id": str(uuid.uuid4()), "device_id": "node01"}
    link.inbox.put((TOPICS.settings_set, json.dumps(command()).encode()))
    link.inbox.put((TOPICS.operator_ack, json.dumps(ack).encode()))
    assert messenger.poll_acks() == [ack]
    assert len(messenger.poll_settings()) == 1  # lệnh vẫn còn dù ACK đã được đọc trước
    assert messenger.poll_settings() == [] and messenger.poll_acks() == []


def test_commands_for_another_device_or_garbage_are_dropped():
    link, messenger = make_messenger()
    link.inbox.put((TOPICS.settings_set, json.dumps(command(device_id="edge99")).encode()))
    link.inbox.put((TOPICS.settings_set, json.dumps(command(site_id="site02")).encode()))
    link.inbox.put((TOPICS.settings_set, b"khong phai json"))
    link.inbox.put((TOPICS.settings_set, b"[1,2]"))
    assert messenger.poll_settings() == []


def feed(pipeline, messenger, service, ts, tracks):
    class D:
        def process(self, image):
            return tracks

    return process_frame(pipeline, D(), JsonlSink(io.StringIO()), messenger, Frame(IMAGE, ts, 0), settings=service)


def sent(link, topic):
    return [m.payload for m in link.sent if m.topic == topic]


def test_runner_replies_with_a_valid_result_and_state_reports_the_new_revision(config, store):
    link, messenger = make_messenger()
    service, pipeline = make(config, store)
    link.inbox.put((TOPICS.settings_set, json.dumps(command()).encode()))
    feed(pipeline, messenger, service, 0.0, [])
    results = sent(link, TOPICS.settings_result)
    assert len(results) == 1 and errors("settings-result", results[0]) == []
    assert (results[0]["result"], results[0]["settings_revision"]) == ("APPLIED", 1)
    feed(pipeline, messenger, service, 1.0, [])
    state = sent(link, TOPICS.state)[-1]
    assert state["settings_revision"] == 1 and errors("state", state) == []


def test_runner_publishes_end_config_changed_when_an_alert_is_open(config, store):
    link, messenger = make_messenger()
    service, pipeline = make(config, store)
    for t in range(0, 65):
        feed(pipeline, messenger, service, float(t), CROWD)
    link.inbox.put((TOPICS.settings_set, json.dumps(command()).encode()))
    feed(pipeline, messenger, service, 65.0, CROWD)
    ends = [a for a in sent(link, TOPICS.alert) if a["transition"] == "END"]
    assert [e["reason"] for e in ends] == ["CONFIG_CHANGED"]
    assert errors("alert", ends[0]) == []


def test_runner_answers_each_request_once_even_when_redelivered(config, store):
    link, messenger = make_messenger()
    service, pipeline = make(config, store)
    cmd = command()
    for _ in range(3):
        link.inbox.put((TOPICS.settings_set, json.dumps(cmd).encode()))
    feed(pipeline, messenger, service, 0.0, [])
    results = sent(link, TOPICS.settings_result)
    assert len(results) == 3 and {r["settings_revision"] for r in results} == {1}  # cùng một câu trả lời, chỉ áp dụng một lần
    assert service.revision == 1
