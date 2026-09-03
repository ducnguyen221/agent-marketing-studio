# Checklist QA một asset — chạy TRƯỚC khi đẩy sang người duyệt

Agent tự chạy. Mục nào trượt thì sửa trước, đừng đẩy sang người kèm lỗi bạn tự thấy được.
Kết quả ghi vào `05_Approval` (10 cột `chk_*`) khi người duyệt xác nhận.

## Nguồn và tính đúng đắn

- [ ] `chk_primary_source` — mọi số liệu có nguồn sơ cấp, ghi rõ ngày
- [ ] `chk_fact_opinion` — đã tách rõ *"Theo [nguồn]…"* với *"Theo mình…"*
- [ ] Mọi claim chưa xác minh được đều mang tag `[KIỂM CHỨNG]`, và
      `verification_open` đã đếm đúng số tag còn mở
- [ ] Không bịa số, không bịa tỷ lệ, không bịa tên khách hàng

## Đóng gói

- [ ] `chk_title_no_overclaim` — title không hứa quá nội dung thật đưa được
- [ ] Hook khớp title (không promise mismatch)
- [ ] `chk_thumbnail_honest` — thumbnail không đánh lừa; chữ trên thumbnail 2–4 từ
- [ ] Số tập đặt ở **cuối** title, không phải đầu

## Giữ chân và chuyển đổi

- [ ] `chk_subscribe_reason` — có lý do rõ ràng để đăng ký, không phải "nhớ subscribe nhé"
- [ ] `chk_next_bridge` — có đường xem tiếp (playlist, related video, link bài trước)
- [ ] Asset này có chức năng riêng, không trùng hook + luận điểm + CTA với asset khác
      trong cùng chiến dịch

## Kênh

- [ ] `chk_hashtag_ok` — đúng giới hạn: YouTube ≤3 · Shorts ≤6 · Facebook 6–13
- [ ] Định dạng đúng kênh (FB dùng Unicode bold + `———` chứ không dùng markdown)
- [ ] Link đặt đúng chỗ theo kênh (Facebook: **đầu bài**)
- [ ] Độ dài trong khoảng của kênh (xem `MULTICHANNEL_MATRIX.md`)

## Tuân thủ và an toàn

- [ ] `chk_cta_ok` — CTA thương mại chỉ xuất hiện ở tập được phép
      (`01_Brief.commercial_cta_episodes`)
- [ ] `chk_no_internal_tool` — **grep toàn bộ nội dung, kết quả phải rỗng**: tên công cụ
      và hạ tầng sản xuất nội bộ, cụm "giọng AI"
- [ ] `chk_no_pii` — không có thông tin định danh cá nhân, không credential, không token
- [ ] Ảnh/nhạc/tư liệu đều rõ quyền sử dụng

## Giọng

- [ ] Có luận điểm riêng, không phải tóm tắt trung tính
- [ ] Có ví dụ hoặc số cụ thể
- [ ] Có ẩn dụ đời thường (với bài dài)
- [ ] Kết luận có tiêu chí, không lửng kiểu "tùy nhu cầu"
- [ ] Không buzzword rỗng, không giật gân, không listicle "Top 10"

---

## Luật vàng khi phát hiện lỗi trong nội dung public-facing

Nội dung công khai mang giọng của tác giả. **Sửa sai còn tệ hơn để nguyên.**

Khi phát hiện lỗi, đừng tự sửa. Ghi thành danh sách, mỗi mục có:

| Trường | |
|---|---|
| Vị trí | file + dòng |
| Hiện tại | trích nguyên văn |
| Đề xuất | bản sửa cụ thể |
| **Độ tự tin** | **cao** = suy ra chắc chắn · **thấp** = có nhiều khả năng |

Mục **độ tự tin cao** → đề xuất và chờ một tiếng gật.
Mục **độ tự tin thấp** → nêu 2 phương án, để người chọn. Không đoán.

Ví dụ thật: heading `𝐄̆𝐈𝐄̂̉𝐌 𝐂𝐇𝐔𝐍𝐆` suy ra được là `ĐIỂM CHUNG` (tự tin cao, vì
`Đ` → `Ĕ` là lỗi chuyển Unicode bold đã biết). Nhưng `𝐐𝐔𝐀𝐍 𝐄̆𝐁𝐈𝐄̣̂𝐓 𝐍𝐇𝐀̂́𝐓`
thì không suy được — phải hỏi.
