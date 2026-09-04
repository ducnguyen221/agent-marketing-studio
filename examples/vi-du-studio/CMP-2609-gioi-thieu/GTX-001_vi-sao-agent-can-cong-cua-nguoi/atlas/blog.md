# Vì sao một xưởng nội dung chạy bằng agent vẫn cần cổng của người

**Bài này nói về quy trình nội dung với AI agent, và về một bài viết đã đi qua đủ mọi khâu
kiểm tra tự động mà vẫn không nên đăng.**

Không phải vì mô hình yếu. Bài đó đúng ngữ pháp, đúng độ dài, đủ nguồn, không link gãy.
Nó chỉ không đáng đăng — và không có cổng máy nào nói được điều đó.

## Cổng tự động kiểm được cái gì

Xưởng này có 23 cổng chạy bằng số: độ dài bài, số nguồn trong phần nghiên cứu, link còn
sống hay đã chết, chữ mẫu còn sót lại, tên công cụ nội bộ lọt ra bản công khai. Mỗi cổng
trả về một trong ba trạng thái: **xanh · đỏ · thiếu**.

Trạng thái thứ ba mới là điều đáng nói. "Thiếu" nghĩa là cổng không chạy được — file không
có, tham số không truyền. Nó **không bao giờ** được cộng vào "xanh". Cổng không chạy được
là *chưa biết*, không phải *đã qua*.

> 💡 Một hệ kiểm tra mà trạng thái "không kiểm được" bị tính là "đạt" thì càng nhiều cổng
> càng nguy hiểm: nó tạo cảm giác an toàn mà không tạo ra an toàn.

## Hai chỗ máy không nên tự quyết

**Chỗ thứ nhất: chọn đề tài.** Viết về cái gì là một quyết định chiến lược — nó tiêu tiền,
tiêu uy tín, và loại trừ những đề tài khác. Script tạo bài ở trạng thái đề xuất với ô duyệt
để **trống**; không có đường nào trong mã tự đặt thành đã duyệt. Người điền ngày vào ô đó,
và đó là chữ ký.

**Chỗ thứ hai: duyệt trước khi đăng.** Đây là chỗ cuối cùng còn sửa được rẻ. Sau khi đăng,
sửa một bài đã có người đọc và người chia sẻ đắt hơn nhiều lần. Lệnh duyệt bắt buộc phải
có tên người duyệt và câu duyệt nguyên văn — duyệt mà không để lại dấu vết thì sáu tháng
sau không ai biết ai đã đồng ý với cái gì.

## Cái máy dò kim loại không bắt được

Máy dò ở sân bay bắt được kim loại. Nó không bắt được ý định. Cổng tự động của xưởng nội
dung cũng vậy: bắt được hình thức, không bắt được *bài này có đáng đăng không*.

Câu hỏi đó cần một người biết chiến dịch đang nhắm ai, đã hứa gì với họ, và tuần trước đã
nói gì. Không có mô hình nào trả lời hộ được, vì câu trả lời không nằm trong bài.

## Góc nhìn thẳng

Cổng người **làm chậm**. Đó là thứ được chọn, không phải thứ phải chịu đựng. Nhưng nếu đo
sai thì sẽ bỏ nó: đừng đo bằng *số bài mỗi tuần*, hãy đo bằng *số bài phải gỡ hoặc sửa sau
khi đã đăng*. Xưởng này chưa chạy đủ lâu để có con số đó, nên bài này không nêu con số nào.

Ai hợp: người có thương hiệu để mất. Ai không hợp: người cần một trăm bài tuần này.

## Kết luận

Thứ làm nội dung dùng được không nằm ở chỗ mô hình viết hay hơn. **Không phải mô hình mạnh
hơn, mà là chỗ người đặt tay vào.**

Muốn xem hai cổng đó trông thế nào trong mã, xưởng này để mở — clone về và chạy một bài
tới bước đăng.
