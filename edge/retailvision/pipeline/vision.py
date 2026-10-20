"""Nhận diện người và theo dõi bằng YOLO + tracker (ByteTrack).

Ultralytics được import khi tạo đối tượng, không import lúc nạp module, để các
test analytics không cần cài torch.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import numpy as np

from retailvision.core.types import Track

PERSON_CLASS_ID = 0


def configure_offline() -> None:
    """Không cho Ultralytics gọi ra Internet: nó kiểm DNS tới Cloudflare/Google lúc import và gửi số liệu
    ẩn danh khi thấy mạng. Edge phải chạy được khi mất WAN và không gửi gì ra ngoài (NFR-08, NFR-10)."""
    os.environ.setdefault("YOLO_OFFLINE", "true")


class Detector(Protocol):
    def process(self, image: np.ndarray) -> list[Track]: ...


class YoloTracker:
    def __init__(self, weights: Path, image_size: int, confidence: float, tracker: str) -> None:
        configure_offline()  # phải đặt trước khi import ultralytics
        from ultralytics import YOLO  # import muộn: chỉ cần khi chạy thật

        self._model = YOLO(str(weights), task="detect")
        self._image_size = image_size
        self._confidence = confidence
        self._tracker = tracker

    def reset(self) -> None:
        """Bỏ bộ theo dõi hiện tại (sau khi mất camera) để không nối ID cũ qua khoảng gián đoạn."""
        self._model.predictor = None

    def process(self, image: np.ndarray) -> list[Track]:
        results = self._model.track(
            image,
            persist=True,
            classes=[PERSON_CLASS_ID],
            imgsz=self._image_size,
            conf=self._confidence,
            tracker=self._tracker,
            verbose=False,
        )
        tracks: list[Track] = []
        for result in results:
            boxes = result.boxes
            if boxes is None or boxes.id is None:
                continue  # box chưa có ID tracking: bỏ qua
            ids = boxes.id.int().tolist()
            xyxy = boxes.xyxy.tolist()
            confs = boxes.conf.tolist()
            for track_id, (x1, y1, x2, y2), conf in zip(ids, xyxy, confs):
                foot = ((x1 + x2) / 2.0, y2)  # điểm giữa cạnh dưới bbox
                tracks.append(Track(track_id=track_id, foot=foot, bbox=(x1, y1, x2, y2), conf=conf))
        return tracks
