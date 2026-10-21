import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type Tone = "blue" | "green" | "violet" | "amber" | "red" | "slate";

/** Ô số liệu lớn: icon màu, nhãn, giá trị, ghi chú. Giá trị luôn do nơi gọi quyết định (không biết thì truyền "—"). */
export function KpiCard({
  icon: Icon,
  tone,
  label,
  value,
  valueTestId,
  hint,
  extra,
  className = "",
}: {
  icon: LucideIcon;
  tone: Tone;
  label: string;
  value: ReactNode;
  valueTestId?: string;
  hint?: ReactNode;
  extra?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`kpi ${className}`.trim()}>
      <div className="kpi-top">
        <span className={`kpi-icon tone-${tone}`} aria-hidden="true">
          <Icon size={22} strokeWidth={2} />
        </span>
        <h2 className="kpi-label">{label}</h2>
        {extra}
      </div>
      <div className="kpi-value" data-testid={valueTestId}>
        {value}
      </div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </section>
  );
}
