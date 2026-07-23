# YouTube playbook — retention, thumbnail, Shorts

Số liệu và luật để làm video/Shorts giữ chân người xem và được thuật toán đẩy. Dùng ở
stage draft (kịch bản/mô tả) và media (thumbnail/Shorts).

> Chưng cất từ `AgriciDaniel/claude-youtube` (MIT, 264★). Số liệu là benchmark tham chiếu,
> không phải cam kết — kênh của bạn có baseline riêng (so median 10 video gần nhất cùng định dạng).

---

## 1. Retention & kịch bản

**Dữ liệu mất người xem:**
- **20%** mất trong **10 giây** đầu · **55%** mất trong **60 giây** đầu.
- **Không mở bằng** "Chào các bạn, welcome back" → tụt người xem đo được ngay.

**Hook 30 giây đầu** (cấu trúc): nêu ngay điều đáng xem → chứng minh nhanh → hứa điều sẽ nhận
→ vào thẳng nội dung. (Khớp `COPY_FRAMEWORKS.md §4` — hook 3 thành phần.)

**Pattern interrupt:** đổi nhịp (góc quay/hình/giọng) đều đặn để reset chú ý — nhất là quanh
các mốc hay tụt (30s, 60s).

**Độ dài tối ưu theo format:**
- **5–10 phút** = đỉnh retention (~31,5%).
- **Ngưỡng 8 phút** mở mid-roll ads → tăng ~50% doanh thu.
- **Shorts chiếm ~75% view** của nền tảng — không bỏ Shorts.

**⚠️ Giọng đọc AI = retention thấp hơn ~70%** so với nội dung có người dẫn. → Với repo này,
giọng đọc phải được trình bày là **của tác giả** (luật `output-styles` + AGENTS), và thực tế
người-dẫn giữ chân tốt hơn hẳn.

**CTA đặt đâu (dual CTA):**
- CTA 1 ở ~1 phút → chạm ~60% người xem.
- CTA 2 ở ~4 phút → chạm ~35%.

---

## 2. Thumbnail & CTR

- **CTR cao nhất trong 24h đầu** (khán giả ấm/đã subscribe). Bền vững **4–8%** khi mở rộng = khoẻ.
- **Thumbnail có mặt người** trung bình nhiều view hơn hẳn — nhưng **cần cảm xúc mạnh**,
  mặt trung tính kém hiệu quả.
- **Luật tách thông tin:** thumbnail = hook hình + cảm xúc · title = keyword + lời hứa ·
  **KHÔNG lặp chữ** giữa thumbnail và title (giống luật hook 3-thành-phần không trùng).
- **Chữ trên thumbnail 2–4 từ.** A/B test thumbnail cho CTR chênh 37–110% trong nhiều case.

---

## 3. Shorts

- **Thuật toán explore → exploit:** test cohort nhỏ trước; engage mạnh (qua 5 giây đầu) →
  đẩy rộng.
- **Tín hiệu quan trọng nhất:** completion/retention **≥70% = đẩy mạnh**; viewed-vs-swiped
  **≥75% tốt; <50% = hook hỏng**.
- **Độ dài:** ngọt nhất **15–60 giây**; hai đỉnh **13s** và **60s**. Đổi hình mỗi **~3 giây**.
  Hook trong **1–3 giây** đầu.
- **Title:** 4–6 từ (20–40 ký tự — phần hiện trước khi bị cắt), **3–5 hashtag**.
- **KHÔNG dùng view thô làm thước đo** (YouTube đổi cách đếm view Shorts từ 31/03/2025) →
  dùng `engaged_views`.

---

## 4. Nối vào quy trình repo

- Số liệu này về **Sheet Engagement** khi kéo YouTube Analytics (retention, CTR, engaged_views).
- Khi báo cáo (hồ sơ `.md` Mục 14): so với **baseline của chính kênh**, không so benchmark ở đây.
- Kịch bản retention → viết ở stage draft (`content.md`). Thumbnail brief → stage media.

## Liên kết
- Hook: `agent/skills/hook-writer/SKILL.md` · `agent/knowledge/COPY_FRAMEWORKS.md`.
- Format đa kênh: `agent/output-styles/multichannel-style.md`.
- Kéo số liệu: `agent/knowledge/PLATFORM_SETUP.md`.
