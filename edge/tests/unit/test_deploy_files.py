"""Kiểm cú pháp và nội dung các file triển khai Pi. Không thay cho việc chạy thật trên Pi."""

import configparser
import shutil
import subprocess
from pathlib import Path

import pytest

from retailvision.config.loader import load_config

REPO = Path(__file__).resolve().parents[3]
PI = REPO / "deploy" / "pi"


def read_unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # systemd phân biệt hoa thường
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def test_edge_service_unit_has_the_needed_directives():
    unit = read_unit(PI / "systemd" / "retail-edge.service")
    assert set(unit.sections()) == {"Unit", "Service", "Install"}
    svc = unit["Service"]
    assert "retailvision.app" in svc["ExecStart"] and "--config" in svc["ExecStart"]
    assert svc["Restart"] == "on-failure"
    assert svc["User"] == "rv" and "video" in svc["SupplementaryGroups"]
    assert svc["EnvironmentFile"].startswith("/etc/retailvision/")  # mật khẩu ngoài repo
    after = unit["Unit"]["After"]
    assert "mosquitto.service" in after and "network-online.target" in after
    assert unit["Install"]["WantedBy"] == "multi-user.target"


def test_service_unit_contains_no_secrets():
    text = (PI / "systemd" / "retail-edge.service").read_text(encoding="utf-8").lower()
    assert "password" not in text and "rv_mqtt_pass" not in text


def test_edge_env_example_is_placeholder_only():
    lines = [l for l in (PI / "edge.env.example").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    keys = dict(l.split("=", 1) for l in lines)
    assert keys["RV_MQTT_USER"] == "edge01"
    assert keys["RV_MQTT_PASS"].startswith("change-me")


def test_chrony_conf_syncs_from_lan_server_first_and_allows_initial_step():
    lines = [l.split() for l in (PI / "chrony" / "retailvision.conf").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    servers = [l for l in lines if l[0] == "server"]
    assert servers and "prefer" in servers[0] and "iburst" in servers[0]
    assert any(l[0] == "makestep" for l in lines)


@pytest.mark.parametrize("name", ["install_edge.sh", "check_clock.sh"])
def test_shell_scripts_are_valid_bash_with_lf_endings(name):
    path = PI / "scripts" / name
    assert b"\r\n" not in path.read_bytes(), "script Linux phải dùng LF"
    assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("không có bash")
    result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_install_script_refuses_non_root_and_never_overwrites_existing_config():
    text = (PI / "scripts" / "install_edge.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "EUID" in text
    assert "[[ -f $CONF/edge.yaml ]] ||" in text and "[[ ! -f $CONF/edge.env ]]" in text


def test_camera_example_config_is_valid_and_wires_mqtt():
    config = load_config(REPO / "configs" / "examples" / "site01-camera.yaml")
    assert config.source.type == "camera"
    assert config.mqtt is not None and config.mqtt.port == 1883
    assert config.model.image_size == 320
    assert "ncnn" in str(config.model.weights).lower()  # trọng số NCNN, kích thước khớp tên thư mục xuất
    assert "_320" in str(config.model.weights)


def test_example_configs_do_not_embed_credentials():
    for cfg in (REPO / "configs" / "examples").glob("*.yaml"):
        text = cfg.read_text(encoding="utf-8").lower()
        assert "password" not in text and "pass:" not in text, cfg.name
