# Output Style — Facebook Post "Tobi Nguyễn" (giọng Đức / Tobi)

> Style chuẩn cho **bài post Facebook** trên Page "Tobi Nguyễn".
> Rút từ 5 post thật (cặp đôi với 5 blog COMPA cùng chủ đề). FB post = **bản full-content** đăng thẳng trên feed, KHÔNG phải teaser ngắn.
> Agent đọc file này + [compa-class-blog](compa-class-blog.md) + lăng kính **tobi-viewpoint** (mô tả trong `compa-class-blog.md`, mục "H2 góc nhìn thẳng") trước khi viết.

---

## VOICE PROFILE (machine-readable)

```yaml
relation_to_blog: mỗi blog có 1 FB post tương ứng. Post = viết lại blog cho feed FB
                  (giữ trọn lập luận, đổi format sang FB-native). KHÔNG chỉ dán link + 2 câu.
length: 4.000–7.500 KÝ TỰ — đo bằng KÝ TỰ, không phải từ. Facebook đếm ký tự, và một bài
        tiếng Việt 3.000 từ vượt xa trần hiển thị. Ngưỡng lấy từ 3 bài đã đăng thật
        (xem `fixtures/baseline/blog_baseline.md`), không lấy từ cảm giác.
xung_ho: "mình" / "Đức" (thân mật hơn blog). Độc giả "bạn" / "anh chị em" / "a/em".
tone: thân thiết + chuyên môn + có khiếu hài hước nhẹ ("Nghe thì oai, nhưng…", "Nói vui một chút…").
opening_hook:
  - câu hỏi/đối lập y như blog ("Ngày xưa hỏi 'Có biết code không?' — Bây giờ hỏi 'Có mô tả rõ điều mình muốn không?'")
  - hoặc câu hỏi thật từ khách hàng/người đọc.
  - link blog đặt Ở ĐẦU bài (FB ưu tiên reach khi link sớm + nội dung đầy đủ bên dưới).
never:
  - teaser cụt "đọc full ở blog 👇" mà không có nội dung
  - clickbait rỗng, "excited to share"
  - markdown (** _ #heading) — FB render literal, KHÔNG dùng
```

---

## FORMAT FACEBOOK-NATIVE (khác blog — vì FB không có markdown)

1. **Tiêu đề phụ = Unicode bold** (vì FB không in đậm được). Dùng ký tự toán học đậm:
   - `𝐕𝐢𝐛𝐞 𝐜𝐨𝐝𝐢𝐧𝐠 𝐥𝐚̀ 𝐠𝐢̀?` · `𝐊𝐇𝐎̂𝐍𝐆 𝐏𝐇𝐀̉𝐈 𝐂𝐔̛́ 𝐌𝐔𝐎̂́𝐍…`
   - Bảng mã (dán trực tiếp, KHÔNG có font nào phải cài):
     | Kiểu | Khoảng Unicode | A | a | 0 |
     |---|---|---|---|---|
     | Bold hoa/thường | U+1D400 / U+1D41A | 𝐀 | 𝐚 | — |
     | Bold số | U+1D7CE | — | — | 𝟎 |
   - Chữ có dấu tiếng Việt KHÔNG có bản bold trong Unicode. Cách duy nhất đúng: tách
     dấu ra (NFD), bold chữ cái nền, giữ nguyên dấu tổ hợp — `fb_format.py` làm việc này.
   - Kiểm bằng `python scripts/pipeline/fb_format.py --check fb_post.txt` (in JSON, exit≠0 khi trượt).
2. **Ngắt section** bằng dòng `———————` hoặc `-----` (3+ ký tự).
3. **Emoji số** cho danh sách bước: 1️⃣ 2️⃣ 3️⃣… ; **emoji nhóm** đầu mỗi phần (🧠 🚀 🪄 🌿 🎯 💡 ⚠️ ✅ ❌).
4. **Emoji action** rải vừa phải trong thân: 👉 😄 😮 🔥 🤔 (1–2/đoạn, không lạm dụng).
5. **Đoạn ngắn** — 2–4 câu/đoạn, nhiều khoảng trắng để dễ đọc trên mobile.

---

## CẤU TRÚC POST CHUẨN
```
[Hook 1–2 câu: đối lập / câu hỏi thật]  🚀
← KHÔNG có link nào ở đây. Thân bài 0 URL.

———————
𝐇𝐞𝐚𝐝𝐢𝐧𝐠 𝟏  🧠
[2–4 đoạn ngắn + bullet/emoji-số]

———————
𝐇𝐞𝐚𝐝𝐢𝐧𝐠 𝟐  🚀
…

———————
[Câu chốt mạnh — dạng "không phải X mà là Y", đứng riêng 1 dòng]

[CTA mềm: "Mình sẽ đồng hành cùng các bạn…" / "Bài sau mình quay lại series…"]

[6–13 hashtag]
```

---

## HASHTAG (6–13 cái, cuối bài)
- **Brand cố định** (luôn có 2–3): `#COMPAClass` `#HọcCùngAI` `#NghềCủaĐức`
- **Chủ đề** theo pillar: vd `#VibeCoding #AIAgent #NoCode` / `#BusinessIntelligence #PowerBI #LLM` / `#OpenSource #GitHub`.
- Mix tiếng Anh (reach) + tiếng Việt brand. Không spam >13.

---

## CTA (luôn mềm, không bán hàng cứng)
- Build kỳ vọng bài sau: "Bài tiếp theo mình sẽ quay lại series…"
- Đồng hành: "Và mình sẽ đồng hành cùng các bạn trong hành trình này nhé 😊"
- Mời đọc full/blog: **KHÔNG dán link vào thân bài.** Chốt bằng chữ ("bản đầy đủ mình để dưới
  comment nhé") rồi đặt link ở comment đầu tiên — nội dung comment nằm ở `fb_comment.txt`.

---

## VÍ DỤ HOOK + CHỐT THẬT (tham chiếu, đừng copy nguyên)
| Bài | Hook | Câu chốt |
|-----|------|----------|
| Vibe coding | "Ngày xưa hỏi 'Có biết code không?'. Bây giờ hỏi 'Có mô tả rõ điều mình muốn không?'" | "Lợi thế không chỉ thuộc về người biết code." |
| AI×Data | "Tôi muốn nhân viên hỏi ChatGPT về doanh số… Vậy phải làm sao?" | "Đừng để AI làm việc của nhau." |
| GitHub alt | "Ngoài GitHub còn nền tảng nào bớt kỹ thuật hơn không?" | "Người mới cần bắt đầu bằng một chiến thắng nhỏ nhất." |
| Open-source repo | "Không biết code có dùng được repo open source không? — Có. Nhưng…" | "Nhỏ nhưng chạy được còn hơn lớn mà nằm trên slide." |
| 2024→2026 AI | "2024 là Chat. 2025 là Work. 2026 là Teamwork." | "Không phải một AI giỏi đến đâu, mà là biết tổ chức cả đội AI làm việc tử tế hay không." |

---

## CHECKLIST TRƯỚC KHI XUẤT
- [ ] Thân bài **0 URL**, và có `fb_comment.txt` chứa link atlas + link video?
- [ ] Hook đối lập/câu hỏi thật?
- [ ] Tiêu đề phụ Unicode bold + ngắt `———`?
- [ ] Đoạn ngắn 2–4 câu, emoji vừa phải?
- [ ] Câu chốt mạnh đứng riêng?
- [ ] CTA mềm + 6–13 hashtag (có brand)?
- [ ] KHÔNG markdown literal, KHÔNG teaser cụt?
