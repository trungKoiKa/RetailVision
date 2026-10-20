"""Dựng bản tin đúng contracts/mqtt. Mọi bản tin có envelope chung; seq tăng trong một session."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional


@dataclass(frozen=True)
class Message:
    topic: str
    payload: dict
    qos: int
    retain: bool = False


def iso_utc(moment: datetime) -> str:
    """ISO 8601 UTC, mili giây, hậu tố Z (khớp pattern trong schema)."""
    moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def minute_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")


class EnvelopeFactory:
    def __init__(
        self,
        site_id: str,
        device_id: str,
        config_version: str,
        session_id: Optional[str] = None,
        new_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.site_id = site_id
        self.device_id = device_id
        self.config_version = config_version
        self.session_id = session_id or new_id()
        self._new_id = new_id
        self._seq = 0
        self._lock = threading.Lock()  # status ONLINE được dựng trong luồng mạng của paho

    def _envelope(self, occurred_at: datetime) -> dict:
        with self._lock:
            seq = self._seq
            self._seq += 1
        body = {
            "schema_version": 1,
            "event_id": self._new_id(),
            "site_id": self.site_id,
            "device_id": self.device_id,
            "session_id": self.session_id,
            "seq": seq,
            "occurred_at": iso_utc(occurred_at),
            "config_version": self.config_version,
        }
        return body

    def crossing(self, occurred_at: datetime, direction: str, track_id: int, line_id: str, profile: str) -> dict:
        return {
            **self._envelope(occurred_at),
            "direction": direction,
            "track_id": track_id,
            "line_id": line_id,
            "profile": profile,
        }

    def alert(
        self,
        occurred_at: datetime,
        alert_id: str,
        transition: str,
        queue_count: Optional[int] = None,
        reason: Optional[str] = None,
        ack_id: Optional[str] = None,
        ack_device_id: Optional[str] = None,
    ) -> dict:
        return {
            **self._envelope(occurred_at),
            "alert_id": alert_id,
            "transition": transition,
            "queue_count": queue_count,
            "reason": reason,
            "ack_id": ack_id,
            "ack_device_id": ack_device_id,
        }

    def state(
        self,
        occurred_at: datetime,
        observed_at: datetime,
        state: str,
        queue_count: Optional[int],
        alert_id: Optional[str],
        acked: bool,
        settings_revision: int = 0,
    ) -> dict:
        # UNKNOWN không bao giờ mang số người: contract bắt queue_count = null
        return {
            **self._envelope(occurred_at),
            "observed_at": iso_utc(observed_at),
            "state": state,
            "queue_count": None if state == "UNKNOWN" else queue_count,
            "alert_id": alert_id,
            "acked": acked,
            "settings_revision": settings_revision,
        }

    def telemetry(
        self,
        occurred_at: datetime,
        minute_start: datetime,
        valid_seconds: int,
        queue_avg: Optional[float],
        queue_max: Optional[int],
        fps: float,
        frame_age_ms: int,
    ) -> dict:
        return {
            **self._envelope(occurred_at),
            "minute_start": minute_iso(minute_start),
            "valid_seconds": valid_seconds,
            "queue_avg": queue_avg,
            "queue_max": queue_max,
            "fps": fps,
            "frame_age_ms": frame_age_ms,
        }

    def settings_result(
        self, occurred_at: datetime, request_id: str, result: str, settings_revision: int, reason: Optional[str]
    ) -> dict:
        return {
            **self._envelope(occurred_at),
            "request_id": request_id,
            "result": result,
            "settings_revision": settings_revision,
            "reason": reason,
        }

    def status(self, occurred_at: datetime, status: str, version: str, clock_synced: bool) -> dict:
        return {
            **self._envelope(occurred_at),
            "status": status,
            "version": version,
            "clock_synced": clock_synced,
        }
