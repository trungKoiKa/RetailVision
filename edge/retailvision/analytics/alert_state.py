"""Máy trạng thái cảnh báo: NORMAL / OVERLOAD / UNKNOWN.

Thuần: không đọc đồng hồ, mọi thời điểm đi vào qua `ts` (giây).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from retailvision.core.types import AlertTransition


class AlertState(str, Enum):
    UNKNOWN = "UNKNOWN"
    NORMAL = "NORMAL"
    OVERLOAD = "OVERLOAD"


@dataclass(frozen=True)
class AlertSettings:
    on_count: int
    on_hold_seconds: float
    off_count: int
    off_hold_seconds: float

    def __post_init__(self) -> None:
        if self.on_count < 1:
            raise ValueError("on_count phải >= 1")
        if self.off_count < 0:
            raise ValueError("off_count không được âm")
        if self.off_count >= self.on_count:
            raise ValueError("off_count phải nhỏ hơn on_count")
        if self.on_hold_seconds < 0 or self.off_hold_seconds < 0:
            raise ValueError("thời gian giữ không được âm")


class AlertStateMachine:
    def __init__(
        self,
        settings: AlertSettings,
        new_alert_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._settings = settings
        self._new_alert_id = new_alert_id
        self.state = AlertState.UNKNOWN
        self.alert_id: Optional[str] = None
        self.acked = False
        self._above_since: Optional[float] = None
        self._below_since: Optional[float] = None

    @property
    def settings(self) -> AlertSettings:
        return self._settings

    def on_observation(self, queue_count: int, ts: float) -> list[AlertTransition]:
        """Nhận số người đủ điều kiện tại ts. Dữ liệu mới luôn đưa UNKNOWN về NORMAL."""
        out: list[AlertTransition] = []
        s = self._settings
        if self.state is AlertState.UNKNOWN:
            self.state = AlertState.NORMAL

        if self.state is AlertState.NORMAL:
            if queue_count >= s.on_count:
                if self._above_since is None:
                    self._above_since = ts
                if ts - self._above_since >= s.on_hold_seconds:
                    self._open(queue_count, ts, out)
            else:
                self._above_since = None

        elif self.state is AlertState.OVERLOAD:
            if queue_count <= s.off_count:
                if self._below_since is None:
                    self._below_since = ts
                if ts - self._below_since >= s.off_hold_seconds:
                    self._end("NORMALIZED", queue_count, ts, out)
            else:
                self._below_since = None
        return out

    def on_stale(self, ts: float) -> list[AlertTransition]:
        """Mất dữ liệu: vào UNKNOWN; alert đang mở kết thúc với INTERRUPTED."""
        out: list[AlertTransition] = []
        if self.state is AlertState.OVERLOAD:
            self._end("INTERRUPTED", None, ts, out)
        self.state = AlertState.UNKNOWN
        self._above_since = None
        self._below_since = None
        return out

    def on_ack(self, alert_id: str, ack_id: str, device_id: str, ts: float) -> list[AlertTransition]:
        """ACK chỉ ghi nhận đã thấy cảnh báo; không đổi trạng thái OVERLOAD."""
        if self.state is not AlertState.OVERLOAD or alert_id != self.alert_id or self.acked:
            return []
        self.acked = True
        return [
            AlertTransition(
                kind="ACK",
                alert_id=self.alert_id,
                ts=ts,
                ack_id=ack_id,
                ack_device_id=device_id,
            )
        ]

    def apply_settings(self, settings: AlertSettings, ts: float) -> list[AlertTransition]:
        """Đổi ngưỡng: alert đang mở kết thúc với CONFIG_CHANGED, timer tính lại."""
        if settings == self._settings:
            return []
        out: list[AlertTransition] = []
        if self.state is AlertState.OVERLOAD:
            self._end("CONFIG_CHANGED", None, ts, out)
            self.state = AlertState.NORMAL
        self._settings = settings
        self._above_since = None
        self._below_since = None
        return out

    def _open(self, queue_count: int, ts: float, out: list[AlertTransition]) -> None:
        self.state = AlertState.OVERLOAD
        self.alert_id = self._new_alert_id()
        self.acked = False
        self._below_since = None
        out.append(AlertTransition(kind="OPEN", alert_id=self.alert_id, ts=ts, queue_count=queue_count))

    def _end(self, reason: str, queue_count: Optional[int], ts: float, out: list[AlertTransition]) -> None:
        out.append(
            AlertTransition(
                kind="END",
                alert_id=self.alert_id,
                ts=ts,
                queue_count=queue_count,
                reason=reason,
            )
        )
        self.state = AlertState.NORMAL
        self.alert_id = None
        self.acked = False
        self._above_since = None
        self._below_since = None
