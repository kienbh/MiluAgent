# MiluAgent

Milu là dự án trợ lý AI mang hình tượng chú chó, chạy trên **Raspberry Pi 5** và thể hiện cảm xúc qua màn hình.

## Trạng thái

Repository hiện chứa kế hoạch ban đầu, chưa có mã nguồn ứng dụng hoặc bản chạy thử. Các lựa chọn kỹ thuật trong kế hoạch là đề xuất, chưa phải tính năng đã hoàn thành.

## Định hướng đã xác định

- Xây dựng trợ lý Milu trên Raspberry Pi 5.
- Hiển thị khuôn mặt và cảm xúc để việc tương tác gần gũi hơn.
- Phát triển từng bước, kiểm chứng trên thiết bị thật trước khi mở rộng.

## Kế hoạch

Đọc [kế hoạch triển khai](docs/PLAN.md) để xem phạm vi bản đầu, kiến trúc đề xuất, các mốc thực hiện và tiêu chí kiểm tra.

Các hướng đang cân nhắc gồm màn hình LCD 3,5 inch, hội thoại bằng giọng nói, kết nối API OpenAI hoặc Claude và bộ nhớ riêng cho Milu. Cấu hình phần cứng, dịch vụ, chi phí và cách lưu dữ liệu cần được chốt trước khi triển khai.

## An toàn dữ liệu

Repository này công khai. Không đưa khóa API, bản ghi âm, lịch sử trò chuyện, dữ liệu bộ nhớ hoặc thông tin cá nhân vào Git. Chỉ dùng dữ liệu giả trong ví dụ và kiểm thử.
