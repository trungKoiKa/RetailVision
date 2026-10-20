import type { LiveState } from "../types/api";

const LABELS: Record<LiveState, string> = {
  NORMAL: "Bình thường",
  OVERLOAD: "Quá tải",
  UNKNOWN: "Không có dữ liệu",
};

export function stateLabel(state: LiveState): string {
  return LABELS[state];
}

export function StatusBadge({ state }: { state: LiveState }) {
  return (
    <span className={`badge badge-${state.toLowerCase()}`} data-testid="status-badge">
      {stateLabel(state)}
    </span>
  );
}
