# 1. Yêu cầu

Tài liệu trả lời: hệ thống làm gì, cho ai, thế nào là đạt. Cách hiện thực xem [2-design.md](2-design.md).

## 1.1 Vấn đề

Điểm bán thiếu số liệu lượt đến theo giờ để xem lại cách bố trí ca, và nhân viên ở vị trí khác không nhận biết kịp khi vùng chờ thanh toán đông kéo dài. Hóa đơn không ghi được lượt ghé không mua; đếm người trong một ảnh không suy ra được lượt vào/ra.

RetailVision dùng **một camera** nhìn chéo thấy cả **một cửa** và **một vùng chờ**: Raspberry Pi đếm lượt qua cửa theo hướng, phát hiện vùng chờ đông kéo dài và báo tới ESP32 ở vị trí nhân viên hỗ trợ; Spring Boot + PostgreSQL + React lưu và hiển thị báo cáo trong LAN.

**Định nghĩa số liệu**

| Thuật ngữ | Nghĩa | Không phải |
| --- | --- | --- |
| Lượt vào/ra | Số lần người vượt vạch theo hướng | Số khách duy nhất, số người mua |
| Số người vùng chờ | Người có điểm chân trong đa giác đủ thời gian dwell | Thời gian chờ của từng khách |
| OVERLOAD | Vùng chờ ≥ ngưỡng đủ lâu | Quá sức chứa, mất an toàn |
| ACK | Nhân viên xác nhận đã thấy cảnh báo | Đã hỗ trợ xong |
| Coverage | Tỷ lệ thời gian có dữ liệu hợp lệ | — |

## 1.2 Người dùng

| Vai trò | Việc làm |
| --- | --- |
| MANAGER | Đăng nhập web, xem trạng thái/báo cáo/lịch sử, xuất CSV, đổi ngưỡng (P1) |
| ADMIN | Quyền MANAGER + quản lý tài khoản, xem thiết bị |
| Nhân viên hỗ trợ | Nhận đèn/còi trên ESP32, bấm ACK; không có tài khoản web |

## 1.3 Phạm vi

**Trong phạm vi:** một site, một camera USB, một cửa, một vùng chờ, một Pi 4 4 GB, một ESP32, một máy chủ LAN; chạy không cần Internet khi LAN còn.

**Ngoài phạm vi:** nhận dạng khuôn mặt/danh tính, nhiều camera/cửa hàng, POS, dự báo, ứng dụng di động, cloud, OTA, heatmap, lưu video ở chế độ vận hành.

**Điều kiện mặt bằng:** cửa và vùng chờ cùng nhìn rõ trong một khung hình; nếu không đạt thì địa điểm nằm ngoài phạm vi.

## 1.4 Luồng chính

1. Pi khởi động, đồng bộ giờ với máy chủ LAN, phát `state` mỗi giây; ESP32 vàng tới khi có state mới.
2. Người qua cửa → crossing event → Spring lưu một lần → web cập nhật lượt theo giờ.
3. Vùng chờ ≥ `on_count` người đủ `on_hold` giây → OVERLOAD: ESP32 đỏ nhấp nháy + còi.
4. Nhân viên bấm nút → Pi ghi ACK → còi tắt, đỏ sáng liên tục (vẫn đông).
5. Vùng chờ ≤ `off_count` đủ `off_hold` giây → kết thúc; web lưu lịch sử.
6. Mất camera → UNKNOWN, không báo 0 người. Tắt máy chủ → Pi/ESP32 vẫn cảnh báo, dữ liệu được bù khi máy chủ bật lại.

## 1.5 Yêu cầu chức năng

| ID | Mức | Yêu cầu | Nghiệm thu |
| --- | --- | --- | --- |
| FR-01 | P0 | Một camera, một lần suy luận mỗi frame dùng chung cho cửa và vùng chờ | Clip có người qua cửa khi vùng chờ có người cho kết quả cả hai nhánh |
| FR-02 | P0 | Đếm vào/ra theo hướng, chống dao động tại vạch | Vào/ra/quay đầu/đứng sát vạch khớp nhãn tay, mỗi lượt một event |
| FR-03 | P0 | Vùng chờ theo đa giác + dwell | Người đi ngang chưa đủ dwell không được tính |
| FR-04 | P0 | OVERLOAD bật/tắt theo hai ngưỡng + hold; UNKNOWN khi dữ liệu cũ | Test mốc biên và mất camera; ACK không đóng OVERLOAD |
| FR-05 | P0 | ESP32 hiện 4 trạng thái bằng LED/còi, gửi ACK theo `alert_id` | ACK lặp/sai alert không nhận nhầm; ACK mất được gửi lại |
| FR-06 | P0 | Spring lưu sự kiện MQTT idempotent | Cùng `event_id` hai lần → một bản ghi; ack broker chỉ sau commit |
| FR-07 | P0 | Web: Login, Overview, Footfall, Alerts, Devices | Dữ liệu thật từ API, không mock khi nghiệm thu |
| FR-08 | P0 | Đăng nhập session, phân quyền ADMIN/MANAGER kiểm ở API | Gọi thẳng API khi chưa đăng nhập/sai quyền bị từ chối |
| FR-09 | P1 | Đổi ngưỡng từ web, Pi xác nhận | Web giữ PENDING tới khi Pi trả APPLIED/REJECTED kèm lý do |
| FR-10 | P0 | Báo cáo giờ/ngày, coverage, CSV | Qua ranh giới giờ/ngày, restart, bản tin trùng, gap khớp nhãn |
| FR-11 | P0 | Cảnh báo khi máy chủ tắt; bù dữ liệu khi bật lại | Tắt máy chủ 5 phút, không mất, không trùng, gap thật hiện rõ |
| FR-12 | P1 | Preview ảnh từ Pi khi bật chế độ hiệu chuẩn/demo | Tắt chế độ thì ngừng phục vụ ảnh |
| FR-13 | P0 | Chạy edge từ file video; công cụ vẽ vạch/vùng ra YAML | Cùng clip hai lần cho cùng kết quả |

## 1.6 Yêu cầu phi chức năng

| ID | Nhóm | Mục tiêu |
| --- | --- | --- |
| NFR-01 | Hiệu năng | Pi 4 chạy cả hai chức năng; thử ≥3 FPS toàn luồng, chốt với giảng viên sau benchmark |
| NFR-02 | Độ đúng | Sai số mỗi hướng ≤10% (≤5% mở rộng); queue MAE ≤1 người trong 0–8 người |
| NFR-03 | Cảnh báo | Precision và recall ≥0,90, ghép sự kiện ±3 giây, công bố cỡ mẫu |
| NFR-04 | Độ trễ | p95 ảnh → state ≤1 giây; state → LED ≤1 giây; không tính dwell/hold |
| NFR-05 | Độ mới | ESP32 UNKNOWN sau 5 giây không có state; web hiện tuổi dữ liệu |
| NFR-06 | Ổn định | Chạy 2 giờ không crash; sau đó thử ≥4 giờ |
| NFR-07 | Bảo mật | Mỗi client MQTT một tài khoản + ACL; mật khẩu ngoài Git; không mở ra Internet |
| NFR-08 | Riêng tư | Chỉ lưu số liệu/sự kiện; track ID chỉ trong RAM; không lưu video vận hành |
| NFR-09 | Phục hồi | Bù dữ liệu trong giới hạn hàng đợi; vượt giới hạn thì báo gap |
| NFR-10 | Offline | Mất Internet ≥10 phút, LAN còn: mọi chức năng chạy |
| NFR-11 | Thời gian | Pi đồng bộ giờ qua máy chủ LAN; báo `clock_synced` |

Các ngưỡng là mục tiêu thử nghiệm, chưa phải kết quả. Kết quả cuối đo trên Pi thật, video có nhãn.

## 1.7 Cổng nghiệm thu MVP

1. Pi thật, một camera đồng thời đếm cửa và giám sát vùng chờ; có bảng so nhãn tay.
2. ESP32 ở vị trí khác nhận cảnh báo, ACK đúng alert, ACK không xóa tình trạng đông.
3. Web hiển thị dữ liệu thật, đăng nhập hai vai trò, phân quyền ở backend.
4. Tắt máy chủ mà Pi/ESP32 vẫn cảnh báo; bật lại không trùng, coverage đúng.
5. Mất camera/broker/node cho UNKNOWN, không hiện 0 như dữ liệu mới.
6. Có số đo FPS, độ trễ, độ đúng kèm phiên bản cấu hình.

Cách đo chi tiết: [evaluation/README.md](../evaluation/README.md).

## 1.8 Giới hạn kết luận

Camera RGB một góc nhạy với che khuất và người ở xa. Lượt vào/ra không cho biết chuyển đổi mua hàng. ACK không chứng minh nhân viên đã hỗ trợ hay thời gian chờ giảm. Thử nghiệm ở lab chỉ kết luận ở mức nguyên mẫu; không tuyên bố lợi thế chi phí hay độ chính xác so với sản phẩm thương mại.

## 1.9 Câu hỏi mở

| ID | Câu hỏi | Khi cần chốt |
| --- | --- | --- |
| OQ-01 | Mặt bằng thử nào thấy rõ cả cửa và vùng chờ? | Trước khi lắp |
| OQ-02 | Máy chủ LAN là laptop demo hay máy luôn bật? | Trước khi thử vận hành |
| OQ-03 | Ngưỡng FPS/độ đúng nghiệm thu cuối với giảng viên? | Sau benchmark |
| OQ-04 | Giá trị giới hạn hàng đợi broker, thời hạn giữ video nghiên cứu? | Trước test offline |
| OQ-06 | Có quyền quay thử tại cửa hàng hay chỉ dùng mô hình lab? | Trước khi thu dữ liệu |
| OQ-07 | Đồ án nhóm hay cá nhân, hạn nộp? | Trước khi chốt lịch |
