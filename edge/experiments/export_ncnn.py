"""Xuất model YOLO sang NCNN (nhanh hơn .pt trên CPU ARM của Pi) và đặt vào models/exported/.

NCNN cố định kích thước đầu vào: `model.image_size` trong cấu hình edge phải bằng `--imgsz` ở đây.
Có thể chạy trên laptop rồi chép thư mục kết quả sang Pi (cùng định dạng).

    python edge/experiments/export_ncnn.py --weights models/source/yolov8n.pt --imgsz 320
    # -> models/exported/yolov8n_ncnn_320/yolov8n_ncnn_model
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    sys.stderr.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--imgsz", type=int, required=True)
    parser.add_argument("--out-root", type=Path, default=REPO / "models" / "exported")
    args = parser.parse_args()

    from ultralytics import YOLO

    exported = Path(YOLO(str(args.weights)).export(format="ncnn", imgsz=args.imgsz))
    target_dir = args.out_root / f"{args.weights.stem}_ncnn_{args.imgsz}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / exported.name
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(exported), str(target))  # ultralytics ghi cạnh file .pt, chuyển vào models/exported
    print(f"Đã xuất: {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
