"""Smoke test cho Raspberry Pi: đọc camera (hoặc video), chạy YOLO + ByteTrack, đo tài nguyên.

Chỉ phụ thuộc ultralytics và opencv, không import code của retailvision, để chạy được
ngay khi mới cài môi trường. In kết quả JSON ra stdout; log tiến trình ra stderr.

Ví dụ trên Pi:
    python smoke_pi.py --weights yolov8n.pt --camera 0 --imgsz 320 --seconds 60 --out smoke.json
Thử trên laptop với file video:
    python smoke_pi.py --weights yolov8n.pt --video clip.mp4 --imgsz 320 --seconds 20
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import cv2

WARMUP_FRAMES = 10
SAMPLE_EVERY_S = 5.0
THROTTLE_BITS = {
    0: "under_voltage_now",
    1: "freq_capped_now",
    2: "throttled_now",
    3: "soft_temp_limit_now",
    16: "under_voltage_occurred",
    17: "freq_capped_occurred",
    18: "throttled_occurred",
    19: "soft_temp_limit_occurred",
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def cpu_temp_c() -> Optional[float]:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return int(path.read_text().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def throttled_flags() -> Optional[dict]:
    """Đọc `vcgencmd get_throttled`; None nếu không phải Pi."""
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3).stdout
        value = int(out.strip().split("=")[1], 16)
    except (OSError, IndexError, ValueError, subprocess.SubprocessError):
        return None
    return {"raw": hex(value), **{name: bool(value >> bit & 1) for bit, name in THROTTLE_BITS.items()}}


def memory_mb() -> Optional[float]:
    """RSS của tiến trình hiện tại (MB), đọc từ /proc hoặc psutil nếu có."""
    try:
        import psutil

        return psutil.Process().memory_info().rss / 1e6
    except ImportError:
        pass
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return None


def system_available_mb() -> Optional[float]:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return None


def model_name() -> Optional[str]:
    try:
        return Path("/proc/device-tree/model").read_bytes().rstrip(b"\0").decode()
    except OSError:
        return None


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def open_source(args: argparse.Namespace) -> cv2.VideoCapture:
    if args.video:
        cap = cv2.VideoCapture(str(args.video))
    else:
        cap = cv2.VideoCapture(args.camera)
        if args.mjpg:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit("Không mở được nguồn video/camera")
    return cap


def run(args: argparse.Namespace) -> dict:
    from ultralytics import YOLO

    model = YOLO(str(args.weights), task="detect")
    cap = open_source(args)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log(f"Nguồn: {width}x{height}, model: {args.weights}, imgsz={args.imgsz}")

    read_ms: list[float] = []
    infer_ms: list[float] = []
    people: list[int] = []
    read_failures = 0
    samples: list[dict] = []
    frames = 0
    track_ids: set[int] = set()
    started = None
    next_sample = 0.0
    peak_rss = 0.0

    while True:
        t0 = time.perf_counter()
        ok, image = cap.read()
        t1 = time.perf_counter()
        if not ok:
            if args.video:
                break
            read_failures += 1
            if read_failures >= 30:
                log("Đọc camera lỗi liên tiếp, dừng")
                break
            continue
        results = model.track(
            image,
            persist=True,
            classes=[0],
            imgsz=args.imgsz,
            conf=args.conf,
            tracker=args.tracker,
            verbose=False,
        )
        t2 = time.perf_counter()
        frames += 1
        if frames <= WARMUP_FRAMES:
            continue  # bỏ các khung đầu: nạp model, khởi tạo bộ nhớ đệm
        if started is None:
            started = time.perf_counter()
            next_sample = 0.0
        read_ms.append((t1 - t0) * 1000)
        infer_ms.append((t2 - t1) * 1000)
        boxes = results[0].boxes
        if boxes is not None and boxes.id is not None:
            ids = boxes.id.int().tolist()
            people.append(len(ids))
            track_ids.update(ids)
        else:
            people.append(0)

        elapsed = time.perf_counter() - started
        if elapsed >= next_sample:
            next_sample += SAMPLE_EVERY_S
            rss = memory_mb()
            peak_rss = max(peak_rss, rss or 0.0)
            samples.append(
                {
                    "t": round(elapsed, 1),
                    "cpu_temp_c": cpu_temp_c(),
                    "rss_mb": round(rss, 1) if rss else None,
                    "throttled": throttled_flags(),
                }
            )
            log(f"t={elapsed:5.1f}s khung={len(infer_ms)} temp={samples[-1]['cpu_temp_c']} rss={samples[-1]['rss_mb']}")
        if elapsed >= args.seconds:
            break

    cap.release()
    if not infer_ms:
        raise SystemExit("Không xử lý được khung hình nào")
    elapsed = time.perf_counter() - started
    loop_ms = [r + i for r, i in zip(read_ms, infer_ms)]
    last_throttle = samples[-1]["throttled"] if samples else None
    return {
        "device": {
            "model": model_name(),
            "machine": platform.machine(),
            "os": platform.platform(),
            "python": platform.python_version(),
            "memory_available_mb_after": system_available_mb(),
        },
        "setup": {
            "source": str(args.video) if args.video else f"camera:{args.camera}",
            "frame_size": [width, height],
            "weights": str(args.weights),
            "imgsz": args.imgsz,
            "conf": args.conf,
            "tracker": args.tracker,
            "mjpg": args.mjpg,
            "requested_seconds": args.seconds,
        },
        "result": {
            "frames_measured": len(infer_ms),
            "measured_seconds": round(elapsed, 1),
            "fps_end_to_end": round(len(infer_ms) / elapsed, 2),
            "infer_ms_mean": round(statistics.mean(infer_ms), 1),
            "infer_ms_p95": round(percentile(infer_ms, 0.95), 1),
            "read_ms_mean": round(statistics.mean(read_ms), 1),
            "read_ms_p95": round(percentile(read_ms, 0.95), 1),
            "loop_ms_p95": round(percentile(loop_ms, 0.95), 1),
            "people_mean": round(statistics.mean(people), 2),
            "unique_track_ids": len(track_ids),
            "read_failures": read_failures,
            "rss_mb_peak": round(peak_rss, 1) if peak_rss else None,
            "cpu_temp_c_max": max((s["cpu_temp_c"] for s in samples if s["cpu_temp_c"] is not None), default=None),
            "throttled_last": last_throttle,
        },
        "samples": samples,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--weights", type=Path, required=True)
    src = p.add_mutually_exclusive_group()
    src.add_argument("--camera", type=int, default=0)
    src.add_argument("--video", type=Path)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--mjpg", action="store_true", help="yêu cầu camera xuất MJPG (thường cần cho 720p mượt trên USB)")
    p.add_argument("--imgsz", type=int, default=320)
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--tracker", default="bytetrack.yaml")
    p.add_argument("--seconds", type=float, default=60.0, help="thời gian đo sau khi khởi động")
    p.add_argument("--out", type=Path, help="ghi kết quả JSON ra file")
    return p


def main() -> int:
    args = build_parser().parse_args()
    report = run(args)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
