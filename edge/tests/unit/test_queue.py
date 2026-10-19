from retailvision.analytics.queue import QueueZone
from retailvision.core.types import Track

SQUARE = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]


def person(track_id, x, y=50.0):
    return Track(track_id, (x, y), (0, 0, 0, 0), 0.9)


def test_person_counts_only_after_dwell():
    zone = QueueZone(SQUARE, dwell_seconds=2.0)
    counts = [zone.update([person(1, 50)], ts) for ts in (0.0, 1.0, 2.0)]
    assert counts == [0, 0, 1]


def test_pass_through_below_dwell_is_not_counted_and_reentry_restarts_timer():
    zone = QueueZone(SQUARE, dwell_seconds=2.0)
    assert zone.update([person(1, 50)], 0.0) == 0
    assert zone.update([person(1, 150)], 1.0) == 0  # ra khỏi đa giác
    assert zone.update([person(1, 50)], 2.0) == 0  # vào lại, đếm lại từ đầu
    assert zone.update([person(1, 50)], 3.0) == 0
    assert zone.update([person(1, 50)], 4.0) == 1


def test_lost_track_leaves_the_count():
    zone = QueueZone(SQUARE, dwell_seconds=0.0)
    assert zone.update([person(1, 50), person(2, 60)], 0.0) == 2
    assert zone.update([person(2, 60)], 1.0) == 1


def test_polygon_needs_three_points():
    import pytest

    with pytest.raises(ValueError):
        QueueZone([(0.0, 0.0), (1.0, 1.0)], dwell_seconds=2.0)
