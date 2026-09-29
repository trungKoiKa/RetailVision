#  KẾ HOẠCH TRIỂN KHAI ĐỒ ÁN

**Định hướng:** Pi 4 xử lý một camera và chạy Mosquitto; ESP32 nhận cảnh báo qua MQTT; Spring Boot + PostgreSQL + React trên máy chủ LAN.  
**Tên đề tài:** “Thiết kế hệ thống giám sát lưu lượng khách ứng dụng thị giác máy tính tại biên”.

**Mục đích:** cung cấp dữ liệu để quản lý tham khảo bố trí nhân sự theo giờ và yêu cầu hỗ trợ khi vùng chờ đông kéo dài. Pi tiếp tục giám sát/cảnh báo khi máy chủ web tạm ngắt; báo cáo sẽ bù dữ liệu theo sự kiện đã lưu trên Pi khi máy chủ trở lại.

---

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

#### 1.6. Kết luận chương 1

**Nội dung cần thể hiện:** lý do đề tài cần cả thống kê lưu lượng và thông báo vùng chờ; điều kiện mặt bằng và nhân viên tiếp nhận; cơ sở lựa chọn công nghệ. Không khẳng định mọi cửa hàng nhỏ đều quá tải, hoặc nguyên mẫu vượt sản phẩm thương mại. Chỉ trình bày lý thuyết thực sự dùng trong thiết kế và đánh giá.

**Đầu ra:** phát biểu bài toán, bảng đối chiếu giải pháp, bảng phạm vi và sơ đồ định hướng hệ thống. Chi tiết yêu cầu được đặc tả ở chương 2 để tránh lặp lại.

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

#### 2.8. Kết luận chương 2

**Nội dung cần thể hiện:** mỗi lựa chọn thiết kế phải đáp ứng một yêu cầu cụ thể. Phân biệt số người trong vùng với thời gian chờ của từng khách; nút xác nhận chỉ cho biết nhân viên đã nhận yêu cầu, không tự xóa tình trạng đông. Tài liệu thiết kế phải thể hiện trạng thái mất dữ liệu, không chỉ luồng hoạt động bình thường.

**Đầu ra:** bảng yêu cầu, sơ đồ kiến trúc/mặt bằng/đấu nối, lưu đồ đếm, biểu đồ trạng thái cảnh báo, hợp đồng MQTT, thiết kế DB và phác thảo giao diện. Không chép hướng dẫn cài đặt chi tiết vào chương thiết kế.

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

#### 3.7. Kết luận chương 3

**Nội dung cần thể hiện:** phần thực sự tự xây dựng, cách tích hợp và các vấn đề triển khai đã giải quyết. Dùng ảnh thiết bị thật, cấu hình thực tế, ảnh giao diện và trích đoạn code có chọn lọc. Nếu chỉ lắp mô hình trong nhà/lab, ghi đúng môi trường đó. Model pretrained là phương án hợp lệ; chỉ thêm nội dung fine-tune khi đã thực hiện và có dữ liệu để trình bày.

**Đầu ra:** nguyên mẫu tích hợp, mã nguồn có phiên bản, ảnh đấu nối/lắp đặt, ảnh hiệu chuẩn, log MQTT, dữ liệu mẫu, dashboard và hướng dẫn khởi động. Chương này nêu cách hiện thực; kết quả đo so sánh các cấu hình được tập trung ở chương 4.

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

#### 4.4. Đánh giá hiệu năng và độ ổn định trên Pi 4

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

#### 4.8. Kết luận chương 4

**Nội dung cần thể hiện:** phương pháp thử và bằng chứng đủ để người đọc hiểu kết quả trong điều kiện nào. Mục tiêu ≥3 FPS là mục tiêu thử nghiệm, không phải kết quả đã đạt. Không dùng số đo GPU/PC thay cho Pi, số lượng người hiện diện thay cho lượt vào, hoặc xác nhận cảnh báo thay cho bằng chứng giảm thời gian chờ.

**Đầu ra:** danh mục dữ liệu, ground truth, bảng sai số, kết quả cảnh báo, benchmark, log sự cố/phục hồi, video tích hợp và bảng yêu cầu – kết quả đo – đạt/chưa đạt – bằng chứng. Phần thử bằng bản tin giả kiểm chứng firmware/logic nhưng không thay thế thử camera thật. Nếu chưa có cửa hàng cho thử nghiệm, giới hạn kết luận ở nguyên mẫu và mô tả điều kiện cần khảo sát trước khi lắp thật.

### Phần cuối báo cáo

**Kết luận và hướng phát triển:** các mục tiêu đã đạt đến đâu dựa trên chương 4; nêu hướng cải thiện theo lỗi thực tế. Nhiều camera, tích hợp POS, đo thời gian chờ cá nhân hoặc fine-tune chỉ là hướng mở rộng nếu chưa triển khai, không thêm thành yêu cầu bắt buộc.

**Trách nhiệm đạo đức nghề nghiệp:** trình bày sự đồng ý khi thu hình, chế độ không lưu video mặc định, phạm vi xem trước khi demo, ID tạm, trung thực số liệu và ghi nguồn mã/model/dataset. Quyền truy cập dữ liệu nghiên cứu cần được kiểm soát; không tuyên bố ẩn danh tuyệt đối chỉ vì không dùng nhận diện khuôn mặt.

**Tài liệu tham khảo:** liệt kê nguồn thực sự được sử dụng và trích dẫn tại nội dung tương ứng; phân biệt nguồn công nghệ, nguồn bối cảnh kinh doanh, báo cáo tham khảo về bố cục và mã nguồn được kế thừa.

**Phụ lục:** sơ đồ đấu nối, BOM, hợp đồng MQTT, cấu hình mẫu, hướng dẫn cài/chạy, cấu trúc thư mục, biểu mẫu gán nhãn, bảng kiểm thử chi tiết và đường dẫn mã nguồn/video được phép chia sẻ.

### Ánh xạ từ kế hoạch triển khai sang báo cáo

| Phần báo cáo        | Các mục kế hoạch cung cấp nội dung | Trọng tâm khi viết                               |
| ------------------- | ---------------------------------- | ------------------------------------------------ |
| Chương 1            | 1, 2, 7, 9, 10, 22, 23, 24         | Bối cảnh, giải pháp liên quan và cơ sở công nghệ |
| Chương 2            | 2–6, 8–12, 14, 15                  | Yêu cầu, thiết kế, các quyết định kỹ thuật       |
| Chương 3            | 4–12, 14, 20, 24                   | Lắp đặt, hiện thực và cấu hình đã triển khai     |
| Chương 4            | 13, 15, 17–19, 24                  | Dữ liệu, thử nghiệm, kết quả đo và hạn chế       |
| Kết luận và phụ lục | 19, 20, 22                         | Mức hoàn thành, bàn giao, nguồn và hướng mở rộng |

### Tài liệu tham khảo chính dự kiến

| Mã   | Tài liệu                                                                                                                             | Vai trò trong báo cáo                                       |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| TK01 | [Footfall counter siêu thị](https://anninhso.com/blog/footfall-counter-sieu-thi-nguyen-ly-ai-ung-dung-thuc-te/)                      | Bối cảnh ứng dụng; không lấy quảng bá làm số đo thực nghiệm |
| TK02 | [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/) và [tracking](https://docs.ultralytics.com/modes/track/)           | Detector, tracker và giới hạn thực nghiệm                   |
| TK03 | [Raspberry Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)                                                       | Cấu hình edge và benchmark                                  |
| TK04 | [Eclipse Mosquitto](https://mosquitto.org/documentation/)                                                                            | Broker MQTT trong LAN                                       |
| TK05 | [Spring Boot](https://docs.spring.io/spring-boot/index.html) và [Spring Security](https://docs.spring.io/spring-security/reference/) | Backend, API và phân quyền                                  |
| TK06 | [PostgreSQL](https://www.postgresql.org/docs/) và [Flyway](https://documentation.red-gate.com/fd/)                                   | Cơ sở dữ liệu và migration                                  |
| TK07 | [React](https://react.dev/) và [Vite](https://vite.dev/guide/)                                                                       | Web dashboard                                               |

---
