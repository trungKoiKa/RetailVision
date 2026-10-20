import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import { StatusBadge } from "../../shared/components/StatusBadge";
import type { AlertView, DeviceView, Live, Overview } from "../../shared/types/api";
import { formatAge, formatCount, formatDateTime, formatTime } from "../../shared/utils/format";
import { useOverview } from "./useOverview";

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
};

export function OverviewPage() {
  const query = useOverview();
  const data = query.data;
  const backendDown = query.isError;
  const live = backendDown || !data ? UNKNOWN_LIVE : data.live;

  return (
    <div className="page">
      {backendDown && <Banner kind="error">Không kết nối được backend. Số liệu bên dưới không phải dữ liệu hiện tại.</Banner>}
      {!backendDown && data && live.stale && (
        <Banner kind="warn">
          Không có dữ liệu tin cậy từ camera
          {live.age_seconds !== null ? ` (state cuối cách đây ${formatAge(live.age_seconds)})` : ""}.
        </Banner>
      )}
      {query.isPending && <p className="muted">Đang tải…</p>}

      <div className="grid">
        <LiveCard live={live} profile={data?.profile ?? null} />
        <TodayCard today={backendDown ? null : (data?.today ?? null)} />
        <AlertCard alert={backendDown ? null : (data?.last_alert ?? null)} unknown={backendDown || !data} />
        <DevicesCard devices={backendDown ? [] : (data?.devices ?? [])} />
      </div>
    </div>
  );
}

function LiveCard({ live, profile }: { live: Live; profile: Overview["profile"] }) {
  return (
    <Card title="Vùng chờ" className="card-live">
      <div className="live-head">
        <StatusBadge state={live.state} />
        {profile && <span className="chip">Profile: {profile}</span>}
      </div>
      <div className="big-number" data-testid="queue-count" aria-label="Số người trong vùng chờ">
        {formatCount(live.queue_count)}
      </div>
      <div className="muted">người trong vùng chờ</div>
      {live.state === "OVERLOAD" && (
        <p className="note" data-testid="ack-note">
          {live.acked
            ? "Nhân viên đã xác nhận (ACK). Vùng chờ vẫn đông, cảnh báo chưa kết thúc."
            : "Chưa có nhân viên xác nhận (ACK)."}
        </p>
      )}
      <div className="muted" data-testid="data-age">
        Tuổi dữ liệu: {formatAge(live.age_seconds)}
      </div>
    </Card>
  );
}

function TodayCard({ today }: { today: Overview["today"] | null }) {
  return (
    <Card title="Hôm nay">
      {today ? (
        <>
          <div className="pair">
            <div>
              <div className="big-number" data-testid="today-in">
                {today.in}
              </div>
              <div className="muted">Lượt vào</div>
            </div>
            <div>
              <div className="big-number" data-testid="today-out">
                {today.out}
              </div>
              <div className="muted">Lượt ra</div>
            </div>
          </div>
          <div className="muted">Ngày {today.date} (giờ Việt Nam)</div>
        </>
      ) : (
        <div className="big-number">—</div>
      )}
    </Card>
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
          <dd>{alert.open ? "Đang mở" : `Đã kết thúc ${formatTime(alert.ended_at)} (${END_REASONS[alert.end_reason ?? ""] ?? "?"})`}</dd>
          <dt>Xác nhận</dt>
          <dd>{alert.acked_at ? `${formatTime(alert.acked_at)} (sau ${formatAge(alert.ack_latency_seconds)})` : "Chưa có ACK"}</dd>
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
