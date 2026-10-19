import itertools

import pytest

from retailvision.analytics.alert_state import AlertSettings, AlertState, AlertStateMachine

SET = AlertSettings(on_count=5, on_hold_seconds=60, off_count=3, off_hold_seconds=10)


def machine(settings=SET):
    ids = (f"alert-{n}" for n in itertools.count(1))
    return AlertStateMachine(settings, new_alert_id=lambda: next(ids))


def feed(sm, start, end, count):
    """Đưa count cho mọi giây trong [start, end]; trả về các transition đã phát."""
    out = []
    for ts in range(start, end + 1):
        out += sm.on_observation(count, float(ts))
    return out


def kinds(transitions):
    return [(t.kind, t.reason) for t in transitions]


def open_alert(sm):
    """Đưa máy về OVERLOAD: 5 người từ ts 0 tới 60."""
    out = feed(sm, 0, 60, 5)
    assert kinds(out) == [("OPEN", None)]
    return out[0].alert_id


def test_t06_59_seconds_over_threshold_does_not_open():
    sm = machine()
    assert feed(sm, 0, 59, 5) == []
    assert sm.state is AlertState.NORMAL


def test_t07_60_seconds_over_threshold_opens_once():
    sm = machine()
    out = feed(sm, 0, 60, 5)
    assert kinds(out) == [("OPEN", None)]
    assert out[0].queue_count == 5
    assert sm.state is AlertState.OVERLOAD


def test_t08_four_people_keeps_overload():
    sm = machine()
    open_alert(sm)
    assert feed(sm, 61, 200, 4) == []
    assert sm.state is AlertState.OVERLOAD


def test_t09_three_people_for_off_hold_ends_normalized():
    sm = machine()
    open_alert(sm)
    assert feed(sm, 61, 70, 3) == []  # mới 9 giây kể từ lần đầu xuống 3 người, chưa đủ off_hold 10 giây
    out = feed(sm, 71, 71, 3)
    assert kinds(out) == [("END", "NORMALIZED")]
    assert sm.state is AlertState.NORMAL


def test_t23_dropping_below_on_count_resets_open_timer():
    sm = machine()
    assert feed(sm, 0, 50, 5) == []
    assert feed(sm, 51, 51, 4) == []  # tụt xuống dưới on_count, timer reset
    assert feed(sm, 52, 111, 5) == []  # 59 giây kể từ lúc vượt lại
    out = feed(sm, 112, 112, 5)
    assert kinds(out) == [("OPEN", None)]


def test_t10_ack_keeps_overload_and_is_recorded_once():
    sm = machine()
    alert_id = open_alert(sm)
    out = sm.on_ack(alert_id, "ack-1", "node01", 70.0)
    assert kinds(out) == [("ACK", None)]
    assert out[0].ack_device_id == "node01"
    assert sm.state is AlertState.OVERLOAD
    assert sm.on_ack(alert_id, "ack-1", "node01", 71.0) == []


def test_ack_for_other_alert_is_ignored():
    sm = machine()
    open_alert(sm)
    assert sm.on_ack("not-the-alert", "ack-1", "node01", 70.0) == []
    assert sm.acked is False


def test_ack_when_not_overload_is_ignored():
    sm = machine()
    assert sm.on_ack("alert-1", "ack-1", "node01", 1.0) == []


def test_t11_stale_interrupts_open_alert_and_returns_unknown():
    sm = machine()
    open_alert(sm)
    out = sm.on_stale(70.0)
    assert kinds(out) == [("END", "INTERRUPTED")]
    assert out[0].queue_count is None
    assert sm.state is AlertState.UNKNOWN


def test_stale_without_alert_is_silent_and_next_data_goes_normal():
    sm = machine()
    assert sm.on_stale(0.0) == []
    assert sm.state is AlertState.UNKNOWN
    assert sm.on_observation(1, 1.0) == []
    assert sm.state is AlertState.NORMAL


def test_reopen_after_interruption_uses_new_alert_id():
    sm = machine()
    first = open_alert(sm)
    sm.on_stale(70.0)
    feed(sm, 71, 71, 1)
    second = feed(sm, 72, 132, 5)[-1].alert_id
    assert second != first


def test_settings_change_ends_open_alert_with_config_changed():
    sm = machine()
    open_alert(sm)
    new = AlertSettings(on_count=4, on_hold_seconds=30, off_count=2, off_hold_seconds=10)
    out = sm.apply_settings(new, 70.0)
    assert kinds(out) == [("END", "CONFIG_CHANGED")]
    assert sm.state is AlertState.NORMAL
    assert sm.settings == new


def test_same_settings_change_is_a_noop():
    sm = machine()
    open_alert(sm)
    assert sm.apply_settings(SET, 70.0) == []
    assert sm.state is AlertState.OVERLOAD


def test_t16_off_count_not_below_on_count_is_rejected():
    with pytest.raises(ValueError):
        AlertSettings(on_count=3, on_hold_seconds=60, off_count=3, off_hold_seconds=10)
    with pytest.raises(ValueError):
        AlertSettings(on_count=5, on_hold_seconds=60, off_count=6, off_hold_seconds=10)
