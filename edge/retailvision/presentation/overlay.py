"""Vẽ kết quả lên khung hình để kiểm tra bằng mắt: vạch, vùng chờ, người có ID, số đếm.

Chỉ dùng cho hiệu chuẩn và xem lại; không ảnh hưởng tới sự kiện ghi ra.
Dùng chữ ASCII vì cv2.putText không hiển thị được tiếng Việt.
"""

from __future__ import annotations

import cv2
import numpy as np

from retailvision.core.types import Point, Track

COLOR_LINE = (0, 255, 255)  # vàng
COLOR_ZONE = (255, 128, 0)  # xanh dương nhạt
COLOR_BOX = (0, 255, 0)  # xanh lá
COLOR_FOOT = (0, 0, 255)  # đỏ
FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw(
    image: np.ndarray,
    tracks: list[Track],
    line_px: tuple[Point, Point],
    polygon_px: list[Point],
    status: str,
) -> np.ndarray:
    out = image.copy()
    a, b = (tuple(map(int, p)) for p in line_px)
    cv2.line(out, a, b, COLOR_LINE, 2)
    cv2.polylines(out, [np.array(polygon_px, dtype=np.int32).reshape(-1, 1, 2)], True, COLOR_ZONE, 2)
    for t in tracks:
        x1, y1, x2, y2 = (int(v) for v in t.bbox)
        cv2.rectangle(out, (x1, y1), (x2, y2), COLOR_BOX, 2)
        cv2.putText(out, f"ID {t.track_id}", (x1, max(y1 - 6, 14)), FONT, 0.6, COLOR_BOX, 2)
        cv2.circle(out, (int(t.foot[0]), int(t.foot[1])), 4, COLOR_FOOT, -1)
    cv2.putText(out, status, (10, 28), FONT, 0.7, (255, 255, 255), 2)
    return out
