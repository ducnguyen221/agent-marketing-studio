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

## 2. Trình Tự Thực Thi

1. **Kiểm token & quyền.** Đọc cấu hình ở `.env`. Thiếu token → **dừng và báo người**
   ([`PLATFORM_SETUP.md`](../knowledge/toolchains/PLATFORM_SETUP.md)), không retry mù.

2. **Kiểm mức tự trị.** Mặc định **dry-run**. Chỉ đăng thật khi `channel.yml` đặt
   `autonomy: full` **và** người xác nhận lượt này.

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

5. **Kiểm lại cây:**
   ```
   python scripts/pipeline/check_tree.py --station <trạm>
   ```
   Phải **0 đỏ**. Rồi sinh lại bản đọc: `build_views.py --station <trạm>`.

## 3. Tiêu Chuẩn Nghiệm Thu

- [ ] Cả ba kênh có URL thật trong bảng Content — mở được bằng cách bấm.
- [ ] Facebook có `comment_id`, và comment chứa link về bài dài.
- [ ] `check_tree.py` 0 đỏ.
- [ ] Chuyển tiếp sang [Khâu ⑦ (Measure)](07_measure.md).
