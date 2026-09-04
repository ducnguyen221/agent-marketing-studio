# Một bài cố tình sai để cổng có cái mà bắt

Bài này KHÔNG phải bài mẫu để học theo. Nó là **fixture đỏ**: mỗi khiếm khuyết ở đây được
đặt vào có chủ đích, và `tests/test_blog_gates.py` khẳng định cổng nào phải đỏ vì lý do nào.
Sửa file này cho "đẹp hơn" sẽ làm test đỏ — nếu cần đổi, đổi cả test trong cùng một commit.

## Khiếm khuyết đã cài

1. Quá ngắn — chỉ vài trăm từ, dưới ngưỡng 2500 (G01 đỏ).
2. Chỉ có 3 mục H2, dưới ngưỡng 6 (G02 đỏ).
3. Không một nguồn ngoài nào (G05 đỏ) — đúng tình trạng thật của 2/3 bài đã đăng.
4. Không có khối chính kiến `> **Góc nhìn:**` (G06 đỏ).
5. Còn dấu [KIỂM CHỨNG] chưa đóng (G08 đỏ).
6. Không có callout emoji nào (G04 đỏ, mức cảnh báo).

## Một đoạn nội dung giả

Theo báo cáo nào đó, số liệu này chưa xác minh được [KIỂM CHỨNG]. Đoạn văn này tồn tại
chỉ để bài có chữ, không mang thông tin thật và không nên trích dẫn.

| Cột | Giá trị |
|---|---|
| Có bảng | để G03 xanh, chứng minh cổng không đỏ hàng loạt |

## Vì sao cần một fixture đỏ

Một bộ test chỉ chạy trên dữ liệu đẹp sẽ xanh mãi mãi kể cả khi cổng đã hỏng hoàn toàn.
Cách duy nhất biết cổng còn sống là cho nó một bài chắc chắn sai và bắt nó gọi tên
đúng từng lỗi. Xanh trên bài đẹp chứng minh cổng không kêu oan; đỏ đúng lý do trên bài
này chứng minh cổng còn kêu được.
