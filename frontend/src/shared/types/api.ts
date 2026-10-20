// Kiểu khớp DTO của backend (JSON snake_case). Nguồn: backend/.../dto/response.

export type LiveState = "NORMAL" | "OVERLOAD" | "UNKNOWN";

export interface Live {
  state: LiveState;
  /** null khi UNKNOWN hoặc dữ liệu cũ: không bao giờ được hiển thị như 0 */
  queue_count: number | null;
  alert_id: string | null;
  acked: boolean;
  observed_at: string | null;
  age_seconds: number | null;
  stale: boolean;
  config_version: string | null;
  settings_revision: number | null;
}

export interface AlertView {
  alert_id: string;
  opened_at: string;
  open_queue_count: number | null;
  acked_at: string | null;
  ack_device_id: string | null;
  ended_at: string | null;
  end_reason: "NORMALIZED" | "INTERRUPTED" | "CONFIG_CHANGED" | null;
  open: boolean;
  ack_latency_seconds: number | null;
}

export interface PageResponse<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
}

export interface DeviceView {
  device_id: string;
  status: "ONLINE" | "OFFLINE" | "UNKNOWN";
  version: string | null;
  clock_synced: boolean | null;
  last_seen_at: string | null;
}

export interface Overview {
  today: { date: string; timezone: string; in: number; out: number };
  live: Live;
  last_alert: AlertView | null;
  profile: "pilot" | "demo" | null;
  devices: DeviceView[];
}

export type Role = "ADMIN" | "MANAGER";

export interface Me {
  username: string;
  role: Role;
}

export interface UserView {
  id: number;
  username: string;
  role: Role;
  enabled: boolean;
  created_at: string;
  last_login_at: string | null;
}

export type Granularity = "hour" | "day";

/** `in`/`out` null = không có dữ liệu (không phải 0). */
export interface FootfallBucket {
  start: string;
  end: string;
  in: number | null;
  out: number | null;
  valid_seconds: number;
  expected_seconds: number;
  coverage: number | null;
  gap: boolean;
  future: boolean;
  alerts_opened: number;
  overload_minutes: number;
  queue_avg: number | null;
  queue_max: number | null;
}

export interface FootfallResponse {
  from: string;
  to: string;
  granularity: Granularity;
  timezone: string;
  buckets: FootfallBucket[];
  totals: { in: number; out: number; gap_buckets: number; coverage: number | null };
}

export interface SettingsValues {
  dwell_seconds: number;
  on_count: number;
  on_hold_seconds: number;
  off_count: number;
  off_hold_seconds: number;
}

export type SettingsStatus = "PENDING" | "UNCONFIRMED" | "APPLIED" | "REJECTED";

export interface SettingsRequestView {
  request_id: string;
  status: SettingsStatus;
  reason: string | null;
  expected_revision: number;
  applied_revision: number | null;
  values: SettingsValues;
  requested_by: string;
  requested_at: string;
  resolved_at: string | null;
}

export interface SettingsOverview {
  edge_revision: number | null;
  current: SettingsValues | null;
  latest: SettingsRequestView | null;
  history: SettingsRequestView[];
  can_submit: boolean;
  cannot_submit_reason: string | null;
}
