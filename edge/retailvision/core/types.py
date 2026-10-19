"""Kiểu dữ liệu dùng chung giữa pipeline và analytics.

Analytics chỉ làm việc với toạ độ pixel và số giây (`ts`). Thời điểm UTC để
ghi vào bản tin do tầng messaging/runner gắn vào, không đưa vào đây.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

Point = Tuple[float, float]


@dataclass(frozen=True)
class Track:
    """Một người đang được theo dõi trong frame hiện tại."""

    track_id: int
    foot: Point  # điểm giữa cạnh dưới bbox, pixel của frame gốc
    bbox: Tuple[float, float, float, float]
    conf: float


@dataclass(frozen=True)
class CrossingEvent:
    track_id: int
    direction: str  # "IN" | "OUT"
    ts: float


@dataclass(frozen=True)
class AlertTransition:
    kind: str  # "OPEN" | "ACK" | "END"
    alert_id: str
    ts: float
    queue_count: Optional[int] = None
    reason: Optional[str] = None  # chỉ với END: NORMALIZED | INTERRUPTED | CONFIG_CHANGED
    ack_id: Optional[str] = None
    ack_device_id: Optional[str] = None
