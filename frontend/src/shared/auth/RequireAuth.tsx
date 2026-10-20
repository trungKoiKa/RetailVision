import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { Role } from "../types/api";
import { useAuth } from "./AuthContext";

/** Chưa đăng nhập thì chuyển tới /login (nhớ trang đang xem); có `role` thì còn kiểm quyền (backend vẫn kiểm lại). */
export function RequireAuth({ children, role }: { children: ReactNode; role?: Role }) {
  const { auth } = useAuth();
  const location = useLocation();
  if (auth.status === "loading") return <p className="page muted">Đang tải…</p>;
  if (auth.status === "anonymous") return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (role && auth.user.role !== role) {
    return (
      <p className="page" role="alert">
        Bạn không có quyền xem trang này.
      </p>
    );
  }
  return <>{children}</>;
}
