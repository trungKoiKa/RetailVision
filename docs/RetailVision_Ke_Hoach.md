# KẾ HOẠCH TRIỂN KHAI ĐỒ ÁN

**Định hướng:** Máy tính nhúng xử lý một camera và chạy Mosquitto; ESP32 nhận cảnh báo qua MQTT; Web dashboard có đầy đủ backend + frontend + cơ sở dữ liệu trên máy chủ LAN.  
**Tên đề tài:** “Thiết kế hệ thống giám sát lưu lượng khách ứng dụng thị giác máy tính tại biên”.

**Mục đích:** cung cấp dữ liệu để quản lý tham khảo bố trí nhân sự theo giờ và yêu cầu hỗ trợ khi vùng chờ đông kéo dài. Pi tiếp tục giám sát/cảnh báo khi máy chủ web tạm ngắt; báo cáo sẽ bù dữ liệu theo sự kiện đã lưu trên Pi khi máy chủ trở lại.

---

## 1. Bài toán

### Bối cảnh và lý do hình thành đề tài

Để đánh giá hoạt động một điểm bán, người quản lý cần phân biệt ba câu hỏi: có bao nhiêu lượt người đến, hoạt động mua hàng tạo ra kết quả gì, và khu vực phục vụ có đáp ứng được nhu cầu tại từng thời điểm hay không. Dữ liệu hóa đơn mô tả giao dịch phát sinh; chỉ có hóa đơn thì chưa biết đầy đủ những lượt ghé không mua hàng hoặc khách đến vào lúc nào trước khi thanh toán. Ngược lại, số người qua cửa không cho biết họ có mua hàng hay đang phải chờ tại quầy.

Phương án đề xuất: camera được dùng để tạo hai loại thông tin bổ sung: lưu lượng qua cửa theo thời gian và tình trạng hiện diện tại vùng chờ. Báo cáo lưu lượng giúp người quản lý có cơ sở xem lại cách bố trí ca; cảnh báo vùng chờ cung cấp tín hiệu để kiểm tra trong ca. Giá trị cần hướng đến là đưa số liệu vào một quyết định vận hành cụ thể, thay vì chỉ hiển thị bộ đếm hoặc bật đèn khi ảnh có nhiều người. Nhận biết giờ đông để bố trí nhân sự; kết hợp heatmap để xem phân bố khách; so sánh lưu lượng giữa các điểm bán.

## 2. Đề xuất triển khai

### Tóm tắt

RetailVision là hệ thống IoT hỗ trợ điểm bán nhận biết lưu lượng khách theo giờ và tình trạng vùng chờ thanh toán. Camera USB kết nối Raspberry Pi; Pi xử lý hình ảnh tại chỗ, theo dõi người tạm thời, ghi nhận lượt qua một cửa và phát hiện vùng chờ đông đủ lâu. ESP32 đặt ở vị trí nhân viên hỗ trợ hiển thị yêu cầu và cho phép xác nhận đã nhận. Web React cho quản lý xem báo cáo và quản trị hệ thống; Spring Boot lưu dữ liệu đã nhận qua MQTT vào PostgreSQL trên máy chủ LAN.

### 2.2 Giá trị và kết quả mong muốn

- Quản lý xem giờ có lưu lượng cao với phần thời gian quan sát hợp lệ để tham khảo bố trí ca.
- Người ở vị trí khác quầy nhận yêu cầu kiểm tra khi vùng chờ đông kéo dài và xác nhận đã nhận.
- Khi máy chủ web tạm tắt, Pi và ESP32 tiếp tục cảnh báo qua broker trên Pi; các sự kiện chưa được ghi PostgreSQL được broker giữ trong hàng đợi persistent session và bù khi máy chủ hoạt động trở lại, trong giới hạn hàng đợi đã công bố.
- Báo cáo phân biệt số lượt qua cửa, số người đang được tính trong vùng chờ.

### 2.3 Vai trò

<table class="markdown-table">
  <tr><th>Vai trò</th><th>Công việc và quyền trong MVP</th></tr>
  <tr><td>Quản lý cửa hàng (MANAGER)</td><td>Đăng nhập, xem trạng thái/báo cáo/lịch sử, xuất CSV, đề xuất thay ngưỡng được phép trong site của mình</td></tr>
  <tr><td>Quản trị hệ thống (ADMIN)</td><td>Quản lý tài khoản, thiết bị, cấu hình hệ thống và xem trạng thái dữ liệu</td></tr>
  <tr><td>Nhân viên hỗ trợ</td><td>Nhận tín hiệu trên ESP32, bấm nút ACK đúng sự kiện; không cần tài khoản web ở MVP</td></tr>
  <tr><td>Pi edge / ESP32 / Spring backend</td><td>Tác nhân hệ thống dùng danh tính MQTT khác nhau; không phải người dùng web</td></tr>
</table>

## 3. Vấn đề và cơ hội

### 3.1 Phát biểu vấn đề

Một điểm bán có thể thiếu số liệu đáng tin về lượt đến theo giờ để xem lại việc bố trí nhân sự; nhân viên ở vị trí khác cũng có thể không nhận biết kịp tình trạng đông kéo dài tại quầy. Hóa đơn không ghi được mọi lượt đến, còn đếm người trong một ảnh không thể tự suy ra lượt khách ra/vào. Hệ thống cần đo đúng hai loại thông tin và đưa cảnh báo đến người có thể hỗ trợ, trong điều kiện một góc camera quan sát được cả cửa và vùng chờ.

### 3.2 Giả thuyết cần kiểm chứng

Nếu hệ thống đo được lượt qua cửa theo hướng và vùng chờ đông kéo dài với sai số có thể chấp nhận, người quản lý có cơ sở xem lại giờ cao điểm và người nhận cảnh báo có thể biết lúc nào cần kiểm tra.

### 3.3 Khó khăn của nhóm

Một khó khăn lớn của đề tài là thu thập dữ liệu thực tế tại cửa hàng tiện lợi hoặc siêu thị. Camera tại các địa điểm này thường liên quan đến quyền riêng tư của khách hàng, quy định nội bộ và sự đồng ý của đơn vị vận hành, nên nhóm khó có thể tự quay hoặc lấy video để làm dữ liệu huấn luyện/đánh giá. Ngoài ra, dữ liệu cần có nhiều tình huống như đông người, che khuất, ánh sáng khác nhau, khách đi sát nhau hoặc đứng lâu tại quầy, trong khi việc thu thập đủ các tình huống này cần nhiều thời gian và sự phối hợp từ cửa hàng. Vì vậy, đồ án có thể phải bắt đầu bằng dữ liệu mô phỏng hoặc quay trong môi trường được cho phép, đồng thời nêu rõ giới hạn rằng kết quả chỉ phản ánh điều kiện thử nghiệm, chưa đại diện hoàn toàn cho mọi cửa hàng thực tế

## ĐỀ CƯƠNG VÀ MỤC LỤC BÁO CÁO ĐỒ ÁN

**Tên đề tài:** Thiết kế hệ thống giám sát lưu lượng khách ứng dụng thị giác máy tính tại biên.

### Phần đầu báo cáo

- Trang bìa và trang phụ bìa.
- Phiếu giao nhiệm vụ, nhận xét và các biểu mẫu nếu khoa yêu cầu.
- Lời cam đoan nếu mẫu báo cáo yêu cầu.
- Lời cảm ơn.
- Mục lục.
- Danh mục các ký hiệu và chữ viết tắt.
- Danh mục hình ảnh.
- Danh mục bảng biểu.
- Lời mở đầu: lý do chọn đề tài, mục tiêu, đối tượng và phạm vi, phương pháp thực hiện, bố cục báo cáo.

### CHƯƠNG 1. TỔNG QUAN BÀI TOÁN VÀ CÔNG NGHỆ SỬ DỤNG

#### 1.1. Tổng quan nhu cầu giám sát lưu lượng khách trong bán lẻ

- **1.1.1.** Lưu lượng khách và nhu cầu bố trí nhân sự theo thời gian.
- **1.1.2.** Tình trạng vùng chờ thanh toán và nhu cầu hỗ trợ trong ca.
- **1.1.3.** Phân biệt lượt qua cửa, số người hiện diện và số giao dịch.

#### 1.2. Các phương pháp và hệ thống liên quan

- **1.2.1.** Đếm thủ công và cảm biến phát hiện qua cửa.
- **1.2.2.** Giải pháp camera phân tích lưu lượng và vùng chờ.
- **1.2.3.** Sản phẩm thương mại và tiêu chí đối chiếu với phạm vi đồ án.

#### 1.3. Phát biểu bài toán và định hướng giải pháp

- **1.3.1.** Vấn đề cần giải quyết, người sử dụng và quyết định được hỗ trợ.
- **1.3.2.** Mô hình một cửa, một vùng chờ trong cùng góc nhìn camera.
- **1.3.3.** Phạm vi, giả định vận hành và giới hạn của nguyên mẫu.

#### 1.4. Cơ sở thị giác máy tính phục vụ hệ thống

- **1.4.1.** Khung hình, độ phân giải, tọa độ và vùng quan tâm.
- **1.4.2.** Phát hiện người bằng YOLO và ý nghĩa đầu ra mô hình.
- **1.4.3.** Theo dõi nhiều đối tượng bằng ByteTrack và ID tạm thời.
- **1.4.4.** Nguyên lý đếm qua vạch, xác định hiện diện và sự kiện theo thời gian.

#### 1.5. Công nghệ IoT và xử lý tại biên

- **1.5.1.** Vai trò Raspberry Pi và ESP32 trong kiến trúc hệ thống.
- **1.5.2.** MQTT, publish/subscribe và phản hồi ở cấp ứng dụng.
- **1.5.3.** PostgreSQL, Spring Boot, React và vận hành qua mạng nội bộ.
- **1.5.4.** Triển khai mô hình trên CPU và định hướng tối ưu với NCNN.

### CHƯƠNG 2. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

#### 2.1. Phân tích yêu cầu hệ thống

- **2.1.1.** Tác nhân và các kịch bản sử dụng chính.
- **2.1.2.** Yêu cầu chức năng: đếm vào/ra, thống kê, cảnh báo và xác nhận.
- **2.1.3.** Yêu cầu phi chức năng: hiệu năng, độ tin cậy, quyền riêng tư và vận hành cục bộ.
- **2.1.4.** Tiêu chí nghiệm thu và điều kiện áp dụng từng yêu cầu.

#### 2.2. Kiến trúc tổng thể

- **2.2.1.** Sơ đồ khối và phân chia chức năng giữa các thành phần.
- **2.2.2.** Luồng ảnh, dữ liệu thống kê, cảnh báo và xác nhận.
- **2.2.3.** Một pipeline phát hiện/theo dõi dùng chung cho hai chức năng.
- **2.2.4.** Ranh giới xử lý trên Pi và vai trò máy tính truy cập dashboard.

#### 2.3. Thiết kế phần cứng và bố trí camera

- **2.3.1.** Lựa chọn camera, Pi, nguồn, tản nhiệt và lưu trữ.
- **2.3.2.** Bố trí góc nhìn chéo xuống, cửa và vùng chờ thanh toán.
- **2.3.3.** Thiết kế thiết bị ESP32 với LED, nút xác nhận và nguồn cấp.
- **2.3.4.** Sơ đồ kết nối, bảng chân và danh mục vật tư.

#### 2.4. Thiết kế thuật toán xử lý ảnh và sự kiện

- **2.4.1.** Thu nhận ảnh, giới hạn bộ đệm và phát hiện khung hình cũ.
- **2.4.2.** Phát hiện người và duy trì tracking ID tạm thời.
- **2.4.3.** Đếm qua vạch theo hướng và chống đếm lặp.
- **2.4.4.** Xác định người đủ điều kiện trong đa giác vùng chờ.
- **2.4.5.** Điều kiện đông kéo dài, ngưỡng bật/tắt và trạng thái UNKNOWN.
- **2.4.6.** Xử lý che khuất, mất ID, mất camera và khởi động lại.

#### 2.5. Thiết kế truyền thông và firmware ESP32

- **2.5.1.** Tổ chức topic và cấu trúc bản tin MQTT.
- **2.5.2.** Mã sự kiện, heartbeat, timeout và chống xử lý trùng.
- **2.5.3.** Máy trạng thái LED, đọc nút và chống dội.
- **2.5.4.** Xác nhận tiếp nhận yêu cầu, gửi lại và phục hồi kết nối.

#### 2.6. Thiết kế cơ sở dữ liệu và báo cáo

- **2.6.1.** Mô hình dữ liệu và quan hệ giữa các bảng.
- **2.6.2.** Lưu lượt qua cửa, mẫu vùng chờ, sự kiện, xác nhận và phiên chạy.
- **2.6.3.** Tổng hợp theo giờ/ngày, múi giờ và khoảng dữ liệu không hợp lệ.
- **2.6.4.** Xuất CSV, chính sách lưu trữ và bảo vệ dữ liệu.

#### 2.7. Thiết kế giao diện và vận hành

- **2.7.1.** Dashboard lưu lượng, vùng chờ và sức khỏe thiết bị.
- **2.7.2.** Lịch sử sự kiện/xác nhận và quản lý cấu hình.
- **2.7.3.** Chế độ xem ảnh phục vụ hiệu chuẩn/demo qua LAN.
- **2.7.4.** Tự khởi động, nhật ký và phân biệt mất Internet với mất LAN/broker.

### CHƯƠNG 3. XÂY DỰNG VÀ TRIỂN KHAI NGUYÊN MẪU

#### 3.1. Môi trường phát triển và tổ chức mã nguồn

- **3.1.1.** Môi trường Windows, Raspberry Pi OS và công cụ phát triển.
- **3.1.2.** Cấu trúc thư mục RetailVision và trách nhiệm các module.
- **3.1.3.** Quản lý phiên bản thư viện, model, cấu hình và mã nguồn tham khảo.

#### 3.2. Lắp đặt phần cứng và hiệu chuẩn camera

- **3.2.1.** Lắp camera, Pi, nguồn và tản nhiệt.
- **3.2.2.** Lắp thiết bị ESP32 và bố trí tại vị trí nhân viên hỗ trợ.
- **3.2.3.** Khảo sát góc nhìn, cố định camera và xác lập vạch/vùng.
- **3.2.4.** Kiểm tra trường nhìn, ánh sáng và nguy cơ che khuất.

#### 3.3. Xây dựng ứng dụng xử lý ảnh trên Pi

- **3.3.1.** Thu ảnh và tích hợp mô hình phát hiện người.
- **3.3.2.** Tích hợp tracking và module đếm lượt vào/ra.
- **3.3.3.** Xây dựng module vùng chờ và bộ quản lý sự kiện.
- **3.3.4.** Ghi nhận thời gian, chất lượng dữ liệu và phục hồi pipeline.

#### 3.4. Xây dựng firmware và tích hợp MQTT

- **3.4.1.** Hiện thực LED, nút xác nhận và chống dội.
- **3.4.2.** Cấu hình Wi-Fi, broker và quyền truy cập cần thiết.
- **3.4.3.** Publish/subscribe, nhận cảnh báo và gửi xác nhận theo event ID.
- **3.4.4.** Xử lý mất kết nối, dữ liệu cũ và bản tin lặp.

#### 3.5. Xây dựng cơ sở dữ liệu và dashboard

- **3.5.1.** Tạo migration PostgreSQL và triển khai API/consumer MQTT trong Spring Boot.
- **3.5.2.** Xây dựng React hiển thị biểu đồ lưu lượng, trạng thái vùng chờ và tuổi dữ liệu qua Spring Boot API.
- **3.5.3.** Lịch sử cảnh báo, xác nhận và xuất CSV.
- **3.5.4.** Xem ảnh do Pi xử lý trên máy tính qua LAN khi demo.

#### 3.6. Triển khai dịch vụ trên Raspberry Pi

- **3.6.1.** Cài môi trường, triển khai model và cấu hình camera.
- **3.6.2.** Thiết lập cấu hình chạy CPU và các cấu hình NCNN cần so sánh.
- **3.6.3.** Cấu hình dịch vụ tự khởi động, nhật ký và lưu trữ cục bộ.
- **3.6.4.** Tích hợp toàn hệ thống và chuẩn bị profile pilot/demo.

### CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ HỆ THỐNG

#### 4.1. Mục tiêu và cấu hình thực nghiệm

- **4.1.1.** Ma trận yêu cầu – phép thử – bằng chứng.
- **4.1.2.** Cấu hình phần cứng, phần mềm, model và ngưỡng thử nghiệm.
- **4.1.3.** Phân biệt camera live, video phát lại và đầu vào mô phỏng.

#### 4.2. Dữ liệu và phương pháp đánh giá

- **4.2.1.** Thu thập dữ liệu trong nhà/lab hoặc tại điểm bán được phép.
- **4.2.2.** Gán nhãn lượt qua cửa, số người vùng chờ và khoảng sự kiện.
- **4.2.3.** Tách dữ liệu chọn tham số với tập kiểm thử cuối.
- **4.2.4.** Chỉ số sai số đếm, MAE, precision/recall, FPS và độ trễ.

#### 4.3. Thực nghiệm chức năng và độ chính xác

- **4.3.1.** Đếm hai chiều: đi đơn, đi sát nhau, quay đầu và dừng sát vạch.
- **4.3.2.** Vùng chờ: hiện diện, người đi ngang, che khuất và thay đổi số người.
- **4.3.3.** Cảnh báo kéo dài: ngưỡng, timer, kết thúc và xác nhận.
- **4.3.4.** Báo cáo theo giờ/ngày, trùng bản tin và khoảng mất dữ liệu.
- **4.3.5.** Hai chức năng đếm cửa và giám sát vùng chờ hoạt động đồng thời.

#### 4.4. Đánh giá hiệu năng và độ ổn định trên máy tính nhúng

- **4.4.1.** So sánh cấu hình model và kích thước đầu vào trên cùng dữ liệu.
- **4.4.2.** FPS toàn pipeline, độ trễ cảnh báo và tải khi bật dashboard/xem trước.
- **4.4.3.** RAM, nhiệt độ và khả năng vận hành liên tục.
- **4.4.4.** Lựa chọn cấu hình theo cả tốc độ và độ chính xác.

#### 4.5. Thử nghiệm sự cố và phục hồi

- **4.5.1.** Mất camera, khung hình cũ và tracking bị gián đoạn.
- **4.5.2.** Mất Internet, mất LAN/broker và mất kết nối ESP32.
- **4.5.3.** Khởi động lại dịch vụ/thiết bị và tính nhất quán của dữ liệu.
- **4.5.4.** Trạng thái UNKNOWN, thời gian phát hiện lỗi và thời gian phục hồi.

#### 4.6. Trình diễn tích hợp và đánh giá khả năng ứng dụng

- **4.6.1.** Chu trình khách vào/ra → đông kéo dài → thông báo → xác nhận → kết thúc.
- **4.6.2.** Pi xử lý độc lập khi máy tính xem dashboard được tắt.
- **4.6.3.** Điều kiện áp dụng, chi phí nguyên mẫu và khả năng lắp đặt thực tế.
- **4.6.4.** Phản hồi người dùng nếu có thử nghiệm tại điểm bán.

#### 4.7. Phân tích kết quả và mức hoàn thành

- **4.7.1.** Đối chiếu kết quả đo với yêu cầu và tiêu chí nghiệm thu.
- **4.7.2.** Phân tích lỗi theo góc camera, detector, tracking, logic và truyền thông.
- **4.7.3.** Phần tự phát triển, phần kế thừa và đóng góp của đồ án.
- **4.7.4.** Hạn chế còn tồn tại và phạm vi kết luận được bằng chứng hỗ trợ.

### Phần cuối báo cáo

**Kết luận và hướng phát triển:**

**Trách nhiệm đạo đức nghề nghiệp:**

**Tài liệu tham khảo**

**Phụ lục**

### Tài liệu tham khảo chính dự kiến

| Mã   | Tài liệu                                                                                                                             | Vai trò trong báo cáo                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| TK01 | [Footfall counter siêu thị](https://anninhso.com/blog/footfall-counter-sieu-thi-nguyen-ly-ai-ung-dung-thuc-te/)                      | Bối cảnh ứng dụng                         |
| TK02 | [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/) và [tracking](https://docs.ultralytics.com/modes/track/)           | Detector, tracker và giới hạn thực nghiệm |
| TK03 | [Raspberry Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)                                                       | Cấu hình edge và benchmark                |
| TK04 | [Eclipse Mosquitto](https://mosquitto.org/documentation/)                                                                            | Broker MQTT trong LAN                     |
| TK05 | [Spring Boot](https://docs.spring.io/spring-boot/index.html) và [Spring Security](https://docs.spring.io/spring-security/reference/) | Backend, API và phân quyền                |
| TK06 | [PostgreSQL](https://www.postgresql.org/docs/) và [Flyway](https://documentation.red-gate.com/fd/)                                   | Cơ sở dữ liệu và migration                |
| TK07 | [React](https://react.dev/) và [Vite](https://vite.dev/guide/)                                                                       | Web dashboard                             |
