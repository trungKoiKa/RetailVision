import { Route, Routes } from "react-router-dom";
import { Layout } from "../app/Layout";
import { OverviewPage } from "../features/overview/OverviewPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="*" element={<p className="page muted">Không tìm thấy trang.</p>} />
      </Route>
    </Routes>
  );
}
