"""Chỉ số đánh giá (xem evaluation/README.md, mục "Cách tính"). Hàm thuần, không đọc file.

Không bịa số: mẫu rỗng cho giá trị None, không phải 0. Mọi tỷ lệ kèm cỡ mẫu và khoảng tin cậy Wilson 95%.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge"))

from retailvision.analytics.alert_state import AlertSettings, AlertStateMachine  # noqa: E402

Crossing = tuple[float, str]  # (ts giây, "IN" | "OUT")
Sample = tuple[float, int]  # (ts giây, số người)

PILOT_ALERT = AlertSettings(on_count=5, on_hold_seconds=60.0, off_count=3, off_hold_seconds=10.0)


def wilson(successes: int, total: int, z: float = 1.96) -> Optional[tuple[float, float]]:
    """Khoảng tin cậy Wilson cho tỷ lệ; None khi chưa có mẫu."""
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    """Phân vị theo xếp hạng gần nhất (q trong 0–1); None khi không có mẫu."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))]


def latency_summary(values_ms: Sequence[float]) -> dict:
    """p50/p95/max và cỡ mẫu của một tập độ trễ (ms). Không có mẫu thì các giá trị là None."""
    return {"n": len(values_ms), "p50_ms": percentile(values_ms, 0.5), "p95_ms": percentile(values_ms, 0.95),
            "max_ms": max(values_ms) if values_ms else None}


# --- đếm qua vạch ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CountResult:
    direction: str
    clips: int
    truth: int  # tổng lượt thật (Σ nhãn)
    counted: int  # tổng lượt hệ thống đếm
    abs_error: int  # Σ|đếm − nhãn| theo clip
    error_rate: Optional[float]  # abs_error / truth; None khi không có lượt thật nào
    bias: int  # Σ(đếm − nhãn): dương là đếm thừa
    false_counts_on_empty_clips: int  # lượt đếm ở các clip không có lượt thật nào (báo riêng)


def count_error(truth_by_clip: dict[str, list[Crossing]], counted_by_clip: dict[str, list[Crossing]], direction: str) -> CountResult:
    """Sai số đếm = Σ|đếm − nhãn| theo clip / tổng lượt thật, tính riêng từng hướng. Clip không có lượt thật nào
    (cảnh trống) không vào mẫu số; số lượt đếm nhầm ở đó được báo riêng."""
    truth_total = counted_total = abs_error = bias = false_on_empty = 0
    for clip, gt in truth_by_clip.items():
        n_truth = sum(1 for _, d in gt if d == direction)
        n_counted = sum(1 for _, d in counted_by_clip.get(clip, []) if d == direction)
        truth_total += n_truth
        counted_total += n_counted
        abs_error += abs(n_counted - n_truth)
        bias += n_counted - n_truth
        if n_truth == 0:
            false_on_empty += n_counted
    return CountResult(
        direction=direction,
        clips=len(truth_by_clip),
        truth=truth_total,
        counted=counted_total,
        abs_error=abs_error,
        error_rate=(abs_error / truth_total) if truth_total else None,
        bias=bias,
        false_counts_on_empty_clips=false_on_empty,
    )


@dataclass(frozen=True)
class MatchResult:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> Optional[float]:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else None

    @property
    def recall(self) -> Optional[float]:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else None

    def precision_ci(self) -> Optional[tuple[float, float]]:
        return wilson(self.tp, self.tp + self.fp)

    def recall_ci(self) -> Optional[tuple[float, float]]:
        return wilson(self.tp, self.tp + self.fn)


def match_times(truth: Sequence[float], predicted: Sequence[float], tol: float) -> MatchResult:
    """Ghép mỗi dự đoán với tối đa một nhãn nếu lệch ≤ tol giây (tham lam theo thời gian, mỗi bên dùng một lần)."""
    used: set[int] = set()
    tp = 0
    for t in sorted(truth):
        best = None
        for i, p in enumerate(predicted):
            if i in used or abs(p - t) > tol:
                continue
            if best is None or abs(p - t) < abs(predicted[best] - t):
                best = i
        if best is not None:
            used.add(best)
            tp += 1
    return MatchResult(tp=tp, fp=len(predicted) - tp, fn=len(truth) - tp)


def match_crossings(truth: Sequence[Crossing], predicted: Sequence[Crossing], tol: float, direction: str) -> MatchResult:
    return match_times([t for t, d in truth if d == direction], [t for t, d in predicted if d == direction], tol)


# --- số người vùng chờ ----------------------------------------------------------------------


@dataclass(frozen=True)
class QueueResult:
    samples: int
    unmatched: int  # mốc nhãn mà hệ thống không có số đo gần đó (không tính vào MAE)
    mae: Optional[float]
    bias: Optional[float]
    mae_0_to_8: Optional[float]  # chỉ các mốc nhãn trong 0–8 người (khoảng nghiệm thu NFR-02)
    samples_0_to_8: int


def queue_mae(truth: Sequence[Sample], system: Sequence[Sample], max_gap: float = 1.5) -> QueueResult:
    """So số người hệ thống với nhãn tại các mốc lấy mẫu: lấy số đo hệ thống mới nhất có ts ≤ mốc và cách mốc
    không quá `max_gap` giây. Mốc không có số đo thì không tính (báo `unmatched`), không điền 0."""
    ordered = sorted(system)
    errors: list[int] = []
    bias: list[int] = []
    in_range: list[int] = []
    unmatched = 0
    for t, true_count in sorted(truth):
        candidate = None
        for ts, value in ordered:
            if ts <= t:
                candidate = (ts, value)
            else:
                break
        if candidate is None or t - candidate[0] > max_gap:
            unmatched += 1
            continue
        diff = candidate[1] - true_count
        errors.append(abs(diff))
        bias.append(diff)
        if 0 <= true_count <= 8:
            in_range.append(abs(diff))
    n = len(errors)
    return QueueResult(
        samples=n,
        unmatched=unmatched,
        mae=sum(errors) / n if n else None,
        bias=sum(bias) / n if n else None,
        mae_0_to_8=sum(in_range) / len(in_range) if in_range else None,
        samples_0_to_8=len(in_range),
    )


# --- cảnh báo -------------------------------------------------------------------------------


def alert_opens_from_counts(counts: Sequence[Sample], settings: AlertSettings = PILOT_ALERT) -> list[float]:
    """Chạy đúng máy trạng thái của edge trên chuỗi số người (ts tăng dần) và trả về thời điểm các alert mở.

    Dùng cho nhãn (đường chuẩn) và cho chuỗi số đếm của hệ thống ("phát lại"), nên hai bên cùng ngưỡng và quy tắc."""
    machine = AlertStateMachine(settings)
    opens: list[float] = []
    for ts, count in sorted(counts):
        for transition in machine.on_observation(count, ts):
            if transition.kind == "OPEN":
                opens.append(transition.ts)
    return opens


def alert_match(truth_opens: Sequence[float], predicted_opens: Sequence[float], tol: float = 3.0) -> MatchResult:
    """Precision/recall cảnh báo: dự đoán khớp nhãn nếu thời điểm mở lệch ≤ tol (mặc định 3 giây)."""
    return match_times(truth_opens, predicted_opens, tol)
