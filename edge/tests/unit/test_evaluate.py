"""Kiểm công cụ báo cáo bằng clip DỰNG TAY (tổng hợp). Chỉ để kiểm logic; đây không phải dữ liệu hay kết quả đo."""

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation"))
import evaluate  # noqa: E402

META = {"hardware": "laptop-test", "model": "fake", "imgsz": "320", "config_version": "v1", "lighting": "den", "density": "thua", "source": "replay"}
HEADER = ["clip_id", "split", "events", "gt_crossings", "gt_queue", *META, "alert_on_count", "alert_on_hold", "alert_off_count", "alert_off_hold"]


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_events(path, crossings=(), queue=(), alerts=()):
    lines = [{"type": "crossing", "ts": t, "track_id": 1, "direction": d} for t, d in crossings]
    lines += [{"type": "queue", "ts": t, "count": c} for t, c in queue]
    lines += [{"type": "alert", "kind": "OPEN", "ts": t, "alert_id": "a"} for t in alerts]
    path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")


def manifest(tmp_path, rows):
    path = tmp_path / "manifest.csv"
    write_csv(path, HEADER, rows)
    return path


def row(clip, split, events="e.jsonl", crossings="", queue="", **meta):
    m = {**META, **meta}
    return [clip, split, events, crossings, queue, *[m[k] for k in META], "5", "60", "3", "10"]


@pytest.fixture
def clip(tmp_path):
    write_csv(tmp_path / "gt_cross.csv", ["ts", "direction"], [[10, "IN"], [20, "IN"], [30, "IN"], [40, "OUT"]])
    write_events(
        tmp_path / "e.jsonl",
        crossings=[(10.2, "IN"), (20.1, "IN"), (31.5, "IN")],  # IN: đủ 3 nhưng một lượt trễ quá dung sai; thiếu OUT
        queue=[(t, 5 if 10 <= t <= 90 else 0) for t in range(0, 121)],
        alerts=[71.0],
    )
    write_csv(tmp_path / "gt_queue.csv", ["ts", "count"], [[t, 5 if 10 <= t <= 90 else 0] for t in range(0, 121, 5)])
    return tmp_path


def test_report_numbers_for_a_hand_built_clip(clip):
    rows = evaluate.load_manifest(manifest(clip, [row("c1", "dev", crossings="gt_cross.csv", queue="gt_queue.csv")]))
    rep = evaluate.evaluate(rows)["dev"]

    cin, cout = rep.count["IN"], rep.count["OUT"]
    assert (cin.truth, cin.counted, cin.error_rate) == (3, 3, 0.0)  # đếm đủ số lượng
    assert (rep.crossing_match["IN"].tp, rep.crossing_match["IN"].fp, rep.crossing_match["IN"].fn) == (2, 1, 1)  # nhưng một lượt lệch giờ
    assert (cout.truth, cout.counted, cout.error_rate) == (1, 0, 1.0)  # thiếu hẳn một lượt OUT

    assert rep.queue.mae == 0.0 and rep.queue.samples == 25
    # nhãn: 5 người từ giây 10 đến 90, giữ ≥60 s => mở ở mốc 70; hệ thống báo 71 => khớp
    assert (rep.alert_live.tp, rep.alert_live.fp, rep.alert_live.fn) == (1, 0, 0)
    assert (rep.alert_replay.tp, rep.alert_replay.fp, rep.alert_replay.fn) == (1, 0, 0)


def test_markdown_states_pass_fail_and_does_not_hide_misses(clip):
    rows = evaluate.load_manifest(manifest(clip, [row("c1", "dev", crossings="gt_cross.csv", queue="gt_queue.csv")]))
    text = evaluate.render_markdown(evaluate.evaluate(rows), 1.0, 3.0)
    assert "Tập dev (1 clip)" in text
    assert "KHÔNG đạt (>10%)" in text  # OUT sai 100%
    assert "đạt (≤5%, mục tiêu mở rộng)" in text  # IN đếm đủ
    assert "đạt (≤1 người)" in text
    assert "đạt (≥0,90)" in text
    assert "chưa có clip nào ở tập test" in text  # không tuyên bố nghiệm thu khi chưa có tập test
    assert "Có clip phát lại (replay)" in text


def test_small_test_set_is_flagged_and_mixed_conditions_are_called_out(clip):
    (clip / "e2.jsonl").write_text("", encoding="utf-8")
    rows = evaluate.load_manifest(manifest(clip, [
        row("t1", "test", crossings="gt_cross.csv", lighting="den"),
        row("t2", "test", events="e2.jsonl", crossings="gt_cross.csv", lighting="toi"),
    ]))
    rep = evaluate.evaluate(rows)["test"]
    joined = " ".join(rep.notes)
    assert "Cỡ mẫu chưa đủ: tập test có 8 lượt" in joined
    assert "trộn nhiều giá trị `lighting`" in joined


def test_missing_labels_give_no_verdict_instead_of_zero(clip):
    write_events(clip / "empty.jsonl")
    write_csv(clip / "none.csv", ["ts", "direction"], [])
    rows = evaluate.load_manifest(manifest(clip, [row("c0", "dev", events="empty.jsonl", crossings="none.csv")]))
    rep = evaluate.evaluate(rows)["dev"]
    assert rep.count["IN"].error_rate is None
    text = evaluate.render_markdown({"dev": rep}, 1.0, 3.0)
    assert "chưa đủ dữ liệu" in text
    assert rep.queue is None


def test_empty_scene_false_counts_are_reported_separately(clip):
    write_events(clip / "ghost.jsonl", crossings=[(5.0, "IN"), (6.0, "OUT")])
    write_csv(clip / "none.csv", ["ts", "direction"], [])
    rows = evaluate.load_manifest(manifest(clip, [row("empty", "dev", events="ghost.jsonl", crossings="none.csv")]))
    rep = evaluate.evaluate(rows)["dev"]
    assert rep.count["IN"].false_counts_on_empty_clips == 1 and rep.count["IN"].error_rate is None
    assert "| IN | 0 | 1 |" in evaluate.render_markdown({"dev": rep}, 1.0, 3.0)


def test_alert_missed_by_the_system_is_a_false_negative(clip):
    write_events(clip / "quiet.jsonl", queue=[(t, 4) for t in range(0, 121)], alerts=[])  # thiếu 1 người: không bao giờ mở
    rows = evaluate.load_manifest(manifest(clip, [row("c", "dev", events="quiet.jsonl", queue="gt_queue.csv")]))
    rep = evaluate.evaluate(rows)["dev"]
    assert (rep.alert_live.tp, rep.alert_live.fn) == (0, 1)
    assert (rep.alert_replay.tp, rep.alert_replay.fn) == (0, 1)
    assert rep.queue.mae > 0
    assert "KHÔNG đạt (<0,90)" in evaluate.render_markdown({"dev": rep}, 1.0, 3.0)


def test_clips_do_not_leak_into_each_other_when_pooled(clip):
    write_events(clip / "late.jsonl", queue=[(t, 0) for t in range(0, 121)], alerts=[71.0])  # alert hệ thống: FP ở clip này
    write_csv(clip / "gt_zero.csv", ["ts", "count"], [[t, 0] for t in range(0, 121, 5)])
    rows = evaluate.load_manifest(manifest(clip, [
        row("a", "dev", queue="gt_queue.csv"),  # clip a có cảnh báo thật mở ở 70, hệ thống mở ở 71
        row("b", "dev", events="late.jsonl", queue="gt_zero.csv"),  # clip b không có cảnh báo thật, hệ thống báo nhầm
    ]))
    rep = evaluate.evaluate(rows)["dev"]
    assert (rep.alert_live.tp, rep.alert_live.fp, rep.alert_live.fn) == (1, 1, 0)


def test_manifest_validation(clip):
    with pytest.raises(ValueError, match="split"):
        evaluate.load_manifest(manifest(clip, [row("x", "validation")]))
    with pytest.raises(ValueError, match="trùng"):
        evaluate.load_manifest(manifest(clip, [row("x", "dev"), row("x", "test")]))


def test_missing_metadata_is_called_out(clip):
    rows = evaluate.load_manifest(manifest(clip, [row("c1", "dev", crossings="gt_cross.csv", hardware="")]))
    rep = evaluate.evaluate(rows)["dev"]
    assert any("Thiếu thông tin `hardware`" in n for n in rep.notes)
    assert "(chưa ghi)" in evaluate.render_markdown({"dev": rep}, 1.0, 3.0)


def test_cli_writes_markdown_and_csv(clip, capsys):
    m = manifest(clip, [row("c1", "dev", crossings="gt_cross.csv", queue="gt_queue.csv")])
    out, summary = clip / "r" / "report.md", clip / "r" / "summary.csv"
    assert evaluate.main(["--manifest", str(m), "--out", str(out), "--csv", str(summary)]) == 0
    assert "Báo cáo độ đúng" in out.read_text(encoding="utf-8")
    rows = list(csv.DictReader(summary.open(encoding="utf-8")))
    assert {"count_error", "queue_mae", "alert_live_precision", "alert_replay_recall"} <= {r["metric"] for r in rows}
    capsys.readouterr()


def test_small_samples_are_never_presented_as_a_clean_pass(clip):
    rows = evaluate.load_manifest(manifest(clip, [row("c1", "dev", crossings="gt_cross.csv", queue="gt_queue.csv")]))
    text = evaluate.render_markdown(evaluate.evaluate(rows), 1.0, 3.0)
    assert "mẫu nhỏ (n=3 < 20)" in text  # đếm IN: chỉ 3 lượt thật
    assert "mẫu nhỏ (n=1 < 10)" in text  # chỉ 1 cảnh báo thật
    assert evaluate.verdict_error(0.04, 500) == "đạt (≤5%, mục tiêu mở rộng)"  # mẫu đủ lớn thì kết luận gọn
    assert "mẫu nhỏ" in evaluate.verdict_error(0.04, 5)
    assert "mẫu nhỏ" in evaluate.verdict_mae(0.5, 10)
    assert "mẫu nhỏ" not in evaluate.verdict_mae(0.5, 100)
