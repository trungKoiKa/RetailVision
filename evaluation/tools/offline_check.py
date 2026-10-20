"""T13 phía edge: mô phỏng mất WAN (LAN còn) và đếm số lần tiến trình cố gọi ra ngoài mạng nội bộ.

Chặn trong tiến trình mọi phân giải tên và kết nối tới địa chỉ không thuộc loopback/mạng riêng, rồi chạy
pipeline thật trên clip. Đây là mô phỏng: nó chứng minh edge không DỰA vào Internet, nhưng không thay cho
lần thử thật rút cáp WAN trên Pi (T13, T26).

    python evaluation/tools/offline_check.py --config configs/examples/site01-video.yaml --source clip.mp4
    # in ra danh sách các lần cố gọi ra ngoài; thoát 0 khi không có lần nào
"""

from __future__ import annotations

import argparse
import ipaddress
import socket
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "edge"))

attempts: list[str] = []


def is_local(host: str) -> bool:
    if host in ("localhost", ""):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # tên miền cần DNS: coi là ra ngoài
    return ip.is_loopback or ip.is_private or ip.is_link_local


def install_block() -> None:
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def guarded_getaddrinfo(host, *args, **kwargs):
        if isinstance(host, bytes):
            host = host.decode()
        if host is not None and not is_local(str(host)):
            attempts.append(f"DNS {host}")
            raise socket.gaierror(f"offline_check: chặn phân giải {host}")
        return real_getaddrinfo(host, *args, **kwargs)

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) else str(address)
        if not is_local(str(host)):
            attempts.append(f"CONNECT {address}")
            raise OSError(f"offline_check: chặn kết nối tới {address}")
        return real_connect(self, address)

    socket.getaddrinfo = guarded_getaddrinfo
    socket.socket.connect = guarded_connect


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=150)
    args = parser.parse_args()

    install_block()  # trước khi import ultralytics: nó kiểm Internet ngay lúc import
    import io

    from retailvision.config.loader import load_config
    from retailvision.pipeline.capture import VideoFileSource
    from retailvision.pipeline.runner import JsonlSink, Pipeline, process_frame
    from retailvision.pipeline.vision import YoloTracker

    config = load_config(args.config)
    detector = YoloTracker(config.model.weights, config.model.image_size, config.model.confidence, config.model.tracker)
    source = VideoFileSource(args.source)
    pipeline = Pipeline(config, source.frame_size)
    sink = JsonlSink(io.StringIO())
    frames = 0
    while frames < args.max_frames:
        frame = source.read()
        if frame is None:
            break
        process_frame(pipeline, detector, sink, None, frame)
        frames += 1
    source.close()

    print(f"Đã xử lý {frames} khung hình khi chặn mọi kết nối ra ngoài mạng nội bộ.")
    if attempts:
        print(f"{len(attempts)} lần cố gọi ra ngoài:")
        for a in sorted(set(attempts)):
            print("  ", a)
        return 1
    print("Không có lần nào cố gọi ra ngoài.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
