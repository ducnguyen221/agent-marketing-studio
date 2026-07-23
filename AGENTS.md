---
scope: marketing-agent engine
updated: 2026-07-23
---

# marketing-agent — Cách AI Agent thực thi công việc marketing

> Engine chạy một chiến dịch nội dung từ đầu đến cuối: **mỗi campaign = 1 folder + 1 file
> `.md` (hồ sơ) + 1 file `.xlsx` (5 sheet)**, Excel làm chủ trạng thái, người duyệt từng bước.
>
> File này viết chung cho **mọi người cài đặt** — không gắn với một thương hiệu nào. Tên
> riêng, pillar, kênh, giọng văn cụ thể do bạn khai trong instance của mình. Muốn xem một
> chiến dịch thật trông thế nào → mở bộ mẫu `content/KPIM/02_campaigns/01_Tobi_Posts/`.

---

## Mô hình dữ liệu (đọc trước)

- **Mỗi campaign = 1 folder + 1 Excel riêng.** Không có Excel chủ chung.
  - Folder: `content/<instance>/02_campaigns/<NN_Ten>/`
  - Hồ sơ: `<NN_Ten>.md` — từ `agent/templates/CAMPAIGN_TEMPLATE.md`, HỒ SƠ nghiệp vụ + lịch sử
  - Excel: `<NN_Ten>.xlsx` — 5 sheet: **Campaign / Post / Result / Engagement / Assets**
- **Asset từng bài:** `<folder campaign>/assets/<post_id>_<slug>/` — `content.md`, `blog.md`,
  `fb_post.txt`, `youtube_desc.txt`, `fb_desc.txt`, `thumbnail.png`, `audio.mp3`, `video.mp4`,
  `preview.html` (tự chứa, ảnh nhúng base64), `meta.json`. Tất cả markdown/txt/html, KHÔNG docx.
- **Dữ liệu nền tảng** (Facebook Graph / YouTube) là thứ DUY NHẤT đến từ ngoài file — kéo về
  sheet **Engagement** qua `fb_post_id`, bằng API hoặc từ file export.

`<instance>` = tên kênh/thương hiệu của bạn (do `install.ps1` hỏi). Bộ mẫu đi kèm repo tên
`KPIM` — dùng để tham chiếu, không phải chỗ bạn làm việc thật.

---

## Quy trình — từ tạo campaign đến báo cáo

### Bước 1 — Làm rõ đề bài (INTERACTIVE, bắt buộc)

Người dùng mô tả campaign. **Agent KHÔNG tạo gì vội** — hỏi 1 lượt các câu còn thiếu:

1. **Tên & mã** — tên dễ đọc, `campaign_code = NN_Ten` (= tên folder).
2. **Pillar** — trụ nội dung chính của chiến dịch (lấy từ bộ pillar của instance, khai ở
   `CAMPAIGN_TEMPLATE.md` Mục 6).
3. **Mục tiêu** — business goal (awareness/demand/conversion/retention) + KPI mong muốn.
4. **Đối tượng** — persona chính + pain.
5. **Key message** — hook + thông điệp lõi + CTA.
6. **Kênh** — những kênh nào sẽ đăng (blog / YouTube / Facebook Page / …).
7. **Lịch** — schedule_start/end, cadence, số bài dự kiến.
8. **prompt_requirements** — angle muốn, phải-có / phải-tránh, nguồn tham khảo.

Gì người dùng đã nói rõ thì không hỏi lại. Đọc `CAMPAIGN_TEMPLATE.md` Mục 6 (Content Pillars)
để gợi ý và phát hiện chủ đề out-of-scope ("What we DON'T cover"). Chốt khi người dùng OK.

### Bước 2 — Dựng hồ sơ + folder

1. Tạo folder `content/<instance>/02_campaigns/<NN_Ten>/`.
2. Copy `CAMPAIGN_TEMPLATE.md` → `<NN_Ten>.md`, điền đủ mọi `{{...}}` từ Bước 1
   (metadata + 7 mục đầu). Mục 8–15 để rỗng, append dần sau.

### Bước 3 — Tạo Excel + đổ Sheet Campaign

```
python scripts/workbook/build_workbook.py new-campaign \
    --out content/<instance>/02_campaigns/<NN_Ten>/<NN_Ten>.xlsx \
    --meta <campaign_meta.json>
```
`campaign_meta.json` map đúng 20 field Sheet Campaign. Rồi cập nhật sổ chiến dịch:
`python scripts/pipeline/campaign_registry.py --instance content/<instance>`.

### Bước 4 — Triển khai bài (pipeline 5 stage, Excel làm chủ)

```
topics  → sinh chủ đề vào Sheet Post (status=proposed)
          → NGƯỜI tick approve_topic
draft   → bài approve_topic → content.md → blog.md + fb_post + youtube_desc + fb_desc
          → NGƯỜI tick approve_content
media   → bài approve_content → thumbnail + audio (podcast) + video
          → short là OPTIONAL: chỉ dựng khi make_short tick, và LUÔN hỏi xác nhận
preview → bài media_ready → preview.html (tự chứa: ảnh/audio nhúng base64; video chỉ hiện link YouTube nếu đã upload)
          → NGƯỜI tick approve_final
publish → bài approve_final → đăng YouTube + FB hẹn lịch → Sheet Result
```

Mỗi stage hỏi CLI để lấy đúng việc, không tự đọc Excel để quyết:
```
python scripts/pipeline/campaign_excel.py list <wb.xlsx> --stage draft --json
```
Danh sách rỗng → dừng, báo ai cần tick cột nào. Không có đường vòng.

### Bước 5 — Đo & báo cáo

- Kéo số liệu FB/YouTube về Sheet Engagement (qua `fb_post_id`) — bằng API hoặc file export.
- Tổng hợp Post + Result + Engagement → append `## Báo cáo <ngày>` vào Mục 14 của hồ sơ `.md`.
  Không xoá mục cũ.

---

## Cổng duyệt — 2 cách, chọn 1

- **Tick Excel** (Sheet Post): `approve_topic` / `approve_content` / `approve_final` = `x`/`X`/`TRUE`/`✓`.
- **Lệnh**: `campaign_excel.py approve <wb> --post-id <ID> --gate approve_topic --by "<tên bạn>"`.

Gating: `draft = approve_topic & proposed` · `media = approve_content & drafted` ·
`preview = media_ready` · `publish = approve_final & {preview_ready, media_ready}`.

**KHÔNG tự tick approve thay người.** `campaign_excel.py set` từ chối ghi vào 3 cột này.

---

## Nên làm / Không nên làm

Đây là mặc định an toàn cho mọi instance. Instance có thể siết thêm trong hồ sơ campaign.

### Nên làm
- Đối chiếu mọi nội dung công khai với brand voice của instance (`agent/output-styles/`).
- Kiểm SEO cho bài blog: meta description 150–160 ký tự, primary keyword ở title + H2 đầu.
- Đồng bộ lead thu được vào nơi quản lý lead của bạn.

### Không nên làm
- Không tự ý công bố/chỉnh giá dịch vụ, sản phẩm khi chưa được duyệt chính thức.
- Không dùng hình ảnh thương hiệu đối tác/khách hàng khi chưa có đồng ý bằng văn bản.
- Tránh tiêu đề giật gân, phóng đại hiệu quả (overpromise).

### Guardrail
- Mọi bài đại diện thương hiệu phải qua duyệt trước khi publish.
- Lead từ form chuyển thẳng vào nơi lưu trữ an toàn, không để lộ công khai.
- Trước khi thiết lập campaign mới, hỏi rõ ngân sách + mục tiêu leads. Nếu chưa rõ, đề xuất
  2 kịch bản (tiết kiệm & tăng trưởng mạnh) kèm dự phóng để người quyết.

---

## Style — đọc trước khi viết

Instance khai giọng văn của mình trong `agent/output-styles/`. Bộ mẫu đi kèm repo dùng
giọng thương hiệu của KPIM — **thay bằng giọng của bạn** khi cài instance riêng.

| Kênh | File style (thay nội dung theo thương hiệu của bạn) |
|---|---|
| Blog | `agent/output-styles/compa-class-blog.md` |
| Facebook (post dài + caption Reel) | `agent/output-styles/tobi-post.md` |
| Format đa kênh (YouTube/FB/X) | `agent/output-styles/multichannel-style.md` |

Quy tắc vàng (chung mọi thương hiệu): cùng 1 nội dung gốc, **FORMAT LẠI** theo từng kênh —
KHÔNG copy y nguyên blog sang FB/YouTube/X.

---

## STOP

- Style lệch với file output-style của instance (vd FB còn markdown literal) → trả writer, không publish.
- Topic trùng >70% bài đã có → refresh thay vì viết mới.
- Thiếu token FB/YouTube → dừng ở publish, báo người dùng setup (`agent/knowledge/PLATFORM_SETUP.md`).

---

## Ví dụ tham chiếu (demo trong repo)

Bộ mẫu `content/KPIM/02_campaigns/01_Tobi_Posts/` minh hoạ trọn quy trình bằng dữ liệu của
một thương hiệu cụ thể (KPIM Academy / COMPA Class), pillar mẫu Power BI / Fabric / AI Agent
/ Career, kênh mẫu blog `ducnguyen.vn` + YouTube + Facebook. Những tên riêng đó **chỉ là ví
dụ trong demo** — khi bạn cài instance của mình, chúng được thay bằng thương hiệu, pillar và
kênh của bạn.
