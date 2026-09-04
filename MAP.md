# MAP.md — Task-Based Context Routing Map for agent-marketing-studio

> **Mục đích:** Hướng dẫn tác nhân AI Agent và người điều phối nạp ĐÚNG tài liệu cần thiết cho từng loại nhiệm vụ cụ thể, triệt tiêu tình trạng đọc lan man gây tràn Context Window.

---

## 1. Bản Đồ Định Tuyến Theo 7 Khâu Vận Hành

| Khâu / Nhiệm Vụ | Điểm Bắt Đầu | Tài Liệu Cần Đọc Tiếp | Tài Liệu Tuyệt Đối KHÔNG Đọc |
|---|---|---|---|
| **① Khởi tạo Chiến dịch (new)** | `workflows/01_new_campaign.md` | • `templates/campaign.md`<br>• `knowledge/data_model/DATA_MODEL.md` (Nhóm Strategic Brief) | • `output_styles/*`<br>• `knowledge/playbooks/*`<br>• `knowledge/toolchains/*` |
| **② Lập Kế hoạch Content (plan)** | `workflows/02_plan_content.md` | • `knowledge/playbooks/SEO_PLAYBOOK.md`<br>• `knowledge/playbooks/COPY_FRAMEWORKS.md`<br>• frontmatter `campaign.md` của chiến dịch<br>• `continuity.json` của kênh (tránh trùng đề tài) | • `knowledge/toolchains/*`<br>• `output_styles/*` (chưa cần ở bước ý tưởng) |
| **③ Viết Bài Đa Kênh (produce)** | `workflows/03_produce_content.md` | **Bắt buộc cả ba:**<br>• `campaign.md` của chiến dịch<br>• `profile.md` ở gốc kênh (fail-closed)<br>• `research.md` của chính bài<br>Rồi: `output_styles/<brand_style>.md` · `.agents/skills/hook-writer/SKILL.md` | • `workflows/06_publish.md`<br>• `knowledge/toolchains/PLATFORM_SETUP.md` |
| **④ Máy Tự Kiểm Tra (selfqa)** | `workflows/04_self_qa.md` | • `.agents/checklists/QA_ASSET.md`<br>• `output_styles/<brand_style>.md` | • `templates/*`<br>• `knowledge/toolchains/*` |
| **⑤ Dựng Asset Hình/Tiếng (render)**| `workflows/05_render_assets.md` | • `knowledge/toolchains/ASSET_TOOLCHAIN.md` | • `output_styles/*`<br>• `knowledge/playbooks/*` |
| **⑥ Đăng Bài & Hẹn Giờ (publish)** | `workflows/06_publish.md` | • `knowledge/toolchains/ATLAS_CHANNEL.md` (trình tự 10 bước một bài blog)<br>• `knowledge/toolchains/PLATFORM_SETUP.md`<br>• Hồ sơ `.md` Mục 5 (Giờ vàng đăng bài) | • `templates/*`<br>• `knowledge/psychology/*` |
| **⑦ Đo Lường & Báo Cáo (measure)**| `workflows/07_measure.md` | • `knowledge/data_model/DATA_MODEL.md` (Nhóm Measurement)<br>• `campaign.md` Mục 9 (nơi DUY NHẤT giữ lịch sử đo) | • `output_styles/*`<br>• `templates/*` |

---

## 2. Bản Đồ Định Tuyến Theo Tác Vụ Đặc Thù

| Tác Vụ Đặc Thù | Điểm Bắt Đầu | Tài Liệu Cần Đọc Tiếp |
|---|---|---|
| **Thêm kênh mạng xã hội mới** | `knowledge/toolchains/PLATFORM_SETUP.md` | `knowledge/data_model/DATA_MODEL.md` (enum `channels`) |
| **Thêm giọng văn thương hiệu mới** | `output_styles/README.md` | `output_styles/compa-class-blog.md` (file mẫu) |
| **Sửa đổi trường dữ liệu** | `knowledge/data_model/DATA_MODEL.md` | `templates/campaign.md` · `scripts/pipeline/export_excel.py` (bộ cột bản xuất) |
| **Dựng trạm nội dung mới** | `install.ps1` | `examples/README.md` (trạm mẫu đã điền) · `README.md` §3 |
| **Xem một trạm đã điền trông thế nào** | `examples/README.md` | `examples/vi-du-studio/` |
| **Kiểm cây liên kết / tìm bài mồ côi** | `scripts/pipeline/check_tree.py` | `workflows/00_WORKFLOW_INDEX.md` |
| **Nâng cấp công cụ / Role Agent** | `.agents/README.md` | `.agents/roles/`, `.agents/skills/` |
---

## 3. Tra Cứu Theo Nhu Cầu (không gắn với khâu nào)

| Cần gì | Đọc |
|---|---|
| Cách agent làm việc, ranh giới an toàn, 2 cổng duyệt | `AGENTS.md` |
| Không biết bắt đầu từ đâu · ai làm khâu nào | `workflows/00_WORKFLOW_INDEX.md` |
| Điều hướng cả chu trình 7 khâu | `.agents/skills/campaign-pipeline/SKILL.md` |
| Sản xuất nội dung từ Content đã duyệt | `.agents/skills/content-production/SKILL.md` |
| Viết hook / câu mở chặn lướt | `.agents/skills/hook-writer/SKILL.md` |
| Viết thread / chuỗi bài | `.agents/skills/thread-writer/SKILL.md` |
| Tâm lý học marketing, vì sao người ta mua | `knowledge/psychology/MARKETING_PSYCHOLOGY.md` |
| Retention / thumbnail / Shorts YouTube | `knowledge/playbooks/YOUTUBE_PLAYBOOK.md` |
| Chuỗi email nuôi dưỡng / chuyển đổi | `knowledge/toolchains/EMAIL_SEQUENCES.md` |
| Newsletter định kỳ | `templates/EMAIL_NEWSLETTER_TEMPLATE.md` |
| Tái chế nội dung 30 ngày | `templates/RECYCLING_PLAN_TEMPLATE.md` |
| Dựng HTML tự chứa để xem trước bài | `scripts/pipeline/build_preview.py` |
| Một campaign hoàn chỉnh trông thế nào | `content/KPIM/02_campaigns/01_Tobi_Posts/` |
| **Một bài blog đi từ đâu tới đâu** (10 bước, 2 cổng duyệt) | `knowledge/toolchains/ATLAS_CHANNEL.md` |
| **Kiểm định dạng bài Facebook** (bold, link, hashtag) | `scripts/pipeline/fb_format.py --check` |
| **Chấm một bài bằng 22 cổng đếm được** | `scripts/pipeline/blog_gates.py <thư mục bài>` |
| **Số đo thật của bài đã đăng, để đặt ngưỡng** | `fixtures/baseline/blog_baseline.md` |
| **Dựng ảnh infographic tóm tắt cả bài** (prompt mẫu + cổng kiểm chính tả) | `templates/INFOGRAPHIC_PROMPT_TEMPLATE.md` |
| Nguồn chưng cất của kho tri thức (ghi công) | `knowledge/README.md` |

**Luật chống ảo giác:** thư mục chỉ có `README`/`.gitkeep` = kho rỗng — không suy nội dung từ tên thư mục.
File không có thông tin thì nói "chưa có", đừng dựng ra.
