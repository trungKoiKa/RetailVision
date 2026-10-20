"""Xử lý lệnh đổi ngưỡng `settings/set` từ backend (P1).

Quy tắc: áp dụng nguyên bộ hoặc từ chối; revision cũ không ghi đè; cùng `request_id` giao lại (QoS 1) không áp
dụng hai lần mà trả lại đúng kết quả cũ; giá trị sai thì giữ cấu hình hiện tại.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from retailvision.config.settings import OperatingSettings, SettingsStore

REMEMBER_REQUESTS = 50


@dataclass(frozen=True)
class SettingsResult:
    request_id: str
    result: str  # "APPLIED" | "REJECTED"
    revision: int
    reason: Optional[str]


class SettingsService:
    def __init__(self, initial: OperatingSettings, store: SettingsStore, revision: int = 0) -> None:
        self.current = initial
        self.revision = revision
        self._store = store
        self._seen: "OrderedDict[str, SettingsResult]" = OrderedDict()

    @classmethod
    def start(cls, config_defaults: OperatingSettings, store: SettingsStore) -> "SettingsService":
        """Dùng ngưỡng đã lưu (nếu hợp lệ) thay cho giá trị trong file cấu hình."""
        saved = store.load()
        if saved is None:
            return cls(config_defaults, store, 0)
        revision, settings = saved
        return cls(settings, store, revision)

    def handle(self, command: dict, pipeline, ts: float) -> tuple[list[dict], Optional[SettingsResult]]:
        """Trả về (sự kiện alert phát sinh, kết quả để gửi). Kết quả None nghĩa là bản tin không dùng được
        (không có request_id hợp lệ): bỏ, không có ai để trả lời."""
        request_id = command.get("request_id")
        if not _is_uuid(request_id):
            return [], None
        if request_id in self._seen:
            return [], self._seen[request_id]  # giao lại: gửi lại đúng kết quả cũ, không áp dụng lần hai

        result, events = self._decide(command, pipeline, request_id, ts)
        self._seen[request_id] = result
        while len(self._seen) > REMEMBER_REQUESTS:
            self._seen.popitem(last=False)
        return events, result

    def _decide(self, command: dict, pipeline, request_id: str, ts: float) -> tuple[SettingsResult, list[dict]]:
        expected = command.get("expected_settings_revision")
        if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
            return self._reject(request_id, "expected_settings_revision không hợp lệ"), []
        if expected != self.revision:
            return self._reject(request_id, f"revision cũ: edge đang ở {self.revision}, lệnh dựa trên {expected}"), []

        try:
            proposed = OperatingSettings(
                dwell_seconds=command["dwell_seconds"],
                on_count=command["on_count"],
                on_hold_seconds=command["on_hold_seconds"],
                off_count=command["off_count"],
                off_hold_seconds=command["off_hold_seconds"],
            )
        except KeyError as missing:
            return self._reject(request_id, f"thiếu trường {missing.args[0]}"), []
        problems = proposed.problems()
        if problems:
            return self._reject(request_id, "; ".join(problems)), []
        proposed = OperatingSettings(
            float(proposed.dwell_seconds), int(proposed.on_count), float(proposed.on_hold_seconds),
            int(proposed.off_count), float(proposed.off_hold_seconds),
        )

        if proposed == self.current:
            return SettingsResult(request_id, "APPLIED", self.revision, None), []  # không đổi gì

        events = pipeline.apply_settings(proposed, ts)
        self.current = proposed
        self.revision += 1
        pipeline.settings_revision = self.revision
        self._store.save(self.revision, proposed)
        return SettingsResult(request_id, "APPLIED", self.revision, None), events

    def _reject(self, request_id: str, reason: str) -> SettingsResult:
        return SettingsResult(request_id, "REJECTED", self.revision, reason[:200])


def _is_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
