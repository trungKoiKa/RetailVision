import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, apiFetch } from "../../shared/api/client";
import { Banner } from "../../shared/components/Banner";
import { Card } from "../../shared/components/Card";
import type { SettingsOverview, SettingsRequestView, SettingsValues } from "../../shared/types/api";
import { formatDateTime } from "../../shared/utils/format";
import { LIMITS, PILOT_DEFAULTS, toForm, validate, type FormValues, type SettingsField } from "./settings";

const POLL_PENDING_MS = 2000;
const POLL_IDLE_MS = 10000;

function describe(r: SettingsRequestView): { kind: "warn" | "error" | "ok"; text: string } {
  switch (r.status) {
    case "PENDING":
      return { kind: "warn", text: "Đang chờ edge xác nhận…" };
    case "UNCONFIRMED":
      return {
        kind: "warn",
        text: "Chưa xác nhận: edge không trả lời trong thời gian chờ. Ngưỡng có thể chưa được áp dụng; xem trạng thái thiết bị rồi thử lại.",
      };
    case "APPLIED":
      return { kind: "ok", text: `Edge đã áp dụng (revision ${r.applied_revision ?? "?"}).` };
    case "REJECTED":
      return { kind: "error", text: `Edge từ chối: ${r.reason ?? "không rõ lý do"}.` };
  }
}

export function SettingsCard() {
  const query = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiFetch<SettingsOverview>("/api/settings"),
    refetchInterval: (q) => (q.state.data?.latest?.status === "PENDING" ? POLL_PENDING_MS : POLL_IDLE_MS),
    retry: false,
  });
  const data = query.isError ? undefined : query.data;

  return (
    <Card title="Ngưỡng cảnh báo">
      {query.isError && <Banner kind="error">Không tải được ngưỡng hiện tại.</Banner>}
      {query.isPending && <p className="muted">Đang tải…</p>}
      {data && <SettingsForm key={data.edge_revision ?? "none"} overview={data} />}
    </Card>
  );
}

function SettingsForm({ overview }: { overview: SettingsOverview }) {
  const client = useQueryClient();
  const initial: SettingsValues = overview.current ?? PILOT_DEFAULTS;
  const [form, setForm] = useState<FormValues>(toForm(initial));
  const [localErrors, setLocalErrors] = useState<string[]>([]);

  const submit = useMutation({
    mutationFn: (values: SettingsValues) => apiFetch<SettingsRequestView>("/api/settings", { method: "PUT", body: JSON.stringify(values) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["settings"] }),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const { errors, values } = validate(form);
    setLocalErrors(errors);
    if (values) submit.mutate(values);
  }

  const latest = overview.latest;
  const status = latest ? describe(latest) : null;
  const serverError = submit.error instanceof ApiError ? (submit.error.serverMessage ?? "Không gửi được yêu cầu.") : submit.error ? "Không gửi được yêu cầu." : null;

  return (
    <>
      <p className="muted" data-testid="settings-source">
        {overview.current
          ? `Đang dùng ngưỡng đã đổi từ web (revision của edge: ${overview.edge_revision ?? "?"}).`
          : "Chưa đổi từ web: edge đang dùng giá trị trong file cấu hình của nó. Giá trị bên dưới là mặc định pilot, không phải giá trị đo được từ edge."}
      </p>
      {status && (
        <Banner kind={status.kind === "ok" ? "warn" : status.kind}>
          <span data-testid="settings-status">{status.text}</span>
        </Banner>
      )}
      {!overview.can_submit && overview.cannot_submit_reason && <p className="note">{overview.cannot_submit_reason}.</p>}

      <form onSubmit={onSubmit} className="form" noValidate>
        {(Object.keys(LIMITS) as SettingsField[]).map((field) => (
          <label key={field}>
            {LIMITS[field].label}
            <input
              inputMode="decimal"
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              aria-label={LIMITS[field].label}
            />
          </label>
        ))}
        {localErrors.length > 0 && (
          <ul className="errors" role="alert">
            {localErrors.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
        {serverError && <Banner kind="error">{serverError}</Banner>}
        <button type="submit" disabled={!overview.can_submit || submit.isPending}>
          {submit.isPending ? "Đang gửi…" : "Gửi tới edge"}
        </button>
      </form>

      {overview.history.length > 0 && (
        <details>
          <summary>Lịch sử yêu cầu ({overview.history.length})</summary>
          <table className="table">
            <thead>
              <tr>
                <th>Gửi lúc</th>
                <th>Bởi</th>
                <th>Kết quả</th>
              </tr>
            </thead>
            <tbody>
              {overview.history.map((r) => (
                <tr key={r.request_id}>
                  <td>{formatDateTime(r.requested_at)}</td>
                  <td>{r.requested_by}</td>
                  <td>{describe(r).text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </>
  );
}
