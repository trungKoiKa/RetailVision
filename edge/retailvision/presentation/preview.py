"""Xem trước MJPEG qua HTTP, chỉ chạy khi được bật rõ ràng (`--preview-port`).

Dùng để hiệu chuẩn vạch/vùng chờ hoặc demo; tắt cờ thì không có cổng nào mở. Ảnh chỉ nằm trong RAM
(khung mới nhất), không ghi đĩa. Mặc định chỉ nghe 127.0.0.1; muốn xem từ máy khác trong LAN phải đặt
`--preview-host` rõ ràng. Chỉ mã hoá JPEG khi có người xem để không tốn CPU của Pi lúc vận hành.
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

import cv2
import numpy as np

BOUNDARY = "rvframe"
PAGE = (
    b"<!doctype html><meta charset=utf-8><title>RetailVision preview</title>"
    b"<body style='margin:0;background:#111'><img src='/stream.mjpg' style='max-width:100%'></body>"
)


class PreviewServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8081, jpeg_quality: int = 70) -> None:
        self._quality = jpeg_quality
        self._cond = threading.Condition()
        self._jpeg: Optional[bytes] = None
        self._seq = 0
        self._viewers = 0
        self._closed = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # không ghi log từng request
                pass

            def do_GET(self) -> None:  # noqa: N802
                if self.path in ("/", "/index.html"):
                    self._send(200, "text/html; charset=utf-8", PAGE)
                elif self.path.startswith("/snapshot.jpg"):
                    jpeg = owner._wait_frame(after=-1, timeout=3.0)
                    if jpeg is None:
                        self._send(503, "text/plain", b"chua co khung hinh")
                    else:
                        self._send(200, "image/jpeg", jpeg[1])
                elif self.path.startswith("/stream.mjpg"):
                    self._stream()
                else:
                    self._send(404, "text/plain", b"not found")

            def _send(self, code: int, ctype: str, body: bytes) -> None:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _stream(self) -> None:
                self.send_response(200)
                self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                seq = -1
                with owner._viewer():
                    try:
                        while not owner._closed:
                            item = owner._wait_frame(after=seq, timeout=2.0)
                            if item is None:
                                continue
                            seq, jpeg = item
                            self.wfile.write(
                                f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n".encode()
                                + jpeg
                                + b"\r\n"
                            )
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        pass

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="preview", daemon=True)

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    @property
    def has_viewers(self) -> bool:
        with self._cond:
            return self._viewers > 0

    def start(self) -> "PreviewServer":
        self._thread.start()
        return self

    def publish(self, image: np.ndarray) -> None:
        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self._quality])
        if not ok:
            return
        with self._cond:
            self._jpeg = buf.tobytes()
            self._seq += 1
            self._cond.notify_all()

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._jpeg = None
            self._cond.notify_all()
        self._httpd.shutdown()
        self._httpd.server_close()

    # --- nội bộ ---
    def _viewer(self):
        owner = self

        class _Ctx:
            def __enter__(self_inner):
                with owner._cond:
                    owner._viewers += 1

            def __exit__(self_inner, *exc):
                with owner._cond:
                    owner._viewers -= 1

        return _Ctx()

    def _wait_frame(self, after: int, timeout: float) -> Optional[tuple[int, bytes]]:
        """Chờ khung mới hơn `after`. after=-1 (snapshot) lấy khung mới nhất; báo có người xem trong lúc chờ."""
        deadline = time.monotonic() + timeout
        with self._cond:
            if after < 0:
                self._viewers += 1  # để vòng xử lý biết cần mã hoá khung kế tiếp
                try:
                    start_seq = self._seq
                    while self._seq == start_seq and not self._closed:
                        left = deadline - time.monotonic()
                        if left <= 0:
                            break
                        self._cond.wait(left)
                    return (self._seq, self._jpeg) if self._jpeg is not None and self._seq != start_seq else None
                finally:
                    self._viewers -= 1
            while self._seq <= after and not self._closed:
                left = deadline - time.monotonic()
                if left <= 0:
                    return None
                self._cond.wait(left)
            if self._closed or self._jpeg is None:
                return None
            return self._seq, self._jpeg
