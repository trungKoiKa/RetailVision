/** Hiển thị thời gian theo giờ Việt Nam; dữ liệu lưu và truyền luôn là UTC. */

export const DISPLAY_ZONE = "Asia/Ho_Chi_Minh";

const dateTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: DISPLAY_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

const timeOnly = new Intl.DateTimeFormat("vi-VN", {
  timeZone: DISPLAY_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "—";
}

export function formatTime(iso: string | null | undefined): string {
  return iso ? timeOnly.format(new Date(iso)) : "—";
}

/** "0,8 giây", "12 giây", "3 phút 05 giây". Không có giá trị thì "—". */
export function formatAge(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "—";
  if (seconds < 10) return `${seconds.toFixed(1).replace(".", ",")} giây`;
  if (seconds < 60) return `${Math.round(seconds)} giây`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes} phút ${String(rest).padStart(2, "0")} giây`;
}

/** Số người: null (không biết) hiển thị "—", không bao giờ thành 0. */
export function formatCount(count: number | null | undefined): string {
  return count === null || count === undefined ? "—" : String(count);
}
