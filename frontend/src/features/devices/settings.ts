import type { SettingsValues } from "../../shared/types/api";

/** Khoảng giá trị khớp contracts/mqtt/commands/settings-set.schema.json (backend và edge kiểm lại). */
export const LIMITS = {
  dwell_seconds: { min: 0, max: 60, label: "Thời gian đứng tối thiểu trong vùng chờ (giây)" },
  on_count: { min: 1, max: 100, label: "Số người để bật cảnh báo" },
  on_hold_seconds: { min: 0, max: 3600, label: "Giữ mức đông trước khi cảnh báo (giây)" },
  off_count: { min: 0, max: 100, label: "Số người để tắt cảnh báo" },
  off_hold_seconds: { min: 0, max: 3600, label: "Giữ mức vắng trước khi tắt (giây)" },
} as const;

export type SettingsField = keyof typeof LIMITS;

/** Giá trị ban đầu của form khi chưa từng đổi từ web: trùng mặc định pilot trong cấu hình mẫu. */
export const PILOT_DEFAULTS: SettingsValues = {
  dwell_seconds: 2,
  on_count: 5,
  on_hold_seconds: 60,
  off_count: 3,
  off_hold_seconds: 10,
};

export type FormValues = Record<SettingsField, string>;

export function toForm(v: SettingsValues): FormValues {
  return {
    dwell_seconds: String(v.dwell_seconds),
    on_count: String(v.on_count),
    on_hold_seconds: String(v.on_hold_seconds),
    off_count: String(v.off_count),
    off_hold_seconds: String(v.off_hold_seconds),
  };
}

/** Lỗi theo từng ô và lỗi chéo; rỗng nếu hợp lệ. Trả số đã chuyển kiểu khi hợp lệ. */
export function validate(form: FormValues): { errors: string[]; values: SettingsValues | null } {
  const errors: string[] = [];
  const parsed: Partial<SettingsValues> = {};
  for (const field of Object.keys(LIMITS) as SettingsField[]) {
    const { min, max, label } = LIMITS[field];
    const raw = form[field].trim().replace(",", ".");
    const n = raw === "" ? NaN : Number(raw);
    if (Number.isNaN(n)) {
      errors.push(`${label}: nhập một số.`);
    } else if ((field === "on_count" || field === "off_count") && !Number.isInteger(n)) {
      errors.push(`${label}: phải là số nguyên.`);
    } else if (n < min || n > max) {
      errors.push(`${label}: từ ${min} đến ${max}.`);
    } else {
      parsed[field] = n;
    }
  }
  if (errors.length === 0 && (parsed.off_count as number) >= (parsed.on_count as number)) {
    errors.push("Số người để tắt cảnh báo phải nhỏ hơn số người để bật.");
  }
  return { errors, values: errors.length === 0 ? (parsed as SettingsValues) : null };
}
