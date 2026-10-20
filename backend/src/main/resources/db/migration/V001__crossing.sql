-- Phiên chạy của edge và lượt qua vạch. event_id unique để chống trùng bản tin QoS 1.
create table edge_session (
    session_id     uuid primary key,
    device_id      text        not null,
    started_at     timestamptz not null,
    config_version text        not null
);

create table crossing_event (
    id                 bigserial primary key,
    event_id           uuid        not null unique,
    session_id         uuid        not null references edge_session (session_id),
    seq                bigint      not null,
    direction          varchar(3)  not null check (direction in ('IN', 'OUT')),
    line_id            text        not null,
    track_id           integer     not null,
    profile            varchar(8)  not null check (profile in ('pilot', 'demo')),
    occurred_at        timestamptz not null,
    server_received_at timestamptz not null default now()
);

create index crossing_event_occurred_at_idx on crossing_event (occurred_at);
