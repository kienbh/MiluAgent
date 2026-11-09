# Kiểm thử bản 0.2

## Môi trường và kết quả

Linux x86_64, Python 3.12.14, Pygame 2.6.1, SDL dummy display. Đây là môi trường phát triển, không phải Raspberry Pi 5 hoặc LCD HAT thật.

- `python -m unittest discover -s tests -v`: **66 kiểm thử đạt**.
- `python -m compileall -q src tests`: đạt.
- Ruff 0.17.4: lint và kiểm tra định dạng đạt.
- Cài lại bản 0.2 thành công trong môi trường ảo; `pip check` đạt. Không thêm phụ thuộc runtime ngoài Pygame.
- Smoke test khuôn mặt và chat giả: chạy headless có giới hạn thời gian, tạo PNG và thoát thành công.
- Đã xem trực tiếp ảnh 5 biểu cảm; kiểm tra ảnh chat có dấu tiếng Việt ở 480 × 320. Đã sửa font thiếu ký tự bằng font hệ thống hỗ trợ tiếng Việt, có kiểm thử ký tự đại diện. Ưu tiên đường dẫn font chuẩn của Debian/Pi OS để tránh timeout khi dò font bằng fontconfig.

## Phạm vi tự động

### Khuôn mặt và ứng dụng

24 kiểm thử nền: trạng thái, demo, phím lặp, vòng chuyển, kích thước ngang/dọc/nhỏ, giữ tỷ lệ, hoạt ảnh, tham số lỗi, lưu ảnh, resize, đóng/mở lại và lỗi màn hình. Không khởi tạo mixer.

### Hội thoại và giao diện chat

22 kiểm thử: nhập tiếng Việt, giới hạn đầu vào, gửi/nhận, biểu cảm, ngữ cảnh tối đa bốn lượt, giới hạn số lần gọi, timeout, hủy, phản hồi cũ, worker duy nhất, lỗi không lộ dữ liệu, xóa ngữ cảnh, đóng phiên, cuộn, font, không xử lý lệnh gửi xếp sau sự kiện đóng, cấu hình cloud bắt buộc đồng ý và không gọi API khi chỉ mở ứng dụng.

### Provider

12 kiểm thử HTTP giả: đúng endpoint/payload/header, tách system cho Anthropic, parse văn bản/usage, từ chối cấu hình thiếu, không đoán mô hình, fake không gọi mạng, chặn redirect, không retry, lỗi xác thực/rate limit/timeout/mạng, JSON lỗi, phản hồi quá lớn và kết quả chưa hoàn thành.

**Không có API call thật hoặc khóa thật trong kiểm thử.** Các bài này không xác nhận tài khoản có quyền dùng model hay dịch vụ đang hoạt động.

### Bộ nhớ

8 kiểm thử: Unicode, CRUD, lưu qua mở lại, giới hạn, rollback, quyền file, symlink/hardlink, file phụ SQLite, xác nhận và hủy, CLI, không nhận nội dung trên dòng lệnh, import/help không tạo nơi lưu mặc định.

Không có bộ nhớ nào được đưa vào yêu cầu API. Database dùng dữ liệu giả trong thư mục tạm.

## CI

`.github/workflows/test.yml` chạy lint, định dạng, toàn bộ kiểm thử, compile và hai smoke test trên GitHub Actions. Xem tab Actions của đúng commit để biết kết quả CI hiện tại.

## Chưa kiểm chứng hoặc chưa triển khai

- Cài đặt ARM, driver/model LCD HAT, độ phân giải, cảm ứng, xoay màn hình và toàn màn hình thật.
- CPU, RAM, nhiệt độ, FPS và chạy dài trên Pi.
- Thao tác với bàn phím/IME và trình quản lý cửa sổ thật; các luồng hiện được kiểm tra bằng sự kiện giả lập và ảnh render.
- Gọi OpenAI/Claude thật, chi phí, quyền model và mạng thật.
- Giọng nói, micro/loa và bộ nhớ tích hợp vào câu trả lời.

Timeout/cancel không bảo đảm dừng request đã gửi hoặc tránh bị nhà cung cấp tính phí. Bộ nhớ không mã hóa; xóa SQLite không bảo đảm xóa bản sao lưu/flash. Xem [hướng dẫn dữ liệu](CHAT_AND_MEMORY.md) và [checklist phần cứng](HARDWARE.md).
