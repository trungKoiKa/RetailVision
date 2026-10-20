-- Tài khoản web. Mật khẩu lưu dạng BCrypt. Tài khoản bị vô hiệu hóa (enabled = false) thay vì xóa để giữ lịch sử.
create table app_user (
    id            bigserial primary key,
    username      text         not null unique check (username = lower(username)),
    password_hash text         not null,
    role          varchar(16)  not null check (role in ('ADMIN', 'MANAGER')),
    enabled       boolean      not null default true,
    created_at    timestamptz  not null default now(),
    last_login_at timestamptz
);
