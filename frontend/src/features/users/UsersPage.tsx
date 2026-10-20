import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, apiFetch } from "../../shared/api/client";
import { useAuth } from "../../shared/auth/AuthContext";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import type { Role, UserView } from "../../shared/types/api";
import { formatDateTime } from "../../shared/utils/format";

const ROLE_TEXT: Record<Role, string> = { ADMIN: "Quản trị (ADMIN)", MANAGER: "Quản lý (MANAGER)" };

function errorText(e: unknown): string {
  return e instanceof ApiError ? (e.serverMessage ?? `Lỗi ${e.status}`) : "Không kết nối được backend.";
}

export function UsersPage() {
  const client = useQueryClient();
  const { auth } = useAuth();
  const list = useQuery({ queryKey: ["users"], queryFn: () => apiFetch<UserView[]>("/api/users"), retry: false });
  const refresh = () => client.invalidateQueries({ queryKey: ["users"] });

  const create = useMutation({
    mutationFn: (body: { username: string; password: string; role: Role }) =>
      apiFetch<UserView>("/api/users", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { role?: Role; enabled?: boolean; password?: string } }) =>
      apiFetch<UserView>(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: refresh,
  });

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("MANAGER");
  const [resetFor, setResetFor] = useState<number | null>(null);
  const [newPassword, setNewPassword] = useState("");

  function onCreate(e: FormEvent) {
    e.preventDefault();
    create.mutate(
      { username: username.trim(), password, role },
      {
        onSuccess: () => {
          setUsername("");
          setPassword("");
        },
      },
    );
  }

  const users = list.isError ? undefined : list.data;
  const error = create.error ?? update.error;

  return (
    <div className="page">
      <Card title="Tài khoản web">
        {list.isError && <Banner kind="error">{errorText(list.error)}</Banner>}
        {error && <Banner kind="error">{errorText(error)}</Banner>}
        {users && (
          <div className="scroll">
            <table className="table" data-testid="users-table">
              <thead>
                <tr>
                  <th>Tên đăng nhập</th>
                  <th>Vai trò</th>
                  <th>Trạng thái</th>
                  <th>Đăng nhập gần nhất</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>
                      <select
                        aria-label={`Vai trò của ${u.username}`}
                        value={u.role}
                        onChange={(e) => update.mutate({ id: u.id, body: { role: e.target.value as Role } })}
                      >
                        {(Object.keys(ROLE_TEXT) as Role[]).map((r) => (
                          <option key={r} value={r}>
                            {ROLE_TEXT[r]}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>{u.enabled ? "Đang hoạt động" : "Đã vô hiệu hóa"}</td>
                    <td>{formatDateTime(u.last_login_at)}</td>
                    <td className="actions">
                      <button
                        type="button"
                        onClick={() => update.mutate({ id: u.id, body: { enabled: !u.enabled } })}
                        disabled={u.username === auth.user?.username && u.enabled}
                        title={u.username === auth.user?.username ? "Không thể tự vô hiệu hóa" : undefined}
                      >
                        {u.enabled ? "Vô hiệu hóa" : "Kích hoạt"}
                      </button>
                      {resetFor === u.id ? (
                        <span>
                          <input
                            type="password"
                            aria-label={`Mật khẩu mới của ${u.username}`}
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            autoComplete="new-password"
                          />
                          <button
                            type="button"
                            disabled={newPassword.length < 8}
                            onClick={() =>
                              update.mutate(
                                { id: u.id, body: { password: newPassword } },
                                {
                                  onSuccess: () => {
                                    setResetFor(null);
                                    setNewPassword("");
                                  },
                                },
                              )
                            }
                          >
                            Lưu
                          </button>
                        </span>
                      ) : (
                        <button type="button" onClick={() => setResetFor(u.id)}>
                          Đặt lại mật khẩu
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Thêm tài khoản">
        <form onSubmit={onCreate} className="form">
          <label>
            Tên đăng nhập (a–z, 0–9, . _ -)
            <input value={username} onChange={(e) => setUsername(e.target.value)} required maxLength={32} autoComplete="off" />
          </label>
          <label>
            Mật khẩu (tối thiểu 8 ký tự)
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
          </label>
          <label>
            Vai trò
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {(Object.keys(ROLE_TEXT) as Role[]).map((r) => (
                <option key={r} value={r}>
                  {ROLE_TEXT[r]}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={create.isPending || !username || password.length < 8}>
            Tạo tài khoản
          </button>
        </form>
        <p className="muted">Tài khoản không bị xóa, chỉ vô hiệu hóa, để giữ lịch sử. Luôn còn ít nhất một ADMIN đang hoạt động.</p>
      </Card>
    </div>
  );
}
