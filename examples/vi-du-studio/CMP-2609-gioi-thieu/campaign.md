---
schema: campaign/1
id: CMP-2609-gioi-thieu
channel: vi-du-studio
id_prefix: GTX
name: Giới thiệu xưởng nội dung
status: active
owner: Người phụ trách (ví dụ)
created: '2026-09-04'
business_problem: Người làm data thấy 'agent viết nội dung' là trò vui, không phải quy trình sản xuất
  — nên không ai dám giao việc thật cho nó
campaign_goal: 50 người clone repo và chạy được bài đầu tiên tới lúc đăng, trong 30 ngày
description: Ba bài kể vì sao một xưởng nội dung chạy bằng agent cần cổng duyệt của người, chứ không cần
  thêm mô hình mạnh hơn
content_pillar: ai-agent
target_audience: Người làm data/BI ở doanh nghiệp Việt, 2-8 năm, đã dùng AI lẻ tẻ nhưng chưa đưa vào quy
  trình
audience_pain_points: Bài do AI viết nghe trôi chảy mà rỗng; sửa lại còn lâu hơn tự viết; không biết chỗ
  nào được phép để máy tự quyết
key_message: Cái làm nội dung dùng được không phải mô hình mạnh hơn, mà là chỗ NGƯỜI đặt tay vào
proof_points: 23 cổng kiểm chạy bằng số trên bài thật; 120 test; một bài đã đăng đủ 3 kênh có URL kiểm
  được
brand_voice_rules: Câu ngắn, số có nguồn, nói thẳng khi thứ gì chưa dùng được
channels:
- web_blog
- youtube
- facebook
primary_cta: traffic
campaign_offer: Repo MIT, clone là chạy
num_posts_planned: 3
cadence: weekly
schedule_start: '2026-09-07'
schedule_end: '2026-09-28'
kpi:
  blog: 500
  youtube: 200
  facebook: 40
budget: null
actual_spend: null
---
# Hồ sơ chiến dịch — Giới thiệu xưởng nội dung

> **ĐÂY LÀ VÍ DỤ ĐÃ ĐIỀN.** Chiến dịch thật của bạn sống ở STATION, không nằm trong repo.
> File này để bạn thấy một `campaign.md` điền xong trông thế nào — `new_post.py` **chặn**
> khi tám trường bắt buộc còn nguyên chữ mẫu, nên đây cũng là mức tối thiểu phải đạt.
>
> `new_campaign.py` copy mẫu vào thư mục chiến dịch, giữ nguyên tên `campaign.md`.
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

- **Vấn đề cần giải**: người làm data nhìn "agent viết nội dung" như trò vui cuối tuần, nên
  không ai giao cho nó việc thật. Không phải vì kết quả tệ — mà vì không ai chỉ được chỗ nào
  máy được tự quyết và chỗ nào người phải đặt tay vào.
- **Vì sao là bây giờ**: mô hình đã đủ tốt để viết trôi chảy từ hơn một năm nay, và đúng vì
  vậy mà vấn đề lộ ra: bài trôi chảy nhưng rỗng vẫn trôi qua mọi khâu, không gì chặn lại.
- **Trụ nội dung phục vụ + lý do chọn**: `ai-agent` — chọn trụ này chứ không phải `career` vì
  đây là câu chuyện quy trình, không phải câu chuyện nghề nghiệp.
- **Điều kiện coi là thành công**: có người lạ clone repo, chạy tới bước đăng thật, và quay
  lại kể họ vướng ở đâu. Một người làm được đáng giá hơn năm trăm lượt xem.
- **Điều campaign này KHÔNG nhằm làm**: không so sánh mô hình, không dạy prompt, không hứa
  tự động hoá hoàn toàn.


> Bản rút gọn của mục này nằm ở `Campaign.business_problem` và `Campaign.campaign_goal`.
> Ở đây viết đủ dài để người mới đọc là hiểu; frontmatter chỉ giữ bản một câu.

## 2. Đối tượng

- **Persona chính**: "Hà, BI lead" — 6 năm làm báo cáo, đang phải viết thêm nội dung
  cho trang kỹ thuật của công ty mà không có ai chuyên trách.
- **Một ngày của họ**: họp và sửa báo cáo tới chiều; đọc nội dung kỹ thuật lúc 21–23h trên
  điện thoại, và trên máy vào sáng thứ Bảy khi định làm thử.
- **Nỗi đau**: giao cho AI thì ra bài nghe hay mà rỗng, sửa lại lâu hơn tự viết; giao cho
  người thì không có người.
- **Rào cản/niềm tin sai cần gỡ**: "chờ mô hình sau mạnh hơn là xong". Không xong — mô hình
  mạnh hơn viết trôi chảy hơn, và bài rỗng càng khó phát hiện hơn.
- **Họ đã tin gì rồi**: họ đã tin AI viết được. Không cần thuyết phục lại chuyện đó.
- **Persona phụ**: người làm marketing một mình ở công ty nhỏ, cần quy trình chứ không cần công cụ.


## 3. Thông điệp & bằng chứng

- **Thông điệp lõi**: cái làm nội dung dùng được không phải mô hình mạnh hơn, mà là chỗ
  NGƯỜI đặt tay vào.
- **Bằng chứng được phép dùng**: 23 cổng kiểm chạy bằng số trên bài thật (xem `gates.json`);
  120 test của chính repo; một bài đã đăng đủ ba kênh, URL kiểm được.
- **Claim bị cấm**: "tự động hoá 100%", "thay thế người viết", bất kỳ con số hiệu quả nào
  không đo được từ chính repo này.
- **Giọng**: thẳng, có chính kiến, không hoa mỹ. Câu đúng giọng: *"Bài trôi chảy mà rỗng vẫn
  đi qua mọi khâu — đó mới là vấn đề."* Chi tiết ở `profile.md` của kênh.
- **CTA chính**: traffic — đưa người về repo.
- **Offer**: repo MIT, clone là chạy.


## 4. Phạm vi nội dung

### Trụ nội dung
| Trụ | Tỷ trọng | Chủ đề bao gồm | Dành cho persona |
|---|---|---|---|
| Quy trình có cổng người | 50% | hai cổng duyệt, vì sao máy không tự đặt `approved` | Hà, BI lead |
| Kiểm bằng số | 30% | 23 cổng, "thiếu" không bao giờ là "xanh" | Hà, BI lead |
| Markdown là nguồn | 20% | vì sao bỏ Excel làm nguồn, Excel thành bản xuất | marketing một mình |


Giá trị hợp lệ của `content_pillar` khai ở `channel.yml:pillars` — mỗi kênh một bộ khác nhau.

### Cái KHÔNG làm
- ❌ so sánh mô hình / bảng xếp hạng benchmark
- ❌ "prompt thần thánh", mẹo vặt tách rời quy trình
- ❌ hứa hẹn con số hiệu quả không đo được từ chính repo


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
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | schedule | published | folder | web | youtube | facebook |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GTX-001 | Vì sao một xưởng nội dung chạy bằng agent vẫn cần cổng của người | ai-agent | opinion | awareness | medium | published | 2026-09-05 | 2026-09-07 | 2026-09-07 | 2026-09-07 | ./GTX-001_vi-sao-agent-can-cong-cua-nguoi/ | https://example.vn/blog/content/ai/vi-sao-agent-can-cong-cua-nguoi.html | https://youtu.be/EXAMPLE0001 | https://www.facebook.com/000000000000000/posts/111111111111111 |
| GTX-002 | Kiểm bài bằng số, không bằng cảm giác: 23 cổng làm gì | ai-agent | explainer | awareness | medium | approved | 2026-09-05 |  | 2026-09-14 |  | ./GTX-002_kiem-bang-so-khong-phai-bang-cam-giac/ |  |  |  |
| GTX-003 | Chúng tôi bỏ Excel làm nguồn sự thật — và đây là cái đã sai trước đó | ai-agent | case_study | awareness | medium | proposed |  |  | 2026-09-21 |  | ./GTX-003_vi-sao-bo-excel-lam-nguon/ |  |  |  |
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
| Blog (atlas) | người tìm kiếm, đọc kỹ | nơi lập luận đầy đủ, có nguồn | bài dài + infographic |
| YouTube | người học bằng mắt | xem quy trình chạy thật | video 6–10 phút |
| Facebook | người lướt | kéo về bài dài | bài kể chuyện + ảnh, link để ở comment |


Kênh khai ở đây phải khớp `Campaign.channels`. Post chỉ được tạo cho kênh trong danh sách này.

### Giờ đăng
Blog: bất kỳ · YouTube: 20–22h · Facebook: 8–9h và 20–21h

### Luật cross-post
- **KHÔNG** copy y nguyên giữa các kênh — format lại theo từng kênh.
- Blog → rút một lập luận đứng độc lập cho Facebook, không cắt mở bài
- Video dài → short lấy đoạn có kết luận riêng, không cắt ngẫu nhiên 60 giây đầu

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
| Bài kỹ thuật quá dài, không ai đọc hết | thời gian đọc trung bình dưới 90 giây | cắt bài 3 thành hai phần, phần sau đăng riêng |
| Người clone về nhưng vướng ở bước cài | có câu hỏi lặp lại về cùng một bước | viết lại đúng bước đó trong README, đo lại sau một tuần |
| Ba bài nghe giống nhau | cùng mở bài bằng một kiểu câu | mỗi bài một góc khác: vì sao · làm thế nào · cái đã sai |

## 8. Nhật ký quyết định

> Ghi mỗi khi chốt một điều **không suy ra được từ dữ liệu** — đổi hướng, bỏ chủ đề, đổi giọng.
> Đây là thứ bảng biểu không giữ được: **lý do**. Append, không xoá dòng cũ.

| Ngày | Quyết định | Vì sao | Ai chốt |
|---|---|---|---|
| 2026-09-04 | Bỏ Excel làm nguồn sự thật, chuyển sang Markdown | .xlsx không diff được, mở là khoá file, agent ghi đè lúc người đang mở là mất trắng | Chủ kênh |
| 2026-09-04 | Giữ nguyên bộ cột Excel khi xuất | người dùng có biểu mẫu và pivot bám vào thứ tự cột cũ | Chủ kênh |

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
| (điền khi chiến dịch chuyển `done`) | | |

---

**Chủ chiến dịch:** Người phụ trách (ví dụ) · **Rà pillar/playbook:** mỗi tháng · **Chạy `check_tree.py`:** hàng tuần và trước mỗi lần đăng
