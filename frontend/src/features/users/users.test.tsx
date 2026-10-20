import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { UserView } from "../../shared/types/api";
import { ADMIN, MANAGER, clearCookies, loggedInAs, mockApi, renderApp, setCsrfCookie } from "../../test/helpers";

const USERS: UserView[] = [
  { id: 1, username: "admin1", role: "ADMIN", enabled: true, created_at: "2026-11-01T00:00:00Z", last_login_at: "2026-11-02T10:00:00Z" },
  { id: 2, username: "manager1", role: "MANAGER", enabled: true, created_at: "2026-11-01T00:00:00Z", last_login_at: null },
  { id: 3, username: "old1", role: "MANAGER", enabled: false, created_at: "2026-11-01T00:00:00Z", last_login_at: null },
];

describe("trang Tài khoản (ADMIN)", () => {
  beforeEach(() => setCsrfCookie("csrf-u"));
  afterEach(() => clearCookies());

  it("liệt kê tài khoản; không cho tự vô hiệu hóa chính mình", async () => {
    mockApi([loggedInAs(ADMIN), { path: "/api/users", body: USERS }]);
    renderApp("/users");
    const rows = within(await screen.findByTestId("users-table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    expect(within(rows[0]).getByRole("button", { name: "Vô hiệu hóa" })).toBeDisabled(); // admin1 đang đăng nhập
    expect(within(rows[1]).getByRole("button", { name: "Vô hiệu hóa" })).toBeEnabled();
    expect(within(rows[2]).getByRole("button", { name: "Kích hoạt" })).toBeEnabled();
    expect(rows[2]).toHaveTextContent("Đã vô hiệu hóa");
  });

  it("tạo tài khoản: gửi đúng nội dung kèm CSRF", async () => {
    const api = mockApi([
      loggedInAs(ADMIN),
      { path: "/api/users", body: USERS },
      { method: "POST", path: "/api/users", status: 201, body: { ...USERS[1], id: 9, username: "newuser" } },
    ]);
    renderApp("/users");
    await screen.findByTestId("users-table");
    await userEvent.type(screen.getByLabelText(/Tên đăng nhập/), "newuser");
    await userEvent.type(screen.getByLabelText(/Mật khẩu \(tối thiểu/), "password-9");
    await userEvent.click(screen.getByRole("button", { name: "Tạo tài khoản" }));
    await screen.findByTestId("users-table");
    const post = api.called("POST", "/api/users")[0];
    expect(post.body).toEqual({ username: "newuser", password: "password-9", role: "MANAGER" });
    expect(post.headers.get("X-XSRF-TOKEN")).toBe("csrf-u");
  });

  it("nút tạo bị khóa khi mật khẩu ngắn", async () => {
    mockApi([loggedInAs(ADMIN), { path: "/api/users", body: USERS }]);
    renderApp("/users");
    await screen.findByTestId("users-table");
    await userEvent.type(screen.getByLabelText(/Tên đăng nhập/), "newuser");
    await userEvent.type(screen.getByLabelText(/Mật khẩu \(tối thiểu/), "short");
    expect(screen.getByRole("button", { name: "Tạo tài khoản" })).toBeDisabled();
  });

  it("vô hiệu hóa và đổi vai trò gọi PATCH đúng; lỗi 409 của backend được hiện nguyên văn", async () => {
    const api = mockApi([
      loggedInAs(ADMIN),
      { path: "/api/users", body: USERS },
      { method: "PATCH", path: "/api/users/2", body: USERS[1] },
      { method: "PATCH", path: "/api/users/3", status: 409, body: { error: "CONFLICT", message: "Phải còn ít nhất một ADMIN đang hoạt động" } },
    ]);
    renderApp("/users");
    const rows = within(await screen.findByTestId("users-table")).getAllByRole("row").slice(1);
    await userEvent.click(within(rows[1]).getByRole("button", { name: "Vô hiệu hóa" }));
    await userEvent.selectOptions(within(rows[1]).getByLabelText("Vai trò của manager1"), "ADMIN");
    await userEvent.click(within(rows[2]).getByRole("button", { name: "Kích hoạt" }));
    const patches = api.called("PATCH", "/api/users/2").map((c) => c.body);
    expect(patches).toContainEqual({ enabled: false });
    expect(patches).toContainEqual({ role: "ADMIN" });
    expect(await screen.findByText("Phải còn ít nhất một ADMIN đang hoạt động")).toBeInTheDocument();
  });

  it("đặt lại mật khẩu: chỉ lưu được khi đủ 8 ký tự", async () => {
    const api = mockApi([loggedInAs(ADMIN), { path: "/api/users", body: USERS }, { method: "PATCH", path: "/api/users/2", body: USERS[1] }]);
    renderApp("/users");
    const rows = within(await screen.findByTestId("users-table")).getAllByRole("row").slice(1);
    await userEvent.click(within(rows[1]).getByRole("button", { name: "Đặt lại mật khẩu" }));
    await userEvent.type(screen.getByLabelText("Mật khẩu mới của manager1"), "short");
    expect(screen.getByRole("button", { name: "Lưu" })).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Mật khẩu mới của manager1"), "12345");
    await userEvent.click(screen.getByRole("button", { name: "Lưu" }));
    expect(api.called("PATCH", "/api/users/2").map((c) => c.body)).toContainEqual({ password: "short12345" });
  });
});

describe("trang Tài khoản của tôi", () => {
  beforeEach(() => setCsrfCookie("csrf-a"));
  afterEach(() => clearCookies());

  it("đổi mật khẩu gửi khóa snake_case kèm CSRF và báo thành công", async () => {
    const api = mockApi([loggedInAs(MANAGER), { method: "POST", path: "/api/auth/password", status: 204 }]);
    renderApp("/account");
    await userEvent.type(await screen.findByLabelText("Mật khẩu hiện tại"), "cu-cu-cu-cu");
    await userEvent.type(screen.getByLabelText(/Mật khẩu mới/), "moi-moi-moi");
    await userEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));
    expect(await screen.findByText("Đã đổi mật khẩu.")).toBeInTheDocument();
    const post = api.called("POST", "/api/auth/password")[0];
    expect(post.body).toEqual({ current_password: "cu-cu-cu-cu", new_password: "moi-moi-moi" });
    expect(post.headers.get("X-XSRF-TOKEN")).toBe("csrf-a");
  });

  it("mật khẩu hiện tại sai: hiện thông báo của backend", async () => {
    mockApi([loggedInAs(MANAGER), { method: "POST", path: "/api/auth/password", status: 400, body: { error: "BAD_REQUEST", message: "Mật khẩu hiện tại không đúng" } }]);
    renderApp("/account");
    await userEvent.type(await screen.findByLabelText("Mật khẩu hiện tại"), "sai-sai-sai");
    await userEvent.type(screen.getByLabelText(/Mật khẩu mới/), "moi-moi-moi");
    await userEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));
    expect(await screen.findByText("Mật khẩu hiện tại không đúng")).toBeInTheDocument();
    expect(screen.queryByText("Đã đổi mật khẩu.")).not.toBeInTheDocument();
  });
});
