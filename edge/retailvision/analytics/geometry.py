"""Hình học thuần: toạ độ, khoảng cách có dấu, cắt đoạn, điểm trong đa giác."""

from __future__ import annotations

import math
from typing import Sequence

from retailvision.core.types import Point


def to_pixels(points_norm: Sequence[Point], width: int, height: int) -> list[Point]:
    """Đổi toạ độ chuẩn hoá 0–1 sang pixel."""
    return [(x * width, y * height) for x, y in points_norm]


def signed_distance(p: Point, a: Point, b: Point) -> float:
    """Khoảng cách có dấu từ p tới đường thẳng AB.

    Dương khi p nằm bên trái của vector A→B (theo hệ toạ độ ảnh có y hướng xuống,
    dấu chỉ dùng để phân biệt hai phía, không mang ý nghĩa hình học tuyệt đối).
    """
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length == 0:
        raise ValueError("Đoạn vạch có hai đầu trùng nhau")
    return (dx * (py - ay) - dy * (px - ax)) / length


def _orientation(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _strictly_opposite(x: float, y: float) -> bool:
    return (x > 0 and y < 0) or (x < 0 and y > 0)


def segments_intersect(p1: Point, p2: Point, a: Point, b: Point) -> bool:
    """Đoạn p1–p2 có cắt đoạn a–b không (không tính trường hợp chạm đầu mút hoặc song song)."""
    d1 = _orientation(a, b, p1)
    d2 = _orientation(a, b, p2)
    d3 = _orientation(p1, p2, a)
    d4 = _orientation(p1, p2, b)
    return _strictly_opposite(d1, d2) and _strictly_opposite(d3, d4)


def point_in_polygon(p: Point, polygon: Sequence[Point]) -> bool:
    """Ray casting. Điểm nằm trên cạnh được coi là ngoài đa giác (đủ cho ngưỡng pixel)."""
    x, y = p
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside
