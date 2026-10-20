from datetime import datetime, timedelta, timezone

from retailvision.resilience.telemetry import MAX_BACKFILL_MINUTES, MinuteAggregator

T0 = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)


def at(seconds):
    return T0 + timedelta(seconds=seconds)


def test_minute_is_closed_only_when_next_minute_starts():
    agg = MinuteAggregator()
    assert agg.add(at(1.0), 2, 100) == []
    assert agg.add(at(59.0), 4, 150) == []
    done = agg.add(at(61.0), 1, 50)
    assert len(done) == 1
    s = done[0]
    assert s.minute_start == T0
    assert s.valid_seconds == 2
    assert s.queue_avg == 3.0
    assert s.queue_max == 4
    assert s.frame_age_ms == 150
    assert s.fps == 1.0  # 2 khung trên 2 giây có phân tích


def test_valid_seconds_counts_distinct_seconds_not_frames():
    agg = MinuteAggregator()
    for i in range(10):
        agg.add(at(5 + i * 0.1), 1, 0)  # 10 khung trong cùng một giây
    s = agg.advance(at(61))[0]
    assert s.valid_seconds == 1
    assert s.fps == 10.0


def test_minutes_without_data_are_reported_with_zero_coverage_and_null_queue():
    agg = MinuteAggregator()
    agg.add(at(10), 3, 0)
    done = agg.advance(at(3 * 60 + 5))  # đã qua 3 phút, chỉ phút đầu có dữ liệu
    assert [d.valid_seconds for d in done] == [1, 0, 0]
    assert done[1].queue_avg is None and done[1].queue_max is None  # không phải 0
    assert [d.minute_start for d in done] == [T0, T0 + timedelta(minutes=1), T0 + timedelta(minutes=2)]


def test_very_long_gap_is_capped():
    agg = MinuteAggregator()
    agg.add(at(10), 3, 0)
    done = agg.advance(at(10 * 24 * 3600))
    assert len(done) == MAX_BACKFILL_MINUTES
