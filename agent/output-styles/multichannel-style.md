# Output Style — Đăng đa kênh (Multichannel Format)

> Quy tắc FORMAT theo từng kênh khi cùng 1 nội dung gốc đi ra nhiều nơi.
> **Nguyên tắc lõi:** 1 nội dung gốc (blog ở `content.md` Mục 3) → **format lại** theo đặc thù từng
> kênh — KHÔNG copy y nguyên. Mỗi kênh có giới hạn độ dài, định dạng, hành vi reach khác nhau.
>
> Giọng văn KHÔNG nằm ở đây — file này chỉ lo FORMAT. Giọng:
> - Blog: `compa-class-blog.md`
> - Facebook (post dài + caption reel): `tobi-post.md`
> - YouTube / X: dùng giọng "mình/Đức" như FB, rút gọn.

---

## YouTube description (→ `youtube_desc.txt`, từ `content.md` Mục 5)

- **Độ dài:** 150–300 từ là đủ (giới hạn cứng ~5.000 ký tự). Đừng nhồi.
- **Hook 1–2 dòng đầu = QUAN TRỌNG NHẤT:** chỉ ~2–3 dòng đầu hiện trên preview (trước nút "...thêm")
  và trong kết quả tìm kiếm. Đặt thông điệp + primary keyword ngay đây, KHÔNG để link/hashtag lên đầu.
- **Cấu trúc:** hook (1–2 dòng) → tóm tắt 3–5 câu → timestamps (nếu video có chương) → link →
  CTA subscribe → hashtag.
- **Timestamps:** `00:00 Mở đầu` rồi `mm:ss Tên chương`. Dòng đầu PHẢI là `00:00` để YouTube nhận chương.
- **Link:** đặt ở khối giữa/cuối (blog Atlas trước, rồi link liên quan). KHÔNG nhồi link lên 2 dòng đầu.
- **Hashtag:** **≤3** (YouTube chỉ hiển thị 3 hashtag đầu phía trên tiêu đề; >15 là bị bỏ qua hết).
- **CTA:** 1 câu subscribe rõ ràng ("Subscribe để không bỏ lỡ series...").

## Facebook (→ `fb_post.txt` + `fb_desc.txt`, từ `content.md` Mục 4 & 6)

Hai sản phẩm FB khác nhau:

- **`fb_post.txt` — post dài full-content** (Mục 4): 2.000–3.500 từ, viết lại trọn lập luận của blog.
  KHÔNG teaser cụt. Giọng + cấu trúc theo `tobi-post.md`.
- **`fb_desc.txt` — caption ngắn cho Reel/video** (Mục 6): 1–3 câu hook + link + ít hashtag.

Quy tắc format FB chung:
- **Link đặt ĐẦU bài** — FB ưu tiên reach khi link xuất hiện sớm + nội dung đầy đủ bên dưới.
- **KHÔNG markdown** — FB render `**`, `#heading`, `_` literal. Nhấn mạnh bằng **Unicode bold**
  (script tự convert tiêu đề phụ), ngắt section bằng `———————`.
- **Emoji:** nhóm đầu mỗi phần (🧠🚀🪄🎯💡⚠️) + emoji-số cho bước (1️⃣2️⃣3️⃣); action 👉😄🔥 rải 1–2/đoạn.
- **Đoạn ngắn 2–4 câu**, nhiều khoảng trắng (đọc trên mobile).
- **Hashtag: 6–13** ở cuối bài; luôn có 2–3 brand (`#COMPAClass #HọcCùngAI #NghềCủaĐức`) + chủ đề theo
  pillar. Mix Anh (reach) + Việt (brand). (Caption Reel: ≤6 hashtag.)
- **Giọng:** xem `tobi-post.md` — đây là nguồn chuẩn cho voice FB.

## X / Threads (→ chuẩn bị trước ở `content.md` Mục 7 — KÊNH TƯƠNG LAI, CHƯA BẬT)

> Soạn sẵn trong content.md để khi bật kênh là đăng ngay. Pipeline hiện CHƯA xuất file riêng cho X.

- **Giới hạn:** ≤**280 ký tự**/tweet (kể cả link ~23 ký tự sau khi rút gọn).
- **KHÔNG markdown**, KHÔNG Unicode-bold rườm rà — X render text thuần.
- **Thread:** bài dài tách thành chuỗi đánh số `1/`, `2/`... Tweet đầu = hook + đặt vấn đề; tweet cuối =
  chốt + link blog + CTA.
- **Hashtag: 1–2** (X phạt nhồi hashtag; 1–2 cái đúng chủ đề là đủ).
- **Link:** thường để ở tweet cuối thread (hoặc reply đầu tiên) để không cắt reach tweet mở.

---

## Bảng tổng hợp format theo kênh

| Kênh | Độ dài | Định dạng | Hashtag | Vị trí link | CTA |
|------|--------|-----------|---------|-------------|-----|
| **Blog (Atlas)** | 2.500–4.000 từ | Markdown đầy đủ (H1/H2/H3, bảng, callout) | — (SEO keyword thay hashtag) | Internal ≥2 + external ≥2 trong bài | Mời KPIM/COMPA, mềm |
| **YouTube desc** | 150–300 từ | Text thuần + timestamps `mm:ss` | **≤3** (hiện trên tiêu đề) | Khối giữa/cuối; blog trước | Subscribe |
| **Facebook post** | 2.000–3.500 từ | Unicode bold + `———` + emoji, KHÔNG markdown | **6–13** (brand + pillar) | **ĐẦU bài** | Mềm, build kỳ vọng bài sau |
| **FB caption (Reel)** | 1–3 câu | Hook + emoji nhẹ, KHÔNG markdown | ≤6 | Sau hook | Mời xem bản đầy đủ |
| **X / Threads** *(chưa bật)* | ≤280 ký tự/tweet, thread đánh số | Text thuần, KHÔNG markdown | **1–2** | Tweet cuối thread | Đọc full ở blog |

> **Nhấn mạnh:** cùng 1 nội dung gốc → mỗi ô trong bảng trên là một bản FORMAT LẠI. Copy y nguyên blog
> sang FB sẽ vỡ (markdown literal); copy sang YouTube sẽ thừa; sang X sẽ tràn 280 ký tự.
