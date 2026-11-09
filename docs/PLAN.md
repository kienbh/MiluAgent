# Kế hoạch phát triển Milu

## 1. Mục tiêu và trạng thái

Milu là trợ lý AI mang hình tượng chú chó, chạy trên Raspberry Pi 5, có màn hình để biểu đạt cảm xúc.

Tài liệu này là kế hoạch được cập nhật cùng tiến độ. Đã có khuôn mặt, giao diện chat, bộ điều phối hội thoại, adapter OpenAI/Claude và bộ nhớ cục bộ có xác nhận. Mặc định vẫn dùng phản hồi giả, chưa gọi API thật; bộ nhớ chưa được đưa tự động vào hội thoại. Chưa có cấu hình phần cứng đã kiểm chứng hoặc kết quả đo trên Raspberry Pi 5. Các mốc dưới đây thể hiện thứ tự làm việc, không phải cam kết thời hạn.

Xem [hướng dẫn chạy](../README.md), [cấu hình tạm thời](HARDWARE.md) và [kết quả kiểm thử](VALIDATION.md).

### Đã xác định

- Nền tảng chính: Raspberry Pi 5.
- Hình tượng: chú chó Milu.
- Giao diện: khuôn mặt và cảm xúc trên màn hình.
- Màn hình LCD HAT 3,5 inch; chưa xác định model, độ phân giải và driver.

### Đề xuất cần xác nhận

- Model LCD HAT 3,5 inch, độ phân giải, giao tiếp và trình điều khiển hỗ trợ Raspberry Pi 5. Không suy ra driver chỉ từ tên HAT.
- Hội thoại tiếng Việt qua micro và loa.
- Dùng API OpenAI hoặc Claude cho phần hội thoại. Chọn một nhà cung cấp trước, thiết kế lớp kết nối để có thể đổi sau.
- Bộ nhớ riêng để lưu thông tin người dùng chủ động muốn Milu nhớ.
- Python cho phần điều phối, SQLite cho bộ nhớ cục bộ và một thư viện giao diện nhẹ, chẳng hạn Pygame. Chỉ chốt sau thử nghiệm màn hình và âm thanh.

## 2. Phạm vi bản đầu

### Mục tiêu bản trình diễn đầu tiên

1. Khởi động được trên Raspberry Pi 5.
2. Hiện khuôn mặt Milu với các trạng thái: chờ, lắng nghe, xử lý, trả lời và gặp lỗi.
3. Nhận văn bản từ bàn phím để kiểm tra luồng hội thoại trước khi thêm giọng nói.
4. Gửi yêu cầu tới một API đã cấu hình và hiển thị câu trả lời.
5. Khi mất mạng, thiếu khóa API hoặc hết thời gian chờ, vẫn giữ giao diện hoạt động và báo lỗi dễ hiểu.
6. Có thể chạy chế độ mô phỏng bằng phản hồi giả mà không cần API.

### Mở rộng sau khi bản đầu ổn định

- Nhấn nút để nói, nhận dạng tiếng nói và đọc câu trả lời.
- Bộ nhớ cục bộ có chức năng xem, sửa, quên và xóa.
- Hoạt ảnh tự nhiên hơn và cơ chế khởi động cùng thiết bị.

### Chưa đưa vào phạm vi ban đầu

- Cơ cấu chuyển động, điều khiển động cơ hoặc khả năng tự di chuyển.
- Camera, nhận diện khuôn mặt hoặc giám sát liên tục.
- Tự gửi tin nhắn, mua hàng hoặc thực hiện hành động trên tài khoản bên ngoài.
- Nghe liên tục bằng từ đánh thức hoặc chạy mô hình ngôn ngữ lớn hoàn toàn trên Raspberry Pi.

Các phần này chỉ được bổ sung sau khi có yêu cầu và đánh giá riêng.

## 3. Kiến trúc đề xuất

### Các thành phần

- **Đầu vào:** bàn phím cho bản thử, sau đó thêm nút nhấn và micro.
- **Điều phối hội thoại:** quản lý lượt nói, hủy yêu cầu cũ, giới hạn thời gian chờ và cập nhật trạng thái.
- **Lớp kết nối AI:** chuẩn hóa yêu cầu và kết quả; giấu chi tiết riêng của từng nhà cung cấp.
- **Màn hình:** vẽ mặt Milu và hoạt ảnh theo trạng thái, không chờ trực tiếp lời gọi mạng.
- **Âm thanh:** thu âm, nhận dạng tiếng nói và tổng hợp tiếng nói ở giai đoạn sau.
- **Bộ nhớ:** lưu thông tin đã được chọn, có nguồn và thời điểm cập nhật.
- **Cấu hình và vận hành:** quản lý thiết bị, tùy chọn dịch vụ, nhật ký kỹ thuật và giới hạn sử dụng.

### Luồng chính

Đầu vào → điều phối → API hội thoại → câu trả lời → màn hình/loa.

Màn hình nhận cập nhật trạng thái riêng để tiếp tục hoạt ảnh khi dịch vụ đang xử lý. Khi có bộ nhớ, chỉ đưa những mục liên quan và được phép chia sẻ vào yêu cầu API.

### Nguyên tắc triển khai

- Không để lời gọi mạng khóa vòng lặp giao diện.
- Tách logic hội thoại khỏi phần cứng để kiểm thử bằng dữ liệu giả.
- Bắt đầu bằng một nhà cung cấp; không tự chuyển dịch vụ và gửi lại dữ liệu sang nơi khác.
- Không mặc định mô hình hội thoại cũng cung cấp nhận dạng hoặc tổng hợp tiếng nói. Hai phần âm thanh được lựa chọn và kiểm chứng riêng.
- Cảm xúc hiển thị là trạng thái giao diện hoặc biểu cảm được thiết kế, không phải kết luận về cảm xúc thật của người dùng.

## 4. Phần cứng cần kiểm tra

Trước khi mua thêm hoặc chọn thư viện, ghi lại:

- Dung lượng RAM và hệ điều hành trên Raspberry Pi 5.
- Model màn hình, giao tiếp, độ phân giải, chiều đặt và khả năng cảm ứng nếu có.
- Nguồn điện đáp ứng yêu cầu của Pi 5 cùng các thiết bị ngoại vi.
- Tản nhiệt và nhiệt độ khi chạy liên tục.
- Micro, loa và cách kết nối được Linux hỗ trợ.
- Dung lượng lưu trữ và kết nối mạng.

Thử màn hình bằng một hình tĩnh, rồi hoạt ảnh đơn giản. Thử micro và loa độc lập trước khi nối vào hội thoại. Chưa giả định các linh kiện đã có hoặc tương thích chỉ từ kích thước màn hình.

## 5. Bộ nhớ và quyền riêng tư

Đề xuất triển khai bộ nhớ sau khi hội thoại cơ bản ổn định:

- Lưu cục bộ trên thiết bị, tách khỏi mã nguồn và thư mục được Git theo dõi.
- Phân biệt ngữ cảnh tạm của phiên nói chuyện với thông tin lưu lâu dài.
- Chỉ lưu lâu dài thông tin người dùng yêu cầu hoặc xác nhận muốn ghi nhớ.
- Cho phép xem, sửa, quên từng mục và xóa toàn bộ dữ liệu.
- Không tự lưu bản ghi âm hoặc toàn bộ lịch sử hội thoại.
- Không tự nhập dữ liệu từ sản phẩm hoặc tài khoản khác. Mọi nguồn nhập cần có cách truy cập hợp lệ và sự đồng ý.
- Trước khi gửi dữ liệu cho API, làm rõ dữ liệu nào được gửi, tới nhà cung cấp nào và vì sao cần gửi.
- Không lưu mật khẩu, khóa API hoặc bí mật trong bộ nhớ hội thoại.

Ở bản đầu, có thể để bộ nhớ dài hạn tắt. Chỉ bật sau khi kiểm tra lưu, truy xuất, xóa và giới hạn dữ liệu gửi ra ngoài.

## 6. Lộ trình và tiêu chí hoàn thành

### Mốc 0: Chốt cấu hình thử nghiệm

- [ ] Xác nhận model màn hình và thiết bị âm thanh.
- [ ] Chọn hệ điều hành, thư viện giao diện và cách chạy ứng dụng.
- [ ] Chọn một dịch vụ hội thoại, mô hình và mức chi phí thử nghiệm.
- [x] Ghi lại các quyết định tạm thời cùng lý do trong `docs/HARDWARE.md`.

**Hoàn thành khi:** màn hình và các thiết bị cần cho bản thử hoạt động độc lập; các lựa chọn chưa rõ được ghi lại.

### Mốc 1: Khuôn mặt Milu

- [x] Vẽ khuôn mặt và các trạng thái chờ, lắng nghe, xử lý, trả lời, lỗi (mô phỏng ngoại tuyến).
- [x] Cho phép đổi trạng thái bằng bàn phím, có kiểm thử tự động.
- [ ] Chạy được ở đúng kích thước màn hình.
- [ ] Đo độ mượt, CPU và nhiệt độ trên thiết bị thật.

**Hoàn thành khi:** các trạng thái chuyển đúng, giao diện không treo và đóng ứng dụng được sạch sẽ.

### Mốc 2: Hội thoại bằng văn bản

- [x] Tạo adapter OpenAI/Claude và phản hồi giả; kiểm thử HTTP giả, chưa gọi API thật.
- [x] Nhận văn bản, hiển thị trả lời và cập nhật biểu cảm; đã thử bằng phản hồi giả.
- [x] Có thời gian chờ giao diện, giới hạn độ dài đầu vào/đầu ra và thông báo lỗi an toàn.
- [x] Cho phép hủy chờ; bỏ phản hồi cũ, không tạo thêm worker khi request trước chưa thoát.
- [x] Giữ số lượt gọi và token trong RAM nếu API trả về; không ghi nội dung riêng tư ra nhật ký.

**Hoàn thành khi:** hoàn tất một lượt hỏi đáp thật; các tình huống thiếu khóa, mất mạng, lỗi dịch vụ và hết thời gian chờ không làm ứng dụng treo.

### Mốc 3: Hội thoại bằng giọng nói

- [ ] Chọn và kiểm tra dịch vụ nhận dạng/tổng hợp tiếng Việt.
- [ ] Bắt đầu bằng nhấn để nói, có chỉ báo rõ lúc đang thu âm.
- [ ] Ngừng thu khi người dùng kết thúc hoặc khi hết giới hạn thời lượng.
- [ ] Tránh thu lại tiếng loa bằng cơ chế luân phiên nói/nghe ở bản đầu.
- [ ] Có nút dừng phát và cách chuyển về nhập văn bản.

**Hoàn thành khi:** người dùng hoàn tất nhiều lượt hỏi đáp bằng giọng nói trong điều kiện thử đã ghi lại; lỗi âm thanh có hướng xử lý rõ ràng.

### Mốc 4: Bộ nhớ có kiểm soát

- [x] SQLite cục bộ, chỉ mở khi người dùng chủ động chạy công cụ bộ nhớ.
- [x] Công cụ terminal thêm/xem/sửa/xóa, xác nhận trước mọi thay đổi.
- [ ] Tích hợp truy xuất bộ nhớ có chọn lọc và giới hạn dữ liệu gửi tới API. Hiện không đọc/gửi bộ nhớ trong chat.
- [x] Kiểm thử xóa, quyền riêng tư của file và lưu qua khởi động lại; dữ liệu bộ nhớ không nằm trong Git.

**Hoàn thành khi:** lưu được thông tin mẫu qua lần khởi động lại, sửa/quên đúng mục và không truy xuất lại mục đã xóa.

### Mốc 5: Vận hành ổn định

- [ ] Viết hướng dẫn cài đặt, cấu hình và khắc phục lỗi.
- [ ] Thêm cơ chế khởi động cùng thiết bị nếu cần.
- [ ] Kiểm thử mất mạng, kết nối lại, rút thiết bị âm thanh và khởi động lại.
- [ ] Chạy thử liên tục theo thời lượng được thống nhất; ghi CPU, RAM, nhiệt độ và lỗi.
- [ ] Đặt giới hạn lượt gọi, xử lý giới hạn dịch vụ và kiểm soát chi phí.

**Hoàn thành khi:** có quy trình tái tạo bản chạy và kết quả kiểm thử trên Pi 5 thực tế. Không dùng kết quả trên máy phát triển để khẳng định đã kiểm chứng phần cứng.

## 7. Tổ chức mã nguồn dự kiến

Đã tạo `src/milu/app.py`, `state.py`, `conversation.py`, `providers.py`, `memory.py`, `ui/` và `tests/`. Bản nhỏ dùng các module này trước; có thể tách thành các thư mục dưới đây khi dự án lớn hơn. Phần âm thanh chưa có:

- `src/milu/ui/`: khuôn mặt và hoạt ảnh.
- `src/milu/conversation/`: điều phối và trạng thái hội thoại.
- `src/milu/providers/`: kết nối API và dịch vụ giả cho kiểm thử.
- `src/milu/audio/`: thu và phát âm thanh.
- `src/milu/memory/`: lưu trữ và truy xuất có kiểm soát.
- `tests/`: kiểm thử tự động không phụ thuộc API thật.
- `docs/`: thiết kế, quyết định và hướng dẫn vận hành.

Cấu trúc có thể điều chỉnh sau bản thử. Ưu tiên ít thành phần, dễ chạy và dễ kiểm tra.

## 8. Bảo mật và chi phí

- Không commit khóa API, tệp `.env`, cơ sở dữ liệu, âm thanh hoặc hội thoại cá nhân.
- Trước khi thêm mã nguồn, tạo `.gitignore` phù hợp và tệp cấu hình mẫu chỉ chứa giá trị giả.
- Lưu khóa ở cấu hình cục bộ có quyền truy cập phù hợp; không in khóa trong nhật ký hoặc lỗi.
- Không thực thi lệnh hệ thống do mô hình tạo ra. Nội dung trả lời không được coi là quyền điều khiển thiết bị.
- Giới hạn thời lượng thu âm, lượng văn bản, số lượt gọi và số lần thử lại. Không thử lại vô hạn.
- Kiểm tra giá và chính sách dữ liệu hiện hành của dịch vụ trước khi dùng. Chưa đưa ra dự toán khi chưa chốt mô hình và mức sử dụng.
- Nếu khóa bị đưa vào Git, thu hồi và thay khóa; chỉ xóa dòng trong commit mới không đủ.
- Không tự áp dụng giấy phép phần mềm trước khi chủ dự án chọn.

## 9. Bước tiếp theo

Tiếp tục **Mốc 0 và Mốc 1**: xác định đúng model màn hình rồi chạy bản khuôn mặt ngoại tuyến trên Raspberry Pi 5. Phần mềm đã có thể chạy thử trên máy phát triển, gồm cả chat giả; chỉ chốt Mốc 1 sau khi kiểm tra thiết bị thật. Để hoàn tất Mốc 2 cần chọn mô hình/chi phí, tự cấu hình khóa tại máy và chạy một lượt API thật. Chưa cần khóa API để thử khuôn mặt, chat giả hoặc bộ nhớ cục bộ. Mốc 3 còn chờ phần âm thanh; Mốc 4 còn phần truy xuất bộ nhớ có kiểm soát vào hội thoại.

