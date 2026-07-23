---
name: content-production
description: >
  Sản xuất nội dung sẵn-đăng theo từng kênh từ một brief ĐÃ DUYỆT và dữ kiện đã kiểm chứng.
  Dùng khi soạn bài blog, post social, caption, newsletter, landing copy, hoặc tái chế nội
  dung. Chạy ở stage draft, sau khi topic đã được duyệt.
---

# Content Production

> Chưng cất từ `content-production` (KPIM 30_MARKETING) + `COPY_FRAMEWORKS.md`.

## Mục đích
Biến brief đã duyệt + dữ kiện đã xác minh → asset sẵn-đăng đúng format từng kênh.

## Quy trình
1. Đọc brief campaign/bài, persona mục tiêu, kênh, CTA, các claim đã duyệt.
2. Chọn công thức phù hợp: tiêu đề + khung bài (`COPY_FRAMEWORKS.md`), giọng theo kênh
   (`output-styles/`). Cùng 1 nội dung gốc → FORMAT LẠI theo từng kênh, không copy y nguyên.
3. Sản xuất asset đúng định dạng và ngôn ngữ yêu cầu.
4. **Gắn nhãn `[KIỂM CHỨNG]`** cho mọi số/claim chưa xác minh được — không bịa.
5. Chạy `checklists/QA_ASSET.md` trước khi đẩy sang người duyệt (đặc biệt: grep tên tool
   nội bộ = rỗng; đúng giới hạn hashtag theo kênh; không lộ PII).

## Đầu ra
- Asset nháp + metadata kênh (ghi vào Sheet Post: `content_md`, `blog_md`, `fb_post`…).
- Danh sách CTA + claim cần nguồn.
- Trạng thái review + những gì còn chờ duyệt.

## Ranh giới (bắt buộc)
- KHÔNG bịa kết quả hiệu quả, lời khách hàng, logo, endorsement, điều khoản ưu đãi.
- Nội dung public phải đúng brand voice của instance (`output-styles/`).
- Phát hành và phân phối trả phí cần người duyệt (cổng `approve_content` / `approve_final`).
