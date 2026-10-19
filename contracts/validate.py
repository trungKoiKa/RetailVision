"""Kiểm tra JSON Schema và ví dụ trong contracts/.

Quy ước tên ví dụ: <prefix>__<case>.json, prefix trỏ tới schema trong SCHEMAS.
Ví dụ trong valid/ phải hợp lệ; ví dụ trong invalid/ phải bị từ chối.

Chạy: python contracts/validate.py   (thoát mã 1 nếu có lỗi)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parent
MQTT = ROOT / "mqtt"
EXAMPLES = ROOT / "examples"

SCHEMAS = {
    "state": "events/state.schema.json",
    "crossing": "events/crossing.schema.json",
    "alert": "events/alert.schema.json",
    "telemetry": "events/telemetry.schema.json",
    "status": "events/status.schema.json",
    "operator-ack": "events/operator-ack.schema.json",
    "settings-set": "commands/settings-set.schema.json",
    "settings-result": "commands/settings-result.schema.json",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_registry() -> Registry:
    registry = Registry()
    for path in MQTT.rglob("*.schema.json"):
        schema = load_json(path)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema, default_specification=DRAFT202012))
    return registry


def main() -> int:
    registry = build_registry()
    failures: list[str] = []
    checked = 0

    validators: dict[str, Draft202012Validator] = {}
    for name, rel in SCHEMAS.items():
        schema = load_json(MQTT / rel)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            failures.append(f"schema {rel}: {exc.message}")
            continue
        validators[name] = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())

    for folder, expect_valid in (("valid", True), ("invalid", False)):
        for path in sorted((EXAMPLES / folder).glob("*.json")):
            prefix = path.name.split("__", 1)[0]
            checked += 1
            if prefix not in validators:
                failures.append(f"{folder}/{path.name}: không rõ schema cho prefix '{prefix}'")
                continue
            try:
                payload = load_json(path)
            except json.JSONDecodeError as exc:
                failures.append(f"{folder}/{path.name}: JSON lỗi ({exc})")
                continue
            errors = sorted(validators[prefix].iter_errors(payload), key=lambda e: list(e.path))
            is_valid = not errors
            if is_valid != expect_valid:
                if expect_valid:
                    detail = "; ".join(e.message for e in errors[:3])
                    failures.append(f"{folder}/{path.name}: phải hợp lệ nhưng bị từ chối: {detail}")
                else:
                    failures.append(f"{folder}/{path.name}: phải bị từ chối nhưng được chấp nhận")

    print(f"Đã kiểm {checked} ví dụ, {len(SCHEMAS)} schema.")
    for line in failures:
        print("LỖI:", line)
    if failures:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252
    sys.exit(main())
