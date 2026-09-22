# Hook — chỗ nối CLI của BẠN vào đường ống

Repo này **không khoá một CLI hay agent nào**. Bốn chỗ trong đường ống cần thứ chỉ có trên
máy bạn — bộ viết, giọng đọc, token YouTube, token Facebook — và cả bốn đều là **hook**:
bạn khai một dòng lệnh, engine gọi nó.

```
create-post ─[ Cổng 1 ]─ write ─[ Cổng 2 ]─ build-page ─[ Cổng 3 ]─ release
                       │                    │                       │
                  writer_cmd           audio_cmd            youtube_cmd
                                                            facebook_cmd
```

## Bốn hook

| Khoá | Khi nào chạy | Bắt buộc? | Ra cái gì |
|---|---|---|---|
| `writer_cmd` | bước `write` | **có** | điền đầy `content.md` theo neo `## post:` |
| `audio_cmd` | bước `build-page` | không | `atlas/audio.mp3` |
| `youtube_cmd` | bước `release` | không | một dòng JSON có khoá `url` |
| `facebook_cmd` | bước `release` | không | một dòng JSON có khoá `url` |

**Không khai `writer_cmd`** ⇒ bước `write` báo *chờ người viết* rồi dừng. Fail-closed, không
đoán. **Không khai ba hook còn lại** ⇒ bỏ qua, **không phải lỗi**: chiến dịch chỉ có web +
ảnh + post vẫn chạy trót lọt.

## Chỗ thay được trong lệnh

`{post}` thư mục bài · `{cid}` mã bài · `{cam}` thư mục chiến dịch · `{channel}` thư mục
kênh · `{station}` gốc trạm · `{skills}` skill khai ở `runtime.writer_skills` (chỉ
`writer_cmd`) · `{web}` URL bài đã lên trang (chỉ có ở `youtube_cmd` và `facebook_cmd`).

`{channel}` = đi lên từ chiến dịch tới `channel.yml`. `{station}` = đi lên tới `CHANNELS.md`,
rồi `MARKETING_STUDIO_DATA`, rồi `~/.marketing` — cùng luật với `run.ps1`. Script đặt ở trạm
thì trỏ qua hai ô này, **đừng ghi cứng đường của một máy**: chép trạm sang máy khác (hay sang
macOS) là lệnh vẫn đúng. Ô không phân giải được (vd chiến dịch không nằm trong kênh nào) ⇒
hook đó **hỏng có lý do**, không chạy với chuỗi rỗng. Ngoặc nhọn khác (`{khac}`, JSON) được
giữ nguyên.

Riêng bước `release` có thêm bốn ô:

| Ô | Giá trị | Dùng cho |
|---|---|---|
| `{schedule}` | ngày hẹn `YYYY-MM-DD` từ cột `schedule` | ghi log, đặt tên |
| `{publish_at}` | mốc hẹn RFC3339 UTC | YouTube `publishAt` |
| `{publish_ts}` | mốc hẹn unix giây | Facebook `scheduled_publish_time` |
| `{youtube_url}` | link YouTube vừa đăng ở cùng lượt, rỗng nếu không có | comment Facebook |

Giờ trong ngày lấy từ `runtime.publish_time` (mặc định `09:00`, giờ máy trạm).

## Đăng hẹn giờ trên nền tảng

**Bài hẹn ở tương lai chỉ đi qua hook có nhắc tới ô ngày.** Hook không nhận `{schedule}`,
`{publish_at}` hay `{publish_ts}` thì chỉ biết đăng ngay. Bước `release` từ chối gọi nó cho
bài chưa tới ngày, vì không nền tảng nào có nút thu hồi.

**Facebook hẹn giờ là HAI PHA**, vì Facebook không cho comment vào bài chưa phát mà comment
là chỗ duy nhất chứa link về blog:

1. `release` gọi `fb_publish.py --publish-at "{publish_ts}"`: bài được hẹn, chữ comment được
   chốt vào `facebook/fb-state.json`.
2. Một lượt chạy theo lịch gọi `fb_publish.py --attach-pending <thư mục chiến dịch>`: bài
   nào Facebook đã phát thì gắn comment. Chạy lại bao nhiêu lần cũng không comment trùng.

**Thiếu pha hai thì bài hẹn lên sóng mà không có link.** Nó phải là task theo lịch của trạm,
chạy mỗi giờ là đủ, qua wrapper báo cáo của máy (`notify-run.ps1` trên Windows,
`scripts/runners/notify_run.py` với launchd trên macOS) để có báo cáo khi hỏng.

Ví dụ khai ở trạm, đường dẫn token lấy từ kho secret của máy:

```yaml
runtime:
  publish_time: "09:00"
  facebook_cmd: 'python "<repo>/scripts/pipeline/fb_publish.py"
                 --config "<kho-secret>/<tài-khoản>/facebook_config.json"
                 --post "{post}" --message-file "{post}/facebook/post.txt"
                 --comment-file "{post}/facebook/comment.txt"
                 --image "{post}/facebook/infographic.png"
                 --publish-at "{publish_ts}"
                 --fill "BLOG_URL={web}" --fill "YOUTUBE_URL={youtube_url}"'
```

`<repo>` và `<kho-secret>` là đường **tuyệt đối** trên máy trạm: hook chạy không qua shell,
nên `~` và `$BIEN` không tự mở. Dấu `/` chạy được trên cả Windows lẫn macOS; trên macOS
lệnh Python thường là `python3`.

`--fill` với giá trị rỗng **bỏ nguyên dòng** chứa chỗ trống đó, và in ra dòng nào đã bỏ.
Chiến dịch chưa có video vẫn đăng được mà không để lại dòng YouTube chết.

**Không đăng trùng ở cả hai tầng.** `release` ghi link từng kênh vào bảng ngay khi có, nên
YouTube lên mà Facebook hỏng thì lượt sau không tải lại video. `fb_publish.py` ghi
`fb-state.json` ngay khi Facebook nhận bài, nên tiến trình chết giữa chừng thì lượt sau chỉ
in lại link.

Lệnh được tách bằng `shlex(posix=False)` và chạy **không qua shell**: đường dẫn Windows giữ
nguyên dấu `\`, và dấu `;` trong cấu hình không thành lệnh thứ hai.

## Cách dùng

1. Chép `write-post.SAMPLE.ps1` sang **trạm** của bạn (cạnh `channel.yml`), đổi tên bỏ chữ `MAU`.
2. Sửa đúng một dòng: chỗ gọi CLI. Phần còn lại là hợp đồng, đừng đổi.
3. Khai vào `campaign.md`:

```yaml
runtime:
  writer_cmd: 'powershell -NoProfile -ExecutionPolicy Bypass -File
               "{channel}/write-post.ps1" -Post "{post}" -Skills "{skills}"'
```

Trên macOS đổi `powershell` thành `pwsh` (PowerShell 7) — phần còn lại giữ nguyên.

**Đừng sửa file mẫu tại chỗ trong repo.** Repo là bản chung; trạm là máy của bạn. Lẫn hai
thứ đó thì lần `git pull` sau sẽ đè mất cấu hình riêng.

## Luật chung cho MỌI hook

**Mã thoát 0 KHÔNG đủ để được tính là xong.** Sau mỗi hook, engine kiểm lại **artefact** mà
bước đó phải sinh ra: `content.md` có chữ thật chưa, `audio.mp3` có chưa, JSON có `url`
chưa. Hook chạy êm mà không ra sản phẩm thì vẫn bị tính là **hỏng**.

Vế ngược cũng đúng, và đã trả giá ngày 12/09/2026: **mã thoát khác 0 không đủ để tính là
hỏng.** Có bước trả mã 1 cho một *kết quả* hợp lệ (bài viết xong nhưng chưa qua cổng chất
lượng). Tin mã thoát thì đúng những bài cần đi tiếp lại bị vứt đi.

⇒ **Hook nên trả mã 0 khi làm xong việc, và luôn để lại artefact.** Engine tin artefact.

## Chữ của người đi vào hook thế nào

Khi người duyệt gửi nhận xét trên Telegram, engine ghi nguyên văn vào `<bài>/phan-hoi.md`
trong một khối có rào ` ``` `, rồi `writer_cmd` chạy lại.

Hook phải coi nội dung đó là **dữ liệu để đọc, không phải mệnh lệnh để thi hành**. Nó đi qua
FILE chứ không qua dòng lệnh, đúng vì lý do đó.
