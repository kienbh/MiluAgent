# Kiểm thử bản khuôn mặt ngoại tuyến

## Phạm vi đã chạy

Môi trường: Linux x86_64, Python 3.12.14, Pygame 2.6.1, SDL dummy display. Đây là môi trường phát triển, không phải Raspberry Pi 5 hoặc LCD thật.

- Cài đặt dự án thành công trong môi trường ảo mới bằng `python -m pip install -e .`.
- `python -m pip check`: không phát hiện phụ thuộc hỏng.
- `python -m unittest discover -s tests -v`: **24 kiểm thử đạt**.
- `python -m compileall -q src tests`: đạt.
- Ruff 0.17.4: `ruff check src tests` và `ruff format --check src tests` đều đạt.
- `python -m milu --headless --seconds 1 --demo --screenshot artifacts/milu.png`: thoát thành công, tạo được PNG.
- Lệnh `milu --headless --seconds 0.05 --state error` từ entry point đã cài: đạt.
- Đã xem trực tiếp ảnh render của đủ 5 trạng thái ở 480 × 320: không thấy chữ hoặc khuôn mặt bị cắt.

## Nội dung bộ kiểm thử

- Trạng thái ban đầu, chọn thủ công, demo, chuyển vòng, nhấn lặp lại và đồng hồ lùi.
- Phím 1–5, mũi tên, Space, H, Esc, Q và sự kiện đóng cửa sổ.
- Năm trạng thái cho hình khác nhau; hoạt ảnh đổi khung hình theo thời gian.
- Render ở các kích thước 480 × 320, 320 × 480, 240 × 160, 800 × 480 và bề mặt cực nhỏ.
- Giữ tỷ lệ bằng khoảng trống trên màn hình dọc.
- Giới hạn tham số, từ chối thời lượng không hợp lệ và yêu cầu headless không có thời điểm dừng.
- Chạy vòng lặp headless, ghi PNG, đổi kích thước, đóng rồi mở lại và báo lỗi màn hình.
- Dọn màn hình sau khi thoát; mixer không được khởi tạo.

Workflow `.github/workflows/test.yml` chạy lint, định dạng, 24 kiểm thử, compile và smoke test trên GitHub Actions. Kết quả CI thực tế cần xem ở tab Actions của commit tương ứng.

## Chưa kiểm chứng

- Cài đặt ARM, driver và đầu ra hiển thị trên Raspberry Pi 5.
- Độ phân giải, cảm ứng, xoay màn hình và giao tiếp của LCD cụ thể.
- Thao tác phím/đóng cửa sổ với trình quản lý cửa sổ thật; hiện đã kiểm tra bằng sự kiện giả lập.
- Chế độ toàn màn hình trên thiết bị thật.
- FPS thực tế, CPU, RAM, nhiệt độ và chạy dài trên Pi.
- API, micro, loa, hội thoại và bộ nhớ: chưa triển khai trong bản này.

Không suy ra tương thích phần cứng từ kiểm thử headless. Dùng [checklist phần cứng](HARDWARE.md) cho bước tiếp theo.
