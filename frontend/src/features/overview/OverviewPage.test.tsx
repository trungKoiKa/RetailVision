import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../../shared/types/api";
import { OverviewPage } from "./OverviewPage";

function overview(patch: Partial<Overview> = {}, live: Partial<Overview["live"]> = {}): Overview {
  return {
    today: { date: "2026-11-02", timezone: "Asia/Ho_Chi_Minh", in: 42, out: 39 },
    live: {
      state: "NORMAL",
      queue_count: 1,
      alert_id: null,
      acked: false,
      observed_at: "2026-11-02T10:00:00Z",
      age_seconds: 0.8,
      stale: false,
      config_version: "pilot-1",
      ...live,
    },
    last_alert: null,
    profile: "pilot",
    devices: [
      { device_id: "edge01", status: "ONLINE", version: "0.1.0", clock_synced: true, last_seen_at: "2026-11-02T10:00:00Z" },
      { device_id: "node01", status: "UNKNOWN", version: null, clock_synced: null, last_seen_at: null },
    ],
    ...patch,
  };
}

function mockApi(body: Overview | "network-error" | number) {
  const fetchMock = vi.fn(async () => {
    if (body === "network-error") throw new TypeError("Failed to fetch");
    if (typeof body === "number") return new Response("{}", { status: body });
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <OverviewPage />
    </QueryClientProvider>,
  );
}

describe("OverviewPage", () => {
  beforeEach(() => vi.useRealTimers());
  afterEach(() => vi.unstubAllGlobals());

  it("hiện trạng thái bình thường, số người và lượt hôm nay", async () => {
    mockApi(overview());
    renderPage();
    expect(await screen.findByText("Bình thường")).toBeInTheDocument();
    expect(screen.getByTestId("queue-count")).toHaveTextContent("1");
    expect(screen.getByTestId("today-in")).toHaveTextContent("42");
    expect(screen.getByTestId("today-out")).toHaveTextContent("39");
    expect(screen.getByTestId("data-age")).toHaveTextContent("0,8 giây");
    expect(screen.getByText("Profile: pilot")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("OVERLOAD chưa ACK: báo chưa có xác nhận", async () => {
    mockApi(overview({}, { state: "OVERLOAD", queue_count: 5, alert_id: "a1", acked: false }));
    renderPage();
    expect(await screen.findByText("Quá tải")).toBeInTheDocument();
    expect(screen.getByTestId("queue-count")).toHaveTextContent("5");
    expect(screen.getByTestId("ack-note")).toHaveTextContent("Chưa có nhân viên xác nhận");
  });

  it("OVERLOAD đã ACK: nói rõ vẫn đông, cảnh báo chưa kết thúc", async () => {
    mockApi(overview({}, { state: "OVERLOAD", queue_count: 5, alert_id: "a1", acked: true }));
    renderPage();
    expect(await screen.findByText("Quá tải")).toBeInTheDocument();
    expect(screen.getByTestId("ack-note")).toHaveTextContent("vẫn đông");
  });

  it("UNKNOWN/state cũ: hiện '—' và banner, không bao giờ hiện 0", async () => {
    mockApi(overview({}, { state: "UNKNOWN", queue_count: null, stale: true, age_seconds: 12 }));
    renderPage();
    const banner = await screen.findByRole("alert"); // đợi dữ liệu tải xong
    expect(screen.getByText("Không có dữ liệu")).toBeInTheDocument();
    expect(screen.getByTestId("queue-count")).toHaveTextContent("—");
    expect(screen.getByTestId("queue-count")).not.toHaveTextContent("0");
    expect(banner).toHaveTextContent("Không có dữ liệu tin cậy");
    expect(banner).toHaveTextContent("12 giây");
  });

  it("chưa từng có state: UNKNOWN, '—', không có tuổi dữ liệu", async () => {
    mockApi(overview({}, { state: "UNKNOWN", queue_count: null, stale: true, age_seconds: null, observed_at: null }));
    renderPage();
    await screen.findByTestId("today-in"); // đợi dữ liệu tải xong
    expect(screen.getByText("Không có dữ liệu")).toBeInTheDocument();
    expect(screen.getByTestId("data-age")).toHaveTextContent("—");
  });

  it.each([["network-error" as const], [500], [503]])("backend lỗi (%s): banner lỗi và không dùng số liệu cũ", async (failure) => {
    mockApi(failure);
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Không kết nối được backend");
    expect(screen.getByTestId("queue-count")).toHaveTextContent("—");
    expect(screen.queryByTestId("today-in")).not.toBeInTheDocument();
    expect(screen.getByText("Không có dữ liệu")).toBeInTheDocument();
    expect(screen.queryByText("Chưa có cảnh báo.")).not.toBeInTheDocument(); // không biết, chứ không phải "không có"
  });

  it("sau khi từng có dữ liệu mà backend lỗi: bỏ số cũ", async () => {
    const fetchMock = mockApi(overview());
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <OverviewPage />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Bình thường")).toBeInTheDocument();
    fetchMock.mockImplementation(async () => {
      throw new TypeError("Failed to fetch");
    });
    await client.invalidateQueries({ queryKey: ["overview"] });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Không kết nối được backend"));
    expect(screen.getByTestId("queue-count")).toHaveTextContent("—");
    expect(screen.queryByText("Bình thường")).not.toBeInTheDocument();
  });

  it("cảnh báo gần nhất: đang mở / đã kết thúc kèm lý do và độ trễ ACK", async () => {
    mockApi(
      overview({
        last_alert: {
          alert_id: "a1",
          opened_at: "2026-11-02T09:00:00Z",
          open_queue_count: 5,
          acked_at: "2026-11-02T09:00:30Z",
          ack_device_id: "node01",
          ended_at: "2026-11-02T09:10:00Z",
          end_reason: "NORMALIZED",
          open: false,
          ack_latency_seconds: 30,
        },
      }),
    );
    renderPage();
    const box = await screen.findByTestId("last-alert");
    expect(box).toHaveTextContent("Đã kết thúc");
    expect(box).toHaveTextContent("đã hết đông");
    expect(box).toHaveTextContent("sau 30 giây");
  });

  it("thiết bị: chưa rõ, và cảnh báo giờ chưa đồng bộ", async () => {
    mockApi(
      overview({
        devices: [
          { device_id: "edge01", status: "ONLINE", version: "0.1.0", clock_synced: false, last_seen_at: "2026-11-02T10:00:00Z" },
          { device_id: "node01", status: "UNKNOWN", version: null, clock_synced: null, last_seen_at: null },
        ],
      }),
    );
    renderPage();
    expect(await screen.findByText(/giờ chưa đồng bộ/)).toBeInTheDocument();
    expect(screen.getByText("Chưa rõ")).toBeInTheDocument();
  });
});
