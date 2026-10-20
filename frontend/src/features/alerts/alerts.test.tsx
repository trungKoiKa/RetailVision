import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { AlertView, PageResponse } from "../../shared/types/api";
import { MANAGER, loggedInAs, mockApi, renderApp, type Call } from "../../test/helpers";

function alert(i: number, patch: Partial<AlertView> = {}): AlertView {
  return {
    alert_id: `a${i}`,
    opened_at: "2026-11-02T09:00:00Z",
    open_queue_count: 5,
    acked_at: "2026-11-02T09:00:30Z",
    ack_device_id: "node01",
    ended_at: "2026-11-02T09:10:00Z",
    end_reason: "NORMALIZED",
    open: false,
    ack_latency_seconds: 30,
    ...patch,
  };
}

const page = (items: AlertView[], total = items.length, p = 0): PageResponse<AlertView> => ({ items, page: p, size: 20, total });

describe("trang Cảnh báo", () => {
  it("hiện từng cảnh báo với độ trễ ACK, chưa ACK, đang mở và lý do kết thúc", async () => {
    mockApi([
      loggedInAs(MANAGER),
      {
        path: "/api/alerts",
        body: page([
          alert(1),
          alert(2, { acked_at: null, ack_latency_seconds: null, ended_at: null, end_reason: null, open: true }),
          alert(3, { end_reason: "INTERRUPTED" }),
          alert(4, { end_reason: "CONFIG_CHANGED", open_queue_count: null }),
        ]),
      },
    ]);
    renderApp("/alerts");
    const rows = within(await screen.findByTestId("alerts-table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent("sau 30 giây");
    expect(rows[0]).toHaveTextContent("đã hết đông");
    expect(rows[1]).toHaveTextContent("Chưa ACK");
    expect(rows[1]).toHaveTextContent("Đang mở");
    expect(rows[2]).toHaveTextContent("gián đoạn");
    expect(rows[3]).toHaveTextContent("đổi ngưỡng");
    expect(within(rows[3]).getAllByRole("cell")[1]).toHaveTextContent("—"); // không biết số người: không phải 0
    expect(screen.getByText(/ACK chỉ cho biết nhân viên đã thấy/)).toBeInTheDocument();
  });

  it("phân trang: bấm Sau gọi page=1, Trước bị khóa ở trang đầu", async () => {
    const api = mockApi([
      loggedInAs(MANAGER),
      { path: "/api/alerts", body: (c: Call) => (c.url.includes("page=1") ? page([alert(21)], 25, 1) : page([alert(1)], 25, 0)) },
    ]);
    renderApp("/alerts");
    expect(await screen.findByText("Trang 1/2 (25 cảnh báo)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trước" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Sau" }));
    expect(await screen.findByText("Trang 2/2 (25 cảnh báo)")).toBeInTheDocument();
    expect(api.called("GET", "/api/alerts").some((c) => c.url.includes("page=1&size=20"))).toBe(true);
    expect(screen.getByRole("button", { name: "Sau" })).toBeDisabled();
  });

  it("chưa có cảnh báo và lỗi tải được phân biệt", async () => {
    mockApi([loggedInAs(MANAGER), { path: "/api/alerts", body: page([]) }]);
    const first = renderApp("/alerts");
    expect(await screen.findByText("Chưa có cảnh báo nào.")).toBeInTheDocument();
    first.unmount();

    mockApi([loggedInAs(MANAGER), { path: "/api/alerts", status: 500, body: {} }]);
    renderApp("/alerts");
    expect(await screen.findByRole("alert")).toHaveTextContent("Không tải được danh sách cảnh báo");
    expect(screen.queryByText("Chưa có cảnh báo nào.")).not.toBeInTheDocument(); // lỗi không được nói thành "không có"
  });
});
