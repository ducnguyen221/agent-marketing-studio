# DATA DICTIONARY — bộ dữ liệu KPIM Bank (MKA-101)

> **Dữ liệu mô phỏng.** KPIM Bank là ngân hàng giả định. Không có PII thật, không có
> credential, không gọi API nào. Sinh bằng `scripts/courseware/generate_kpim_bank.py`
> (seed `20260721` — chạy lại ra kết quả y hệt).

Tài liệu này dành cho **giảng viên**: mọi "nhiễu" trong dữ liệu đều là cố ý và được liệt
kê đầy đủ ở mục [Nhiễu cố ý](#nhiễu-cố-ý-đáp-án-cho-giảng-viên).

---

## 0. Ba tên của cùng một khoá

Cùng một mã bài (`P-Q1-01`) mang **ba tên** ở ba nơi — đây chính là bài học crosswalk:

| Nơi | Tên cột | Ghi chú |
|---|---|---|
| `templates/schema/model.yml` (canonical) | `asset_id` | khoá chính của `dim_asset` |
| `KPIM_Bank_Marketing_Plan.xlsx` sheet Post | `post_code` | nguồn gốc |
| Tài liệu MKA-101 & các bảng lab (`execution_log`, `content_review`, `cta_lead_bridge`) | `post_id` | tên học viên gặp trong đề bài |

**Giá trị giống hệt nhau** ⇒ join trực tiếp được, không cần bảng trung gian.
`calendar.csv` mang cả `asset_id` lẫn `post_code` để thấy rõ điều đó.

Khoá nối sang số liệu Facebook: `platform_native_id_fb` ↔ cột `ID bài viết` của cả hai
file export (khớp 60/60).

---

## 1. `content/KPIM/instance.yml`
Khai báo instance: tên, mức tự trị (`suggest` — cấm publish), 3 gốc thư mục, kênh,
và `data_kind: simulated` (gate an toàn để script publish từ chối chạy trên bộ mẫu).

## 2. `content/KPIM/01_brand/pillars.csv`
**Grain:** 1 dòng = 1 content pillar của KPIM Bank. **Khoá:** `pillar_code`. **6 dòng.**

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `pillar_code` | string | Mã pillar — **trùng nguyên văn** giá trị `content_pillar` của sheet Post ⇒ join thẳng, không cần map |
| `pillar_name` | string | Tên tiếng Việt hiển thị trên dashboard |
| `goal` | string | Pillar này tồn tại để làm gì |
| `target_share` | decimal 0–1 | Tỷ trọng bài kỳ vọng; tổng = 1.00 |
| `crosswalk_personal` | string | Ánh xạ sang hệ pillar A..F của kênh cá nhân (51.01) |
| `crosswalk_course` | string | Ánh xạ sang `content_pillar` của KPIM Bank (ở đây = chính nó) |
| `default_funnel_stage` | enum | Tầng phễu mặc định, dùng khi calendar không khai riêng |
| `default_cta_type` | enum `cta_type` | CTA mặc định của pillar |

## 3. `content/KPIM/02_campaigns/<campaign_id>/brief.yml`
**Grain:** 1 file = 1 chiến dịch (4 file). Lấy 16 cột từ sheet `Campaign` + **sinh bù 4 nhóm
không có trong nguồn**: `persona_primary/secondary`, `key_message`, `tone`, `compliance_notes`.
`compliance_notes` cố tình viết theo giọng pháp chế ngân hàng để bài S03 (kiểm nội dung AI)
có tiêu chí chấm thật.

## 4. `content/KPIM/02_campaigns/<campaign_id>/calendar.csv` ★
**Grain:** 1 dòng = 1 asset (chưa unpivot theo kênh). **Khoá:** `asset_id`.
**Số dòng:** 25 · 26 · 26 · 25
(tổng 102 dòng vật lý = 100 dòng logic + 2 dòng lặp cố ý).

Mỗi quý = **15 bài đã đăng** (nguyên văn sheet Post) **+ 10 bài kế hoạch chưa đăng**.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `asset_id` | string | Khoá chính. = `post_code` = `post_id` |
| `post_code` | string | Giá trị gốc từ sheet Post (giữ để truy vết) |
| `campaign_id` | string | FK → `brief.yml` / sheet Campaign |
| `quarter` | string | Q1..Q4 |
| `planned_publish_date` | date ISO | `planned_date` của sheet Post |
| `schedule_date` | date | Ngày hẹn đăng của workflow (**có 3 dòng sai định dạng — cố ý**) |
| `pillar_code` | string | FK → `pillars.csv` |
| `format_source` | string | Giá trị gốc tiếng Việt: Ảnh · Video · Thước phim · Liên kết |
| `format` | enum `format` | Canonical sau `value_map` của crosswalk: fb_post · long_video · fb_reel |
| `funnel_stage` | enum | Suy ra từ pillar |
| `platform_primary` | enum `platform` | Kênh chính của asset |
| `on_facebook` / `on_youtube` | Y/N | **Giữ nguyên dạng 2 cột cờ** của nguồn — unpivot về grain `platform` là bài tập S04 |
| `title` | string | Tiêu đề bài |
| `caption` | string | **Sinh bù** — caption tiếng Việt theo pillar + CTA + hashtag |
| `media_link` | string | **Sinh bù** — đường dẫn giả `media/Q1/P-Q1-01.jpg` (**5 dòng để trống — cố ý**) |
| `cta_label` | string | Nhãn CTA của kế hoạch (cột `cta` của nguồn) — **khác** `cta_clicks` (số đo) |
| `cta_type` | enum `cta_type` | Canonical |
| `approval_status` | enum `approval_status_course` | Draft · Need Review · Approved · Need Revision · Rejected |
| `status` | enum `status` | Canonical, map từ `approval_status` (+ `published` khi đã đăng) |
| `is_published` | Y/N | **Cột trọng tài** — xem mục dưới |
| `platform_native_id_fb` | string | `fb_post_id` — khoá nối sang 2 file Facebook |
| `platform_native_id_yt` | string | `yt_video_id` — khoá nối sang `youtube_export.csv` |
| `owner` | string | Chủ sở hữu |

### Cách xử lý mâu thuẫn "60/60 đều Đã đăng" ⚠️ ĐỌC KỸ
Nguồn có 60/60 bài `status = "Đã đăng"`, nên nút **IF Approved** của n8n không có gì để lọc.
Giải pháp đã chọn (nhất quán, không mâu thuẫn với dữ liệu Facebook có thật):

1. **Thêm cột `is_published`.** 60 bài có `fb_post_id` thật → `is_published = Y`,
   `approval_status = Approved`, `status = published`. Không đụng vào sự thật đã đăng.
2. **Thêm 40 bài KẾ HOẠCH** (10 bài/quý, `asset_id` = `P-Qn-16` … `P-Qn-25`),
   `is_published = N`, **không có** `fb_post_id`/`yt_video_id`. Toàn bộ các trạng thái
   duyệt khác nằm ở đây.
3. Phân bố trên **100 dòng logic**: 70 Approved (70%) ·
   12 Need Review · 10 Draft ·
   5 Need Revision · 3 Rejected.
   Trong đó **10 bài Approved nhưng chưa đăng** — đây chính là tập
   mà nhánh "IF Approved" của n8n phải chạy qua.

**Quy tắc bất biến:** `is_published = Y` ⟹ `approval_status = Approved` (không có ngoại lệ).
Ngược lại thì không: Approved mà chưa đăng là hợp lệ (đang chờ tới lịch).

## 5. `content/KPIM/03_approvals/content_review.csv` ★
**Grain:** 1 dòng = 1 (`post_id` × `content_type`). **300 dòng** = 100 bài × 3 loại nội dung.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `post_id` | string | FK → `calendar.asset_id` |
| `content_type` | enum | `website` · `caption` · `media_prompt` |
| `prompt_used` | string | Prompt đã dùng để sinh nháp (có persona + tone + key message của brief) |
| `ai_draft_excerpt` | string | Trích đoạn nháp AI |
| `review_status` | enum | Need Review · Approved · Need Revision · Rejected — **luôn khớp `calendar.approval_status` của cùng post** |
| `reviewer` | string | Người duyệt; rỗng khi còn `Draft` |
| `review_timestamp` | datetime | Rỗng khi còn `Draft` |
| `revision_note` | string | Lý do trả về — viết theo ngôn ngữ pháp chế ngân hàng |
| `checklist_claim_ok` | bool | Tuyên bố/con số có kèm điều kiện? |
| `checklist_pii_ok` | bool | Không lộ thông tin định danh? |
| `checklist_tone_ok` | bool | Đúng tone brief? |
| `checklist_cta_ok` | bool | CTA khớp landing page? |

Checklist `FALSE` **luôn** đi kèm `review_status` ∈ (Need Revision, Rejected) — dùng làm
đáp án cho bài "vì sao nội dung này bị chặn".

## 6. `content/KPIM/04_published/execution_log.csv` ★
**Grain:** 1 dòng = 1 lần workflow n8n xử lý (`post_id` × `channel`). **141 dòng.**

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `run_id` | string | `RUN-2026-0001`… |
| `post_id` | string | FK → calendar |
| `channel` | enum | facebook · youtube |
| `processed_timestamp` | datetime | Thời điểm node xử lý |
| `status` | enum | `pending` · `drafted` · `skipped` · `error` · `need_review` |
| `error_message` | string | Rỗng khi thành công |
| `draft_link` | string | Chỉ có khi `drafted` |

**Ca lỗi cài sẵn (để học viên phải xử lý):**
| Ca | Điều kiện sinh ra | status | Số dòng |
|---|---|---|---|
| Thiếu media | `media_link` rỗng | `skipped` | 7 |
| Trùng post_id | `asset_id` đã xuất hiện ở run trước cùng batch | `error` | 4 |
| Chưa duyệt | `approval_status` ≠ Approved | `need_review` | 30 |
| Lỗi hạ tầng | 429 / timeout / caption quá dài | `error` | 3 |
| Chưa tới lượt | — | `pending` | 7 |

## 7. `data/KPIM/raw/youtube_export.csv` ★
**Grain:** 1 dòng = 1 video (trọn đời). **Khoá:** `video_id`. **29 dòng** — đúng 29 bài có `yt_video_id`.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `video_id` | string | = `yt_video_id` của sheet Post |
| `post_id` | string | FK → calendar (tiện lợi, YouTube Studio thật không có cột này) |
| `campaign_id` | string | FK |
| `publish_date` | date ISO | |
| `title` | string | |
| `views` | int | **Neo theo reach Facebook của chính bài đó** (18–46%) ⇒ hai kênh so được với nhau |
| `impressions` | int | = views / ctr |
| `ctr` | decimal 0–1 | 3,5–9,2% |
| `avg_view_duration_sec` | decimal | |
| `avg_percentage_viewed` | decimal 0–100 | |
| `watch_time_min` | decimal | = views × AVD / 60 |
| `likes` / `comments` / `shares` | int | |
| `subscribers_gained` | int | 4.0–9.0 sub/1000 view |

## 8. `data/KPIM/raw/leads/lead_*.csv` ★ — 7 FILE, 7 SCHEMA LỆCH NHAU
**Tổng 5687 lead.** Đây là **bài luyện chuẩn hoá & append đa nguồn của buổi S05**:
7 file cố ý **không** cùng tên cột, **không** cùng định dạng ngày, **không** cùng bộ cột.

| File | Dòng | Cột khoá | Cột SĐT | Định dạng ngày | Cột lệch đáng chú ý |
|---|---|---|---|---|---|
| `lead_app.csv` | 949 | `lead_id` · `ma_chien_dich` · `ma_bai_viet`(=fb_post_id) | `sdt` | **epoch mili giây** | thừa `app_version`; `trang_thai` tiếng **Anh** |
| `lead_hotline.csv` | 1056 | `LeadID` · `Campaign` · `PostCode`(=post_code) | `Phone` (+84 …) | `dd-MM-yyyy HH:mm` | PascalCase; thừa `AgentName`, `CallDurationSec` |
| `lead_form.csv` | 739 | `lead_id` · `campaign_id` · `fb_post_id` | `so_dien_thoai` | `yyyy-MM-dd` (**không có giờ**) | thừa `utm_source`, `utm_campaign` |
| `lead_social_inbox.csv` | 340 | `id` · `campaign` · `post_id` | `phone` | `yyyy-MM-dd HH:mm:ss` | **THIẾU hẳn cột `branch`**; thừa `channel_page` |
| `lead_website.csv` | 698 | `lead_id` · `campaign_id` · `post_id` | `phone_number` | **epoch giây** | thừa `landing_page`, `utm_medium` |
| `lead_branch.csv` | 1588 | `MaLead` · `MaChienDich` | `SoDienThoai` | `dd/MM/yyyy` | `MaBaiViet` **luôn rỗng** (khách tới quầy); `PhanLoai` là nhãn **tiếng Việt** (Nóng/Ấm/Cần nuôi/Ưu tiên thấp) |
| `lead_qr_event.csv` | 317 | `lead_id` · `campaign_id` · `post_id` | `sdt` | **ISO 8601 có `Z`** (UTC) | thừa `event_name`, `qr_code_id` |

**Trường tối thiểu quy về được** (sau chuẩn hoá, đúng `fact_lead` của model.yml):
`lead_id` · `source` · `created_at` · `campaign_id` · `post_id` · `product_interest` ·
`region` · `branch` · `need_type` · `lead_status` · `lead_segment`.

- `source` **không có sẵn trong file** — suy từ tên file (đúng `lead_source` enum: app · hotline ·
  form · social_inbox · website · branch · qr_event). Tiền tố `lead_id` cũng mã hoá nguồn
  (`APP-` · `HL-` · `FRM-` · `SIB-` · `WEB-` · `BRC-` · `QR-`).
- **Nối về bài viết theo 2 đường khác nhau**: `lead_app` và `lead_form` dùng `fb_post_id`
  (khớp `calendar.platform_native_id_fb`); các file còn lại dùng `post_id`/`PostCode`
  (khớp `calendar.asset_id`). Cố ý — để học viên gặp cả hai kiểu khoá.
- **KHÔNG PII:** SĐT là chuỗi sinh máy `09xxxxxxxx` (định dạng hiển thị khác nhau theo nguồn),
  tên dạng `Khách hàng 0421`.
- **KHÔNG có cột `is_duplicate_of` trong file thô** — phát hiện trùng là việc của học viên.

## 9. `data/KPIM/raw/Facebook Post Summary.csv` · `Facebook Post Daily.csv`
**Copy nguyên si từ nguồn — KHÔNG dọn cột rỗng.** Summary giữ đủ 95 cột (56 cột rỗng hoàn
toàn) vì dọn cột rỗng là bài lab S04. Bẫy đã biết: cột `Ngày` của Summary là hằng số
`"Trọn đời"`, chỉ Daily mới có ngày thật; `Thời gian đăng` theo định dạng **MM/DD/YYYY**.

## 10. `data/KPIM/star/kpi_target.csv` ★
**Grain:** `campaign_id` × `platform` × `pillar_code` × `metric_name` × `period` (tháng).
**135 dòng.** Đúng schema `dim_kpi_target` của model.yml.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `campaign_id` | string | FK |
| `platform` | enum | facebook · youtube |
| `pillar_code` | string | FK |
| `format` | enum | để trống ở bộ này (target không tách theo định dạng) |
| `metric_name` | string | `reach` · `leads` |
| `period` | string | `YYYY-MM` |
| `target_value` | decimal | **Tổng theo campaign khớp đúng `target_reach` / `target_leads` của sheet Campaign** (chia bằng largest-remainder nên không lệch do làm tròn) |
| `unit` | string | người · lead |
| `baseline_median` | decimal | Median của các bài **cùng platform + cùng pillar ở các quý TRƯỚC** |
| `baseline_source` | string | `fb_post_summary_median` · `youtube_export_median`; **rỗng = chưa đủ mẫu, KHÔNG điền số đoán** |
| `baseline_n` | int | Số mẫu. **Q1 luôn = 0** (không có lịch sử). `< 10` ⇒ dashboard phải hiện "chưa đủ mẫu" |

## 11. `data/KPIM/star/cost_by_post.csv`
**Grain:** 1 dòng = 1 asset. **100 dòng.** Tồn tại vì **không nguồn nào có chi phí cấp post**
(`budget_vnd` chỉ có ở cấp campaign — xem `crosswalk.yml` mục `cost.gap: true`).
`cost` = `budget_vnd` chia theo trọng số định dạng (long_video 3.2 · fb_reel 2.4 · fb_post 1.0);
`allocation_method` và `allocation_weight` ghi rõ cách chia để học viên biết đây là **số phân bổ,
không phải số kế toán**. Tổng `cost` theo campaign = đúng `budget_vnd`.

## 12. `data/KPIM/star/cta_lead_bridge.csv` ★
**Grain:** 1 dòng = 1 (post × lead). **1154 dòng.** Mắt xích nối **S04 (số liệu bài)** sang
**S05 (lead)**.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `post_id` | string | FK → calendar |
| `campaign_id` | string | FK |
| `cta_type` | enum | Từ calendar |
| `cta_link` | string | Có UTM đầy đủ: `utm_source` · `utm_medium` · `utm_campaign` · `utm_content=<post_id>` |
| `landing_page` | string | `/lp/cmp-2026-qn` |
| `lead_id` | string | **Rỗng** ⇒ bài có CTA nhưng không ra lead nào (giữ dòng để lead-per-post = 0 chứ không BLANK) |
| `lead_source` | string | Nguồn của lead đó |
| `lead_created_at` | datetime | |

---

## Nhiễu cố ý (đáp án cho giảng viên)

| # | Nhiễu | Ở đâu | Số lượng | Học viên phải làm gì |
|---|---|---|---|---|
| 1 | `media_link` rỗng | `calendar.csv` | **5** dòng | Lọc trước khi đưa vào workflow ⇒ tương ứng 7 dòng `skipped` trong `execution_log` |
| 2 | `schedule_date` sai định dạng (`dd/MM/yyyy` lẫn trong ISO) | `calendar.csv` | **3** dòng | Ép kiểu ngày tường minh, không để Power Query tự đoán locale |
| 3 | Lặp `asset_id` (bản sao lệch `schedule_date` 1 ngày) | `calendar.csv` | **2** dòng | Dedupe theo `asset_id`, giữ bản mới nhất ⇒ tương ứng 4 dòng `error` |
| 4 | Lead trùng người (cùng SĐT + tên, khác nguồn, lệch vài giờ) | 7 file lead | **219** cặp (~4%) | Dedupe theo (SĐT chuẩn hoá + tên); **không** có cột đánh dấu sẵn |
| 5 | 3 định dạng ngày + 4 kiểu hiển thị SĐT | 7 file lead | toàn bộ | Chuẩn hoá về ISO datetime + SĐT 10 số |
| 6 | Nhãn trạng thái/segment lẫn Anh–Việt | `lead_app`, `lead_social_inbox`, `lead_website` (Anh) vs `lead_branch` (Việt) | toàn bộ | Map về 1 bộ giá trị |
| 7 | `lead_social_inbox` thiếu hẳn cột `branch` | 1 file | toàn bộ | Append đa nguồn phải xử lý cột thiếu, không được để lệch cột |
| 8 | 56 cột rỗng hoàn toàn trong Post Summary | file gốc | 56 cột | Dọn cột rỗng (bài S04) |
| 9 | `Ngày` = `"Trọn đời"` trong Summary | file gốc | 60 dòng | Lấy trục thời gian từ `Thời gian đăng` |
| 10 | `baseline_median`/`baseline_source` rỗng (chưa đủ mẫu) | `kpi_target.csv` | 75/135 dòng — **toàn bộ 35 dòng của Q1** (không có quý trước) | Hiện "chưa đủ mẫu", **không** thay bằng số đoán. Thêm nữa: 55 dòng có baseline nhưng `baseline_n < 10` ⇒ theo model.yml vẫn phải hiện "chưa đủ mẫu" |

---

## Câu chuyện dữ liệu — 5 insight bộ dữ liệu được thiết kế để học viên tìm ra

1. **Video và Reel ăn đứt Ảnh về tương tác.** Engagement rate (`Cảm xúc, bình luận và lượt
   chia sẻ` / `Số người tiếp cận`): Thước phim ≈ 2.48% · Video ≈ 2.47%
   so với Ảnh ≈ 2.00% và Liên kết ≈ 0.59%. Reel còn có reach trung vị
   cao gấp ~2,3 lần Ảnh. ⇒ Khuyến nghị dịch tỷ trọng định dạng, không phải tăng số bài.

2. **Bẫy kinh điển: Promo click nhiều nhất nhưng ra khách kém nhất.** Promo chiếm
   67% tổng lượt click vào liên kết (2,307 click)
   nhưng chỉ đổi được **0.17 lead/click** — **thấp nhất** trong 6 pillar, trong khi
   Education 0.74 · HowTo 0.69
   (cao nhất: Education 0.74).
   ⇒ Nếu chấm hiệu quả bằng CTR, Promo thắng; chấm bằng lead, Promo thua. Dạy học viên
   **đo tới cuối phễu**.

3. **Education + HowTo cho lead chất lượng cao nhất.** Tỷ lệ `lead_segment = hot` trên lead
   gắn được về bài: Education ≈ 47% · HowTo ≈ 41%,
   so với Promo ≈ 10% · Brand ≈ 7%.
   ⇒ Nội dung "dạy" nuôi phễu tốt hơn nội dung "giảm giá". Kết hợp với insight #2: Promo vừa
   ra ít lead trên mỗi click, vừa ra lead nguội hơn.

4. **Q3 hụt mục tiêu lead rõ rệt.** `CMP-2026-Q3` đặt target 2500 lead nhưng thực
   tế chỉ 1760 lead (**70%**), trong khi Q1 106% ·
   Q2 100% · Q4 103%. ⇒ Trang "KPI vs Actual" có một quý
   đỏ để phân tích: reach vẫn đạt, nhưng chuyển đổi sang lead sụp — vấn đề ở CTA/landing,
   không ở phân phối.

5. **YouTube nhỏ hơn nhưng "đắt" hơn.** Với 29 bài chạy cả hai kênh, tổng view
   YouTube (38,530) chỉ bằng ~31% reach Facebook của
   chính các bài đó (126,000). Nhưng YouTube đổi được
   ~6.51 subscriber/1000 view, trong khi cùng nhóm bài đó Facebook chỉ ra
   ~5.00 lead/1000 reach. ⇒ Kênh nhỏ không có nghĩa là kênh kém;
   phải so bằng chỉ số chuyển đổi chứ không bằng quy mô.
   *(Lưu ý khi chấm bài: subscriber và lead là hai sự kiện chuyển đổi khác nhau nên đây là so
   sánh **định hướng**, không phải so ngang hàng. Kết luận đúng mà học viên cần rút ra là
   "phải chuẩn hoá theo quy mô trước khi kết luận kênh nào tốt hơn" — chứ không phải
   "YouTube tốt hơn Facebook".)*

---

## Workbook chiến dịch — `<CAMPAIGN_ID>.xlsx`

*(bổ sung 2026-07-21 — sinh bởi `scripts/workbook/build_workbook.py` từ `schema/workbook_spec.yml`)*

Từ nay mỗi chiến dịch có **một workbook 13 sheet** gom toàn bộ vòng đời. Các file CSV mô tả
ở trên **vẫn là nguồn sự thật**; workbook là lớp làm việc của con người, nạp lại từ CSV.

| Sheet | Grain | Ai ghi | Ghi chú |
|---|---|---|---|
| `00_README` | 1 mục hướng dẫn | 🤖 agent | Luật màu, cách chạy lại |
| `01_Brief` | 1 trường (bố cục dọc) | 👤 người | Thay cho `brief.yml` — brief là thứ người duyệt |
| `02_KPI_Target` | campaign × kênh × pillar × chỉ số × kỳ | 👤 target · ⚙️ baseline | `baseline_n < 10` ⟹ chặn mọi so-sánh-median |
| `03_Calendar` | **1 asset** | 🤖 sinh · 👤 duyệt | 39 cột, 6 nhóm; sheet trung tâm |
| `04_Content` | asset × loại nội dung × biến thể | 🤖 agent | Giữ được title A/B; text dài trỏ `draft_path` |
| `05_Approval` | asset × vòng duyệt | 👤 người | 10 cột checklist; giữ lịch sử revise |
| `06_Publish_Log` | asset × kênh × lần chạy | ⚙️ script | `mode=live` chỉ hợp lệ khi `autonomy_at_run=full` |
| `07_Metrics_Daily` | asset × kênh × ngày | ⚙️ script | Bản nạp lại của riêng chiến dịch này |
| `08_Metrics_Summary` | asset × kênh | ⚙️ tính · 👤 chốt | `subs_per_1000_engaged` · `is_winner` · `decision_28d` |
| `09_Leads` | 1 lead | ⚙️ script | **Cố ý để RỖNG** — xem ghi chú bên dưới |
| `10_Insights` | 1 phát hiện | 🤖 đề xuất · 👤 duyệt | Bắt buộc `evidence_metric` + `evidence_value` |
| `_Lists` | | ⚙️ | 20 danh sách enum → dropdown ràng buộc |
| `_Dictionary` | 1 cột của 1 sheet | ⚙️ | 190 dòng — đọc ngay trong file, không cần mở tài liệu khác |

### Vì sao `09_Leads` để rỗng

Đây là **sheet đích của bài S05**, không phải dữ liệu cho sẵn. Chỉ **3/7** file lead
(`lead_form`, `lead_qr_event`, `lead_website`) dùng đúng tên cột `campaign_id`;
4 file còn lại đặt tên khác — đúng thiết kế "schema lệch nhau" để luyện chuẩn hoá.
Nạp sẵn một phần sẽ khiến học viên tưởng dữ liệu đã sạch. Nhiệm vụ của họ là append
đủ **5.687 dòng** từ 7 nguồn về đúng schema của sheet này.

### Quy ước màu hàng tiêu đề

| Màu | Ý nghĩa |
|---|---|
| 🟡 Vàng | Cột của **người** — agent/script không bao giờ ghi đè |
| 🟢 Xanh lá | Do **script** sinh — sửa tay sẽ bị ghi đè lần chạy sau |
| 🔵 Xanh dương | Do **agent** sinh — sửa thoải mái |

**Ô rỗng nghĩa là CHƯA BIẾT.** Không điền 0, không điền "N/A", không đoán.
Riêng `baseline_median` rỗng = chưa đủ mẫu, dashboard phải hiện "chưa đủ mẫu".
