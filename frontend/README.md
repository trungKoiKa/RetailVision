# Frontend (React)

React 19 + TypeScript + Vite 7, TanStack Query (polling), React Router. Chỉ gọi API của Spring cùng origin, không kết nối MQTT hay DB.

**Trạng thái:** Phần 7 (trang Tổng quan). Đã chạy với backend và dữ liệu thật qua Mosquitto/PostgreSQL, kiểm trên Chrome. Các trang Footfall, Alerts, Devices, Login thuộc Phần 10.

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

## Quy tắc hiển thị

- Số người `null` (UNKNOWN hoặc state cũ) hiện **"—"**, không bao giờ hiện 0.
- Quá 5 giây không có state: banner "Không có dữ liệu tin cậy" kèm tuổi state cuối.
- Không gọi được backend: banner đỏ, mọi số liệu thành "—" (không dùng lại số cũ như dữ liệu sống), thẻ cảnh báo cũng "—" thay vì "chưa có cảnh báo".
- OVERLOAD đã ACK nói rõ "vẫn đông, cảnh báo chưa kết thúc".
- Thời gian lưu là UTC, hiển thị theo giờ `Asia/Ho_Chi_Minh`. Tuổi dữ liệu luôn hiện.
