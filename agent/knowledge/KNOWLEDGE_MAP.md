# Bản đồ tri thức — cần gì thì đọc file nào

Tra bảng này trước. Đừng đọc bừa cả repo — vừa tốn context vừa dễ lấy nhầm file cũ.

| Cần gì | Đọc |
|---|---|
| **Không biết bắt đầu từ đâu** | `agent/workflows/00_WORKFLOW_INDEX.md` ← điểm vào |
| Dựng chiến dịch mới | `agent/templates/README.md` + `campaign-types.yml` |
| Chạy tiếp một chiến dịch | `agent/skills/campaign-run/SKILL.md` |
| Giọng viết, điều cấm, tự kiểm | `agent/knowledge/BRAND_VOICE.md` |
| Độ dài / hashtag / vị trí link theo kênh | `agent/knowledge/MULTICHANNEL_MATRIX.md` |
| Chấm chủ đề trước khi sản xuất | `agent/knowledge/SCORING.md` |
| Số liệu xấu, không biết vì sao | `agent/knowledge/DIAGNOSTICS.md` |
| QA một asset trước khi trình duyệt | `agent/checklists/QA_ASSET.md` |
| Prompt viết nội dung | `agent/prompts/content-write.md` |
| Prompt đề xuất chủ đề | `agent/prompts/topic-gen.md` |
| **Cột nào tồn tại, kiểu gì, ai ghi** | `schema/model.yml` |
| **Giá trị nào hợp lệ, luật chuyển trạng thái, luật cổng** | `schema/enums.yml` + `schema/model.yml` khối `stages` |
| Cùng một thứ có mấy tên | `schema/crosswalk.yml` |
| Workbook có sheet nào, ai ghi cột nào | `schema/workbook_spec.yml` |
| Một chiến dịch hoàn chỉnh trông thế nào | `content/KPIM/` (dữ liệu mô phỏng) |
| Từ điển dữ liệu bộ mẫu | `content/KPIM/DATA_DICTIONARY.md` |
| Cấu hình kênh: đường dẫn, mức tự trị, từ cấm | `<content_root>/instance.yml` |

## Luật chống ảo giác

**Thư mục chỉ có `README.md` hoặc `.gitkeep` = kho rỗng.** Không được suy nội dung từ
tên thư mục. Nếu cần thông tin mà file không có, nói "chưa có" — đừng dựng ra.

**Trạng thái hiện tại của repo** (cập nhật 2026-07-21):

| Vùng | Trạng thái |
|---|---|
| `schema/` | ✅ đầy đủ 4 file |
| `scripts/calendar` · `workbook` · `pipeline` · `courseware` | ✅ chạy được |
| `scripts/publish` · `collect` · `model` | ⛔ **chưa có** — đừng gọi, đừng hứa |
| `agent/skills` · `knowledge` · `checklists` · `prompts` · `workflows` · `templates` | ✅ có nội dung |
| `content/KPIM` + `data/KPIM` | ✅ bộ mẫu đầy đủ |
| Thu số liệu từ YouTube/Facebook | ⛔ **chưa nối API** — `07_Metrics_Daily` hiện trống |

## Ưu tiên khi thông tin mâu thuẫn

1. `instance.yml` của kênh đang làm — luật riêng thắng luật chung
2. `schema/*.yml` — hợp đồng dữ liệu
3. `agent/knowledge/*` — tri thức nghiệp vụ
4. `README.md` — mô tả tổng quan, có thể lạc hậu hơn code

Người dùng nói trực tiếp thì đè tất cả.
