import pytest
from pydantic import ValidationError

from retailvision.config.loader import load_config

BASE = """
site_id: site01
config_version: v1
source: {type: video, path: ../data/raw/clip.mp4}
model: {weights: ../models/source/yolov8n.pt}
counting:
  line: [[0.45, 0.1], [0.45, 0.9]]
  a_to_b_direction: IN
queue:
  polygon: [[0.6, 0.2], [0.9, 0.2], [0.9, 0.9]]
"""


def write(tmp_path, text, name="site.yaml"):
    p = tmp_path / "configs" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_valid_config_resolves_paths_relative_to_yaml(tmp_path):
    cfg = load_config(write(tmp_path, BASE))
    assert cfg.source.path == (tmp_path / "data" / "raw" / "clip.mp4").resolve()
    assert cfg.model.weights == (tmp_path / "models" / "source" / "yolov8n.pt").resolve()
    assert cfg.alert.on_count == 5  # mặc định


def test_off_count_not_below_on_count_is_rejected(tmp_path):
    bad = BASE + "alert: {on_count: 3, off_count: 3}\n"
    with pytest.raises(ValidationError):
        load_config(write(tmp_path, bad))


def test_video_source_requires_path(tmp_path):
    bad = BASE.replace("path: ../data/raw/clip.mp4", "")
    with pytest.raises(ValidationError):
        load_config(write(tmp_path, bad))


def test_polygon_needs_three_points(tmp_path):
    bad = BASE.replace("[[0.6, 0.2], [0.9, 0.2], [0.9, 0.9]]", "[[0.6, 0.2], [0.9, 0.2]]")
    with pytest.raises(ValidationError):
        load_config(write(tmp_path, bad))


def test_shipped_example_config_is_valid():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    cfg = load_config(repo / "configs" / "examples" / "site01-video.yaml")
    assert cfg.profile == "pilot"
    assert cfg.counting.a_to_b_direction == "IN"
    # đường dẫn phải trỏ đúng tới models/source, không được tạo thư mục mới
    assert cfg.model.weights == (repo / "models" / "source" / "yolov8n.pt").resolve()
    assert cfg.model.tracker == str((repo / "configs" / "edge" / "bytetrack-tuned.yaml").resolve())
