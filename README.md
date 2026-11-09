# MiluAgent

Milu là dự án trợ lý AI mang hình tượng chú chó, hướng tới **Raspberry Pi 5** và thể hiện cảm xúc qua màn hình.

## Bản hiện tại: khuôn mặt ngoại tuyến

Đã có bản thử Python/Pygame với năm trạng thái, chớp mắt, chuyển động nhẹ, miệng nói và chế độ trình diễn. Bản này **không gọi API, không thu âm, không lưu hội thoại**. “Lắng nghe” và “đang nói” hiện chỉ là biểu cảm mô phỏng.

Đã kiểm thử tự động trên Linux bằng màn hình giả lập. Chưa kiểm chứng trên Raspberry Pi 5, LCD thật hoặc thiết bị âm thanh. Mốc 0 và phần kiểm tra phần cứng của Mốc 1 còn mở.

## Chạy thử

Cần Python 3.10 trở lên và môi trường đồ họa. Trong thư mục repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m milu --demo
```

Trên Raspberry Pi OS, nếu thiếu công cụ tạo môi trường ảo, cài gói `python3-venv` bằng trình quản lý gói của hệ điều hành trước. Thư viện Pygame phụ thuộc SDL; quá trình cài đặt trên đúng phiên bản Pi OS cần được kiểm tra thực tế.

Mặc định cửa sổ là 480 × 320, **chỉ là kích thước giả định để phát triển**, không phải thông số LCD đã xác nhận:

```sh
python -m milu --width 800 --height 480
python -m milu --fullscreen --demo
```

Toàn màn hình dùng độ phân giải hiện tại của hệ điều hành. Khuôn mặt giữ đúng tỷ lệ, thêm khoảng trống khi tỷ lệ màn hình khác. Ứng dụng cần màn hình mà SDL nhận được; chưa bao gồm driver LCD SPI hay cài đặt phần cứng.

### Điều khiển

- `1`: chờ; `2`: lắng nghe; `3`: xử lý; `4`: trả lời; `5`: lỗi.
- Mũi tên trái/phải: chuyển trạng thái.
- `Space`: bật/tắt trình diễn, đổi trạng thái mỗi 3 giây.
- Chọn trạng thái bằng tay sẽ tắt trình diễn.
- `H`: ẩn/hiện gợi ý phím. `Esc`, `Q` hoặc đóng cửa sổ: thoát.

Các nhãn trên LCD dùng tiếng Anh ngắn để dễ đọc ở màn hình nhỏ. Hướng dẫn dự án dùng tiếng Việt.

## Kiểm thử không cần màn hình hoặc khóa API

Sau khi cài đặt:

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m milu --headless --seconds 1 --demo --screenshot artifacts/milu.png
```

`--headless` bắt buộc có `--seconds` để không chạy vô hạn. `--screenshot` chỉ lưu khung hình ứng dụng tại đường dẫn cục bộ đã chỉ định. Thư mục `artifacts/` được loại khỏi Git.

Kiểm tra định dạng và lỗi tĩnh (dành cho phát triển):

```sh
python -m pip install -e ".[dev]"
ruff check src tests
ruff format --check src tests
```

## Tài liệu và việc tiếp theo

- [Kế hoạch tổng thể](docs/PLAN.md)
- [Quyết định kỹ thuật tạm thời và checklist phần cứng](docs/HARDWARE.md)
- [Kết quả kiểm thử bản đầu](docs/VALIDATION.md)

Bước tiếp theo là xác định model LCD, độ phân giải, giao tiếp và kiểm thử khuôn mặt trên Pi 5. Sau đó thêm hội thoại văn bản theo Mốc 2. Dịch vụ API, mô hình, chi phí và bộ nhớ vẫn chưa chốt.

## An toàn dữ liệu

Repository công khai. Không đưa khóa API, bản ghi âm, lịch sử trò chuyện, dữ liệu bộ nhớ hoặc thông tin cá nhân vào Git. Dùng dữ liệu giả trong ví dụ và kiểm thử. Chưa áp dụng giấy phép phần mềm; chủ dự án sẽ chọn riêng.
