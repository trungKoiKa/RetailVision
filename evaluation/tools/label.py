"""Gán nhãn tay các lượt qua vạch trên một video.

Phím:
  space  tạm dừng / tiếp tục
  a / d  lùi / tiến 1 giây
  z / c  lùi / tiến 1 khung hình
  i      đánh dấu lượt VÀO (IN) tại thời điểm hiện tại
  o      đánh dấu lượt RA (OUT) tại thời điểm hiện tại
  u      xoá nhãn vừa đánh dấu cuối cùng
  q      lưu và thoát

Kết quả: file CSV với hai cột ts (giây) và direction (IN/OUT).
Ví dụ:
    python evaluation/tools/label.py --video data/raw/clip2.mp4 --out evaluation/ground_truth/my_labels.csv         --config configs/examples/site01-video.yaml

--config: vẽ vạch vàng (đường đếm) và vùng chờ lên video để biết chính xác lúc người chạm vạch.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

FIELDS = ["ts", "direction"]
DUPLICATE_WINDOW_S = 0.05  # không cho hai nhãn cùng chiều trong khoảng này


def write_labels(path: Path, labels: list[tuple[float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for ts, direction in sorted(labels):
            writer.writerow([f"{ts:.3f}", direction])


def load_geometry(config_path: Path, width: int, height: int):
    """Đọc vạch và vùng chờ (toạ độ 0–1) trong file cấu hình, đổi ra pixel của khung hình."""
    with config_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    line = [(x * width, y * height) for x, y in cfg["counting"]["line"]]
    polygon = [(x * width, y * height) for x, y in cfg["queue"]["polygon"]]
    return line, polygon


def draw_geometry(img, line, polygon) -> None:
    a, b = (tuple(int(v) for v in p) for p in line)
    cv2.line(img, a, b, (0, 255, 255), 3)  # vạch vàng
    cv2.polylines(img, [np.array(polygon, dtype=np.int32).reshape(-1, 1, 2)], True, (255, 128, 0), 2)


def can_add(labels: list[tuple[float, str]], ts: float, direction: str) -> bool:
    return not any(d == direction and abs(t - ts) < DUPLICATE_WINDOW_S for t, d in labels)


def read_labels(path: Path) -> list[tuple[float, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [(float(r["ts"]), r["direction"]) for r in csv.DictReader(f)]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, help="file cấu hình để vẽ vạch và vùng chờ")
    args = parser.parse_args()

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    line, polygon = load_geometry(args.config, width, height) if args.config else (None, None)
    labels = read_labels(args.out)
    playing = True
    frame_idx = 0
    last_frame = None
    window = "gan nhan"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    def seek(idx: int) -> None:
        nonlocal frame_idx, last_frame
        frame_idx = max(0, min(idx, total - 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if ok:
            last_frame = frame
        frame_idx += 1

    seek(0)
    while True:
        ts = (frame_idx - 1) / fps
        if last_frame is not None:
            img = last_frame.copy()
            if line is not None:
                draw_geometry(img, line, polygon)
            count_in = sum(1 for _, d in labels if d == "IN")
            count_out = sum(1 for _, d in labels if d == "OUT")
            text = f"t={ts:6.2f}s  IN={count_in} OUT={count_out}  {'PLAY' if playing else 'PAUSE'}"
            cv2.putText(img, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(window, img)
        key = cv2.waitKey(1 if playing else 30) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            playing = not playing
        elif key == ord("d"):
            seek(frame_idx - 1 + int(fps))
        elif key == ord("a"):
            seek(frame_idx - 1 - int(fps))
        elif key == ord("c"):
            seek(frame_idx)
        elif key == ord("z"):
            seek(frame_idx - 2)
        elif key in (ord("i"), ord("o")):
            direction = "IN" if key == ord("i") else "OUT"
            if can_add(labels, ts, direction):
                labels.append((ts, direction))
            else:
                print(f"Bỏ qua: đã có nhãn {direction} gần t={ts:.2f}s")
        elif key == ord("u") and labels:
            labels.pop()
        if playing:
            ok, frame = cap.read()
            if not ok:
                playing = False
            else:
                last_frame = frame
                frame_idx += 1

    cap.release()
    cv2.destroyAllWindows()
    write_labels(args.out, labels)
    print(f"Đã lưu {len(labels)} nhãn vào {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
