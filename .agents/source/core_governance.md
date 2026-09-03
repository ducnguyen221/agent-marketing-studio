# Core Governance — Luật Cốt Lõi Của agent-marketing-studio

1. **Excel Là Single Source of Execution State:** Mọi thay đổi trạng thái phải được ghi nhận vào file `.xlsx`.
2. **Con Người Kiểm Soát 2 Cổng Duyệt:**
   - Cổng 1: `Content.status = approved` + `approved_date`.
   - Cổng 2: `Post.review_status = approved`.
   Agent không bao giờ tự ý vượt cổng.
3. **Bảo Mật Tuyệt Đối:** Không đưa token, secret hoặc dữ liệu khách hàng vào repo.