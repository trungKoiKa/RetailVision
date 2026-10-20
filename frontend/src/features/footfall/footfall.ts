import type { FootfallBucket, Granularity } from "../../shared/types/api";
import { DISPLAY_ZONE } from "../../shared/utils/format";

export const MAX_RANGE_DAYS: Record<Granularity, number> = { hour: 7, day: 366 };

const dateParts = new Intl.DateTimeFormat("en-CA", { timeZone: DISPLAY_ZONE, year: "numeric", month: "2-digit", day: "2-digit" });
const hourLabel = new Intl.DateTimeFormat("vi-VN", { timeZone: DISPLAY_ZONE, hour: "2-digit", minute: "2-digit", hour12: false });
const dayLabel = new Intl.DateTimeFormat("vi-VN", { timeZone: DISPLAY_ZONE, day: "2-digit", month: "2-digit" });

/** Ngày hôm nay theo giờ Việt Nam, dạng yyyy-MM-dd. */
export function todayVn(now: Date = new Date()): string {
  return dateParts.format(now); // en-CA cho yyyy-MM-dd
}

/** Số ngày gồm cả hai đầu giữa hai chuỗi yyyy-MM-dd; null nếu sai dạng. */
export function daysInclusive(from: string, to: string): number | null {
  const ok = /^\d{4}-\d{2}-\d{2}$/;
  if (!ok.test(from) || !ok.test(to)) return null;
  const a = Date.parse(`${from}T00:00:00Z`);
  const b = Date.parse(`${to}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.round((b - a) / 86_400_000) + 1;
}

/** Lý do khoảng chọn không hợp lệ; null nếu hợp lệ. Backend vẫn kiểm lại. */
export function rangeProblem(from: string, to: string, granularity: Granularity): string | null {
  const days = daysInclusive(from, to);
  if (days === null) return "Chọn ngày bắt đầu và kết thúc.";
  if (days < 1) return "Ngày bắt đầu không được sau ngày kết thúc.";
  if (days > MAX_RANGE_DAYS[granularity]) {
    return `Tối đa ${MAX_RANGE_DAYS[granularity]} ngày khi xem theo ${granularity === "hour" ? "giờ" : "ngày"}.`;
  }
  return null;
}

export function bucketLabel(b: FootfallBucket, granularity: Granularity): string {
  const start = new Date(b.start);
  return granularity === "hour" ? hourLabel.format(start) : dayLabel.format(start);
}

export function rangeLabel(b: FootfallBucket, granularity: Granularity): string {
  const fmt = granularity === "hour" ? hourLabel : dayLabel;
  return `${fmt.format(new Date(b.start))}${granularity === "hour" ? `–${hourLabel.format(new Date(b.end))}` : ""}`;
}

export type BucketKind = "future" | "gap" | "low" | "ok";

/** future: chưa tới; gap: không có telemetry; low: độ phủ dưới 90%; ok: đủ dữ liệu. */
export function bucketKind(b: FootfallBucket): BucketKind {
  if (b.future) return "future";
  if (b.gap) return "gap";
  if (b.coverage !== null && b.coverage < 0.9) return "low";
  return "ok";
}

export interface ChartRow {
  label: string;
  in?: number;
  out?: number;
  kind: BucketKind;
}

/** Số liệu null không thành cột 0: bucket thiếu dữ liệu không có cột (khung xám được vẽ riêng). */
export function toChartRows(buckets: FootfallBucket[], granularity: Granularity): ChartRow[] {
  return buckets.map((b) => ({
    label: bucketLabel(b, granularity),
    in: b.in ?? undefined,
    out: b.out ?? undefined,
    kind: bucketKind(b),
  }));
}

export function formatCoverage(coverage: number | null): string {
  return coverage === null ? "—" : `${Math.round(coverage * 100)}%`;
}
