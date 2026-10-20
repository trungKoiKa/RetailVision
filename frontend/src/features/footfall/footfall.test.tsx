import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FootfallBucket, FootfallResponse } from "../../shared/types/api";
import { MANAGER, loggedInAs, mockApi, renderApp } from "../../test/helpers";
import { bucketKind, daysInclusive, formatCoverage, rangeProblem, toChartRows, todayVn } from "./footfall";

function bucket(hour: number, patch: Partial<FootfallBucket> = {}): FootfallBucket {
  const start = new Date(Date.UTC(2026, 10, 1, 17 + hour, 0, 0)); // 00:00 giờ VN ngày 2/11 + hour
  return {
    start: start.toISOString(),
    end: new Date(start.getTime() + 3600_000).toISOString(),
    in: 10,
    out: 8,
    valid_seconds: 3600,
    expected_seconds: 3600,
    coverage: 1,
    gap: false,
    future: false,
    alerts_opened: 0,
    overload_minutes: 0,
    queue_avg: 1.5,
    queue_max: 3,
    ...patch,
  };
}

const GAP = { in: null, out: null, valid_seconds: 0, coverage: 0, gap: true, queue_avg: null, queue_max: null } satisfies Partial<FootfallBucket>;
const FUTURE = { in: null, out: null, valid_seconds: 0, expected_seconds: 0, coverage: null, future: true, queue_avg: null, queue_max: null } satisfies Partial<FootfallBucket>;

function report(buckets: FootfallBucket[], totals?: Partial<FootfallResponse["totals"]>): FootfallResponse {
  return {
    from: "2026-11-02",
    to: "2026-11-02",
    granularity: "hour",
    timezone: "Asia/Ho_Chi_Minh",
    buckets,
    totals: { in: 18, out: 14, gap_buckets: 1, coverage: 0.75, ...totals },
  };
}

describe("hàm trợ giúp báo cáo", () => {
  it("ngày hôm nay theo giờ Việt Nam, không theo UTC", () => {
    expect(todayVn(new Date("2026-11-02T16:59:59Z"))).toBe("2026-11-02");
    expect(todayVn(new Date("2026-11-02T17:00:00Z"))).toBe("2026-11-03"); // đã qua nửa đêm ở Việt Nam
  });

  it("đếm ngày gồm cả hai đầu và từ chối sai dạng", () => {
    expect(daysInclusive("2026-11-02", "2026-11-02")).toBe(1);
    expect(daysInclusive("2026-11-01", "2026-11-07")).toBe(7);
    expect(daysInclusive("2026-11-03", "2026-11-02")).toBe(0);
    expect(daysInclusive("", "2026-11-02")).toBeNull();
    expect(daysInclusive("02/11/2026", "2026-11-02")).toBeNull();
  });

  it("giới hạn khoảng theo cách gom", () => {
    expect(rangeProblem("2026-11-01", "2026-11-07", "hour")).toBeNull();
    expect(rangeProblem("2026-11-01", "2026-11-08", "hour")).toContain("Tối đa 7 ngày");
    expect(rangeProblem("2026-11-01", "2026-11-30", "day")).toBeNull();
    expect(rangeProblem("2025-01-01", "2026-11-30", "day")).toContain("Tối đa 366 ngày");
    expect(rangeProblem("2026-11-03", "2026-11-02", "hour")).toContain("không được sau");
    expect(rangeProblem("", "", "hour")).toContain("Chọn ngày");
  });

  it("phân loại khung và không biến null thành cột 0", () => {
    expect(bucketKind(bucket(0))).toBe("ok");
    expect(bucketKind(bucket(0, GAP))).toBe("gap");
    expect(bucketKind(bucket(0, FUTURE))).toBe("future");
    expect(bucketKind(bucket(0, { coverage: 0.5 }))).toBe("low");
    const rows = toChartRows([bucket(0), bucket(1, GAP), bucket(2, FUTURE)], "hour");
    expect(rows.map((r) => r.label)).toEqual(["00:00", "01:00", "02:00"]);
    expect(rows[1].in).toBeUndefined();
    expect(rows[1].out).toBeUndefined();
    expect(rows[2].in).toBeUndefined();
    expect(rows[0].in).toBe(10);
    expect(formatCoverage(null)).toBe("—");
    expect(formatCoverage(0.847)).toBe("85%");
  });
});

describe("trang Lượt vào/ra", () => {
  it("hiện số liệu, khung thiếu dữ liệu và khung chưa tới đúng như dữ liệu; gap không thành 0", async () => {
    const api = mockApi([
      loggedInAs(MANAGER),
      { path: "/api/footfall", body: report([bucket(0), bucket(1, GAP), bucket(2, { coverage: 0.5 }), bucket(3, FUTURE)]) },
    ]);
    renderApp("/footfall");
    const table = await screen.findByTestId("footfall-table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);

    const gap = rows[1];
    expect(gap).toHaveAttribute("data-kind", "gap");
    expect(within(gap).getByText("Thiếu dữ liệu")).toBeInTheDocument();
    const gapCells = within(gap).getAllByRole("cell").map((c) => c.textContent);
    expect(gapCells[1]).toBe("—"); // Vào
    expect(gapCells[2]).toBe("—"); // Ra
    expect(gapCells[1]).not.toBe("0");

    expect(rows[2]).toHaveAttribute("data-kind", "low");
    expect(within(rows[2]).getByText("Độ phủ thấp")).toBeInTheDocument();
    expect(rows[3]).toHaveAttribute("data-kind", "future");
    expect(within(rows[3]).getByText("Chưa tới")).toBeInTheDocument();
    expect(within(rows[0]).getAllByRole("cell")[1]).toHaveTextContent("10");

    expect(screen.getByTestId("total-in")).toHaveTextContent("18");
    expect(screen.getByTestId("total-coverage")).toHaveTextContent("75%");
    expect(screen.getByTestId("gap-note")).toHaveTextContent("1 khung thiếu dữ liệu");
    expect(api.called("GET", "/api/footfall")[0].url).toMatch(/granularity=hour/);
  });

  it("không có khung thiếu thì không hiện ghi chú gap", async () => {
    mockApi([loggedInAs(MANAGER), { path: "/api/footfall", body: report([bucket(0)], { gap_buckets: 0, coverage: 1 }) }]);
    renderApp("/footfall");
    await screen.findByTestId("footfall-table");
    expect(screen.queryByTestId("gap-note")).not.toBeInTheDocument();
  });

  it("liên kết CSV theo đúng khoảng và cách gom đang chọn", async () => {
    mockApi([loggedInAs(MANAGER), { path: "/api/footfall", body: report([bucket(0)]) }]);
    renderApp("/footfall");
    const link = await screen.findByRole("link", { name: "Xuất CSV" });
    expect(link.getAttribute("href")).toMatch(/^\/api\/reports\/export\.csv\?from=\d{4}-\d{2}-\d{2}&to=\d{4}-\d{2}-\d{2}&granularity=hour$/);
    fireEvent.change(screen.getByLabelText("Gom theo"), { target: { value: "day" } });
    expect((await screen.findByRole("link", { name: "Xuất CSV" })).getAttribute("href")).toContain("granularity=day");
  });

  it("khoảng quá dài: báo ngay trên giao diện, không gọi API và khóa nút CSV", async () => {
    const api = mockApi([loggedInAs(MANAGER), { path: "/api/footfall", body: report([bucket(0)]) }]);
    renderApp("/footfall");
    await screen.findByTestId("footfall-table");
    const before = api.called("GET", "/api/footfall").length;
    fireEvent.change(screen.getByLabelText("Từ ngày"), { target: { value: "2020-01-01" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Tối đa 7 ngày");
    expect(screen.queryByTestId("footfall-table")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Xuất CSV" })).not.toBeInTheDocument();
    expect(api.called("GET", "/api/footfall").length).toBe(before); // không gọi thêm
  });

  it("lỗi tải báo cáo: banner lỗi và không hiện số liệu", async () => {
    mockApi([loggedInAs(MANAGER), { path: "/api/footfall", status: 500, body: {} }]);
    renderApp("/footfall");
    expect(await screen.findByRole("alert")).toHaveTextContent("Không tải được báo cáo");
    expect(screen.queryByTestId("footfall-table")).not.toBeInTheDocument();
    expect(screen.queryByTestId("total-in")).not.toBeInTheDocument();
  });
});
