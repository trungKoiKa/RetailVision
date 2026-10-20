import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../shared/api/client";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import type { DeviceView } from "../../shared/types/api";
import { formatDateTime } from "../../shared/utils/format";
import { SettingsCard } from "./SettingsCard";

const STATUS_TEXT = { ONLINE: "Trực tuyến", OFFLINE: "Ngoại tuyến", UNKNOWN: "Chưa rõ" } as const;

export function DevicesPage() {
  const query = useQuery({
    queryKey: ["devices"],
    queryFn: () => apiFetch<DeviceView[]>("/api/devices"),
    refetchInterval: 5000,
    retry: false,
  });
  const devices = query.isError ? undefined : query.data;

  return (
    <div className="page">
      <Card title="Thiết bị">
        {query.isError && <Banner kind="error">Không tải được danh sách thiết bị.</Banner>}
        {query.isPending && <p className="muted">Đang tải…</p>}
        {devices && (
          <div className="scroll">
            <table className="table" data-testid="devices-table">
              <thead>
                <tr>
                  <th>Thiết bị</th>
                  <th>Trạng thái</th>
                  <th>Phiên bản</th>
                  <th>Đồng hồ</th>
                  <th>Lần cuối thấy</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((d) => (
                  <tr key={d.device_id}>
                    <td>{d.device_id}</td>
                    <td>
                      <span className={`dot dot-${d.status.toLowerCase()}`} aria-hidden="true" />
                      {STATUS_TEXT[d.status]}
                    </td>
                    <td>{d.version ?? "—"}</td>
                    <td>{d.clock_synced === null ? "—" : d.clock_synced ? "Đã đồng bộ" : "Chưa đồng bộ"}</td>
                    <td>{formatDateTime(d.last_seen_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <SettingsCard />
    </div>
  );
}
