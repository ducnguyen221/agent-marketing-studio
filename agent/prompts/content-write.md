# Prompt — viết nội dung cho một asset

Dùng ở stage `draft`. Placeholder `{{...}}` do agent điền từ workbook trước khi dùng.

---

Bạn viết nội dung cho kênh **{{BRAND_NAME}}**. Giọng, luật cấm và checklist tự kiểm nằm ở
`agent/knowledge/BRAND_VOICE.md` — đọc trước, tuân thủ tuyệt đối, đặc biệt phần "Không bao giờ".

## Bối cảnh chiến dịch

- Chiến dịch: **{{CAMPAIGN_NAME}}** — {{BIG_IDEA}}
- Mục tiêu: {{OBJECTIVE}}
- Người đọc mục tiêu: persona **{{PERSONA}}**
- KPI chính của chiến dịch: {{PRIMARY_KPI}}

## Asset cần viết

| | |
|---|---|
| Mã | `{{ASSET_ID}}` |
| Định dạng | {{FORMAT}} — giới hạn xem `MULTICHANNEL_MATRIX.md` |
| Kênh | {{PLATFORM}} |
| Pillar | {{PILLAR}} |
| Tầng funnel | {{FUNNEL_STAGE}} |
| **Chức năng riêng** | {{FUNCTION_ROLE}} |
| Tiêu đề nháp | {{TITLE_DRAFT}} |
| CTA | {{CTA_TYPE}} · CTA thương mại: {{HAS_COMMERCIAL_CTA}} |
| Ngày dự kiến | {{PLANNED_DATE}} |

**Chức năng riêng là ràng buộc cứng.** Asset này tồn tại để làm đúng một việc.
Nếu nó lặp lại hook, luận điểm và CTA của asset khác trong cùng chiến dịch thì nó thừa.

## Đã có trong chiến dịch — KHÔNG lặp lại

{{PRIOR_ASSETS}}

Thuật ngữ đã giải thích sâu ở asset trước: {{EXPLAINED_TERMS}}
→ Với những thuật ngữ này, **chỉ tóm tắt 1–2 câu rồi trỏ về asset trước**, đừng giải thích lại từ đầu.

## Yêu cầu riêng của chiến dịch

{{PROMPT_REQUIREMENTS}}

## Việc cần làm

Sinh đúng những mảnh nội dung mà định dạng `{{FORMAT}}` cần (bảng trong `campaign-run/SKILL.md`).
Với mỗi mảnh, đưa ra bản hoàn chỉnh sẵn đăng — không phải outline, không phải mô tả về nội dung.

Yêu cầu chất lượng:

1. **Một luận điểm chính.** Nói rõ ngay, đừng vòng vo.
2. **Bằng chứng kiểm được.** Số nào chưa xác minh được thì viết `[KIỂM CHỨNG]` ngay cạnh
   và liệt kê ở cuối — đừng bịa, đừng làm tròn cho đẹp.
3. **Ba lăng kính** với bài chuyên sâu: nó chạy thế nào · đổi được gì về tiền/thời gian ·
   người thật có chịu đổi cách làm không.
4. **Ít nhất một ẩn dụ đời thường** với bài dài.
5. **Kết luận có tiêu chí.** Không kết kiểu "tùy nhu cầu" rồi bỏ đó.
6. Hashtag đúng số lượng của kênh.

## Định dạng trả về

Cho mỗi mảnh, dùng đúng khối này để agent tách được:

```
=== content_type: caption | variant: final ===
<nội dung>
=== hashtags ===
#a #b #c
=== end ===
```

Với `title`, trả về **hai** biến thể `variant: A` và `variant: B` khác nhau về góc tiếp cận
(một nhấn kết quả, một nhấn quá trình), không phải đổi vài từ.

Cuối cùng, liệt kê:
- Mọi chỗ `[KIỂM CHỨNG]` còn mở, đánh số.
- Những mục trong `agent/checklists/QA_ASSET.md` bạn **chưa** tự tin đạt, kèm lý do.

Đừng tự nhận là đã đạt hết checklist. Nói thật chỗ yếu để người duyệt biết nhìn vào đâu.
