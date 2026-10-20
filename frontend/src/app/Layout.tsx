import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../shared/auth/AuthContext";

export function Layout() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();
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

  return (
    <>
      <header className="topbar">
        <strong className="brand">RetailVision</strong>
        <nav aria-label="Điều hướng chính">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
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
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
