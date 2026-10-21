import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { UNAUTHORIZED_EVENT } from "../../shared/api/client";
import { ADMIN, MANAGER, clearCookies, loggedInAs, mockApi, renderApp, setCsrfCookie, type Route } from "../../test/helpers";

const OVERVIEW: Route = {
  path: "/api/overview",
  body: {
    today: { date: "2026-11-02", timezone: "Asia/Ho_Chi_Minh", in: 5, out: 4 },
    live: { state: "NORMAL", queue_count: 1, alert_id: null, acked: false, observed_at: null, age_seconds: 0.5, stale: false, config_version: "p", settings_revision: 0 },
    last_alert: null,
    profile: "pilot",
    devices: [],
  },
};

describe("đăng nhập và phân quyền trên web", () => {
  beforeEach(() => setCsrfCookie("csrf-abc"));
  afterEach(() => clearCookies());

  it("chưa đăng nhập: mọi trang chuyển về /login", async () => {
    mockApi([{ path: "/api/auth/me", status: 401, body: { error: "UNAUTHENTICATED" } }]);
    renderApp("/footfall");
    expect(await screen.findByText("Đăng nhập RetailVision")).toBeInTheDocument();
    expect(screen.queryByText("Lượt vào/ra")).not.toBeInTheDocument();
  });

  it("đăng nhập đúng: gửi CSRF header, vào trang ban đầu và hiện vai trò", async () => {
    let session = false;
    const api = mockApi([
      { path: "/api/auth/me", status: () => (session ? 200 : 401), body: () => (session ? MANAGER : {}) },
      { method: "POST", path: "/api/auth/login", body: () => { session = true; return MANAGER; } },
      OVERVIEW,
    ]);
    renderApp("/");
    await userEvent.type(await screen.findByLabelText("Tên đăng nhập"), "manager1");
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "mat-khau-dung");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(await screen.findByText("manager1 (MANAGER)")).toBeInTheDocument();
    const login = api.calls.find((c) => c.url === "/api/auth/login")!;
    expect(login.method).toBe("POST");
    expect(login.headers.get("X-XSRF-TOKEN")).toBe("csrf-abc");
    expect(login.body).toEqual({ username: "manager1", password: "mat-khau-dung" });
  });

  it.each([
    [401, "Tên đăng nhập hoặc mật khẩu không đúng."],
    [429, "Sai quá nhiều lần"],
    [403, "Tải lại trang"],
  ])("đăng nhập lỗi %s: hiện thông báo phù hợp và ở lại trang đăng nhập", async (status, text) => {
    mockApi([
      { path: "/api/auth/me", status: 401, body: {} },
      { method: "POST", path: "/api/auth/login", status, body: { error: "X" } },
    ]);
    renderApp("/login");
    await userEvent.type(await screen.findByLabelText("Tên đăng nhập"), "manager1");
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "sai-mat-khau");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
    expect(screen.getByText("Đăng nhập RetailVision")).toBeInTheDocument();
  });

  it("nút đăng nhập bị khóa khi chưa nhập đủ", async () => {
    mockApi([{ path: "/api/auth/me", status: 401, body: {} }]);
    renderApp("/login");
    expect(await screen.findByRole("button", { name: "Đăng nhập" })).toBeDisabled();
  });

  it("đăng xuất: gọi logout với CSRF, xóa dữ liệu và về trang đăng nhập", async () => {
    let session = true;
    const api = mockApi([
      { path: "/api/auth/me", status: () => (session ? 200 : 401), body: () => (session ? MANAGER : {}) },
      { method: "POST", path: "/api/auth/logout", status: 204, body: () => { session = false; return undefined; } },
      OVERVIEW,
    ]);
    renderApp("/");
    expect(await screen.findByText("manager1 (MANAGER)")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Đăng xuất" })[0]);
    expect(await screen.findByText("Đăng nhập RetailVision")).toBeInTheDocument();
    const logout = api.calls.find((c) => c.url === "/api/auth/logout")!;
    expect(logout.headers.get("X-XSRF-TOKEN")).toBe("csrf-abc");
    expect(screen.queryByText("manager1 (MANAGER)")).not.toBeInTheDocument();
  });

  it("phiên hết hạn giữa chừng (API trả 401): tự về trang đăng nhập", async () => {
    mockApi([loggedInAs(MANAGER), OVERVIEW]);
    renderApp("/");
    expect(await screen.findByText("manager1 (MANAGER)")).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    });
    expect(await screen.findByText("Đăng nhập RetailVision")).toBeInTheDocument();
  });

  it("MANAGER không thấy mục Tài khoản và bị chặn khi gõ thẳng /users", async () => {
    const api = mockApi([loggedInAs(MANAGER)]);
    renderApp("/users");
    expect(await screen.findByRole("alert")).toHaveTextContent("không có quyền");
    expect(screen.queryByRole("link", { name: "Tài khoản" })).not.toBeInTheDocument();
    expect(api.called("GET", "/api/users")).toHaveLength(0); // không gọi API quản lý tài khoản
  });

  it("ADMIN thấy mục Tài khoản và vào được trang", async () => {
    mockApi([loggedInAs(ADMIN), { path: "/api/users", body: [] }]);
    renderApp("/users");
    expect(await screen.findByText("Tài khoản web")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tài khoản" })).toBeInTheDocument();
  });

  it("đã đăng nhập mà vào /login thì được đưa về trang chính", async () => {
    mockApi([loggedInAs(MANAGER), OVERVIEW]);
    renderApp("/login");
    await waitFor(() => expect(screen.queryByText("Đăng nhập RetailVision")).not.toBeInTheDocument());
    expect(await screen.findByText("manager1 (MANAGER)")).toBeInTheDocument();
  });
});
