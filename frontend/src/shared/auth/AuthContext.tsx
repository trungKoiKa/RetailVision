import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { ApiError, UNAUTHORIZED_EVENT, apiFetch } from "../api/client";
import type { Me } from "../types/api";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "anonymous"; user: null }
  | { status: "authenticated"; user: Me };

interface AuthContextValue {
  auth: AuthState;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const ME_KEY = ["me"];

/** Bỏ dữ liệu của mọi truy vấn khác (của phiên trước), nhưng giữ truy vấn "me" để giao diện vẫn theo dõi nó. */
function dropSessionData(client: ReturnType<typeof useQueryClient>) {
  client.removeQueries({ predicate: (q) => q.queryKey[0] !== ME_KEY[0] });
}

/**
 * Trạng thái đăng nhập lấy từ GET /api/auth/me. Lần gọi này cũng làm backend gửi cookie XSRF-TOKEN (kể cả khi 401),
 * cần có trước khi đăng nhập.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const me = useQuery({
    queryKey: ME_KEY,
    queryFn: async (): Promise<Me | null> => {
      try {
        return await apiFetch<Me>("/api/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    retry: false,
    staleTime: 60_000,
  });

  // Bất kỳ API nào trả 401 (phiên hết hạn, bị đăng xuất nơi khác): coi như đã đăng xuất.
  useEffect(() => {
    const onUnauthorized = () => client.setQueryData(ME_KEY, null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [client]);

  const login = useCallback(
    async (username: string, password: string) => {
      const user = await apiFetch<Me>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      dropSessionData(client);
      client.setQueryData(ME_KEY, user);
    },
    [client],
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch<void>("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
    } finally {
      dropSessionData(client); // không để lại dữ liệu của người đã đăng xuất
      client.setQueryData(ME_KEY, null);
    }
  }, [client]);

  const auth: AuthState = me.isPending
    ? { status: "loading", user: null }
    : me.data
      ? { status: "authenticated", user: me.data }
      : { status: "anonymous", user: null };

  const value = useMemo(() => ({ auth, login, logout }), [auth.status, auth.user?.username, auth.user?.role, login, logout]); // eslint-disable-line react-hooks/exhaustive-deps
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth phải nằm trong AuthProvider");
  return ctx;
}
