"""Tổng hợp độ đúng từ nhãn tay và kết quả chạy hệ thống, theo manifest các clip (dev/test).

Đọc `manifest.csv` (cột ở evaluation/ground_truth/README.md), tính chỉ số trong metrics.py cho từng nhóm dev/test,
in báo cáo Markdown (và CSV tóm tắt). Ngưỡng nghiệm thu là mục tiêu thử nghiệm, không phải kết quả: báo cáo ghi rõ
đạt hay chưa, kèm cỡ mẫu và khoảng tin cậy; mẫu quá ít thì nói "chưa đủ dữ liệu".

    python evaluation/evaluate.py --manifest evaluation/ground_truth/manifest.csv --out evaluation/results/report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402

TARGET_ERROR = 0.10
TARGET_ERROR_EXTENDED = 0.05
TARGET_QUEUE_MAE = 1.0
TARGET_ALERT = 0.90
MIN_TEST_CROSSINGS = 100
# dưới các cỡ mẫu này kết luận đạt/không đạt chỉ mang tính tham khảo (khoảng tin cậy rất rộng)
MIN_VERDICT_CROSSINGS = 20
MIN_VERDICT_QUEUE_SAMPLES = 30
MIN_VERDICT_ALERTS = 10
META_FIELDS = ["hardware", "model", "imgsz", "config_version", "lighting", "density", "source"]
ALERT_FIELDS = ["alert_on_count", "alert_on_hold", "alert_off_count", "alert_off_hold"]


@dataclass
class ClipRow:
    clip_id: str
    split: str
    events: Path
    gt_crossings: Optional[Path]
    gt_queue: Optional[Path]
    meta: dict[str, str]
    alert: metrics.AlertSettings


def _opt(base: Path, value: str) -> Optional[Path]:
    value = (value or "").strip()
    return (base / value) if value else None


def load_manifest(path: Path) -> list[ClipRow]:
    base = path.parent
    rows: list[ClipRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            split = r["split"].strip().lower()
            if split not in ("dev", "test"):
                raise ValueError(f"clip {r.get('clip_id')}: split phải là dev hoặc test, không phải {split!r}")
            settings = metrics.AlertSettings(
                on_count=int(r.get("alert_on_count") or 5),
                on_hold_seconds=float(r.get("alert_on_hold") or 60),
                off_count=int(r.get("alert_off_count") or 3),
                off_hold_seconds=float(r.get("alert_off_hold") or 10),
            )
            rows.append(ClipRow(
                clip_id=r["clip_id"].strip(),
                split=split,
                events=base / r["events"].strip(),
                gt_crossings=_opt(base, r.get("gt_crossings", "")),
                gt_queue=_opt(base, r.get("gt_queue", "")),
                meta={k: (r.get(k) or "").strip() for k in META_FIELDS},
                alert=settings,
            ))
    ids = [r.clip_id for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"clip_id bị trùng trong manifest: {sorted(dup)}")
    return rows


def read_crossings_csv(path: Path) -> list[metrics.Crossing]:
    with path.open(encoding="utf-8", newline="") as f:
        return [(float(r["ts"]), r["direction"].strip().upper()) for r in csv.DictReader(f)]


def read_queue_csv(path: Path) -> list[metrics.Sample]:
    with path.open(encoding="utf-8", newline="") as f:
        return [(float(r["ts"]), int(r["count"])) for r in csv.DictReader(f)]


@dataclass
class RunEvents:
    crossings: list[metrics.Crossing] = field(default_factory=list)
    queue: list[metrics.Sample] = field(default_factory=list)
    alert_opens: list[float] = field(default_factory=list)


def read_events(path: Path) -> RunEvents:
    """Sự kiện JSONL do `retailvision.app --events-out` ghi: crossing, queue (mỗi giây), alert."""
    out = RunEvents()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        kind = e.get("type")
        if kind == "crossing":
            out.crossings.append((float(e["ts"]), e["direction"]))
        elif kind == "queue":
            out.queue.append((float(e["ts"]), int(e["count"])))
        elif kind == "alert" and e.get("kind") == "OPEN":
            out.alert_opens.append(float(e["ts"]))
    return out


@dataclass
class SplitReport:
    split: str
    clips: int = 0
    meta_values: dict[str, set] = field(default_factory=dict)
    count: dict[str, metrics.CountResult] = field(default_factory=dict)
    crossing_match: dict[str, metrics.MatchResult] = field(default_factory=dict)
    queue: Optional[metrics.QueueResult] = None
    queue_clips: int = 0
    alert_live: Optional[metrics.MatchResult] = None
    alert_replay: Optional[metrics.MatchResult] = None
    alert_clips: int = 0
    notes: list[str] = field(default_factory=list)


def evaluate(rows: list[ClipRow], tol_crossing: float = 1.0, tol_alert: float = 3.0) -> dict[str, SplitReport]:
    reports: dict[str, SplitReport] = {}
    for split in ("dev", "test"):
        subset = [r for r in rows if r.split == split]
        if not subset:
            continue
        rep = SplitReport(split=split, clips=len(subset))
        for key in META_FIELDS:
            rep.meta_values[key] = {r.meta[key] for r in subset if r.meta[key]}

        truth_cross: dict[str, list[metrics.Crossing]] = {}
        run_cross: dict[str, list[metrics.Crossing]] = {}
        match = {"IN": [0, 0, 0], "OUT": [0, 0, 0]}
        queue_truth: list[metrics.Sample] = []
        queue_sys: list[metrics.Sample] = []
        live = [0, 0, 0]
        replay = [0, 0, 0]
        offset = 0.0  # ghép nhiều clip vào một trục thời gian để dùng chung hàm tính, cách nhau đủ xa
        for r in subset:
            run = read_events(r.events)
            if r.gt_crossings is not None:
                gt = read_crossings_csv(r.gt_crossings)
                truth_cross[r.clip_id] = gt
                run_cross[r.clip_id] = run.crossings
                for d in ("IN", "OUT"):
                    m = metrics.match_crossings(gt, run.crossings, tol_crossing, d)
                    match[d][0] += m.tp
                    match[d][1] += m.fp
                    match[d][2] += m.fn
            if r.gt_queue is not None:
                qt = read_queue_csv(r.gt_queue)
                rep.queue_clips += 1
                queue_truth += [(t + offset, c) for t, c in qt]
                queue_sys += [(t + offset, c) for t, c in run.queue]
                m_live = metrics.alert_match(metrics.alert_opens_from_counts(qt, r.alert), run.alert_opens, tol_alert)
                m_rep = metrics.alert_match(
                    metrics.alert_opens_from_counts(qt, r.alert), metrics.alert_opens_from_counts(run.queue, r.alert), tol_alert
                )
                for acc, m in ((live, m_live), (replay, m_rep)):
                    acc[0] += m.tp
                    acc[1] += m.fp
                    acc[2] += m.fn
                rep.alert_clips += 1
                last = max([t for t, _ in qt] + [t for t, _ in run.queue] + [0.0])
                offset += last + 1000.0  # khoảng cách lớn: không clip nào ghép nhầm sang clip khác
        for d in ("IN", "OUT"):
            if truth_cross:
                rep.count[d] = metrics.count_error(truth_cross, run_cross, d)
                rep.crossing_match[d] = metrics.MatchResult(*match[d])
        if queue_truth:
            rep.queue = metrics.queue_mae(queue_truth, queue_sys)
            rep.alert_live = metrics.MatchResult(*live)
            rep.alert_replay = metrics.MatchResult(*replay)
        _add_notes(rep)
        reports[split] = rep
    return reports


def _add_notes(rep: SplitReport) -> None:
    for key, values in rep.meta_values.items():
        if len(values) > 1:
            rep.notes.append(f"Nhóm {rep.split} trộn nhiều giá trị `{key}`: {sorted(values)}; kết quả không áp dụng riêng cho từng giá trị.")
        if not values:
            rep.notes.append(f"Thiếu thông tin `{key}` trong manifest.")
    if "replay" in rep.meta_values.get("source", set()):
        rep.notes.append("Có clip phát lại (replay): không phải đo trực tiếp trên thiết bị.")
    if rep.split == "test" and rep.count:
        total = sum(c.truth for c in rep.count.values())
        if total < MIN_TEST_CROSSINGS:
            rep.notes.append(f"Cỡ mẫu chưa đủ: tập test có {total} lượt qua cửa, mục tiêu ≥ {MIN_TEST_CROSSINGS}.")


def _pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _ci(ci: Optional[tuple[float, float]]) -> str:
    return "—" if ci is None else f"[{ci[0] * 100:.0f}%, {ci[1] * 100:.0f}%]"


def _small(n: int, minimum: int) -> str:
    return f" — mẫu nhỏ (n={n} < {minimum}): chưa đủ để kết luận" if n < minimum else ""


def verdict_error(rate: Optional[float], n: int = 10**9) -> str:
    if rate is None:
        return "chưa đủ dữ liệu"
    if rate <= TARGET_ERROR_EXTENDED:
        text = "đạt (≤5%, mục tiêu mở rộng)"
    elif rate <= TARGET_ERROR:
        text = "đạt (≤10%)"
    else:
        text = "KHÔNG đạt (>10%)"
    return text + _small(n, MIN_VERDICT_CROSSINGS)


def verdict_mae(mae: Optional[float], n: int = 10**9) -> str:
    if mae is None:
        return "chưa đủ dữ liệu"
    return ("đạt (≤1 người)" if mae <= TARGET_QUEUE_MAE else "KHÔNG đạt (>1 người)") + _small(n, MIN_VERDICT_QUEUE_SAMPLES)


def verdict_alert(m: Optional[metrics.MatchResult]) -> str:
    """Một chỉ số đã xác định mà dưới ngưỡng là đủ để kết luận không đạt (ví dụ bỏ sót hết: recall = 0 dù precision
    chưa xác định vì không có dự đoán nào). Chỉ khi cả hai chưa đủ để chứng minh đạt mới nói thiếu dữ liệu."""
    if m is None:
        return "chưa đủ dữ liệu"
    defined = [x for x in (m.precision, m.recall) if x is not None]
    n = m.tp + m.fn  # số cảnh báo thật
    if any(x < TARGET_ALERT for x in defined):
        return "KHÔNG đạt (<0,90)" + _small(n, MIN_VERDICT_ALERTS)
    if len(defined) == 2:
        return "đạt (≥0,90)" + _small(n, MIN_VERDICT_ALERTS)
    return "chưa đủ dữ liệu"


def render_markdown(reports: dict[str, SplitReport], tol_crossing: float, tol_alert: float) -> str:
    lines = [
        "# Báo cáo độ đúng",
        "",
        "Ngưỡng là mục tiêu thử nghiệm (docs/1-requirements.md), không phải kết quả. Số liệu chỉ có giá trị với đúng điều kiện ghi ở mục Điều kiện.",
        "",
    ]
    for split, rep in reports.items():
        lines += [f"## Tập {split} ({rep.clips} clip)", "", "### Điều kiện", ""]
        for key in META_FIELDS:
            vals = sorted(rep.meta_values.get(key, set()))
            lines.append(f"- {key}: {', '.join(vals) if vals else '(chưa ghi)'}")
        lines.append("")
        if rep.count:
            lines += ["### Đếm qua cửa", "", f"Ghép theo thời gian lệch ≤ {tol_crossing:g} s cho precision/recall.", "",
                      "| Hướng | Lượt thật | Hệ thống đếm | Sai số đếm | Lệch (đếm − thật) | Đếm nhầm ở clip trống | Precision | Recall | Kết luận |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for d in ("IN", "OUT"):
                c, m = rep.count[d], rep.crossing_match[d]
                lines.append(
                    f"| {d} | {c.truth} | {c.counted} | {_pct(c.error_rate)} | {c.bias:+d} | {c.false_counts_on_empty_clips} | "
                    f"{_pct(m.precision)} {_ci(m.precision_ci())} | {_pct(m.recall)} {_ci(m.recall_ci())} | {verdict_error(c.error_rate, c.truth)} |")
            lines.append("")
        if rep.queue is not None:
            q = rep.queue
            lines += ["### Số người vùng chờ", "",
                      f"{rep.queue_clips} clip, {q.samples} mốc so được, {q.unmatched} mốc không có số đo gần (không tính).", "",
                      "| MAE | Lệch trung bình | MAE trong 0–8 người | Số mốc 0–8 | Kết luận |", "| --- | --- | --- | --- | --- |",
                      f"| {'—' if q.mae is None else f'{q.mae:.2f}'} | {'—' if q.bias is None else f'{q.bias:+.2f}'} | "
                      f"{'—' if q.mae_0_to_8 is None else f'{q.mae_0_to_8:.2f}'} | {q.samples_0_to_8} | {verdict_mae(q.mae_0_to_8, q.samples_0_to_8)} |", ""]
            lines += ["### Cảnh báo", "", f"Ghép thời điểm mở lệch ≤ {tol_alert:g} s; nhãn suy ra từ nhãn số người bằng cùng máy trạng thái và ngưỡng.", "",
                      "| Nguồn dự đoán | Cảnh báo thật | TP | FP | FN | Precision | Recall | Kết luận |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            for name, m in (("Sự kiện alert của hệ thống (live/replay clip)", rep.alert_live), ("Chạy máy trạng thái trên số người hệ thống", rep.alert_replay)):
                lines.append(f"| {name} | {m.tp + m.fn} | {m.tp} | {m.fp} | {m.fn} | {_pct(m.precision)} {_ci(m.precision_ci())} | "
                             f"{_pct(m.recall)} {_ci(m.recall_ci())} | {verdict_alert(m)} |")
            lines.append("")
        if not rep.count and rep.queue is None:
            lines += ["Chưa có nhãn nào cho tập này.", ""]
        for note in rep.notes:
            lines.append(f"> Lưu ý: {note}")
        lines.append("")
    if "test" not in reports:
        lines += ["> Lưu ý: chưa có clip nào ở tập test, nên chưa có kết quả nghiệm thu.", ""]
    return "\n".join(lines)


def write_csv(reports: dict[str, SplitReport], path: Path) -> None:
    cols = ["split", "clips", "metric", "key", "value", "n"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for split, rep in reports.items():
            for d, c in rep.count.items():
                w.writerow([split, rep.clips, "count_error", d, "" if c.error_rate is None else round(c.error_rate, 4), c.truth])
            if rep.queue:
                w.writerow([split, rep.clips, "queue_mae", "all", "" if rep.queue.mae is None else round(rep.queue.mae, 3), rep.queue.samples])
                w.writerow([split, rep.clips, "queue_mae", "0-8", "" if rep.queue.mae_0_to_8 is None else round(rep.queue.mae_0_to_8, 3), rep.queue.samples_0_to_8])
            for name, m in (("alert_live", rep.alert_live), ("alert_replay", rep.alert_replay)):
                if m:
                    w.writerow([split, rep.clips, f"{name}_precision", "", "" if m.precision is None else round(m.precision, 4), m.tp + m.fp])
                    w.writerow([split, rep.clips, f"{name}_recall", "", "" if m.recall is None else round(m.recall, 4), m.tp + m.fn])


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tol-crossing", type=float, default=1.0)
    parser.add_argument("--tol-alert", type=float, default=3.0)
    parser.add_argument("--out", type=Path, help="ghi báo cáo Markdown")
    parser.add_argument("--csv", type=Path, help="ghi CSV tóm tắt")
    args = parser.parse_args(argv)
    reports = evaluate(load_manifest(args.manifest), args.tol_crossing, args.tol_alert)
    text = render_markdown(reports, args.tol_crossing, args.tol_alert)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    if args.csv:
        write_csv(reports, args.csv)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
