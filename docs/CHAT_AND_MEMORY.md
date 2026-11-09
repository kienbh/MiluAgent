# Hội thoại và bộ nhớ

## Thử ngay, không cần khóa API

```sh
python -m milu --chat --width 800 --height 600
```

Mặc định dùng `fake`: câu trả lời cố định, ngoại tuyến, chỉ để kiểm thử luồng nhập → xử lý → trả lời. Đây chưa phải hội thoại AI thật. Ứng dụng không thu âm, không đọc file bộ nhớ và không tự lưu lịch sử.

Giao diện cần font có đủ dấu tiếng Việt. Bản này tìm DejaVu Sans, Noto Sans hoặc Liberation Sans. Trên Raspberry Pi OS có thể cài gói `fonts-dejavu-core` nếu máy chưa có font phù hợp. Nếu thiếu, ứng dụng báo lỗi thay vì hiển thị chữ mất dấu.

### Phím trong chế độ chat

- Gõ nội dung rồi Enter để gửi. Tối đa 2.000 ký tự mỗi lần.
- Esc: ngừng chờ và bỏ kết quả của lượt hiện tại. Không thoát ứng dụng.
- Page Up/Page Down hoặc con lăn: cuộn câu trả lời.
- Ctrl+L: xóa ngữ cảnh phiên trong RAM, giữ bộ đếm lượt gọi.
- Ctrl+Q hoặc đóng cửa sổ: thoát.

Phím của bản chỉ hiển thị khuôn mặt vẫn giữ nguyên. Các chữ “listening”/“speaking” là trạng thái giao diện; chưa có thu âm hay phát giọng nói.

## Bật một dịch vụ AI khi đã sẵn sàng

Chỉ bật sau khi chọn dịch vụ, mô hình, giá và chính sách dữ liệu phù hợp. Không có mô hình cloud mặc định và không tự chuyển sang nhà cung cấp khác.

1. Thiết lập `OPENAI_API_KEY` hoặc `ANTHROPIC_API_KEY` trong môi trường cục bộ của ứng dụng. Không nhập khóa vào chat, tham số dòng lệnh, GitHub, ảnh chụp hoặc bộ nhớ Milu. Ứng dụng không đọc tệp `.env` tự động.
2. Thay `MODEL_ID` bên dưới bằng model ID thực tế mà tài khoản có quyền dùng.
3. Chỉ dùng `--allow-cloud` khi đồng ý gửi văn bản nhập và tối đa bốn lượt hỏi đáp trước của phiên đến dịch vụ đã chọn.

OpenAI:

```sh
python -m milu --chat --provider openai --model MODEL_ID --allow-cloud
```

Anthropic/Claude:

```sh
python -m milu --chat --provider anthropic --model MODEL_ID --allow-cloud
```

Không có lệnh nào ở bước phát triển này gửi yêu cầu API thật. Hai adapter hiện được kiểm thử bằng phản hồi HTTP giả; cần chạy một lượt thử thật sau khi chủ dự án tự cấu hình và chấp thuận chi phí/dữ liệu.

### Giới hạn và xử lý lỗi

- Mặc định 20 lượt gọi mỗi lần mở ứng dụng: `--max-requests 20` (1–100).
- Mặc định tối đa 512 output token: `--max-output-tokens 512` (64–2.048). Đây là giới hạn token, không phải cam kết chi phí tiền.
- Chờ tối đa 20 giây trên giao diện: `--timeout 20` (lớn hơn 0, tối đa 120).
- Chỉ một tác vụ mạng chạy tại một thời điểm, không tự retry hay fallback.
- Các lượt bị hủy, lỗi hoặc hết thời gian vẫn tính vào giới hạn số lần gửi; dịch vụ có thể đã xử lý và tính phí.
- Khi hủy/hết thời gian, phản hồi cũ không được ghi đè lượt mới hay thêm vào ngữ cảnh. Tác vụ mạng đang chạy có thể chưa kết thúc; ứng dụng chờ tác vụ đó thoát trước khi cho gửi tiếp.
- Timeout HTTP là timeout thao tác socket, không bảo đảm hạn chót tuyệt đối cho DNS hoặc dữ liệu đến rất chậm. Giao diện vẫn hoạt động và có thể thoát; nếu worker không kết thúc, mở lại ứng dụng để thử sau.
- Lỗi hiển thị dùng thông báo cố định, không đưa thân phản hồi lỗi hoặc khóa API ra màn hình.
- Kết quả chưa hoàn thành do chạm giới hạn token không được đưa vào lịch sử như một câu trả lời hoàn chỉnh.
- Thống kê token chỉ có khi dịch vụ trả về; giữ trong RAM, không ghi nội dung hội thoại vào nhật ký.

Ngữ cảnh giữ tối đa bốn lượt thành công, tối đa 4.000 ký tự câu trả lời mỗi lượt. Câu trả lời dài hơn được rút gọn. Ctrl+L và thoát xóa ngữ cảnh trong ứng dụng, không xóa dữ liệu đã gửi cho nhà cung cấp.

OpenAI adapter gửi `store: false`. Điều này không có nghĩa dịch vụ không lưu bất cứ dữ liệu nào. Xem chính sách hiện hành của nhà cung cấp. Không có quyền truy cập hay nhập bộ nhớ từ ChatGPT hoặc sản phẩm khác.

Tài liệu API đã đối chiếu:
- [OpenAI Responses](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create)
- [Anthropic API overview](https://platform.claude.com/docs/en/api/overview)

## Bộ nhớ cục bộ, chủ động lưu

Bộ nhớ được quản lý riêng qua terminal Linux. Nó **chưa được tự truy xuất vào hội thoại hoặc gửi tới API**. Bản này không mở cơ sở dữ liệu khi khởi động khuôn mặt/chat.

```sh
python -m milu.memory list
python -m milu.memory add
python -m milu.memory edit 1
python -m milu.memory delete 1
python -m milu.memory clear
```

`add`/`edit` hỏi nội dung sau khi chạy, không nhận văn bản trên dòng lệnh để tránh lưu vào shell history. Mọi thay đổi yêu cầu gõ chính xác `yes`; nhập khác hoặc hủy thì không thay đổi dữ liệu.

- Mặc định: `~/.local/share/milu/memory.sqlite3`.
- Đổi đường dẫn nếu cần: `python -m milu.memory --db /duong/dan/rieng/memory.sqlite3 list`.
- Tối đa 1.000 mục, mỗi mục 4.096 ký tự Unicode, kèm thời điểm tạo/cập nhật.
- Thư mục mới dùng quyền 0700, file mới dùng 0600. Từ chối symlink, hardlink, file phụ SQLite không an toàn và quyền truy cập quá rộng. Không tự thay quyền của file đã có.
- Dữ liệu **không mã hóa**. Không lưu mật khẩu, khóa API hoặc thông tin nhạy cảm không cần thiết.
- SQLite bật `secure_delete`, nhưng không bảo đảm xóa khỏi bản sao lưu, snapshot hoặc các bản còn lại trên bộ nhớ flash.
- Không tự lưu bản ghi âm, hội thoại, ảnh, tài khoản hay nhập dữ liệu từ nơi khác.

Chỉ chạy thao tác xóa khi thực sự muốn xóa. Dùng dữ liệu giả để thử lần đầu. `--screenshot` của giao diện có thể lưu văn bản đang hiển thị vào ảnh cục bộ; kiểm tra trước khi chia sẻ. Thư mục `artifacts/` đã được loại khỏi Git.

## Chưa triển khai

Giọng nói, từ đánh thức, loa/micro, kết nối bộ nhớ vào câu trả lời, điều khiển phần cứng và hành động trên tài khoản bên ngoài vẫn là các bước sau. Chưa tự cài driver LCD HAT hoặc giả định model màn hình.
