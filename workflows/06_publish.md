# Khâu ⑥: Xuất Bản & Hẹn Giờ Đa Kênh (Publish Distribution)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `distribution-manager` |
| **Đầu vào (Input)** | `publish.json → posts[]` có `review.status = approved` **và** `quality_check = passed` |
| **Công cụ (Tools)** | `scripts/pipeline/register_publish.py` · [`../knowledge/toolchains/PLATFORM_SETUP.md`](../knowledge/toolchains/PLATFORM_SETUP.md) |
| **Đầu ra (Output)** | Bài đã đăng + `publish.json` + **URL thật trong bảng Content** của `campaign.md` |

---

## 1. Thứ tự đăng — YouTube → trang blog → Facebook

Đây là **thứ tự duy nhất** mà mỗi bước đều có sẵn đầu vào nó cần:

1. **YouTube trước** → có `youtube_url`.
2. **Trang blog** → nhúng được video *và* sinh ra `blog_url`.
3. **Facebook** → comment mới có link blog để dẫn về.

Đăng blog trước thì bài không có video, hoặc phải sửa lại sau. Đăng Facebook trước thì
comment chưa có gì để dẫn — mà **bài Facebook không có comment là bài mồ côi**: thân bài
không chứa link, nên người đọc không có đường nào đi tiếp.

**Chiến dịch bật Cổng 3** (bảng Content có cột `g3`) đi thứ tự khác: trang web lên trước →
🔒 Cổng 3 (người mở link xem bản thật) → YouTube → Facebook, rồi có video thì dựng lại trang
để nhúng. Xem [`CAMPAIGN_PIPELINE.md`](../knowledge/toolchains/CAMPAIGN_PIPELINE.md) §1, §5.

## 2. Trình Tự Thực Thi

1. **Kiểm token & quyền.** Tên biến khai ở `channel.yml:secrets_env` của kênh; biến giữ
   **đường dẫn** tới file bí mật trong kho `~/.secret/` ([`SECRETS.md`](../knowledge/toolchains/SECRETS.md)).
   Biến chưa đặt hoặc trỏ vào file không có → **dừng và báo người**
   ([`PLATFORM_SETUP.md`](../knowledge/toolchains/PLATFORM_SETUP.md)), không retry mù.

2. **Cổng tự trị — cổng MÁY, không phải lời dặn.** `fb_publish.py --post <thư mục bài>`
   đọc `autonomy` từ `channel.yml` của kênh chứa bài. Khác `full` → **thoát mã 4**, không
   gọi Graph. Không tìm thấy `channel.yml`, hoặc thiếu `--post` → cũng mã 4 (fail-closed:
   không biết mức tự trị mà vẫn đăng là đúng kiểu lỗi tệ nhất).
   `--dry-run` luôn chạy được kể cả khi `suggest` — kiểm thử mà bị chặn thì người ta bỏ kiểm.

3. **Đăng theo giờ vàng** đã khai ở `campaign.md` Mục 5.

4. **Ghi sổ ngay khi có URL:**
   ```
   python scripts/pipeline/register_publish.py <thư mục bài> set --post yt  --link <url>
   python scripts/pipeline/register_publish.py <thư mục bài> set --post web --link <url>
   python scripts/pipeline/register_publish.py <thư mục bài> set --post fb  --link <url> \
       --platform-id <page_post_id> --comment-id <comment_id>
   ```

   Mỗi lệnh `set` làm bốn việc:
   - ghi `publish.status`, `link`, `at` vào `publish.json`;
   - thay `{{BLOG_URL}}` / `{{YOUTUBE_URL}}` trong các file đem đăng;
   - cập nhật `continuity.json` của kênh (idempotent theo `post_id`);
   - ghi **URL thật** vào cột `web` / `youtube` / `facebook` của bảng Content, và đặt
     `status = published` + ngày.

   ⚠️ **Facebook bắt buộc có `--comment-id`.** Permalink Facebook trả HTTP 200 cả khi đó là
   trang đăng nhập, nên kiểm bằng HTTP ở đây là vô nghĩa — cái kiểm được là có `platform_id`
   và có comment. Không có comment = bài mồ côi.

5. **Quy trình Đăng Page & Share bài vào Group kèm Teaser Caption (Chuẩn vận hành):**
   - Khi chiến dịch phân phối nội dung đa kênh (vừa kéo tương tác cho Fanpage, vừa lan tỏa vào Group cộng đồng):
     ```bash
     # 1. Đăng tự động lên Page, kèm cờ tự động chia sẻ bài viết vào Group + teaser caption:
     python scripts/pipeline/fb_publish.py --post <thư mục bài> --share-to-group <group_id> \
         --share-message-file <thư_mục_bài>/facebook/group_share.txt

     # Hoặc qua runner trực tiếp:
     python scripts/runners/post_facebook.py --message-file <fb.txt> --image <anh.png> \
         --share-to-group <group_id> --share-message-file <thư_mục_bài>/facebook/group_share.txt
     ```
   - *Cơ chế vận hành:*
     - Khối `## post:group_share` trong `content.md` được bóc tách nguyên tử ra `facebook/group_share.txt` theo 4 phong cách teaser ([`../templates/GROUP_SHARE_GUIDELINES.md`](../templates/GROUP_SHARE_GUIDELINES.md)): 3-Bullet Summary, Curiosity Hook, Quick Explainer, Practitioner Story.
     - Bài viết và ảnh Infographic đăng hoàn chỉnh lên Fanpage trước (kèm comment đầu chứa link blog).
     - Script tự động gọi Graph API để share link bài viết của Page vào Group (`/{group_id}/feed`) kèm teaser message.
     - Nếu Meta từ chối do hạn chế Groups API v19+ (Error 100/33), hệ thống chuyển sang trạng thái `manual_share_needed`, in sẵn link 1-click Web Share (`https://www.facebook.com/sharer/sharer.php?u=...`) VÀ in kèm `FB_GROUP_SHARE_CAPTION` để người vận hành copy dán ngay.
     - Với bài hẹn giờ (`--publish-at`): Pha 2 `attach_pending` sẽ tự động thực hiện cả 2 việc khi bài phát sóng: gắn comment blog và kích hoạt share Group với teaser đã lưu sẵn trong state.
     - Vẫn hỗ trợ cờ `--group-id` nếu đăng bài trực tiếp dưới tư cách Page vào Group (khi Meta cấp phép hoặc dùng môi trường tương thích).

6. **Kiểm lại cây:**
   ```
   python scripts/pipeline/check_tree.py --station <trạm>
   ```
   Phải **0 đỏ**. Rồi sinh lại bản đọc: `build_views.py --station <trạm>`.

## 3. Tiêu Chuẩn Nghiệm Thu

- [ ] Cả ba kênh có URL thật trong bảng Content — mở được bằng cách bấm.
- [ ] Facebook có `comment_id`, và comment chứa link về bài dài.
- [ ] `check_tree.py` 0 đỏ.
- [ ] Chuyển tiếp sang [Khâu ⑦ (Measure)](07_measure.md).
