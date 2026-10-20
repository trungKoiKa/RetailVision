import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "../../shared/api/client";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import type { AlertView, PageResponse } from "../../shared/types/api";
import { formatAge, formatDateTime, formatTime } from "../../shared/utils/format";

const PAGE_SIZE = 20;
const END_REASONS: Record<string, string> = {
  NORMALIZED: "đã hết đông",
  INTERRUPTED: "gián đoạn (mất dữ liệu)",
  CONFIG_CHANGED: "đổi ngưỡng",
};

export function AlertsPage() {
  const [page, setPage] = useState(0);
  const query = useQuery({
    queryKey: ["alerts", page],
    queryFn: () => apiFetch<PageResponse<AlertView>>(`/api/alerts?page=${page}&size=${PAGE_SIZE}`),
    placeholderData: keepPreviousData,
    refetchInterval: 5000,
    retry: false,
  });
  const data = query.isError ? undefined : query.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="page">
      <Card title="Lịch sử cảnh báo">
        {query.isError && <Banner kind="error">Không tải được danh sách cảnh báo.</Banner>}
        {query.isPending && <p className="muted">Đang tải…</p>}
        {data && data.items.length === 0 && <p className="muted">Chưa có cảnh báo nào.</p>}
        {data && data.items.length > 0 && (
          <div className="scroll">
            <table className="table" data-testid="alerts-table">
              <thead>
                <tr>
                  <th>Mở lúc</th>
                  <th>Số người</th>
                  <th>Xác nhận (ACK)</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.alert_id}>
                    <td>{formatDateTime(a.opened_at)}</td>
                    <td>{a.open_queue_count ?? "—"}</td>
                    <td>{a.acked_at ? `${formatTime(a.acked_at)} (sau ${formatAge(a.ack_latency_seconds)})` : "Chưa ACK"}</td>
                    <td>{a.open ? "Đang mở" : `Kết thúc ${formatTime(a.ended_at)}: ${END_REASONS[a.end_reason ?? ""] ?? "?"}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && (
          <nav className="pager" aria-label="Phân trang">
            <button type="button" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
              Trước
            </button>
            <span>
              Trang {page + 1}/{pages} ({data.total} cảnh báo)
            </span>
            <button type="button" onClick={() => setPage((p) => p + 1)} disabled={page + 1 >= pages}>
              Sau
            </button>
          </nav>
        )}
        <p className="muted">ACK chỉ cho biết nhân viên đã thấy cảnh báo, không phải đã xử lý xong.</p>
      </Card>
    </div>
  );
}
