# Kịch bản video demo (3–5 phút)

Video chưa được quay. Đây là dàn ý để quay khi có phần cứng; mọi số hiển thị phải là số thật của lần quay đó.

| Phút | Cảnh | Nội dung |
| --- | --- | --- |
| 0:00 | Sơ đồ | Camera → Pi → ESP32 / máy chủ; không lưu video |
| 0:30 | Cửa | Người đi vào/ra, web Tổng quan tăng IN/OUT |
| 1:15 | Vùng chờ | Đủ người quá thời gian giữ → OVERLOAD, đèn đỏ + còi, web đổi trạng thái |
| 2:00 | ACK | Nhân viên bấm nút: còi tắt, đèn vẫn đỏ vì chưa hết đông; web ghi giờ ACK |
| 2:30 | Hết đông | NORMALIZED sau thời gian giữ, đèn xanh |
| 3:00 | Mất dữ liệu | Rút camera → UNKNOWN (đèn vàng, web "—", không hiện 0); cắm lại tự hồi phục |
| 3:45 | Báo cáo | Trang Lưu lượng: giờ thiếu dữ liệu tô xám; xuất CSV |
| 4:15 | Giới hạn | Nêu số đo thật (FPS, sai số) và những gì chưa đạt |

Khi không có phần cứng: chạy `compose.demo.yaml` (xem README gốc) và nói rõ đây là dữ liệu giả lập.
