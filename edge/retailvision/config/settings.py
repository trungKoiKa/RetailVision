"""Ngưỡng vận hành sửa được từ web (P1) và nơi lưu chúng.

`settings` (ngưỡng, có revision) khác `config_version` (profile kỹ thuật của edge). Chỉ dwell, số người và thời
gian giữ sửa được từ web; vạch, vùng chờ và model sửa bằng file cấu hình.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from retailvision.config.loader import EdgeConfig

# Khoảng giá trị khớp contracts/mqtt/commands/settings-set.schema.json
LIMITS = {
    "dwell_seconds": (0.0, 60.0),
    "on_count": (1, 100),
    "on_hold_seconds": (0.0, 3600.0),
    "off_count": (0, 100),
    "off_hold_seconds": (0.0, 3600.0),
}


@dataclass(frozen=True)
class OperatingSettings:
    dwell_seconds: float
    on_count: int
    on_hold_seconds: float
    off_count: int
    off_hold_seconds: float

    @classmethod
    def from_config(cls, config: EdgeConfig) -> "OperatingSettings":
        a = config.alert
        return cls(config.queue.dwell_seconds, a.on_count, a.on_hold_seconds, a.off_count, a.off_hold_seconds)

    def problems(self) -> list[str]:
        """Danh sách lý do không hợp lệ (rỗng nếu hợp lệ)."""
        found: list[str] = []
        for name, (low, high) in LIMITS.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
                found.append(f"{name} phải là số")
            elif name in ("on_count", "off_count") and int(value) != value:
                found.append(f"{name} phải là số nguyên")
            elif not (low <= value <= high):
                found.append(f"{name} ngoài khoảng {low}–{high}")
        if not found and self.off_count >= self.on_count:
            found.append("off_count phải nhỏ hơn on_count")
        return found


class SettingsStore:
    """Lưu ngưỡng đã áp dụng và revision xuống file để sống sót qua restart (ghi nguyên tử)."""

    def __init__(self, path: Optional[Path]) -> None:
        self._path = path

    def load(self) -> Optional[tuple[int, OperatingSettings]]:
        if self._path is None or not self._path.is_file():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            revision = int(raw["revision"])
            settings = OperatingSettings(
                dwell_seconds=float(raw["dwell_seconds"]),
                on_count=int(raw["on_count"]),
                on_hold_seconds=float(raw["on_hold_seconds"]),
                off_count=int(raw["off_count"]),
                off_hold_seconds=float(raw["off_hold_seconds"]),
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None  # file hỏng: dùng cấu hình gốc thay vì từ chối khởi động
        if revision < 0 or settings.problems():
            return None
        return revision, settings

    def save(self, revision: int, settings: OperatingSettings) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"revision": revision, **asdict(settings)}, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)
