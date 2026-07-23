# Bản đồ tri thức — cần gì đọc file nào

Tra bảng này trước. Đừng đọc bừa cả repo.

| Cần gì | Đọc |
|---|---|
| **Cách agent làm việc, quy trình 5 bước** | `AGENTS.md` (gốc repo) |
| Không biết bắt đầu từ đâu | `agent/workflows/00_WORKFLOW_INDEX.md` |
| Dựng campaign mới | `agent/templates/CAMPAIGN_TEMPLATE.md` |
| Viết 1 bài (content.md đa kênh) | `agent/templates/CONTENT_TEMPLATE.md` |
| Giọng blog | `agent/output-styles/compa-class-blog.md` |
| Giọng + format Facebook (post dài + caption Reel) | `agent/output-styles/tobi-post.md` |
| Format độ dài/hashtag/link theo kênh | `agent/output-styles/multichannel-style.md` |
| Công thức tiêu đề, khung bài, hook | `agent/knowledge/COPY_FRAMEWORKS.md` |
| Tâm lý học marketing, vì sao người ta mua | `agent/knowledge/MARKETING_PSYCHOLOGY.md` |
| Newsletter | `agent/templates/EMAIL_NEWSLETTER_TEMPLATE.md` |
| Tái chế nội dung 30 ngày | `agent/templates/RECYCLING_PLAN_TEMPLATE.md` |
| Dựng file HTML tự chứa hình dung bài (chuyển folder không vỡ) | `scripts/pipeline/build_preview.py` |
| Nối agent với Facebook/YouTube | `agent/knowledge/PLATFORM_SETUP.md` |
| **Cột nào ở sheet nào, luật cổng** | `schema/workbook_spec.yml` |
| Một campaign hoàn chỉnh trông thế nào | `content/KPIM/02_campaigns/01_Tobi_Posts/` |

## Mô hình dữ liệu (nhắc lại vì hay nhầm)

Mỗi campaign = **1 folder + 1 file `.md` (hồ sơ) + 1 file `.xlsx` (5 sheet)**.

| Sheet | Là gì |
|---|---|
| Campaign | form dọc — metadata nghiệp vụ |
| Post | bảng chủ — 1 bài/dòng, 3 cổng duyệt approve_topic/content/final ở đây |
| Result | URL + ID sau khi đăng |
| Engagement | số liệu nền tảng kéo về (dữ liệu DUY NHẤT đến từ ngoài file) |
| Assets | sổ file thật của bài |

Asset từng bài: `<folder campaign>/assets/<post_id>_<slug>/content.md, blog.md, ...`

## Luật chống ảo giác

Thư mục chỉ có `README`/`.gitkeep` = kho rỗng. Không suy nội dung từ tên thư mục.
Nếu file không có thông tin, nói "chưa có" — đừng dựng ra.

## Nguồn chưng cất

Một số file knowledge chưng cất tri thức chuẩn ngành từ các repo marketing mã nguồn mở (MIT), viết lại và Việt hoá cho model của repo này:
- `coreyhaines31/marketingskills` (41k★) — copy frameworks, hook system, marketing psychology.
- `zubair-trabzada/ai-marketing-claude`, `blacktwist/social-media-skills`, `AgriciDaniel/claude-youtube` — social/YouTube playbook.
