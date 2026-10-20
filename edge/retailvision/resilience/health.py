"""Kiểm tra sức khoẻ thiết bị."""

from __future__ import annotations

import subprocess
import sys


def clock_synced() -> bool:
    """Đồng hồ Pi đã đồng bộ NTP/chrony chưa. Ngoài Linux (phát triển trên Windows) coi là đã đồng bộ."""
    if not sys.platform.startswith("linux"):
        return True
    try:
        out = subprocess.run(
            ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
            capture_output=True,
            text=True,
            timeout=3,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False
    return out == "yes"
