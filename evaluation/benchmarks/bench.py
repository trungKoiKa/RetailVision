"""Benchmark toàn luồng edge trên cùng một clip: so nhiều biến thể model (.pt, NCNN) ở nhiều kích thước.

Mỗi biến thể chạy đúng pipeline thật (đọc khung → detect + track → đếm vạch/vùng chờ/cảnh báo) trong
`--seconds` giây đồng hồ rồi ghi một dòng CSV. Clip ngắn hơn thì được lặp lại. Số đo nhiệt, throttling,
RAM chỉ có trên Pi; máy khác ghi trống (không bịa). Ghi `--note` để biết máy/OS/nguồn khi đọc lại.

Ví dụ trên Pi:
    python evaluation/benchmarks/bench.py --config configs/examples/site01-video.yaml \\
        --source data/raw/clip.mp4 --seconds 60 --out evaluation/results/bench.csv \\
        --note "Pi4 4GB, Bookworm 64-bit, nguon 5V/3A" \\
        --variant pt320=models/source/yolov8n.pt:320 \\
        --variant ncnn320=models/exported/yolov8n_ncnn_320/yolov8n_ncnn_model:320
"""

from __future__ import annotations

import argparse
import csv
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "edge"))

from retailvision.config.loader import EdgeConfig, load_config  # noqa: E402
from retailvision.pipeline.runner import Pipeline  # noqa: E402
from retailvision.resilience import sysmetrics  # noqa: E402

WARMUP_FRAMES = 10
COLUMNS = [
    "timestamp_utc", "variant", "imgsz", "frames", "seconds", "fps_pipeline", "fps_model",
    "read_ms_mean", "detect_ms_mean", "detect_ms_p95", "analytics_ms_mean", "loop_ms_p95",
    "people_mean", "rss_mb_peak", "cpu_temp_c_max", "throttled_any", "config_version", "device", "note",
]


@dataclass(frozen=True)
class VariantSpec:
    name: str
    weights: Path
    imgsz: int


def parse_variant(text: str) -> VariantSpec:
    """`ten=duong/dan:kich_thuoc`. Tách `:` cuối cùng để đường dẫn Windows (C:\\...) không bị cắt nhầm."""
    name, sep, rest = text.partition("=")
    path, sep2, size = rest.rpartition(":")
    if not sep or not sep2 or not name or not path or not size.isdigit() or int(size) <= 0:
        raise ValueError(f"biến thể sai dạng ten=duong/dan:kich_thuoc: {text!r}")
    return VariantSpec(name, Path(path), int(size))


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def run_variant(
    spec: VariantSpec,
    config: EdgeConfig,
    source_factory: Callable[[], object],
    detector_factory: Callable[[VariantSpec], object],
    seconds: float,
    clock: Callable[[], float] = time.perf_counter,
    note: str = "",
    max_frames: Optional[int] = None,
) -> dict:
    detector = detector_factory(spec)
    source = source_factory()
    first = source.read()
    if first is None:
        raise RuntimeError("nguồn không có khung hình nào")
    h, w = first.image.shape[:2]
    pipeline = Pipeline(config, (w, h))

    read_ms: list[float] = []
    detect_ms: list[float] = []
    analytics_ms: list[float] = []
    loop_ms: list[float] = []
    people: list[int] = []
    rss_peak = 0.0
    temps: list[float] = []
    throttled_any: Optional[bool] = None
    seen = 0
    started: Optional[float] = None
    next_sample = 0.0
    pending = first

    while True:
        t0 = clock()
        frame = pending if pending is not None else source.read()
        pending = None
        if frame is None:  # hết clip: mở lại để đo đủ thời gian
            source.close()
            source = source_factory()
            frame = source.read()
            if frame is None:
                break
        t1 = clock()
        tracks = detector.process(frame.image)
        t2 = clock()
        pipeline.step(tracks, frame.ts)
        t3 = clock()
        seen += 1
        if seen <= WARMUP_FRAMES:
            continue
        if started is None:
            started = t0
        read_ms.append((t1 - t0) * 1000)
        detect_ms.append((t2 - t1) * 1000)
        analytics_ms.append((t3 - t2) * 1000)
        loop_ms.append((t3 - t0) * 1000)
        people.append(len(tracks))
        elapsed = t3 - started
        if elapsed >= next_sample:
            next_sample += 5.0
            rss = sysmetrics.process_rss_mb()
            rss_peak = max(rss_peak, rss or 0.0)
            temp = sysmetrics.cpu_temp_c()
            if temp is not None:
                temps.append(temp)
            flags = sysmetrics.throttled_flags()
            if flags is not None:
                throttled_any = bool(throttled_any) or any(v for k, v in flags.items() if k != "raw")
        if elapsed >= seconds or (max_frames is not None and len(loop_ms) >= max_frames):
            break
    source.close()
    if not loop_ms:
        raise RuntimeError("không đo được khung hình nào (clip quá ngắn so với số khung khởi động)")

    elapsed = (clock() - started) if started is not None else 0.0
    return {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "variant": spec.name,
        "imgsz": spec.imgsz,
        "frames": len(loop_ms),
        "seconds": round(elapsed, 1),
        "fps_pipeline": round(len(loop_ms) / elapsed, 2) if elapsed > 0 else None,
        "fps_model": round(1000.0 / statistics.mean(detect_ms), 2),
        "read_ms_mean": round(statistics.mean(read_ms), 1),
        "detect_ms_mean": round(statistics.mean(detect_ms), 1),
        "detect_ms_p95": round(percentile(detect_ms, 0.95), 1),
        "analytics_ms_mean": round(statistics.mean(analytics_ms), 2),
        "loop_ms_p95": round(percentile(loop_ms, 0.95), 1),
        "people_mean": round(statistics.mean(people), 2),
        "rss_mb_peak": round(rss_peak, 1) if rss_peak else "",
        "cpu_temp_c_max": max(temps) if temps else "",
        "throttled_any": "" if throttled_any is None else throttled_any,
        "config_version": config.config_version,
        "device": sysmetrics.device_model() or platform.platform(),
        "note": note,
    }


def append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--config", type=Path, required=True, help="cấu hình edge (vạch, vùng chờ, tracker)")
    p.add_argument("--source", type=Path, required=True, help="clip dùng chung cho mọi biến thể")
    p.add_argument("--variant", action="append", required=True, help="ten=duong/dan:kich_thuoc (lặp lại nhiều lần)")
    p.add_argument("--seconds", type=float, default=60.0, help="thời gian đo mỗi biến thể, sau khi khởi động")
    p.add_argument("--out", type=Path, required=True, help="file CSV (ghi nối tiếp)")
    p.add_argument("--note", default="", help="ghi chú: máy, OS, nguồn điện, nhiệt độ phòng...")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    from retailvision.pipeline.capture import VideoFileSource
    from retailvision.pipeline.vision import YoloTracker

    config = load_config(args.config)
    specs = [parse_variant(v) for v in args.variant]
    for spec in specs:
        print(f"== {spec.name}: {spec.weights} imgsz={spec.imgsz}", file=sys.stderr, flush=True)
        row = run_variant(
            spec,
            config,
            source_factory=lambda: VideoFileSource(args.source),
            detector_factory=lambda s: YoloTracker(s.weights, s.imgsz, config.model.confidence, config.model.tracker),
            seconds=args.seconds,
            note=args.note,
        )
        append_csv(args.out, row)
        print(
            f"   fps_pipeline={row['fps_pipeline']} fps_model={row['fps_model']} "
            f"detect_p95={row['detect_ms_p95']} ms rss={row['rss_mb_peak']} MB",
            file=sys.stderr,
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
