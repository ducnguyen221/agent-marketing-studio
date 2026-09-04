# ATLAS_CHANNEL — một bài blog đi từ đâu tới đâu

> **File này là hợp đồng cấp BÀI.** Bảy khâu trong `workflows/00_WORKFLOW_INDEX.md` là cấp
> CHIẾN DỊCH — chúng trả lời "chiến dịch này gồm những gì", không trả lời "làm một bài cụ
> thể thì gõ cái gì trước cái gì sau". Đây là chỗ trả lời câu thứ hai.
>
> **Khi làm một bài blog, đây là file DUY NHẤT cần đọc thêm** ngoài template và giọng văn.
> Đừng nạp cả kho tri thức — xem bảng nạp ở cuối.

Ký hiệu: 👤 người quyết · 🤖 agent · ⚙️ script.

---

## 1. Bộ file của một bài trên web

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

| Bước | Khâu | Ai | Việc | Ra | Kiểm bằng SỐ |
|---|---|---|---|---|---|
| **B0** Chọn đề tài | ② | 🤖→👤 | Đối chiếu sổ `continuity.json` ở STATION: chưa trùng · nối được bài gần nhất cùng nhóm · **tìm được use-case thật, không thì HOÃN** · ghi lý do chọn | 1 dòng `Content` (`status=proposed`) | `slug` không trùng sổ · lý do chọn ≥1 câu |
| 🔒 **Cổng 1** | | 👤 | `Content.status=approved` + `approved_date` | | **agent không tự đặt** |
| **B1** Nghiên cứu | ③ | 🤖 | WebSearch: định nghĩa từ nguồn chính chủ · **≥1 use-case doanh nghiệp THẬT có dẫn nguồn** · số liệu có ngày. Không tìm ra use-case → **dừng và báo**, đề xuất hoãn | `research.md`: mỗi nguồn 1 dòng `URL · tổ chức · ngày truy cập · trích 1 câu` | **3–7 nguồn**; `<3` thì DỪNG |
| **B2** Viết | ③ | 🤖 | Điền `content.md` theo neo `## post:`. **Chính kiến tác giả đọc FAIL-CLOSED** — không đọc được thì DỪNG, không viết tiếp | `content.md` | số khối `## post:` = số dòng `Post` · ≥1 khối `> **Góc nhìn:**` |
| **B3** Tách kênh | ③ | ⚙️ | `gen_article.py` tách **theo neo** | `blog.md` · `fb_post.txt` · `fb_comment.txt` · `youtube_desc.txt` · `fb_desc.txt` | mỗi file tồn tại và **>0 byte** |
| **B4** Tự kiểm | ④ | ⚙️+🤖 | `blog_gates.py` + `fb_format.py --check` + `QA_ASSET.md` | `gates.json` | 22 cổng; đỏ-chặn → `quality_check=failed` |
| 🔒 **Cổng 2** | | 👤 | `Post.review_status=approved` | | **agent không tự đặt** |
| **B5** Dựng tiếng & hình | ⑤ | ⚙️ | cover `gen_infographic.py` · `podcast.txt` → `make_podcast.py` **[venv OmniVoice]** · `scenes.json` → `make_podcast_video.py` · **ảnh FB** (`ASSET_TOOLCHAIN.md` §6.1) | `thumbnail.png` · `audio.mp3` · `video.mp4` · `fb_image.png` + `.prompt.txt` | cover 1280×720 · 8 scene · \|video−audio\| ≤1s · podcast 750–1000 từ |
| **B6** Dựng trang | ⑤ | ⚙️ | `build_blog_html.py` | `atlas.html` | **≥6 thẻ `og:`** |
| **B7** Đăng YouTube | ⑥ | ⚙️ | upload + `publishAt` giờ vàng | `youtube_url` | GET 200 |
| **B8** Đăng web | ⑥ | ⚙️ | chép 3 file vào `atlas/content/<cat>/` (trang **nhúng video B7**) → `generate-manifest.js` → `git add` **đích danh từng path** → push | `blog_url` | **GET `blog_url` = 200 TRƯỚC khi ghi sổ** |
| **B9** Đăng Facebook | ⑥ | ⚙️ | ⑨a post + `fb_image.png`, **thân bài không link nào** → `fb_post_id`; ⑨b **comment ngay** bằng `fb_comment.txt` → `fb_comment_id` | `fb_post_id` · `fb_permalink` · `fb_comment_id` | URL trong thân post = **0** · `fb_comment_id` khác rỗng · comment cách post **≤60 giây** |
| **B10** Ghi sổ & đo | ⑥→⑦ | ⚙️ | `continuity.json` ở STATION (idempotent theo `post_id`) **ngay khi có URL** · sheet `Result` · hồ sơ `.md` | bản ghi continuity | `summary` ≤60 từ · `key_terms_explained` ≥3 |

### Vì sao verify HTTP 200 trước khi ghi sổ

Sổ của bài đầu tiên từng ghi một URL **dựng bằng cách nối chuỗi** — thiếu một đoạn đường
dẫn, và URL đó chết ngay từ lúc được ghi. Không ai phát hiện vì không có bước mở lại.
URL vào sổ phải là URL đã mở được, không phải URL đã tính ra.

## 4. Năm điều khác với các bài trước

| | Trước | Nay | Vì |
|---|---|---|---|
| 1 | Link atlas + video **trong thân post** | **Trong comment đầu**, thân post 0 URL | Chốt 04/09 |
| 2 | Ảnh kèm post = cover 16:9 dùng lại | **`fb_image.png` riêng, khổ đứng** | `ASSET_TOOLCHAIN.md` §6.1 |
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
| Viết `content.md` | `templates/CONTENT_TEMPLATE.md` + `output_styles/<giọng>.md` + `COPY_FRAMEWORKS.md` | toolchains, `PLATFORM_SETUP.md` |
| Tự kiểm | `.agents/checklists/QA_ASSET.md` + chạy `blog_gates.py` | templates |
| Dựng asset | `knowledge/toolchains/ASSET_TOOLCHAIN.md` | `output_styles/*` |
| Đăng | file này §3 (B7–B10) + `PLATFORM_SETUP.md` | templates, psychology |

## 8. Lệnh

```bash
# Windows: ép UTF-8, nếu không sẽ crash cp1252 khi in tiếng Việt
export PYTHONIOENCODING=utf-8

python scripts/pipeline/gen_article.py --content-md content.md --meta meta.json --out-dir .
python scripts/pipeline/blog_gates.py .            # 22 cổng -> gates.json, exit!=0 khi đỏ
python scripts/pipeline/fb_format.py --check fb_post.txt
python scripts/pipeline/build_blog_html.py --blog-md blog.md --meta meta.json --out atlas.html
```

Điều phối cả bài: `scripts/orchestrator/run-tobi-post.ps1` (dựng) và `publish-tobi.ps1` (đăng).
Đường dẫn trong hai script phân giải theo `-RootDocs` → `$env:MARKETING_STUDIO_DATA` → `~/.marketing`;
không đường nào hardcode theo máy.
