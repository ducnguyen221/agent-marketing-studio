# Bảng chẩn đoán — triệu chứng → nguyên nhân → hành động

Đây là "não" của agent ở khâu đo. Khi viết dòng vào `10_Insights`, tra bảng này
trước khi tự nghĩ ra nguyên nhân mới.

Chưng cất từ `Brain/50_CONTENT/51_BRAND/ducnguyen-ai/51.01…md` §13 và
`…/nghe-tien-truyen/51.02…md` §13.

| # | Triệu chứng (đo được) | Nguyên nhân khả dĩ | Hành động | Ưu tiên |
|---|---|---|---|---|
| 1 | Impression cao · CTR thấp | Packaging yếu — title/thumbnail không hứa gì rõ | A/B lại title + thumbnail, giữ nguyên nội dung | P1 |
| 2 | CTR cao · retention @30s thấp | Promise mismatch — hook hứa một đằng, nội dung một nẻo | Sửa 30 giây đầu cho khớp title | P1 |
| 3 | Watch time tốt · subscriber thấp | Thiếu channel promise — người xem không biết đăng ký để được gì | Thêm CTA theo series, nói rõ tập sau có gì | P1 |
| 4 | Engagement tốt · CTA click thấp | CTA đặt sai chỗ hoặc quá mềm | Đưa CTA lên sớm hơn, làm cụ thể hơn | P2 |
| 5 | Short view cao · hero view thấp | Short không dẫn về hero | Sửa Related Video / link, thêm 1 câu cầu nối cuối short | P1 |
| 6 | Community post vote tốt · video liên quan yếu | Poll lệch nhu cầu thật, hoặc chủ đề đúng nhưng đóng gói sai | Đọc lại comment, sửa góc tiếp cận chứ không sửa chủ đề | P2 |
| 7 | Reach giảm đều nhiều bài liên tiếp | Tần suất hoặc chất lượng tụt, hoặc lệch pillar | Rà tỷ trọng pillar so `target_share`, giảm số lượng tăng chất | P1 |
| 8 | Một pillar CTR cao nhưng lead/click thấp | Nội dung câu click, không câu người đúng nhu cầu | Giảm tỷ trọng pillar đó, hoặc đổi CTA sang lọc người | P1 |
| 9 | Bài dài tốt · short kém, hoặc ngược lại | Nội dung chỉ hợp một định dạng | Đừng ép atomize mọi thứ; chọn định dạng theo bản chất nội dung | P3 |
| 10 | Tất cả chỉ số tốt · không ra lead | Đo nhầm mục tiêu — đang tối ưu vanity metric | Xem lại `primary_kpi` của campaign trong `01_Brief` | P1 |

## Luật viết insight

Một dòng `10_Insights` chỉ hợp lệ khi có **đủ bốn thứ**:

1. `symptom` — quan sát được, không phải cảm nhận
2. `evidence_metric` + `evidence_value` — **tên chỉ số và con số thật**
3. `likely_cause` — dùng bảng trên; nếu không khớp dòng nào, ghi rõ "ngoài bảng"
4. `recommendation` — hành động cụ thể, làm được trong tuần tới

**Không có số thì không được ghi dòng.** Thà để `10_Insights` trống còn hơn có một dòng
nghe hợp lý mà không kiểm được.

## So sánh với baseline — luật cứng

Baseline = **median 10 nội dung gần nhất CÙNG định dạng của chính kênh này**.
Không dùng benchmark ngành, không dùng con số đọc được trên mạng.

- `baseline_n < 10` → `vs_median_*` để **trống**, dashboard hiện "chưa đủ mẫu".
- So sánh phải cùng định dạng. Đừng so short với video dài.
- Nội dung có vai trò khác nhau thì so trong cùng vai trò (mở vấn đề vs recap).

**"Winner"** = vượt median ở **≥2 KPI** đã khai trong `01_Brief.winner_rule`
**VÀ** guardrail không tụt dưới median. Thiếu một trong hai thì không phải winner,
kể cả khi một chỉ số nào đó rất đẹp.

## Nhịp đo và quyết định

| Mốc | Nhìn gì |
|---|---|
| 24h | Có sống không — impression, CTR đầu |
| 72h | Packaging đã ổn định chưa |
| 7 ngày | Consumption + engagement thật |
| **28 ngày** | Chốt: `SCALE` / `ITERATE` / `REPURPOSE` / `EVERGREEN` / `STOP` |

Quyết định 28 ngày ghi vào `08_Metrics_Summary.decision_28d` — **cột này của người**,
agent đề xuất trong `10_Insights`, người chốt.
