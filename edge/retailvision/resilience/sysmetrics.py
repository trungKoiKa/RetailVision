"""Số đo hệ thống của Pi: nhiệt, throttling, RAM. Thiếu nguồn (máy không phải Pi) thì trả None, không bịa số."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

THERMAL_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
PROC_STATUS = Path("/proc/self/status")
PROC_MEMINFO = Path("/proc/meminfo")
DEVICE_MODEL = Path("/proc/device-tree/model")

# bit của `vcgencmd get_throttled`
THROTTLE_BITS = {
    0: "under_voltage_now",
    1: "freq_capped_now",
    2: "throttled_now",
    3: "soft_temp_limit_now",
    16: "under_voltage_occurred",
    17: "freq_capped_occurred",
    18: "throttled_occurred",
    19: "soft_temp_limit_occurred",
}


def cpu_temp_c(path: Path = THERMAL_PATH) -> Optional[float]:
    try:
        return int(path.read_text().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def parse_throttled(output: str) -> Optional[dict]:
    """Đọc dòng `throttled=0x50005` của vcgencmd; None nếu không đúng dạng."""
    try:
        value = int(output.strip().split("=")[1], 16)
    except (IndexError, ValueError):
        return None
    return {"raw": hex(value), **{name: bool(value >> bit & 1) for bit, name in THROTTLE_BITS.items()}}


def throttled_flags() -> Optional[dict]:
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_throttled(out)


def _kib_field(path: Path, key: str) -> Optional[float]:
    try:
        for line in path.read_text().splitlines():
            if line.startswith(key + ":"):
                return int(line.split()[1]) / 1024.0  # kB -> MB
    except (OSError, ValueError, IndexError):
        pass
    return None


def process_rss_mb(status_path: Path = PROC_STATUS) -> Optional[float]:
    """RSS của tiến trình hiện tại (MB). Dùng psutil nếu có, ngược lại đọc /proc."""
    try:
        import psutil

        return psutil.Process().memory_info().rss / 1e6
    except ImportError:
        return _kib_field(status_path, "VmRSS")


def available_memory_mb(meminfo_path: Path = PROC_MEMINFO) -> Optional[float]:
    return _kib_field(meminfo_path, "MemAvailable")


def device_model(path: Path = DEVICE_MODEL) -> Optional[str]:
    try:
        return path.read_bytes().rstrip(b"\0").decode()
    except OSError:
        return None
