# SECURITY.md — Chính Sách An Toàn & Bảo Mật Dữ Liệu

## 1. Nguyên Tắc Bảo Vệ Token & Credentials
- **Tuyệt đối cấm commit API token** (Facebook Graph API, YouTube Data API, OpenAI/Claude API keys, Mailchimp/Klaviyo tokens) vào kho Git.
- Mọi token phải được cấu hình qua file `.env` ở cấp máy tính hoặc cấp trạm, và đã được khai
  báo trong `.gitignore`.
- **Trạm nội dung nằm ngoài git.** `profile.md` (hồ sơ cá nhân của tác giả) và `publish.json`
  (link thật, ID bài) không bao giờ được commit lên repo công khai. `channel.yml` chỉ ghi
  **TÊN biến môi trường** của secret, không bao giờ ghi giá trị.
- Dự án chỉ cung cấp file mẫu `.env.example` với các trường biến giả định.

## 2. Bảo Vệ Dữ Liệu Khách Hàng & Leads (PII)
- Dữ liệu thu thập từ các chiến dịch (họ tên, email, số điện thoại người đăng ký) **không bao giờ được lưu trực tiếp vào repository**.
- Lead phải được đẩy thẳng vào CRM / Database bảo mật. File Excel và Markdown trong kho chỉ lưu trữ số liệu tổng hợp (`actual_leads`, `actual_conversions`).

## 3. Ranh Giới An Toàn Cho Tác Nhân AI Agent
- Agent **không bao giờ tự động phát hành (Publish)** nội dung ra các kênh công khai khi chưa có sự xác nhận của con người ở Cổng 2 (`Post.review_status = approved`).
- Mọi hành động gọi API xuất bản ra bên ngoài ở chế độ mặc định đều là `dry-run` trừ khi được ủy quyền rõ ràng.