---
schema: research/1
content_id: GTX-001
campaign_id: CMP-2609-gioi-thieu
content_goal: Người đọc chỉ ra được HAI chỗ trong quy trình của chính họ mà máy không nên tự quyết
audience_profile: Người làm data/BI 2-8 năm, đã thử giao việc viết cho AI và thấy kết quả rỗng, chưa biết
  đặt ranh giới ở đâu
core_brief: 'Vấn đề: bài do agent viết nghe trôi chảy nhưng rỗng, và không khâu nào chặn lại. Insight:
  cái thiếu không phải chất lượng sinh chữ mà là ĐIỂM DỪNG có người. Thông điệp: cái làm nội dung dùng
  được là chỗ NGƯỜI đặt tay vào. Luận điểm: (1) chọn đề tài là quyết định chiến lược, không phải việc
  sinh chữ; (2) duyệt trước khi đăng là chỗ duy nhất còn sửa được rẻ; (3) cổng máy kiểm được hình thức,
  không kiểm được có đáng đăng hay không. Phản biện đã lường: ''cổng người làm chậm'' - đo bằng số bài
  phải gỡ sau khi đăng, không bằng số bài/tuần. CTA: clone repo, chạy một bài tới bước đăng.'
key_sources: 'Chính repo này: hai cổng trong ATLAS_CHANNEL.md, bộ 23 cổng trong blog_gates.py, một bài
  đã đăng đủ ba kênh'
target_keyword: quy trình nội dung với AI agent
creative_direction: 'Đã cân nhắc ba hướng: (a) hướng dẫn từng bước - bị loại vì bài 1 mà đọc như tài liệu
  thì không ai đọc hết; (b) so sánh có/không có cổng - bị loại vì thành bài quảng cáo; (c) CHỌN: kể một
  thứ đã đi qua mọi khâu mà vẫn rỗng, rồi hỏi ''khâu nào lẽ ra phải chặn'''
constraints: Không hứa tự động hoá hoàn toàn; không nêu con số hiệu quả nào không đo được từ chính repo
content_relationship: Bài 1 của series 3 bài. Dẫn sang GTX-002 (cổng kiểm bằng số làm gì)
audio: 'yes'
video: 'yes'
short: 'no'
notes: VÍ DỤ trong repo — nguồn ở đây là file của chính repo, kiểm được bằng cách mở file
---
# research.md — GTX-001 · Vì sao một xưởng nội dung chạy bằng agent vẫn cần cổng của người

> **Frontmatter = brief.** Viết ở khâu ② (lập kế hoạch), người sửa cho tới khi qua Cổng 1.
> **Thân bài = nghiên cứu.** Viết ở B1, và **đóng băng sau B1** — chỉ được *append* mục
> "Kiểm sau", không sửa lại phần đã có.
>
> Vì sao đóng băng: đây là **bằng chứng** của bài. Bằng chứng mà sửa được cùng lúc với bài
> thì nó bị làm đẹp theo bài, và cổng G05 (đối chiếu nguồn trong blog với file này) mất ý
> nghĩa. Đó cũng là lý do research và content phải là hai file, không gộp một.
>
> **3–7 nguồn. Dưới 3 thì DỪNG**, báo lại, đề xuất hoãn đề tài — đừng hạ chuẩn.

## S0 — Cổng sự thật

Đề bài nói gì, và điều đó có đúng không. Ghi rõ điều kiện đi tiếp: ≥3 nguồn uy tín và
chúng nhất quán về sự kiện chính. Không đủ, hoặc các nguồn mâu thuẫn nhau → dừng và báo.

## Nguồn

| # | URL | Tổ chức | Ngày xuất bản | Ngày truy cập | Mức đọc | Trích 1 câu |
|---|---|---|---|---|---|---|
| 1 | `knowledge/toolchains/ATLAS_CHANNEL.md` | repo này | 2026-09-04 | 2026-09-04 | toàn văn | "Cổng 1 là của NGƯỜI: agent không tự đặt `approved`." |
| 2 | `scripts/pipeline/blog_gates.py` | repo này | 2026-09-04 | 2026-09-04 | toàn văn | "23 cổng; trạng thái `thiếu` không bao giờ được tính là `xanh`." |
| 3 | `scripts/pipeline/new_post.py` | repo này | 2026-09-04 | 2026-09-04 | toàn văn | "Bài sinh ra ở `proposed`; ô `g1` để trống cho tới khi người điền ngày." |

> Ví dụ này lấy nguồn từ chính repo — mở file là kiểm được. Bài thật lấy nguồn ngoài, và
> mỗi dòng phải ghi đủ tổ chức, ngày, mức đọc. **3–7 nguồn; dưới 3 thì DỪNG.**

> **Mức đọc**: *toàn văn* hay *trích dẫn tìm kiếm*. Nguồn bị chặn tự động thì ghi rõ —
> "đã xác nhận ở mức tóm tắt" khác với "đã đọc".

## Dữ kiện đã đối chiếu

- `new_post.py` tạo bài ở `status=proposed`, ô `g1` rỗng — script không có đường nào tự đặt
  `approved` (kiểm bằng test `test_chuoi_day_du_va_KHONG_tu_dat_approved`).
- Bộ cổng có ba trạng thái: xanh · đỏ · **thiếu**. "Thiếu" không được cộng vào "xanh" —
  cổng không chạy được là chưa biết, không phải là qua.
- `register_publish approve` bắt buộc có `--by` và `--note` — duyệt mà không để lại dấu vết
  thì sau này không ai biết ai duyệt và duyệt cái gì.

## ⚠️ Mâu thuẫn giữa các nguồn — KHÔNG được chép bừa một con số

Hai nguồn lệch nhau thì **nêu cả hai và nói rõ là chúng lệch**, đừng chọn con số đẹp hơn.

## Phản biện có nguồn

- **"Cổng người làm chậm."** Đúng — và đó là điều được chọn. Phép đo phải là *số bài phải
  gỡ hoặc sửa sau khi đăng*, không phải *số bài mỗi tuần*. Repo này chưa có đủ mẫu để công
  bố con số đó, nên bài không được nêu con số nào.
- **"Cổng máy đủ rồi."** Không. 23 cổng kiểm được độ dài, nguồn, link gãy, chữ mẫu còn sót,
  tên công cụ nội bộ lọt ra ngoài — không cổng nào trả lời được *bài này có đáng đăng không*.

Để bài không thành bài quảng cáo. Ưu tiên phản biện đến từ chính người làm ra thứ đang bàn.

## Use-case doanh nghiệp thật, có dẫn nguồn

Chính repo này: một bài (`AST-001`) đi qua đủ B0→B12, đăng thật lên ba kênh, có URL kiểm
được ghi trong bảng Content của `campaign.md`. Cổng 1 và Cổng 2 đều do người bấm.

> Bài thật cần use-case **ngoài** tổ chức mình. Không tìm ra thì hoãn đề tài, đừng thay
> bằng ví dụ giả định.

Không tìm ra thì **hoãn đề tài**, đừng thay bằng ví dụ giả định.

## Chưa xác minh được — KHÔNG đưa vào bài như sự thật

- Cổng người tiết kiệm được bao nhiêu thời gian sửa về sau. Chưa đo. **Không đưa vào bài.**
- Bao nhiêu phần trăm bài do agent viết bị đánh giá là rỗng. Không có số đáng tin. Bỏ.

## Kiểm sau (append-only)
