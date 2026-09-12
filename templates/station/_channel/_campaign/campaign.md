---
schema: campaign/1
id: CMP-YYMM-slug                 # = TÊN THƯ MỤC chứa file này
channel: ten-kenh                 # = channel.yml:id của thư mục cha
id_prefix: XXX                    # content_id sẽ là XXX-001, XXX-002…
name: "Tên chiến dịch dễ đọc"
status: proposed                  # proposed → active → paused → done → archived
owner: "Người phụ trách"
created: 2026-01-01

# --- Brief chiến lược, bản MỘT CÂU. Đây là thứ xuất sang sheet Campaign.
#     Bản dài nằm ở Mục 1-3 bên dưới; đừng chép lại ở cả hai chỗ.
business_problem: "Vấn đề kinh doanh/truyền thông — KHÔNG phải chủ đề nội dung"
campaign_goal: "Kết quả mong muốn, đo được"
description: "Mô tả chiến dịch trong một câu"
content_pillar: tru-cot            # phải nằm trong channel.yml:pillars
target_audience: "Ai"
audience_pain_points: "Họ đau gì"
key_message: "Một câu lặp xuyên suốt chiến dịch"
proof_points: "Bằng chứng được phép dùng"
brand_voice_rules: "Một dòng — chi tiết ở channel.yml:brand_voice"

# --- Phân phối & kế hoạch
channels: [web_blog, youtube, facebook]   # phải ⊆ channel.yml:platforms
primary_cta: awareness            # awareness|engagement|traffic|lead_generation|conversion|community|retention
campaign_offer: ""
num_posts_planned: 1
cadence: "ad-hoc"
schedule_start: 2026-01-01
schedule_end: 2026-01-31

# --- Đo lường & ngân sách
# ⚠️ KPI phải đến từ SỐ LIỆU THẬT của bài đã đăng. Chưa có bài để so thì ĐỂ TRỐNG.
#    Ô rỗng nói "chưa biết"; số 0 nói "đo được là 0" — hai chuyện khác nhau.
kpi:
  blog:
  youtube:
  facebook:
budget:
actual_spend:

# ── CHỈ cho chiến dịch CHẠY THEO LỊCH (bản tin, series tự động). Chiến dịch viết tay thì
#    xoá cả bốn khối dưới đây đi.
#
#    `campaign_cfg.py` đọc chúng, hợp nhất với `channel.yml` + `brand.md`, rồi in ra một
#    khối JSON. `run.ps1` ghi khối đó thành bản chụp và truyền vào engine qua `-Config`.
#    PowerShell 5.1 KHÔNG đọc được YAML — đó là lý do có bước dịch này, không phải thừa.

# runtime — máy đọc. `label` và `runner` là BẮT BUỘC; thiếu thì campaign_cfg.py dừng hẳn
# (exit 2) thay vì để engine chạy tiếp với giá trị rỗng rồi ra sản phẩm sai mà không báo.
runtime:
  label:                    # tên ngắn engine dùng trong tên file log, tiêu đề
  runner:                   # tìm theo BA chỗ: thư mục này > scripts/runners/ của repo > engine của máy
  runner_args: ""           # vd "-Brand ai -Publish" · hoặc "-Buoc create-post" cho run-blog-campaign.ps1
  # prompt: prompt.txt
  # out_dir: daily-out
  # yt_playlist: ""
  # fb_text_post: false     # true = đăng thêm bài chữ riêng trên Facebook (mặc định KHÔNG)
  #
  # ── Chiến dịch blog dài kỳ (run-blog-campaign.ps1) ────────────────────────
  # SÁU bước RỜI, mỗi lượt chạy một bước:
  #   create-post ─[ Cổng 1 ]─ soan ─[ Cổng 2 ]─ build-page ─[ Cổng 3 ]─ release
  # Gộp các bước là dựng lại thứ đã bị gỡ vì nuốt cổng duyệt của người vào giữa chuỗi.
  # `dang` là TÊN CŨ của `build-page`, giữ để lệnh cũ không gãy.
  #
  # Cổng 3 bật bằng cách KHAI CỘT `g3` trong bảng Content (mẫu này đã khai sẵn).
  # Bỏ cột đó đi = tắt Cổng 3, đi thẳng từ dựng trang tới phát hành.
  #
  # ── BỐN HOOK — repo KHÔNG khoá CLI hay agent nào ──────────────────────────
  # Mỗi hook là một lệnh CỦA BẠN. Chỗ thay được: {post} thư mục bài · {cid} mã bài ·
  # {cam} thư mục chiến dịch · {web} URL bài (chỉ ở hai hook cuối).
  #
  # writer_cmd:   '<lệnh của bạn> --post "{post}"'
  #     Vào : thư mục bài (meta.json · research.md · content.md khung · prompt.txt ·
  #           phan-hoi.md nếu bị trả lại).  Ra: điền đầy content.md theo neo `## post:`.
  #     KHÔNG khai = bước `soan` báo *chờ người viết* và dừng. Fail-closed, không đoán.
  #     ⚠️ Mã thoát 0 KHÔNG đủ để tính là xong — hệ còn kiểm content.md có chữ thật không.
  #
  # audio_cmd:    '<lệnh của bạn> --post "{post}"'      # → atlas/audio.mp3, TUỲ CHỌN
  # youtube_cmd:  '<lệnh của bạn> --post "{post}"'      # in JSON có khoá `url`, TUỲ CHỌN
  # facebook_cmd: '<lệnh của bạn> --post "{post}" --web "{web}"'   # in JSON `url`, TUỲ CHỌN
  #
  # Ba hook cuối KHÔNG khai thì BỎ QUA, không phải lỗi — chiến dịch chỉ có web + ảnh +
  # post vẫn chạy trót lọt. Repo có sẵn `scripts/pipeline/fb_publish.py` làm bản tham
  # chiếu để trỏ `facebook_cmd` vào.
  #
  # Xem `templates/hooks/` để lấy script mẫu chép về sửa.
  #
  # approval_mode: batch_gate   # batch_gate = N bài một tin · per_post = mỗi bài một tin
  # approval_lo: 10             # tối đa bao nhiêu bài gom vào một tin xin duyệt
  # lookahead_days: 7           # dựng trước bao nhiêu ngày so với cột `schedule`
  #
  # Ba khoá trên TUỲ CHỌN — thiếu thì rơi về mặc định ghi ngay đây, không fail.
  # Nhưng `autonomy` thì KHÔNG khai ở đây: nó thuộc `channel.yml` và cố ý không đè được
  # từ file này (xem chú thích tại chỗ đó).

# identity — nhận diện trên video. Để TRỐNG nghĩa là dùng mặc định của template renderer;
# điền vào là ĐỔI hình ảnh đang chạy, nên chỉ điền khi cố ý.
identity: {}
  # brand_a: ""
  # brand_b: ""
  # kicker: ""
  # site: ""

# titles — CÂU CHỮ, không phải cấu hình. Chỗ này để người sửa mà không phải mở .json.
titles: {}
  # yt_prefix: ""
  # recap: "... {week} ... {range}"
  # short: "... {week}"

# theme — GHI CHÉP màu đang dùng, kèm file:dòng nơi nó nằm cứng. Không phải nguồn cấu hình
# trừ khi engine thật sự đọc khoá đó (vd video_accents -> biến môi trường).
theme: {}

hashtags: []
---

# Hồ sơ chiến dịch — {{Tên chiến dịch}}

> `new_campaign.py` copy file này vào thư mục chiến dịch, giữ nguyên tên `campaign.md`.
>
> Frontmatter = bản một câu (máy đọc, xuất Excel). Thân bài = bản dài (người đọc).
> Mục 4–6 là **chuẩn dùng chung** — giữ làm mặc định, chỉ chỉnh khi chiến dịch này khác thật.

## Bản đồ dữ liệu — cái gì sống ở đâu

Một sự thật chỉ có **một** nơi canonical. Sắp gõ lại con số đã có ở `publish.json` thì
dừng lại, trỏ sang đó.

| Thứ | Nơi canonical |
|---|---|
| Brief chiến lược, KPI, lịch (bản một câu) | frontmatter file này |
| Danh sách bài + trạng thái + hai cổng duyệt | **Mục 4b** file này |
| Brief chi tiết từng bài | `<folder>/research.md` (frontmatter) |
| Nghiên cứu, nguồn, mâu thuẫn số liệu | `<folder>/research.md` (thân bài) |
| Định danh máy đọc của bài (slug, category, hashtag) | `<folder>/meta.json` |
| Text mọi kênh | `<folder>/content.md` (neo `## post:`) |
| Từng bài đăng theo nền tảng · duyệt · link · **số liệu thật** | `<folder>/publish.json → posts[]` |
| Định nghĩa mọi trường | `knowledge/data_model/DATA_MODEL.md` |
| Vì sao làm · persona sâu · cái KHÔNG làm · playbook · rủi ro · quyết định · báo cáo | Mục 1–10 file này |


## 1. Bối cảnh — vì sao làm, vì sao lúc này

- **Vấn đề cần giải**: {{vấn đề kinh doanh/truyền thông, KHÔNG phải chủ đề nội dung}}
- **Vì sao là bây giờ**: {{sự kiện, mùa vụ, thay đổi thị trường, động thái đối thủ}}
- **Trụ nội dung phục vụ + lý do chọn**: {{pillar — vì sao trụ này chứ không phải trụ khác}}
- **Điều kiện coi là thành công**: {{1–2 câu, cụ thể tới mức cãi được}}
- **Điều campaign này KHÔNG nhằm làm**: {{chống phình phạm vi}}

> Bản rút gọn của mục này nằm ở `Campaign.business_problem` và `Campaign.campaign_goal`.
> Ở đây viết đủ dài để người mới đọc là hiểu; frontmatter chỉ giữ bản một câu.

## 2. Đối tượng

- **Persona chính**: {{tên gọi nội bộ}} — {{vai trò, thâm niên, công cụ đang dùng}}
- **Một ngày của họ**: {{bối cảnh công việc thật, họ đọc nội dung lúc nào}}
- **Nỗi đau**: {{đau thật, không phải đau giả định}}
- **Rào cản/niềm tin sai cần gỡ**: {{cái làm họ không hành động}}
- **Họ đã tin gì rồi**: {{để không giảng lại thứ họ biết}}
- **Persona phụ** (nếu có): {{...}}

## 3. Thông điệp & bằng chứng

- **Thông điệp lõi**: {{một câu, lặp xuyên suốt campaign}}
- **Bằng chứng được phép dùng**: {{demo, số liệu, case study, tài liệu — kèm nguồn}}
- **Claim bị cấm**: {{điều tuyệt đối không được nói, kể cả khi nghe hay}}
- **Giọng**: {{tính từ + ví dụ câu đúng giọng}} — chi tiết ở `output_styles/`
- **CTA chính**: {{awareness | engagement | traffic | lead_generation | conversion | community | retention}}
- **Offer** (nếu có): {{thứ người xem nhận được}}

## 4. Phạm vi nội dung

### Trụ nội dung
| Trụ | Tỷ trọng | Chủ đề bao gồm | Dành cho persona |
|---|---|---|---|
| {{Trụ 1}} | {{35%}} | {{...}} | {{...}} |
| {{Trụ 2}} | {{25%}} | {{...}} | {{...}} |

Giá trị hợp lệ của `content_pillar` khai ở `channel.yml:pillars` — mỗi kênh một bộ khác nhau.

### Cái KHÔNG làm
- ❌ {{chủ đề lệch định vị}}
- ❌ {{dạng nội dung không muốn gắn tên vào}}
- ❌ {{vùng nhạy cảm}}

> Đây là **cổng lọc ở khâu đề xuất chủ đề**. Ý tưởng rơi vào danh sách này → loại, không thương lượng.

## 4b. Bảng Content — mỗi bài một dòng

> Thay cho sheet Content của mô hình Excel cũ. `new_post.py` thêm dòng;
> **người** điền `status=approved` và `g1` (Cổng 1); `register_publish.py` cập nhật `g2`,
> `status=published` và `published`.
>
> Đây là bảng **tổng quát** để điều phối — nhìn vào biết bài nào tới đâu. Brief chi tiết
> của từng bài (mục tiêu, chân dung độc giả, core brief, nguồn, keyword) nằm ở frontmatter
> `<folder>/research.md`, không nằm ở đây: 23 cột nhét hết vào một bảng thì không ai đọc nổi.
>
> `g1` = ngày qua Cổng 1 (duyệt đề tài) · `g2` = ngày qua Cổng 2 (duyệt trước khi đăng,
> mirror của `publish.json → posts[].review`).
>
> Ba cột cuối giữ **URL THẬT** của bài đã đăng, `register_publish set` ghi vào. Đây là chỗ
> mở lại bài sau này mà không phải đi lục từng `publish.json` — và cũng là thứ `campaign.html`
> render thành nút bấm được.

<!-- CONTENT:BEGIN -->
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | g3 | schedule | published | folder | web | youtube | facebook |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
<!-- CONTENT:END -->

Giá trị hợp lệ —
`status`: proposed → approved → in_production → scheduled → published → archived ·
`angle`: explainer · how_to · case_study · myth_vs_fact · opinion · comparison · checklist · news_analysis ·
`funnel`: awareness · consideration · conversion · retention ·
`priority`: high · medium · low

## 5. Playbook phân phối

### Vai từng kênh
| Kênh | Đối tượng | Vai trò | Format mạnh nhất |
|---|---|---|---|
| {{Blog}} | {{search/SEO}} | {{authority}} | {{long-form}} |
| {{YouTube}} | {{visual learner}} | {{tutorial}} | {{video dài + short}} |
| {{Facebook}} | {{cộng đồng}} | {{reach}} | {{story-driven}} |

Kênh khai ở đây phải khớp `Campaign.channels`. Post chỉ được tạo cho kênh trong danh sách này.

### Giờ đăng
{{Kênh A: 8–10h, 16–18h · Kênh B: 12–14h, 20–22h}}

### Luật cross-post
- **KHÔNG** copy y nguyên giữa các kênh — format lại theo từng kênh.
- {{Blog → cắt thành ... }}
- {{Video dài → rút insight độc lập thành short, không cắt ngẫu nhiên}}

### Sau khi đăng
- T+0→2h: trả lời bình luận
- T+1 ngày: xem lại, ghim bình luận tốt
- T+3 ngày: đối chiếu `posts[].actual` với `posts[].target` trong `publish.json`
  (`register_publish.py metrics`) → lưu hook thắng

## 6. Quy ước file & asset

### Một content = một thư mục = một `content.md`
```
<folder_path>/
├── content.md          ← TEXT của MỌI kênh, tách bằng heading '## post:<post_format>'
├── thumbnail.png
├── audio.mp3
├── video.mp4
└── short.mp4
```

`Content.folder_path` trỏ tới thư mục này. `Post.post_content` là **anchor** trỏ vào đúng đoạn
trong `content.md` — ví dụ `post:facebook_post`. Cùng một content có nhiều post trùng format
thì thêm hậu tố: `post:facebook_post#2`.

### Asset mặc định theo kênh × format
`Post.asset_ref` **để trống** = dùng đúng bảng này. Chỉ điền khi khác mặc định.

| post_format | Asset dùng |
|---|---|
| `blog_article` | `thumbnail.png` (+ `audio.mp3` nếu `Content.audio = yes`) |
| `youtube_video` | `video.mp4` + `thumbnail.png` |
| `youtube_short` · `reel` | `short.mp4` |
| `facebook_post` | `thumbnail.png` |
| `carousel` · `infographic` | phải điền `asset_ref` — không có mặc định |

Thư mục **chính là** kho asset. Không có sổ asset riêng.
Bố cục một bài khai ở `scripts/lib/post_paths.py` — gốc là nghiên cứu/viết,
`youtube/ atlas/ facebook/` là thứ đem đăng. Không chép file giữa các thư mục kênh.

## 7. Rủi ro

| Rủi ro | Dấu hiệu sớm | Cách giảm |
|---|---|---|
| {{Content trễ}} | {{quá 2 content ở in_production}} | {{...}} |
| {{Tương tác thấp}} | {{actual_interaction < 50% target 3 bài liền}} | {{...}} |

## 8. Nhật ký quyết định

> Ghi mỗi khi chốt một điều **không suy ra được từ dữ liệu** — đổi hướng, bỏ chủ đề, đổi giọng.
> Đây là thứ bảng biểu không giữ được: **lý do**. Append, không xoá dòng cũ.

| Ngày | Quyết định | Vì sao | Ai chốt |
|---|---|---|---|
| {{YYYY-MM-DD}} | {{...}} | {{...}} | {{...}} |

## 9. Báo cáo

> Append một mục `### Báo cáo YYYY-MM-DD` mỗi lần chạy. **KHÔNG xoá mục cũ.**
>
> Vì `posts[].actual` trong `publish.json` **ghi đè** (không lưu lịch sử), chỗ này là nơi
> duy nhất giữ được diễn biến theo thời gian. Mỗi báo cáo phải chốt số tại thời điểm chạy.

<!-- BÁO CÁO APPEND BÊN DƯỚI -->

## 10. Retro

> Điền khi campaign chuyển `done`.

| Cái chạy được | Cái không chạy | Lần sau làm khác |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

---

**Chủ chiến dịch:** {{...}} · **Rà pillar/playbook:** {{định kỳ}} · **Chạy `check_tree.py`:** {{hàng tuần}}
