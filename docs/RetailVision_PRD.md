# RetailVision Edge — Tài liệu yêu cầu sản phẩm (PRD)

> **Trạng thái:** Dự thảo phục vụ triển khai và bảo vệ đồ án  
> **Phiên bản:** 0.2 — 17/10/2026  
> **Phạm vi:** một điểm bán hoặc mô hình thử; một camera cố định quan sát một cửa và một vùng chờ thanh toán  
> **Tài liệu kỹ thuật đi kèm:** `TrienKhai.md`, `RetailVision_Ke_Hoach.md`  
> **Quyết định kỹ thuật ràng buộc:** [ADR-0001](./decisions/0001-hop-nhat-quyet-dinh-ky-thuat.md) — khi PRD mâu thuẫn với ADR, theo ADR  
> **Cơ sở bố cục:** PRD EDUA Physics do người dùng cung cấp; nội dung yêu cầu sản phẩm dưới đây được viết riêng cho RetailVision.

## 1. Kiểm soát tài liệu

### 1.1 Mục đích

PRD định nghĩa vấn đề, người dùng, mục tiêu, luồng sử dụng, yêu cầu có ID, dữ liệu, tiêu chí nghiệm thu và giới hạn kết luận của nguyên mẫu RetailVision. Đây là tài liệu để viết task thiết kế, backend, firmware, frontend và đánh giá; kế hoạch triển khai chi tiết là tài liệu kỹ thuật riêng.

### 1.2 Cách đọc mức ưu tiên

| Mức | Ý nghĩa                                                                               |
| --- | ------------------------------------------------------------------------------------- |
| P0  | Thiếu yêu cầu này thì chưa hoàn thành MVP đồ án                                       |
| P1  | Cần cho trải nghiệm/đánh giá hoàn chỉnh; có thể thu gọn khi thiếu thời gian và ghi rõ |
| P2  | Hướng nâng cao, không phải điều kiện nghiệm thu MVP                                   |

Các ngưỡng tốc độ/độ chính xác trong PRD là **mục tiêu thử nghiệm đề xuất**, chưa phải hiệu năng đã chứng minh. Kết quả cuối dựa trên video có nhãn và phần cứng thật; khóa profile pilot và test trước khi đo chính thức.

## 2. Định nghĩa sản phẩm

### 2.1 Tóm tắt

RetailVision là hệ thống IoT hỗ trợ điểm bán nhận biết lưu lượng khách theo giờ và tình trạng vùng chờ thanh toán. Camera USB kết nối Raspberry Pi; Pi xử lý hình ảnh tại chỗ, theo dõi người tạm thời, ghi nhận lượt qua một cửa và phát hiện vùng chờ đông đủ lâu. ESP32 đặt ở vị trí nhân viên hỗ trợ hiển thị yêu cầu bằng LED và còi, cho phép xác nhận đã nhận. Web React cho quản lý xem báo cáo và quản trị hệ thống; Spring Boot lưu dữ liệu đã nhận qua MQTT vào PostgreSQL trên máy chủ LAN.

### 2.2 Giá trị và kết quả mong muốn

- Quản lý xem giờ có lưu lượng cao với phần thời gian quan sát hợp lệ để tham khảo bố trí ca.
- Người ở vị trí khác quầy nhận yêu cầu kiểm tra khi vùng chờ đông kéo dài và xác nhận đã nhận.
- Khi máy chủ web tạm tắt, Pi và ESP32 tiếp tục cảnh báo qua broker trên Pi; các sự kiện chưa được ghi PostgreSQL được broker giữ trong hàng đợi persistent session và bù khi máy chủ hoạt động trở lại, trong giới hạn hàng đợi đã công bố.
- Báo cáo phân biệt số lượt qua cửa, số người đang được tính trong vùng chờ.

### 2.3 Vai trò

| Vai trò                          | Công việc và quyền trong MVP                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Quản lý cửa hàng (MANAGER)       | Đăng nhập, xem trạng thái/báo cáo/lịch sử, xuất CSV, thay ngưỡng được phép trong site của mình (P1)    |
| Quản trị hệ thống (ADMIN)        | Quản lý tài khoản, thiết bị, cấu hình hệ thống và xem trạng thái dữ liệu                               |
| Nhân viên hỗ trợ                 | Nhận tín hiệu trên ESP32, bấm nút ACK đúng sự kiện; không cần tài khoản web ở MVP                      |
| Pi edge / ESP32 / Spring backend | Tác nhân hệ thống dùng danh tính MQTT khác nhau; không phải người dùng web                             |

## 3. Vấn đề và cơ hội

### 3.1 Phát biểu vấn đề

Một điểm bán có thể thiếu số liệu đáng tin về lượt đến theo giờ để xem lại việc bố trí nhân sự; nhân viên ở vị trí khác cũng có thể không nhận biết kịp tình trạng đông kéo dài tại quầy. Hóa đơn không ghi được mọi lượt đến, còn đếm người trong một ảnh không thể tự suy ra lượt khách ra/vào. Hệ thống cần đo đúng hai loại thông tin và đưa cảnh báo đến người có thể hỗ trợ, trong điều kiện một góc camera quan sát được cả cửa và vùng chờ.

### 3.2 Giả thuyết cần kiểm chứng

Nếu hệ thống đo được lượt qua cửa theo hướng và vùng chờ đông kéo dài với sai số có thể chấp nhận, người quản lý có cơ sở xem lại giờ cao điểm và người nhận cảnh báo có thể biết lúc nào cần kiểm tra.

### 3.3 Điều kiện triển khai

Camera cố định; một cửa và vùng khách chờ nhìn rõ trong cùng khung hình; có nguồn cho Pi/ESP32 và router LAN; có người nhận cảnh báo. Nếu quầy bị tường/kệ che hoặc cửa quá xa làm người nhỏ, địa điểm đó chưa phù hợp phạm vi một camera.

## 4. Mục tiêu, không mục tiêu và phạm vi

### 4.1 Mục tiêu MVP

| Năng lực                                    | MVP                       | Sau MVP                                            |
| ------------------------------------------- | ------------------------- | -------------------------------------------------- |
| Camera Pi, phát hiện người, tracking        | P0                        | Tối ưu model/độ phân giải                          |
| Đếm hai chiều ở một cửa                     | P0                        | Nhiều cửa/camera                                   |
| Vùng chờ có dwell, cảnh báo kéo dài         | P0                        | Ước lượng thời gian chờ cá nhân sau khi có dữ liệu |
| ESP32 LED/còi/nút ACK qua MQTT              | P0                        | Nhiều điểm nhận                                    |
| OLED trên ESP32 hiện trạng thái/số người    | P1                        | Màn hình lớn hơn                                   |
| Spring Boot + PostgreSQL + React, 2 vai trò | P0 (session auth)         | Đa cửa hàng, phân quyền chi tiết                   |
| Báo cáo giờ/ngày, coverage, CSV             | P0                        | Dự báo ca làm                                      |
| Bù sự kiện sau ngắt máy chủ                 | P0 trong giới hạn đã đo   | Outbox trên edge, đồng bộ quy mô lớn               |
| Đổi ngưỡng từ web có xác nhận từ Pi         | P1                        | Duyệt nhiều cấp                                    |
| Replay video, công cụ vẽ vạch/vùng          | P0 (công cụ phát triển)   | Giao diện hiệu chuẩn trên web                      |
| Xem trước ảnh từ Pi cho hiệu chuẩn/demo     | P1                        | Quản lý video an toàn có kiểm soát                 |
| NCNN và benchmark so sánh                   | P1                        | Tăng tốc phần cứng                                 |
| Fine-tune model                             | P2 khi pretrained chưa đủ | Bộ dữ liệu thực địa lớn                            |

### 4.2 Ngoài phạm vi

Nhận dạng khuôn mặt, lưu ID người dài hạn, kết nối POS, dự báo doanh thu, đo thời gian chờ của từng người, camera xoay, nhiều cửa hàng, AI Agent, ứng dụng di động và OTA. Bản đầu không đưa video khách lên máy chủ web; preview chỉ bật trong phiên demo/hiệu chuẩn được kiểm soát.

## 5. User story

| ID    | Là ... tôi muốn ...                                                                                       | Ưu tiên |
| ----- | --------------------------------------------------------------------------------------------------------- | ------- |
| US-01 | Quản lý, xem lượt vào/ra theo giờ kèm coverage để không hiểu nhầm giờ mất camera là giờ vắng khách        | P0      |
| US-02 | Nhân viên hỗ trợ, được đèn báo khi vùng chờ đông kéo dài và bấm ACK để người quản lý biết đã nhận yêu cầu | P0      |
| US-03 | Quản lý, xem một sự kiện bắt đầu, đã ACK hay chưa, kết thúc lúc nào để theo dõi tình huống                | P0      |
| US-04 | Quản trị, biết camera/Pi/ESP32/máy chủ còn dữ liệu mới hay đã mất kết nối                                 | P0      |
| US-05 | Quản lý, đổi ngưỡng từ web và biết chắc Pi đã áp dụng hay từ chối                                         | P1      |
| US-06 | Quản trị, quản lý quyền ADMIN/MANAGER để thông tin cửa hàng không hiển thị sai người                      | P0      |
| US-07 | Người đánh giá, xem bằng chứng benchmark Pi, sai số đếm và kết quả trên cùng góc camera                   | P0      |

## 6. Luồng trải nghiệm đầu cuối

### 6.1 Ca vận hành bình thường

1. Pi đồng bộ giờ với máy chủ LAN (chrony); Pi, camera, Mosquitto khởi động; ESP32 ban đầu vàng (UNKNOWN), máy chủ web khởi động riêng.
2. Pi có frame/analysis mới, phát `state` NORMAL mỗi giây cùng thời điểm và session mới.
3. Người đi qua cửa theo hướng vào/ra tạo crossing event. Spring nhận, kiểm trùng, commit PostgreSQL rồi mới PUBACK; web tổng hợp theo giờ địa phương.
4. Người bước vào vùng chờ, sau dwell mới được tính; khi vượt ngưỡng đủ hold time, Pi mở alert OVERLOAD với `alert_id` mới.
5. ESP32 đỏ nhấp nháy và kêu còi; nhân viên bấm một lần, ESP32 gửi `alert_id`/`ack_id` (gửi lại tới khi state báo `acked=true`). Pi chấp nhận ACK, phát transition ACK; Spring ghi nhận từ transition đó. Còi tắt, đỏ sáng liên tục vẫn thể hiện vùng chờ đông.
6. Số người giảm đủ thời gian, Pi kết thúc alert (END, `NORMALIZED`); web lưu lịch sử và cập nhật báo cáo.

### 6.2 Thay cấu hình (P1)

Quản lý có quyền nhập ngưỡng trên React → Spring kiểm kiểu/quyền/miền giá trị, publish `settings/set` có `request_id` và `expected_settings_revision` → Pi kiểm và trả `settings/result` → web hiển thị PENDING/APPLIED/REJECTED. Hết thời gian chờ mà không có kết quả thì hiển thị “chưa xác nhận áp dụng”, không tự kết luận đã thành công. `config_version` vẫn chỉ phiên bản profile kỹ thuật đầy đủ của edge, không đồng nghĩa revision ngưỡng sửa từ web.

### 6.3 Sự cố và phục hồi

- Mất camera/analysis cũ: Pi gửi UNKNOWN, `queue_count=null`; alert đang mở kết thúc với `reason=INTERRUPTED`; ESP32 vàng và web báo dữ liệu quá hạn.
- Tắt máy chủ/laptop: web không truy cập được; Pi/ESP32 tiếp tục xử lý; Mosquitto giữ các bản tin QoS 1 cho session bền của Spring. Sau khi máy chủ bật, Spring nhận hàng đợi, ghi chống trùng, commit rồi mới PUBACK từng bản tin.
- Mất broker Pi/Wi-Fi ESP32: node về UNKNOWN sau timeout; Pi tiếp tục suy luận nếu camera còn, nhưng không tuyên bố LED đã được bật.

## 7. Yêu cầu chức năng

| ID    | Yêu cầu và mức                                                                          | Tiêu chí nghiệm thu kiểm chứng được                                                               |
| ----- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| FR-01 | P0 — Thu ảnh một camera USB trên Pi; cùng detector/tracker dùng cho cửa và vùng chờ     | Clip chứa người qua cửa khi vùng chờ có người cho ra cả hai nhánh; camera không bị mở hai lần     |
| FR-02 | P0 — Đếm lượt vào/ra theo hướng, chống dao động tại đường đếm                           | Clip đi vào/ra/quay đầu/đứng sát vạch được so với nhãn tay; mỗi lượt chỉ ghi một event            |
| FR-03 | P0 — Vùng chờ dùng đa giác + dwell, không gọi là thời gian chờ khách                    | Người đi ngang không đủ dwell không được tính; mẫu hợp lệ được đối chiếu timestamp                |
| FR-04 | P0 — OVERLOAD bật/tắt theo hai ngưỡng và hold time; UNKNOWN khi dữ liệu cũ              | Unit/integration test ở mốc biên và mất camera; ACK không đóng OVERLOAD                           |
| FR-05 | P0 — ESP32 nhận `state` qua MQTT, điều khiển LED/còi và gửi ACK theo `alert_id`         | LED vật lý đúng bốn trạng thái; ACK lặp hoặc sai alert không nhận nhầm; ACK bị mất được gửi lại   |
| FR-06 | P0 — Spring consume MQTT và lưu PostgreSQL có idempotency                               | QoS 1/replay cùng `event_id` hai lần chỉ có một bản ghi; PUBACK chỉ gửi sau khi commit            |
| FR-07 | P0 — Dashboard React có Overview, Footfall, Alerts, Settings/Devices, login             | Quản lý đăng nhập và xem dữ liệu thật từ API, không dùng số mock trong nghiệm thu                 |
| FR-08 | P0 — Spring Security đăng nhập bằng session, phân quyền ADMIN/MANAGER tại API           | Request chưa đăng nhập/hết session hoặc trái quyền bị từ chối ở API dù gọi thẳng; ghi cần CSRF    |
| FR-09 | P1 — Cấu hình qua web có xác nhận từ Pi                                                 | Web giữ PENDING trước khi Pi trả APPLIED; giá trị sai REJECTED kèm lý do                          |
| FR-10 | P0 — Báo cáo giờ/ngày, CSV và coverage                                                  | Dữ liệu thử qua ranh giới giờ/ngày, restart, trùng bản tin và gap khớp nhãn                       |
| FR-11 | P0 — Pi/ESP32 vẫn cảnh báo khi server web tắt; bù dữ liệu qua hàng đợi broker           | Ngắt server rồi thử OVERLOAD/ACK, bật lại kiểm dữ liệu không nhân đôi và báo gap thật             |
| FR-12 | P1 — Xem trước ảnh từ Pi khi bật chế độ demo                                            | Máy tính cùng LAN xem đúng overlay Pi, tắt chế độ thì ngừng phục vụ ảnh                           |
| FR-13 | P0 — Edge chạy được từ file video theo timestamp video; có công cụ vẽ vạch/vùng ra YAML | Cùng clip cho cùng kết quả đếm qua hai lần chạy; YAML do công cụ tạo qua được validation          |

## 8. Yêu cầu phi chức năng

| ID     | Danh mục       | Điều kiện thử / mục tiêu ban đầu                                                                                                                                |
| ------ | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-01 | Edge           | Pi 4 4 GB chạy cả hai chức năng; đề xuất thử ≥3 FPS toàn luồng và đo RAM/nhiệt trên cấu hình cuối; ngưỡng nghiệm thu chốt với giảng viên sau pilot              |
| NFR-02 | Độ đúng        | Sai số tổng tuyệt đối từng chiều/tổng lượt thật ≤10% khi tổng lượt thật >0 (≤5% là mục tiêu mở rộng); clip 0 lượt báo số đếm giả; queue MAE ≤1 người (0–8 người) |
| NFR-03 | Cảnh báo       | Precision và recall ≥0,90 theo ghép sự kiện ±3 giây trên test đã khóa; đánh giá trên chuỗi queue-count có nhãn và clip live profile demo, ghi rõ nguồn và cỡ mẫu |
| NFR-04 | Độ trễ         | Đo p95 pipeline ảnh→state mục tiêu ≤1 giây, state→LED mục tiêu ≤1 giây trong LAN; không gộp với dwell/hold 2+60 giây                                            |
| NFR-05 | Freshness      | ESP32 chuyển UNKNOWN nếu không nhận state hợp lệ trong khoảng 5 giây; web hiển thị timestamp/tuổi dữ liệu và trạng thái stale                                   |
| NFR-06 | Ổn định        | Chạy 2 giờ bench, sau đó thử ca ≥4 giờ; ghi crash, gap, RAM/nhiệt và nguồn điện                                                                                 |
| NFR-07 | Bảo mật        | Mỗi MQTT client một tài khoản/topic ACL, đăng nhập web và role kiểm ở Spring, mật khẩu không commit; broker không public Internet                               |
| NFR-08 | Quyền riêng tư | Mặc định chỉ metadata; track ID tạm trong RAM; video nghiên cứu tách biệt, quyền truy cập và thời hạn giữ được ghi rõ                                           |
| NFR-09 | Phục hồi       | Mosquitto persistence + session bền của Spring giữ sự kiện QoS 1 chưa PUBACK, có giới hạn hàng đợi; test restart broker/backend, trùng và hàng đợi đầy; vượt giới hạn phải hiện coverage gap |
| NFR-11 | Thời gian      | Pi đồng bộ giờ với máy chủ LAN (Pi 4 không có RTC); `status` báo `clock_synced`; sự kiện lưu cả `occurred_at` và `server_received_at`                           |
| NFR-10 | Offline        | Mất Internet ≥10 phút nhưng LAN còn: Pi/ESP32 và server LAN vẫn chạy; mất server riêng được thử theo FR-11                                                      |

## 9. Yêu cầu dữ liệu

| Thực thể           | Trường cần thiết và ràng buộc                                               |
| ------------------ | --------------------------------------------------------------------------- |
| User (`app_user`)                    | id, username, password hash BCrypt, role ADMIN/MANAGER, trạng thái, mốc thời gian                    |
| Device (`device_status`)             | device_id (edge01/node01), phiên bản, last_seen, ONLINE/OFFLINE, clock_synced                        |
| Session (`edge_session`)             | session_id, lúc khởi động, config/model version; ID mới sau restart                                  |
| Crossing (`crossing_event`)          | event_id unique, session_id, seq, direction, occurred_at UTC, server_received_at, profile            |
| TelemetryMinute (`telemetry_minute`) | session_id + seq unique, phút, valid_seconds, queue_avg, queue_max, FPS, tuổi frame                  |
| AlertEvent (`alert_event`)           | alert_id unique, opened_at, acked_at, ack_device_id, ended_at, end_reason NORMALIZED/INTERRUPTED/CONFIG_CHANGED |
| AlertTransition (`alert_transition`) | event_id unique, alert_id, OPEN/ACK/END, ack_id (với ACK), occurred_at, server_received_at           |
| SettingsRevision (P1)                | request_id unique, revision, ngưỡng, người yêu cầu, PENDING/APPLIED/REJECTED, reason                 |

Flyway quản lý schema, mỗi giai đoạn thêm migration của mình (xem ADR-0001 D6). Spring commit transaction rồi mới PUBACK bản tin MQTT. Báo cáo lưu timestamp UTC, hiển thị/tổng hợp theo giờ Việt Nam; coverage tính từ `valid_seconds`, phút không có telemetry là gap chứ không phải 0. Hàng đợi broker có giới hạn; vượt giới hạn được báo là gap. Dữ liệu video thử nghiệm do người thực hiện quản lý riêng theo quyền cho phép; không đưa video vào PostgreSQL.

## 10. Chiến lược nghiệm thu và chất lượng

### 10.1 Cổng nghiệm thu MVP

1. Trên Pi thật, một camera cố định đồng thời đếm cửa và giám sát vùng chờ; có bảng so nhãn tay theo clip.
2. ESP32 ở vị trí khác nhận yêu cầu, ACK đúng event; nút ACK không làm mất tình trạng đông.
3. React hiển thị dữ liệu thật qua Spring/PostgreSQL, đăng nhập hai vai trò, phân quyền backend hoạt động.
4. Tắt máy chủ web mà Pi/ESP32 vẫn cảnh báo; bật lại kiểm replay không trùng và coverage đúng.
5. Camera/broker/node mất kết nối cho UNKNOWN hoặc trạng thái lỗi rõ, không hiển thị khách bằng 0 như dữ liệu mới.
6. Có log FPS/độ trễ/độ đúng, video minh họa, phiên bản cấu hình, BOM và quy trình khởi động/khôi phục.

### 10.2 Bộ dữ liệu và cách chấm

Thu clip độc lập theo buổi/góc lắp: qua cửa một người/hai người/ngược chiều/quay đầu, vùng chờ 0–8 người, che khuất, người đi ngang, thay đổi ánh sáng. Nhãn tay gồm crossing direction/time, queue count theo mốc, alert interval theo profile. Tách validation chỉnh ngưỡng với test cuối theo **clip/buổi**, không trộn frame sát nhau. Báo số mẫu, clip và thời lượng trước khi tính precision/recall; đếm 0 người cần số false positive riêng. Test bằng bản tin MQTT giả không thay thế phép đo Pi/camera thật.

## 11. Giới hạn kết luận

Một góc RGB nhìn chéo bị ảnh hưởng bởi che khuất và người nhỏ. Lượt ra/vào không cho biết chuyển đổi mua hàng; số người trong vùng chờ không cho biết thời gian chờ từng khách. Bấm ACK xác nhận thông báo đã đến nhân viên, chưa chứng minh người đó hỗ trợ hoặc thời gian chờ giảm. Nếu thí nghiệm chỉ ở lab, kết luận ở mức nguyên mẫu; thử cửa hàng thật cần mặt bằng phù hợp, sự đồng ý và đủ ca quan sát. Không tuyên bố lợi thế chi phí thương mại nếu chưa tính vận hành/bảo trì.

## 12. Phụ thuộc và ghi chú triển khai

- Phần cứng: Pi, nguồn/tản nhiệt, camera UVC, ESP32 với LED/còi/nút (OLED tùy chọn) và router LAN.
- Phần mềm: Python edge; Mosquitto trên Pi (persistence bật); firmware Arduino-ESP32 + PubSubClient + ArduinoJson; Java 21/Spring Boot + Spring Security session, PostgreSQL, React/TypeScript/Vite trên máy chủ LAN; NTP trên máy chủ LAN, chrony trên Pi.
- MQTT QoS 1 có thể giao trùng; cần khóa idempotency theo `event_id`, session bền của Spring và PUBACK thủ công sau commit. PubSubClient chỉ publish QoS 0 nên ACK của ESP32 được gửi lại ở cấp ứng dụng.
- Nếu laptop là máy chủ demo, web chỉ online khi laptop mở; Pi/ESP32 vẫn hoạt động nếu broker trên Pi và LAN của chúng còn. Triển khai lâu dài cần máy chủ luôn bật.
- Model pretrained là baseline; fine-tune nếu có bằng chứng thiếu độ đúng. So `.pt`/NCNN trên cùng Pi và cùng bộ dữ liệu.

## 13. Thước đo thành công

| ID     | Chỉ số                    | Phép tính và nguồn                                             | Mục tiêu thử nghiệm                             |
| ------ | ------------------------- | -------------------------------------------------------------- | ----------------------------------------------- |
| MET-01 | Sai số đếm vào/ra         | Σ sai số tuyệt đối theo clip/tổng lượt thật, tính riêng hướng  | ≤10% nếu có lượt thật; ≤5% là mục tiêu mở rộng  |
| MET-02 | MAE vùng chờ              | Trung bình abs(đoán − nhãn) tại các mốc lấy mẫu sau dwell      | ≤1 người trong phạm vi 0–8 người                |
| MET-03 | Precision/recall cảnh báo | TP/FP/FN theo event interval và profile                        | ≥0,90 từng chỉ số                               |
| MET-04 | FPS Pi                    | Số frame phân tích/thời gian thực của pipeline tích hợp        | Mục tiêu ban đầu ≥3 FPS, đo thực để chốt        |
| MET-05 | Từ state đến LED          | Đo trong LAN với đồng hồ/mốc đo thống nhất                     | Đề xuất ≤1 giây                                 |
| MET-06 | Tính đúng báo cáo         | So crossing log có nhãn với báo cáo giờ, ngày, CSV, gap        | Không lệch trong tập thử biết trước             |
| MET-07 | Bù sau sự cố server       | Tắt server 5 phút, phát sự kiện, phục hồi, kiểm DB unique và coverage | Không trùng; báo nếu hàng đợi đầy hoặc mất dữ liệu |
| MET-08 | ACK đúng                  | ACK cùng `alert_id` được lưu một lần và không đóng OVERLOAD    | 100% ca kiểm thử chức năng                      |

Thành công về lợi ích vận hành (ví dụ giảm chờ) cần đánh giá thực địa riêng; thước đo kỹ thuật trên chưa đủ để kết luận lợi ích kinh doanh.

## 14. Câu hỏi mở và quyết định cần chốt

| ID    | Câu hỏi                                                                               | Thời điểm chốt            | Tình trạng |
| ----- | ------------------------------------------------------------------------------------- | ------------------------- | ---------- |
| OQ-01 | Mặt bằng nào có một góc camera thấy rõ cả cửa và vùng chờ?                            | Trước khi lắp             | Mở         |
| OQ-02 | Máy chủ LAN chỉ là laptop demo hay máy luôn bật cho pilot thực?                       | Trước khi thử vận hành    | Mở         |
| OQ-03 | Sau đo Pi, chốt model/input size và ngưỡng FPS/độ đúng nghiệm thu nào với giảng viên? | Sau pilot benchmark       | Mở         |
| OQ-04 | Giới hạn hàng đợi broker và thời hạn lưu metadata/video nghiên cứu?                   | Trước test offline        | Một phần: cơ chế chốt ở ADR-0001 D3, giá trị giới hạn chốt sau bài thử |
| OQ-05 | Quản lý được thay những ngưỡng nào, cần duyệt hay không?                              | Trước khi viết API config | Đã chốt: chỉ dwell/on/off count/hold, không cần duyệt; ROI/model sửa bằng file |
| OQ-07 | Đồ án làm nhóm hay cá nhân, hạn nộp ngày nào?                                         | Trước khi chốt lịch       | Mở         |
| OQ-06 | Có quyền thu hình thử tại cửa hàng hay chỉ dùng mô hình lab?                          | Trước khi chốt dataset    | Mở         |

## 15. Nhật ký thay đổi

| Phiên bản | Ngày       | Thay đổi                                                                                 |
| --------- | ---------- | ---------------------------------------------------------------------------------------- |
| 0.1       | 29/09/2026 | PRD ban đầu theo phạm vi một camera, Pi 4, ESP32, MQTT, Spring Boot, PostgreSQL và React |
| 0.2       | 17/10/2026 | Áp dụng ADR-0001: session auth thay JWT, bù dữ liệu qua persistent session thay spool, ESP32 nhận `state` và có còi, FR-09 xuống P1, thêm FR-13/NFR-11, sửa bảng dữ liệu và MET-02 |

## 16. Tài liệu tham khảo

- [ADR-0001: Hợp nhất quyết định kỹ thuật](./decisions/0001-hop-nhat-quyet-dinh-ky-thuat.md).
- [Kế hoạch kỹ thuật và kiến trúc triển khai](./TrienKhai.md).
- [Đề cương và ánh xạ nội dung báo cáo](./RetailVision_Ke_Hoach.md).
- [Checklist khởi tạo theo từng giai đoạn](./implementation-checklist.md).
- Tài liệu công nghệ liên kết trong phần tài liệu tham khảo của kế hoạch triển khai.
