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
| `facebook_post` | `thumbnail.png` |
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

- **Chữ tiếng Việt phải overlay lúc dựng**, không để model sinh chữ trong ảnh — sai dấu.
- Thumbnail: 2–4 từ, **không lặp chữ với title** (title bán keyword + lời hứa, thumbnail bán hook hình).
- Có số liệu trên hình → **ghi nguồn ngay trên hình**.

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
