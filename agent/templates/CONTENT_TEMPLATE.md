---
post_id: POST-YYYY-NNN
slug: vi-du-slug-bai-viet
pillar: powerbi | fabric | ai-agent | career
topic_group: 01_powerbi | 02_fabric | 03_ai-agent | 04_career
campaign: CMP-YYYY-NN
schedule_date: YYYY-MM-DD
---

# CONTENT — Chuẩn hóa 1 bài đăng (instance `content.md`)

> **File này là gì:** mỗi bài đăng = 1 instance của template này, đặt tên `content.md` trong folder bài
> `ASSET_ROOT\<topic_group>\<post_id>_<slug>\`. AI điền đầy đủ 8 mục dưới đây.
> `gen_article.py --content-md content.md` sẽ TÁCH file này thành: `blog.md` (từ Mục 3) →
> `fb_post.txt` (Mục 4) → `youtube_desc.txt` (Mục 5) → `fb_desc.txt` (Mục 6). KHÔNG xuất `.docx`.
>
> **Trước khi viết, ĐỌC:**
> - Giọng blog: `agent/output-styles/compa-class-blog.md`
> - Giọng FB: `agent/output-styles/tobi-post.md`
> - Format đa kênh (YouTube/FB/X): `agent/output-styles/multichannel-style.md`
> - SEO title + description: `31_CAMPAIGNS/31.03_seo_playbook.md`
>
> **Quy tắc vàng:** cùng 1 nội dung gốc (Mục 1–3), FORMAT LẠI theo từng kênh — KHÔNG copy y nguyên blog
> sang FB/YouTube/X.

---

## 0. Metadata

> Đồng bộ với frontmatter trên + sheet Post của Excel campaign. Điền đầy đủ trước khi chạy pipeline.

- **post_id:** {{POST-YYYY-NNN}}
- **slug:** {{slug-khong-dau-ngan-gon-co-primary-keyword}}
- **pillar:** {{powerbi | fabric | ai-agent | career}}
- **topic_group:** {{01_powerbi | 02_fabric | 03_ai-agent | 04_career}}
- **campaign:** {{CMP-YYYY-NN — mã campaign chứa bài này}}
- **schedule_date:** {{YYYY-MM-DD — ngày dự kiến đăng}}
- **title (blog/SEO):** {{Tiêu đề bài — câu hỏi/khẳng định phá định kiến, có primary keyword}}

---

## 1. Tư duy & prompt

> "Đề bài" để ra bài — vì sao viết, viết cho ai, muốn người đọc nghĩ/làm gì khác đi.
> Mục này KHÔNG xuất ra kênh nào; nó định hướng toàn bộ phần còn lại.

- **Góc nhìn (angle):** {{góc tiếp cận riêng — không trùng bài đã có; phá vỡ định kiến gì?}}
- **Thông điệp lõi (1 câu):** {{sau khi đọc/xem, người ta nhớ đúng 1 điều này}}
- **Vì sao chủ đề này, lúc này:** {{liên quan xu thế / pain khách hàng / campaign / mùa vụ}}
- **Đối tượng + pain:** {{persona chính + nỗi đau bài này chạm tới}}
- **Prompt nội bộ (đề bài cho AI viết):** {{tóm tắt yêu cầu: độ sâu, ví dụ cần có, điều cấm}}

---

## 2. Phân tích yếu tố nội dung

> Bộ khung trước khi viết văn. Đây là "nguyên liệu" để Mục 3–6 nhất quán.

- **Outline (H2 → H3):**
  - {{## Section 1 — ...}}
    - {{H3 phụ ...}}
  - {{## Section 2 — ...}}
  - {{## Section 3 — ...}}
- **Key points (3–6 ý phải truyền tải):**
  1. {{...}}
  2. {{...}}
  3. {{...}}
- **Số liệu / nguồn (fact, ghi rõ nguồn — phân biệt fact vs quan điểm):**
  - {{Theo [nguồn]: số/sự kiện ...}}
  - {{Internal asset / case study (anonymized): ...}}
- **Ẩn dụ đời thường (≥1, bắt buộc — theo compa-class-blog.md):** {{ví dụ: "GitHub là xưởng — Netlify là quầy trưng bày"}}
- **CTA:** {{mềm/vừa/cứng?}} — wording: {{câu mời cụ thể, không bán hàng lộ liễu}}
- **Visual / asset cần:** feature image {{...}} · infographic/diagram {{...}} · screenshot {{...}}

---

## 3. Blog chi tiết (markdown)

> Bài blog ĐẦY ĐỦ theo `compa-class-blog.md` (sapo in đậm, 5–10 H2, callout emoji, câu chốt
> "không phải X mà là Y", **2.500–4.000 từ** — đủ dài để dựng podcast). Đây là NGUỒN để `gen_article.py` build `blog.md` → Atlas HTML.
> Viết trực tiếp markdown bên dưới (không bọc trong code-fence). KHÔNG xuất `.docx`.
>
> SEO (theo 31.03_seo_playbook.md): primary keyword xuất hiện trong title, H1, 100 từ đầu, kết luận;
> secondary keyword 2–3 lần; internal link ≥2; external link ≥2.

<!-- BEGIN BLOG -->

# {{Tiêu đề bài (H1) — trùng title ở Mục 0}}

**{{Sapo in đậm 1–3 câu: đối lập quá khứ–hiện tại HOẶC câu hỏi thật từ người đọc}}**

{{1 câu hạ kỳ vọng/đính chính ngay sau sapo}}

## {{H2 — Section 1: định nghĩa / "X là gì?"}}

{{Nội dung... định nghĩa in đậm, giải thích "tại sao" không chỉ "cái gì".}}

> 💡 {{Callout: Nguyên tắc vàng / Điều cần nhớ}}

## {{H2 — Section 2: phá vỡ ngộ nhận / so sánh}}

{{Nội dung... có thể kèm bảng so sánh hoặc numbered list thực hành.}}

## {{H2 — Section 3: hướng dẫn thực hành}}

{{Numbered list: lộ trình / công thức / các bước.}}

## {{H2 — Góc nhìn thẳng (lăng kính 3 lớp: technical / business / human)}}

{{Chính kiến rõ — tốt cho ai, khó cho ai. Không "tùy nhu cầu".}}

## Kết luận

{{1 đoạn ngắn.}} **{{Câu chốt mạnh dạng "không phải X, mà là Y".}}**

{{CTA mềm: mời kết nối KPIM / COMPA Class hoặc build kỳ vọng bài sau.}}

<!-- END BLOG -->

---

## 4. Facebook post chi tiết

> Bản FULL-CONTENT cho feed FB theo `tobi-post.md` (KHÔNG teaser cụt). 2.000–3.500 từ, viết lại blog
> sang FB-native: KHÔNG markdown literal, tiêu đề phụ Unicode bold, ngắt `———`, emoji vừa phải,
> đoạn ngắn 2–4 câu. Link blog đặt ĐẦU bài. NGUỒN cho `fb_post.txt`.
>
> Format chi tiết theo kênh: `agent/output-styles/multichannel-style.md`.

<!-- BEGIN FB_POST -->

{{[Link blog] — đặt đầu bài}}

{{Hook 1–2 câu: đối lập / câu hỏi thật}} 🚀

———————
{{𝐇𝐞𝐚𝐝𝐢𝐧𝐠 𝟏 (Unicode bold)}} 🧠
{{2–4 đoạn ngắn + bullet/emoji-số 1️⃣2️⃣3️⃣}}

———————
{{𝐇𝐞𝐚𝐝𝐢𝐧𝐠 𝟐}} 🚀
{{...}}

———————
{{Câu chốt mạnh — "không phải X mà là Y", đứng riêng 1 dòng}}

{{CTA mềm}}

{{6–13 hashtag: 2–3 brand cố định (#COMPAClass #HọcCùngAI #NghềCủaĐức) + chủ đề theo pillar}}

<!-- END FB_POST -->

---

## 5. YouTube description

> Chuẩn YouTube (theo `multichannel-style.md`): 2–3 dòng hook ĐẦU (hiện trên preview, trước nút "...thêm")
> → tóm tắt → timestamps (nếu video có chương) → link blog + link liên quan → CTA subscribe → ≤3 hashtag.
> NGUỒN cho `youtube_desc.txt`. Tối đa ~5.000 ký tự nhưng 150–300 từ là đủ.

<!-- BEGIN YOUTUBE_DESC -->

{{Dòng 1–2: hook mạnh, có primary keyword — đây là phần hiện trên preview}}

{{Đoạn tóm tắt video: 3–5 câu, video nói về gì, người xem được gì.}}

⏱️ Nội dung chính:
00:00 {{Mở đầu}}
{{mm:ss}} {{Chương ...}}
{{mm:ss}} {{Chương ...}}

📖 Đọc bản blog đầy đủ: {{link blog Atlas}}
🔗 {{link liên quan: khóa học COMPA Class / playlist}}

👉 Subscribe để không bỏ lỡ series về Power BI, Fabric & AI Agent.

{{#hashtag1 #hashtag2 #hashtag3 — tối đa 3}}

<!-- END YOUTUBE_DESC -->

---

## 6. Facebook description

> Caption NGẮN đi kèm video/Reel (khác bài post dài ở Mục 4). 1–3 câu hook + link + ≤6 hashtag.
> Dùng khi đăng Reel/video FB riêng. NGUỒN cho `fb_desc.txt`. Nếu không có video riêng, để trống
> hoặc copy hook của Mục 4.

<!-- BEGIN FB_DESC -->

{{Hook 1–2 câu cho video/reel — gọn, gây tò mò}} 🎬

📖 Bản đầy đủ: {{link blog}}

{{#hashtag — ≤6, có brand}}

<!-- END FB_DESC -->

---

## 7. X / Threads (chuẩn bị trước — KÊNH TƯƠNG LAI, chưa bật)

> Soạn sẵn để sau bật kênh là đăng được ngay. Theo `multichannel-style.md`: ≤280 ký tự/tweet,
> KHÔNG markdown, 1–2 hashtag. Bài dài tách thành thread đánh số.

<!-- BEGIN X_THREAD (future) -->

**Tweet đơn (≤280 ký tự):**
{{Hook + thông điệp lõi + link blog. 1–2 hashtag.}}

**Thread (nếu cần):**
1/ {{mở — hook, đặt vấn đề}}
2/ {{ý chính 1}}
3/ {{ý chính 2}}
.../ {{chốt + link blog + CTA}}

<!-- END X_THREAD -->
