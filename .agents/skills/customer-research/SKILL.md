---
name: customer-research
description: Analyze customer reviews, transcripts, or survey responses to extract verified pains, desires, objections, and verbatim customer language by segment without inventing personas.
---

# Nghiên cứu khách hàng (Customer Research)

Trích xuất insight khách hàng có căn cứ từ dữ liệu thực tế (review, phỏng vấn, khảo sát, ticket) phục vụ định vị và nội dung.

## Khi nào dùng
- Người dùng yêu cầu tìm hiểu nhu cầu, nỗi đau hoặc rào cản thực tế của khách hàng.
- Cần phân tích tài liệu phản hồi (review, transcript, khảo sát, hội thoại bán hàng).
- Cần trích xuất ngôn ngữ thực tế của khách hàng (Voice of Customer) để viết thông điệp.

## Khi không dùng
- Tìm kiếm tin tức sự kiện bên ngoài cho bài viết đơn lẻ (dùng research của bài).
- Đã có brief rõ và chỉ cần lập dàn ý hoặc viết bài (dùng `campaign-pipeline` hoặc `content-production`).

## Đầu vào cần có
- Dữ liệu khách hàng thực tế (file dữ liệu, đoạn trích transcript, danh sách review).
- Bối cảnh sản phẩm hoặc phân khúc quan tâm (nếu có).

## Trao đổi tư vấn
- Nếu chưa rõ phân khúc: hỏi nhóm khách hàng cụ thể cần ưu tiên phân tích.
- Nếu dữ liệu ít: nêu rõ hạn chế mẫu, gắn nhãn giả định (`ASSUMPTION`) cho các điểm chưa đủ chứng cứ.
- Không tự bịa lời nhận xét hoặc persona không có trong dữ liệu.

## Các bước thực hiện
1. **Tiếp nhận & làm sạch:** Đọc dữ liệu được giao, loại bỏ PII, xác định phân khúc và bối cảnh của nguồn.
2. **Phân loại 4 trục:** Nhóm dữ liệu vào Nỗi đau (Pains), Rào cản (Objections), Động lực (Triggers), Giải pháp thay thế (Alternatives).
3. **Đánh giá mức tin cậy:** Gán mức Cao (≥3 nguồn lặp lại), Vừa (1-2 nguồn rõ), Thấp (ý kiến cá biệt/suy luận).
4. **Trích xuất Voice of Customer:** Ghi lại các cụm từ nguyên văn sinh động khách hàng dùng để mô tả vấn đề.
5. **Tổng hợp báo cáo:** Điền kết quả vào bảng theo mẫu `templates/CUSTOMER_RESEARCH_TEMPLATE.md`.

## Đầu ra
- Bảng tổng hợp insight khách hàng phân theo chủ đề và mức độ tin cậy.
- Ma trận đối chiếu ngôn ngữ khách hàng (VoC) và thuật ngữ nội bộ.
- Danh sách khoảng trống dữ liệu và mâu thuẫn cần lưu ý.

## Kiểm tra chất lượng & Dừng
- Mọi insight đều có trích dẫn hoặc nguồn gốc rõ ràng, không có persona giả tưởng.
- Đạt yêu cầu: bàn giao bảng insight cho người dùng hoặc chuyển tiếp sang `content-strategy`.

## Tài liệu tham khảo
- Chi tiết phương pháp: `knowledge/playbooks/CUSTOMER_RESEARCH.md`
- Mẫu báo cáo: `templates/CUSTOMER_RESEARCH_TEMPLATE.md`
- Hợp đồng tư vấn: `.agents/skills/marketing-routing/references/consultation.md`
