import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../shared/api/client";
import { useAuth } from "../../shared/auth/AuthContext";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Tên đăng nhập hoặc mật khẩu không đúng.";
    if (error.status === 429) return "Sai quá nhiều lần. Thử lại sau vài phút.";
    if (error.status === 403) return "Phiên chưa sẵn sàng. Tải lại trang rồi thử lại.";
  }
  return "Không đăng nhập được. Kiểm tra kết nối tới backend.";
}

export function LoginPage() {
  const { auth, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (auth.status === "authenticated") return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <Card title="Đăng nhập RetailVision">
        {error && <Banner kind="error">{error}</Banner>}
        <form onSubmit={submit} className="form">
          <label>
            Tên đăng nhập
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required maxLength={64} />
          </label>
          <label>
            Mật khẩu
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </label>
          <button type="submit" disabled={busy || !username || !password}>
            {busy ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
        </form>
      </Card>
    </main>
  );
}
