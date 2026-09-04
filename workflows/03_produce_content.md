# Khâu ③: Sản Xuất Nội Dung Đa Kênh (Produce Content)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `content-producer` (hỗ trợ bởi `seo-specialist`, skills: `hook-writer`, `thread-writer`) |
| **Đầu vào (Input)** | Dòng trong bảng Content có `status = approved` và ô `g1` có ngày |
| **Công cụ (Tools)** | Markdown editor · `.agents/skills/hook-writer/` · `register_publish.py init` |
| **Đầu ra (Output)** | `<thư mục bài>/content.md` + các phần tử `posts[]` trong `publish.json` |

---

## 0. ĐỌC TRƯỚC KHI VIẾT MỘT CHỮ — bắt buộc

| # | Đọc gì | Không đọc thì sao |
|---|---|---|
| 1 | `campaign.md` của chiến dịch — đối tượng, thông điệp, **Mục 4: cái KHÔNG làm** | bài hay nhưng lạc chiến dịch, phát hiện sau khi đã dựng tiếng và hình |
| 2 | `profile.md` ở gốc kênh — tác giả là ai, giọng gì, chính kiến gì | ra bài trung tính, đúng mà nhạt — lỗi từng chạy suốt ba bài mà không ai thấy |
| 3 | `research.md` của **chính bài đó** — mục tiêu và nguồn riêng của bài | viết theo trí nhớ; G05 bắt được nhưng đã mất một vòng |

Đọc (2) **fail-closed**: đọc không được thì **DỪNG**, đừng viết tiếp với chính kiến rỗng.

Không cổng máy nào bắt được việc *có đọc hay không* — chỉ bắt được hậu quả. Vì vậy nó là
kỷ luật, và nó được ghi ở ba chỗ: đây, docstring `new_post.py`, và `ATLAS_CHANNEL.md`.

## 1. Trình Tự Thực Thi

1. **Nội dung nằm sẵn ở đó.** `new_post.py` đã copy `templates/content.md` vào thư mục bài.
   Không tạo lại file, chỉ điền.

2. **Soạn BRIEF rồi từng khối kênh:**
   - Viết mục **BRIEF** trước — mọi khối `post:` bên dưới phải bám nó.
   - Mỗi kênh một khối `## post:<post_format>` (`blog_article`, `youtube_desc`,
     `facebook_post`…). Neo phải **đúng chính tả, viết thường, không thêm chữ**.
   - Chỉ tạo khối cho kênh có trong `channels` của `campaign.md`. Kênh không đăng thì
     **xoá khối**, đừng để rỗng.
   - Cùng một brief phải **FORMAT LẠI** theo từng kênh, không copy y nguyên.
   - Claim/số liệu chưa kiểm được → gắn `[KIỂM CHỨNG]`, không bịa.

   > Khối trích dẫn `>` ngay dưới mỗi neo là **hướng dẫn cho người viết**, không phải nội
   > dung. `gen_article.py` tự bỏ nó và báo lại đã bỏ gì — nhưng đừng viết thêm vào đó.

3. **Dựng khung `posts[]`:**
   ```
   python scripts/pipeline/register_publish.py <thư mục bài> init
   ```
   Lệnh này đọc các neo trong `content.md` và sinh một phần tử `posts[]` cho mỗi khối, kèm
   `post_id`, `channel`, `post_format`, `post_content`. **Một khối = một phần tử.** Lệch nhau
   là mồ côi, `check_tree.py` bắt được.

4. **Tách file đem đăng:**
   ```
   python scripts/pipeline/gen_article.py --content-md <bài>/content.md \
       --meta <bài>/meta.json --out-dir <bài>
   ```
   Ra `atlas/blog.md`, `youtube/description.txt`, `facebook/post.txt`, `facebook/comment.txt`.

5. **Cập nhật trạng thái:** `status = in_production` trong bảng Content.
   Chuyển tiếp sang [Khâu ④ (Self-QA)](04_self_qa.md).
