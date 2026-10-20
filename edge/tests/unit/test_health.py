"""T26: reboot Pi không Internet. Đồng hồ chưa đồng bộ thì phải báo clock_synced=false, không tự nhận là đúng."""

import subprocess
import sys
from datetime import datetime, timezone

from retailvision.messaging.bridge import EdgeMessenger
from retailvision.messaging.mqtt_client import ListLink
from retailvision.messaging.payloads import EnvelopeFactory
from retailvision.messaging.topics import Topics
from retailvision.resilience import health
from schema_helper import errors


class Completed:
    def __init__(self, stdout):
        self.stdout = stdout


def patch_linux(monkeypatch, stdout=None, error=None):
    monkeypatch.setattr(health.sys, "platform", "linux")

    def fake_run(*args, **kwargs):
        if error is not None:
            raise error
        return Completed(stdout)

    monkeypatch.setattr(health.subprocess, "run", fake_run)


def test_synced_when_timedatectl_says_yes(monkeypatch):
    patch_linux(monkeypatch, "yes\n")
    assert health.clock_synced() is True


def test_not_synced_when_timedatectl_says_no(monkeypatch):
    patch_linux(monkeypatch, "no\n")
    assert health.clock_synced() is False


def test_unknown_output_or_missing_tool_is_treated_as_not_synced(monkeypatch):
    patch_linux(monkeypatch, "")
    assert health.clock_synced() is False
    patch_linux(monkeypatch, error=FileNotFoundError("timedatectl"))
    assert health.clock_synced() is False
    patch_linux(monkeypatch, error=subprocess.TimeoutExpired("timedatectl", 3))
    assert health.clock_synced() is False


def test_non_linux_development_machine_counts_as_synced(monkeypatch):
    monkeypatch.setattr(health.sys, "platform", "win32")
    assert health.clock_synced() is True


def test_status_reports_clock_not_synced_and_is_schema_valid():
    link = ListLink()
    messenger = EdgeMessenger(
        link, EnvelopeFactory("site01", "edge01", "v1"), Topics("site01"), profile="pilot", version="0.1.0",
        clock_synced=lambda: False,
        now=lambda: datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
    )
    online = messenger.hello()[0].payload
    will = messenger.will().payload
    assert online["clock_synced"] is False and will["clock_synced"] is False
    assert errors("status", online) == [] and errors("status", will) == []
