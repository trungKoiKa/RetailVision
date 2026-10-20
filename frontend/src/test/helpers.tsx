import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthProvider } from "../shared/auth/AuthContext";
import { AppRoutes } from "../routes/AppRoutes";
import type { Me } from "../shared/types/api";

export interface Call {
  method: string;
  url: string;
  headers: Headers;
  body: unknown;
}

export interface Route {
  method?: string; // mặc định GET
  path: string | RegExp;
  status?: number | ((call: Call) => number);
  /** Giá trị trả về, hoặc hàm nhận request để trả khác nhau theo lần gọi. */
  body?: unknown | ((call: Call) => unknown);
}

function matches(route: Route, call: Call): boolean {
  if ((route.method ?? "GET") !== call.method) return false;
  const path = call.url.split("?")[0];
  return typeof route.path === "string" ? path === route.path || call.url === route.path : route.path.test(call.url);
}

/** Giả lập fetch theo bảng route; gọi tới route không khai báo thì ném lỗi để test không âm thầm chạy sai. */
export function mockApi(routes: Route[]) {
  const calls: Call[] = [];
  const handler = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const call: Call = {
      method: (init?.method ?? "GET").toUpperCase(),
      url: String(input),
      headers: new Headers(init?.headers),
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    };
    calls.push(call);
    const route = [...routes].reverse().find((r) => matches(r, call)); // khai báo sau thắng
    if (!route) throw new Error(`mockApi: chưa khai báo ${call.method} ${call.url}`);
    const payload = typeof route.body === "function" ? (route.body as (c: Call) => unknown)(call) : route.body;
    const status = typeof route.status === "function" ? route.status(call) : (route.status ?? 200);
    return new Response(status === 204 || payload === undefined ? null : JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", handler);
  return { calls, handler, called: (method: string, path: string) => calls.filter((c) => c.method === method && c.url.split("?")[0] === path) };
}

export function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: false } } });
}

/** Dựng cả ứng dụng (định tuyến + đăng nhập) tại một đường dẫn. */
export function renderApp(path: string, client: QueryClient = newClient()) {
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <MemoryRouter initialEntries={[path]}>
            <AppRoutes />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    ),
  };
}

export const MANAGER: Me = { username: "manager1", role: "MANAGER" };
export const ADMIN: Me = { username: "admin1", role: "ADMIN" };

export function loggedInAs(me: Me): Route {
  return { path: "/api/auth/me", body: me };
}

export function setCsrfCookie(value = "token-123") {
  document.cookie = `XSRF-TOKEN=${value}; path=/`;
}

export function clearCookies() {
  document.cookie = "XSRF-TOKEN=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
}
