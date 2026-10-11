---
name: marketing-measurement
description: Design tracking plans, UTM conventions, metric hierarchies, and controlled A/B test briefs without claiming unverified analytics connectors or declaring premature winners.
---

# Đo lường & Thử nghiệm (Marketing Measurement)

Thiết kế hệ thống chỉ số đo lường (KPI), kế hoạch gắn thẻ UTM và đề cương thử nghiệm A/B phục vụ ra quyết định kinh doanh dựa trên dữ liệu xác thực.

## Khi nào dùng
- Cần lập kế hoạch đo lường hiệu quả chiến dịch (KPI hierarchy, mốc chốt D+1/D+7/D+30).
- Cần quy chuẩn hóa tham số gắn thẻ UTM liên kênh (Facebook, LinkedIn, Email, YouTube).
- Cần thiết kế đề cương thử nghiệm A/B (giả thuyết, mẫu số, chỉ số chính và chỉ số an toàn).

## Khi không dùng
- Đòi hỏi kết nối API analytics tự động trực tiếp từ nền tảng (hiện tại nhập số liệu thủ công).
- Chiến dịch chưa xuất bản hoặc chưa có bài viết nào được đăng tải (dùng `campaign-pipeline`).

## Đầu vào cần có
- Mục tiêu chiến dịch cần đo lường hoặc câu hỏi kinh doanh cần trả lời.
- Kênh phát hành và liên kết trang đích dự kiến gắn thẻ.
- Dữ liệu cơ sở (baseline) hoặc số liệu thu thập được từ dashboard nền tảng (nếu có).

## Trao đổi tư vấn
- Xác định rõ quyết định nào sẽ thay đổi dựa trên chỉ số này; không đo lường chỉ để trang trí.
- Nêu rõ các hạn chế về công cụ (chưa có API tự động, số liệu do con người nhập tay theo mốc).
- Khi lượng mẫu chưa đạt mức tối thiểu: bắt buộc ghi nhận trạng thái "chưa đủ mẫu", cấm tự phong biến thể thắng cuộc.

## Các bước thực hiện
1. **Xác định chỉ số quyết định:** Phân cấp chỉ số (Kết quả kinh doanh → Đòn bẩy chuyển đổi → Tiêu thụ).
2. **Lập bảng gắn thẻ UTM:** Chuẩn hóa các tham số `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`.
3. **Thiết kế đề cương thử nghiệm (nếu có A/B):** Soạn giả thuyết, xác định chỉ số chính, chỉ số an toàn và cỡ mẫu tối thiểu theo `templates/EXPERIMENT_BRIEF_TEMPLATE.md`.
4. **Đối chiếu & Báo cáo kết quả:** So sánh số thực tế với mục tiêu; nối thêm (append) snapshot vào Mục 9 của campaign, tuyệt đối không ghi đè lịch sử.

## Đầu ra
- Kế hoạch đo lường và danh mục sự kiện (`templates/TRACKING_PLAN_TEMPLATE.md`).
- Đề cương thử nghiệm A/B (`templates/EXPERIMENT_BRIEF_TEMPLATE.md`).
- Snapshot báo cáo định kỳ theo các mốc chốt (D+1, D+7, D+30).

## Kiểm tra chất lượng & Dừng
- Phân biệt rõ dữ liệu thật và số giả định; thiếu mẫu phải ghi rõ "chưa đủ mẫu".
- Đạt yêu cầu: bàn giao kế hoạch đo lường hoặc đề cương thử nghiệm cho người dùng phê duyệt.

## Tài liệu tham khảo
- Sổ tay chi tiết: `knowledge/playbooks/MEASUREMENT_PLAYBOOK.md`
- Quy trình đo lường khâu 7: `workflows/07_measure.md`
- Hợp đồng tư vấn: `.agents/skills/marketing-routing/references/consultation.md`
