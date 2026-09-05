---
name: campaign-pipeline
description: >
  Vận hành pipeline một chiến dịch content end-to-end: 7 khâu new → plan → produce → selfqa →
  render → publish → measure, Excel làm chủ trạng thái, 2 cổng duyệt của người. Dùng khi người
  dùng nói "chạy chiến dịch", "tiếp tục campaign", "tới bước tiếp theo", "campaign này đang ở
  đâu", hoặc đưa một workbook chiến dịch.
---

# Campaign Pipeline — hợp đồng 7 khâu

> Mô hình dữ liệu đầy đủ: [`../../knowledge/DATA_MODEL.md`](../../knowledge/DATA_MODEL.md).
> Thứ tự + điều kiện từng khâu: [`../../workflows/00_WORKFLOW_INDEX.md`](../../workflows/00_WORKFLOW_INDEX.md).
> Skill này là bản rút gọn để chạy nhanh — có gì mâu thuẫn thì **hai file kia thắng**.

## Nguyên tắc lõi

- **Excel làm chủ trạng thái.** Chỉ xử lý dòng đủ điều kiện vào của khâu. Không nhảy cóc.
- **Hai cổng của người.** Cổng 1: `Content.status = approved` + `approved_date`.
  Cổng 2: `Post.review_status = approved`. Agent **không tự đặt** ba giá trị này.
- **Ghi tới đâu xác nhận tới đó.** Ghi xong đọc lại. Cuối lượt báo đã đổi gì ở sheet nào.
- **Giá trị lạ → báo người**, không im lặng bỏ qua dòng.

## Luôn bắt đầu bằng hiện trạng

Chạy `check_tree.py --station <trạm>` rồi đếm bảng Content theo `status` và `posts[]` theo
`post_status`, rồi báo: đang tắc ở đâu, NGƯỜI cần đặt ô nào thành gì. Rồi mới hỏi người muốn chạy khâu nào (trừ khi họ đã nói rõ).

## Ba tầng — nhớ đúng quan hệ

```
Kênh  →  Chiến dịch  →  Bài (ý tưởng)  →  posts[] (1 kênh × 1 format)
channel.yml  campaign.md      ↓                    ↓
profile.md   bảng Content   <thư mục bài>/   post_content = neo
continuity     (15 cột)      content.md   ←──  trỏ vào đúng khối '## post:<format>'
```

---

## Hợp đồng từng khâu

### ① `new` — dựng chiến dịch
**Vào:** đề bài của người · **Làm:** `new_channel.py` (nếu chưa có kênh — `--path` phải HỎI
NGƯỜI) → `new_campaign.py` → điền frontmatter và Mục 1–6 · **Ra:** `status: active`.
Dùng script — **không** dựng thư mục bằng tay.

### ② `plan` — đề xuất content
**Vào:** frontmatter `campaign.md` + hồ sơ `.md` Mục 4 (cái KHÔNG làm) + content đã có.
**Làm:** `new_post.py` (hoặc `--bulk` cho cả đợt), rồi điền frontmatter `research.md` của từng
bài: Strategy / Knowledge / SEO / Creativity / Governance.
`schedule_date` nằm trong khoảng campaign, rải theo `cadence`.
**Ra:** `status = proposed` → **dừng, chờ cổng 1**.

### 🔒 Cổng 1 — người duyệt Content

### ③ `produce` — viết nội dung + sinh Post
**Vào:** Content `approved`.
**Làm:** đọc đủ ba thứ (chiến dịch · hồ sơ kênh · nghiên cứu của bài) rồi điền `content.md`
sẵn có — BRIEF trước, rồi từng khối `## post:<post_format>`. `register_publish init` sinh
đúng **một** phần tử `posts[]` cho mỗi khối, `channel` lấy từ `channels` của chiến dịch.
**Ra:** `Content.status = in_production`, `Post.agent_status = completed`.

### ④ `selfqa` — máy tự kiểm
**Vào:** Post `agent_status = completed`.
**Làm:** chạy `../../checklists/QA_ASSET.md`. Kiểm: đúng giọng · không lộ tên tool nội bộ ·
hashtag đúng giới hạn kênh · không còn `[KIỂM CHỨNG]` mở · claim có trong `key_sources` ·
Facebook không markdown literal.
**Ra:** `quality_check` + `agent_status` (do `register_publish qa` đặt từ `gates.json`).
**Nghi ngờ → để `failed` và ghi lý do, đừng tự xác nhận `passed`.**

### 🔒 Cổng 2 — người duyệt Post
`changes_requested` → đọc `review.feedback`, sửa, chạy lại ④. Không có trạng thái trung gian
nào để đặt — `post_status` chỉ nhận `not_created` · `approved` · `published`.
Không xoá feedback cũ.

### ⑤ `render` — hình & tiếng
**Vào:** Post `review_status = approved`, theo cờ `Content.audio/video/short`.
**Làm:** theo [`../../knowledge/ASSET_TOOLCHAIN.md`](../../knowledge/ASSET_TOOLCHAIN.md) —
HyperFrames render, OmniVoice lồng tiếng. Cờ `no` thì không dựng. Short **luôn hỏi xác nhận**.
**Ra:** file trong `folder_path`, `post_status = approved`.

### ⑥ `publish`
**Vào:** `review_status = approved` **và** `quality_check = passed`.
**Ra:** `publish_status`, `publish_link`, `post_status = published`; `Content.status = published`
+ `published_date`. Thiếu token → **dừng**, báo setup. Mặc định dry-run.

### ⑦ `measure`
**Vào:** Post `publish_status = published`.
**Ra:** các cột `actual_*` + `metric_updated_at`; append `### Báo cáo <ngày>` vào hồ sơ `.md` Mục 9.

> ⚠️ `actual_*` **ghi đè**, Excel không giữ lịch sử. Không chốt số vào hồ sơ `.md` = mất vĩnh viễn.

---

## Điều không bao giờ làm

Tự duyệt hộ (3 giá trị ở cổng) · đăng thật khi chưa đủ token / chưa qua cổng 2 / `autonomy`
chưa cho phép · bịa số, nguồn, kết quả · điền `0` thay cho "chưa có" · lộ tên tool nội bộ ·
copy y nguyên một nội dung sang mọi kênh.
