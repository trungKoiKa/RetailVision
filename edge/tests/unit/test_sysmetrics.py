from retailvision.resilience import sysmetrics


def test_cpu_temp_reads_millidegrees(tmp_path):
    f = tmp_path / "temp"
    f.write_text("54321\n")
    assert sysmetrics.cpu_temp_c(f) == 54.321


def test_missing_sources_return_none_not_zero(tmp_path):
    assert sysmetrics.cpu_temp_c(tmp_path / "nope") is None
    assert sysmetrics.available_memory_mb(tmp_path / "nope") is None
    assert sysmetrics.device_model(tmp_path / "nope") is None
    bad = tmp_path / "bad"
    bad.write_text("abc")
    assert sysmetrics.cpu_temp_c(bad) is None


def test_parse_throttled_flags():
    flags = sysmetrics.parse_throttled("throttled=0x50005\n")
    assert flags["raw"] == "0x50005"
    assert flags["under_voltage_now"] and flags["throttled_now"]
    assert flags["under_voltage_occurred"] and flags["throttled_occurred"]
    assert not flags["freq_capped_now"] and not flags["soft_temp_limit_now"]
    clean = sysmetrics.parse_throttled("throttled=0x0")
    assert not any(v for k, v in clean.items() if k != "raw")


def test_parse_throttled_rejects_garbage():
    assert sysmetrics.parse_throttled("") is None
    assert sysmetrics.parse_throttled("command not found") is None
    assert sysmetrics.parse_throttled("throttled=zz") is None


def test_meminfo_converts_kb_to_mb(tmp_path):
    f = tmp_path / "meminfo"
    f.write_text("MemTotal:  3900000 kB\nMemAvailable:    2048000 kB\n")
    assert sysmetrics.available_memory_mb(f) == 2000.0


def test_device_model_strips_nul(tmp_path):
    f = tmp_path / "model"
    f.write_bytes(b"Raspberry Pi 4 Model B Rev 1.5\0")
    assert sysmetrics.device_model(f) == "Raspberry Pi 4 Model B Rev 1.5"
