"""Đếm lượt qua vạch hai chiều, có deadband và chống đếm lặp."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from retailvision.analytics.geometry import segments_intersect, signed_distance
from retailvision.core.types import CrossingEvent, Point, Track


@dataclass
class _TrackState:
    last_seen: float
    stable_side: Optional[int] = None  # -1 hoặc +1; None khi chưa ổn định
    stable_point: Optional[Point] = None
    cand_side: Optional[int] = None
    cand_count: int = 0

    def clear_candidate(self) -> None:
        self.cand_side = None
        self.cand_count = 0


class LineCounter:
    """Đếm lượt qua một đoạn vạch A–B.

    Quy ước phía: -1 là phía có signed_distance âm, +1 là phía dương. Chuyển từ
    -1 sang +1 gọi là A→B và nhận nhãn `a_to_b_direction`; chiều ngược lại nhận
    nhãn đối diện.

    Một lượt được tính khi track đã ổn định ở phía cũ, sang phía mới và đứng
    ở phía mới đủ `min_stable_observations` lần liên tiếp, và đoạn đi từ điểm
    ổn định cuối tới điểm hiện tại cắt đoạn vạch (không phải đường thẳng kéo dài).
    """

    def __init__(
        self,
        line_px: tuple[Point, Point],
        deadband_px: float,
        min_stable_observations: int,
        a_to_b_direction: str,
        track_ttl_s: float = 2.0,
        reassoc_px: float = 80.0,
        reassoc_window_s: float = 2.0,
    ) -> None:
        if min_stable_observations < 1:
            raise ValueError("min_stable_observations phải >= 1")
        if a_to_b_direction not in ("IN", "OUT"):
            raise ValueError("a_to_b_direction phải là IN hoặc OUT")
        self._a, self._b = line_px
        self._deadband = deadband_px
        self._min_stable = min_stable_observations
        self._a_to_b = a_to_b_direction
        self._ttl = track_ttl_s
        self._reassoc_px = reassoc_px
        self._reassoc_window = reassoc_window_s
        self._states: dict[int, _TrackState] = {}

    def update(self, tracks: list[Track], ts: float) -> list[CrossingEvent]:
        events: list[CrossingEvent] = []
        seen_now = {t.track_id for t in tracks}
        for track in tracks:
            st = self._states.setdefault(track.track_id, _TrackState(last_seen=ts))
            st.last_seen = ts
            side = self._side(track.foot)
            if side is None:  # trong dải deadband: không tính, không reset ứng viên
                continue

            if st.stable_side is None:
                if self._bump(st, side) >= self._min_stable:
                    self._settle(st, side, track.foot)
                    matched = self._reassociate(track.track_id, side, ts, seen_now)
                    if matched is not None:
                        events.append(matched)
                continue

            if side == st.stable_side:
                st.stable_point = track.foot
                st.clear_candidate()
                continue

            if self._bump(st, side) >= self._min_stable:
                if segments_intersect(st.stable_point, track.foot, self._a, self._b):
                    events.append(
                        CrossingEvent(
                            track_id=track.track_id,
                            direction=self._direction(st.stable_side, side),
                            ts=ts,
                        )
                    )
                self._settle(st, side, track.foot)

        self._expire(ts)
        return events

    def _reassociate(self, new_id: int, side: int, ts: float, seen_now: set[int]) -> Optional[CrossingEvent]:
        """Track mới vừa ổn định ở phía `side`. Nếu có track cũ vừa mất ở phía đối diện, gần vạch
        và mất trong khoảng reassoc_window_s, coi đó là cùng một người đã qua vạch và tính một lượt.
        Track cũ được xoá để không tính lần thứ hai."""
        for tid, other in list(self._states.items()):
            if tid == new_id or tid in seen_now:
                continue
            if other.stable_side is None or other.stable_side == side or other.stable_point is None:
                continue
            if ts - other.last_seen > self._reassoc_window:
                continue
            if abs(signed_distance(other.stable_point, self._a, self._b)) > self._reassoc_px:
                continue
            direction = self._direction(other.stable_side, side)
            del self._states[tid]
            return CrossingEvent(track_id=new_id, direction=direction, ts=ts)
        return None

    def _side(self, foot: Point) -> Optional[int]:
        d = signed_distance(foot, self._a, self._b)
        if abs(d) <= self._deadband:
            return None
        return 1 if d > 0 else -1

    def _direction(self, from_side: int, to_side: int) -> str:
        a_to_b = from_side == -1 and to_side == 1
        if a_to_b:
            return self._a_to_b
        return "OUT" if self._a_to_b == "IN" else "IN"

    @staticmethod
    def _bump(st: _TrackState, side: int) -> int:
        if st.cand_side == side:
            st.cand_count += 1
        else:
            st.cand_side = side
            st.cand_count = 1
        return st.cand_count

    @staticmethod
    def _settle(st: _TrackState, side: int, point: Point) -> None:
        st.stable_side = side
        st.stable_point = point
        st.clear_candidate()

    def _expire(self, ts: float) -> None:
        stale = [tid for tid, st in self._states.items() if ts - st.last_seen > self._ttl]
        for tid in stale:
            del self._states[tid]
