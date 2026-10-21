import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Gauge, LogIn, LogOut } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiFetch } from "../../shared/api/client";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import { KpiCard } from "../../shared/components/KpiCard";
import type { FootfallResponse, Granularity } from "../../shared/types/api";
import { formatCount } from "../../shared/utils/format";
import { bucketKind, formatCoverage, rangeLabel, rangeProblem, todayVn, toChartRows } from "./footfall";

const KIND_TEXT = { future: "Chưa tới", gap: "Thiếu dữ liệu", low: "Độ phủ thấp", ok: "" } as const;

export function FootfallPage() {
  const today = todayVn();
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [granularity, setGranularity] = useState<Granularity>("hour");

  const problem = rangeProblem(from, to, granularity);
  const query = useQuery({
    queryKey: ["footfall", from, to, granularity],
    queryFn: () => apiFetch<FootfallResponse>(`/api/footfall?from=${from}&to=${to}&granularity=${granularity}`),
    enabled: problem === null,
    retry: false,
  });
  const csvHref = `/api/reports/export.csv?from=${from}&to=${to}&granularity=${granularity}`;
  const data = problem === null && !query.isError ? query.data : undefined;

  return (
    <div className="page">
      <Card title="Bộ lọc báo cáo">
        <div className="filters">
          <label>
            Từ ngày
            <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label>
            Đến ngày
            <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} />
          </label>
          <label>
            Gom theo
            <select value={granularity} onChange={(e) => setGranularity(e.target.value as Granularity)}>
              <option value="hour">Giờ (tối đa 7 ngày)</option>
              <option value="day">Ngày (tối đa 366 ngày)</option>
            </select>
          </label>
          {problem === null ? (
            <a className="button" href={csvHref} download>
              Xuất CSV
            </a>
          ) : (
            <span className="button disabled" aria-disabled="true">
              Xuất CSV
            </span>
          )}
        </div>
        {problem && <Banner kind="warn">{problem}</Banner>}
        {query.isError && <Banner kind="error">Không tải được báo cáo. Số liệu cũ (nếu có) không được hiển thị.</Banner>}
        {problem === null && query.isPending && <p className="muted">Đang tải…</p>}
      </Card>

      {data && <Report data={data} />}
    </div>
  );
}

function Report({ data }: { data: FootfallResponse }) {
  const rows = toChartRows(data.buckets, data.granularity);
  const gaps = data.totals.gap_buckets;
  return (
    <>
      <div className="kpi-row three">
        <KpiCard icon={LogIn} tone="green" label="Lượt vào" value={data.totals.in} valueTestId="total-in" />
        <KpiCard icon={LogOut} tone="blue" label="Lượt ra" value={data.totals.out} valueTestId="total-out" />
        <KpiCard
          icon={Gauge}
          tone="violet"
          label="Độ phủ quan sát"
          value={formatCoverage(data.totals.coverage)}
          valueTestId="total-coverage"
          hint="Tỉ lệ thời gian camera có dữ liệu hợp lệ"
        />
      </div>
      {gaps > 0 && (
        <div className="alert-strip acked" data-testid="gap-note">
          {gaps} khung thiếu dữ liệu: tổng chỉ cộng các khung có số liệu, không coi khung thiếu là 0.
        </div>
      )}

      <Card title="Biểu đồ">
        <div className="chart" aria-label="Biểu đồ lượt vào/ra">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rows}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              {rows.filter((r) => r.kind === "gap").map((r) => (
                <ReferenceArea key={r.label} x1={r.label} x2={r.label} fill="var(--chart-gap)" fillOpacity={0.25} ifOverflow="visible" />
              ))}
              <Bar dataKey="in" name="Vào" fill="var(--chart-in)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="out" name="Ra" fill="var(--chart-out)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="muted">Khung xám là thiếu dữ liệu (không có cột, không phải 0).</p>
      </Card>

      <Card title="Chi tiết">
        <div className="scroll">
          <table className="table" data-testid="footfall-table">
            <thead>
              <tr>
                <th>Khung</th>
                <th>Vào</th>
                <th>Ra</th>
                <th>Độ phủ</th>
                <th>Cảnh báo</th>
                <th>Phút quá tải</th>
                <th>Người TB / tối đa</th>
                <th>Ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {data.buckets.map((b) => {
                const kind = bucketKind(b);
                return (
                  <tr key={b.start} className={`row-${kind}`} data-kind={kind}>
                    <td>{rangeLabel(b, data.granularity)}</td>
                    <td>{formatCount(b.in)}</td>
                    <td>{formatCount(b.out)}</td>
                    <td>{formatCoverage(b.coverage)}</td>
                    <td>{b.future ? "—" : b.alerts_opened}</td>
                    <td>{b.future ? "—" : b.overload_minutes}</td>
                    <td>{b.queue_avg === null ? "—" : `${b.queue_avg} / ${b.queue_max ?? "—"}`}</td>
                    <td>{KIND_TEXT[kind]}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
