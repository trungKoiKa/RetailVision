"""Quay clip từ camera ở đúng độ phân giải vận hành để gán nhãn và đánh giá, hoặc chụp một khung hình để hiệu chuẩn.

Video luôn đúng thời gian thực: camera USB thường chậm hơn fps yêu cầu, nên mỗi khung ra được lấp bằng khung mới
nhất tại đúng mốc `k / fps` (lặp khung khi camera chậm). Nhờ đó timestamp trong video khớp thời gian thật và nhãn
theo giây dùng được. File JSON đi kèm ghi giờ bắt đầu UTC, độ phân giải thật, fps đo được; KHÔNG ghi gì về người.

    python -m retailvision.tools.record --out data/raw/buoi1_clip01.avi --seconds 120
    python -m retailvision.tools.record --snapshot data/raw/khung.jpg
Chỉ quay người đã đồng ý. Video không commit (data/raw/ đã .gitignore).
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import cv2


class Resampler:
    """Đưa luồng khung hình có tốc độ bất kỳ về tốc độ cố định theo đồng hồ thực."""

    def __init__(self, fps: float, start: float) -> None:
        if fps <= 0:
            raise ValueError("fps phải dương")
        self._interval = 1.0 / fps
        self._start = start
        self._written = 0

    def due(self, now: float) -> int:
        """Số khung cần ghi ngay bây giờ để video bắt kịp thời gian thực."""
        return max(0, int((now - self._start) / self._interval) + 1 - self._written)

    def wrote(self, n: int = 1) -> None:
        self._written += n

    @property
    def written(self) -> int:
        return self._written


def record(
    out: Path,
    seconds: float,
    camera: int,
    width: int,
    height: int,
    fps: float,
    capture_factory: Callable[[int], "cv2.VideoCapture"] = cv2.VideoCapture,
    clock: Callable[[], float] = time.monotonic,
    now_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict:
    cap = capture_factory(camera)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được camera {camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("Camera không trả khung hình")
    h, w = frame.shape[:2]
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"Không tạo được file video: {out}")

    started_utc = now_utc()
    start = clock()
    resampler = Resampler(fps, start)
    captured = 0
    latest = frame
    captured += 1
    try:
        while True:
            now = clock()
            if now - start >= seconds:
                break
            for _ in range(resampler.due(now)):
                writer.write(latest)
                resampler.wrote()
            ok, frame = cap.read()
            if ok:
                latest = frame
                captured += 1
    finally:
        writer.release()
        cap.release()
    elapsed = clock() - start
    meta = {
        "clip": out.name,
        "started_at": started_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seconds": round(elapsed, 2),
        "camera_index": camera,
        "requested_size": [width, height],
        "actual_size": [w, h],
        "fps_written": fps,
        "fps_captured_measured": round(captured / elapsed, 2) if elapsed > 0 else None,
        "frames_written": resampler.written,
        "frames_captured": captured,
        "codec": "MJPG",
        "host": platform.node(),
    }
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def snapshot(
    out: Path,
    camera: int,
    width: int,
    height: int,
    capture_factory: Callable[[int], "cv2.VideoCapture"] = cv2.VideoCapture,
    warmup_frames: int = 10,
) -> tuple[int, int]:
    """Chụp một khung hình (bỏ vài khung đầu cho camera ổn định phơi sáng) để dùng với calibrate."""
    cap = capture_factory(camera)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được camera {camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    frame = None
    try:
        for _ in range(max(1, warmup_frames)):
            ok, got = cap.read()
            if ok:
                frame = got
    finally:
        cap.release()
    if frame is None:
        raise RuntimeError("Camera không trả khung hình")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), frame):
        raise RuntimeError(f"Không ghi được ảnh: {out}")
    h, w = frame.shape[:2]
    return w, h


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=float, default=15.0)
    parser.add_argument("--seconds", type=float, default=60.0)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path, help="file video .avi")
    group.add_argument("--snapshot", type=Path, help="chỉ chụp một ảnh .jpg")
    args = parser.parse_args(argv)
    if args.snapshot:
        w, h = snapshot(args.snapshot, args.camera, args.width, args.height)
        print(f"Đã chụp {w}x{h}: {args.snapshot}", file=sys.stderr)
        return 0
    meta = record(args.out, args.seconds, args.camera, args.width, args.height, args.fps)
    print(json.dumps(meta, indent=2, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
