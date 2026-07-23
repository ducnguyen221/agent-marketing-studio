# Công thức copywriting — headline, khung bài, hook

Bộ công thức để agent viết tiêu đề, cấu trúc bài và hook có căn cứ, không viết mò.
Đây là tri thức chuẩn ngành — dùng làm khung, luôn format lại theo giọng của instance
(`agent/output-styles/`), đừng dán công thức lộ ra ngoài.

> Chưng cất từ: `coreyhaines31/marketingskills` (MIT, 41k★) · `zubair-trabzada/ai-marketing-claude` (MIT).
> Viết lại và Việt hoá cho model 5 sheet của repo này.

---

## 1. Công thức tiêu đề (headline)

Chọn nhóm theo mục tiêu bài. Mỗi công thức: khuôn + ví dụ.

### Hướng kết quả (outcome)
- **{Đạt kết quả mong muốn} mà không cần {nỗi đau}** — "Hiểu người dùng thật sự trải nghiệm site thế nào mà không chết chìm trong số liệu."
- **{Kết quả} nhờ {cách sản phẩm làm được}** — "Ra nhiều lead hơn nhờ thấy công ty nào đang ghé site bạn."
- **Biến {đầu vào} thành {kết quả}** — "Biến khách mua một lần thành khách quay lại."
- **{Đạt kết quả} trong {khung thời gian}** — "Dựng dashboard đầu tiên trong 30 phút."

### Hướng vấn đề (problem)
- **Đừng bao giờ {chuyện khó chịu} nữa** — "Đừng bao giờ để measure DAX tính sai âm thầm nữa."
- **{Câu hỏi chạm đúng nỗi đau}** — "Ghét phải giải thích lại cùng một biểu đồ mỗi tuần?"
- **Dừng {nỗi đau}. Bắt đầu {niềm vui}.** — "Dừng đoán mò. Bắt đầu đo."

### Hướng đối tượng (audience)
- **{Tính năng/loại sản phẩm} cho {đối tượng}** — "Phân tích nâng cao cho người làm data."
- **Bạn không cần {kỹ năng/nguồn lực} để {đạt kết quả}** — "Bạn không cần biết code để dựng agent đầu tiên."

### Hướng khác biệt / bằng chứng
- **{Loại sản phẩm} duy nhất {điểm khác biệt duy nhất}**
- **{Số} {đối tượng} đã {đạt kết quả}** — chỉ dùng khi có SỐ THẬT, kiểm được (nếu chưa chắc → tag `[KIỂM CHỨNG]`).

**Luật:** tiêu đề không hứa quá nội dung. Số tập/số thứ tự đặt ở CUỐI tiêu đề, không phải đầu.

---

## 2. Khung bài (copy frameworks)

Chọn 1 khung theo loại nội dung, đừng trộn nửa vời.

| Khung | Cấu trúc | Hợp với |
|---|---|---|
| **AIDA** | Attention → Interest → Desire → Action | bài bán hàng, landing |
| **PAS** | Pain → Agitate → Solution | bài chạm nỗi đau, quảng cáo |
| **BAB** | Before → After → Bridge | case study, transformation |
| **4P** | Picture → Promise → Prove → Push | email, bài dài có bằng chứng |
| **FAB** | Feature → Advantage → Benefit | mô tả sản phẩm |
| **PPPP** | Problem → Promise → Proof → Proposal | proposal, pitch |
| **StoryBrand** | Nhân vật (khách) gặp vấn đề → gặp người dẫn đường (bạn) → có kế hoạch → hành động → tránh thất bại | thương hiệu cá nhân, video |

**Lăng kính 3 lớp** (bắt buộc với bài chuyên sâu — giữ từ `output-styles/compa-class-blog`):
kỹ thuật (nó chạy thế nào) → business (đổi được gì về tiền/thời gian) → con người (ai chịu đổi cách làm).

---

## 3. Các phần của landing page

Lõi: Hero (headline + subhead + CTA) → Vấn đề → Giải pháp → Cách hoạt động → Bằng chứng
(testimonial/số liệu) → Chống phản đối (FAQ) → CTA cuối.
Bổ trợ: logo tin cậy, so sánh, bảng giá, bảo đảm.

- **Phần vấn đề:** mô tả nỗi đau bằng CHÍNH lời khách (lấy từ review/comment), không paraphrase.
- **Phần lợi ích:** nói kết quả đạt được, không liệt kê tính năng.
- **Chọn testimonial:** cái chạm đúng phản đối lớn nhất, không phải cái khen chung chung.

---

## 4. Hook — ba thành phần, không phải một câu

Ba giây đầu quyết định phần còn lại có được xem không. Với video, hook là **kết hợp đồng thời**:

| Thành phần | Là gì | Nhiệm vụ |
|---|---|---|
| **Hành động hình** | Cái gì đang diễn ra trên màn hình giây 0–3 | Chặn ngón tay lướt |
| **Câu thoại** | Những chữ đầu tiên | Mở vòng tò mò |
| **Chữ overlay** | Header/caption trên hình | Neo thông điệp cho người xem tắt tiếng |

**Luật không trùng:** ba thành phần bổ trợ nhau, KHÔNG lặp lại. Nếu thoại nói "Tôi bỏ 200$/tháng"
mà caption cũng ghi y hệt trên mặt người nói tĩnh → phí 2/3 slot. Hook mạnh chia việc:
hình cho thấy email huỷ, thoại nói câu đó, caption nêu giải pháp thay thế.

**Đường sinh hook:** `Phân khúc → Động cơ → Format → Hook (3 thành phần)`
1. **Phân khúc** — nhóm người cụ thể có tình huống chung, không phải cả tệp.
2. **Động cơ** — nỗi đau/mong muốn/phản đối bằng CHÍNH lời họ (lấy verbatim từ comment/review).
3. **Format** — chọn dạng thể hiện TRƯỚC khi viết câu (phỏng vấn đường phố, POV selfie, quay màn hình, demo so sánh, nói thẳng vào camera).
4. **Hook** — viết 3 thành phần cho ô phân khúc × động cơ × format đó.

**Xuất ra dạng ma trận hook** để thấy độ phủ:
`| # | Phân khúc | Động cơ (nguồn verbatim) | Format | Hành động hình | Câu thoại | Caption |`

Sinh THEO ma trận (10 hook cho 10 ô khác nhau) tốt hơn 30 cách nói lại của 1 ô —
đa dạng ma trận = đa dạng đối tượng tiếp cận.

**Các kiểu mở hook** (luân phiên, đừng bám 1 kiểu):
- Khoảng trống tò mò — giấu danh từ: "Không ai nói cho bạn cái thật sự gây ra điều này." (phải trả lời trong bài, không thì thành clickbait)
- Tuyên bố mạnh, cụ thể, kiểm được: "Cái này thay cả quy trình sáng của tôi." (cần bằng chứng trên màn hình)
- Câu hỏi thật từ khách · đối lập quá khứ–hiện tại · con số gây sốc có nguồn.

---

## Liên kết
- Giọng viết: `agent/output-styles/compa-class-blog.md` (blog) · `tobi-post.md` (Facebook).
- Format theo kênh: `agent/output-styles/multichannel-style.md`.
- Tâm lý học phía sau: `agent/knowledge/MARKETING_PSYCHOLOGY.md`.
