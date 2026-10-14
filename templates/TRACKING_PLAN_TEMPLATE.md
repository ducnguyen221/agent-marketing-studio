---
title: "Tracking Plan Template"
doc: template
repo: agent-marketing-team
version: "1.1.10"
---

# Kế hoạch đo lường & Danh mục sự kiện (Tracking Plan)

---

## 1. Thông tin chung
- **Chiến dịch / Dự án:** [Mã hoặc tên chiến dịch]
- **Kênh áp dụng:** [Website / Blog / Landing Page / Social]
- **Mục tiêu đo lường chính:** [Theo dõi chuyển đổi form / Tải tài liệu / Xem trang]

---

## 2. Bảng phân loại sự kiện (Event Taxonomy)

| Tên sự kiện | Điều kiện kích hoạt (Trigger) | Tham số cần gửi (Parameters) | Vị trí đặt mã | Quyết định liên quan |
|---|---|---|---|---|
| `view_landing_page` | Người dùng tải trang đích thành công | `page_path`, `referrer`, `utm_source` | Header trang | Đánh giá lưu lượng đầu phễu |
| `click_cta_button` | Người dùng nhấn nút kêu gọi hành động | `cta_text`, `cta_location`, `button_id` | Nút đăng ký | Đo lường mức độ hấp dẫn của CTA |
| `submit_lead_form` | Người dùng gửi form thành công | `form_id`, `lead_magnet_name` | Form xử lý | Đo lường tỷ lệ thu hút Lead thực tế |
| `download_asset` | Người dùng nhấn link tải tài liệu | `file_name`, `file_format` | Trang xác nhận | Đo lường mức độ tương tác sau đăng ký |

---

## 3. Quy ước cấu trúc URL & UTM

| Kênh phát hành | Mẫu URL hoàn chỉnh có gắn thẻ UTM |
|---|---|
| **Facebook Post** | `https://example.com/landing?utm_source=facebook&utm_medium=social-post&utm_campaign=[campaign_id]&utm_content=[post_id]` |
| **Email Newsletter**| `https://example.com/landing?utm_source=email&utm_medium=newsletter&utm_campaign=[campaign_id]&utm_content=cta-button` |
| **YouTube Description**| `https://example.com/landing?utm_source=youtube&utm_medium=video-desc&utm_campaign=[campaign_id]&utm_content=link-pinned` |

---

## 4. Quy trình kiểm tra dữ liệu (QA Data Collection)
- Kiểm tra URL có bị chuyển hướng (301 redirect) làm mất tham số UTM hay không.
- Thử nghiệm gửi dữ liệu thử từ môi trường test và xác nhận sự kiện xuất hiện đúng trên dashboard.
- Ghi nhận rõ ràng người phụ trách thu số và mốc thời gian chốt số liệu.
