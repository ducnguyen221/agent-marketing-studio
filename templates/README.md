# templates/ — khuôn để dựng kênh, chiến dịch, bài

`station/` là **cây mẫu phản chiếu đúng hình dạng một trạm nội dung thật**. Mở nó ra là thấy
ngay cái gì lồng trong cái gì — không phải đọc tên file rồi tự đoán.

```
station/
├─ CHANNELS.md                    sổ kênh của cả trạm
└─ _channel/                      ← khuôn MỘT kênh   (thư mục thật mang tên kênh)
   ├─ channel.yml                 MÁY đọc: id · platforms · pillars · theme · brand · paths
   ├─ brand.md                    NGƯỜI đọc: nhận diện · giọng · chính kiến · cái KHÔNG làm
   ├─ CAMPAIGNS.md                sổ chiến dịch của kênh
   ├─ continuity.json             sổ bài đã đăng
   ├─ build-index.ps1             [kênh có web] dựng index.html + feed.xml
   ├─ send_newsletter.py          [kênh có web] gửi bản tin
   ├─ subscribe.gs                [kênh có web] Apps Script nhận đăng ký
   ├─ build_yt_desc.py            [kênh có YouTube] dựng mô tả video
   └─ _campaign/                  ← khuôn MỘT chiến dịch
      ├─ campaign.md              brief + cấu hình; `runtime:` là phần máy đọc
      ├─ prompt.txt               prompt bước CHỌN đề tài (chạy mỗi kỳ)
      ├─ run.ps1                  [chạy theo lịch] điểm vào duy nhất, 12 dòng
      └─ _content/                ← khuôn MỘT bài
         ├─ prompt.txt            prompt bước VIẾT bài này
         ├─ research.md           nghiên cứu: nguồn, ràng buộc, hướng sáng tạo
         └─ content.md            nội dung MỌI kênh, tách bằng `## post:<format>`
```

Thư mục bắt đầu bằng `_` là **khuôn**, không phải kênh/chiến dịch thật. Tên thật do
`--id` quyết định lúc tạo.

## Ba loại file, ba vai — đừng trộn

| Đuôi | Ai đọc | Ví dụ |
|---|---|---|
| `.yml` | **máy** | `channel.yml` — nguồn cấu hình duy nhất của kênh |
| `.md` | **người** (và agent đọc để hiểu) | `brand.md`, `campaign.md`, `research.md` |
| `.txt` | **model** | `prompt.txt` — đọc thô, bơm thẳng, không qua bộ dựng markdown |

Vì sao tách: một file vừa là cấu hình vừa là tài liệu thì sửa câu chữ cũng phải sợ làm hỏng
máy, và ngược lại.

## Dựng từ khuôn này

```bash
python scripts/pipeline/new_channel.py  --id <kênh> --label "…" --path ./<kênh>
python scripts/pipeline/new_campaign.py --channel <kênh> --id <slug> --name "…" --prefix XXX
python scripts/pipeline/new_post.py     --campaign <slug> --id XXX-001 --slug … --title "…"
```

Chiến dịch **chạy theo lịch** thêm `--runner <script>.ps1 --runner-args "…"` để nhận
`run.ps1` + `prompt.txt` + khối `runtime:`. Không có cờ đó thì không sinh — cố ý: một điểm
vào không ai gọi là thứ sáu tháng sau không ai dám xoá.

Script chỉ chép file mà kênh **thật sự cần**: kênh chỉ đăng YouTube không nhận
`build-index.ps1` hay `subscribe.gs`.

## Khuôn phải TRUNG TÍNH — cổng kiểm giữ điều đó

Bốn script cấp kênh (`build-index.ps1`, `send_newsletter.py`, `build_yt_desc.py`,
`subscribe.gs`) được chưng cất từ bản đang chạy thật. Mọi thứ thuộc **nhận diện** — tên
kênh, tagline, tác giả, tên miền, id Meta Pixel — phải đến từ cấu hình, không được ghi cứng:

| Nguồn | Khoá |
|---|---|
| `channel.yml:brand` | `a` · `b` · `site_base` · `home_url` · `author` · `gh_repo` · `script_url` · `fb_pixel_id` |
| `brand.md` frontmatter | `tagline` · `tagline_short` · `welcome` · `email_accent` |
| `channel.yml:theme` | `web_accent` · `web_accent2` · `web_accent3` · `video_accents` |
| tuỳ chọn, có mặc định suy từ tên kênh | `og_title` · `og_description` · `site_description` · `rss_description` · `edition_word` · `edition_title` · `hot_label` · `hot_tagline` · `og_image` · `pixel_lead_name` |

`build-index.ps1` **dừng hẳn** khi thiếu một khoá nhận diện bắt buộc, chứ không lùi về mặc
định. Lý do: màu thiếu thì trang chỉ khác diện mạo, còn tên và tên miền thiếu thì trang mang
nhận diện của người khác — và không có dòng lỗi nào báo. Cùng lý do, khối Meta Pixel chỉ
sinh ra khi kênh tự khai `fb_pixel_id`.

Cổng `tests/test_no_identity_leak.py::test_TEMPLATE_khong_mang_nhan_dien_that` quét cả cây khuôn và
đỏ ngay khi một tên miền, email, tên người hay id pixel thật lọt vào.

## Bốn khuôn còn lại ở gốc

`CAMPAIGN_TEMPLATE.xlsx` · `EMAIL_NEWSLETTER_TEMPLATE.md` · `INFOGRAPHIC_PROMPT_TEMPLATE.md` ·
`RECYCLING_PLAN_TEMPLATE.md` — chúng không thuộc cây trạm, là biểu mẫu dùng riêng từng lúc.
