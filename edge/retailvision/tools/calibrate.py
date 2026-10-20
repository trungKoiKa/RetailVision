"""Vẽ vạch đếm và vùng chờ lên một khung hình (ảnh, video hoặc camera) rồi in đoạn YAML chuẩn hoá để dán vào cấu hình.

    python -m retailvision.tools.calibrate --image data/raw/khung.jpg
    python -m retailvision.tools.calibrate --video data/raw/clip.mp4 --config configs/site.yaml   # bắt đầu từ cấu hình hiện có

Chuột trái thêm điểm; phím: L = vẽ vạch (2 điểm), P = vẽ vùng chờ (≥3 điểm, Enter để đóng), D = đổi chiều vào/ra,
U = hoàn tác điểm cuối, C = xoá hình đang vẽ, S = in YAML (và ghi vào --out nếu có), Q = thoát.
Mũi tên trên ảnh chỉ chiều bước qua vạch được tính là hướng đã chọn (a_to_b_direction): người đi theo mũi tên là "vào".
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

Point = tuple[float, float]


@dataclass
class Calibration:
    """Trạng thái hiệu chuẩn theo toạ độ pixel; xuất ra toạ độ chuẩn hoá 0–1 như file cấu hình."""

    width: int
    height: int
    line: list[Point] = field(default_factory=list)
    polygon: list[Point] = field(default_factory=list)
    direction: str = "IN"  # nhãn của chiều bước từ phía -1 sang phía +1 của vạch (A→B)
    mode: str = "line"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("kích thước khung hình phải dương")

    def add_point(self, x: float, y: float) -> None:
        x = min(max(float(x), 0.0), self.width - 1.0)  # kẹp trong khung hình
        y = min(max(float(y), 0.0), self.height - 1.0)
        if self.mode == "line":
            if len(self.line) >= 2:
                self.line = []  # chấm điểm đầu của vạch mới
            self.line.append((x, y))
        else:
            self.polygon.append((x, y))

    def undo(self) -> None:
        target = self.line if self.mode == "line" else self.polygon
        if target:
            target.pop()

    def clear(self) -> None:
        (self.line if self.mode == "line" else self.polygon).clear()

    def flip_direction(self) -> None:
        self.direction = "OUT" if self.direction == "IN" else "IN"

    def problems(self) -> list[str]:
        found: list[str] = []
        if len(self.line) != 2:
            found.append("Vạch cần đúng 2 điểm.")
        elif self.line[0] == self.line[1]:
            found.append("Hai đầu vạch không được trùng nhau.")
        if len(self.polygon) < 3:
            found.append("Vùng chờ cần ít nhất 3 đỉnh.")
        return found

    def normalized(self, points: list[Point]) -> list[list[float]]:
        return [[round(x / self.width, 4), round(y / self.height, 4)] for x, y in points]

    def to_yaml(self) -> str:
        """Đoạn YAML dán vào file cấu hình (mục counting.line, counting.a_to_b_direction và queue.polygon)."""
        errors = self.problems()
        if errors:
            raise ValueError(" ".join(errors))
        line = ", ".join(f"[{x}, {y}]" for x, y in self.normalized(self.line))
        poly = ", ".join(f"[{x}, {y}]" for x, y in self.normalized(self.polygon))
        return (
            "counting:\n"
            f"  line: [{line}]\n"
            f"  a_to_b_direction: {self.direction}\n"
            "queue:\n"
            f"  polygon: [{poly}]\n"
        )

    def direction_arrow(self, length: float = 80.0) -> Optional[tuple[Point, Point]]:
        """Mũi tên (từ, tới) theo pixel chỉ chiều bước từ phía âm sang phía dương của vạch (A→B), tức chiều mang nhãn
        `direction`. Pháp tuyến dương của signed_distance là (-dy, dx)."""
        if len(self.line) != 2 or self.line[0] == self.line[1]:
            return None
        (ax, ay), (bx, by) = self.line
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        nx, ny = -dy / norm, dx / norm
        mx, my = (ax + bx) / 2, (ay + by) / 2
        return (mx - nx * length / 2, my - ny * length / 2), (mx + nx * length / 2, my + ny * length / 2)


def from_config(path: Path, width: int, height: int) -> Calibration:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from retailvision.config.loader import load_config

    cfg = load_config(path)
    cal = Calibration(width, height)
    cal.line = [(x * width, y * height) for x, y in cfg.counting.line]
    cal.polygon = [(x * width, y * height) for x, y in cfg.queue.polygon]
    cal.direction = cfg.counting.a_to_b_direction
    return cal


def main(argv: Optional[list[str]] = None) -> int:
    import cv2
    import numpy as np

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path)
    source.add_argument("--video", type=Path)
    source.add_argument("--camera", type=int)
    parser.add_argument("--frame", type=int, default=0, help="chỉ số khung hình lấy từ video")
    parser.add_argument("--config", type=Path, help="bắt đầu từ vạch/vùng trong cấu hình này")
    parser.add_argument("--out", type=Path, help="ghi đoạn YAML ra file khi nhấn S")
    args = parser.parse_args(argv)

    if args.image:
        frame = cv2.imread(str(args.image))
    else:
        cap = cv2.VideoCapture(str(args.video) if args.video else args.camera)
        if args.video:
            cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
        ok, frame = cap.read()
        cap.release()
        frame = frame if ok else None
    if frame is None:
        print("Không đọc được khung hình.", file=sys.stderr)
        return 2
    height, width = frame.shape[:2]
    cal = from_config(args.config, width, height) if args.config else Calibration(width, height)

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            cal.add_point(x, y)

    window = "calibrate"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)
    while True:
        view = frame.copy()
        if len(cal.line) >= 1:
            pts = [tuple(int(v) for v in p) for p in cal.line]
            for p in pts:
                cv2.circle(view, p, 8, (0, 255, 255), -1)
            if len(pts) == 2:
                cv2.line(view, pts[0], pts[1], (0, 255, 255), 3)
        if cal.polygon:
            cv2.polylines(view, [np.array([[int(x), int(y)] for x, y in cal.polygon], dtype=np.int32)], len(cal.polygon) >= 3, (255, 160, 0), 3)
        arrow = cal.direction_arrow()
        if arrow:
            a, b = arrow
            cv2.arrowedLine(view, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (0, 200, 0), 4, tipLength=0.3)
            cv2.putText(view, f"theo mui ten = {cal.direction}", (int(b[0]) + 10, int(b[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 0), 2)
        cv2.putText(view, f"che do: {'VACH' if cal.mode == 'line' else 'VUNG CHO'}  (L/P doi, D doi chieu, S in YAML, Q thoat)",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.imshow(window, view)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("l"):
            cal.mode = "line"
        elif key == ord("p"):
            cal.mode = "polygon"
        elif key == ord("d"):
            cal.flip_direction()
        elif key == ord("u"):
            cal.undo()
        elif key == ord("c"):
            cal.clear()
        elif key == ord("s"):
            try:
                text = cal.to_yaml()
            except ValueError as e:
                print(f"Chưa hợp lệ: {e}", file=sys.stderr)
                continue
            print(text)
            if args.out:
                args.out.write_text(text, encoding="utf-8")
                print(f"Đã ghi {args.out}", file=sys.stderr)
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
