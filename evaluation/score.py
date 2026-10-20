"""Chấm kết quả đếm qua vạch: so sánh sự kiện pipeline (JSONL) với nhãn tay (CSV).

Mỗi nhãn tay được ghép với tối đa một sự kiện cùng chiều, lệch thời gian không quá --tol giây.
  TP: sự kiện khớp một nhãn; FP: sự kiện không khớp nhãn nào; FN: nhãn không có sự kiện khớp.

    python evaluation/score.py --gt evaluation/ground_truth/virat_60s.csv --events run.jsonl --tol 1.0
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def read_gt(path: Path) -> list[tuple[float, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return [(float(r["ts"]), r["direction"]) for r in csv.DictReader(f)]


def read_events(path: Path) -> list[tuple[float, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("type") == "crossing":
            out.append((float(e["ts"]), e["direction"]))
    return out


def match(gt: list[tuple[float, str]], events: list[tuple[float, str]], tol: float) -> dict:
    used_events: set[int] = set()
    tp = 0
    for g_ts, g_dir in sorted(gt):
        best = None
        for i, (e_ts, e_dir) in enumerate(events):
            if i in used_events or e_dir != g_dir or abs(e_ts - g_ts) > tol:
                continue
            if best is None or abs(e_ts - g_ts) < abs(events[best][0] - g_ts):
                best = i
        if best is not None:
            used_events.add(best)
            tp += 1
    fp = len(events) - len(used_events)
    fn = len(gt) - tp
    return {"tp": tp, "fp": fp, "fn": fn, "gt": len(gt), "events": len(events)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--tol", type=float, default=1.0, help="sai lệch thời gian cho phép (giây)")
    args = parser.parse_args()

    gt = read_gt(args.gt)
    events = read_events(args.events)
    for direction in ("IN", "OUT"):
        r = match([g for g in gt if g[1] == direction], [e for e in events if e[1] == direction], args.tol)
        if r["gt"] == 0 and r["events"] == 0:
            continue
        precision = r["tp"] / r["events"] if r["events"] else 0.0
        recall = r["tp"] / r["gt"] if r["gt"] else 0.0
        print(f"{direction}: nhãn={r['gt']} sự_kiện={r['events']} TP={r['tp']} FP={r['fp']} FN={r['fn']} "
              f"precision={precision:.2f} recall={recall:.2f} (tol={args.tol}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
