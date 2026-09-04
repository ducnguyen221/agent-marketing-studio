# Quy trình tổng — agent làm gì, theo thứ tự nào

Điểm vào duy nhất. Mô hình: **mỗi campaign = 1 thư mục + 1 hồ sơ `.md` + 1 workbook `.xlsx`
(4 sheet: Campaign · Content · Post · _Legend)**.

Trước khi đụng bất cứ ô nào: đọc [`../knowledge/data_model/DATA_MODEL.md`](../knowledge/data_model/DATA_MODEL.md) —
đó là nguồn sự thật về mọi trường. File này chỉ nói **thứ tự và luật vận hành**.

---

## Vòng đời — 7 khâu, 2 cổng của người

```
① new ─→ ② plan ─🔒cổng 1─→ ③ produce ─→ ④ selfqa ─🔒cổng 2─→ ⑤ render ─→ ⑥ publish ─→ ⑦ measure
         Content              content.md      quality_check      audio/video    Post.publish_*   actual_*
         (proposed)           + Post rows      (MÁY tự kiểm)                                     + báo cáo .md
```

**Cổng 1 — người duyệt Content:** `Content.status = approved` **và** `Content.approved_date` có ngày.
**Cổng 2 — người duyệt Post:** `Post.review_status = approved`.

Agent **không bao giờ** tự đặt hai giá trị đó. `quality_check` là bước MÁY tự kiểm **trước**
khi trình người — nó không thay được cổng.

> **Vì sao render sau cổng 2:** dựng video/audio tốn thời gian và GPU. Duyệt chữ trước, dựng sau
> — nội dung bị trả về sửa thì chưa mất công render.

---

## Hợp đồng từng khâu

### ① new — dựng chiến dịch
| | |
|---|---|
| **Vai** | `campaign-strategist` |
| **Vào** | Đề bài của người + `instance.yml` |
| **Làm** | Hỏi 1 lượt phần còn thiếu → tạo thư mục → **copy** `CAMPAIGN_TEMPLATE.xlsx` và `campaign.md` vào, đổi tên theo `campaign_code` → điền sheet Campaign |
| **Ra** | `Campaign.status = active` |

**Copy, không dựng lại.** Workbook mới = `shutil.copy2(CAMPAIGN_TEMPLATE.xlsx)` rồi chỉ ghi giá
trị ô. Không tạo sheet, không set style, không sinh từ spec — làm thế là mất format.
Sau khi copy: **xoá dữ liệu mẫu** ở sheet Campaign và Content.

### ② plan — đề xuất content
| | |
|---|---|
| **Vai** | `content-strategist` · hỗ trợ `seo-specialist` |
| **Vào** | Sheet Campaign + hồ sơ `.md` Mục 4 (**cái KHÔNG làm**) + content đã có (tránh trùng) |
| **Làm** | Sinh N dòng Content. Điền đủ nhóm Strategy (`content_goal`, `audience_profile`, `core_brief`), Knowledge (`key_sources`), SEO (`target_keyword`), Creativity (`creative_direction`), Governance (`constraints`) |
| **Ra** | `Content.status = proposed` → **dừng, chờ người** |

- `content_pillar` phải nằm trong danh sách hợp lệ. Lần đầu chạy campaign → **chốt bộ pillar
  chi tiết với người trước khi sinh hàng loạt**.
- `schedule_date` nằm trong `schedule_start`–`schedule_end`, rải theo `cadence`.
- Chủ đề rơi vào "cái KHÔNG làm" → loại, không thương lượng để cho đủ số.

### 🔒 Cổng 1 — người duyệt Content
Người đặt `status = approved` + `approved_date`. Chưa có → khâu ③ **không có việc**.
Người có thể duyệt trước hàng loạt nếu đã thống nhất kế hoạch mass production.

### ③ produce — viết nội dung + sinh dòng Post
| | |
|---|---|
| **Vai** | `content-producer` · hỗ trợ `seo-specialist`, skill `hook-writer`/`thread-writer` |
| **Vào** | Content đã `approved` |
| **Làm** | Tạo `<folder_path>/content.md` từ `content.md`; viết BRIEF rồi từng khối `## post:<post_format>` |
| **Ra** | `Content.status = in_production`; mỗi khối = 1 dòng Post, `agent_status = completed` |

Mỗi dòng Post phải điền: `post_id`, `content_id`, `channel`, `post_format`, `post_role`,
`post_content` (= anchor), `target_view`, `target_interaction` (kế thừa `kpi_*_target`),
`publish_plan`, `updated_at`.

- **Một khối = một dòng Post.** Có khối mà không có dòng, hoặc ngược lại = sai, phải báo.
- `channel` chỉ được lấy từ `Campaign.channels`.
- `asset_ref` **để trống** nếu dùng asset mặc định (bảng trong hồ sơ `.md` Mục 6).
  `carousel`/`infographic` thì bắt buộc điền.
- Số/claim chưa kiểm được → gắn `[KIỂM CHỨNG]`, không bịa.

### ④ selfqa — máy tự kiểm
| | |
|---|---|
| **Vai** | `qa-reviewer` (tuân thủ, chặn phát hành) · `content-editor` (hay/rõ, tư vấn) |
| **Vào** | Post `agent_status = completed` |
| **Làm** | Chạy `../.agents/checklists/QA_ASSET.md`: giọng đúng instance · không lộ tên tool nội bộ · hashtag đúng giới hạn kênh · không còn `[KIỂM CHỨNG]` mở · claim có trong `key_sources` · Facebook không markdown literal |
| **Ra** | `quality_check = passed` / `needs_review` / `failed`; `post_status = human_review` |

**Còn nghi ngờ thì chọn `needs_review`, không tự xác nhận `passed`.** Trượt → `agent_status
= ai_qa_failed`, ghi lý do vào `review_feedback`, sửa rồi kiểm lại.

### 🔒 Cổng 2 — người duyệt Post
Người đặt `review_status = approved`. Nếu `changes_requested` → đọc `review_feedback`, sửa,
`post_status = revision`, quay lại ④. **Không xoá feedback cũ.**

### ⑤ render — dựng hình & tiếng
| | |
|---|---|
| **Vai** | `creative-producer` |
| **Vào** | Post `review_status = approved`, theo cờ `Content.audio` / `video` / `short` |
| **Làm** | Xem [`../knowledge/toolchains/ASSET_TOOLCHAIN.md`](../knowledge/toolchains/ASSET_TOOLCHAIN.md) — HyperFrames render, OmniVoice lồng tiếng |
| **Ra** | File nằm trong `<folder_path>`, đặt tên đúng quy ước; `post_status = approved` |

Cờ `= no` thì **không dựng**. Short luôn **hỏi xác nhận** trước khi dựng.

### ⑥ publish — đăng đa kênh
| | |
|---|---|
| **Vai** | `distribution-manager` |
| **Vào** | Post `review_status = approved` **và** `quality_check = passed` |
| **Làm** | Đăng/hẹn lịch theo giờ vàng từng kênh (hồ sơ `.md` Mục 5) |
| **Ra** | `publish_status`, `publish_link`, `post_status = published`; `Content.status = published` + `published_date` (lấy ngày post đầu tiên đăng) |

Thiếu token → **dừng**, báo người setup (`../knowledge/toolchains/PLATFORM_SETUP.md`). Không retry mù.
Mặc định dry-run trừ khi `instance.yml` đặt `autonomy: full` **và** người xác nhận lượt này.

### ⑦ measure — đo & báo cáo
| | |
|---|---|
| **Vai** | `growth-analyst` |
| **Vào** | Post `publish_status = published` |
| **Làm** | Kéo số về các cột `actual_*` + `metric_updated_at`; đối chiếu `target_*` |
| **Ra** | `post_status = measuring` → `completed`; append `### Báo cáo <ngày>` vào hồ sơ `.md` Mục 9 |

> ⚠️ **Cột `actual_*` GHI ĐÈ — file Excel không giữ lịch sử đo.** Muốn so D+1 với D+30 thì
> **bắt buộc** chốt số vào Mục 9 của hồ sơ `.md` mỗi lần đo. Bỏ bước này là mất vĩnh viễn.

Nền tảng không trả chỉ số nào → **để trống**, không điền 0, không quy đổi từ chỉ số khác.

---

## Ai làm khâu nào

Điều phối: **`marketing-director`** — chiến lược tổng, giao vai, giám sát, quản mức tự trị.

| Khâu | Vai chính | Hỗ trợ |
|---|---|---|
| ① new | `campaign-strategist` | `marketing-director` |
| ② plan | `content-strategist` | `seo-specialist` |
| ③ produce | `content-producer` | `seo-specialist` · skill `hook-writer`, `thread-writer` |
| ④ selfqa | `qa-reviewer` (chặn) | `content-editor` (tư vấn) |
| ⑤ render | `creative-producer` | — |
| ⑥ publish | `distribution-manager` | — |
| ⑦ measure | `growth-analyst` | — |

---

## Vòng lặp chuẩn mỗi lượt

```
1. Xem hiện trạng   → đếm Content theo status, Post theo post_status
2. Chọn khâu        → khâu sớm nhất còn việc; không nhảy cóc
3. Lọc đúng điều kiện vào của khâu đó
4. Danh sách rỗng?  → DỪNG. Báo rõ AI cần đặt CỘT NÀO thành GÌ. Không tự tick.
5. Xử lý TỪNG dòng, ghi ngay vào Excel sau mỗi dòng
6. Cuối lượt        → báo đã đổi gì, ở sheet nào, dòng nào
```

**Đọc giá trị lạ** (không có trong danh sách hợp lệ ở `DATA_MODEL.md`) → **báo cáo cho người**,
không im lặng bỏ qua dòng đó. Bỏ qua im lặng là kiểu lỗi tệ nhất của hệ này: nhìn như "không
có việc" trong khi thật ra dữ liệu sai.

---

## Bảy điều tuyệt đối

1. Không đặt hộ `Content.status = approved`, `approved_date`, hay `review_status = approved`.
2. Không đăng thật khi chưa đủ token, chưa qua cổng 2, hoặc `autonomy` chưa cho phép.
3. Không bịa số, nguồn, kết quả. Chưa kiểm được thì gắn `[KIỂM CHỨNG]` hoặc để trống.
4. Không điền `0` thay cho "chưa có". Ô rỗng là một giá trị có nghĩa.
5. Không lộ tên công cụ/hạ tầng sản xuất nội bộ trong nội dung công khai.
6. Cùng một brief phải FORMAT LẠI theo từng kênh — không copy y nguyên.
7. Cuối mỗi lượt báo đã đổi gì, ở sheet nào.

---

## Trạng thái công cụ

| Vùng | |
|---|---|
| `templates/CAMPAIGN_TEMPLATE.xlsx` (4 sheet) | ✅ chuẩn hiện hành |
| `knowledge/data_model/DATA_MODEL.md` | ✅ nguồn sự thật về trường |
| Bộ mẫu `content/KPIM/02_campaigns/01_Tobi_Posts` | ✅ 15 content · 25 post |
| `scripts/` (`campaign_excel.py`, `build_workbook.py`, `build_preview.py`, `campaign_registry.py`) | ⛔ **còn theo mô hình cũ, chưa chạy được với 4 sheet mới** |
| `schema/workbook_spec.yml` | ⛔ còn mô tả 5 sheet cũ |
| Kéo số liệu nền tảng về `actual_*` (API) | ⛔ chưa có script — quy trình thủ công ở `../knowledge/toolchains/PLATFORM_SETUP.md` |

Trong lúc script chưa cập nhật: agent đọc/ghi workbook **trực tiếp bằng `openpyxl`**, theo đúng
tên sheet và tên cột khai ở `DATA_MODEL.md`. Ghi xong phải đọc lại để xác nhận.
