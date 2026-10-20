"""Tổng hợp telemetry theo phút. Phút không có dữ liệu vẫn được báo (valid_seconds = 0), không bỏ trống."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

MAX_BACKFILL_MINUTES = 120


@dataclass
class MinuteSummary:
    minute_start: datetime
    valid_seconds: int
    queue_avg: Optional[float]
    queue_max: Optional[int]
    fps: float
    frame_age_ms: int


@dataclass
class _Bucket:
    minute: datetime
    seconds: set = field(default_factory=set)
    frames: int = 0
    queue_sum: int = 0
    queue_max: Optional[int] = None
    frame_age_max: int = 0

    def summary(self) -> MinuteSummary:
        valid = len(self.seconds)
        return MinuteSummary(
            minute_start=self.minute,
            valid_seconds=valid,
            queue_avg=round(self.queue_sum / self.frames, 2) if self.frames else None,
            queue_max=self.queue_max,
            # khung/giây tính trên số giây có phân tích, để phút khởi động dở dang không bị đánh thấp
            fps=round(self.frames / valid, 2) if valid else 0.0,
            frame_age_ms=self.frame_age_max,
        )


def _floor_minute(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc).replace(second=0, microsecond=0)


class MinuteAggregator:
    def __init__(self) -> None:
        self._bucket: Optional[_Bucket] = None

    def add(self, wall: datetime, queue_count: int, frame_age_ms: int) -> list[MinuteSummary]:
        """Ghi một lần phân tích hợp lệ. Trả về các phút vừa kết thúc."""
        done = self.advance(wall)
        bucket = self._bucket
        bucket.seconds.add(int(wall.timestamp()))
        bucket.frames += 1
        bucket.queue_sum += queue_count
        bucket.queue_max = queue_count if bucket.queue_max is None else max(bucket.queue_max, queue_count)
        bucket.frame_age_max = max(bucket.frame_age_max, frame_age_ms)
        return done

    def advance(self, wall: datetime) -> list[MinuteSummary]:
        """Đóng các phút đã qua tính đến `wall`, kể cả phút không có dữ liệu."""
        minute = _floor_minute(wall)
        if self._bucket is None:
            self._bucket = _Bucket(minute)
            return []
        done: list[MinuteSummary] = []
        while self._bucket.minute < minute:
            done.append(self._bucket.summary())
            next_minute = self._bucket.minute + timedelta(minutes=1)
            if len(done) >= MAX_BACKFILL_MINUTES:
                next_minute = minute  # khoảng trống quá dài: nhảy thẳng tới phút hiện tại
            self._bucket = _Bucket(next_minute)
        return done
