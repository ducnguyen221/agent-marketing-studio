# Khâu ⑤: Dựng Asset Hình Ảnh & Video (Render Assets)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `creative-producer` |
| **Đầu vào (Input)** | Dòng `Post` đã có `review_status = approved` và cờ dựng `audio`/`video`/`short` bật |
| **Công cụ (Tools)** | [`../knowledge/toolchains/ASSET_TOOLCHAIN.md`](../knowledge/toolchains/ASSET_TOOLCHAIN.md) (HyperFrames, OmniVoice) |
| **Đầu ra (Output)** | File asset (thumbnail.png, audio.mp3, video.mp4) nằm tại `<folder_path>/` |

---

## 1. Trình Tự Thực Thi

1. **Kiểm tra Cờ Dựng:** Đối chiếu cờ `audio`, `video`, `short` trong frontmatter `research.md` của bài. Nếu là `no` → bỏ qua không dựng.
2. **Tạo Hình Ảnh & Thumbnail:** Tạo thumbnail theo đúng tỷ lệ kích thước kênh (16:9 cho YouTube, 1:1 hoặc 4:5 cho Facebook).
3. **Lồng Tiếng & Dựng Video:** Áp dụng toolchain theo tài liệu [`../knowledge/toolchains/ASSET_TOOLCHAIN.md`](../knowledge/toolchains/ASSET_TOOLCHAIN.md).
4. **Ảnh đính kèm bài Facebook — sinh rồi NGƯỜI soát chữ:**
   ```
   python scripts/pipeline/make_fb_image.py make   --post <thư mục bài> [--force]
   python scripts/pipeline/make_fb_image.py verify --post <thư mục bài> --by "<tên>" \
       --quote "<câu người soát nói nguyên văn>" [--failed]
   ```
   `make` đọc `facebook/infographic.prompt.txt` (khối `### image_prompt` của `content.md`), ra
   `facebook/infographic.png` + `facebook/infographic.meta.json` với `text_check = pending`.
   Không ghi đè ảnh cũ trừ khi `--force` (ảnh cũ được giữ cạnh bên).
   Model sinh ảnh hay vỡ dấu tiếng Việt, máy không đo được — nên `verify` là **dấu vết của
   người**: ai soát, nói gì, gắn với đúng sha256 của ảnh đã soát. `fb_publish.py` **từ chối
   đăng** ảnh chưa soát, ảnh soát `--failed`, hoặc ảnh bị đổi sau khi soát. Prompt đổi sau
   khi sinh ảnh thì `verify` từ chối — sinh lại bằng `make --force` rồi mới soát.
5. **Lưu trữ Asset:** file nằm **thẳng trong thư mục bài** — không có thư mục `assets/` riêng.
   Gốc thư mục giữ thứ để nghiên cứu và dựng (`audio.mp3`, `video.mp4`, `infographic.png`);
   `atlas/`, `youtube/`, `facebook/` giữ thứ đem đăng. Bố cục khai ở `scripts/lib/post_paths.py`.
   Chỉ điền `asset_ref` khi dùng asset **khác** mặc định (bảng ở `campaign.md` Mục 6).