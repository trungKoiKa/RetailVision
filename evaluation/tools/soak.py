"""T18 phía edge: chạy pipeline liên tục (lặp clip) và theo dõi RAM, số luồng, số khung theo thời gian.

Phát hiện rò rỉ: so RSS trung bình của phần tư đầu (sau khởi động) với phần tư cuối. Tăng quá `--max-growth-mb`
thì thoát mã 1. Số đo máy phát triển chỉ chứng minh công cụ; muốn kết luận cho Pi phải chạy ≥2 giờ rồi ≥4 giờ trên Pi.

    python evaluation/tools/soak.py --config configs/examples/site01-video.yaml --source clip.mp4 \\
        --seconds 7200 --out evaluation/results/soak.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import statistics
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "edge"))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--sample-every", type=float, default=5.0)
    parser.add_argument("--max-growth-mb", type=float, default=50.0)
    parser.add_argument("--out", type=Path, help="ghi CSV theo thời gian")
    args = parser.parse_args()

    from retailvision.config.loader import load_config
    from retailvision.pipeline.capture import VideoFileSource
    from retailvision.pipeline.runner import JsonlSink, Pipeline, process_frame
    from retailvision.pipeline.vision import YoloTracker
    from retailvision.resilience import sysmetrics

    config = load_config(args.config)
    detector = YoloTracker(config.model.weights, config.model.image_size, config.model.confidence, config.model.tracker)
    source = VideoFileSource(args.source)
    pipeline = Pipeline(config, source.frame_size)
    sink = JsonlSink(io.StringIO())

    samples: list[tuple[float, float, int, int]] = []  # (giây, RSS MB, số luồng, số khung)
    started = time.time()
    next_sample = 0.0
    frames = 0
    while time.time() - started < args.seconds:
        frame = source.read()
        if frame is None:  # hết clip: lặp lại, giữ nguyên pipeline và tracker như chạy liên tục
            source.close()
            source = VideoFileSource(args.source)
            continue
        process_frame(pipeline, detector, sink, None, frame)
        frames += 1
        elapsed = time.time() - started
        if elapsed >= next_sample:
            next_sample += args.sample_every
            rss = sysmetrics.process_rss_mb() or float("nan")
            samples.append((round(elapsed, 1), round(rss, 1), threading.active_count(), frames))
            print(f"t={elapsed:6.1f}s rss={rss:7.1f} MB threads={threading.active_count()} frames={frames}", file=sys.stderr, flush=True)
            sink = JsonlSink(io.StringIO())  # sự kiện không cần giữ: tránh tự gây tăng RAM trong bộ đo
    source.close()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["seconds", "rss_mb", "threads", "frames"])
            w.writerows(samples)

    usable = [s for s in samples if s[1] == s[1]]  # bỏ NaN
    if len(usable) < 8:
        print("Quá ít mẫu để kết luận (cần ≥ 8): tăng --seconds.")
        return 2
    quarter = len(usable) // 4
    first = statistics.mean(s[1] for s in usable[1 : quarter + 1])  # bỏ mẫu đầu (khởi động)
    last = statistics.mean(s[1] for s in usable[-quarter:])
    thread_growth = usable[-1][2] - usable[1][2]
    print(f"RSS phần tư đầu {first:.1f} MB, phần tư cuối {last:.1f} MB, tăng {last - first:+.1f} MB; luồng tăng {thread_growth:+d}; {frames} khung")
    ok = (last - first) <= args.max_growth_mb and thread_growth <= 5
    print("ĐẠT" if ok else "KHÔNG ĐẠT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
