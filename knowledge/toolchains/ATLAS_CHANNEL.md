# ATLAS_CHANNEL — một bài blog đi từ đâu tới đâu

> **File này là hợp đồng cấp BÀI.** Bảy khâu trong `workflows/00_WORKFLOW_INDEX.md` là cấp
> CHIẾN DỊCH — chúng trả lời "chiến dịch này gồm những gì", không trả lời "làm một bài cụ
> thể thì gõ cái gì trước cái gì sau". Đây là chỗ trả lời câu thứ hai.
>
> **Khi làm một bài blog, đây là file DUY NHẤT cần đọc thêm** ngoài template và giọng văn.
> Đừng nạp cả kho tri thức — xem bảng nạp ở cuối.

Ký hiệu: 👤 người quyết · 🤖 agent · ⚙️ script.

---

## 1. Bố cục thư mục một bài

```
AST-001_gpt6-astra/                  ← Content.folder_path — MỘT thư mục, không tách handoff
│  # gốc = NGHIÊN CỨU và VIẾT (thứ người làm bài đọc và sửa)
├─ meta.json          định danh bài. KHÔNG chứa URL sau đăng — URL ở publish.json
├─ research.md        B1 · ĐÓNG BĂNG sau B1, chỉ được append mục "Kiểm sau"
├─ content.md         B2 · nguồn DUY NHẤT của text mọi kênh
├─ podcast.txt        B5 · kịch bản đọc
├─ scenes.json        B5 · kịch bản cảnh (src phân giải theo thư mục CỦA scenes.json)
├─ gates.json         B4 · nhật ký 23 cổng
├─ publish.json       B10 · gộp result.json + continuity.json cũ
│  # thư mục con = ĐEM ĐI ĐĂNG, theo KÊNH, đọc theo thứ tự đăng
├─ youtube/   video.mp4 · thumbnail.png · description.txt
├─ atlas/     blog.md · atlas.html · audio.mp3
└─ facebook/  post.txt · comment.txt · infographic.png · infographic.prompt.txt
              reel.txt  ← CHỈ khi bài có short.mp4 (gen_article --with-reel)
```

Tên file khai ở đúng một chỗ: `scripts/lib/post_paths.py`. Đổi tên file thì sửa ở đó,
không đi sửa 14 chỗ rải rác.

⚠️ **Không chép file sang thư mục kênh khác.** Kênh khác cần cùng một ảnh thì script DẪN
XUẤT sang đích (vd `facebook/infographic.png` → atlas `<slug>-1.jpg`). Có hai bản là sớm
muộn hai bản lệch, và không ai biết bản nào đã đăng.

## 1b. Bộ file của một bài trên web

Mỗi bài xuất bản thành **ba file cùng tên, cùng thư mục**:

```
atlas/content/<category>/<slug>.html    ← trang bài
atlas/content/<category>/<slug>.jpg     ← ảnh cover, cũng là og:image
atlas/content/<category>/<slug>.mp3     ← bản đọc
```

`<category>` suy từ `pillar` (xem `build_blog_html.py`):

| pillar | category |
|---|---|
| `powerbi` | `bi` |
| `fabric` | `de` |
| `ai-agent` | `ai` |
| `career` | `strategy` |
| *(không khớp)* | `ai` |

> ⚠️ **Bẫy đặt tên — đọc trước khi thêm ảnh thân bài.** `generate-manifest.js` dò ảnh cover
> bằng cách tìm file ảnh cùng tên bài. Ảnh MINH HOẠ trong thân bài phải đặt `<slug>-1.jpg`,
> `<slug>-2.jpg`… **Không bao giờ** đặt tên trùng `<slug>.jpg`, nếu không card ngoài trang
> chủ sẽ lấy nhầm ảnh minh hoạ làm cover.

## 2. Open Graph — 6 thẻ, không phải trang trí

Đo ngày 04/09/2026: **0/3 bài đã xuất bản có bất kỳ thẻ `og:` nào.** Nghĩa là mọi lần chia
sẻ lên Facebook đều ra một dòng link trần.

Với luật hiện hành (link nằm ở **comment đầu**, không nằm trong thân post), điều này quan
trọng hơn hẳn trước: comment chỉ có đúng một dòng link, mất preview là gần như mất hết click.

`build_blog_html.py` nay in đủ:

```
og:type · og:title · og:description · og:url · og:image · og:site_name
+ article:published_time · twitter:card · <link rel="canonical">
```

Hai điều bắt buộc:

- **`og:image` phải là URL tuyệt đối.** Facebook đi lấy ảnh từ máy chủ của họ — đường dẫn
  tương đối hay `data:` URI đều không tải được, và lỗi này **không hiện ra** khi xem thử
  tại máy.
- Tên miền lấy từ `ATLAS_BASE_URL`, không hardcode.

## 3. Trình tự 10 bước

Thứ tự đăng: **YouTube → Atlas → Facebook**. Đây là thứ tự duy nhất mà mỗi bước đều có sẵn
đầu vào nó cần: video lên YouTube trước để có `youtube_url` → trang atlas nhúng được video
*và* sinh ra `atlas_url` → comment Facebook mới có link atlas để dẫn. Đăng atlas trước thì
bài không có video hoặc phải sửa lại sau; đăng Facebook trước thì comment chưa có gì để dẫn.


### Hợp đồng đọc — ba thứ agent PHẢI đọc trước khi viết một chữ

| # | Đọc gì | Vì sao | Không đọc thì sao |
|---|---|---|---|
| 1 | `campaign.md` của chiến dịch | bài toán kinh doanh, đối tượng, thông điệp, trụ nội dung, **mục KHÔNG LÀM** | bài hay nhưng lạc chiến dịch — phát hiện sau khi đã dựng tiếng và hình |
| 2 | `profile.md` ở gốc kênh | tác giả là ai, giọng gì, chính kiến gì, không bao giờ viết gì | ra bài trung tính, đúng mà nhạt — đây là lỗi từng chạy suốt 3 bài mà không ai thấy |
| 3 | `research.md` của **chính bài đó** | mục tiêu nghiên cứu và nguồn riêng của bài | viết theo trí nhớ, G05 bắt được nhưng đã mất một vòng |

`new_post.py` chặn ở (1): `campaign.md` còn chữ mẫu thì không đẻ bài — điền đủ 8 trường
`business_problem · campaign_goal · target_audience · audience_pain_points · key_message ·
content_pillar · channels · primary_cta` rồi mới tạo. (2) và (3) không có cổng máy nào bắt
được việc *có đọc hay không* — chỉ bắt được hậu quả (G05 nguồn, G11 giọng). Nên nó nằm ở
đây thành chữ, và nằm trong docstring của `new_post.py`.

**Tạo hàng loạt** — `new_post.py --campaign <id> --bulk loat.tsv` (`id⇥slug⇥title[⇥angle]`).
Đọc chiến dịch và hồ sơ MỘT LẦN rồi nghiên cứu và viết cả loạt. Kiểm hết TSV trước khi tạo
thư mục đầu tiên: sai một dòng thì không bài nào được tạo — nửa loạt xong nửa loạt lỗi là
trạng thái khó dọn nhất.

| Bước | Khâu | Ai | Việc | Ra | Kiểm bằng SỐ |
|---|---|---|---|---|---|
| **B0** Chọn đề tài | ② | 🤖→👤 | Đối chiếu sổ `continuity.json` ở gốc kênh (đọc CÓ LỌC theo slug, đừng nạp cả file): chưa trùng · nối được bài gần nhất cùng nhóm · **tìm được use-case thật, không thì HOÃN** · ghi lý do chọn | 1 dòng `Content` (`status=proposed`) | `slug` không trùng sổ · lý do chọn ≥1 câu |
| 🔒 **Cổng 1** | | 👤 | `Content.status=approved` + `approved_date` | | **agent không tự đặt** |
| **B1** Nghiên cứu | ③ | 🤖 | WebSearch: định nghĩa từ nguồn chính chủ · **≥1 use-case doanh nghiệp THẬT có dẫn nguồn** · số liệu có ngày. Không tìm ra use-case → **dừng và báo**, đề xuất hoãn | `research.md`: mỗi nguồn 1 dòng `URL · tổ chức · ngày truy cập · trích 1 câu` | **3–7 nguồn**; `<3` thì DỪNG |
| **B2** Viết | ③ | 🤖 | Điền `content.md` theo neo `## post:`. **Chính kiến tác giả đọc FAIL-CLOSED** — không đọc được thì DỪNG, không viết tiếp | `content.md` | số khối `## post:` = số dòng `Post` · ≥1 khối `> **Góc nhìn:**` |
| **B3** Tách kênh | ③ | ⚙️ | `gen_article.py` tách **theo neo** | `atlas/blog.md` · `facebook/post.txt` · `facebook/comment.txt` · `youtube/description.txt` | mỗi file tồn tại và **>0 byte** |
| **B4** Tự kiểm | ④ | ⚙️+🤖 | `blog_gates.py` + `fb_format.py --check` + `QA_ASSET.md` | `gates.json` | 23 cổng; đỏ-chặn → `quality_check=failed` |
| 🔒 **Cổng 2** | | 👤 | `Post.review_status=approved` | | **agent không tự đặt** |
| **B5** Dựng tiếng & hình | ⑤ | ⚙️ | cover `gen_infographic.py` · `podcast.txt` → `make_podcast.py` **[venv OmniVoice]** · `scenes.json` → `make_podcast_video.py` · **ảnh tóm tắt** (`templates/INFOGRAPHIC_PROMPT_TEMPLATE.md`) | `youtube/thumbnail.png` · `atlas/audio.mp3` · `youtube/video.mp4` · `facebook/infographic.png` + `.prompt.txt` | cover 1280×720 · 8 scene · \|video−audio\| ≤1s · podcast 750–1000 từ |
| **B6** Dựng trang | ⑤ | ⚙️ | `build_blog_html.py` | `atlas/atlas.html` | **≥6 thẻ `og:`** |
| **B7** Đăng YouTube | ⑥ | ⚙️ | upload + `publishAt` giờ vàng | `youtube_url` | GET 200 |
| **B8** Đăng web | ⑥ | ⚙️ | chép 3 file vào `atlas/content/<cat>/` (trang **nhúng video B7**) → `generate-manifest.js` → `git add` **đích danh từng path** → push | `blog_url` | **GET `blog_url` = 200 TRƯỚC khi ghi sổ** |
| **B9** Đăng Facebook | ⑥ | ⚙️ | ⑨a post + `facebook/infographic.png`, **thân bài không link nào** → `fb_post_id`; ⑨b **comment ngay** bằng `facebook/comment.txt` → `fb_comment_id` | `fb_post_id` · `fb_permalink` · `fb_comment_id` | URL trong thân post = **0** · `fb_comment_id` khác rỗng · comment cách post **≤60 giây** |
| **B10** Ghi sổ & đo | ⑥→⑦ | ⚙️ | `register_publish set` ghi `publish.json` · `continuity.json` ở gốc kênh · **URL THẬT vào 3 cột `web`/`youtube`/`facebook` của bảng Content trong `campaign.md`** (idempotent theo `post_id`) **ngay khi có URL** | `publish.json` | `summary` ≤60 từ · `key_terms_explained` ≥3 |

### Vì sao verify HTTP 200 trước khi ghi sổ

Sổ của bài đầu tiên từng ghi một URL **dựng bằng cách nối chuỗi** — thiếu một đoạn đường
dẫn, và URL đó chết ngay từ lúc được ghi. Không ai phát hiện vì không có bước mở lại.
URL vào sổ phải là URL đã mở được, không phải URL đã tính ra.

## 4. Năm điều khác với các bài trước

| | Trước | Nay | Vì |
|---|---|---|---|
| 1 | Link atlas + video **trong thân post** | **Trong comment đầu**, thân post 0 URL | Chốt 04/09 |
| 2 | Ảnh kèm post = cover 16:9 dùng lại | **`facebook/infographic.png` — ảnh tóm tắt cả bài, cũng đặt ở đầu trang blog** | `templates/INFOGRAPHIC_PROMPT_TEMPLATE.md` |
| 3 | `atlas.html` không có `og:` | **≥6 thẻ** | Link ở comment thì preview là gần như tất cả |
| 4 | Nguồn ngoài 0–5, không đo | **3–7, có cổng chặn** | 2/3 bài cũ có 0 nguồn |
| 5 | Chính kiến rỗng, im lặng | **fail-closed** | Cả 3 bài cũ viết với chính kiến rỗng |

## 5. Bốn cái bẫy đã trả giá

1. **Tham số optional làm hỏng bài trong im lặng.** Chính kiến tác giả chưa từng được bơm
   vào prompt suốt 3 bài — file nguồn nằm ở đường dẫn khác, mà tham số là optional nên
   script vẫn chạy tiếp. Nay **fail-closed**: đọc không được thì dừng.
2. **Sai venv.** `make_podcast.py` cần venv OmniVoice (`soundfile` + `torch`), không phải
   Python hệ thống. Chạy nhầm ra `ModuleNotFoundError: soundfile`. Ghim `$OVPY` trong mọi lệnh.
3. **TTS treo trông y hệt TTS đang chạy.** Nhận biết bằng **CPU-time có tăng theo thời gian
   hay không**, không bằng "tiến trình còn sống". Đừng pipe qua `tail`/`head` — output bị
   giữ tới lúc kết thúc, và tiến trình treo nhìn giống hệt tiến trình bận.
4. **`git add -A` cướp file của phiên khác.** Máy này chạy nhiều phiên agent song song.
   Luôn `git add` **đích danh từng đường dẫn**.

## 6. PROTECTED — không đọc, không in ra

Token, `.env*`, `facebook_config.json`, `youtube_token.json`, `youtube_client_secret.json`.
Chúng nằm ở thư mục runtime **ngoài repo** và ngoài mọi thư mục đồng bộ đám mây. Script chỉ
được truyền **đường dẫn** tới chúng, không bao giờ đọc nội dung ra log hay ra chat.

Hồ sơ chính kiến tác giả cũng **không vào repo** — nó chứa thông tin cá nhân và tổ chức thật.
Nó sống ở STATION và được phân giải lúc chạy.

## 7. Đang làm gì thì đọc gì

| Đang làm | Đọc | KHÔNG đọc |
|---|---|---|
| Chọn đề tài | file này §3 (B0) + sổ continuity ở STATION | `output_styles/*`, playbooks |
| Viết `content.md` | `templates/content.md` + `output_styles/<giọng>.md` + `COPY_FRAMEWORKS.md` | toolchains, `PLATFORM_SETUP.md` |
| Tự kiểm | `.agents/checklists/QA_ASSET.md` + chạy `blog_gates.py` | templates |
| Dựng asset | `knowledge/toolchains/ASSET_TOOLCHAIN.md` | `output_styles/*` |
| Đăng | file này §3 (B7–B10) + `PLATFORM_SETUP.md` | templates, psychology |

## 8. Lệnh

```bash
# Windows: ép UTF-8, nếu không sẽ crash cp1252 khi in tiếng Việt
export PYTHONIOENCODING=utf-8

python scripts/pipeline/gen_article.py --content-md content.md --meta meta.json --out-dir .
#   -> atlas/blog.md · facebook/post.txt · facebook/comment.txt · youtube/description.txt
python scripts/pipeline/blog_gates.py .            # 23 cổng -> gates.json, exit!=0 khi đỏ
python scripts/pipeline/fb_format.py --check facebook/post.txt --comment facebook/comment.txt
python scripts/pipeline/build_blog_html.py --blog-md atlas/blog.md --meta meta.json \n    --infographic youtube/thumbnail.png --summary-img '<slug>-1.jpg' \n    --youtube-url <link> --audio-src '<slug>.mp3' --out atlas/atlas.html
```

**Không còn script điều phối gộp.** Hai file PowerShell cũ (`run-tobi-post.ps1`,
`publish-tobi.ps1`) đã bỏ: chúng gộp dựng và đăng vào một lệnh, nên một bước hỏng là phải
chạy lại từ đầu, và cổng duyệt của người bị nuốt vào giữa chuỗi.

Nay mỗi bước một lệnh, chạy lại được từng bước, và hai cổng nằm rõ giữa các lệnh:

```bash
python scripts/pipeline/register_publish.py <bài> init      # dựng khung posts[]
#   🔒 người duyệt Cổng 2
python scripts/pipeline/register_publish.py <bài> approve --by "<tên>" --note "<câu duyệt>"
#   … đăng YouTube → blog → Facebook …
python scripts/pipeline/register_publish.py <bài> set --post yt --link <url>
python scripts/pipeline/check_tree.py --station <trạm>      # phải 0 đỏ
python scripts/pipeline/build_views.py  --station <trạm>    # sinh lại bản đọc
```

Trạm phân giải theo `--station` → `$env:MARKETING_STUDIO_DATA` → `~/.marketing`; không đường
nào hardcode theo máy.
