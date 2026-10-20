"""Đọc và kiểm tra file cấu hình YAML của edge.

Đường dẫn tương đối trong YAML được tính từ thư mục chứa file YAML, không phụ
thuộc thư mục đang đứng khi chạy lệnh.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

Point = tuple[float, float]


class SourceConfig(BaseModel):
    type: Literal["video", "camera"] = "video"
    path: Optional[Path] = None  # type=video: đường dẫn file, đã resolve theo file YAML
    index: int = 0  # type=camera: chỉ số thiết bị
    width: int = 1280
    height: int = 720

    @model_validator(mode="after")
    def _check(self) -> "SourceConfig":
        if self.type == "video" and self.path is None:
            raise ValueError("source.type=video cần source.path")
        return self


class ModelConfig(BaseModel):
    weights: Path
    image_size: int = Field(320, gt=0)
    confidence: float = Field(0.35, ge=0, le=1)
    tracker: str = "bytetrack.yaml"


class CountingConfig(BaseModel):
    line: tuple[Point, Point]  # chuẩn hoá 0–1
    deadband_px: float = Field(12, ge=0)
    min_stable_observations: int = Field(2, ge=1)
    a_to_b_direction: Literal["IN", "OUT"] = "IN"


class QueueConfig(BaseModel):
    polygon: list[Point] = Field(min_length=3)  # chuẩn hoá 0–1
    dwell_seconds: float = Field(2.0, ge=0)


class AlertConfig(BaseModel):
    on_count: int = Field(5, ge=1)
    on_hold_seconds: float = Field(60, ge=0)
    off_count: int = Field(3, ge=0)
    off_hold_seconds: float = Field(10, ge=0)

    @model_validator(mode="after")
    def _check(self) -> "AlertConfig":
        if self.off_count >= self.on_count:
            raise ValueError("alert.off_count phải nhỏ hơn alert.on_count")
        return self


class HealthConfig(BaseModel):
    stale_seconds: float = Field(3.0, gt=0)


class MqttConfig(BaseModel):
    """Địa chỉ broker. Tài khoản/mật khẩu lấy từ biến môi trường RV_MQTT_USER, RV_MQTT_PASS, không ghi vào file này."""

    host: str = "127.0.0.1"
    port: int = Field(1883, gt=0, lt=65536)


class EdgeConfig(BaseModel):
    site_id: str = Field(min_length=1, max_length=64)
    device_id: str = "edge01"
    node_id: str = "node01"
    profile: Literal["pilot", "demo"] = "pilot"
    config_version: str = Field(min_length=1, max_length=64)
    source: SourceConfig
    model: ModelConfig
    counting: CountingConfig
    queue: QueueConfig
    alert: AlertConfig = AlertConfig()
    health: HealthConfig = HealthConfig()
    mqtt: Optional[MqttConfig] = None  # không khai báo: chạy không gửi MQTT


def _resolve(base: Path, value: Optional[Path]) -> Optional[Path]:
    if value is None:
        return None
    return value if value.is_absolute() else (base / value).resolve()


def load_config(path: Path | str) -> EdgeConfig:
    """Đọc YAML, kiểm tra và đổi mọi đường dẫn sang đường dẫn tuyệt đối."""
    yaml_path = Path(path).resolve()
    with yaml_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    config = EdgeConfig.model_validate(raw)
    base = yaml_path.parent
    config.source.path = _resolve(base, config.source.path)
    config.model.weights = _resolve(base, config.model.weights)
    if "/" in config.model.tracker or "\\" in config.model.tracker or config.model.tracker.startswith("."):
        # đường dẫn tới file cấu hình tracker: tương đối theo file YAML.
        # Tên có sẵn như 'bytetrack.yaml' giữ nguyên cho ultralytics.
        tracker_file = (base / config.model.tracker).resolve()
        if not tracker_file.is_file():
            raise ValueError(f"Không thấy file cấu hình tracker: {tracker_file}")
        config.model.tracker = str(tracker_file)
    return config
