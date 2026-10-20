# Máy chủ LAN (Compose)

PostgreSQL + backend Spring + web (nginx). Mosquitto chạy trên Pi ([../pi/mosquitto/README.md](../pi/mosquitto/README.md)). Web chỉ có một cổng (`WEB_PORT`, mặc định 8088); nginx chuyển `/api` tới backend nên trình duyệt dùng một origin, cookie phiên và CSRF hoạt động không cần CORS. PostgreSQL không mở cổng ra ngoài.

**Trạng thái kiểm chứng:** đã dựng, chạy chế độ demo (broker + edge giả) từ một bản clone sạch trên Windows + Docker Desktop, đăng nhập và thấy số liệu thật qua web, sao lưu rồi khôi phục vào CSDL mới. Chưa chạy với Pi thật, chưa chạy trên Linux và chưa cấu hình HTTPS.

## Chạy thử không cần Pi (demo)

```bash
cp deploy/server/.env.example deploy/server/.env          # có thể giữ nguyên các giá trị giả để thử
docker compose --env-file deploy/server/.env -f deploy/server/compose.yaml -f deploy/server/compose.demo.yaml up -d --build
```

Mở `http://localhost:8088`, đăng nhập bằng `RV_ADMIN_USER` / `RV_ADMIN_PASS` trong `.env`. Edge giả phát kịch bản NORMAL → OVERLOAD (40 giây) → NORMAL, lặp mỗi 90 giây; trang Tổng quan, Cảnh báo, Thiết bị cập nhật theo. Dừng và xóa dữ liệu: `docker compose -p retailvision down -v`.

Chế độ demo dùng broker không mật khẩu: **không dùng để vận hành**. Số liệu là giả lập, không phải đo từ camera.

## Vận hành thật

```bash
cp deploy/server/.env.example deploy/server/.env
# sửa: POSTGRES_PASSWORD, RV_MQTT_HOST (IP của Pi), RV_MQTT_BACKEND_PASS (mật khẩu backend01 đặt trên Pi), RV_ADMIN_PASS
docker compose --env-file deploy/server/.env -f deploy/server/compose.yaml up -d --build
```

- Mọi bí mật nằm trong `deploy/server/.env` (đã `.gitignore`); Compose từ chối chạy nếu thiếu `POSTGRES_PASSWORD` hoặc `RV_MQTT_HOST`.
- Đăng nhập ADMIN đầu tiên rồi **đổi mật khẩu** (trang "Tài khoản của tôi"). `RV_ADMIN_*` chỉ tạo tài khoản khi bảng còn rỗng; sau đó có thể xóa khỏi `.env`.
- Cookie phiên chưa bật `Secure` vì LAN dùng HTTP. Nếu đặt sau HTTPS, bật `server.servlet.session.cookie.secure` cho backend.
- Mất kết nối tới Pi: backend tự nối lại; web báo "không có dữ liệu tin cậy" thay vì hiện số cũ.
- Cập nhật: `git pull` rồi chạy lại lệnh `up -d --build`; Flyway tự áp dụng migration mới.

## Sao lưu và khôi phục

```bash
bash deploy/server/scripts/backup.sh ./backups 14          # Linux/macOS/Git Bash
powershell -File deploy\server\scripts\backup.ps1 -Dest .\backups -KeepDays 14   # Windows
```

Mỗi lần sao lưu tạo `retailvision_<thời gian>.dump` (định dạng custom của `pg_dump`), tự kiểm file đọc được bằng `pg_restore --list` và xóa bản cũ hơn số ngày giữ. Nên đặt vào Task Scheduler/cron hằng ngày và chép bản sao sang ổ khác.

**Thử khôi phục** (không đụng dữ liệu đang chạy):

```bash
bash deploy/server/scripts/restore.sh ./backups/retailvision_xxx.dump            # vào CSDL mới 'retailvision_restore'
powershell -File deploy\server\scripts\restore.ps1 -File .\backups\retailvision_xxx.dump
```

Khôi phục thật đè lên CSDL đang dùng: dừng backend (`docker compose -p retailvision stop backend web`), chạy với `--target-db retailvision --force` (Windows: `-TargetDb retailvision -Force`), rồi bật lại. Dữ liệu từ lúc sao lưu đến lúc sự cố bị mất, trừ phần broker còn giữ cho backend (phiên cleanSession=false) sẽ được bù khi backend nối lại.
