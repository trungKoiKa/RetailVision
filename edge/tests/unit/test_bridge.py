import io
import json
from datetime import datetime, timezone

import numpy as np

from retailvision.messaging.bridge import EdgeMessenger, parse_operator_ack
from retailvision.messaging.mqtt_client import ListLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.pipeline.capture import Frame
from retailvision.pipeline.runner import JsonlSink, apply_acks, process_frame
from schema_helper import errors
from test_pipeline import ScriptedDetector, make_pipeline, person

WALL0 = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
TOPICS = Topics("site01")
IMAGE = np.zeros((100, 100, 3), dtype=np.uint8)
CROWD = [person(i, 65 + i * 5) for i in range(5)]  # 5 người trong vùng chờ


def make(tmp_path):
    link = ListLink()
    messenger = EdgeMessenger(
        link,
        EnvelopeFactory("site01", "edge01", "v1"),
        TOPICS,
        profile="pilot",
        version="0.1.0",
        now=lambda: WALL0,
    )
    return link, messenger, make_pipeline(tmp_path), JsonlSink(io.StringIO())


def feed(pipeline, messenger, sink, ts, tracks):
    return process_frame(pipeline, ScriptedDetector([tracks]), sink, messenger, Frame(IMAGE, ts, 0))


def sent(link, topic):
    return [m for m in link.sent if m.topic == topic]


def overload(pipeline, messenger, sink):
    """Giữ 5 người trong vùng chờ đủ lâu để mở cảnh báo; trả về alert_id."""
    for second in range(0, 70):
        feed(pipeline, messenger, sink, float(second), CROWD)
    return pipeline.alert.alert_id


def test_hello_is_retained_online_and_will_is_retained_offline(tmp_path):
    _, messenger, _, _ = make(tmp_path)
    online = messenger.hello()[0]
    will = messenger.will()
    assert (online.topic, online.qos, online.retain, online.payload["status"]) == (TOPICS.edge_status, 1, True, "ONLINE")
    assert (will.qos, will.retain, will.payload["status"]) == (1, True, "OFFLINE")
    assert errors("status", online.payload) == [] and errors("status", will.payload) == []


def test_close_publishes_offline_then_closes_link(tmp_path):
    link, messenger, _, _ = make(tmp_path)
    messenger.close()
    assert link.closed and link.sent[-1].payload["status"] == "OFFLINE"


def test_crossing_event_is_published_and_matches_schema(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    for ts, x in [(0.0, 60), (0.5, 55), (1.0, 40), (1.5, 35)]:  # phải→trái qua vạch x=50
        feed(pipeline, messenger, sink, ts, [person(1, x)])
    crossings = sent(link, TOPICS.crossing)
    assert len(crossings) == 1
    body = crossings[0].payload
    assert (body["direction"], body["profile"], body["line_id"]) == ("IN", "pilot", "main")
    assert crossings[0].qos == 1 and errors("crossing", body) == []


def test_state_is_published_once_per_second_at_qos0(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    for ts in [0.0, 0.3, 0.6, 1.0, 1.4, 2.1]:
        feed(pipeline, messenger, sink, ts, [])
    states = sent(link, TOPICS.state)
    assert len(states) == 3  # giây 0, 1, 2
    assert all(m.qos == 0 and not m.retain and errors("state", m.payload) == [] for m in states)
    assert states[0].payload["state"] == "NORMAL" and states[0].payload["queue_count"] == 0


def test_occurred_at_follows_frame_time_from_first_frame(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    feed(pipeline, messenger, sink, 100.0, [])  # neo ts=100 vào WALL0
    feed(pipeline, messenger, sink, 102.5, [])
    states = sent(link, TOPICS.state)
    assert states[-1].payload["occurred_at"] == "2026-11-02T10:00:02.500Z"


def test_stale_reports_unknown_with_null_count_and_ends_open_alert(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    alert_id = overload(pipeline, messenger, sink)
    assert alert_id is not None
    events = pipeline.stale(80.0)
    messenger.publish_events(80.0, events)
    messenger.on_idle(80.0, pipeline)
    end = sent(link, TOPICS.alert)[-1].payload
    assert (end["transition"], end["reason"], end["alert_id"]) == ("END", "INTERRUPTED", alert_id)
    state = sent(link, TOPICS.state)[-1].payload
    assert (state["state"], state["queue_count"]) == ("UNKNOWN", None)
    assert errors("state", state) == [] and errors("alert", end) == []


def test_overload_open_is_published_once(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    alert_id = overload(pipeline, messenger, sink)
    opens = [m.payload for m in sent(link, TOPICS.alert) if m.payload["transition"] == "OPEN"]
    assert [o["alert_id"] for o in opens] == [alert_id]
    assert errors("alert", opens[0]) == []
    state = sent(link, TOPICS.state)[-1].payload
    assert (state["state"], state["alert_id"], state["acked"]) == ("OVERLOAD", alert_id, False)


def ack_payload(alert_id, ack_id="9d0c1b2a-3e4f-4a5b-9c6d-7e8f9a0b1c2d", device="node01"):
    return json.dumps({"ack_id": ack_id, "alert_id": alert_id, "device_id": device}).encode()


def test_valid_ack_is_applied_once_keeps_overload_and_is_published(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    alert_id = overload(pipeline, messenger, sink)
    link.inbox.put((TOPICS.operator_ack, ack_payload(alert_id)))
    link.inbox.put((TOPICS.operator_ack, ack_payload(alert_id)))  # ESP32 gửi lặp cùng ack_id
    apply_acks(pipeline, messenger, sink, 70.0)
    acks = [m.payload for m in sent(link, TOPICS.alert) if m.payload["transition"] == "ACK"]
    assert len(acks) == 1
    assert acks[0]["ack_device_id"] == "node01" and errors("alert", acks[0]) == []
    assert pipeline.alert.state.value == "OVERLOAD" and pipeline.alert.acked  # ACK không đóng cảnh báo


def test_ack_for_other_alert_is_ignored(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    overload(pipeline, messenger, sink)
    link.inbox.put((TOPICS.operator_ack, ack_payload("11111111-2222-4333-8444-555555555555")))
    apply_acks(pipeline, messenger, sink, 70.0)
    assert not [m for m in sent(link, TOPICS.alert) if m.payload["transition"] == "ACK"]
    assert not pipeline.alert.acked


def test_ack_when_no_alert_is_ignored(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    feed(pipeline, messenger, sink, 0.0, [])
    link.inbox.put((TOPICS.operator_ack, ack_payload("11111111-2222-4333-8444-555555555555")))
    apply_acks(pipeline, messenger, sink, 1.0)
    assert not sent(link, TOPICS.alert)


def test_parse_operator_ack_rejects_bad_payloads():
    good = ack_payload("5b8e2f10-1c3d-4e5f-8a6b-7c8d9e0f1a2b")
    assert parse_operator_ack(good, "node01") is not None
    assert parse_operator_ack(b"not json", "node01") is None
    assert parse_operator_ack(b"[1,2]", "node01") is None
    assert parse_operator_ack(good.replace(b"node01", b"intruder"), "node01") is None
    assert parse_operator_ack(ack_payload("not-a-uuid"), "node01") is None
    extra = json.loads(good)
    extra["extra"] = 1
    assert parse_operator_ack(json.dumps(extra).encode(), "node01") is None


def test_ack_on_wrong_topic_is_ignored(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    alert_id = overload(pipeline, messenger, sink)
    link.inbox.put(("retailvision/v1/site01/other/events/operator-ack", ack_payload(alert_id)))
    apply_acks(pipeline, messenger, sink, 70.0)
    assert not pipeline.alert.acked


def test_telemetry_published_when_minute_closes_with_gap_minute_reported(tmp_path):
    link, messenger, pipeline, sink = make(tmp_path)
    feed(pipeline, messenger, sink, 10.0, [person(1, 70)])
    messenger.on_idle(130.0, pipeline)  # không có khung nào trong 2 phút tiếp theo
    tel = [m.payload for m in sent(link, TOPICS.telemetry)]
    assert [t["valid_seconds"] for t in tel] == [1, 0]
    assert tel[1]["queue_avg"] is None and tel[1]["queue_max"] is None
    assert all(errors("telemetry", t) == [] for t in tel)
