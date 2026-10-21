import { useOverview } from "../features/overview/useOverview";
import { formatAge } from "../shared/utils/format";

export type SystemStatus = { tone: "ok" | "warn" | "bad"; label: string; detail: string };

/** Một dòng trạng thái hệ thống luôn hiện ở khung ngoài: lấy từ cùng truy vấn Tổng quan, không gọi thêm API. */
export function useSystemStatus(): SystemStatus {
  const query = useOverview();
  if (query.isError) return { tone: "bad", label: "Mất kết nối backend", detail: "Số liệu không phải hiện tại" };
  if (!query.data) return { tone: "warn", label: "Đang tải", detail: "" };
  const { live, devices } = query.data;
  const edge = devices.find((d) => d.device_id === "edge01");
  if (live.stale || live.state === "UNKNOWN") {
    return {
      tone: "warn",
      label: "Không có dữ liệu tin cậy",
      detail: live.age_seconds !== null ? `Tin cuối cách ${formatAge(live.age_seconds)}` : edge?.status === "ONLINE" ? "Edge online, chưa có state" : "Chưa có state",
    };
  }
  return { tone: "ok", label: "Đang nhận dữ liệu", detail: `Tuổi dữ liệu ${formatAge(live.age_seconds)}` };
}
