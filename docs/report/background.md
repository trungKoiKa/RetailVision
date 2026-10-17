# Bối cảnh, đối thủ và dữ liệu

Tài liệu phục vụ viết chương 1 và chương 4 của báo cáo, không thuộc luồng đọc của dev.

## 1. Bài toán và problem statement

### Bối cảnh và lý do hình thành đề tài

Để đánh giá hoạt động một điểm bán, người quản lý cần phân biệt ba câu hỏi: có bao nhiêu lượt người đến, hoạt động mua hàng tạo ra kết quả gì, và khu vực phục vụ có đáp ứng được nhu cầu tại từng thời điểm hay không. Dữ liệu hóa đơn mô tả giao dịch phát sinh; chỉ có hóa đơn thì chưa biết đầy đủ những lượt ghé không mua hàng hoặc khách đến vào lúc nào trước khi thanh toán. Ngược lại, số người qua cửa không cho biết họ có mua hàng hay đang phải chờ tại quầy. 

Phương án đề xuất: camera được dùng để tạo hai loại thông tin bổ sung: lưu lượng qua cửa theo thời gian và tình trạng hiện diện tại vùng chờ. Báo cáo lưu lượng giúp người quản lý có cơ sở xem lại cách bố trí ca; cảnh báo vùng chờ cung cấp tín hiệu để kiểm tra trong ca. Giá trị cần hướng đến là đưa số liệu vào một quyết định vận hành cụ thể, thay vì chỉ hiển thị bộ đếm hoặc bật đèn khi ảnh có nhiều người. Nhận biết giờ đông để bố trí nhân sự; kết hợp heatmap để xem phân bố khách; so sánh lưu lượng giữa các điểm bán.

### 1.1 Đồ án giải quyết việc gì, cho ai?

Người sử dụng chính là quản lý điểm bán và nhân viên có thể hỗ trợ quầy thanh toán. Một cơ sở bán lẻ có thể chưa có số liệu khách ra/vào theo giờ để tham khảo khi bố trí ca làm, trong khi nhân viên hỗ trợ ở vị trí khác không quan sát liên tục được vùng chờ. Hệ thống giải quyết hai nhu cầu liên quan: nhìn lại quy luật lưu lượng và nhận biết tình trạng cần kiểm tra ngay trong ca.

Đối tượng triển khai là điểm bán có mặt bằng phù hợp để một góc camera thấy rõ cửa và vùng chờ, có người sử dụng báo cáo và có nhân viên có thể phản hồi cảnh báo. Không giả định mọi cửa hàng nhỏ đều thường xuyên quá tải; không tuyên bố bao quát toàn bộ siêu thị lớn. Quy mô mặt bằng phù hợp và quy trình phản hồi quan trọng hơn nhãn “nhỏ/lớn”.

| Nhu cầu                               | Dữ liệu hệ thống cung cấp                                           | Quyết định hỗ trợ                                           | Giới hạn                                                      |
| ------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- |
| Biết lúc nào khách thường đến đông    | Lượt vào/ra theo giờ/ngày, thời gian dữ liệu hợp lệ                 | Tham khảo sắp ca, giờ nghỉ, thời điểm chuẩn bị người hỗ trợ | Lưu lượng không tự quy đổi thành số nhân viên cần có          |
| Phát hiện vùng chờ đông kéo dài       | Số người đủ điều kiện trong vùng, sự kiện vượt ngưỡng và thời lượng | Người nhận kiểm tra, hỗ trợ quầy hoặc báo quản lý           | Cần có người phản hồi; camera không tự mở thêm quầy           |
| Xem việc gọi hỗ trợ có được tiếp nhận | Thời điểm mở sự kiện và nhận xác nhận                               | Rà soát quy trình tiếp nhận                                 | Xác nhận không chứng minh nhân viên đã đến hoặc đã giải quyết |
| Giảm việc xem lại camera để thống kê  | Báo cáo và CSV tại chỗ                                              | Tổng hợp vận hành                                           | Độ tin cậy phụ thuộc sai số và thời gian mất dữ liệu          |

Ví dụ giả định: báo cáo nhiều ca cho thấy lưu lượng thường cao lúc 17–19 giờ; quản lý cân nhắc bố trí người hỗ trợ trong khung đó. Trong một ca, vùng chờ có ít nhất 5 người đủ điều kiện liên tục 60 giây; ESP32 ở vị trí hỗ trợ báo đỏ. Người nhận xác nhận, kiểm tra và quyết định hỗ trợ. Đây là kịch bản để thiết kế/kiểm thử, chưa phải bằng chứng tiết kiệm nhân sự hay giảm thời gian chờ.

### 1.2 Problem statement dùng trong đề cương

> Bài toán đặt ra là bổ sung dữ liệu về lưu lượng ghé thăm và tình trạng vùng chờ để hỗ trợ quản lý vận hành tại điểm bán. Số liệu giao dịch không tự mô tả toàn bộ lượt người đến, còn tổng lượt qua cửa chưa đủ phản ánh tình trạng đông người chờ thanh toán. Trong phạm vi một cửa ra/vào và một vùng chờ cùng nằm trong một góc quan sát, để đồng thời thống kê lượt vào/ra theo giờ, ngày và phát hiện vùng chờ đông vượt ngưỡng kéo dài. Báo cáo được cung cấp cho quản lý tham khảo bố trí nhân sự; cảnh báo được truyền ESP32 tại vị trí nhân viên hỗ trợ và có xác nhận tiếp nhận. Hệ thống xử lý hình ảnh tại chỗ, mặc định chỉ lưu số liệu và sự kiện, hoạt động không phụ thuộc Internet khi mạng nội bộ còn duy trì. Đồ án đánh giá độ đúng của hai chức năng khi chạy đồng thời, độ trễ, tính chính xác của báo cáo và khả năng phục hồi lỗi; lợi ích về nhân sự hoặc thời gian chờ chỉ được kết luận khi có bằng chứng thử nghiệm vận hành.

### 1.3 Vì sao dùng camera và khi nào không phù hợp?

Một camera cung cấp vị trí người để vừa xét đi qua cửa vừa xét hiện diện trong vùng chờ. Hai phép tính sử dụng chung một lần phát hiện/tracking trên mỗi frame. Cảm biến cắt tia có thể phù hợp hơn nếu chỉ cần đếm ở cửa hẹp, nhưng không trực tiếp cho biết số người đứng trong vùng chờ rộng. RFID cần người mang/quét thẻ và không tự cho biết vị trí trong hàng chờ.

Một camera là lựa chọn có điều kiện: cửa và vùng chờ phải nhìn rõ đồng thời, người xa vẫn đủ lớn để nhận diện, ít che khuất. Nếu mặt bằng không đáp ứng thì vị trí đó không phù hợp bản cơ sở.

Nếu nhân viên luôn nhìn thấy quầy và không có ai có thể hỗ trợ, giá trị cảnh báo thấp. Nếu quản lý cũng không cần báo cáo lưu lượng, cần xem lại nhu cầu ứng dụng. Khảo sát thực địa dùng để kiểm chứng tính cần thiết, không chỉ để chọn chỗ lắp thiết bị.

### 1.4 Sản phẩm cạnh tranh, hạn chế và điểm khác biệt của đề tài

#### 1.4.1 Đề tài đang đứng ở đâu trên thị trường?

RetailVision thuộc nhóm **đếm người, phân tích lưu lượng và giám sát vùng chờ cho bán lẻ**. Thị trường đã có sản phẩm thương mại giải quyết các chức năng này. Vì vậy, mục tiêu phù hợp của đồ án là thiết kế và kiểm chứng một cấu hình nhỏ, có thể tự điều chỉnh và tận dụng thiết bị sẵn có; chưa phải chứng minh vượt mọi sản phẩm thương mại.

Khảo sát dưới đây dựa trên trang sản phẩm “Đang có trên thị trường” ở đây nghĩa là hãng đang giới thiệu dòng sản phẩm/giải pháp trên website; chưa xác nhận hàng tồn, báo giá hoặc dịch vụ triển khai tại Việt Nam. Các tính năng do hãng công bố chưa được kiểm thử độc lập trong đồ án.

Phân biệt ba mức bằng chứng: **đã xác nhận trong tài liệu hãng**, **nhận định về độ phù hợp với phạm vi đồ án**, và **lợi thế dự kiến cần đo kiểm**. Không suy rằng một tính năng không xuất hiện trên trang web thì sản phẩm chắc chắn không hỗ trợ.

#### 1.4.2 Ba đối thủ/giải pháp tham chiếu trực tiếp

| Sản phẩm/giải pháp | Phần cạnh tranh trực tiếp | Điều kiện hoặc hạn chế cần cân nhắc | Cơ hội của RetailVision |
| --- | --- | --- | --- |
| [AXIS Object Analytics](https://www.axis.com/products/axis-object-analytics) trên camera Axis tương thích | Đếm qua vạch, số người trong vùng, xử lý trên camera | Cần camera và chức năng tương thích; không phải ứng dụng cài cho webcam USB bất kỳ. | Tận dụng webcam/PC đang có; tự sửa thuật toán và giao thức ứng dụng. |
| [V-Count Nano AI](https://v-count.com/nano-ai-people-counting-sensor/) + BoostBI | Cảm biến đếm người và phân tích vùng chờ; dashboard bán lẻ | Cấu hình phần cứng, tính năng và gói phần mềm cần chọn đúng nhu cầu. | Thiết kế một luồng cảnh báo local hẹp, dữ liệu lưu tại chỗ, dễ kiểm tra từng module. |
| [Xovis PC2SE/PC2-series](https://www.xovis.com/technology/sensor/pc2-series) và giải pháp retail qua hệ sinh thái đối tác | Cảm biến stereo 3D, đếm lưu lượng và phân tích hành vi trong cửa hàng | Dùng cảm biến chuyên dụng, yêu cầu bố trí và tích hợp tương ứng. | Thử nghiệm bằng thiết bị phổ thông khi đã có máy tính; không cần triển khai đa cảm biến ở bản đầu. |

#### 1.4.3 Nhược điểm tương đối của từng phương án so với phạm vi đề tài

##### A. AXIS Object Analytics: ràng buộc camera, nhưng là đối thủ chức năng rất gần

**Điểm đã xác nhận:** ứng dụng được cài sẵn không tính thêm phí trên camera Axis tương thích và xử lý tại camera. Không nên viết rằng dùng nó luôn phải trả thêm phí analytics hoặc cần máy chủ xử lý video riêng. [Axis — thông tin sản phẩm](https://www.axis.com/products/axis-object-analytics)

**Hạn chế trong hoàn cảnh của bạn:** nếu hiện chỉ có webcam USB và laptop, bạn không thể dùng trực tiếp AXIS Object Analytics trên hai thiết bị đó. Phải chọn camera Axis phù hợp. Suy ra, RetailVision có thể thuận tiện hơn để tận dụng phần cứng đang sở hữu và thực hiện các thí nghiệm thay model, logic đếm hay định dạng bản tin. Đây là lợi thế về khả năng tự phát triển, chưa phải bằng chứng tổng chi phí thấp hơn.

**Điểm cần thừa nhận:** Axis đã có hướng dẫn kích hoạt đèn/còi mạng qua MQTT khi số người trong vùng vượt ngưỡng trong một thời gian xác định. Do đó, “đếm người → MQTT → bật đèn” không phải chức năng mới độc quyền của đề tài. [Hướng dẫn AXIS Object Analytics](https://help.axis.com/en-us/axis-object-analytics)

**Cập nhật tên sản phẩm:** AXIS People Counter đã được hãng chỉ định thay thế bằng AXIS Object Analytics; nên dùng tên sản phẩm hiện tại khi phân tích đối thủ. [Trang hỗ trợ AXIS People Counter](https://www.axis.com/products/axis-people-counter/support)

##### B. V-Count Nano AI + BoostBI: nền tảng nhiều tính năng, cần xem đúng gói và nhịp cập nhật

**Điểm đã xác nhận:** Nano AI xử lý dữ liệu độ sâu trên thiết bị; vì vậy không có cơ sở nói sản phẩm phải đưa toàn bộ video lên cloud để phát hiện người. [V-Count Nano AI](https://v-count.com/nano-ai-people-counting-sensor/)

BoostBI công bố nhịp cập nhật báo cáo thường là **10 phút**, có thể **1 phút** khi bật cập nhật realtime. Quyền API và queue analytics thuộc các lựa chọn sublicence trong gói báo giá. Đây là nhịp báo cáo, không phải thời gian suy luận của cảm biến hay độ trễ mọi kênh cảnh báo. [BoostBI — capability matrix và API access](https://v-count.com/boostbi-retail-visitor-analytics-footfall-analytics-software-shopper-analytics-platform/)

**Hạn chế trong hoàn cảnh của bạn:** nếu mục tiêu chính là đèn phản ứng theo trạng thái cập nhật khoảng mỗi giây và lưu số liệu hoàn toàn tại chỗ, cần hỏi hãng về đường dữ liệu local, cơ chế cảnh báo, quyền API và chi phí gói tương ứng. Không thể dùng nhịp dashboard trên để kết luận toàn bộ V-Count cảnh báo chậm hơn đồ án.

**Cơ hội của RetailVision:** giao thức MQTT, chu kỳ trạng thái, DB và quy trình xác nhận do người làm đồ án kiểm soát. Có thể thiết kế chính xác một nghiệp vụ quầy nhỏ. Đây là lựa chọn kiến trúc của đề tài, không phải kết luận V-Count không tích hợp được. Những phần như phân tích bán hàng, nhiều cửa hàng và app quản lý từ xa nằm ngoài phạm vi MVP này.

##### C. Xovis PC2SE: phần cứng chuyên dụng và yêu cầu lắp đặt

**Điểm đã xác nhận:** PC2SE thuộc dòng stereo 3D, hỗ trợ PoE; hãng nêu dải độ cao lắp của PC2SE/PC2RE là **1,95–6 m**. [Thông số PC2-series](https://www.xovis.com/technology/sensor/pc2-series)

**Hạn chế trong hoàn cảnh của bạn:** cần cảm biến phù hợp, nguồn/mạng và giá lắp tương ứng; bộ webcam USB đang dùng không thay thế được thiết bị này trong giải pháp Xovis. Với mô hình một quầy và thiết bị sẵn có, tự làm bằng webcam có thể giảm số hạng mục phải mua. Đó là suy luận về cấu hình đầu tư ban đầu, không phải báo giá so sánh đã xác minh. Webcam của đồ án vẫn cần góc lắp ổn định, không được coi là lắp tùy ý.

**Điểm cần thừa nhận:** giải pháp retail của Xovis có đếm người, dwell time và khả năng phối hợp nhiều cảm biến. [Xovis Retail](https://www.xovis.com/solutions/retail) Hãng cũng mô tả xử lý nhúng và xuất metadata, nên xử lý biên và hạn chế truyền hình ảnh không phải điểm khác biệt riêng của RetailVision. [Xovis Sensors](https://www.xovis.com/technology/sensor)

#### 1.4.4 Đâu là lợi thế có thể bảo vệ được của đề tài?

<table class="markdown-table">
  <tr><th>Lợi thế dự kiến</th><th>Điều kiện để đúng</th><th>Bằng chứng cần bổ sung</th></tr>
  <tr><td>Tận dụng webcam/PC sẵn có</td><td>Thiết bị thực tế đạt yêu cầu độ đúng và độ trễ</td><td>Danh sách thiết bị đang có, hóa đơn phần mua mới, benchmark</td></tr>
  <tr><td>Tùy chỉnh logic nghiệp vụ</td><td>Tự xây dựng và hiểu code đếm, dwell, hysteresis, timeout, ack</td><td>Demo thay đổi yêu cầu và bộ test tương ứng</td></tr>
  <tr><td>Chủ động lưu dữ liệu local</td><td>DB, broker và dashboard đều chạy tại chỗ như thiết kế</td><td>Kiểm tra luồng dữ liệu và thử mất Internet</td></tr>
  <tr><td>Dễ nghiên cứu và giải thích từng khâu</td><td>Có log và ranh giới module rõ</td><td>Phân tích một ca lỗi từ camera đến LED</td></tr>
  <tr><td>Phạm vi một cửa và một vùng chờ</td><td>Thống kê lưu lượng theo giờ và hỗ trợ phản hồi tại quầy trong cùng góc camera</td><td>Phỏng vấn người dùng báo cáo, pilot có người tiếp nhận và kiểm thử đồng thời</td></tr>
</table>

“Tùy chỉnh” ở đây là tự sửa mã nguồn ứng dụng do mình xây dựng, không chỉ đổi một ngưỡng trên giao diện. Không đồng nghĩa các hãng không có API hay tùy chọn cấu hình. Việc dùng mô hình/thư viện có sẵn vẫn phải theo giấy phép của chúng.

Không dùng các câu sau làm kết luận cạnh tranh khi chưa có bằng chứng: “chính xác hơn sản phẩm thương mại”, “rẻ hơn 80%”, “các hãng đều phụ thuộc cloud”, “chỉ đề tài này có MQTT”, “bảo mật tốt hơn tuyệt đối” hoặc “cài đơn giản hơn”. Các nguồn đã kiểm tra cho thấy ít nhất một số nhận định đó không đúng hoặc chưa đủ căn cứ.

#### 1.4.5 Nhược điểm hiện tại của RetailVision cần ghi nhận

Đây vẫn là thiết kế cần triển khai. Camera RGB một góc nhìn còn nhạy với che khuất và ánh sáng; tracking có thể đổi ID. Máy edge, nay chọn Raspberry Pi, phải được duy trì nguồn, tiến trình và cập nhật. Chưa có số đo độ tin cậy dài hạn, dịch vụ bảo hành, quản lý nhiều cửa hàng hoặc phân quyền hoàn chỉnh. Khi phải mua Pi cùng phụ kiện và thuê người bảo trì, lợi thế chi phí linh kiện có thể giảm đáng kể. Các so sánh tận dụng PC tại mục 1.4 phải được tính lại cho BOM Pi trong `docs/2-design.md` mục 2.3.

Nếu cửa hàng đã có camera Axis tương thích, hoặc cần sản phẩm được nhà cung cấp chịu trách nhiệm vận hành ngay, tự phát triển chưa chắc là lựa chọn kinh tế hơn. Nếu mục tiêu là đồ án và pilot một quầy với máy sẵn có, quyền chủ động thử nghiệm của RetailVision có giá trị rõ hơn.

#### 1.4.6 Cách chứng minh khả năng cạnh tranh thay vì chỉ so tính năng

So sánh các phương án theo cùng một nhu cầu: một cửa ra/vào và một vùng chờ, báo cáo lưu lượng theo giờ, phạm vi quan sát tương đương, giờ chạy/ngày giống nhau, cùng yêu cầu lịch sử và cảnh báo ở vị trí hỗ trợ.

<table class="markdown-table">
  <tr><th>Nội dung cần hỏi/đo</th><th>Cách thực hiện</th></tr>
  <tr><td>Tổng chi phí 12 tháng</td><td>Phần cứng + giấy phép/dịch vụ + lắp đặt + điện + công cấu hình/bảo trì</td></tr>
  <tr><td>Tận dụng tài sản</td><td>Lập hai bảng: đã có PC/camera và phải mua mới toàn bộ</td></tr>
  <tr><td>Hoạt động khi mất Internet</td><td>Kiểm tra riêng cảm biến, local alert, dashboard và lịch sử; không gộp thành một nhãn “offline”</td></tr>
  <tr><td>Độ đúng</td><td>Test cùng địa điểm và định nghĩa lượt/vùng/sự kiện; không so MAE của mình với phần trăm quảng cáo khác định nghĩa</td></tr>
  <tr><td>Độ trễ</td><td>Đo tách thời gian dwell/hold, xử lý, truyền tin và bật LED</td></tr>
  <tr><td>Khả năng tích hợp</td><td>Thử xuất dữ liệu, đổi ngưỡng, điều khiển đèn và phục hồi mất kết nối</td></tr>
  <tr><td>Chi phí thay đổi yêu cầu</td><td>Ghi số giờ thực hiện một thay đổi nghiệp vụ cụ thể</td></tr>
</table>

Hiện chưa có báo giá cùng cấu hình và chưa mượn được các sản phẩm để đối chứng, nên kết luận đúng mức là **lợi thế dự kiến**, không phải đã thắng đối thủ về giá/độ chính xác. Danh mục phần cứng tại `docs/2-design.md` mục 2.3 chỉ là chi phí bổ sung khi tận dụng PC/router, không phải tổng chi phí thương mại của một hệ thống hoàn chỉnh.

#### 1.4.7 Đoạn lập luận có thể dùng trong báo cáo hoặc bảo vệ

> Thị trường đã có các giải pháp đếm người và giám sát vùng như AXIS Object Analytics, V-Count Nano AI kết hợp BoostBI và hệ thống Xovis. Vì vậy, đề tài không đặt tính mới ở việc lần đầu sử dụng camera hoặc xử lý tại biên để đếm người. Đề tài tập trung xây dựng và đánh giá một cấu hình cho một cửa và một vùng chờ trong cùng góc camera nhìn chéo, dùng Pi 4 4 GB và webcam phổ thông, thống kê lưu lượng và chủ động điều chỉnh logic gọi hỗ trợ và kết nối thiết bị IoT. Giá trị cần chứng minh là mức đáp ứng yêu cầu trong điều kiện triển khai cụ thể, khả năng hoạt động khi mất Internet và chi phí đầy đủ. Các lợi thế về độ chính xác, độ ổn định và kinh tế chỉ được kết luận sau thực nghiệm và đối chiếu phù hợp.

Các sản phẩm được nêu trong đoạn trên có nguồn tại mục 1.4.2–1.4.3. Phần định vị RetailVision là đề xuất của tài liệu này. Khi giảng viên hỏi “đã có sản phẩm rồi, tại sao vẫn làm?”, trọng tâm trả lời là **phạm vi ứng dụng, năng lực tự thiết kế và bằng chứng kiểm chứng hệ thống**, thay vì tuyên bố công nghệ hoàn toàn mới.

### 1.5 Định nghĩa đúng số liệu và đóng góp

- **Footfall trong đồ án:** lượt người qua vạch theo chiều vào; lượt ra báo riêng. Không phải khách duy nhất, người mua hàng hay số hóa đơn. Bản cơ sở có thể tính cả nhân viên/người quay lại; không nhận dạng để loại họ tự động.
- **Số người vùng chờ:** người có điểm đại diện trong đa giác và đủ thời gian hiện diện tối thiểu. Đây là đại lượng thay thế để phát hiện khả năng ùn khách, không chứng minh ý định xếp hàng.
- **OVERLOAD:** tên trạng thái kỹ thuật cho vùng chờ đông vượt ngưỡng đủ lâu; không phải kết luận cửa hàng vượt sức chứa hoặc mất an toàn.
- **Thời gian vùng chờ đông:** thời lượng sự kiện, không phải thời gian chờ từng khách. Xác nhận cảnh báo không phải hoàn tất hỗ trợ.
- **Đóng góp đồ án:** thiết kế, tích hợp và kiểm chứng một hệ thống CV–IoT trên máy tính nhúng, có dữ liệu lịch sử, phản hồi của nhân viên, offline và xử lý lỗi; không phát minh YOLO/ByteTrack.

Hệ thống hỗ trợ con người ra quyết định, không tự tính lịch nhân sự tối ưu.

**Cách chọn lọc cho RetailVision — đề xuất thiết kế của đồ án:**

| Hướng ứng dụng                          | Mức đưa vào đồ án                                                       | Dữ liệu/điều kiện còn cần                                                           |
| --------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Tham khảo bố trí nhân sự theo khung giờ | Mục tiêu chính: cung cấp báo cáo, quản lý quyết định                    | Nhiều ca có dữ liệu hợp lệ; đối chiếu lịch nhân sự và loại công việc                |
| So sánh các ngày có hoạt động quảng bá  | Có thể dùng CSV hiện có để phân tích mô tả, không thêm module marketing | Ghi ngày diễn ra hoạt động và các khác biệt giữa ca; chưa kết luận quan hệ nhân quả |
| Phân tích vị trí hàng hóa               | Hướng phát triển, không nghiệm thu trong bản cơ sở                      | Cần quan sát các khu trưng bày, không suy từ camera chỉ thấy cửa/quầy               |
| So sánh nhiều chi nhánh                 | Hướng phát triển                                                        | Nhiều địa điểm, cùng định nghĩa số đo và điều kiện so sánh                          |
| Gọi hỗ trợ khi vùng chờ đông kéo dài    | Mục tiêu chính bổ sung của RetailVision                                 | Vùng chờ nhìn rõ, ngưỡng phù hợp, người nhận có khả năng hỗ trợ                     |

### 1.6 Từ số liệu đến quyết định: ba tình huống cần phân biệt

**Tình huống A — lưu lượng tăng nhưng vùng chờ vẫn bình thường.** Người quản lý thấy nhiều lượt vào hơn trong một khung giờ, nhưng chưa có sự kiện đông vùng chờ. Hệ thống tiếp tục thống kê, không gọi hỗ trợ chỉ vì lượt vào cao. Dữ liệu này có thể được xem cùng lịch ca để chuẩn bị cho những ngày tương tự. Việc có cần tăng nhân sự hay không còn phụ thuộc công việc thực tế, không thể suy từ bộ đếm một mình.

**Tình huống B — lưu lượng không cao nhưng vùng chờ đông kéo dài.** Một giao dịch mất nhiều thời gian hoặc nhiều khách tới quầy gần nhau có thể là giả thuyết cần kiểm tra. Hệ thống chỉ nhận biết trạng thái vùng quan sát; không tự kết luận nguyên nhân. Nó gửi yêu cầu kiểm tra tới nhân viên hỗ trợ, ghi thời điểm tiếp nhận và thời điểm vùng chờ trở lại bình thường. Tình huống này giải thích vì sao cần đo tại quầy dù đã có bộ đếm cửa.

**Tình huống C — sự kiện đông lặp lại ở cùng khung giờ qua nhiều ca.** Báo cáo đặt cạnh nhau lượt vào, số phút vùng chờ đông và lịch sử tiếp nhận để quản lý xem có cần đổi thời điểm nghỉ hoặc bố trí người sẵn sàng hỗ trợ hay không. Nếu phần lớn thời gian camera bị mất dữ liệu, không dùng báo cáo đó để khẳng định quầy ít khách. Nếu nhân viên đã xác nhận nhưng chưa thể hỗ trợ, cần ghi nhận bằng quan sát/trao đổi; nút nhấn không đại diện cho việc vấn đề đã được giải quyết.

Ba tình huống cho thấy hai đầu ra có vai trò khác nhau: lưu lượng phục vụ việc xem xét kế hoạch, còn vùng chờ phục vụ việc kiểm tra và phản hồi tại thời điểm xảy ra sự kiện. Không cần cửa hàng liên tục quá tải mới có lý do thu thập lưu lượng; nhưng cần người sử dụng số liệu và hành động tiếp theo rõ ràng.

### 1.7 Tính cần thiết, tính khả thi và ý nghĩa của đề tài

**Tính cần thiết cần kiểm chứng:** khi điểm bán thiếu báo cáo lượt ghé và nhân viên hỗ trợ không nhìn trực tiếp vùng chờ, hệ thống có thể bổ sung thông tin cho hai nhóm người dùng. Khảo sát phải xác nhận khoảng thiếu thông tin này. Nếu cửa hàng đã có số liệu phù hợp, luôn có người quan sát và không có hành động nào thay đổi sau thông báo thì lý do triển khai bổ sung sẽ yếu.

**Tính khả thi trong phạm vi đã chọn:** một camera có thể cung cấp cùng kết quả phát hiện người cho vạch cửa và đa giác vùng chờ, giúp tránh nhân đôi pipeline suy luận. Điều kiện tiên quyết là mặt bằng cho phép nhìn rõ cả hai khu vực và Pi đáp ứng độ đúng/độ trễ trong thực nghiệm.

**Ý nghĩa đối với chuyên ngành hệ thống IoT:** đồ án bao gồm thu nhận dữ liệu, xử lý tại máy tính nhúng, truyền sự kiện qua mạng, thiết bị nhận cảnh báo ở vị trí khác, phản hồi của con người và lưu trữ lịch sử. Phần cần bảo vệ không chỉ là nhận diện đúng một người trong ảnh mà là toàn bộ luồng hoạt động có kiểm soát: tín hiệu còn mới hay đã lỗi, cảnh báo đến đúng nơi hay chưa, phản hồi có gắn đúng sự kiện không, dữ liệu có tổng hợp đúng qua giờ và sau restart không.

**Ý nghĩa thực tiễn có thể đánh giá:** cung cấp được báo cáo dùng được, phát hiện đúng sự kiện và thông báo tới người nhận trong phạm vi đo. Mức giảm thời gian chờ, chi phí lao động hoặc tăng doanh thu là câu hỏi đánh giá tiếp theo.

### 1.8 Câu hỏi khảo sát để kiểm chứng problem statement

| Câu hỏi cần hỏi/quan sát                                                     | Tác dụng đối với quyết định triển khai                         |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Hiện quản lý biết giờ đông bằng cách nào? Có số lượt ghé hay chỉ có hóa đơn? | Xác định báo cáo footfall có bổ sung thông tin cần thiết không |
| Quyết định nào có thể thay đổi khi xem báo cáo theo giờ?                     | Tránh xây dashboard mà không có mục đích sử dụng               |
| Vùng chờ từng đông kéo dài chưa, xảy ra khi nào, hiện ai phát hiện?          | Kiểm chứng nhu cầu cảnh báo và chọn ca khảo sát                |
| Người nhận đang ở đâu, có thể tới hỗ trợ công việc gì?                       | Xác định vị trí ESP32 và hành động sau thông báo               |
| Một camera có thấy rõ cả cửa và vùng khách đứng chờ không?                   | Kiểm tra điều kiện bắt buộc của mặt bằng                       |
| Khi nào nhân viên coi cảnh báo là hữu ích hoặc gây phiền?                    | Chọn ngưỡng/dwell/hold trên validation và đánh giá báo nhầm    |

## 2. Thu thập dữ liệu và fine-tune

### 2.1 Làm baseline trước

Chạy YOLOv8n pretrained với video tại chỗ. Phân loại lỗi: detector bỏ sót → xem góc/ánh sáng/dữ liệu; tracking đổi ID → xem che khuất/tham số; đếm lặp → sửa logic; LED chậm → đo mạng/vòng firmware. Không dùng fine-tune để chữa mọi loại lỗi.

Thu khoảng 12–20 clip qua nhiều buổi; các clip eval cảnh báo pilot phải dài hơn dwell + 60 giây và có cả giai đoạn kết thúc (nên khoảng 2–3 phút hoặc hơn): người đơn, nhóm, ngược chiều, dừng ở vạch, quầy vắng, vừa đủ ngưỡng, dưới ngưỡng, ánh sáng kém. Đây là quy mô pilot để bắt đầu; không đủ chứng minh khả năng tổng quát cho mọi cửa hàng. Chỉ quay người đã đồng ý tham gia nghiên cứu và giới hạn quyền truy cập video thử nghiệm.

### 2.2 Phân biệt nhãn phát hiện, đếm và sự kiện

| Nhãn                             | Cách tạo                                | Dùng cho            |
| -------------------------------- | --------------------------------------- | ------------------- |
| Bounding box `person` trên ảnh   | Công cụ như CVAT; bao từng người        | Train/eval detector |
| Thời điểm/lượt qua vạch          | Xem video, ghi hướng và timestamp       | Eval counting       |
| Số người vùng chờ theo thời điểm | Đếm thủ công theo cùng định nghĩa dwell | Eval vùng chờ       |
| Khoảng quá tải                   | Dựa trên nhãn đếm và cùng ngưỡng/hold   | Eval cảnh báo       |

Chia train/validation/test theo buổi hoặc clip độc lập trước khi trích frame. Không rải các frame gần trùng của cùng video sang cả train và test. Validation dùng chọn tham số; test giữ lại đến khi chốt. Nếu cần sửa tiếp sau test thì ghi rõ đó là vòng phát triển và thu một test mới độc lập.

Bổ sung clip bắt buộc: cửa có người ra/vào trong lúc hàng chờ đông; người ở xa; quầy/xe đẩy che người; thu ngân đứng đúng vị trí; hàng chờ tràn gần cửa. Ghi lỗi riêng cho cửa và vùng chờ trên cùng clip, không chỉ báo một độ chính xác chung.

### 2.3 Nếu cần fine-tune

Bắt đầu 500–1.500 ảnh đa dạng; chọn frame khoảng 1–2 giây/lần và bổ sung cảnh khó, bỏ ảnh gần trùng. Gán đủ người, có cả ảnh âm tính, thống nhất visible/full-body box. Dùng model hỗ trợ tạo nhãn nhưng sửa nhãn bỏ sót bằng tay. Train từ pretrained trên PC có GPU phù hợp hoặc môi trường huấn luyện được phép; thiết bị vận hành chỉ inference. So sánh pretrained và fine-tuned trên cùng test, cả độ đúng và FPS.

Nguồn mở tham khảo: [COCO với lớp person](https://docs.ultralytics.com/datasets/detect/coco/), [CrowdHuman cho che khuất đông người](https://www.crowdhuman.org/), [MOT17 cho chuỗi tracking](https://motchallenge.net/data/MOT17/), [xuất YOLO từ CVAT](https://docs.cvat.ai/docs/dataset_management/formats/format-yolo/). Kiểm tra điều khoản nguồn dữ liệu trước khi tái sử dụng. Chúng hỗ trợ nghiên cứu, không thay cho dữ liệu test đúng góc camera triển khai.

### 2.4 Quyền riêng tư theo thiết kế

Chế độ vận hành chỉ lưu số liệu và sự kiện; không lưu ảnh, face embedding hoặc lịch sử định danh. Track ID tạm trong RAM và không xuất ra dashboard công khai. Không thể khẳng định mọi metadata tự động ẩn danh tuyệt đối: số liệu thời gian/vị trí vẫn cần giới hạn quyền truy cập. Tách thư mục nghiên cứu có video khỏi runtime, xác định thời hạn xóa và người được xem. Làm mờ khuôn mặt dựa trên detector không bảo đảm che được mọi người nên mặc định không truyền hình ảnh là phương án đơn giản hơn.


## 3. Thử nghiệm tại cửa hàng

### 3.1 Các bước pilot

**Khảo sát:** xác nhận người dùng báo cáo lưu lượng, người nhận hỗ trợ, mặt bằng đáp ứng một camera nhìn chéo thấy rõ cửa và vùng chờ, ánh sáng, quyền đặt camera và quay thử. Nếu không có người phản ứng với đèn, chỉ thêm cảnh báo không giải quyết được vấn đề vận hành.

**Lắp thử:** cố định camera và hộp LED, dây gọn, máy có nguồn ổn định; đi thử từng vị trí. Đồng bộ giờ máy, xác nhận cấu hình. Không dùng tạm webcam laptop có góc nhìn thay đổi mỗi lần mở màn hình làm cấu hình cuối.

**Chạy quan sát:** 1–2 ca đầu chỉ ghi và so sánh, chưa yêu cầu nhân viên phụ thuộc cảnh báo. Thu lỗi điển hình, hỏi phản hồi; chốt ngưỡng trên dữ liệu validation thay vì đổi trên test cuối.

**Chạy hỗ trợ:** bật LED, chỉ định nhân viên tiếp nhận. Nhân viên thấy đỏ sẽ kiểm tra quầy và quyết định hỗ trợ. Hệ thống không tự quyết định phân công con người.

**Đánh giá:** đối chiếu báo cáo lượt theo giờ/ngày và coverage; hỏi quản lý số liệu có dùng được để tham khảo bố trí ca không. Tiếp theo so số lần vùng chờ đông được phát hiện đúng, số cảnh báo sai, thời gian từ cảnh báo đến xác nhận và phản hồi nhân viên. Nếu so trước/sau, cần các ca tương đồng và ghi yếu tố nhiễu như lưu lượng/nhân sự; không gán mọi thay đổi cho hệ thống.

### 3.2 Vận hành hằng ngày

Đầu ca kiểm tra tuổi dữ liệu, camera lệch hay không, đi thử một lượt, kiểm tra LED. Trong ca xem cảnh báo lỗi, không chỉ số người. Cuối ca xuất thống kê qua Spring, backup PostgreSQL trên máy chủ, kiểm `clock_synced` và log broker, xem log. Khi camera bị di chuyển phải cấu hình lại ROI/vạch và chạy kiểm thử ngắn.

Giai đoạn pilot: tắt sleep cho máy chủ web trong giờ chạy; Pi tự khởi động edge/Mosquitto bằng systemd, máy chủ tự khởi động PostgreSQL/Spring/React theo cách đã chọn. Nếu máy chủ là laptop demo, tắt laptop sẽ làm web tạm vắng và kích hoạt kịch bản replay, nhưng Pi/ESP32 còn chạy khi LAN của chúng còn.

### 3.3 Điều kiện trước khi triển khai lâu dài

Có máy edge dành riêng, khởi động/phục hồi tự động đã thử, mạng và tài khoản hạn chế quyền, backup và retention, người phụ trách xử lý lỗi, cách cập nhật/rollback model và cấu hình. Kiểm tra giấy phép thư viện/model trước khi phân phối thương mại; YOLOv8 có các lựa chọn giấy phép được nêu trong [tài liệu Ultralytics](https://docs.ultralytics.com/models/yolov8/). Pilot của đồ án chưa đồng nghĩa sản phẩm thương mại sẵn sàng.

