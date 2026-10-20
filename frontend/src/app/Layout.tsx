import { NavLink, Outlet } from "react-router-dom";

const LINKS = [{ to: "/", label: "Tổng quan", end: true }];

export function Layout() {
  return (
    <>
      <header className="topbar">
        <strong className="brand">RetailVision</strong>
        <nav aria-label="Điều hướng chính">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "nav active" : "nav")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
