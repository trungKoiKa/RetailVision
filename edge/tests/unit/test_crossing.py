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


def feed_timed(counter, observations):
    """observations: list of (ts, [(track_id, x)]); trả về mọi sự kiện."""
    events = []
    for ts, people in observations:
        frame = [Track(tid, (x, 50.0), (0, 0, 0, 0), 0.9) for tid, x in people]
        events += counter.update(frame, ts)
    return events


def test_track_lost_at_line_reappearing_on_other_side_counts_once():
    counter = make_counter("IN")
    events = feed_timed(counter, [
        (0.0, [(1, 60)]), (0.5, [(1, 55)]),          # track 1 ổn định bên phải vạch
        (1.0, []), (1.5, []),                          # mất khi qua vạch
        (2.0, [(2, 40)]), (2.5, [(2, 40)]),          # track 2 xuất hiện bên trái
        (3.0, [(2, 35)]),
    ])
    assert [(e.track_id, e.direction) for e in events] == [(2, "IN")]


def test_reappearance_on_same_side_is_not_counted():
    counter = make_counter("IN")
    events = feed_timed(counter, [
        (0.0, [(1, 60)]), (0.5, [(1, 55)]),
        (1.0, []), (1.5, []),
        (2.0, [(2, 60)]), (2.5, [(2, 60)]),
    ])
    assert events == []


def test_reassociation_respects_distance_to_line():
    # điểm ổn định cuối của track 1 cách vạch đúng 5 px
    observations = [
        (0.0, [(1, 60)]), (0.5, [(1, 55)]),
        (1.0, []), (1.5, []),
        (2.0, [(2, 40)]), (2.5, [(2, 40)]),
    ]
    tight = LineCounter(LINE, deadband_px=2, min_stable_observations=2, a_to_b_direction="IN", reassoc_px=4)
    loose = LineCounter(LINE, deadband_px=2, min_stable_observations=2, a_to_b_direction="IN", reassoc_px=5)
    assert feed_timed(tight, observations) == []
    assert [(e.track_id, e.direction) for e in feed_timed(loose, observations)] == [(2, "IN")]


def test_reassociation_expires_after_window():
    counter = make_counter("IN")
    events = feed_timed(counter, [
        (0.0, [(1, 60)]), (0.5, [(1, 55)]),
        (1.0, []), (4.0, []),                  # mất quá lâu
        (4.5, [(2, 40)]), (5.0, [(2, 40)]),
    ])
    assert events == []


def test_crossing_time_is_interpolated_to_the_line_not_confirmation():
    counter = make_counter("IN", deadband=2.0, min_stable=2)
    events = feed_timed(counter, [
        (0.0, [(1, 60)]), (1.0, [(1, 55)]),     # ổn định bên phải
        (2.0, [(1, 45)]), (3.0, [(1, 40)]),     # sang trái, xác nhận ở t=3
    ])
    assert len(events) == 1
    # đoạn (55 @ 1.0) → (40 @ 3.0) chạm x=50 sau 1/3 đoạn: t = 1 + 2 * 5/15
    assert abs(events[0].ts - (1.0 + 2.0 * 5 / 15)) < 1e-9


def test_reassociated_crossing_time_is_interpolated():
    counter = make_counter("IN")
    events = feed_timed(counter, [
        (0.0, [(1, 60)]), (0.5, [(1, 55)]),      # track 1 cuối cùng ở 55 @ 0.5
        (1.0, []), (1.5, []),
        (2.0, [(2, 45)]), (2.5, [(2, 45)]),      # track 2 xác nhận ở 45 @ 2.5
    ])
    assert len(events) == 1
    assert abs(events[0].ts - 1.5) < 1e-9        # chạm vạch giữa 0.5 và 2.5
