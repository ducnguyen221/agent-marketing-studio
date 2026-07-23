# Quy trình tổng — agent nạp gì, lúc nào

Điểm vào duy nhất. Mô hình chuẩn KPIM: **mỗi campaign = 1 folder + 1 file `.md` (hồ sơ) +
1 file `.xlsx` (5 sheet)**. Excel làm chủ trạng thái, người duyệt từng bước.

Tổng quan cách agent làm việc: đọc [`AGENTS.md`](../../AGENTS.md) ở gốc repo.

---

## Vòng đời — 5 bước, 3 cổng duyệt của người

```
①new  →  ②topics ─[approve_topic]→ ③draft ─[approve_content]→ ④media → ⑤preview ─[approve_final]→ ⑥publish → ⑦report
```

Ba cổng `approve_topic` / `approve_content` / `approve_final` là **cột trong sheet Post**.
Người không tick thì stage sau không có việc. CLI chỉ trả bài đã qua cổng.

---


## Ai làm khâu nào (phân vai chuẩn)

Điều phối: **marketing-director** — chiến lược tổng, giao vai, giám sát, quản mức tự trị.

| Khâu | Vai chính (agent) | Hỗ trợ |
|---|---|---|
| ① new — thiết kế chiến dịch | `campaign-strategist` | marketing-director |
| ② topics — lịch + chủ đề | `content-strategist` | seo-specialist (từ khoá) |
| ③ draft — viết nội dung | `content-producer` | seo-specialist, hook-writer/thread-writer (skill) |
| ④ media — hình + tiếng | `creative-producer` | — |
| trước cổng — biên tập | `content-editor` (hay/rõ/thuyết phục, tư vấn) | — |
| trước cổng — tuân thủ | `qa-reviewer` (đúng/an toàn, chặn phát hành) | — |
| ⑥ publish — đăng đa kênh | `distribution-manager` | — |
| ⑦ report — đo & chẩn đoán | `growth-analyst` | — |

Cổng duyệt (approve_topic/content/final) LUÔN là **người**, không vai nào tick hộ.

## Nạp gì ở mỗi bước

| Bước | Việc | Đọc | Template | Script |
|---|---|---|---|---|
| **① new** | Dựng campaign | `AGENTS.md` §Bước 1–3 | `CAMPAIGN_TEMPLATE.md` | `build_workbook.py new-campaign` |
| **② topics** | Đề xuất chủ đề vào Sheet Post | `CAMPAIGN_TEMPLATE.md` (Mục 6 pillar), hồ sơ campaign | — | `campaign_excel.py upsert` |
| 🔒 | **NGƯỜI tick approve_topic** | | | `campaign_excel.py approve` |
| **③ draft** | Viết `content.md` → tách đa kênh | `output-styles/*` | `CONTENT_TEMPLATE.md` | `campaign_excel.py set` |
| 🔒 | **NGƯỜI tick approve_content** | | | |
| **④ media** | Thumbnail · audio · video | `output-styles/tobi-post.md` | — | `campaign_excel.py set` |
| 🔒 | **NGƯỜI tick approve_final** | | | |
| **⑤ preview** | Dựng `preview.html` tự chứa (ảnh/audio nhúng base64; video = link YouTube nếu đã upload) — chuyển folder không vỡ | — | — | `build_preview.py` |
| **⑥ publish** | Đăng → Sheet Result | `output-styles/multichannel-style.md` | — | `campaign_excel.py result` |
| **⑦ report** | Đo → Engagement, báo cáo vào hồ sơ .md Mục 14 | — | — | `campaign_excel.py upsert-engagement` |

Style theo kênh: blog `output-styles/compa-class-blog.md` · Facebook `output-styles/tobi-post.md`
· format đa kênh `output-styles/multichannel-style.md`.

---

## Vòng lặp chuẩn mỗi stage

```
python scripts/pipeline/campaign_excel.py status <wb.xlsx>          # xem hiện trạng TRƯỚC
python scripts/pipeline/campaign_excel.py list   <wb.xlsx> --stage draft --json
# rỗng → DỪNG, báo ai cần tick cột nào. Không rỗng → xử lý TỪNG bài.
# ghi kết quả về đúng sheet, rồi đặt status sang to_status khai ở workbook_spec.yml
```

Luật cổng nằm ở `schema/workbook_spec.yml` khối `stages`. Đọc file, đừng nhớ thuộc lòng.

---

## Bảy điều tuyệt đối

1. Không tick hộ cổng duyệt (`campaign_excel.py set` từ chối ghi 3 cột approve_*).
2. Không đăng thật khi chưa đủ token + chưa `approve_final`.
3. Không bịa số, bịa nguồn, bịa kết quả.
4. Không tự sửa nội dung public-facing — liệt kê kèm độ tự tin, tự tin thấp thì nêu 2 phương án.
5. Không lộ tên công cụ/hạ tầng sản xuất nội bộ trong nội dung công khai.
6. Cùng 1 nội dung gốc phải FORMAT LẠI theo từng kênh, không copy y nguyên.
7. Cuối mỗi lượt báo đã đổi gì ở sheet nào.

---

## Trạng thái repo

| Vùng | |
|---|---|
| `schema/workbook_spec.yml` (5 sheet) | ✅ |
| `scripts/{workbook,pipeline,lib}` | ✅ chạy được |
| Kéo số liệu nền tảng về Sheet Engagement (API) | ⛔ chưa có script — quy trình ở `agent/knowledge/PLATFORM_SETUP.md` |
| Bộ mẫu `content/KPIM/02_campaigns/01_Tobi_Posts` | ✅ campaign hoàn chỉnh (hồ sơ .md + workbook 5 sheet + asset) |
