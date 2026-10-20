"""Kiểm các chỉ số đánh giá bằng dữ liệu dựng tay (chỉ để kiểm công thức, KHÔNG phải kết quả đo)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation"))
import metrics  # noqa: E402


def test_wilson_interval_basics():
    assert metrics.wilson(0, 0) is None
    low, high = metrics.wilson(9, 10)
    assert 0.55 < low < 0.60 and 0.97 < high < 0.99  # ~[0,596; 0,982] cho 9/10
    assert metrics.wilson(10, 10)[1] == 1.0
    assert metrics.wilson(0, 10)[0] == 0.0


def test_count_error_per_direction_and_empty_clips():
    truth = {
        "a": [(1.0, "IN"), (2.0, "IN"), (3.0, "OUT")],
        "b": [(1.0, "IN")],
        "empty": [],
    }
    counted = {
        "a": [(1.1, "IN"), (2.1, "IN"), (2.9, "OUT"), (4.0, "OUT")],  # thừa một OUT
        "b": [],  # thiếu một IN
        "empty": [(5.0, "IN"), (6.0, "OUT")],  # đếm nhầm ở cảnh trống
    }
    r_in = metrics.count_error(truth, counted, "IN")
    assert (r_in.truth, r_in.counted, r_in.abs_error, r_in.bias) == (3, 3, 2, 0)  # |2-2| + |0-1| + |1-0|; thiếu và thừa triệt tiêu ở bias nhưng không ở sai số
    assert r_in.error_rate == pytest.approx(2 / 3)
    assert r_in.false_counts_on_empty_clips == 1
    r_out = metrics.count_error(truth, counted, "OUT")
    assert (r_out.truth, r_out.counted, r_out.abs_error) == (1, 3, 2)
    assert r_out.error_rate == pytest.approx(2.0)  # sai số có thể vượt 100%: không bị chặn


def test_count_error_without_any_true_crossing_has_no_rate_not_zero():
    r = metrics.count_error({"empty": []}, {"empty": [(1.0, "IN")]}, "IN")
    assert r.error_rate is None and r.false_counts_on_empty_clips == 1


def test_missing_clip_in_system_output_counts_as_zero_counted_not_ignored():
    r = metrics.count_error({"a": [(1.0, "IN"), (2.0, "IN")]}, {}, "IN")
    assert (r.counted, r.abs_error, r.error_rate) == (0, 2, 1.0)


def test_match_times_pairs_each_side_once_and_respects_tolerance():
    m = metrics.match_times([10.0, 20.0, 30.0], [10.5, 19.0, 50.0], tol=1.0)
    assert (m.tp, m.fp, m.fn) == (2, 1, 1)
    assert m.precision == pytest.approx(2 / 3) and m.recall == pytest.approx(2 / 3)
    # hai dự đoán gần cùng một nhãn: chỉ một được ghép, dư là FP
    m2 = metrics.match_times([10.0], [9.5, 10.4], tol=1.0)
    assert (m2.tp, m2.fp, m2.fn) == (1, 1, 0)
    # đúng ngưỡng vẫn khớp, vượt thì không
    assert metrics.match_times([10.0], [13.0], tol=3.0).tp == 1
    assert metrics.match_times([10.0], [13.1], tol=3.0).tp == 0


def test_match_returns_none_not_zero_when_undefined():
    m = metrics.match_times([], [], tol=1.0)
    assert m.precision is None and m.recall is None
    assert m.precision_ci() is None


def test_match_crossings_filters_by_direction():
    truth = [(1.0, "IN"), (2.0, "OUT")]
    pred = [(1.2, "IN"), (2.2, "IN")]
    assert metrics.match_crossings(truth, pred, 1.0, "IN").tp == 1
    assert metrics.match_crossings(truth, pred, 1.0, "OUT").tp == 0


def test_queue_mae_uses_latest_reading_and_reports_unmatched():
    truth = [(10.0, 2), (15.0, 5), (20.0, 0), (100.0, 3)]
    system = [(9.5, 2), (14.0, 4), (14.9, 4), (19.8, 1)]
    r = metrics.queue_mae(truth, system)
    # mốc 10: 2 vs 2 (0); mốc 15: 4 vs 5 (1); mốc 20: 1 vs 0 (1); mốc 100: không có số đo gần => unmatched
    assert r.samples == 3 and r.unmatched == 1
    assert r.mae == pytest.approx(2 / 3)
    assert r.bias == pytest.approx(0.0)  # 0, -1, +1
    assert r.samples_0_to_8 == 3


def test_queue_mae_with_no_overlap_is_none_not_zero():
    r = metrics.queue_mae([(10.0, 3)], [])
    assert r.mae is None and r.unmatched == 1 and r.samples == 0


def test_queue_mae_range_0_to_8_excludes_crowds():
    r = metrics.queue_mae([(1.0, 3), (2.0, 20)], [(1.0, 3), (2.0, 10)])
    assert r.mae == pytest.approx(5.0)
    assert r.mae_0_to_8 == 0.0 and r.samples_0_to_8 == 1


def series(counts, start=0.0):
    return [(start + i, c) for i, c in enumerate(counts)]


def test_alert_opens_follow_the_edge_state_machine():
    five = [5] * 61
    assert metrics.alert_opens_from_counts(series(five)) == [60.0]  # đủ 60 giây
    assert metrics.alert_opens_from_counts(series([5] * 60)) == []  # 59 giây: chưa mở (T06)
    # tụt xuống 4 rồi vượt lại: timer reset (T23)
    assert metrics.alert_opens_from_counts(series([5] * 40 + [4] + [5] * 40)) == []
    assert metrics.alert_opens_from_counts(series([5] * 40 + [4] + [5] * 61)) == [101.0]


def test_alert_match_uses_three_second_window():
    m = metrics.alert_match([60.0, 200.0], [62.5, 190.0], tol=3.0)
    assert (m.tp, m.fp, m.fn) == (1, 1, 1)


def test_replaying_system_counts_through_the_same_machine_gives_comparable_opens():
    truth = series([5] * 70 + [0] * 30)
    system_counts = series([5] * 70 + [0] * 30)  # hệ thống đếm đúng
    m = metrics.alert_match(metrics.alert_opens_from_counts(truth), metrics.alert_opens_from_counts(system_counts))
    assert (m.tp, m.fp, m.fn) == (1, 0, 0)
    undercount = series([4] * 100)  # hệ thống đếm thiếu một người: bỏ sót cảnh báo
    m2 = metrics.alert_match(metrics.alert_opens_from_counts(truth), metrics.alert_opens_from_counts(undercount))
    assert (m2.tp, m2.fp, m2.fn) == (0, 0, 1)
