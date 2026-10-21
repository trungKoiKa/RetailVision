import { lazy, Suspense } from "react";
import { Cpu, LogIn, LogOut, Users } from "lucide-react";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import { KpiCard } from "../../shared/components/KpiCard";
import { StatusBadge } from "../../shared/components/StatusBadge";
import type { AlertView, DeviceView, Live } from "../../shared/types/api";
import { formatAge, formatCount, formatDateTime, formatTime } from "../../shared/utils/format";
import { useOverview } from "./useOverview";

const TodayChart = lazy(() => import("./TodayChart"));

const END_REASONS: Record<string, string> = {
  NORMALIZED: "đã hết đông",
  INTERRUPTED: "bị gián đoạn (mất dữ liệu)",
  CONFIG_CHANGED: "đổi ngưỡng",
};

/** Khi không gọi được backend, coi như không biết gì về hiện tại: không dùng lại số cũ như dữ liệu sống. */
const UNKNOWN_LIVE: Live = {
  state: "UNKNOWN",
  queue_count: null,
  alert_id: null,
  acked: false,
  observed_at: null,
  age_seconds: null,
  stale: true,
  config_version: null,
  settings_revision: null,
};

export function OverviewPage() {
  const query = useOverview();
  const data = query.data;
  const backendDown = query.isError;
  const live = backendDown || !data ? UNKNOWN_LIVE : data.live;
  const today = backendDown ? null : (data?.today ?? null);
  const devices = backendDown ? [] : (data?.devices ?? []);
  const online = devices.filter((d) => d.status === "ONLINE").length;

  return (
    <div className="page">
      {backendDown && (
        <Banner kind="error">Không kết nối được backend. Số liệu bên dưới không phải dữ liệu hiện tại.</Banner>
      )}
      {!backendDown && data && live.stale && (
        <Banner kind="warn">
          Không có dữ liệu tin cậy từ camera
          {live.age_seconds !== null ? ` (state cuối cách đây ${formatAge(live.age_seconds)})` : ""}.
        </Banner>
      )}
      {query.isPending && <p className="muted">Đang tải…</p>}

      <div className="kpi-row">
        <KpiCard
          className={`kpi-live live-${live.state.toLowerCase()}`}
          icon={Users}
          tone={live.state === "OVERLOAD" ? "red" : live.state === "NORMAL" ? "green" : "amber"}
          label="Người trong vùng chờ"
          value={formatCount(live.queue_count)}
          valueTestId="queue-count"
          extra={<StatusBadge state={live.state} />}
          hint={
            <>
              <span data-testid="data-age">Tuổi dữ liệu: {formatAge(live.age_seconds)}</span>
              {data?.profile && <span className="chip">Profile: {data.profile}</span>}
            </>
          }
        />
        <KpiCard
          icon={LogIn}
          tone="green"
          label="Lượt vào hôm nay"
          value={today ? today.in : "—"}
          valueTestId={today ? "today-in" : undefined}
          hint={today ? `Ngày ${today.date} (giờ Việt Nam)` : undefined}
        />
        <KpiCard
          icon={LogOut}
          tone="blue"
          label="Lượt ra hôm nay"
          value={today ? today.out : "—"}
          valueTestId={today ? "today-out" : undefined}
          hint={today ? `Chênh lệch vào − ra: ${today.in - today.out}` : undefined}
        />
        <KpiCard
          icon={Cpu}
          tone="violet"
          label="Thiết bị trực tuyến"
          value={backendDown || !data ? "—" : `${online}/${devices.length}`}
          hint="edge01 (Pi) và node01 (ESP32)"
        />
      </div>

      {live.state === "OVERLOAD" && (
        <div className={`alert-strip ${live.acked ? "acked" : ""}`} data-testid="ack-note">
          {live.acked
            ? "Nhân viên đã xác nhận (ACK). Vùng chờ vẫn đông, cảnh báo chưa kết thúc."
            : "Chưa có nhân viên xác nhận (ACK)."}
        </div>
      )}

      <div className="split">
        <Card title="Lượt vào/ra hôm nay theo giờ">
          <Suspense fallback={<p className="muted">Đang tải biểu đồ…</p>}>
            {backendDown ? <p className="muted">—</p> : <TodayChart />}
          </Suspense>
          <p className="muted">Khung xám là thiếu dữ liệu (không có cột, không phải 0).</p>
        </Card>
        <div className="stack">
          <AlertCard alert={backendDown ? null : (data?.last_alert ?? null)} unknown={backendDown || !data} />
          <DevicesCard devices={devices} />
        </div>
      </div>
    </div>
  );
}

function AlertCard({ alert, unknown }: { alert: AlertView | null; unknown: boolean }) {
  return (
    <Card title="Cảnh báo gần nhất">
      {unknown ? (
        <p className="muted">—</p>
      ) : !alert ? (
        <p className="muted">Chưa có cảnh báo.</p>
      ) : (
        <dl className="facts" data-testid="last-alert">
          <dt>Mở lúc</dt>
          <dd>{formatDateTime(alert.opened_at)}</dd>
          <dt>Trạng thái</dt>
          <dd>
            {alert.open
              ? "Đang mở"
              : `Đã kết thúc ${formatTime(alert.ended_at)} (${END_REASONS[alert.end_reason ?? ""] ?? "?"})`}
          </dd>
          <dt>Xác nhận</dt>
          <dd>
            {alert.acked_at
              ? `${formatTime(alert.acked_at)} (sau ${formatAge(alert.ack_latency_seconds)})`
              : "Chưa có ACK"}
          </dd>
        </dl>
      )}
    </Card>
  );
}

function DevicesCard({ devices }: { devices: DeviceView[] }) {
  return (
    <Card title="Thiết bị">
      {devices.length === 0 ? (
        <p className="muted">—</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Thiết bị</th>
              <th>Trạng thái</th>
              <th>Lần cuối thấy</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => (
              <tr key={d.device_id}>
                <td>{d.device_id}</td>
                <td>
                  <span className={`dot dot-${d.status.toLowerCase()}`} aria-hidden="true" />
                  {d.status === "UNKNOWN" ? "Chưa rõ" : d.status}
                  {d.status === "ONLINE" && d.clock_synced === false ? " (giờ chưa đồng bộ)" : ""}
                </td>
                <td>{formatTime(d.last_seen_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
