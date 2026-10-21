import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiFetch } from "../../shared/api/client";
import type { FootfallResponse } from "../../shared/types/api";
import { todayVn, toChartRows } from "../footfall/footfall";

/** Lượt vào/ra hôm nay theo giờ. Không tải được thì không vẽ gì (không vẽ cột 0 thay cho thiếu dữ liệu). */
export default function TodayChart() {
  const today = todayVn();
  const query = useQuery({
    queryKey: ["footfall", today, today, "hour"],
    queryFn: () => apiFetch<FootfallResponse>(`/api/footfall?from=${today}&to=${today}&granularity=hour`),
    refetchInterval: 60_000,
    retry: false,
  });
  if (query.isPending) return <p className="muted">Đang tải biểu đồ…</p>;
  if (query.isError || !query.data || !Array.isArray(query.data.buckets)) return <p className="muted">Chưa tải được biểu đồ hôm nay.</p>;
  const rows = toChartRows(query.data.buckets, "hour");
  const total = rows.reduce((n, r) => n + (r.in ?? 0) + (r.out ?? 0), 0);
  const hasData = rows.some((r) => r.in !== undefined || r.out !== undefined);
  return (
    <div className="chart" role="img" aria-label="Biểu đồ lượt vào và ra theo giờ trong hôm nay">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} barGap={2}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={32} />
          <Tooltip cursor={{ fill: "var(--surface-2)" }} />
          {rows
            .filter((r) => r.kind === "gap")
            .map((r) => (
              <ReferenceArea key={r.label} x1={r.label} x2={r.label} fill="var(--chart-gap)" fillOpacity={0.25} ifOverflow="visible" />
            ))}
          <Bar dataKey="in" name="Vào" fill="var(--chart-in)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="out" name="Ra" fill="var(--chart-out)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      {hasData && total === 0 && <p className="muted">Chưa ghi nhận lượt vào/ra nào trong các khung có dữ liệu.</p>}
      {!hasData && <p className="muted">Chưa có khung nào có dữ liệu hôm nay.</p>}
    </div>
  );
}
