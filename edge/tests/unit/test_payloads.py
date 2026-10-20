from datetime import datetime, timezone

from retailvision.messaging.payloads import EnvelopeFactory, iso_utc, minute_iso
from retailvision.messaging.topics import Topics
from schema_helper import errors

T = datetime(2026, 11, 2, 10, 15, 3, 120000, tzinfo=timezone.utc)
ALERT = "5b8e2f10-1c3d-4e5f-8a6b-7c8d9e0f1a2b"
ACK = "9d0c1b2a-3e4f-4a5b-9c6d-7e8f9a0b1c2d"


def factory():
    return EnvelopeFactory("site01", "edge01", "pilot-2026-11-01")


def test_iso_utc_has_milliseconds_and_z():
    assert iso_utc(T) == "2026-11-02T10:15:03.120Z"
    assert minute_iso(T) == "2026-11-02T10:15:00Z"


def test_non_utc_input_is_converted_to_utc():
    from datetime import timedelta

    local = T.astimezone(timezone(timedelta(hours=7)))
    assert iso_utc(local) == "2026-11-02T10:15:03.120Z"


def test_seq_increases_and_event_ids_differ():
    f = factory()
    a = f.crossing(T, "IN", 3, "main", "pilot")
    b = f.crossing(T, "OUT", 4, "main", "pilot")
    assert (a["seq"], b["seq"]) == (0, 1)
    assert a["event_id"] != b["event_id"]
    assert a["session_id"] == b["session_id"]


def test_crossing_matches_schema():
    assert errors("crossing", factory().crossing(T, "IN", 3, "main", "pilot")) == []


def test_alert_open_ack_end_match_schema():
    f = factory()
    assert errors("alert", f.alert(T, ALERT, "OPEN", queue_count=5)) == []
    assert errors("alert", f.alert(T, ALERT, "ACK", ack_id=ACK, ack_device_id="node01")) == []
    assert errors("alert", f.alert(T, ALERT, "END", reason="NORMALIZED", queue_count=2)) == []
    assert errors("alert", f.alert(T, ALERT, "END", reason="INTERRUPTED")) == []


def test_state_matches_schema_for_each_state():
    f = factory()
    assert errors("state", f.state(T, T, "NORMAL", 1, None, False)) == []
    assert errors("state", f.state(T, T, "OVERLOAD", 5, ALERT, True)) == []


def test_unknown_state_never_carries_a_count():
    payload = factory().state(T, T, "UNKNOWN", 4, None, False)
    assert payload["queue_count"] is None
    assert errors("state", payload) == []


def test_telemetry_with_and_without_data_matches_schema():
    f = factory()
    assert errors("telemetry", f.telemetry(T, T, 58, 1.25, 4, 12.5, 180)) == []
    assert errors("telemetry", f.telemetry(T, T, 0, None, None, 0.0, 0)) == []


def test_status_online_offline_match_schema():
    f = factory()
    assert errors("status", f.status(T, "ONLINE", "0.1.0", True)) == []
    assert errors("status", f.status(T, "OFFLINE", "0.1.0", False)) == []


def test_topics_follow_contract_names():
    t = Topics("site01")
    assert t.state == "retailvision/v1/site01/edge01/state"
    assert t.crossing == "retailvision/v1/site01/edge01/events/crossing"
    assert t.alert == "retailvision/v1/site01/edge01/events/alert"
    assert t.telemetry == "retailvision/v1/site01/edge01/telemetry"
    assert t.edge_status == "retailvision/v1/site01/edge01/status"
    assert t.operator_ack == "retailvision/v1/site01/node01/events/operator-ack"
    assert t.node_status == "retailvision/v1/site01/node01/status"
