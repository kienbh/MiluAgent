# Cấu hình thử và việc cần xác nhận

## Quyết định tạm thời cho bản ngoại tuyến

- Python 3.10+ và Pygame 2.6.1: đủ để vẽ hoạt ảnh, nhận phím và kiểm thử không cần màn hình thật.
- Vẽ bằng hình học, không tải tài sản đồ họa từ bên ngoài.
- Khung thiết kế 480 × 320, hiển thị giữ tỷ lệ theo cửa sổ hoặc màn hình thực tế.
- 30 khung hình/giây mặc định; điều chỉnh bằng `--fps` trong khoảng 1–60.
- Chỉ khởi tạo màn hình và font ở chế độ khuôn mặt. Chat dùng phản hồi giả mặc định; cloud yêu cầu cấu hình và bật rõ ràng. Không khởi tạo mixer/micro hoặc mở bộ nhớ khi chạy giao diện.
- Các quyết định này có thể đổi sau khi kiểm tra trên Pi, không khóa vào một model LCD.

## Thông tin đã xác nhận

- Raspberry Pi 5.
- LCD HAT 3,5 inch cắm vào Pi.

Chưa có model, độ phân giải hoặc driver. HAT không đủ để kết luận giao tiếp là SPI hay chọn lệnh cài driver.

## Chưa biết, cần ghi lại trên thiết bị

- [ ] RAM của Raspberry Pi 5 và phiên bản Raspberry Pi OS.
- [ ] Tên/model đầy đủ của màn hình, không chỉ kích thước 3,5 inch.
- [ ] Giao tiếp HDMI, DSI hay SPI; độ phân giải gốc; hướng đặt màn hình.
- [ ] Driver tương thích Pi 5, cách màn hình xuất hiện với SDL/desktop.
- [ ] Nguồn điện, tản nhiệt và dung lượng lưu trữ.
- [ ] Micro, loa và cách kết nối, dành cho giai đoạn giọng nói.

Chỉ chia sẻ thông số kỹ thuật cần thiết. Không đăng số sê-ri, địa chỉ mạng riêng, mật khẩu Wi-Fi hoặc thông tin tài khoản lên repository.

## Checklist chạy thật cho Mốc 1

1. Cài và chạy ứng dụng từ môi trường đồ họa của Pi.
2. Thử `python -m milu --demo`, sau đó `--fullscreen --demo`.
3. Kiểm tra đủ 5 trạng thái, chữ không bị cắt, hình giữ tỷ lệ.
4. Thử chọn trạng thái nhiều lần, bật/tắt demo, ẩn/hiện trợ giúp, đổi kích thước cửa sổ.
5. Thoát bằng Esc và nút đóng, rồi mở lại ứng dụng.
6. Chạy thử ít nhất 10 phút như một phép kiểm tra ban đầu; ghi FPS quan sát/đo được, CPU, RAM, nhiệt độ và hiện tượng giật/treo. Đây là đề xuất phép đo, chưa phải kết quả.
7. Ghi rõ hệ điều hành, độ phân giải, tùy chọn chạy và điều kiện tản nhiệt bên cạnh kết quả.

Chưa đánh dấu Mốc 1 hoàn tất cho đến khi có kết quả trên thiết bị thật. Chưa cần khóa API để chạy các bước này.
