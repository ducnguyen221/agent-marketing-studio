---
name: campaign-pipeline
description: >
  Vận hành pipeline một chiến dịch content end-to-end: 5 stage topics → draft → media →
  preview → publish, Excel làm chủ, 3 cổng duyệt của người. Dùng khi người dùng nói "chạy
  chiến dịch", "tiếp tục campaign", "tới bước tiếp theo", "campaign này đang ở đâu", hoặc
  đưa một workbook chiến dịch. Mô tả hợp đồng từng stage: vào gì / ra gì / điều kiện chuyển.
---

# Campaign Pipeline — hợp đồng 5 stage

> Chưng cất từ `tobi-content-pipeline` (KPIM 30_MARKETING), thay stage `atlas` bằng `preview`.
> Mô hình dữ liệu + quy trình đầy đủ: [`../../../AGENTS.md`](../../../AGENTS.md).

## Nguyên tắc lõi

- **Excel làm chủ trạng thái.** Chỉ xử lý bài đã qua cổng của stage trước. Hỏi CLI, không
  tự đọc Excel để quyết: `campaign_excel.py list <wb> --stage <stage> --json`.
- **Cổng duyệt của người.** `approve_topic` / `approve_content` / `approve_final` là cột
  trong Sheet Post. Agent KHÔNG tự tick — `campaign_excel.py set` từ chối ghi 3 cột này.
- **Mỗi script in kết quả rõ, dừng khi lỗi.** Cuối lượt báo đã đổi gì ở sheet nào.

## Luôn bắt đầu bằng hiện trạng

```
python scripts/pipeline/campaign_excel.py status <wb.xlsx>
```
Báo cáo status + cổng + việc theo stage. Rồi hỏi người muốn chạy stage nào (trừ khi họ đã nói rõ).

## Hợp đồng từng stage

### STAGE 1 — `topics` (research + pillar)
- **Vào:** Sheet Campaign (pillar, prompt_requirements, num_posts) + `CAMPAIGN_TEMPLATE.md`
  Mục 6 (Content Pillars) + persona + WebSearch + các bài đã đăng (để nối mạch, tránh lặp).
- **Làm:** đề xuất N chủ đề fit pillar, angle phá định kiến, tránh "What we DON'T cover".
  Chấm theo pillar gate; ngoài pillar → loại. Ghi vào Sheet Post (`upsert`), status=`proposed`.
- **Ra → dừng:** người tick `approve_topic`.

### STAGE 2 — `draft` (viết nội dung đa kênh)
- **Vào:** bài `approve_topic` + `CONTENT_TEMPLATE.md` + `output-styles/*` + `COPY_FRAMEWORKS.md`.
- **Làm:** điền `content.md` (8 mục), tách thành `blog.md` + `fb_post.txt` + `youtube_desc.txt`
  + `fb_desc.txt`. Chạy checklist `checklists/QA_ASSET.md` trước khi đẩy.
- **Ra → dừng:** status=`drafted`, người tick `approve_content`.

### STAGE 3 — `media` (hình + tiếng)
- **Vào:** bài `approve_content`.
- **Làm:** thumbnail + audio (podcast) + video. Short là OPTIONAL: chỉ dựng khi `make_short`
  tick, và LUÔN hỏi xác nhận trước khi dựng.
- **Ra:** status=`media_ready`.

### STAGE 4 — `preview` (file HTML tự chứa)
- **Vào:** bài `media_ready`.
- **Làm:** `python scripts/pipeline/build_preview.py --campaign-dir <dir> --post-id <ID> --workbook <wb>`
  → `preview.html` nhúng ảnh/audio base64 (chuyển folder không vỡ); video chỉ hiện link
  YouTube nếu đã upload. Ghi ngược `preview_html` + đăng ký Sheet Assets.
- **Ra → dừng:** status=`preview_ready`, người tick `approve_final`.

### STAGE 5 — `publish`
- **Vào:** bài `approve_final`.
- **Làm:** đăng YouTube + FB hẹn lịch → ghi Sheet Result (`result`): blog_url, youtube_url,
  fb_post_id, fb_permalink. Thiếu token → dừng, báo người setup (`knowledge/PLATFORM_SETUP.md`).
- **Ra:** status=`published`.

### Sau publish — đo
- Kéo số liệu FB/YouTube về Sheet Engagement (`upsert-engagement`) qua `fb_post_id`.
- Tổng hợp Post + Result + Engagement → append `## Báo cáo <ngày>` vào hồ sơ `.md` Mục 14.

## Gating (nhắc lại)
`draft = approve_topic & proposed` · `media = approve_content & drafted` ·
`preview = media_ready` · `publish = approve_final & {preview_ready, media_ready}`.

## Điều không bao giờ làm
Tự tick cổng · đăng thật khi chưa đủ token / chưa approve_final · bịa số/nguồn/kết quả ·
lộ tên tool nội bộ · copy y nguyên 1 nội dung sang mọi kênh (phải format lại theo kênh).
