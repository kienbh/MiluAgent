# MiluAgent

Milu là trợ lý AI mang hình tượng chú chó, hướng tới **Raspberry Pi 5 với LCD HAT 3,5 inch**. Model màn hình, độ phân giải và driver cụ thể vẫn cần xác nhận.

## Bản hiện tại

- Khuôn mặt có 5 trạng thái, chớp mắt, chuyển động và demo ngoại tuyến.
- Hội thoại văn bản tiếng Việt với mặt Milu đổi theo trạng thái xử lý/trả lời.
- Phản hồi giả mặc định; adapter OpenAI/Claude chỉ hoạt động khi cấu hình và bật rõ ràng.
- Giới hạn lượt gọi, ngữ cảnh, thời gian chờ; hủy và bỏ phản hồi cũ.
- Bộ nhớ SQLite cục bộ với xem, thêm, sửa, xóa có xác nhận. Chưa tự đưa bộ nhớ vào hội thoại.

**Mặc định không gọi mạng, không thu âm và không lưu hội thoại.** Chưa có giọng nói hoặc kiểm chứng trên Pi 5/LCD thật. API được kiểm thử bằng HTTP giả, chưa gọi dịch vụ thật.

## Cài và chạy

Cần Linux với Python 3.10+, môi trường đồ họa và Pygame/SDL. Trong repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m milu --demo
```

Nếu Raspberry Pi OS thiếu môi trường ảo hoặc font tiếng Việt, cần các gói hệ điều hành `python3-venv` và `fonts-dejavu-core`. Cài đặt Pygame trên ARM và driver LCD vẫn cần thử trên thiết bị thật.

Thử hội thoại bằng phản hồi giả, không cần khóa API:

```sh
python -m milu --chat --width 800 --height 600
```

Gõ rồi Enter để gửi; Esc hủy chờ; Page Up/Down cuộn; Ctrl+L xóa ngữ cảnh; Ctrl+Q thoát.

[Hướng dẫn cấu hình API và bộ nhớ](docs/CHAT_AND_MEMORY.md) giải thích dữ liệu được gửi, giới hạn và cách bật dịch vụ. Không đưa khóa API vào repo hoặc chat.

### Màn hình và phím của chế độ khuôn mặt

```sh
python -m milu --width 800 --height 480
python -m milu --fullscreen --demo
```

Mặc định 480 × 320 chỉ là kích thước phát triển, không phải thông số LCD đã xác nhận. Toàn màn hình dùng độ phân giải hiện tại của hệ điều hành. Ứng dụng giữ tỷ lệ khuôn mặt; chưa bao gồm driver LCD HAT/SPI.

- `1` chờ; `2` lắng nghe; `3` xử lý; `4` trả lời; `5` lỗi.
- Mũi tên: chuyển trạng thái. `Space`: bật/tắt demo.
- `H`: gợi ý phím. `Esc`, `Q` hoặc đóng cửa sổ: thoát.
- Chế độ chat có phím riêng như hướng dẫn bên trên; không dùng `Q` đơn lẻ để thoát khi đang nhập văn bản.

Các nhãn biểu cảm là trạng thái giao diện, chưa phải hoạt động thu/phát âm thanh.

## Kiểm thử không cần API hoặc thiết bị thật

```sh
python -m pip install -e ".[dev]"
ruff check src tests
ruff format --check src tests
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m milu --headless --seconds 1 --demo --screenshot artifacts/milu.png
python -m milu --chat --headless --seconds 1 --screenshot artifacts/chat.png
```

`--headless` bắt buộc có `--seconds` để kết thúc. Ảnh chụp có thể chứa văn bản hiển thị, nên xem kỹ trước khi chia sẻ; `artifacts/` không được Git theo dõi.

## Tài liệu

- [Kế hoạch và tiến độ](docs/PLAN.md)
- [Cấu hình tạm thời, checklist LCD/Pi](docs/HARDWARE.md)
- [Hội thoại, API và bộ nhớ](docs/CHAT_AND_MEMORY.md)
- [Kết quả và giới hạn kiểm thử](docs/VALIDATION.md)

## An toàn dữ liệu

Repository công khai. Không đưa khóa API, âm thanh, lịch sử hội thoại, cơ sở dữ liệu bộ nhớ hoặc thông tin cá nhân vào Git. Chỉ dùng dữ liệu giả trong ví dụ và kiểm thử. Chưa áp dụng giấy phép phần mềm; chủ dự án sẽ chọn riêng.
