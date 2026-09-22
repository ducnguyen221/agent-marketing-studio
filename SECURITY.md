# SECURITY.md — Chính Sách An Toàn & Bảo Mật Dữ Liệu

## 1. Nguyên Tắc Bảo Vệ Token & Credentials
- **Tuyệt đối cấm commit API token** (Facebook Graph API, YouTube Data API, OpenAI/Claude API keys, Mailchimp/Klaviyo tokens) vào kho Git.
- Mọi token nằm trong **file** ở kho bí mật ngoài git (mặc định `~/.secret/<tài-khoản>/`). Biến
  môi trường chỉ giữ **đường dẫn** tới file đó, không giữ giá trị. Chi tiết:
  `knowledge/toolchains/SECRETS.md`.
- **Trạm nội dung không bao giờ vào git.** `brand.md` (hồ sơ cá nhân của tác giả) và
  `publish.json` (link thật, ID bài) không được commit lên repo công khai. `channel.yml` chỉ
  ghi **TÊN biến môi trường** của secret, không bao giờ ghi giá trị.
  Chế độ cài `embedded` đặt trạm ở `<repo>/workspace/` cho tiện — và vì nó nằm trong repo,
  nó có **ba** lớp rào, không phải một: `.gitignore` (`/workspace/`, `.env`, `.env.*`,
  `studio.local.json`), hook `templates/hooks/pre-commit` (chặn cả `git add -f` và dòng thêm
  mới trông giống token), và `scripts/pipeline/doctor.py` đo lại rằng hai lớp trên còn sống.
- Dự án chỉ cung cấp `.env.example` — danh mục TÊN biến, không có giá trị. `.env*` bị
  gitignore. Ở chế độ `embedded`, `<repo>/.env` **được script nạp** (`studio_paths.secret_env`)
  nhưng vẫn chỉ giữ **đường dẫn** và cấu hình máy: token sống trong file JSON ngoài git mà
  đường dẫn đó trỏ tới, không bao giờ trong `.env`.

## 2. Bảo Vệ Dữ Liệu Khách Hàng & Leads (PII)
- Dữ liệu thu thập từ các chiến dịch (họ tên, email, số điện thoại người đăng ký) **không bao giờ được lưu trực tiếp vào repository**.
- Lead phải được đẩy thẳng vào CRM / Database bảo mật. File Excel và Markdown trong kho chỉ lưu trữ số liệu tổng hợp (`actual_leads`, `actual_conversions`).

## 3. Ranh Giới An Toàn Cho Tác Nhân AI Agent
- Agent **không bao giờ tự động phát hành (Publish)** nội dung ra các kênh công khai khi chưa có sự xác nhận của con người ở Cổng 2 (`Post.review_status = approved`).
- Mọi hành động gọi API xuất bản ra bên ngoài ở chế độ mặc định đều là `dry-run` trừ khi được ủy quyền rõ ràng.