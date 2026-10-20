import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { SettingsOverview, SettingsRequestView, SettingsValues } from "../../shared/types/api";
import { MANAGER, clearCookies, loggedInAs, mockApi, renderApp, setCsrfCookie, type Route } from "../../test/helpers";
import { PILOT_DEFAULTS, toForm, validate } from "./settings";

const DEVICES: Route = {
  path: "/api/devices",
  body: [
    { device_id: "edge01", status: "ONLINE", version: "0.1.0", clock_synced: false, last_seen_at: "2026-11-02T10:00:00Z" },
    { device_id: "node01", status: "UNKNOWN", version: null, clock_synced: null, last_seen_at: null },
  ],
};

const VALUES: SettingsValues = { dwell_seconds: 3, on_count: 4, on_hold_seconds: 30, off_count: 2, off_hold_seconds: 5 };

function request(status: SettingsRequestView["status"], patch: Partial<SettingsRequestView> = {}): SettingsRequestView {
  return {
    request_id: "r1",
    status,
    reason: null,
    expected_revision: 0,
    applied_revision: null,
    values: VALUES,
    requested_by: "manager1",
    requested_at: "2026-11-02T10:00:00Z",
    resolved_at: null,
    ...patch,
  };
}

function overview(patch: Partial<SettingsOverview> = {}): SettingsOverview {
  return { edge_revision: 0, current: null, latest: null, history: [], can_submit: true, cannot_submit_reason: null, ...patch };
}

const field = (label: string) => screen.getByLabelText(label) as HTMLInputElement;
const LABEL = {
  dwell: "Thời gian đứng tối thiểu trong vùng chờ (giây)",
  on: "Số người để bật cảnh báo",
  onHold: "Giữ mức đông trước khi cảnh báo (giây)",
  off: "Số người để tắt cảnh báo",
  offHold: "Giữ mức vắng trước khi tắt (giây)",
};

describe("kiểm tra giá trị ngưỡng", () => {
  it("mặc định pilot hợp lệ và chuyển được qua lại dạng chuỗi", () => {
    const { errors, values } = validate(toForm(PILOT_DEFAULTS));
    expect(errors).toEqual([]);
    expect(values).toEqual(PILOT_DEFAULTS);
  });

  it("từ chối ngoài khoảng, không phải số, số lẻ cho số người, và off >= on", () => {
    const base = toForm(PILOT_DEFAULTS);
    expect(validate({ ...base, dwell_seconds: "61" }).errors[0]).toContain("từ 0 đến 60");
    expect(validate({ ...base, on_count: "0" }).errors[0]).toContain("từ 1 đến 100");
    expect(validate({ ...base, on_hold_seconds: "abc" }).errors[0]).toContain("nhập một số");
    expect(validate({ ...base, off_count: "1.5" }).errors[0]).toContain("số nguyên");
    expect(validate({ ...base, off_hold_seconds: "" }).errors[0]).toContain("nhập một số");
    expect(validate({ ...base, on_count: "3", off_count: "3" }).errors).toEqual(["Số người để tắt cảnh báo phải nhỏ hơn số người để bật."]);
    expect(validate({ ...base, dwell_seconds: "2,5" }).values?.dwell_seconds).toBe(2.5); // dấu phẩy kiểu Việt Nam
  });
});

describe("trang Thiết bị và đổi ngưỡng", () => {
  beforeEach(() => setCsrfCookie("csrf-xyz"));
  afterEach(() => clearCookies());

  it("hiện thiết bị, kể cả đồng hồ chưa đồng bộ, và nói rõ giá trị ban đầu là mặc định chứ không phải đo từ edge", async () => {
    mockApi([loggedInAs(MANAGER), DEVICES, { path: "/api/settings", body: overview() }]);
    renderApp("/devices");
    const table = await screen.findByTestId("devices-table");
    expect(within(table).getByText("Chưa đồng bộ")).toBeInTheDocument();
    expect(within(table).getByText("Chưa rõ")).toBeInTheDocument();
    expect(await screen.findByTestId("settings-source")).toHaveTextContent("không phải giá trị đo được từ edge");
    expect(field(LABEL.on).value).toBe("5");
  });

  it("đã đổi từ web: điền sẵn ngưỡng hiện hành", async () => {
    mockApi([loggedInAs(MANAGER), DEVICES, { path: "/api/settings", body: overview({ edge_revision: 2, current: VALUES, latest: request("APPLIED", { applied_revision: 2 }) }) }]);
    renderApp("/devices");
    expect(await screen.findByTestId("settings-source")).toHaveTextContent("revision của edge: 2");
    expect(field(LABEL.on).value).toBe("4");
    expect(field(LABEL.dwell).value).toBe("3");
    expect(screen.getByTestId("settings-status")).toHaveTextContent("Edge đã áp dụng (revision 2)");
  });

  it("gửi đúng nội dung và CSRF; hiện 'đang chờ' rồi 'đã áp dụng' khi edge trả lời", async () => {
    let state: SettingsOverview = overview();
    const api = mockApi([
      loggedInAs(MANAGER),
      DEVICES,
      { path: "/api/settings", body: () => state },
      {
        method: "PUT",
        path: "/api/settings",
        status: 202,
        body: () => {
          state = overview({ latest: request("PENDING") });
          return request("PENDING");
        },
      },
    ]);
    renderApp("/devices");
    await screen.findByTestId("settings-source");
    await userEvent.clear(field(LABEL.on));
    await userEvent.type(field(LABEL.on), "6");
    await userEvent.clear(field(LABEL.off));
    await userEvent.type(field(LABEL.off), "2");
    await userEvent.click(screen.getByRole("button", { name: "Gửi tới edge" }));

    expect(await screen.findByText("Đang chờ edge xác nhận…")).toBeInTheDocument();
    const put = api.called("PUT", "/api/settings")[0];
    expect(put.body).toEqual({ dwell_seconds: 2, on_count: 6, on_hold_seconds: 60, off_count: 2, off_hold_seconds: 10 });
    expect(put.headers.get("X-XSRF-TOKEN")).toBe("csrf-xyz");

    // edge trả lời: lần làm mới sau cho thấy kết quả
    state = overview({ edge_revision: 1, current: VALUES, latest: request("APPLIED", { applied_revision: 1 }) });
    await userEvent.click(screen.getByText("Thiết bị", { selector: "a" })); // điều hướng trong ứng dụng kích hoạt tải lại
    await waitFor(() => expect(screen.getByTestId("settings-status")).toHaveTextContent("đã áp dụng"), { timeout: 4000 });
  });

  it("giá trị sai: báo ngay, không gửi gì tới backend", async () => {
    const api = mockApi([loggedInAs(MANAGER), DEVICES, { path: "/api/settings", body: overview() }]);
    renderApp("/devices");
    await screen.findByTestId("settings-source");
    await userEvent.clear(field(LABEL.off));
    await userEvent.type(field(LABEL.off), "5"); // off (5) >= on (5)
    await userEvent.click(screen.getByRole("button", { name: "Gửi tới edge" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("phải nhỏ hơn");
    expect(api.called("PUT", "/api/settings")).toHaveLength(0);
  });

  it("không gửi được lúc này (edge không có dữ liệu mới): khóa nút và nói lý do", async () => {
    mockApi([loggedInAs(MANAGER), DEVICES, { path: "/api/settings", body: overview({ edge_revision: null, can_submit: false, cannot_submit_reason: "Edge không có dữ liệu mới nên không thể đổi ngưỡng lúc này" }) }]);
    renderApp("/devices");
    expect(await screen.findByText(/Edge không có dữ liệu mới nên không thể đổi ngưỡng/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gửi tới edge" })).toBeDisabled();
  });

  it("backend từ chối (409): hiện đúng thông báo của backend", async () => {
    mockApi([
      loggedInAs(MANAGER),
      DEVICES,
      { path: "/api/settings", body: overview() },
      { method: "PUT", path: "/api/settings", status: 409, body: { error: "CONFLICT", message: "Đang chờ edge xác nhận yêu cầu trước" } },
    ]);
    renderApp("/devices");
    await screen.findByTestId("settings-source");
    await userEvent.click(screen.getByRole("button", { name: "Gửi tới edge" }));
    expect(await screen.findByText("Đang chờ edge xác nhận yêu cầu trước")).toBeInTheDocument();
  });

  it.each([
    ["REJECTED", { reason: "revision cũ: edge đang ở 2" }, "Edge từ chối: revision cũ: edge đang ở 2"],
    ["UNCONFIRMED", {}, "Ngưỡng có thể chưa được áp dụng"],
  ] as const)("trạng thái %s hiển thị đúng và không nói là đã áp dụng", async (status, patch, text) => {
    mockApi([loggedInAs(MANAGER), DEVICES, { path: "/api/settings", body: overview({ latest: request(status, patch), history: [request(status, patch)] }) }]);
    renderApp("/devices");
    expect(await screen.findByTestId("settings-status")).toHaveTextContent(text);
    expect(screen.getByTestId("settings-status")).not.toHaveTextContent("đã áp dụng");
    expect(screen.getByText("Lịch sử yêu cầu (1)")).toBeInTheDocument();
  });

  it("lỗi tải ngưỡng: banner lỗi, không hiện form với số bịa", async () => {
    mockApi([loggedInAs(MANAGER), DEVICES, { path: "/api/settings", status: 500, body: {} }]);
    renderApp("/devices");
    expect(await screen.findByText("Không tải được ngưỡng hiện tại.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Gửi tới edge" })).not.toBeInTheDocument();
  });
});
