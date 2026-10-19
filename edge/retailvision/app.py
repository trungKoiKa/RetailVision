"""Điểm vào của edge.

Ví dụ:
    python -m retailvision.app --config ../configs/examples/site01-video.yaml --check-config
    python -m retailvision.app --config ../configs/examples/site01-video.yaml \\
        --source ../data/raw/clip.mp4 --events-out ../evaluation/results/run.jsonl
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import cv2

from pydantic import ValidationError

from retailvision.config.loader import load_config
from retailvision.pipeline.capture import CameraSource, Frame, VideoFileSource
from retailvision.pipeline.runner import JsonlSink, Pipeline, open_events_file, run_pipeline
from retailvision.presentation.overlay import draw

CAMERA_STALE_POLL_S = 0.01
WINDOW_NAME = "RetailVision"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="retailvision.app", description=__doc__.split("\n")[0])
    parser.add_argument("--config", type=Path, required=True, help="file YAML cấu hình edge")
    parser.add_argument("--source", type=Path, help="ghi đè nguồn bằng file video")
    parser.add_argument("--events-out", type=Path, help="ghi sự kiện JSONL (mặc định: stdout)")
    parser.add_argument("--video-out", type=Path, help="ghi video đã vẽ vạch, vùng chờ, ID người (chỉ khi xử lý file)")
    parser.add_argument("--show", action="store_true", help="mở cửa sổ xem trực tiếp; nhấn q để dừng")
    parser.add_argument("--check-config", action="store_true", help="chỉ kiểm tra cấu hình rồi thoát")
    return parser


def _summary(events_seen: dict, processed: int) -> str:
    return (
        f"khung đã xử lý: {processed}; "
        f"lượt IN: {events_seen['IN']}, OUT: {events_seen['OUT']}; "
        f"cảnh báo mở: {events_seen['OPEN']}, ACK: {events_seen['ACK']}, kết thúc: {events_seen['END']}"
    )


class _Counts(dict):
    def __init__(self) -> None:
        super().__init__(IN=0, OUT=0, OPEN=0, ACK=0, END=0)

    def observe(self, events: list[dict]) -> None:
        for e in events:
            if e["type"] == "crossing":
                self[e["direction"]] += 1
            elif e["type"] == "alert":
                self[e["kind"]] += 1


class _CountingSink:
    """Ghi sự kiện ra file và đếm để in tóm tắt cuối phiên."""

    def __init__(self, sink: JsonlSink, counts: _Counts) -> None:
        self._sink = sink
        self._counts = counts

    def write(self, events: list[dict]) -> None:
        self._counts.observe(events)
        self._sink.write(events)


def _wait_first_frame(read, timeout_s: float = 10.0) -> Frame:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        frame = read()
        if frame is not None:
            return frame
        time.sleep(CAMERA_STALE_POLL_S)
    raise RuntimeError("Camera không trả khung hình trong 10 giây")


def run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except (ValidationError, ValueError) as exc:
        print(f"Cấu hình không hợp lệ: {exc}", file=sys.stderr)
        return 2

    if args.check_config:
        print(f"Cấu hình hợp lệ: site={config.site_id} profile={config.profile} version={config.config_version}")
        return 0

    from retailvision.pipeline.vision import YoloTracker

    detector = YoloTracker(
        weights=config.model.weights,
        image_size=config.model.image_size,
        confidence=config.model.confidence,
        tracker=config.model.tracker,
    )

    counts = _Counts()
    out = open_events_file(args.events_out)
    sink = _CountingSink(JsonlSink(out), counts)
    processed = 0
    try:
        if args.source is not None or config.source.type == "video":
            path = args.source or config.source.path
            source = VideoFileSource(path)
            pipeline = Pipeline(config, source.frame_size)
            writer = None
            if args.video_out is not None:
                args.video_out.parent.mkdir(parents=True, exist_ok=True)
                fps = source.fps or 25.0
                writer = cv2.VideoWriter(
                    str(args.video_out), cv2.VideoWriter_fourcc(*"mp4v"), fps, source.frame_size
                )
                if not writer.isOpened():
                    raise RuntimeError(f"Không tạo được file video: {args.video_out}")
            if args.show:
                cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

            drawn = {"n": 0}

            def observer(frame, tracks, pl):
                drawn["n"] += 1
                status = (
                    f"t={frame.ts:6.1f}s  IN={pl.in_count}  OUT={pl.out_count}  "
                    f"queue={pl.last_queue_count}  state={pl.alert.state.value}"
                )
                annotated = draw(frame.image, tracks, pl.line_px, pl.polygon_px, status)
                if writer is not None:
                    writer.write(annotated)
                if args.show:
                    cv2.imshow(WINDOW_NAME, annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        raise KeyboardInterrupt

            observer_needed = writer is not None or args.show
            try:
                run_pipeline(pipeline, source.read, detector, sink, observer=observer if observer_needed else None)
            finally:
                processed = drawn["n"] if observer_needed else processed
                if writer is not None:
                    writer.release()
                if args.show:
                    cv2.destroyAllWindows()
            source.close()
        else:
            processed = _run_camera(config, detector, sink)
    except KeyboardInterrupt:
        print("Dừng theo yêu cầu.", file=sys.stderr)
    finally:
        if args.events_out is not None:
            out.close()
    print(_summary(counts, processed), file=sys.stderr)
    return 0


def _run_camera(config, detector, sink: _CountingSink) -> int:
    """Chạy camera thật cho đến khi nhấn Ctrl+C. Mất khung hình quá lâu thì vào UNKNOWN."""
    source = CameraSource(config.source.index, config.source.width, config.source.height)
    try:
        first = _wait_first_frame(source.read)
        h, w = first.image.shape[:2]
        pipeline = Pipeline(config, (w, h))
        stale_s = config.health.stale_seconds
        last_frame_at = time.monotonic()
        is_stale = False
        processed = 0

        frame: Optional[Frame] = first
        while True:
            now = time.monotonic()
            if frame is not None:
                last_frame_at = now
                is_stale = False
                tracks = detector.process(frame.image)
                sink.write(pipeline.step(tracks, frame.ts))
                processed += 1
            elif not is_stale and now - last_frame_at > stale_s:
                is_stale = True
                sink.write(pipeline.stale(now))
            time.sleep(CAMERA_STALE_POLL_S)
            frame = source.read()
    finally:
        source.close()
    return processed


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
