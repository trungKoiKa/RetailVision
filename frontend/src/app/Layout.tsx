import { Activity, Bell, Cpu, LayoutDashboard, LogOut, TrendingUp, UserCog } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../shared/auth/AuthContext";
import { useSystemStatus } from "./useSystemStatus";

const TITLES: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Tổng quan", subtitle: "Tình hình vùng chờ và lượt vào/ra ngay lúc này" },
  "/footfall": { title: "Lượt vào/ra", subtitle: "Báo cáo theo giờ hoặc theo ngày, kèm độ phủ dữ liệu" },
  "/alerts": { title: "Cảnh báo", subtitle: "Lịch sử cảnh báo đông khách và xác nhận của nhân viên" },
  "/devices": { title: "Thiết bị", subtitle: "Trạng thái Pi, ESP32 và ngưỡng cảnh báo" },
  "/users": { title: "Tài khoản", subtitle: "Quản lý người dùng web" },
  "/account": { title: "Tài khoản của tôi", subtitle: "Đổi mật khẩu" },
};

export function Layout() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const status = useSystemStatus();
  const links = [
    { to: "/", label: "Tổng quan", icon: LayoutDashboard, end: true },
    { to: "/footfall", label: "Lượt vào/ra", icon: TrendingUp },
    { to: "/alerts", label: "Cảnh báo", icon: Bell },
    { to: "/devices", label: "Thiết bị", icon: Cpu },
    ...(auth.user?.role === "ADMIN" ? [{ to: "/users", label: "Tài khoản", icon: UserCog }] : []),
  ];
  const heading = TITLES[location.pathname] ?? { title: "RetailVision", subtitle: "" };
  const tone = status.tone;

  async function onLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Bỏ qua điều hướng
      </a>
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <Activity size={20} strokeWidth={2.5} />
          </span>
          <span>
            RetailVision
            <small>Giám sát lưu lượng khách</small>
          </span>
        </div>
        <nav aria-label="Điều hướng chính">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              <l.icon size={18} strokeWidth={2} aria-hidden="true" />
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className={`sys-status tone-${tone}`} role="status" aria-live="polite">
            <strong>Hệ thống</strong>
            <span className="sys-line">
              <span className="pulse" aria-hidden="true" />
              {status.label}
            </span>
            {status.detail && <span className="sys-detail">{status.detail}</span>}
          </div>
        </div>
      </aside>

      <div className="content">
        <header className="topbar">
          <div>
            <h1 className="page-title">{heading.title}</h1>
            {heading.subtitle && <p className="page-sub">{heading.subtitle}</p>}
          </div>
          <div className="topbar-right">
            <span className={`status-pill tone-${tone}`}>
              <span className="pulse" aria-hidden="true" />
              {status.label}
            </span>
            {auth.user && (
              <>
                <NavLink to="/account" className="user-chip" title="Đổi mật khẩu">
                  <span className="avatar" aria-hidden="true">
                    {auth.user.username.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="user-text">
                    {auth.user.username} ({auth.user.role})
                  </span>
                </NavLink>
                <button type="button" className="ghost" onClick={onLogout}>
                  <LogOut size={16} aria-hidden="true" />
                  <span>Đăng xuất</span>
                </button>
              </>
            )}
          </div>
        </header>
        <main id="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
