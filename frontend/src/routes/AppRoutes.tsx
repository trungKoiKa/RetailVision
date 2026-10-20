import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "../app/Layout";
import { AccountPage } from "../features/auth/AccountPage";
import { LoginPage } from "../features/auth/LoginPage";
import { AlertsPage } from "../features/alerts/AlertsPage";
import { DevicesPage } from "../features/devices/DevicesPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { UsersPage } from "../features/users/UsersPage";
import { RequireAuth } from "../shared/auth/RequireAuth";

// Recharts chiếm phần lớn dung lượng: chỉ nạp khi mở trang biểu đồ
const FootfallPage = lazy(() => import("../features/footfall/FootfallPage").then((m) => ({ default: m.FootfallPage })));

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route
          path="footfall"
          element={
            <Suspense fallback={<p className="page muted">Đang tải…</p>}>
              <FootfallPage />
            </Suspense>
          }
        />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route
          path="users"
          element={
            <RequireAuth role="ADMIN">
              <UsersPage />
            </RequireAuth>
          }
        />
        <Route path="account" element={<AccountPage />} />
        <Route path="*" element={<p className="page muted">Không tìm thấy trang.</p>} />
      </Route>
    </Routes>
  );
}
