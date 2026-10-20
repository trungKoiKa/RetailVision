-- Yêu cầu đổi ngưỡng từ web (P1). PENDING cho tới khi edge trả settings/result (APPLIED/REJECTED).
-- Không có dòng nào nghĩa là edge đang chạy theo giá trị trong file cấu hình của nó. request_id unique.
create table settings_revision (
    id                bigserial primary key,
    request_id        uuid          not null unique,
    expected_revision integer       not null check (expected_revision >= 0),
    dwell_seconds     numeric(6, 2) not null check (dwell_seconds between 0 and 60),
    on_count          integer       not null check (on_count between 1 and 100),
    on_hold_seconds   numeric(8, 2) not null check (on_hold_seconds between 0 and 3600),
    off_count         integer       not null check (off_count between 0 and 100),
    off_hold_seconds  numeric(8, 2) not null check (off_hold_seconds between 0 and 3600),
    status            varchar(10)   not null check (status in ('PENDING', 'APPLIED', 'REJECTED')),
    reason            text,
    applied_revision  integer,
    requested_by      text          not null,
    requested_at      timestamptz   not null,
    resolved_at       timestamptz
);

create index settings_revision_requested_at_idx on settings_revision (requested_at);
