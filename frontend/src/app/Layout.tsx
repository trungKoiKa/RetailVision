import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../shared/auth/AuthContext";
import { useSystemStatus } from "./useSystemStatus";

export function Layout() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();
  const status = useSystemStatus();
  const links = [
    { to: "/", label: "Tổng quan", end: true },
    { to: "/footfall", label: "Lượt vào/ra" },
    { to: "/alerts", label: "Cảnh báo" },
    { to: "/devices", label: "Thiết bị" },
    ...(auth.user?.role === "ADMIN" ? [{ to: "/users", label: "Tài khoản" }] : []),
  ];

  async function onLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  const dot = status.tone === "ok" ? "dot-online" : status.tone === "bad" ? "dot-offline" : "dot-unknown";

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Bỏ qua điều hướng
      </a>
      <aside className="sidebar">
        <div className="brand">
          RetailVision
          <small>Giám sát lưu lượng khách</small>
        </div>
        <nav aria-label="Điều hướng chính">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="sys-status" role="status" aria-live="polite">
            <strong>Hệ thống</strong>
            <span>
              <span className={`dot ${dot}`} aria-hidden="true" />
              {status.label}
            </span>
            {status.detail && <span className="muted">{status.detail}</span>}
          </div>
          {auth.user && (
            <div className="who">
              <NavLink to="/account" className="nav" title="Đổi mật khẩu">
                {auth.user.username} ({auth.user.role})
              </NavLink>
              <button type="button" onClick={onLogout}>
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </aside>
      <div className="content">
        <div className="mobile-bar">
          <span>
            <span className={`dot ${dot}`} aria-hidden="true" />
            <strong className="mobile-brand">RetailVision</strong> <span className="muted">{status.label}</span>
          </span>
          {auth.user && (
            <span className="mobile-actions">
              <NavLink to="/account" className="nav" title="Đổi mật khẩu">
                {auth.user.username}
              </NavLink>
              <button type="button" onClick={onLogout}>
                Đăng xuất
              </button>
            </span>
          )}
        </div>
        <main id="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
