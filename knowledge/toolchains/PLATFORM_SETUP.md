# Nối agent với Facebook và YouTube

Ba việc agent cần làm được trên nền tảng: **đăng bài** · **xuất dữ liệu** · **kéo số liệu về**.
Mỗi việc cần một quyền khác nhau. File này là quy trình; script sẽ viết sau.

**Luật xuyên suốt:** token đọc từ `.env`, không bao giờ nằm trong workbook, brief hay repo.
Và dù có đủ token, agent vẫn **không đăng thật** khi `channel.yml` chưa đặt `autonomy: full`.

---

## 1. Facebook Page

### Quyền cần
| Việc | Quyền |
|---|---|
| Đăng bài / Reel | `pages_manage_posts` |
| Đọc tương tác bài | `pages_read_engagement` |
| Kéo số liệu insights | `read_insights` |
| Liệt kê Page mình quản trị | `pages_show_list` |

### Các bước
1. Tạo App tại `developers.facebook.com` → loại **Business**.
2. Thêm sản phẩm **Facebook Login** và **Pages API**.
3. Graph API Explorer → chọn App → **Get Page Access Token** → tick đủ 4 quyền trên.
4. Đổi token ngắn hạn thành **token dài hạn** (60 ngày) rồi lấy **Page token vĩnh viễn**.
5. Điền vào `.env`: `FB_PAGE_ID__<INSTANCE>` và `FB_PAGE_TOKEN__<INSTANCE>`.
6. Kiểm: `GET /{page-id}?fields=name,id` — trả về tên Page là xong.

### Mã bài để đối soát
Đăng xong Graph trả `id` dạng **`{page_id}_{post_id}`**. Ghi nguyên chuỗi này vào
trường `publish_link` trong `publish.json → posts[]`. Đây là khoá nối duy nhất về sau.

### Nếu KHÔNG cấp được quyền
Vẫn chạy được bằng đường xuất tay: Meta Business Suite → Insights → Nội dung → Xuất CSV.
File có cột **`ID bài viết`** — chính là khoá nối. Nối về bài qua `publish_link` của `publish.json → posts[]`.

⚠️ Graph API **không đọc được trang cá nhân**, chỉ đọc Page. Nội dung đăng trên profile
cá nhân thì chỉ còn đường xuất tay.

---

## 2. YouTube

### Quyền cần
| Việc | Scope |
|---|---|
| Tải video, sửa, quản lý playlist | `https://www.googleapis.com/auth/youtube` |
| Đọc số liệu (CTR, retention, subs gained) | `https://www.googleapis.com/auth/yt-analytics.readonly` |
| Đọc doanh thu (không bắt buộc) | `.../yt-analytics-monetary.readonly` |

### Các bước
1. Google Cloud Console → tạo project → bật **YouTube Data API v3** và **YouTube Analytics API**.
2. Tạo **OAuth client ID** loại *Desktop app* → tải `client_secret.json`.
3. Chạy luồng OAuth một lần, chọn đúng kênh, cấp **cả hai** scope ở trên.
4. Lưu đường dẫn vào `.env`: `YT_CLIENT_SECRET__<INSTANCE>`, `YT_TOKEN_PATH__<INSTANCE>`.
5. Kiểm: `channels.list(part="id,snippet", mine=True)` — trả đúng kênh của bạn là xong.

⚠️ **Đã có token cũ chỉ với scope `youtube`?** Thêm scope **không tự động** mở rộng token cũ —
phải chạy lại luồng cấp quyền, nếu không mọi lời gọi Analytics sẽ trả 403.

⚠️ Retention, impressions, CTR **chỉ có với kênh mình sở hữu**. Kênh người khác thì dù
có API cũng chỉ đọc được số liệu công khai (view, like, comment).

### Mã bài để đối soát
`videoId` 11 ký tự. Ghi vào trường `publish_link` trong `publish.json → posts[]`.

### Nếu KHÔNG cấp được quyền
YouTube Studio → Analytics → Nâng cao → Xuất CSV. Có `videoId` làm khoá nối.
Hạn chế: không có retention theo ngày.

---

## 3. Quy trình đồng bộ — 4 bước, giống nhau cho cả hai nền tảng

```
① Đăng xong          → ghi publish_link + publish_status vào `publish.json → posts[]`
② Lấy số liệu về     → file export tay HOẶC gọi API
③ Nối theo publish_link → ghi vào các cột actual_* CÙNG DÒNG Post
④ Đóng dấu           → metric_updated_at, VÀ chốt số vào hồ sơ .md Mục 9

> ⚠️ Cột `actual_*` **GHI ĐÈ** — workbook không giữ lịch sử đo. Không chốt số vào Mục 9
> của hồ sơ `.md` trước khi ghi đè = mất vĩnh viễn mốc đo cũ.
```

**Bước ① là bước hay bị bỏ nhất, và bỏ nó là hỏng cả chuỗi.** Không có `publish_link`
thì số liệu tải về không biết thuộc bài nào — dữ liệu vẫn nằm đó nhưng vô dụng.

### Đối soát định kỳ
Chạy lại kéo số liệu theo lịch. Ba tình huống phải xử lý, không được lờ:

| Tình huống | Nghĩa là | Làm gì |
|---|---|---|
| bài not found | Bài đã bị xoá hoặc đổi chế độ riêng tư | Hỏi người, đừng tự xoá dòng |
| permission denied | Token hết hạn hoặc mất scope | Cấp lại quyền, đừng thử vòng lặp |
| quá lâu chưa đồng bộ | Quá N ngày | Chạy lại; nếu vẫn lỗi thì báo |

### Dấu hiệu có người sửa tay trên nền tảng
tiêu đề trên nền tảng khác `content_name` của Content → ai đó đã đổi tiêu đề trực tiếp.
Đây không phải lỗi, nhưng phải báo cho người biết chứ đừng ghi đè lại.

---

## 4. Cấu hình theo instance

`channel.yml` giữ **định danh**, `.env` giữ **bí mật**. Không trộn.

```yaml
platforms:
  facebook:
    enabled: true
    page_id: ""                 # định danh — để được ở đây
    token_env: FB_PAGE_TOKEN__DUCNGUYEN_AI   # TÊN biến, không phải giá trị
    scopes: [pages_manage_posts, pages_read_engagement, read_insights]
  youtube:
    enabled: true
    channel_id: ""
    client_secret_env: YT_CLIENT_SECRET__DUCNGUYEN_AI
    token_env: YT_TOKEN_PATH__DUCNGUYEN_AI
    scopes: ["https://www.googleapis.com/auth/youtube",
             "https://www.googleapis.com/auth/yt-analytics.readonly"]
# File export tải về (Meta Business Suite / YouTube Studio) là TẠM: tải về thư mục
# bất kỳ, nhập vào `posts[].actual`, rồi bỏ. Không cần chỗ lưu cố định.
```

## 5. Trước khi bật đăng thật — bốn thứ phải xanh

1. `channel.yml` đặt `autonomy: full` (do người sửa tay, không phải agent).
2. Token còn hạn, đúng scope — kiểm bằng lệnh ở mục 1/2 trên.
3. Post đã `review_status = approved` VÀ `quality_check = passed`.
4. Đã chạy thử dry-run và kiểm `publish.json` thấy đúng ý.

Thiếu bất kỳ điều nào thì hệ thống tự chặn — đó là thiết kế, không phải lỗi.
