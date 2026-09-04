# Quy trình tổng — agent làm gì, theo thứ tự nào

Điểm vào duy nhất. Mô hình: **mỗi kênh = 1 thư mục · mỗi chiến dịch = 1 thư mục có
`campaign.md` · mỗi bài = 1 thư mục con**. Markdown là nguồn sự thật; `.xlsx` chỉ là bản
xuất một chiều (`export_excel.py`).

Trước khi đụng bất cứ ô nào: đọc [`../knowledge/data_model/DATA_MODEL.md`](../knowledge/data_model/DATA_MODEL.md) —
đó là nguồn sự thật về mọi trường. File này chỉ nói **thứ tự và luật vận hành**.

---

## Vòng đời — 7 khâu, 2 cổng của người

```
① new ─→ ② plan ─🔒cổng 1─→ ③ produce ─→ ④ selfqa ─🔒cổng 2─→ ⑤ render ─→ ⑥ publish ─→ ⑦ measure
     bảng Content         content.md      23 cổng kiểm       audio/video    publish.json     actual_*
      (proposed)          + posts[]        (MÁY tự kiểm)                    + URL vào bảng   + báo cáo .md
```

**Cổng 1 — người duyệt đề tài:** trong bảng Content của `campaign.md`, `status = approved`
**và** ô `g1` có ngày.
**Cổng 2 — người duyệt trước khi đăng:** `publish.json → posts[].review.status = approved`,
bắt buộc kèm `approved_by` và câu duyệt nguyên văn (`register_publish approve --by … --note …`).

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
| **Vào** | Đề bài của người + `channel.yml` của kênh |
| **Làm** | Hỏi 1 lượt phần còn thiếu → `new_campaign.py --channel … --id CMP-YYMM-slug --name … --prefix XXX` → **điền cho đủ** frontmatter và Mục 1–4 của `campaign.md` |
| **Ra** | `status: active` trong frontmatter |

**Dùng script, không dựng tay.** `new_campaign.py` copy từ `templates/campaign.md` và ghi đúng
chỗ. Tự tạo thư mục bằng tay là sớm muộn lệch cấu trúc, và `check_tree.py` mới phát hiện ra.

**Điền cho ĐỦ trước khi tạo bài.** `new_post.py` chặn khi tám trường bắt buộc còn nguyên chữ
mẫu: `business_problem · campaign_goal · target_audience · audience_pain_points ·
key_message · content_pillar · channels · primary_cta`. Bài viết ra từ một chiến dịch chưa rõ
đối tượng thì viết xong mới biết lệch — lúc đó đã tốn cả vòng nghiên cứu, dựng tiếng, dựng hình.

### ② plan — đề xuất content
| | |
|---|---|
| **Vai** | `content-strategist` · hỗ trợ `seo-specialist` |
| **Vào** | frontmatter `campaign.md` + Mục 4 (**cái KHÔNG làm**) + `continuity.json` của kênh (tránh trùng đề tài) |
| **Làm** | `new_post.py` cho từng bài, hoặc `--bulk loat.tsv` cho cả đợt. Rồi điền frontmatter `research.md` của từng bài: `content_goal`, `audience_profile`, `core_brief`, `key_sources`, `target_keyword`, `creative_direction`, `constraints` |
| **Ra** | dòng trong bảng Content, `status = proposed`, ô `g1` **rỗng** → **dừng, chờ người** |

- `content_pillar` phải nằm trong danh sách hợp lệ. Lần đầu chạy campaign → **chốt bộ pillar
  chi tiết với người trước khi sinh hàng loạt**.
- `schedule_date` nằm trong `schedule_start`–`schedule_end`, rải theo `cadence`.
- Chủ đề rơi vào "cái KHÔNG làm" → loại, không thương lượng để cho đủ số.

### 🔒 Cổng 1 — người duyệt đề tài
Người đặt `status = approved` + ngày vào ô `g1` của bảng Content. Chưa có → khâu ③ **không có việc**.
Người có thể duyệt trước hàng loạt nếu đã thống nhất kế hoạch mass production.

### ③ produce — viết nội dung + sinh dòng Post
| | |
|---|---|
| **Vai** | `content-producer` · hỗ trợ `seo-specialist`, skill `hook-writer`/`thread-writer` |
| **Vào** | Content đã `approved` |
| **Làm** | **Đọc đủ ba thứ trước khi viết một chữ**: `campaign.md` của chiến dịch · `profile.md` của kênh · `research.md` của chính bài. Rồi điền `content.md`: BRIEF, sau đó từng khối `## post:<post_format>` |
| **Ra** | `status = in_production`; mỗi khối = 1 phần tử trong `publish.json → posts[]`, `agent_status = completed` |

> **Hợp đồng đọc.** Không cổng máy nào bắt được việc *có đọc hay không* — chỉ bắt được hậu
> quả (G05 nguồn, G11 giọng). Bỏ (2) thì ra bài trung tính, đúng mà nhạt; đó là lỗi từng
> chạy suốt ba bài mà không ai thấy. Bảng đầy đủ ở
> [`../knowledge/toolchains/ATLAS_CHANNEL.md`](../knowledge/toolchains/ATLAS_CHANNEL.md).

Mỗi phần tử `posts[]` phải có: `post_id`, `channel`, `post_format`, `post_role`,
`post_content` (= neo `post:<format>`), `target`, `publish_plan`, `updated_at`.
`register_publish init` dựng sẵn khung này từ `content.md`.

- **Một khối = một phần tử `posts[]`.** Lệch nhau = mồ côi; `check_tree.py` bắt được.
- `channel` chỉ được lấy từ `channels` trong frontmatter `campaign.md`.
- `asset_ref` **để trống** nếu dùng asset mặc định (bảng trong hồ sơ `.md` Mục 6).
  `carousel`/`infographic` thì bắt buộc điền.
- Số/claim chưa kiểm được → gắn `[KIỂM CHỨNG]`, không bịa.

### ④ selfqa — máy tự kiểm
| | |
|---|---|
| **Vai** | `qa-reviewer` (tuân thủ, chặn phát hành) · `content-editor` (hay/rõ, tư vấn) |
| **Vào** | Post `agent_status = completed` |
| **Làm** | Chạy `blog_gates.py` (23 cổng, kiểm bằng số) + `../.agents/checklists/QA_ASSET.md`: giọng đúng kênh · không lộ tên công cụ nội bộ · hashtag đúng giới hạn · không còn `[KIỂM CHỨNG]` mở · claim có trong `research.md` · Facebook không markdown literal |
| **Ra** | `quality_check = passed` / `needs_review` / `failed`; `post_status = human_review` |

Trạng thái cổng có **ba** giá trị: xanh · đỏ · **thiếu**. Cổng không chạy được là *chưa biết*,
**không bao giờ** được cộng vào xanh. Miễn trừ một cổng thì phải ghi lý do:
`--cho-phep "tên=lý do"` — nới danh sách từ khoá để đỡ đỏ là làm hỏng cổng cho mọi bài sau.

**Còn nghi ngờ thì chọn `needs_review`, không tự xác nhận `passed`.** Trượt → `agent_status
= ai_qa_failed`, ghi lý do vào `review_feedback`, sửa rồi kiểm lại.

### 🔒 Cổng 2 — người duyệt trước khi đăng
`register_publish approve --by "<tên>" --note "<câu duyệt nguyên văn>"`. **Bắt buộc cả hai**:
duyệt mà không để lại dấu vết thì sáu tháng sau không ai biết ai đã đồng ý với cái gì. Nếu `changes_requested` → đọc `review_feedback`, sửa,
`post_status = revision`, quay lại ④. **Không xoá feedback cũ.**

### ⑤ render — dựng hình & tiếng
| | |
|---|---|
| **Vai** | `creative-producer` |
| **Vào** | `posts[].review.status = approved`, theo cờ `audio` / `video` / `short` trong `research.md` |
| **Làm** | Xem [`../knowledge/toolchains/ASSET_TOOLCHAIN.md`](../knowledge/toolchains/ASSET_TOOLCHAIN.md) — HyperFrames render, OmniVoice lồng tiếng |
| **Ra** | File nằm trong `<folder_path>`, đặt tên đúng quy ước; `post_status = approved` |

Cờ `= no` thì **không dựng**. Short luôn **hỏi xác nhận** trước khi dựng.

### ⑥ publish — đăng đa kênh
| | |
|---|---|
| **Vai** | `distribution-manager` |
| **Vào** | Post `review_status = approved` **và** `quality_check = passed` |
| **Làm** | Đăng theo thứ tự **YouTube → trang blog → Facebook** — thứ tự duy nhất mà mỗi bước có sẵn đầu vào nó cần. Giờ vàng từng kênh ở `campaign.md` Mục 5 |
| **Ra** | `register_publish set` ghi `publish.json`, thay `{{BLOG_URL}}`/`{{YOUTUBE_URL}}`, cập nhật `continuity.json`, và ghi **URL thật** vào ba cột `web`/`youtube`/`facebook` của bảng Content |

Thiếu token → **dừng**, báo người setup (`../knowledge/toolchains/PLATFORM_SETUP.md`). Không retry mù.
Mặc định dry-run trừ khi `channel.yml` đặt `autonomy: full` **và** người xác nhận lượt này.

### ⑦ measure — đo & báo cáo
| | |
|---|---|
| **Vai** | `growth-analyst` |
| **Vào** | Post `publish_status = published` |
| **Làm** | `register_publish metrics` ghi vào `posts[].actual`; đối chiếu `posts[].target`. Thu tự động qua API **chưa có** — hiện nhập tay |
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
1. Xem hiện trạng   → `check_tree.py --station <trạm>` rồi đếm bảng Content theo status
2. Chọn khâu        → khâu sớm nhất còn việc; không nhảy cóc
3. Lọc đúng điều kiện vào của khâu đó
4. Danh sách rỗng?  → DỪNG. Báo rõ NGƯỜI cần đặt Ô NÀO thành GÌ. Không tự điền.
5. Xử lý TỪNG bài, ghi ngay vào file sau mỗi bài (ghi nguyên tử, không hỏng nửa chừng)
6. Cuối lượt        → báo đã đổi gì, ở file nào, dòng nào
```

**Đọc giá trị lạ** (không có trong danh sách hợp lệ ở `DATA_MODEL.md`) → **báo cáo cho người**,
và nhớ: `md_io.upsert_row` **ném lỗi** khi ghi một khoá không có trong bảng — trước đây nó bỏ
im lặng, người gọi tưởng đã ghi và giá trị bốc hơi.
không im lặng bỏ qua dòng đó. Bỏ qua im lặng là kiểu lỗi tệ nhất của hệ này: nhìn như "không
có việc" trong khi thật ra dữ liệu sai.

---

## Bảy điều tuyệt đối

1. Không đặt hộ `status = approved`, ô `g1`, hay `posts[].review.status = approved`.
2. Không đăng thật khi chưa đủ token, chưa qua cổng 2, hoặc `autonomy` chưa cho phép.
3. Không bịa số, nguồn, kết quả. Chưa kiểm được thì gắn `[KIỂM CHỨNG]` hoặc để trống.
4. Không điền `0` thay cho "chưa có". Ô rỗng là một giá trị có nghĩa.
5. Không lộ tên công cụ/hạ tầng sản xuất nội bộ trong nội dung công khai.
6. Cùng một brief phải FORMAT LẠI theo từng kênh — không copy y nguyên.
7. Cuối mỗi lượt báo đã đổi gì, ở file nào.

---

## Trạng thái công cụ

| Vùng | |
|---|---|
| `templates/campaign.md` · `channel.yml` · `CHANNELS.md` | ✅ chuẩn hiện hành |
| `templates/CAMPAIGN_TEMPLATE.xlsx` | ✅ chỉ còn là **mẫu cột** cho `export_excel.py` |
| `knowledge/data_model/DATA_MODEL.md` | ✅ nguồn sự thật về trường |
| `examples/` — trạm mẫu đã điền, 3 bài ở 3 trạng thái | ✅ đọc để hiểu hình dạng |
| `scripts/pipeline/` — `new_channel` · `new_campaign` · `new_post` · `gen_article` · `blog_gates` · `register_publish` · `check_tree` · `build_views` · `export_excel` | ✅ chuẩn hiện hành |
| `scripts/lib/` — `md_io` (đọc/ghi Markdown nguyên tử) · `studio_paths` · `post_paths` | ✅ nền của mọi script |
| Kéo số liệu nền tảng về `actual` (API) | ⛔ chưa có script — nhập tay qua `register_publish metrics` |

**Không đọc/ghi Markdown bằng regex cả file.** Mọi cập nhật bảng đi qua `md_io.upsert_row`,
chỉ đụng vùng giữa marker `<!-- CONTENT:BEGIN/END -->`, và ghi nguyên tử (`.tmp` rồi đổi tên).
Một lần regex neo hai đầu mà mốc đầu trượt đã từng xoá mất nguyên khối governance.
