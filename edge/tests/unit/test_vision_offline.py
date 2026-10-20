import os

from retailvision.pipeline import vision


def test_configure_offline_sets_the_flag(monkeypatch):
    monkeypatch.delenv("YOLO_OFFLINE", raising=False)
    vision.configure_offline()
    assert os.environ["YOLO_OFFLINE"] == "true"


def test_configure_offline_respects_an_explicit_choice(monkeypatch):
    monkeypatch.setenv("YOLO_OFFLINE", "false")
    vision.configure_offline()
    assert os.environ["YOLO_OFFLINE"] == "false"  # người vận hành đặt rõ ràng thì giữ nguyên
