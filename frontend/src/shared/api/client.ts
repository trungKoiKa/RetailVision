/** Gọi API cùng origin, kèm cookie phiên. Lỗi HTTP được ném thành ApiError. */

export class ApiError extends Error {
  readonly status: number;
  /** Thông báo backend trả về (tiếng Việt, hiển thị được cho người dùng), nếu có. */
  readonly serverMessage: string | null;

  constructor(status: number, message: string, serverMessage: string | null = null) {
    super(message);
    this.status = status;
    this.serverMessage = serverMessage;
  }
}

/** Sự kiện phát ra khi API trả 401, để giao diện chuyển về trang đăng nhập. */
export const UNAUTHORIZED_EVENT = "rv:unauthorized";

function csrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const token = csrfToken();
    if (token) headers.set("X-XSRF-TOKEN", token);
  }
  const response = await fetch(path, { ...init, method, headers, credentials: "include" });
  if (response.status === 401) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!response.ok) {
    let serverMessage: string | null = null;
    try {
      const body = (await response.json()) as { message?: unknown };
      if (typeof body.message === "string") serverMessage = body.message;
    } catch {
      // không phải JSON: bỏ qua
    }
    throw new ApiError(response.status, `${method} ${path} -> ${response.status}`, serverMessage);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
