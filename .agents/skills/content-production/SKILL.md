---
name: content-production
description: >
  Sản xuất nội dung sẵn-đăng theo từng kênh từ một Content ĐÃ DUYỆT và dữ kiện đã kiểm chứng.
  Dùng khi soạn bài blog, post social, caption, newsletter, landing copy, hoặc tái chế nội
  dung. Chạy ở khâu ③ produce, sau cổng 1.
---

# Content Production

> Chưng cất từ `content-production` (KPIM 30_MARKETING) + `COPY_FRAMEWORKS.md`.

## Mục đích
Biến brief đã duyệt + dữ kiện đã xác minh → asset sẵn-đăng đúng format từng kênh.

## Quy trình
1. Đọc frontmatter `campaign.md` + dòng Content (`core_brief`, `audience_profile`, `constraints`,
   `key_sources`, `creative_direction`), hồ sơ `.md` Mục 4 và Mục 5.
2. Chọn công thức phù hợp: tiêu đề + khung bài (`COPY_FRAMEWORKS.md`), giọng theo kênh
   (`output_styles/`). Cùng 1 nội dung gốc → FORMAT LẠI theo từng kênh, không copy y nguyên.
3. Sản xuất asset đúng định dạng và ngôn ngữ yêu cầu.
4. **Gắn nhãn `[KIỂM CHỨNG]`** cho mọi số/claim chưa xác minh được — không bịa.
5. Chạy `checklists/QA_ASSET.md` trước khi đẩy sang người duyệt (đặc biệt: grep tên tool
   nội bộ = rỗng; đúng giới hạn hashtag theo kênh; không lộ PII).

## Đầu ra
- **Một** file `content.md` trong thư mục bài chứa text của MỌI kênh, tách bằng heading
  `## post:<post_format>`. Không tách ra nhiều file `.txt`/`.md` theo kênh.
- **Một dòng Post cho mỗi khối**, với `post_content` = anchor tương ứng (vd `post:facebook_post`;
  trùng format thì thêm `#2`). `channel` chỉ lấy từ `Campaign.channels`.
- Danh sách CTA + claim cần nguồn.
- `Content.status = in_production`, `Post.agent_status = completed`.

**Bất biến phải giữ:** số khối `## post:` = số dòng Post. Lệch = khối mồ côi hoặc anchor chết.

## Ranh giới (bắt buộc)
- KHÔNG bịa kết quả hiệu quả, lời khách hàng, logo, endorsement, điều khoản ưu đãi.
- Nội dung public phải đúng giọng của kênh: `profile.md` ở gốc kênh + `output_styles/`.
- Phát hành và phân phối trả phí cần người duyệt — cổng 2 (`Post.review_status = approved`).
