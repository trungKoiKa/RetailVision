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
