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
    python evaluation/tools/label.py --video data/raw/VIRAT_S_000002.mp4 --out evaluation/ground_truth/virat_60s.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2

FIELDS = ["ts", "direction"]


def write_labels(path: Path, labels: list[tuple[float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for ts, direction in sorted(labels):
            writer.writerow([f"{ts:.3f}", direction])


def read_labels(path: Path) -> list[tuple[float, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [(float(r["ts"]), r["direction"]) for r in csv.DictReader(f)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
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
        elif key == ord("i"):
            labels.append((ts, "IN"))
        elif key == ord("o"):
            labels.append((ts, "OUT"))
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
