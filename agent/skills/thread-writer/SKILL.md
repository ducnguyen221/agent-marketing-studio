---
name: thread-writer
description: >
  Viết thread nhiều post (X/Threads/LinkedIn) hoặc bài dài chia mạch từ một nội dung gốc.
  Dùng khi người dùng cần "thread", "chuỗi bài", "chia bài dài thành nhiều phần", hoặc tái
  chế một bài blog/video thành thread. Gọi từ content-production khi atomize nội dung.
---

# Thread Writer

> Chưng cất từ `blacktwist/social-media-skills` (MIT).

## Kiến trúc thread

```
Post 1 — HOOK        (đứng một mình cũng phải hay; dùng skill hook-writer)
Body posts           (mỗi post MỘT ý; đủ giá trị dù đọc lẻ)
Post cuối — CLOSER   (chốt bài học + CTA mềm)
```

- **Post 1** là 90% ăn thua: người ta quyết đọc tiếp hay lướt ngay đây. Kết bằng gợi ý
  "còn tiếp" (một dấu mở vòng), không phải "đọc thread nhé".
- **Body:** mỗi post tự đứng được — người vào giữa thread vẫn hiểu. Một ý/post, đừng nhồi.
- **Closer:** rút bài học lớn cả thread hé lộ + CTA mềm (theo dõi, lưu, hỏi).

## 4 format thread

| Format | Hợp với | Cấu trúc | Mở mẫu |
|---|---|---|---|
| **Listicle** | tips, công cụ, sai lầm, thói quen | "[N] thứ về [chủ đề]" — mỗi post 1 mục → chốt bài học chung | "7 thói quen viết giúp tôi gấp đôi sản lượng. (Thread:)" |
| **Story Arc** | hành trình, case study, bài học từ thất bại/thành công | Setup → Conflict → Resolution → Lesson | "3 năm trước tôi suýt bỏ cuộc. Giờ điều hành business 7 chữ số. Đây là thread tôi ước có ai viết cho mình lúc đó." |
| **Framework** | quy trình, hệ thống, playbook lặp lại được | Đặt tên framework → định nghĩa từng bước → cho thấy đầu ra | "Framework 5 bước tôi dùng để viết cả tháng content trong một buổi chiều. (Lưu lại.)" |
| **Breakdown** | mổ xẻ một ví dụ/case cụ thể | Chọn đối tượng → tách từng phần → rút nguyên lý | "Bài này đạt 2 triệu view. Đây là lý do, từng dòng một." |

## Cách dùng
1. Xác định format theo bản chất nội dung (đừng ép story arc cho nội dung tips).
2. Viết Post 1 bằng `hook-writer` (chọn pattern hợp format).
3. Viết body — một ý/post, giữ mạch, đừng lặp thuật ngữ đã giải thích ở post trước.
4. Closer + CTA mềm.
5. Nếu thread sinh từ một bài gốc (blog/video) → giữ liên kết về bản đầy đủ ở post cuối.

## Luật
- Mỗi post trong giới hạn ký tự của kênh (X ≤280).
- Không markdown literal trên nền tảng không render (X/Facebook).
- Đây là một bản FORMAT LẠI của nội dung gốc — không dán y nguyên blog thành thread.
