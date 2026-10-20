-- Telemetry mỗi phút: valid_seconds là độ phủ quan sát. Phút không có dòng nào là gap, không phải 0.
create table telemetry_minute (
    id                 bigserial primary key,
    event_id           uuid        not null unique,
    session_id         uuid        not null references edge_session (session_id),
    seq                bigint      not null,
    minute_start       timestamptz not null,
    valid_seconds      integer     not null check (valid_seconds between 0 and 60),
    queue_avg          numeric(8, 2),
    queue_max          integer,
    fps                numeric(8, 2) not null,
    frame_age_ms       integer     not null,
    server_received_at timestamptz not null default now(),
    unique (session_id, seq)
);

create index telemetry_minute_start_idx on telemetry_minute (minute_start);

-- Trạng thái mới nhất của edge01 và node01 (từ topic status, retained).
create table device_status (
    device_id     text primary key,
    site_id       text        not null,
    status        varchar(8)  not null check (status in ('ONLINE', 'OFFLINE')),
    version       text        not null,
    clock_synced  boolean     not null,
    reported_at   timestamptz not null,
    last_seen_at  timestamptz not null
);
