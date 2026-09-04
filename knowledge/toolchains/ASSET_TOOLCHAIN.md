# ASSET_TOOLCHAIN — cờ trong Excel → công cụ nào dựng ra file gì

Dùng ở khâu ⑤ `render`, sau khi Post đã qua cổng 2 (`review_status = approved`).
Vai chịu trách nhiệm: `creative-producer`.

> Công cụ liệt kê ở đây là **của máy đang cài**. Máy khác cài instance riêng thì thay bằng
> công cụ tương đương — quy ước tên file và cột Excel giữ nguyên.

---

## 1. Quyết định dựng gì

Đọc 3 cờ ở sheet **Content**, không tự suy:

| Cờ | `= yes` thì dựng | `= no` |
|---|---|---|
| `audio` | `audio.mp3` — bản đọc của content | không dựng |
| `video` | `video.mp4` — video dài | không dựng |
| `short` | `short.mp4` — video dọc 15–60s | không dựng |

Ảnh (`thumbnail.png`, `carousel_*.png`, `infographic_*.png`) không có cờ riêng — dựng theo
`post_format` của các dòng Post thuộc content đó.

**Short LUÔN hỏi xác nhận trước khi dựng**, kể cả khi cờ đã bật.

## 2. Tên file — quy ước cứng

Mọi file nằm thẳng trong `<Content.folder_path>`. `Post.asset_ref` để trống nghĩa là agent
suy ra file theo bảng này:

| `post_format` | File dùng |
|---|---|
| `blog_article` | `thumbnail.png` (+ `audio.mp3` nếu `Content.audio = yes`) |
| `youtube_video` | `video.mp4` + `thumbnail.png` |
| `youtube_short` · `reel` | `short.mp4` |
| `facebook_post` | `fb_image.png` — ảnh riêng khổ đứng 1080×1350 (xem §6.1); dự phòng `thumbnail.png` |
| `carousel` | **không có mặc định** — bắt buộc điền `asset_ref` |
| `infographic` | **không có mặc định** — bắt buộc điền `asset_ref` |

Đặt tên khác quy ước → **phải** ghi vào `asset_ref`, nếu không khâu ⑥ sẽ không tìm thấy file.

---

## 3. Audio — OmniVoice

Nguồn text: khối `## post:youtube_video` → mục **Kịch bản đọc**, hoặc `## post:blog_article`
nếu làm bản đọc bài blog. Văn nói, không đọc nguyên bullet.

**Qua MCP** (ưu tiên — agent gọi trực tiếp):
```
omnivoice-tts · synthesize_speech(text, output_path, instruct, language, speed)
```

**Qua CLI:**
```powershell
cd $env:USERPROFILE\.tts\omnivoice   # nơi cài OmniVoice trên máy bạn
.\.venv\Scripts\python.exe narrate_cli.py --text "..." --out audio.mp3 `
  --instruct "female, young adult, moderate pitch"
```

- `instruct` mô tả giọng bằng tiếng Anh (giới tính, tuổi, cao độ).
- Kịch bản dài → dùng `--text-file` thay vì nhồi vào dòng lệnh.
- Giọng trình bày là **giọng của tác giả**. Trong nội dung công khai **không nhắc "giọng AI"**.

## 4. Video dài — HyperFrames + OmniVoice

HyperFrames render HTML/CSS thành MP4 câm; OmniVoice lồng tiếng vào.

**Một lệnh, ra video hoàn chỉnh** (cách dùng mặc định):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "$env:USERPROFILE\.video\render_and_narrate.ps1" `
  -Project "$env:USERPROFILE\.video\<project>" `
  -TextFile script.txt `
  -Out "<folder_path>\video.mp4" `
  -Instruct "female, young adult, moderate pitch" -Speed 1.0 -Mode fit
```

- `-Mode fit` (mặc định): lệch độ dài thì giữ khung hình cuối hoặc chèn im lặng.
  `-Mode shortest` cắt theo cái ngắn hơn — chỉ dùng khi cố ý.
- `-KeepSilent` giữ lại bản render câm để dựng lại nhanh.

**Tách bước, khi cần soi kỹ:**
```powershell
cd $env:USERPROFILE\.video\<project>
npx hyperframes lint       # kiểm composition trước
npx hyperframes preview    # xem trước trên web
npx hyperframes render -o silent.mp4
npx hyperframes doctor     # khi render lỗi — kiểm dependency
```

Composition đặt ở `<project>\compositions\*.html`. **Animation phải seekable** — điều khiển
theo timeline, không dựa thời gian thực; không thì render ra sai khung.

**Thứ tự làm:** chia cảnh + lời đọc từng cảnh → viết HTML → `lint` → `preview` → `render` →
lồng tiếng → giao `video.mp4`.

## 5. Short — cắt có chủ đích

Nguồn: khối `## post:youtube_short`. Đây là **một insight độc lập có hook riêng**, không phải
đoạn cắt ngẫu nhiên từ video dài.

Dựng như video dài nhưng project HyperFrames **khổ dọc 9:16**. Hook trong 1–3 giây đầu,
đổi hình khoảng mỗi 3 giây.

## 6. Ảnh — thumbnail, carousel, infographic

Nguồn nội dung: khối `## post:carousel` / `## post:infographic` trong `content.md`.

- Chữ tiếng Việt: model **được phép** vẽ, kèm cổng kiểm chính tả trước khi đăng (§6.1).
- Thumbnail: 2–4 từ, **không lặp chữ với title** (title bán keyword + lời hứa, thumbnail bán hook hình).
- Có số liệu trên hình → **ghi nguồn ngay trên hình**.

### 6.0 Hai loại ảnh, đừng lẫn

| | Dựng bằng | Khổ | Dùng ở đâu |
|---|---|---|---|
| **`thumbnail.png`** — ảnh bìa | `gen_infographic.py` (HTML + Chrome, chữ luôn đúng dấu) | 1280×720 | cover card trên atlas · hình thu nhỏ YouTube |
| **`infographic.png`** — ảnh tóm tắt | model sinh ảnh qua cầu Codex, theo `templates/INFOGRAPHIC_PROMPT_TEMPLATE.md` | 1920×1080 | **ảnh đăng Facebook** · đặt **ở đầu bài blog** |

Ảnh tóm tắt là bản rút gọn của cả bài trong một hình — người lướt qua phải nắm được ý
chính trong 5 giây mà không cần bấm gì. Nó thay cho `fb_image.png` cũ (một nền + ba dòng
chữ). **Một ảnh, hai chỗ dùng.** Cách viết prompt, ngữ pháp bố cục 5 vùng và cổng kiểm
chính tả nằm ở `templates/INFOGRAPHIC_PROMPT_TEMPLATE.md` — đọc file đó trước khi dựng.

Trên atlas, ảnh tóm tắt đặt tên `<slug>-1.jpg`, **không** đặt `<slug>.jpg`.

### 6.1 Ảnh cho bài Facebook — `fb_image.png` *(cách cũ, giữ để tham chiếu)*

Bài Facebook nay đăng **kèm ảnh riêng**, không dùng lại cover 16:9 của blog. Lý do đo được:
cover 16:9 chiếm rất ít chiều cao trên feed điện thoại, trong khi khổ đứng 4:5 chiếm gần
gấp đôi — cùng một lần lướt, ảnh đứng có nhiều thời gian được nhìn hơn.

```
Kích cỡ  : 1080×1350 (4:5)   — khổ chiếm nhiều màn hình mobile nhất
           dự phòng 1200×630 (1,91:1) nếu bài đi bằng preview link
Tên file : fb_image.png              <- ảnh chính đăng kèm post
           fb_image-2.png, -3.png    <- nếu đăng nhiều ảnh
           fb_image.prompt.txt       <- BẮT BUỘC, sidecar ghi nguyên văn prompt
Nơi lưu  : cùng thư mục bài, cạnh mọi asset khác
Excel    : Post.asset_ref = "fb_image.png"  (khác mặc định thì PHẢI điền)
```

**Năm điều không được vi phạm**

1. **Ảnh sinh bằng model KHÔNG tái lập.** Cùng một prompt cho ra ảnh khác. Vì thế phải lưu
   *cả ảnh lẫn prompt*, và **cấm sinh lại lúc đăng** — sinh lại nghĩa là bài đăng lên mang
   ảnh khác với ảnh đã duyệt, mà không ai thấy sự khác biệt đó ở đâu.
2. **Không đặt trùng tên `<slug>.jpg`** nếu ảnh được chép sang atlas. `findThumb` trong
   `generate-manifest.js` sẽ nhặt nhầm ảnh thân bài làm cover card. Ảnh thân bài đặt
   `<slug>-1.jpg`, `-2.jpg`…
3. **Ảnh có số liệu phải ghi nguồn ngay trên hình.** Số liệu rời khỏi bài viết thì mất ngữ
   cảnh; ảnh bị chia sẻ lại một mình là chuyện bình thường.
4. **Model không hỗ trợ nền trong suốt** — đừng thiết kế lớp cần alpha.
5. **Chữ trên ảnh phải được đọc lại và đối chiếu với văn bản nguồn trước khi đăng.**
   Xem mục ngay dưới.

**Chữ tiếng Việt trên ảnh — đổi từ CẤM sang KIỂM (Đức chốt 04/09/2026)**

Luật cũ: không giao chữ tiếng Việt cho model vẽ, mọi chữ phải overlay lúc dựng. Luật đó
sinh ra vì model sinh ảnh hay vỡ dấu tiếng Việt — chữ trông như tiếng Việt nhưng sai dấu
hoặc vô nghĩa — mà **ảnh đã đăng công khai thì không sửa được**.

Luật mới: **model được vẽ cả chữ.** Đổi lại, thêm một cổng bắt buộc:

- Trước khi đăng, **đọc lại từng chữ trên ảnh** và đối chiếu với văn bản nguồn.
- Sai một dấu cũng **sinh lại**, không đăng, không "tạm chấp nhận".
- Ảnh không đọc được chữ (mờ, cắt cụt, chồng chữ) xử lý như sai chính tả.

> ⚠️ Rủi ro chuyển từ *cấm* sang *kiểm*, chứ không biến mất. Bỏ luật cấm mà cũng bỏ luôn
> bước kiểm thì rủi ro cũ quay lại nguyên vẹn — và lần này không còn hàng rào nào.

Overlay lúc dựng vẫn là cách **chắc chắn đúng** cho chữ phải chuẩn tuyệt đối (tên riêng,
số liệu, tên thương hiệu). Giờ nó là *lựa chọn*, không còn là *bắt buộc*.

**Cổng kiểm ảnh (đếm được, xem `blog_gates.py` G19)**

- `fb_image.png` **và** `fb_image.prompt.txt` — thiếu một trong hai là trượt.
- Đúng tỉ lệ đã khai (±2 px).
- Cổng chỉ nói cái nó đo được: báo *"thiếu fb_image.prompt.txt"*, **không** báo
  *"ảnh không đạt chất lượng"* — cổng không đo được chất lượng, mắt người mới đo được.

## 7. Sau khi dựng — ghi lại vào Excel

1. Kiểm file tồn tại và mở được. Render lỗi mà vẫn ghi vào Excel là tạo dữ liệu giả.
2. Tên khác quy ước → điền `Post.asset_ref` (đường dẫn **tương đối** trong `folder_path`).
3. Đặt `Post.post_status = approved`, cập nhật `updated_at`.
4. Báo cho người: dựng file gì, nằm đâu, dung lượng bao nhiêu.

**Không đăng ký asset vào sổ nào cả.** Thư mục `folder_path` chính là kho — không có sheet
Asset. `asset_ref` chỉ ghi *lựa chọn khác mặc định*, không phải danh mục file.

---

## Khi nào DỪNG

- Chưa rõ quyền dùng một asset (ảnh, nhạc, tư liệu) → hỏi. **Không tự khai "own".**
- Render thất bại 2 lần liên tiếp → dừng, báo lỗi thật. Không retry mù.
- Cờ `= no` nhưng người bảo "cứ dựng đi" → sửa cờ trong Excel trước, rồi mới dựng. Excel là
  nguồn sự thật, không phải câu nói trong chat.
