-- alert_transition: mọi bản tin OPEN/ACK/END (chống trùng theo event_id).
-- alert_event: một dòng mỗi cảnh báo, gộp từ các transition. ACK không đóng cảnh báo.
create table alert_event (
    id               bigserial primary key,
    alert_id         uuid        not null unique,
    session_id       uuid        not null references edge_session (session_id),
    opened_at        timestamptz not null,
    open_queue_count integer,
    acked_at         timestamptz,
    ack_device_id    text,
    ended_at         timestamptz,
    end_reason       varchar(16) check (end_reason in ('NORMALIZED', 'INTERRUPTED', 'CONFIG_CHANGED'))
);

create index alert_event_opened_at_idx on alert_event (opened_at);

create table alert_transition (
    id                 bigserial primary key,
    event_id           uuid        not null unique,
    alert_id           uuid        not null,
    session_id         uuid        not null references edge_session (session_id),
    seq                bigint      not null,
    transition         varchar(8)  not null check (transition in ('OPEN', 'ACK', 'END')),
    ack_id             uuid,
    occurred_at        timestamptz not null,
    server_received_at timestamptz not null default now()
);

create index alert_transition_alert_id_idx on alert_transition (alert_id);
