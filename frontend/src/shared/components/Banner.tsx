import type { ReactNode } from "react";

/** Dải cảnh báo đầu trang. `warn` = dữ liệu không tin cậy; `error` = không gọi được backend. */
export function Banner({ kind, children }: { kind: "warn" | "error"; children: ReactNode }) {
  return (
    <div className={`banner banner-${kind}`} role="alert">
      {children}
    </div>
  );
}
