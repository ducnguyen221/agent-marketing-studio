---
schema: brand/1
channel: ten-kenh            # = channel.yml:id
label: "Tên kênh đọc được"
tagline: "Câu định vị một dòng"
tagline_short: "Bản ngắn, dùng cho video/short"
welcome: "Câu chào — dùng ở email và trang chủ"
email_accent: ""             # màu nhấn cho email (nền trắng cần đủ tương phản)
---

# <Tên kênh> — hồ sơ kênh

> **MỘT file duy nhất định nghĩa kênh này, cho người và cho agent.**
>
> Ba loại file, ba vai, đừng trộn:
> · `channel.yml` — **máy** đọc (đường dẫn, nền tảng, trụ nội dung, khoá `brand:`)
> · `brand.md` — **người** đọc và sửa (file này): nhận diện, giọng, chính kiến, cái không làm
> · `<chiến-dịch>/campaign.md` — cấu hình + brief của TỪNG chiến dịch
>
> Frontmatter ở trên là phần agent bơm vào prompt; thân bài là phần agent ĐỌC để hiểu kênh.

## 1. Kênh này là gì

Một đoạn: kênh phục vụ ai, giải quyết chuyện gì, và **khác gì** những nguồn sẵn có.
Đừng viết khẩu hiệu — viết thứ mà người mới vào đọc xong là biết nên viết bài kiểu gì.

| Chiến dịch | Cho ai | Nhịp |
|---|---|---|
| | | |

## 2. Nhận diện

| | |
|---|---|
| Tên hiển thị | |
| Câu định vị | |
| Câu ngắn | |
| Câu chào | |
| Web / YouTube / Facebook | |

## 3. Giọng & chính kiến

Giọng của kênh, và **chính kiến** — thứ khiến bài của kênh này khác bài của bất kỳ ai khác.

> ⚠️ **Hồ sơ TÁC GIẢ không thuộc về đây nếu nhiều kênh chung một tác giả.** Đó là dữ kiện về
> *người*, không phải về *kênh*; chép nó vào từng `brand.md` thì sáu tháng sau các bản lệch
> nhau và không ai biết bản nào đúng. Để một bản dùng chung, ở đây chỉ **trỏ** tới.

## 4. Nguồn được phép dùng

Loại bằng chứng nào được dùng để chứng minh một khẳng định. Càng cụ thể càng ít phải sửa sau.

## 5. Cái KHÔNG bao giờ làm

Mục quan trọng nhất của file này. Mỗi gạch đầu dòng nên đến từ **một lần đã trả giá**, không
phải từ nguyên tắc chung chung.

-
-

## 6. Trụ nội dung

Vì sao chọn đúng bộ trụ ở `channel.yml:pillars`, và trụ nào đang để dành.

## 7. Thiết kế màu — GHI CHÉP hiện trạng

Ghi màu **đang dùng** và **nó nằm cứng ở file:dòng nào**. Đây là ghi chép, không phải nguồn
cấu hình — trừ khi engine thật sự đọc khoá đó (khi ấy nó thuộc `campaign.md`).

| Mặt | Màu | Ghi cứng tại |
|---|---|---|
| Web | | |
| Video | | |
| Email | | |
