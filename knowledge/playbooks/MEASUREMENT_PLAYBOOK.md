---
title: "Marketing Measurement Playbook"
doc: playbook
repo: agent-marketing-team
version: "1.1.10"
---

# Sổ tay đo lường & Thử nghiệm tiếp thị (Marketing Measurement Playbook)

Đọc khi: cần thiết kế kế hoạch đo lường, quy ước gắn thẻ UTM, xây dựng hệ thống chỉ số (KPI), hoặc thiết lập đề cương thử nghiệm A/B nhằm đưa ra quyết định dựa trên dữ liệu xác thực.

---

## 1. Nguyên tắc đo lường cốt lõi
1. **Đo lường phục vụ quyết định (Decision-driven Metrics):** Mỗi chỉ số thu thập phải phục vụ một quyết định kinh doanh cụ thể; không thu thập số liệu tràn lan chỉ để làm đẹp báo cáo.
2. **Không kết luận vội khi thiếu mẫu (No Underpowered Claims):** Khi lượng truy cập hoặc số chuyển đổi chưa đạt cỡ mẫu tối thiểu, bắt buộc ghi nhận trạng thái "chưa đủ mẫu" (`insufficient_sample`); tuyệt đối không tự xưng "biến thể thắng cuộc".
3. **Minh bạch nguồn và mốc thời gian:** Mọi số liệu phải ghi rõ nguồn trích xuất (Meta Business Suite, Google Analytics, YouTube Studio) và mốc chốt đo lường (D+1, D+7, D+30).
4. **Bảo toàn lịch sử đo lường:** Không ghi đè hoặc chỉnh sửa các báo cáo snapshot cũ; luôn nối thêm (append) mốc mới vào lịch sử theo dõi.
5. **Không giả định có kết nối API tự động:** Hiện tại hệ thống ghi nhận số liệu thủ công hoặc qua lệnh script; không bịa đặt rằng đã có connector đồng bộ tự động thời gian thực.

---

## 2. Phân cấp hệ thống chỉ số (Metric Hierarchy)

### Cấp 1: Chỉ số kết quả kinh doanh (Business Outcomes / North Star)
- Doanh thu mang lại, Số khách hàng trả phí mới, Chi phí thu hút một khách hàng (CAC), Giá trị vòng đời (LTV).
- Đây là mục tiêu tối thượng mà toàn bộ chiến dịch hướng tới.

### Cấp 2: Chỉ số chuyển đổi trung gian (Driver / Proxy Metrics)
- Số lượt đăng ký nhận tài liệu (Leads), Số cuộc hẹn tư vấn, Tỷ lệ chuyển đổi trang đích (CR), Tỷ lệ nhấp chuột (CTR).
- Phản ánh mức độ hiệu quả của thông điệp và lời chào hàng.

### Cấp 3: Chỉ số tiêu thụ & Tương tác (Consumption Metrics)
- Lượt tiếp cận (Reach), Lượt hiển thị (Impressions), Lượt xem video (Views), Lượt tương tác (Reactions, Comments, Shares).
- Phản ánh độ lan tỏa và khả năng giữ chân độc giả ở đầu phễu.

---

## 3. Quy ước gắn thẻ UTM (UTM Tagging Standards)
Mọi liên kết dẫn về website hoặc trang đích bắt buộc phải có đủ 5 tham số chuẩn hóa (viết thường, không dấu, nối bằng gạch nối `-`):
- `utm_source`: Kênh phát hành (`facebook`, `linkedin`, `youtube`, `email`, `threads`).
- `utm_medium`: Định dạng truyền thông (`social-post`, `newsletter`, `video-desc`, `bio-link`).
- `utm_campaign`: Mã chiến dịch khớp với thư mục bài viết (`cmp-2610-ai-news`).
- `utm_content`: Biến thể nội dung hoặc góc tiếp cận (`cta-button`, `text-link`, `hook-v1`).
- `utm_term`: Từ khóa tìm kiếm hoặc phân khúc độc giả (tùy chọn).

---

## 4. Khung thiết kế thử nghiệm A/B (A/B Testing Framework)

1. **Giả thuyết khoa học:** Soạn theo mẫu: *Nếu thay đổi [Biến số A], thì [Chỉ số chính B] sẽ tăng, vì [Lý do tâm lý/hành vi C].*
2. **Chỉ số chính (Primary Metric):** Duy nhất 1 chỉ số quyết định kết quả thử nghiệm (ví dụ: Tỷ lệ click vào nút đăng ký).
3. **Chỉ số an toàn (Guardrail Metric):** Chỉ số kiểm soát để tránh tối ưu cục bộ gây hại (ví dụ: Tỷ lệ thoát trang, Tỷ lệ hủy đăng ký email).
4. **Cỡ mẫu và thời gian tối thiểu:**
   - Thời gian chạy tối thiểu: Ít nhất 7 ngày đầy đủ để triệt tiêu ảnh hưởng của chu kỳ ngày trong tuần (day-of-week effect).
   - Cỡ mẫu tối thiểu: Cần đủ số lượt chuyển đổi ở mỗi biến thể trước khi đối chiếu; nếu dưới ngưỡng, duy trì trạng thái thử nghiệm chưa kết luận.
