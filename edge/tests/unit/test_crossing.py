from retailvision.analytics.crossing import LineCounter
from retailvision.core.types import Track

# Vạch đứng x=50. Phía x<50 là +1, phía x>50 là -1.
# Chuyển phải→trái là -1 → +1, tức A→B, nhận nhãn a_to_b_direction.
LINE = ((50.0, 0.0), (50.0, 100.0))


def make_counter(a_to_b="IN", deadband=2.0, min_stable=2, line=LINE):
    return LineCounter(line, deadband_px=deadband, min_stable_observations=min_stable, a_to_b_direction=a_to_b)


def run(counter, xs, track_id=1, y=50.0, dt=0.5):
    events = []
    for i, x in enumerate(xs):
        frame = [Track(track_id, (x, y), (0, 0, 0, 0), 0.9)]
        events += counter.update(frame, i * dt)
    return events


def test_t01_right_to_left_counts_a_to_b_label():
    events = run(make_counter("IN"), [60, 55, 45, 40])
    assert [e.direction for e in events] == ["IN"]


def test_t01_left_to_right_counts_opposite_label():
    events = run(make_counter("IN"), [40, 45, 55, 60])
    assert [e.direction for e in events] == ["OUT"]


def test_t02_jitter_inside_deadband_is_not_counted():
    assert run(make_counter(), [50.5, 49.5, 50.8, 49.2, 50.6, 49.4]) == []


def test_quay_dau_without_crossing_is_not_counted():
    assert run(make_counter(), [60, 55, 45, 55, 60]) == []


def test_endpoint_bypass_is_not_counted():
    # đường đi nằm phía trên đầu mút A của vạch đoạn 20–80
    counter = make_counter(line=((50.0, 20.0), (50.0, 80.0)))
    frames = [(60, 10), (60, 10), (40, 10), (40, 10)]
    events = []
    for i, (x, y) in enumerate(frames):
        events += counter.update([Track(1, (x, y), (0, 0, 0, 0), 0.9)], i * 0.5)
    assert events == []


def test_track_born_on_other_side_is_not_counted():
    # track xuất hiện sát vạch rồi đứng hẳn một phía: chưa có chuyển phía nên không tính
    assert run(make_counter(), [51, 60, 70]) == []


def test_two_tracks_in_opposite_directions_are_counted_separately():
    counter = make_counter("IN")
    xs_a = [60, 55, 45, 40]
    xs_b = [40, 45, 55, 60]
    events = []
    for i in range(4):
        frame = [
            Track(1, (xs_a[i], 50.0), (0, 0, 0, 0), 0.9),
            Track(2, (xs_b[i], 50.0), (0, 0, 0, 0), 0.9),
        ]
        events += counter.update(frame, i * 0.5)
    by_track = {e.track_id: e.direction for e in events}
    assert by_track == {1: "IN", 2: "OUT"}


def test_in_then_out_gives_two_events():
    counter = make_counter("IN")
    xs = [60, 55, 45, 40, 45, 55, 60]
    events = run(counter, xs)
    assert [e.direction for e in events] == ["IN", "OUT"]


def test_invalid_config_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        make_counter(min_stable=0)
    with pytest.raises(ValueError):
        make_counter(a_to_b="LEFT")
