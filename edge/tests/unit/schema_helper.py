"""Kiểm tra bản tin so với JSON Schema thật trong contracts/ (nguồn sự thật)."""

from __future__ import annotations

import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
sys.path.insert(0, str(CONTRACTS))
import validate as contract_validate  # noqa: E402  (contracts/validate.py)

_REGISTRY = contract_validate.build_registry()
_VALIDATORS: dict[str, Draft202012Validator] = {}


def errors(kind: str, payload: dict) -> list[str]:
    """Danh sách lỗi của `payload` so với schema `kind` (khoá trong contract_validate.SCHEMAS)."""
    if kind not in _VALIDATORS:
        schema = contract_validate.load_json(contract_validate.MQTT / contract_validate.SCHEMAS[kind])
        _VALIDATORS[kind] = Draft202012Validator(schema, registry=_REGISTRY, format_checker=FormatChecker())
    return [e.message for e in _VALIDATORS[kind].iter_errors(payload)]
