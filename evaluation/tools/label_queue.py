"""Gán nhãn số người trong vùng chờ theo các mốc cố định (mặc định mỗi 5 giây) cho một clip.

Quy tắc đếm (phải giống hệ thống): chỉ đếm người có điểm chân trong đa giác vùng chờ và đã ở đó đủ `dwell`
(mặc định 2 giây). Người đi ngang chưa đủ dwell thì KHÔNG đếm. Clip để đánh giá cảnh báo nên dùng bước ngắn
hơn (2 giây) để thời điểm mở cảnh báo suy ra từ nhãn đủ chính xác cho cửa sổ ghép ±3 giây.

    python evaluation/tools/label_queue.py --video data/raw/clip.mp4 --config configs/site.yaml \\
        --out evaluation/ground_truth/clip_queue.csv --step 5

Phím: số 0–9 nhập số người, Enter xác nhận và sang mốc kế, Backspace xóa số, b = mốc trước, s = bỏ qua mốc,
q = lưu và thoát. Chạy lại với cùng --out để tiếp tục từ nhãn đã lưu.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional


class QueueLabeler:
    """Trạng thái gán nhãn, tách khỏi giao diện để kiểm bằng test."""

    MAX_COUNT = 99

    def __init__(self, duration_s: float, step_s: float = 5.0) -> None:
        if duration_s <= 0 or step_s <= 0:
            raise ValueError("duration_s và step_s phải dương")
        self.marks = [round(i * step_s, 3) for i in range(int(duration_s // step_s) + 1)]
        self.values: dict[float, int] = {}
        self.index = 0
        self.buffer = ""

    @property
    def mark(self) -> float:
        return self.marks[self.index]

    @property
    def finished(self) -> bool:
        return self.index >= len(self.marks)

    def type_digit(self, digit: str) -> None:
        if not digit.isdigit() or len(digit) != 1 or self.finished:
            return
        candidate = self.buffer + digit
        if int(candidate) <= self.MAX_COUNT:
            self.buffer = candidate.lstrip("0") or "0"

    def backspace(self) -> None:
        self.buffer = self.buffer[:-1]

    def confirm(self) -> bool:
        """Ghi số đang gõ cho mốc hiện tại và sang mốc kế. Chưa gõ gì thì không làm gì (tránh ghi 0 nhầm)."""
        if self.finished or self.buffer == "":
            return False
        self.values[self.mark] = int(self.buffer)
        self.buffer = ""
        self.index += 1
        return True

    def skip(self) -> None:
        if not self.finished:
            self.buffer = ""
            self.index += 1

    def back(self) -> None:
        self.buffer = ""
        if self.index > 0:
            self.index -= 1
            self.buffer = str(self.values.get(self.marks[self.index], ""))

    def rows(self) -> list[tuple[float, int]]:
        return sorted(self.values.items())

    def to_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts", "count"])
            for ts, count in self.rows():
                w.writerow([ts, count])

    @classmethod
    def resume(cls, path: Path, duration_s: float, step_s: float) -> "QueueLabeler":
        labeler = cls(duration_s, step_s)
        if path.is_file():
            with path.open(encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    ts = round(float(r["ts"]), 3)
                    if ts in labeler.marks:
                        labeler.values[ts] = int(r["count"])
            while not labeler.finished and labeler.mark in labeler.values:
                labeler.index += 1
        return labeler


def main(argv: Optional[list[str]] = None) -> int:
    import cv2
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "edge"))
    from retailvision.analytics.geometry import to_pixels
    from retailvision.config.loader import load_config

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, help="cấu hình edge để vẽ vùng chờ lên khung hình")
    parser.add_argument("--step", type=float, default=5.0, help="giây giữa hai mốc")
    args = parser.parse_args(argv)

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print(f"Không mở được video: {args.video}", file=sys.stderr)
        return 2
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    polygon = None
    if args.config:
        polygon = np.array(to_pixels(load_config(args.config).queue.polygon, width, height), dtype=np.int32)

    labeler = QueueLabeler.resume(args.out, duration, args.step)
    window = "label_queue"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    while not labeler.finished:
        cap.set(cv2.CAP_PROP_POS_MSEC, labeler.mark * 1000)
        ok, frame = cap.read()
        if not ok:
            labeler.skip()
            continue
        if polygon is not None:
            cv2.polylines(frame, [polygon], True, (255, 160, 0), 3)
        previous = labeler.values.get(labeler.mark)
        text = f"t={labeler.mark:.0f}s  nhap: {labeler.buffer or '_'}" + (f"  (da luu: {previous})" if previous is not None else "")
        cv2.putText(frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        cv2.imshow(window, frame)
        key = cv2.waitKey(0) & 0xFF
        if key == ord("q"):
            break
        if ord("0") <= key <= ord("9"):
            labeler.type_digit(chr(key))
        elif key in (13, 10):
            labeler.confirm()
        elif key in (8, 127):
            labeler.backspace()
        elif key == ord("b"):
            labeler.back()
        elif key == ord("s"):
            labeler.skip()
    cap.release()
    cv2.destroyAllWindows()
    labeler.to_csv(args.out)
    print(f"Đã lưu {len(labeler.rows())}/{len(labeler.marks)} mốc vào {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
