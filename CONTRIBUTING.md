# CONTRIBUTING.md — Quy Chuẩn Đóng Góp & Phát Triển agent-marketing-studio

## 1. Nguyên Tắc Mở Rộng Hệ Thống
1. **Thêm Giọng Văn Mới (Brand Output Style):**
   - Đặt file mới vào `output_styles/<brand-slug>.md`.
   - Phải có đủ 3 phần: Giọng văn cốt lõi, Quy tắc định dạng theo kênh, và Bộ ví dụ Đúng/Sai.
2. **Thêm Role / Subagent Mới:**
   - Khai báo tại `.agents/roles/<role-name>.md`.
   - Định nghĩa rõ: Mục tiêu, Input, Output, Tools được dùng, và Khâu phụ trách trong 7 khâu.
3. **Thêm Kỹ Năng (Skill):**
   - Đặt trong `.agents/skills/<skill-name>/SKILL.md`.
4. **Sửa Đổi Mô Hình Dữ Liệu (Data Model):**
   - Mọi thay đổi trường dữ liệu phải bắt đầu từ `knowledge/data_model/DATA_MODEL.md`.
   - Rồi cập nhật `templates/campaign.md` (bảng Content) và `COT_CONTENT`/`COT_POST` trong
     `scripts/pipeline/export_excel.py`.
   - **Bộ cột bản xuất Excel phải khớp `templates/CAMPAIGN_TEMPLATE.xlsx`** — người dùng có
     biểu mẫu và pivot bám vào thứ tự cột đó. `tests/test_export_excel.py` so trực tiếp với
     file template, nên đổi một bên mà quên bên kia là test đỏ ngay.

## 2. Quy Trình Git & Pull Request
- Luôn tạo nhánh mới: `feat/<feature-name>` hoặc `fix/<issue-name>`.
- Commit tuân thủ Conventional Commits: `feat(skills): add tiktok-script-writer`, `docs(data-model): add thread_post_id`.
- PR phải vượt qua toàn bộ checks tự động và được Code Owner phê duyệt trước khi merge vào `main`.