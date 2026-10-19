"""Vùng chờ: đếm người có điểm chân trong đa giác đủ thời gian dwell."""

from __future__ import annotations

from retailvision.analytics.geometry import point_in_polygon
from retailvision.core.types import Point, Track


class QueueZone:
    def __init__(self, polygon_px: list[Point], dwell_seconds: float) -> None:
        if len(polygon_px) < 3:
            raise ValueError("Đa giác vùng chờ cần ít nhất 3 đỉnh")
        if dwell_seconds < 0:
            raise ValueError("dwell_seconds không được âm")
        self._polygon = polygon_px
        self._dwell = dwell_seconds
        self._entered_at: dict[int, float] = {}

    def update(self, tracks: list[Track], ts: float) -> int:
        """Trả về số người đủ điều kiện ở thời điểm ts.

        Track rời đa giác hoặc không còn xuất hiện thì bị xoá khỏi bộ đếm dwell,
        nên khi quay lại phải chờ đủ dwell từ đầu.
        """
        present: set[int] = set()
        count = 0
        for track in tracks:
            if not point_in_polygon(track.foot, self._polygon):
                continue
            present.add(track.track_id)
            entered = self._entered_at.setdefault(track.track_id, ts)
            if ts - entered >= self._dwell:
                count += 1

        for tid in [tid for tid in self._entered_at if tid not in present]:
            del self._entered_at[tid]
        return count
