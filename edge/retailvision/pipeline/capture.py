"""Nguồn khung hình: file video (chạy lại có timestamp) hoặc camera trực tiếp.

Mọi nguồn trả `Frame`; runner không cần biết đang đọc từ đâu.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class Frame:
    image: np.ndarray  # BGR, kích thước gốc của nguồn
    ts: float  # giây: timestamp video khi replay, monotonic khi live
    index: int


class VideoFileSource:
    """Đọc file video tuần tự. ts lấy từ vị trí phát của video, không phụ thuộc tốc độ máy."""

    def __init__(self, path: Path) -> None:
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            raise RuntimeError(f"Không mở được video: {path}")
        self._index = 0
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 0.0

    @property
    def frame_size(self) -> tuple[int, int]:
        return (
            int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def read(self) -> Optional[Frame]:
        ok, image = self._cap.read()
        if not ok:
            return None
        ts = self._cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if ts <= 0 and self._fps > 0:  # một số codec không báo vị trí: suy từ chỉ số khung
            ts = self._index / self._fps
        frame = Frame(image=image, ts=ts, index=self._index)
        self._index += 1
        return frame

    def close(self) -> None:
        self._cap.release()


class CameraSource:
    """Camera USB chạy trên luồng riêng, chỉ giữ khung hình mới nhất.

    Khung cũ bị bỏ thay vì xếp hàng, để độ trễ không tích luỹ. Đọc lỗi liên tiếp
    thì đóng và mở lại sau 2 giây.
    """

    def __init__(self, index: int, width: int, height: int) -> None:
        self._index_dev = index
        self._size = (width, height)
        self._lock = threading.Lock()
        self._latest: Optional[Frame] = None
        self._frames = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _open(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self._index_dev)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._size[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._size[1])
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _loop(self) -> None:
        cap = self._open()
        errors = 0
        while not self._stop.is_set():
            ok, image = cap.read()
            if not ok:
                errors += 1
                if errors >= 10:
                    cap.release()
                    time.sleep(2.0)
                    cap = self._open()
                    errors = 0
                continue
            errors = 0
            with self._lock:
                self._frames += 1
                self._latest = Frame(image=image, ts=time.monotonic(), index=self._frames)
        cap.release()

    def read(self) -> Optional[Frame]:
        """Khung mới nhất chưa được đọc, hoặc None nếu chưa có khung mới."""
        with self._lock:
            frame, self._latest = self._latest, None
        return frame

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3.0)
