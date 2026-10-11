# Lịch sử thay đổi

## 2026-10-11

- **Định tuyến & Nền tảng (A0):** Bổ sung catalog và router theo yêu cầu/trạng thái campaign (`marketing-routing`); làm rõ tư vấn độc lập không ghi campaign và production campaign vẫn cần cổng hiện hành. Cập nhật `AGENTS.md` (DN3), `MAP.md`, validator catalog và workflow/role liên quan.
- **Nghiên cứu & Chiến lược (A1):** Triển khai `customer-research`, `content-strategy`, khuôn mẫu `PRODUCT_MARKETING_CONTEXT.md`, sổ tay `CUSTOMER_RESEARCH.md`, `CONTENT_STRATEGY.md` cùng các biểu mẫu tổng hợp insight và ma trận ưu tiên đề tài. Nâng cấp `content-production` hỗ trợ 2 chế độ (`campaign` và `standalone-edit`) cùng sổ tay 7 lượt biên tập `COPY_EDITING.md`.
- **Chuyển đổi & Thu hút Lead (Đợt B):** Triển khai `offer-design`, `lead-generation`, `conversion-optimization` cùng các sổ tay `OFFER_DESIGN.md`, `LEAD_GENERATION.md`, `CRO_PLAYBOOK.md` và các biểu mẫu `OFFER_BRIEF_TEMPLATE.md`, `LEAD_MAGNET_TEMPLATE.md`.
- **Đo lường & Thử nghiệm (Đợt C):** Triển khai `marketing-measurement`, sổ tay `MEASUREMENT_PLAYBOOK.md`, kế hoạch gắn thẻ `TRACKING_PLAN_TEMPLATE.md` và đề cương thử nghiệm A/B `EXPERIMENT_BRIEF_TEMPLATE.md`.
- **Đồng bộ hệ thống & Host Adapters:** Hoàn tất 11 skills đích trong `.agents/skill-catalog.yaml`, tự động đồng bộ bảng chọn skill trong `MAP.md` và sinh toàn bộ host adapter Claude (`.claude/skills/`).
