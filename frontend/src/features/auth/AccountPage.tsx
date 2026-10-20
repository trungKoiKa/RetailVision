import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, apiFetch } from "../../shared/api/client";
import { useAuth } from "../../shared/auth/AuthContext";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";

export function AccountPage() {
  const { auth } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const change = useMutation({
    mutationFn: () => apiFetch<void>("/api/auth/password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) }),
    onSuccess: () => {
      setCurrent("");
      setNext("");
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    change.mutate();
  }

  const error = change.error instanceof ApiError ? (change.error.serverMessage ?? `Lỗi ${change.error.status}`) : change.error ? "Không kết nối được backend." : null;

  return (
    <div className="page">
      <Card title="Tài khoản của tôi">
        <p>
          <strong>{auth.user?.username}</strong> ({auth.user?.role})
        </p>
        {change.isSuccess && <Banner kind="warn">Đã đổi mật khẩu.</Banner>}
        {error && <Banner kind="error">{error}</Banner>}
        <form onSubmit={onSubmit} className="form">
          <label>
            Mật khẩu hiện tại
            <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
          </label>
          <label>
            Mật khẩu mới (tối thiểu 8 ký tự)
            <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required minLength={8} />
          </label>
          <button type="submit" disabled={change.isPending || !current || next.length < 8}>
            Đổi mật khẩu
          </button>
        </form>
      </Card>
    </div>
  );
}
