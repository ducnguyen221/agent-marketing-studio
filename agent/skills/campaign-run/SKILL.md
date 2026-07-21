---
name: campaign-run
description: >
  Chạy một chiến dịch marketing end-to-end qua workbook Excel — từ brief, lịch nội dung,
  viết nháp, qua ba cổng duyệt của người, tới đăng bài và đo kết quả. Dùng khi người dùng
  nói "chạy chiến dịch", "tiếp tục campaign", "viết nội dung cho campaign X", "tới bước
  tiếp theo", "campaign này đang ở đâu rồi", hoặc đưa một file workbook chiến dịch.
  KHÔNG dùng để tạo campaign mới từ số không — dùng skill campaign-new.
---

# campaign-run

## Nguyên tắc lõi — đọc trước khi làm bất cứ gì

**Cổng duyệt là dữ liệu, không phải trí nhớ của bạn.** Ba cột `approve_topic`,
`approve_content`, `approve_final` trong sheet `03_Calendar` do **người** tick.
Bạn không đọc Excel trực tiếp để tự quyết — bạn hỏi CLI, và CLI chỉ trả về những
asset đã qua cổng. Nếu danh sách rỗng, việc của bạn là **báo cáo và dừng**, không
phải tìm đường vòng.

**Ba cột đó bạn tuyệt đối không ghi vào.** `campaign_excel.py set` sẽ từ chối.

## Bước 0 — Luôn báo cáo hiện trạng TRƯỚC, đừng làm gì vội

```bash
python scripts/pipeline/campaign_excel.py status <workbook.xlsx>
```

Trình bày cho người dùng: mỗi trạng thái bao nhiêu asset, mỗi cổng đã tick bao nhiêu,
stage nào đang có việc. Rồi hỏi họ muốn chạy stage nào — trừ khi họ đã nói rõ.

## Vòng lặp chuẩn cho mọi stage

```bash
python scripts/pipeline/campaign_excel.py list <workbook.xlsx> --stage <stage> --json
```

1. Lấy danh sách asset đủ điều kiện. **Rỗng → dừng, báo ai cần tick cột nào.**
2. Xử lý **từng asset một**, theo đúng phần "Việc của từng stage" bên dưới.
3. Ghi kết quả về workbook bằng CLI (`content`, `set`, `publish-log`).
4. Đặt `status` sang giá trị `to_status` khai trong `schema/model.yml`.
5. Cuối lượt: **báo cáo đã đổi gì ở đâu** — asset nào, sheet nào, cột nào. Không có
   báo cáo này thì người không biết state đã lệch.

Luật cổng nằm ở `schema/model.yml` khối `stages`. Đừng nhớ thuộc lòng, hãy đọc file.

## Việc của từng stage

### `topics` — đề xuất chủ đề
Đọc `01_Brief` (objective, big idea, persona, pillar) và `02_KPI_Target`.
Đọc `agent/prompts/topic-gen.md`. Với mỗi chủ đề đề xuất: `title_draft`, `pillar_primary`,
`format`, `funnel_stage`, `function_role`, `planned_publish_date`.
**Chấm TOS và HRS** theo `agent/knowledge/SCORING.md` — TOS < 2.5 thì loại, đừng đề xuất cho có.
→ `status = drafted`. Rồi **dừng**: người phải tick `approve_topic`.

### `draft` — viết nội dung
Đọc `agent/prompts/content-write.md` + `agent/knowledge/BRAND_VOICE.md` +
`agent/knowledge/MULTICHANNEL_MATRIX.md`.

Với mỗi asset, sinh đúng những mảnh nội dung mà định dạng của nó cần:

| format | mảnh cần có (`content_type`) |
|---|---|
| `long_video` | `title` (2 biến thể A/B) · `hook` · `description` · `chapters` · `thumbnail_brief` · `pinned_comment` |
| `short` | `hook` · `script` · `caption` |
| `fb_post` · `fb_reel` | `caption` (bản đầy đủ, không teaser cụt) |
| `yt_community` | `caption` |

Ghi từng mảnh:
```bash
python scripts/pipeline/campaign_excel.py content <wb> --asset <id> \
    --type caption --variant final --body-file draft.md --hashtags "#a #b" --select
```
Nội dung dài hơn ~2.000 ký tự: lưu thành `.md` trong `<content_root>/campaigns/<ID>/drafts/`
rồi truyền `--draft-path`, đừng nhét cả bài vào ô Excel.

**Trước khi đặt `status = need_review`, tự chạy `agent/checklists/QA_ASSET.md`.**
Mục nào trượt thì sửa, không đẩy sang người với lỗi bạn tự thấy được.
→ `status = need_review`. **Dừng**: người tick `approve_content`.

### `media` — brief hình ảnh và âm thanh
Sinh `media_prompt` và `thumbnail_brief`. **Không sinh ảnh thật trong stage này** trừ khi
được yêu cầu rõ. Chữ tiếng Việt nên overlay lúc đóng gói, đừng để model viết trong ảnh —
model hay sai dấu.
→ `status = approved`. **Dừng**: người tick `approve_final`.

### `publish` — đăng
```bash
python scripts/pipeline/campaign_excel.py publish-log <wb> --asset <id> \
    --platform youtube --mode dry_run --autonomy <từ instance.yml> --status skipped
```
CLI tự chặn nếu: chưa tick `approve_final`, còn `verification_open > 0`, hoặc
`mode=live` mà `autonomy != full`. **Đừng cố lách những chặn này** — chúng là lý do
tồn tại của repo.

Mặc định luôn là `--mode dry_run`. Chỉ chuyển `live` khi `instance.yml` ghi
`autonomy: full` **và** người dùng nói rõ trong lượt này.

### `measure` — đo
Nạp số liệu vào `07_Metrics_Daily`, tính `08_Metrics_Summary`.
Viết insight vào `10_Insights` theo `agent/knowledge/DIAGNOSTICS.md`.
**Mỗi insight bắt buộc có `evidence_metric` + `evidence_value`.** Không có số thì không
được ghi dòng — thà để trống còn hơn bịa.

`vs_median_*` chỉ tính khi `baseline_n ≥ 10`. Chưa đủ mẫu thì để trống và nói
"chưa đủ mẫu", tuyệt đối không thay bằng con số ước lượng.

## Điều không bao giờ được làm

- Tự tick hộ cổng duyệt, hoặc gọi `approve` thay người mà họ chưa bảo.
- Đăng thật khi `autonomy` chưa phải `full`.
- Bịa số liệu, bịa nguồn, bịa tên khách hàng, bịa kết quả.
- Nhắc tên công cụ/hạ tầng sản xuất nội bộ trong bất kỳ nội dung công khai nào.
- Sửa nội dung public-facing mà bạn không chắc nguyên bản — liệt kê kèm mức tự tin
  và để người chọn (xem `agent/checklists/QA_ASSET.md` mục cuối).
