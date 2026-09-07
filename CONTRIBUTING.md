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
   - Rồi cập nhật `templates/station/_channel/_campaign/campaign.md` (bảng Content) và `COT_CONTENT`/`COT_POST` trong
     `scripts/pipeline/export_excel.py`.
   - **Bộ cột bản xuất Excel phải khớp `templates/CAMPAIGN_TEMPLATE.xlsx`** — người dùng có
     biểu mẫu và pivot bám vào thứ tự cột đó. `tests/test_export_excel.py` so trực tiếp với
     file template, nên đổi một bên mà quên bên kia là test đỏ ngay.

5. **Thêm/Sửa Khuôn (Template):**
   - Khuôn trạm nằm ở `templates/station/`, lồng **đúng hình dạng trạm thật**:
     `_channel/` → `_campaign/` → `_content/`. Thư mục mở đầu bằng `_` là khuôn, không phải
     kênh/chiến dịch thật.
   - Sửa khuôn thì phải sửa cả script chép nó (`new_channel.py` · `new_campaign.py` ·
     `new_post.py`) — chúng trỏ vào `TPL_STATION / TPL_KENH / TPL_CAM / TPL_BAI`.
   - **Khuôn không được đoán hộ kênh thật.** `content_pillar` và `channels` trong
     `campaign.md` mẫu bị script thu hẹp về đúng bộ của kênh lúc tạo; giữ chữ mẫu thì chiến
     dịch vừa sinh ra đã đỏ ở `check_tree.py` trước khi người dùng kịp viết chữ nào.
   - `.ps1` sinh ra **bắt buộc có BOM UTF-8**: PowerShell 5.1 đọc `.ps1` không BOM sẽ
     parse-fail **im lặng** — scheduled task "chạy" mà không làm gì.
   - `tests/test_docs_khong_troi.py` bắt mọi đường dẫn `templates/…` trong tài liệu; đổi cây
     mà quên tài liệu là test đỏ ngay.
   - **Khuôn phải trung tính.** Chưng cất một script đang chạy về `templates/` thì mọi thứ
     thuộc nhận diện — tên kênh, tác giả, tên miền, email, id pixel — phải thành khoá cấu
     hình. `tests/test_dename.py::test_TEMPLATE_khong_mang_nhan_dien_that` quét cả cây và
     đỏ ngay; chi tiết bộ khoá ở `templates/README.md`.

## 2. Quy Trình Git & Pull Request
- Luôn tạo nhánh mới: `feat/<feature-name>` hoặc `fix/<issue-name>`.
- Commit tuân thủ Conventional Commits: `feat(skills): add tiktok-script-writer`, `docs(data-model): add thread_post_id`.
- PR phải vượt qua toàn bộ checks tự động và được Code Owner phê duyệt trước khi merge vào `main`.