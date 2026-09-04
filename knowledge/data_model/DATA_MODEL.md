<!-- CANONICAL. Đây là NGUỒN SỰ THẬT về ĐỊNH NGHĨA trường.
     Dữ liệu thật sống trong campaign.md (frontmatter + bảng Content) và publish.json.
     Sửa trường / thêm giá trị hợp lệ → sửa file này TRƯỚC, rồi mới đổi templates/campaign.md
     và bộ cột trong scripts/pipeline/export_excel.py. -->

# DATA_MODEL — mô hình dữ liệu campaign

> Agent đọc **file này** để biết mỗi trường nghĩa là gì và phải hành xử ra sao với nó.
> Luật vận hành (thứ tự khâu, ai duyệt) nằm ở [`../workflows/00_WORKFLOW_INDEX.md`](../../workflows/00_WORKFLOW_INDEX.md) — đừng trộn hai thứ vào một chỗ.

## Ba tầng

```
Channel   một giọng, một tập người đọc     channel.yml + profile.md + continuity.json
 └─ Campaign  brief chiến lược             1 campaign = 1 thư mục + 1 campaign.md
     └─ Content   ý tưởng gốc, chưa gắn kênh     1 dòng trong bảng Content + 1 thư mục bài
          └─ Post      1 đầu ra cho 1 nền tảng × format   1 phần tử publish.json → posts[]
```

Kế thừa xuôi chiều: giá trị ở tầng trên là **ràng buộc** cho tầng dưới, không phải gợi ý.

| Từ Campaign | Chảy xuống Content | Rồi tới Post |
|---|---|---|
| `campaign_goal` | `content_goal` | `post_role` |
| `target_audience` + `audience_pain_points` | `audience_profile` | hook, ví dụ |
| `proof_points` | `key_sources` | claim trong nội dung |
| `brand_voice_rules` | `constraints` | `quality_check` |
| `key_message` | `target_keyword`, `core_brief` | tiêu đề, hook |
| `channels` (danh sách đóng) | — | `channel` |
| `primary_cta` | — | `post_role` + CTA |
| `kpi_*_target` | — | `target_view`, `target_interaction` |
| `schedule_start`/`end` + `cadence` | `schedule_date` | `publish_plan` |

## Quy ước chung

- **Ô rỗng = chưa có / chưa biết.** Không điền `0` thay cho thiếu, không đoán.
- **Ngày** `YYYY-MM-DD` · **thời điểm** `YYYY-MM-DD HH:MM`.
- **Giá trị hợp lệ** liệt kê bên dưới **không** được Excel ép bằng data validation —
  file tối ưu cho agent ghi. Agent gặp giá trị lạ → **báo cáo cho người**, không im lặng bỏ dòng.
- **Cột `actual_*` ghi đè**, file không lưu lịch sử đo. Cần diễn biến theo thời gian →
  ghi vào Mục 9 của hồ sơ `.md`.
- Nội dung text sống ở `<thư mục bài>/content.md`, **không** nằm trong ô Excel.

---

## ⚠️ MỘT TRƯỜNG, HAI TÊN — đọc bảng này trước khi ghi bất cứ đâu

File này định nghĩa **ý nghĩa** của từng trường. Nhưng cùng một trường có **hai tên**, tuỳ
chỗ nó đang nằm:

| Nơi | Tên dùng | Ai ghi |
|---|---|---|
| `campaign.md` — frontmatter + bảng Content | tên **ngắn** (`id`, `g1`, `folder`…) | script + người |
| `publish.json` | cấu trúc **lồng** (`posts[].publish.link`) | `register_publish` |
| `.xlsx` bản xuất | tên **dài, phẳng** (`campaign_code`, `approved_date`, `publish_link`…) | `export_excel` |

Phần lớn file này viết theo cột **bản xuất Excel** — đó là bộ tên có từ mô hình cũ và được
giữ nguyên để biểu mẫu, công thức và pivot của người dùng không phải học lại. **Ghi dữ liệu
thì ghi theo cột trái**, không phải cột phải.

| Ý nghĩa | Tên trong Markdown / `publish.json` (GHI VÀO ĐÂY) | Tên cột trong `.xlsx` |
|---|---|---|
| mã chiến dịch | `id` (frontmatter) | `campaign_code` |
| chỉ tiêu từng kênh | `kpi: {blog:, youtube:, facebook:}` | `kpi_blog_target`… |
| trụ nội dung của bài | `pillar` | `content_pillar` |
| tầng phễu | `funnel` | `funnel_stage` |
| góc tiếp cận | `angle` | `content_angle` |
| ngày qua **Cổng 1** | `g1` | `approved_date` |
| ngày qua **Cổng 2** | `g2` (gương của `posts[].review`) | — |
| ngày dự kiến đăng | `schedule` | `schedule_date` |
| ngày đã đăng | `published` | `published_date` |
| thư mục bài | `folder` | `folder_path` |
| **URL thật** sau khi đăng | `web` · `youtube` · `facebook` | `publish_link` (mỗi post một dòng) |
| trạng thái duyệt của post | `posts[].review.status` | `review_status` |
| ghi chú duyệt | `posts[].review.note` | `review_feedback` |
| ai duyệt | `posts[].review.approved_by` | — |
| link post | `posts[].publish.link` | `publish_link` |
| id nền tảng | `posts[].publish.platform_id` | — |
| id comment (Facebook) | `posts[].publish.comment_id` | — |
| chỉ tiêu | `posts[].target` | `target_view`, `target_interaction` |
| số liệu thật | `posts[].actual` | `actual_view`, `actual_reach`… |

> Nguồn sự thật của bộ cột bản xuất là `scripts/pipeline/export_excel.py`
> (`COT_CONTENT` / `COT_POST`), và có test so trực tiếp với `templates/CAMPAIGN_TEMPLATE.xlsx`.

## Bảng Content trong `campaign.md` — 15 cột đang chạy

Bảng này nằm giữa `<!-- CONTENT:BEGIN -->` và `<!-- CONTENT:END -->`. **Chỉ ghi bằng
`md_io.upsert_row`**, không bao giờ regex cả file.

| Cột | Nghĩa | Ai ghi | Giá trị hợp lệ |
|---|---|---|---|
| `content_id` | mã bài, khoá của bảng | `new_post` | `<PREFIX>-NNN` |
| `content_name` | tên bài | `new_post` | |
| `pillar` | trụ nội dung | `new_post` | phải có trong `channel.yml:pillars` |
| `angle` | góc tiếp cận | người / `new_post` | explainer · how_to · case_study · myth_vs_fact · opinion · comparison · checklist · news_analysis |
| `funnel` | tầng phễu | người | awareness · consideration · conversion · retention |
| `priority` | ưu tiên | người | high · medium · low |
| `status` | trạng thái bài | người (Cổng 1) + `register_publish` | proposed → approved → in_production → scheduled → published → archived |
| `g1` | **Cổng 1** — ngày người duyệt đề tài | **NGƯỜI** | `YYYY-MM-DD`; script không bao giờ tự điền |
| `g2` | **Cổng 2** — ngày duyệt trước khi đăng | `register_publish approve` | `YYYY-MM-DD` |
| `schedule` | ngày dự kiến đăng | người | trong `schedule_start`–`schedule_end` |
| `published` | ngày đã đăng | `register_publish set` | |
| `folder` | thư mục bài, tương đối | `new_post` | `./<content_id>_<slug>/` |
| `web` | **URL thật** bài blog | `register_publish set` | |
| `youtube` | **URL thật** video | `register_publish set` | |
| `facebook` | **URL thật** bài Facebook | `register_publish set` | |

Ô rỗng ở `g1`/`g2` **có nghĩa**: chưa qua cổng đó. Đừng điền gì cho "đỡ trống".

---

## Trường của chiến dịch (frontmatter `campaign.md` → sheet `Campaign` khi xuất)

*Ghi vào frontmatter của `campaign.md`. `export_excel` đổ chúng ra sheet `Campaign` dạng
`field | value`.* — 26 trường.

> Tám trường **bắt buộc** phải điền xong trước khi tạo bài — `new_post.py` chặn:
> `business_problem · campaign_goal · target_audience · audience_pain_points ·
> key_message · content_pillar · channels · primary_cta`.

| Trường | Kiểu | Nhóm |
|---|---|---|
| [`campaign_code`](#campaign-code) | string | Identity |
| [`name`](#name) | string | Identity |
| [`status`](#status) | category | Workflow |
| [`owner`](#owner) | string | Human |
| [`created`](#created) | date | Audit |
| [`business_problem`](#business-problem) | text | Strategic Brief |
| [`campaign_goal`](#campaign-goal) | text | Strategic Brief |
| [`content_pillar`](#content-pillar) | string | Strategic Brief |
| [`target_audience`](#target-audience) | text | Audience |
| [`audience_pain_points`](#audience-pain-points) | text | Audience |
| [`key_message`](#key-message) | text | Strategic Brief |
| [`proof_points`](#proof-points) | text | Knowledge |
| [`brand_voice_rules`](#brand-voice-rules) | text | Governance |
| [`description`](#description) | text | Strategic Brief |
| [`channels`](#channels) | text | Distribution |
| [`primary_cta`](#primary-cta) | category | Distribution |
| [`campaign_offer`](#campaign-offer) | text | Distribution |
| [`num_posts_planned`](#num-posts-planned) | integer | Planning |
| [`cadence`](#cadence) | string | Planning |
| [`schedule_start`](#schedule-start) | date | Planning |
| [`schedule_end`](#schedule-end) | date | Planning |
| [`kpi_blog_target`](#kpi-blog-target) | integer | Measurement |
| [`kpi_youtube_target`](#kpi-youtube-target) | integer | Measurement |
| [`kpi_fb_target`](#kpi-fb-target) | integer | Measurement |
| [`budget`](#budget) | number | Budget |
| [`actual_spend`](#actual-spend) | number | Budget |

### `campaign_code`

**Kiểu** `string` · **Nhóm** Identity · **Sheet** Campaign

Mã campaign duy nhất, ổn định theo thời gian và dùng để liên kết Content/Post.

> **Luật cho agent:** Không tự đổi mã; dùng đúng mã có sẵn khi tạo content và post.

*Ví dụ:* `01_Tobi_Posts`

### `name`

**Kiểu** `string` · **Nhóm** Identity · **Sheet** Campaign

Tên dễ đọc của campaign.

> **Luật cho agent:** Dùng để hiểu bối cảnh; không suy diễn mục tiêu chỉ từ tên.

*Ví dụ:* `AI Agent nhap mon cho nguoi lam Data`

### `status`

**Kiểu** `category` · **Nhóm** Workflow · **Sheet** Campaign

Trạng thái vận hành campaign.

**Giá trị hợp lệ:** `proposed` · `active` · `paused` · `done` · `archived`

> **Luật cho agent:** Chỉ tạo/lập lịch nội dung khi status là active; dừng tạo khi paused, done hoặc archived.

*Ví dụ:* `active`

### `owner`

**Kiểu** `string` · **Nhóm** Human · **Sheet** Campaign

Người chịu trách nhiệm campaign.

> **Luật cho agent:** Gán người này làm đầu mối khi thiếu quyết định hoặc cần phê duyệt ở cấp campaign.

*Ví dụ:* `Duc Nguyen`

### `created`

**Kiểu** `date` · **Nhóm** Audit · **Sheet** Campaign

Ngày tạo campaign.

> **Luật cho agent:** Chỉ dùng để audit và sắp xếp, không dùng làm ngày xuất bản.

*Ví dụ:* `2026-06-21`

### `business_problem`

**Kiểu** `text` · **Nhóm** Strategic Brief · **Sheet** Campaign

Vấn đề kinh doanh/truyền thông mà campaign cần giải quyết.

> **Luật cho agent:** Bắt đầu lập luận từ vấn đề này; mỗi content phải giải quyết hoặc làm rõ một phần vấn đề.

*Ví dụ:* `Nguoi lam Data thay AI Agent qua ky thuat va chua thay cach bat dau`

### `campaign_goal`

**Kiểu** `text` · **Nhóm** Strategic Brief · **Sheet** Campaign

Kết quả truyền thông hoặc kinh doanh mong muốn của toàn campaign.

> **Luật cho agent:** Đánh giá ý tưởng theo mức đóng góp cho goal, không chỉ theo độ mới hoặc khả năng viral.

*Ví dụ:* `Xay dung Học cung Tobi thanh nguon chia se AI Agent dang tin cay`

### `content_pillar`

**Kiểu** `string` · **Nhóm** Strategic Brief · **Sheet** Campaign

Trụ nội dung chung; là phạm vi chủ đề cấp cao.

> **Luật cho agent:** Dùng để tạo topic cluster đa dạng nhưng không đi lệch phạm vi campaign.

*Ví dụ:* `AI Agent`

### `target_audience`

**Kiểu** `text` · **Nhóm** Audience · **Sheet** Campaign

Nhóm đối tượng mục tiêu của campaign.

> **Luật cho agent:** Kế thừa vào audience_profile ở Content và điều chỉnh theo từng chủ đề nếu cần.

*Ví dụ:* `Senior Data Analyst, BI Developer, Data Engineer`

### `audience_pain_points`

**Kiểu** `text` · **Nhóm** Audience · **Sheet** Campaign

Các nỗi đau, rào cản, niềm tin sai hoặc câu hỏi của người xem.

> **Luật cho agent:** Chọn ít nhất một pain point cụ thể cho mỗi Content; không cố gắng giải quyết tất cả trong một bài.

*Ví dụ:* `So phai biet lap trinh; khong biet use case phu hop`

### `key_message`

**Kiểu** `text` · **Nhóm** Strategic Brief · **Sheet** Campaign

Thông điệp cốt lõi cần được lặp lại nhất quán qua campaign.

> **Luật cho agent:** Bảo toàn ý nghĩa; diễn đạt mới theo từng góc khai thác, không lặp nguyên câu một cách máy móc.

*Ví dụ:* `Agent la doi tho AI co viec ro rang`

### `proof_points`

**Kiểu** `text` · **Nhóm** Knowledge · **Sheet** Campaign

Bằng chứng, demo, case study hoặc tài liệu được phép dùng.

> **Luật cho agent:** Chỉ tạo claim khi có proof point hoặc nguồn đáng tin cậy; ghi nhận nhu cầu nghiên cứu nếu thiếu bằng chứng.

*Ví dụ:* `Vi du quy trinh kiem tra chat luong du lieu`

### `brand_voice_rules`

**Kiểu** `text` · **Nhóm** Governance · **Sheet** Campaign

Quy tắc giọng điệu, ngôn ngữ và các claim cần tránh.

> **Luật cho agent:** Phải áp dụng cho mọi output; ưu tiên rõ ràng, thực chiến và giải thích jargon.

*Ví dụ:* `Than thien, binh tinh, tranh hype va claim AI thay the analyst`

### `description`

**Kiểu** `text` · **Nhóm** Strategic Brief · **Sheet** Campaign

Mô tả phạm vi và câu chuyện tổng quan campaign.

> **Luật cho agent:** Dùng để kiểm tra ý tưởng mới có thuộc campaign hay không.

*Ví dụ:* `Series nhap mon giup nguoi lam Data hieu AI Agent`

### `channels`

**Kiểu** `text` · **Nhóm** Distribution · **Sheet** Campaign

Các kênh phân phối được phép trong campaign.

> **Luật cho agent:** Chỉ tạo Post cho các channel nằm trong danh sách này, trừ khi có chỉ định mới.

*Ví dụ:* `Web Blog, YouTube, Facebook`

### `primary_cta`

**Kiểu** `category` · **Nhóm** Distribution · **Sheet** Campaign

Mục tiêu CTA chính cấp campaign; câu CTA cụ thể tạo ở Post.

**Giá trị hợp lệ:** `awareness` · `engagement` · `traffic` · `lead_generation` · `conversion` · `community` · `retention`

> **Luật cho agent:** Dùng để chọn post_role và CTA; không bắt buộc mọi post phải dùng đúng một câu CTA.

*Ví dụ:* `awareness`

### `campaign_offer`

**Kiểu** `text` · **Nhóm** Distribution · **Sheet** Campaign

Giá trị/offer mà audience nhận được khi thực hiện CTA.

> **Luật cho agent:** Chỉ nhắc offer khi phù hợp post_role và đúng claim đã được phê duyệt.

*Ví dụ:* `Free AI Agent Starter Roadmap`

### `num_posts_planned`

**Kiểu** `integer` · **Nhóm** Planning · **Sheet** Campaign

Số content atom hoặc đầu ra dự kiến theo quy ước campaign.

> **Luật cho agent:** Dùng để cân đối kế hoạch; không nhầm số Content gốc với số Post đa kênh.

*Ví dụ:* `30`

### `cadence`

**Kiểu** `string` · **Nhóm** Planning · **Sheet** Campaign

Nhịp xuất bản dự kiến.

> **Luật cho agent:** Dùng để phân bổ schedule_date, tránh dồn nhiều post cùng ngày nếu không có chủ đích.

*Ví dụ:* `2 bai/tuan`

### `schedule_start`

**Kiểu** `date` · **Nhóm** Planning · **Sheet** Campaign

Ngày bắt đầu khoảng xuất bản.

> **Luật cho agent:** Không lập lịch trước ngày này trừ khi có approval ngoại lệ.

*Ví dụ:* `2026-06-25`

### `schedule_end`

**Kiểu** `date` · **Nhóm** Planning · **Sheet** Campaign

Ngày kết thúc khoảng xuất bản.

> **Luật cho agent:** Ưu tiên hoàn thành Content và Post trong khoảng ngày này.

*Ví dụ:* `2026-07-02`

### `kpi_blog_target`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Campaign

Mục tiêu view mỗi bài blog.

> **Luật cho agent:** Dùng làm benchmark khi đánh giá Post dạng blog, không dùng như claim trong nội dung.

*Ví dụ:* `500`

### `kpi_youtube_target`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Campaign

Mục tiêu view mỗi video YouTube.

> **Luật cho agent:** Dùng làm benchmark cho Post YouTube.

*Ví dụ:* `200`

### `kpi_fb_target`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Campaign

Mục tiêu reaction mỗi Facebook Post.

> **Luật cho agent:** Dùng làm benchmark cho Post Facebook.

*Ví dụ:* `30`

### `budget`

**Kiểu** `number` · **Nhóm** Budget · **Sheet** Campaign

Ngân sách kế hoạch theo VND.

> **Luật cho agent:** Không tự đề xuất chi tiêu hoặc claim có quảng cáo nếu budget bằng 0/trống.

*Ví dụ:* `0`

### `actual_spend`

**Kiểu** `number` · **Nhóm** Budget · **Sheet** Campaign

Chi phí thực tế đã ghi nhận theo VND.

> **Luật cho agent:** Chỉ dùng để phân tích sau; không tự ghi đè.

*Ví dụ:* `0`

---

## Sheet `Content`

*bảng, một dòng = một content atom* — 23 trường.

| Trường | Kiểu | Nhóm |
|---|---|---|
| [`content_id`](#content-id) | string | Identity |
| [`content_name`](#content-name) | string | Identity |
| [`content_pillar`](#content-pillar) | category | Classification |
| [`funnel_stage`](#funnel-stage) | category | Classification |
| [`content_angle`](#content-angle) | category | Classification |
| [`priority`](#priority) | category | Classification |
| [`content_goal`](#content-goal) | text | Strategy |
| [`audience_profile`](#audience-profile) | text | Strategy |
| [`core_brief`](#core-brief) | text | Strategy |
| [`key_sources`](#key-sources) | text | Knowledge |
| [`target_keyword`](#target-keyword) | string | SEO |
| [`creative_direction`](#creative-direction) | text | Creativity |
| [`constraints`](#constraints) | text | Governance |
| [`content_relationship`](#content-relationship) | text | Series |
| [`audio`](#audio) | category | Asset Planning |
| [`video`](#video) | category | Asset Planning |
| [`short`](#short) | category | Asset Planning |
| [`status`](#status) | category | Workflow |
| [`approved_date`](#approved-date) | date | Human |
| [`schedule_date`](#schedule-date) | date | Planning |
| [`published_date`](#published-date) | date | Publishing |
| [`folder_path`](#folder-path) | string | Asset |
| [`notes`](#notes) | text | Operations |

### `content_id`

**Kiểu** `string` · **Nhóm** Identity · **Sheet** Content

Mã duy nhất của một content gốc; một Content có thể sinh nhiều Post.

> **Luật cho agent:** Không đổi sau khi tạo. Dùng mã này trong toàn bộ post, asset, liên kết series và báo cáo.

*Ví dụ:* `TOBI-001`

### `content_name`

**Kiểu** `string` · **Nhóm** Identity · **Sheet** Content

Tên làm việc mô tả rõ chủ đề và lời hứa giá trị của content.

> **Luật cho agent:** Tạo tên cụ thể, hướng người xem, không dùng tiêu đề mơ hồ; có thể khác tiêu đề cuối của Post.

*Ví dụ:* `AI Agent la gi voi nguoi lam Data`

### `content_pillar`

**Kiểu** `category` · **Nhóm** Classification · **Sheet** Content

Nhóm chủ đề chuẩn để phân tích cơ cấu nội dung.

**Giá trị hợp lệ:** `01_fundamentals` · `02_tool_guides` · `03_ai_agent` · `04_use_cases` · `05_data_quality` · `06_productivity`

> **Luật cho agent:** Từ nội dung từ campaign_pillar chung xây dựng các nhóm chi tiết hơn cho từng content gọi là content_pillar. Chọn đúng một nhóm gần nhất thành drop-down (nên trao đổi và chốt với user trước khi thực thi mass production).

*Ví dụ:* `03_ai_agent`

### `funnel_stage`

**Kiểu** `category` · **Nhóm** Classification · **Sheet** Content

Giai đoạn trong hành trình audience mà Content phục vụ.

**Giá trị hợp lệ:** `awareness` · `consideration` · `conversion` · `retention`

> **Luật cho agent:** Chọn theo mức sẵn sàng hiện tại của audience, không theo mục tiêu nội bộ của đội marketing.

*Ví dụ:* `awareness`

### `content_angle`

**Kiểu** `category` · **Nhóm** Classification · **Sheet** Content

Kiểu triển khai giúp một topic có góc kể mới và đa dạng.

**Giá trị hợp lệ:** `explainer` · `how_to` · `case_study` · `myth_vs_fact` · `opinion` · `comparison` · `checklist` · `news_analysis`

> **Luật cho agent:** Chọn một angle rõ ràng; đối chiếu content_relationship để tránh lặp angle trong cùng series.

*Ví dụ:* `explainer`

### `priority`

**Kiểu** `category` · **Nhóm** Classification · **Sheet** Content

Độ ưu tiên sản xuất dựa trên giá trị chiến lược và deadline.

**Giá trị hợp lệ:** `high` · `medium` · `low`

> **Luật cho agent:** High: tạo trước; medium: theo backlog; low: làm sau cùng.

*Ví dụ:* `high`

### `content_goal`

**Kiểu** `text` · **Nhóm** Strategy · **Sheet** Content

Kết quả hành vi hoặc nhận thức cụ thể mong muốn từ Content.

> **Luật cho agent:** Kế thừa từ campaign_goal ở campaign và làm rõ hơn cho content. Viết một mục tiêu có thể quan sát; dùng nó để chọn thông điệp, cấu trúc và post_role.

*Ví dụ:* `Nguoi xem hieu khi nao nen dung AI Agent`

### `audience_profile`

**Kiểu** `text` · **Nhóm** Strategy · **Sheet** Content

Nhóm người xem cụ thể, trình độ, pain point và bối cảnh của riêng Content.

> **Luật cho agent:** Kế thừa từ target_audience và audience_pain_points từ campaign nhưng thu hẹp cho chủ đề; chọn ví dụ phù hợp trực tiếp với nhóm này và làm rõ để tạo content chuẩn.

*Ví dụ:* `BI Developer moi tim hieu AI Agent, so can lap trinh`

### `core_brief`

**Kiểu** `text` · **Nhóm** Strategy · **Sheet** Content

Nguồn sự thật của Content: vấn đề, insight, thông điệp, luận điểm, phản biện và CTA lõi.

> **Luật cho agent:** Trước khi tạo content, tóm tắt brief bằng một câu; bảo toàn thông điệp nhưng chuyển thể khác nhau cho từng Post.

*Ví dụ:* `Agent khong phai chatbot; no thuc hien quy trinh co vai tro va du lieu ro rang`

### `key_sources`

**Kiểu** `text` · **Nhóm** Knowledge · **Sheet** Content

Nguồn, fact, số liệu, tài liệu tham chiếu và ví dụ được phép dùng.

> **Luật cho agent:** Kiểm tra nguồn trước khi dùng; tách fact đã xác minh khỏi giả định; không bịa số liệu hay case study. Đảm bảo đồng bộ với proof_points từ campaign.

*Ví dụ:* `Tai lieu Anthropic; demo kiem tra data quality`

### `target_keyword`

**Kiểu** `string` · **Nhóm** SEO · **Sheet** Content

Từ khóa/cụm truy vấn chính mà Content cần đáp ứng.

> **Luật cho agent:** Chọn một keyword chính có ý định phù hợp; dùng tự nhiên trong outline, tiêu đề và post liên quan, không nhồi từ khóa. Các keyword này cũng phải đồng nhất với key_message tổng quát của campaign

*Ví dụ:* `AI Agent la gi cho Data Analyst`

### `creative_direction`

**Kiểu** `text` · **Nhóm** Creativity · **Sheet** Content

Hướng sáng tạo: cảm xúc, cấu trúc, phép so sánh, nhịp kể và điều cần thử nghiệm.

> **Luật cho agent:** Tạo ít nhất 3 hướng/góc khác nhau, chấm theo audience + goal + brand voice, rồi chọn phương án mạnh nhất và ghi lý do.

*Ví dụ:* `Mo dau bang tinh huong bao cao loi; giai thich bang vi du doi tho AI`

### `constraints`

**Kiểu** `text` · **Nhóm** Governance · **Sheet** Content

Các giới hạn bắt buộc: brand voice, claim cấm, pháp lý, bản quyền, dữ liệu nhạy cảm và policy.

> **Luật cho agent:** Đọc trước khi tạo nội dung content; nếu yêu cầu mâu thuẫn hoặc thiếu quyền sử dụng, đánh dấu blocked thay vì suy đoán.

*Ví dụ:* `Khong hype; khong claim AI thay the analyst; chi dung asset co quyen`

### `content_relationship`

**Kiểu** `text` · **Nhóm** Series · **Sheet** Content

Bản đồ Content trong series: content trước/sau/liên quan, vị trí và CTA liên kết nội bộ.

> **Luật cho agent:** Dùng để tránh lặp ý, viết cầu nối hợp lý và đề xuất next content; không chèn link khi chưa có target rõ ràng.

*Ví dụ:* `series: ai_agent_basics; position: 2_of_5; previous: TOBI-001; next: TOBI-003`

### `audio`

**Kiểu** `category` · **Nhóm** Asset Planning · **Sheet** Content

Cho biết Content cần có phiên bản/audio asset hay không.

**Giá trị hợp lệ:** `yes` · `no`

> **Luật cho agent:** Nếu yes, tạo yêu cầu audio phù hợp tone/độ dài; nếu no, không tạo tài sản audio không cần thiết. Agent dựa theo hướng dẫn sử dụng công cụ được liệt kê tạo audio.

*Ví dụ:* `no`

### `video`

**Kiểu** `category` · **Nhóm** Asset Planning · **Sheet** Content

Cho biết Content cần có video dài hay không.

**Giá trị hợp lệ:** `yes` · `no`

> **Luật cho agent:** Nếu yes, lập outline, script và visual plan; nếu no, không cần tạo video.

*Ví dụ:* `yes`

### `short`

**Kiểu** `category` · **Nhóm** Asset Planning · **Sheet** Content

Cho biết Content cần có phiên bản video ngắn/short hay không.

**Giá trị hợp lệ:** `yes` · `no`

> **Luật cho agent:** Nếu yes, rút các insight độc lập có hook mạnh để tạo thành short video, không chỉ cắt ngẫu nhiên từ video dài.

*Ví dụ:* `yes`

### `status`

**Kiểu** `category` · **Nhóm** Workflow · **Sheet** Content

Trạng thái vận hành của Content gốc.

**Giá trị hợp lệ:** `proposed` · `approved` · `in_production` · `scheduled` · `published` · `archived`

> **Luật cho agent:** Chỉ tạo Post khi Content đã approved hoặc theo luồng được chủ sở hữu cho phép; cập nhật trạng thái sau từng mốc.

*Ví dụ:* `published`

### `approved_date`

**Kiểu** `date` · **Nhóm** Human · **Sheet** Content

Ngày Content được con người duyệt.

> **Luật cho agent:** Chỉ điền khi con người đã duyệt; quyết định duyệt nằm ở content.status = approved, ô này chỉ ghi NGÀY. Không tự điền thay người.

*Ví dụ:* `2026-06-24`

### `schedule_date`

**Kiểu** `date` · **Nhóm** Planning · **Sheet** Content

Ngày dự kiến xuất bản Content/đợt post chính.

> **Luật cho agent:** Đảm bảo nằm trong campaign window và phù hợp cadence; Post có thể có lịch chi tiết riêng. Lịch của content là gốc để xây dựng lịch cho post.

*Ví dụ:* `2026-06-25`

### `published_date`

**Kiểu** `date` · **Nhóm** Publishing · **Sheet** Content

Ngày Content có đầu ra chính đã xuất bản.

> **Luật cho agent:** Chỉ cập nhật theo kết quả publish thực tế, không dùng ngày dự kiến. Nếu có nhiều post của 1 content lấy ngày post đầu được đăng tải.

*Ví dụ:* `2026-06-25`

### `folder_path`

**Kiểu** `string` · **Nhóm** Asset · **Sheet** Content

Đường dẫn thư mục chứa brief, asset, bản nháp và file cuối.

> **Luật cho agent:** Lưu asset mới đúng folder; Post trỏ về asset trong folder này thay vì nhân bản đường dẫn tùy tiện. Đảm bảo 1 content chỉ có 1 folder chứa toàn bộ asset cho tất cả post.

*Ví dụ:* `assets/TOBI-001_ai-agent-la-gi`

### `notes`

**Kiểu** `text` · **Nhóm** Operations · **Sheet** Content

Ghi chú vận hành bổ sung chưa phù hợp với các trường có cấu trúc khác.

> **Luật cho agent:** Chỉ ghi thông tin tạm thời/bối cảnh; không dùng thay cho constraints, review_feedback hay key_sources.

*Ví dụ:* `Can xin phep dung logo cong cu`

---

## Sheet `Post`

*bảng, một dòng = một đầu ra cho MỘT kênh × format* — 26 trường.

| Trường | Kiểu | Nhóm |
|---|---|---|
| [`post_id`](#post-id) | string | Identity |
| [`content_id`](#content-id) | string | Relationship |
| [`channel`](#channel) | category | Channel |
| [`post_format`](#post-format) | category | Channel |
| [`post_role`](#post-role) | category | Strategy |
| [`post_content`](#post-content) | text | Creation |
| [`quality_check`](#quality-check) | category | Governance |
| [`agent_status`](#agent-status) | category | Agent |
| [`review_status`](#review-status) | category | Human |
| [`review_feedback`](#review-feedback) | text | Human |
| [`post_status`](#post-status) | category | Workflow |
| [`publish_plan`](#publish-plan) | text | Publishing |
| [`publish_status`](#publish-status) | category | Publishing |
| [`publish_link`](#publish-link) | string | Publishing |
| [`target_view`](#target-view) | integer | Measurement |
| [`target_interaction`](#target-interaction) | integer | Measurement |
| [`updated_at`](#updated-at) | datetime | Audit |
| [`asset_ref`](#asset-ref) | string | Asset |
| [`actual_view`](#actual-view) | integer | Measurement |
| [`actual_interaction`](#actual-interaction) | integer | Measurement |
| [`actual_reaction`](#actual-reaction) | integer | Measurement |
| [`actual_comment`](#actual-comment) | integer | Measurement |
| [`actual_share`](#actual-share) | integer | Measurement |
| [`actual_click`](#actual-click) | integer | Measurement |
| [`actual_reach`](#actual-reach) | integer | Measurement |
| [`metric_updated_at`](#metric-updated-at) | datetime | Audit |

### `post_id`

**Kiểu** `string` · **Nhóm** Identity · **Sheet** Post

Mã duy nhất của một đầu ra đăng đa kênh.

> **Luật cho agent:** Không đổi sau khi tạo; một Post thuộc đúng một Content và một platform/format.

*Ví dụ:* `PST-2026-015`

### `content_id`

**Kiểu** `string` · **Nhóm** Relationship · **Sheet** Post

Mã Content gốc mà Post chuyển thể từ đó.

> **Luật cho agent:** Bắt buộc dùng Content đã tồn tại; đọc core_brief, constraints và creative_direction trước khi tạo post.

*Ví dụ:* `TOBI-001`

### `channel`

**Kiểu** `category` · **Nhóm** Channel · **Sheet** Post

Nền tảng/kênh đăng của Post.

**Giá trị hợp lệ:** `web_blog` · `youtube` · `facebook` · `linkedin` · `tiktok`

> **Luật cho agent:** Chọn một channel từ dropdown và chỉ chọn channel được phép trong Campaign.

*Ví dụ:* `youtube`

### `post_format`

**Kiểu** `category` · **Nhóm** Channel · **Sheet** Post

Định dạng cụ thể trên channel.

**Giá trị hợp lệ:** `blog_article` · `youtube_video` · `youtube_short` · `facebook_post` · `carousel` · `infographic` · `reel`

> **Luật cho agent:** Chọn format phù hợp channel; điều chỉnh độ dài, cấu trúc và CTA theo format thay vì sao chép y nguyên.

*Ví dụ:* `youtube_short`

### `post_role`

**Kiểu** `category` · **Nhóm** Strategy · **Sheet** Post

Vai trò Post trong funnel hoặc chuỗi nội dung.

**Giá trị hợp lệ:** `discovery` · `education` · `nurture` · `conversion` · `community` · `retention`

> **Luật cho agent:** Dùng role để quyết định hook, độ sâu, CTA và internal linking; mỗi post chỉ chọn một vai trò chính.

*Ví dụ:* `discovery`

### `post_content`

**Kiểu** `text` · **Nhóm** Creation · **Sheet** Post

Nội dung của Post — lưu dưới dạng ANCHOR trỏ tới đúng đoạn trong content.md của Content (1 content = 1 file .md chứa text của MỌI kênh).

> **Luật cho agent:** Ghi anchor dạng 'post:<post_format>', thêm '#2' nếu cùng một Content có nhiều Post trùng format. KHÔNG dán nội dung dài vào ô Excel — text thật nằm ở <folder_path>/content.md dưới heading '## <anchor>'. Tạo phiên bản native cho channel: bám core_brief nhưng đổi cấu trúc, hook và CTA theo format, không bê nguyên văn.

*Ví dụ:* `post:facebook_post#2`

### `quality_check`

**Kiểu** `category` · **Nhóm** Governance · **Sheet** Post

Kết quả kiểm tra fact, brand safety, quyền sử dụng và quy định nền tảng.

**Giá trị hợp lệ:** `pending` · `passed` · `failed` · `needs_review`

> **Luật cho agent:** Tự kiểm tra post content dạng nội dung text có trong asset trước khi gửi human review; chọn needs_review/failed khi còn nghi ngờ thay vì tự xác nhận passed.

*Ví dụ:* `passed`

### `agent_status`

**Kiểu** `category` · **Nhóm** Agent · **Sheet** Post

Trạng thái agent tạo, sửa hoặc tự QA Post.

**Giá trị hợp lệ:** `not_started` · `generating` · `ai_qa_passed` · `ai_qa_failed` · `blocked` · `completed`

> **Luật cho agent:** Cập nhật theo công việc thực tế; khi ai_qa_failed phải nêu lỗi ở review_feedback hoặc notes liên quan.

*Ví dụ:* `ai_qa_passed`

### `review_status`

**Kiểu** `category` · **Nhóm** Human · **Sheet** Post

Quyết định/phản hồi human-in-the-loop đối với Post.

**Giá trị hợp lệ:** `not_requested` · `pending` · `changes_requested` · `approved` · `rejected`

> **Luật cho agent:** Không tự chuyển thành approved; nếu changes_requested, sửa đúng feedback rồi gửi lại review.

*Ví dụ:* `pending`

### `review_feedback`

**Kiểu** `text` · **Nhóm** Human · **Sheet** Post

Phản hồi cụ thể của người duyệt và yêu cầu chỉnh sửa.

> **Luật cho agent:** Đọc từng yêu cầu, cập nhật Post có liên quan và tóm tắt thay đổi; không xóa feedback cũ nếu chưa lưu lịch sử.

*Ví dụ:* `Rut ngan hook; them vi du ke toan`

### `post_status`

**Kiểu** `category` · **Nhóm** Workflow · **Sheet** Post

Trạng thái vận hành tổng từ tạo đến đo hiệu quả.

**Giá trị hợp lệ:** `not_created` · `generating` · `ai_qa` · `human_review` · `revision` · `approved` · `scheduled` · `published` · `measuring` · `completed` · `publish_failed` · `cancelled`

> **Luật cho agent:** Tuân thủ luồng; chỉ scheduled/published khi review_status approved và quality_check passed.

*Ví dụ:* `scheduled`

### `publish_plan`

**Kiểu** `text` · **Nhóm** Publishing · **Sheet** Post

Kế hoạch đăng: thời điểm, timezone, người chịu trách nhiệm và ghi chú platform.

> **Luật cho agent:** Lập lịch phù hợp campaign cadence; không ghi published tại đây vì đây là kế hoạch.

*Ví dụ:* `2026-08-05 19:30 ICT; owner: content_team`

### `publish_status`

**Kiểu** `category` · **Nhóm** Publishing · **Sheet** Post

Kết quả trạng thái gửi lên nền tảng.

**Giá trị hợp lệ:** `not_scheduled` · `scheduled` · `publishing` · `published` · `failed`

> **Luật cho agent:** Cập nhật từ kết quả thực tế; nếu failed giữ lỗi ở notes/operational log và không đánh dấu published.

*Ví dụ:* `scheduled`

### `publish_link`

**Kiểu** `string` · **Nhóm** Publishing · **Sheet** Post

URL hoặc ID của Post sau khi đăng.

> **Luật cho agent:** Chỉ điền sau khi nền tảng trả kết quả publish; dùng link để làm internal linking cho content sau.

*Ví dụ:* `https://youtube.com/...`

### `target_view`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Mục tiêu lượt xem của riêng Post.

> **Luật cho agent:** Kế thừa benchmark Campaign nếu phù hợp; không dùng số này trong nội dung public.

*Ví dụ:* `200`

### `target_interaction`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Mục tiêu tương tác phù hợp kênh: reaction, comment, share hoặc engagement.

> **Luật cho agent:** Chọn metric phù hợp format/channel và dùng để đánh giá sau khi đăng.

*Ví dụ:* `30`

### `updated_at`

**Kiểu** `datetime` · **Nhóm** Audit · **Sheet** Post

Thời điểm cập nhật gần nhất của Post.

> **Luật cho agent:** Hệ thống hoặc người vận hành cập nhật; không dùng làm published date.

*Ví dụ:* `2026-08-06 08:00`

### `asset_ref`

**Kiểu** `string` · **Nhóm** Asset · **Sheet** Post

Danh sách file asset (ảnh/audio/video) mà Post này dùng, đường dẫn tương đối trong folder_path của Content.

> **Luật cho agent:** Để TRỐNG nếu dùng asset mặc định theo quy ước channel × post_format (youtube_video→video.mp4+thumbnail.png; youtube_short/reel→short.mp4; facebook_post/blog_article→thumbnail.png). Chỉ điền khi khác mặc định. Không ghi đường dẫn tuyệt đối; thư mục folder_path CHÍNH LÀ kho asset, không có sổ asset riêng.

*Ví dụ:* `cover_fb_nhac_lai.png`

### `actual_view`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Lượt xem/đọc thực tế của Post, cập nhật mới nhất.

> **Luật cho agent:** GHI ĐÈ trực tiếp mỗi lần lấy số — file không lưu lịch sử đo. Chỉ ghi số nền tảng trả về; ô rỗng = chưa lấy được, KHÔNG điền 0 thay cho thiếu. Đối chiếu với target_view.

*Ví dụ:* `1240`

### `actual_interaction`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Tổng tương tác thực tế (reaction + comment + share).

> **Luật cho agent:** Ghi đè như trên; đối chiếu với target_interaction để đánh giá Post.

*Ví dụ:* `107`

### `actual_reaction`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Số reaction/like thực tế.

> **Luật cho agent:** Ghi đè; không ước lượng, không suy diễn.

*Ví dụ:* `86`

### `actual_comment`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Số bình luận thực tế.

> **Luật cho agent:** Ghi đè; không ước lượng.

*Ví dụ:* `12`

### `actual_share`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Số chia sẻ thực tế.

> **Luật cho agent:** Ghi đè; không ước lượng.

*Ví dụ:* `9`

### `actual_click`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Số click vào link, nếu nền tảng có.

> **Luật cho agent:** Để TRỐNG nếu nền tảng không cung cấp — không quy đổi từ chỉ số khác.

*Ví dụ:* `40`

### `actual_reach`

**Kiểu** `integer` · **Nhóm** Measurement · **Sheet** Post

Số người tiếp cận, nếu nền tảng có.

> **Luật cho agent:** Để TRỐNG nếu nền tảng không cung cấp.

*Ví dụ:* `5300`

### `metric_updated_at`

**Kiểu** `datetime` · **Nhóm** Audit · **Sheet** Post

Thời điểm lấy số liệu gần nhất cho Post này.

> **Luật cho agent:** Cập nhật cùng lúc với các cột actual_*; số liệu không kèm mốc thời gian là số liệu không đọc được. Khác updated_at (sửa nội dung) và published_date.

*Ví dụ:* `2026-07-30 09:00`
