---
content_id: {{TOBI-001}}              # = Content.content_id trong .xlsx
campaign_code: {{01_Tobi_Posts}}      # = Campaign.campaign_code
content_name: {{Tên làm việc của content}}
folder_path: {{assets/TOBI-001_slug}} # = Content.folder_path, chính là thư mục chứa file này
---

# {{content_name}}

> **File này là gì:** MỘT content = MỘT thư mục = MỘT `content.md`. File này chứa **toàn bộ text
> của mọi kênh**, mỗi kênh một khối `## post:<post_format>`.
>
> **Vì sao dùng anchor:** mỗi dòng trong sheet Post trỏ tới đây qua cột `post_content`
> (vd `post:facebook_post`). Agent đọc đúng khối đó, không đoán theo kênh. Cùng một content có
> nhiều post trùng format → thêm hậu tố: `## post:facebook_post#2`.
>
> **Luật anchor — bắt buộc:**
> - Heading phải đúng `## post:<post_format>`, viết thường, không thêm chữ.
> - `<post_format>` phải là giá trị hợp lệ (xem `knowledge/data_model/DATA_MODEL.md` → `post_format`).
> - Chỉ tạo khối cho kênh có trong `Campaign.channels`. Kênh không đăng thì **xoá khối**, đừng để rỗng.
> - Mỗi khối phải có một dòng Post tương ứng trong Excel. Có khối mà không có dòng = mồ côi.
>
> **Trước khi viết, ĐỌC:** `output_styles/` (giọng của instance) ·
> `knowledge/playbooks/COPY_FRAMEWORKS.md` · `knowledge/playbooks/SEO_PLAYBOOK.md` ·
> hồ sơ campaign `.md` (persona, cái KHÔNG làm, luật cross-post).
>
> **Quy tắc vàng:** cùng một brief → **FORMAT LẠI** theo từng kênh. Không copy y nguyên blog
> sang Facebook/YouTube.

---

# BRIEF — không đăng ở đâu cả

> Nguồn sự thật của content. Mọi khối `post:` bên dưới phải bám mục này. Nội dung mục này
> đồng bộ với các cột tương ứng ở sheet Content — viết ở đây bản đầy đủ, Excel giữ bản rút gọn.

- **Mục tiêu content** (`content_goal`): {{kết quả quan sát được sau khi người ta đọc/xem}}
- **Người xem cụ thể** (`audience_profile`): {{ai, trình độ, đang kẹt ở đâu}}
- **Brief lõi** (`core_brief`): {{vấn đề → insight → thông điệp → luận điểm → phản biện → CTA}}
- **Nguồn & bằng chứng** (`key_sources`): {{fact + nguồn. Phân biệt rõ fact đã kiểm vs giả định}}
- **Từ khoá chính** (`target_keyword`): {{1 keyword, đúng ý định tìm kiếm}}
- **Hướng sáng tạo** (`creative_direction`): {{đã cân nhắc ≥3 hướng, chọn hướng nào, vì sao}}
- **Giới hạn** (`constraints`): {{claim cấm, bản quyền, dữ liệu nhạy cảm}}
- **Vị trí trong series** (`content_relationship`): {{series, bài trước, bài sau}}

### Outline dùng chung
1. {{ý chính 1}}
2. {{ý chính 2}}
3. {{ý chính 3}}

### Ẩn dụ đời thường (≥1, bắt buộc)
{{ẩn dụ giúp người ngoài ngành hiểu ngay}}

### Claim cần kiểm chứng
- [ ] {{claim}} → gắn `[KIỂM CHỨNG]` trong bài cho tới khi có nguồn

---

## post:blog_article

> Bài blog đầy đủ. Sapo in đậm → 5–10 H2 → callout → câu chốt dạng "không phải X mà là Y".
> SEO: primary keyword ở title, H1, 100 từ đầu và kết luận; internal link ≥2.
> Viết markdown trực tiếp, không bọc code-fence.

# {{Tiêu đề H1 — có primary keyword}}

**{{Sapo 1–3 câu: đối lập quá khứ–hiện tại, hoặc câu hỏi thật của người đọc}}**

{{1 câu hạ kỳ vọng / đính chính ngay sau sapo}}

## {{H2 — "X là gì" / định nghĩa}}

{{Định nghĩa in đậm. Giải thích "vì sao", không chỉ "cái gì".}}

> 💡 {{Callout: điều cần nhớ}}

## {{H2 — phá ngộ nhận / so sánh}}

{{Bảng so sánh hoặc danh sách đánh số.}}

## {{H2 — hướng dẫn thực hành}}

{{Các bước làm được ngay.}}

## {{H2 — góc nhìn thẳng}}

{{Chính kiến rõ: tốt cho ai, khó cho ai. Không "tuỳ nhu cầu".}}

## Kết luận

{{Một đoạn ngắn.}} **{{Câu chốt "không phải X, mà là Y".}}**

{{CTA mềm.}}

---

## post:youtube_video

> Mô tả video YouTube. 2–3 dòng đầu là phần hiện trên preview — quan trọng nhất.
> 150–300 từ là đủ. Tối đa 3 hashtag.

{{Dòng 1–2: hook mạnh, có primary keyword}}

{{Tóm tắt 3–5 câu: video nói gì, người xem được gì.}}

⏱️ Nội dung chính:
00:00 {{Mở đầu}}
{{mm:ss}} {{Chương}}

📖 Bản blog đầy đủ: {{link}}

👉 {{CTA subscribe}}

{{#hashtag1 #hashtag2 #hashtag3}}

### Kịch bản đọc (cho OmniVoice)

> Văn nói, không đọc nguyên bullet. Đây là text đưa vào `-TextFile` khi dựng video.
> Xem `knowledge/toolchains/ASSET_TOOLCHAIN.md`.

{{Kịch bản lời đọc, chia theo cảnh}}

---

## post:youtube_short

> 15–60 giây. Hook trong 1–3 giây đầu. Rút một insight ĐỘC LẬP có hook mạnh —
> không cắt ngẫu nhiên từ video dài.

**Hook (1–3s):** {{câu chặn đứng cú lướt}}

**Thân (15–45s):** {{một ý duy nhất, không tham}}

**Chốt (3–5s):** {{câu đóng + CTA}}

**Caption:** {{1–2 câu + ≤3 hashtag}}

---

## post:facebook_post

> Bản FULL cho feed, không phải teaser cụt. Facebook-native: **không markdown literal**,
> tiêu đề phụ dùng Unicode bold, ngắt bằng `———`, đoạn ngắn 2–4 câu. Link đặt ĐẦU bài.

{{[Link blog] — đặt đầu bài}}

{{Hook 1–2 câu}} 🚀

———————
{{𝐇𝐞𝐚𝐝𝐢𝐧𝐠 𝟏}} 🧠
{{2–4 đoạn ngắn}}

———————
{{𝐇𝐞𝐚𝐝𝐢𝐧𝐠 𝟐}}
{{...}}

———————
{{Câu chốt mạnh, đứng riêng một dòng}}

{{CTA mềm}}

{{6–13 hashtag: 2–3 hashtag thương hiệu cố định + hashtag chủ đề}}

---

## post:reel

> Caption NGẮN đi kèm video/Reel — khác hẳn bài dài ở trên. 1–3 câu + link + ≤6 hashtag.

{{Hook 1–2 câu, gọn, gây tò mò}} 🎬

📖 Bản đầy đủ: {{link}}

{{#hashtag ≤6}}

---

## post:carousel

> Mỗi trang một ý. 5–8 trang. Trang 1 là hook, trang cuối là CTA.
> **Bắt buộc điền `asset_ref`** trong sheet Post — carousel không có asset mặc định.

| Trang | Chữ trên hình | Ghi chú thiết kế |
|---|---|---|
| 1 | {{hook 4–8 chữ}} | {{...}} |
| 2 | {{...}} | {{...}} |
| … | | |
| N | {{CTA}} | {{...}} |

**Caption:** {{2–4 câu + hashtag}}

---

## post:infographic

> Một hình, một thông điệp. **Bắt buộc điền `asset_ref`**.

**Tiêu đề trên hình:** {{≤8 chữ}}

**Các khối nội dung:**
1. {{...}}
2. {{...}}

**Nguồn ghi trên hình:** {{bắt buộc nếu có số liệu}}

**Caption:** {{2–4 câu + hashtag}}

---

<!-- Xoá mọi khối post: không dùng cho content này. Khối rỗng gây nhầm cho agent. -->
