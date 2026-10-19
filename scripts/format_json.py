"""Định dạng lại mọi file .json trong repo.

Quy ước: thụt lề 2 dấu cách, giữ nguyên tiếng Việt (UTF-8), xuống dòng LF
cuối file, giữ thứ tự khóa như trong file gốc.

    python scripts/format_json.py          # ghi lại các file chưa đúng định dạng
    python scripts/format_json.py --check  # chỉ liệt kê file sai, thoát mã 1 nếu có
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "node_modules", ".claude", "target", "dist", "__pycache__"}


def json_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.json"):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            files.append(path)
    return sorted(files)


def format_text(text: str) -> str:
    return json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chỉ kiểm tra, không ghi file")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    changed: list[Path] = []
    errors: list[str] = []
    files = json_files()
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            formatted = format_text(text)
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: JSON lỗi ({exc})")
            continue
        if formatted != text:
            changed.append(path)
            if not args.check:
                with path.open("w", encoding="utf-8", newline="\n") as f:
                    f.write(formatted)

    verb = "cần định dạng lại" if args.check else "đã định dạng lại"
    for path in changed:
        print(f"{verb}: {path.relative_to(ROOT).as_posix()}")
    for line in errors:
        print("LỖI:", line)
    print(f"Tổng {len(files)} file, {len(changed)} file {verb}, {len(errors)} lỗi cú pháp.")

    if errors or (args.check and changed):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
