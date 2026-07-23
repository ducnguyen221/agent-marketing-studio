# SEO playbook — on-page, technical, và AI search

Luật SEO để bài blog được tìm thấy, dùng ở stage draft (viết) và trước publish (kiểm).

> Chưng cất từ `coreyhaines31/marketingskills` (MIT) `ai-seo` + `seo-audit`. Việt hoá.

---

## 1. On-page (kiểm trước khi publish)

- **Title:** ≤60 ký tự, primary keyword ở đầu, không nhồi keyword.
- **Meta description:** 150–160 ký tự, có primary keyword, viết như lời mời (đây là "quảng cáo"
  trên trang kết quả tìm kiếm).
- **H1 duy nhất**, trùng ý title. Primary keyword xuất hiện trong: title, H1, **100 từ đầu**, kết luận.
- **H2/H3** có cấu trúc rõ; secondary keyword 2–3 lần, tự nhiên.
- **Internal link ≥2** (bài liên quan của bạn) + **external link ≥2** (nguồn uy tín).
- **Alt text** cho mọi ảnh, mô tả thật, có keyword khi hợp.
- **Slug** ngắn, có primary keyword, không dấu.

## 2. E-E-A-T — thứ AI search và Google cùng thưởng

Experience · Expertise · Authoritativeness · Trustworthiness. Nội dung **helpful, người-thật-viết,
người-đọc-trước** thắng. Cụ thể:
- Có kinh nghiệm thật (ví dụ mình đã làm), không tổng hợp chung chung.
- Dẫn nguồn cho mọi claim (khớp luật `[KIỂM CHỨNG]`).
- Tác giả rõ ràng, có chuyên môn thể hiện qua kết quả.

## 3. AI search (ChatGPT / Perplexity / Google AI Overview) — khác SEO truyền thống

- **KHÔNG cần markup đặc biệt**, KHÔNG viết nội dung riêng cho AI (rủi ro dính "scaled content
  abuse"). Viết cho người, tổ chức bằng heading + đoạn văn bình thường.
- **Cùng chuẩn E-E-A-T** như Search thường.
- **Query fan-out:** AI tách một câu hỏi thành 5–10 câu liên quan rồi tổng hợp. → Khi lên kế
  hoạch nội dung, brainstorm 5–10 câu hỏi AI có thể tách ra và đảm bảo bài (hoặc cả site) phủ được.
- Nội dung **trả lời trực tiếp, súc tích ở đầu** dễ được trích dẫn hơn.

## 4. Content cluster (kiến trúc site)

- **Pillar page** (bài trụ, chủ đề lớn) + **5–10 bài phụ** (supporting) trỏ về nhau.
- Mỗi bài phụ nhắm một truy vấn/nỗi đau khác nhau, dẫn về pillar.
- Đây chính là cây atomization của `agent/output-styles/multichannel-style.md` nhìn từ góc SEO.

## 5. Nối vào quy trình repo
- Kiểm on-page ở stage draft (trong `content.md`) và trong `checklists/QA_ASSET.md`.
- Từ khoá + cluster do `agent/agents/seo-specialist.md` lo (nếu instance dùng vai này).

## Liên kết
- Tiêu đề: `agent/knowledge/COPY_FRAMEWORKS.md` · YouTube SEO: `YOUTUBE_PLAYBOOK.md`.
