# Frontend (React)

React 19 + TypeScript + Vite 7, TanStack Query (polling), React Router. Chỉ gọi API của Spring cùng origin, không kết nối MQTT hay DB.

**Trạng thái:** Phần 7 và 10c: Đăng nhập, Tổng quan, Lượt vào/ra, Cảnh báo, Thiết bị + đổi ngưỡng, Tài khoản (ADMIN), Tài khoản của tôi. 59 test vitest. Đã chạy trên Chrome với backend thật, PostgreSQL, Mosquitto và edge Python thật (đăng nhập, báo cáo có khung xám, đổi ngưỡng được edge áp dụng).

## Chạy

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm test             # vitest
npm run typecheck
npm run build
```

`vite` chuyển tiếp `/api` tới `http://localhost:8080`; đổi bằng `VITE_API_TARGET` (ví dụ backend chạy ở cổng khác vì 8080 đã bị chiếm). Nếu 5173 đã có chương trình khác dùng, Vite tự chuyển sang cổng kế tiếp và in ra cổng thật.

## Trang

| Đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `/login` | công khai | Đăng nhập. Lấy cookie CSRF từ `GET /api/auth/me` trước khi gửi |
| `/` | MANAGER, ADMIN | Tổng quan (polling 2 s) |
| `/footfall` | MANAGER, ADMIN | Chọn khoảng ngày và gom giờ/ngày; biểu đồ, bảng chi tiết, độ phủ, tải CSV |
| `/alerts` | MANAGER, ADMIN | Lịch sử cảnh báo phân trang, độ trễ ACK |
| `/devices` | MANAGER, ADMIN | Trạng thái thiết bị và đổi ngưỡng (gửi tới edge, chờ xác nhận) |
| `/users` | ADMIN | Tạo, đổi vai trò, vô hiệu hóa, đặt lại mật khẩu |
| `/account` | đã đăng nhập | Đổi mật khẩu của mình |

Quyền được kiểm ở backend; web chỉ ẩn mục và chặn trang để dễ dùng. API trả 401 (phiên hết hạn) thì web tự về trang đăng nhập; đăng nhập/đăng xuất xóa dữ liệu đã tải của phiên trước.

## Quy tắc hiển thị

- Số người `null` (UNKNOWN hoặc state cũ) hiện **"—"**, không bao giờ hiện 0.
- Quá 5 giây không có state: banner "Không có dữ liệu tin cậy" kèm tuổi state cuối.
- Không gọi được backend: banner đỏ, mọi số liệu thành "—" (không dùng lại số cũ như dữ liệu sống), thẻ cảnh báo cũng "—" thay vì "chưa có cảnh báo".
- OVERLOAD đã ACK nói rõ "vẫn đông, cảnh báo chưa kết thúc".
- Thời gian lưu là UTC, hiển thị theo giờ `Asia/Ho_Chi_Minh`. Tuổi dữ liệu luôn hiện.
- Báo cáo: khung thiếu dữ liệu (`gap`) tô xám và ghi "Thiếu dữ liệu", ô Vào/Ra hiện "—", biểu đồ không vẽ cột; khung chưa tới ghi "Chưa tới". Tổng chỉ cộng các khung có số liệu và nói rõ có bao nhiêu khung thiếu. Độ phủ dưới 90% được đánh dấu.
- Đổi ngưỡng: kiểm giá trị ngay trên web (khớp contract; `off < on`) trước khi gửi; hiện đúng bốn trạng thái PENDING, APPLIED, REJECTED (kèm lý do), UNCONFIRMED (không nói là đã áp dụng). Khi chưa từng đổi từ web, giá trị điền sẵn là mặc định pilot và được ghi rõ là không phải số đo từ edge.
- Lỗi tải dữ liệu luôn hiện banner lỗi, không bao giờ nói thành "không có dữ liệu".
- Biểu đồ (Recharts) được nạp theo yêu cầu, gói chính khoảng 320 kB.
