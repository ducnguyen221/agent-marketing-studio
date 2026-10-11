---
name: content-production
description: Produce ready-to-publish multi-channel assets from an approved campaign item, or polish independent drafts via 7-pass copy editing without bypassing campaign gates.
---

# Sản xuất nội dung & Biên tập (Content Production)

Sản xuất nội dung đa kênh sẵn-đăng từ brief chiến dịch đã duyệt Gate 1, hoặc biên tập nâng cao bản nháp độc lập qua 7 lượt biên tập.

## Khi nào dùng
- Sản xuất bài viết (blog, social, email, newsletter, landing copy) cho chiến dịch đã qua Gate 1.
- Biên tập, làm sắc nét và gọt giũa bản nháp (loại bỏ sáo rỗng AI, làm rõ luận điểm, kiểm tra claim).
- Tái chế một nội dung gốc sang nhiều định dạng kênh phát hành khác nhau.

## Khi không dùng
- Chưa có brief hoặc chiến dịch chưa qua Gate 1 (cần hoàn tất ở `campaign-pipeline`).
- Tư vấn định hướng chiến lược hoặc thay đổi gói dịch vụ/offer (dùng `content-strategy`).

## Hai chế độ hoạt động
1. **Chế độ `campaign` (Mặc định trong chiến dịch):**
   - Đòi hỏi: Chiến dịch đã qua Gate 1 (`Content.status = in_production`).
   - Đầu vào: `campaign.md` (frontmatter + brief), hồ sơ kênh (`brand.md`), research bài viết.
   - Đầu ra: Ghi file `content.md`, tạo khối `## post:<post_format>`, cập nhật trạng thái `Post.agent_status = completed`, chuẩn bị trình Gate 2.
2. **Chế độ `standalone-edit` (Biên tập độc lập):**
   - Đòi hỏi: Bản nháp độc lập không thuộc chiến dịch + mục tiêu biên tập + giọng kênh/nguồn.
   - Đầu vào: Văn bản nháp, đối tượng độc giả, tài liệu kiểm chứng (nếu có).
   - Đầu ra: Bản nháp đã chỉnh sửa + ghi chú lý do sửa; KHÔNG tạo thư mục bài, KHÔNG ghi trạng thái.
   - **Ranh giới cứng:** Nếu bản nháp thuộc về một chiến dịch đang quản lý, bắt buộc phải tuân theo chế độ `campaign` và kiểm tra Gate 1, nghiêm cấm dùng `standalone-edit` để né cổng duyệt.

## Quy trình sản xuất & Biên tập
1. **Tiếp nhận & Xác định chế độ:** Nhận brief hoặc bản nháp; kiểm tra tính hợp lệ của Gate 1 nếu là campaign.
2. **Khung bài & Giọng điệu:** Chọn công thức (`COPY_FRAMEWORKS.md`) và giọng theo kênh (`brand.md`, `output_styles/`).
3. **Áp dụng 7 lượt biên tập (`COPY_EDITING.md`):**
   - Lượt 1: Cấu trúc & Mạch lập luận (Flow & Structure).
   - Lượt 2: Độ rõ ràng & Tinh gọn (cắt sáo rỗng AI).
   - Lượt 3: Giọng tác giả & Phù hợp kênh.
   - Lượt 4: Bằng chứng & Tính cụ thể (gắn `[KIỂM CHỨNG]` cho số liệu chưa xác minh).
   - Lượt 5: Lời kêu gọi hành động (CTA) trực diện, duy nhất.
   - Lượt 6: Trình bày & Quét mắt (tiêu đề phụ, bullet, đoạn ngắn).
   - Lượt 7: Rà soát an toàn (loại bỏ PII, không lộ tool nội bộ).
4. **Kiểm tra QA:** Chạy checklist `checklists/QA_ASSET.md` trước khi bàn giao.

## Đầu ra
- Với `campaign`: File `content.md` chứa các khối `## post:<format>`, danh sách CTA và claim cần kiểm chứng.
- Với `standalone-edit`: Bản sửa hoàn chỉnh kèm bảng giải thích thay đổi.

## Kiểm tra chất lượng & Ranh giới an toàn
- Giữ nguyên sự thật và giọng tác giả; không tự ý thay đổi offer, cam kết hoặc chính sách giá.
- Không bịa đặt chứng chỉ, logo đối tác hoặc lời chứng thực của khách hàng.
- Số khối `## post:` phải khớp chính xác số dòng Post trong campaign.

## Tài liệu tham khảo
- Sổ tay biên tập 7 lượt: `knowledge/playbooks/COPY_EDITING.md`
- Công thức viết: `knowledge/playbooks/COPY_FRAMEWORKS.md`
- Checklist QA: `.agents/checklists/QA_ASSET.md`
