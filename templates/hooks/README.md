# Hook — chỗ nối CLI của BẠN vào đường ống

Repo này **không khoá một CLI hay agent nào**. Bốn chỗ trong đường ống cần thứ chỉ có trên
máy bạn — bộ viết, giọng đọc, token YouTube, token Facebook — và cả bốn đều là **hook**:
bạn khai một dòng lệnh, engine gọi nó.

```
create-post ─[ Cổng 1 ]─ soan ─[ Cổng 2 ]─ build-page ─[ Cổng 3 ]─ release
                       │                    │                       │
                  writer_cmd           audio_cmd            youtube_cmd
                                                            facebook_cmd
```

## Bốn hook

| Khoá | Khi nào chạy | Bắt buộc? | Ra cái gì |
|---|---|---|---|
| `writer_cmd` | bước `soan` | **có** | điền đầy `content.md` theo neo `## post:` |
| `audio_cmd` | bước `build-page` | không | `atlas/audio.mp3` |
| `youtube_cmd` | bước `release` | không | một dòng JSON có khoá `url` |
| `facebook_cmd` | bước `release` | không | một dòng JSON có khoá `url` |

**Không khai `writer_cmd`** ⇒ bước `soan` báo *chờ người viết* rồi dừng. Fail-closed, không
đoán. **Không khai ba hook còn lại** ⇒ bỏ qua, **không phải lỗi**: chiến dịch chỉ có web +
ảnh + post vẫn chạy trót lọt.

## Chỗ thay được trong lệnh

`{post}` thư mục bài · `{cid}` mã bài · `{cam}` thư mục chiến dịch · `{web}` URL bài đã lên
trang (chỉ có ở `youtube_cmd` và `facebook_cmd`).

Lệnh được tách bằng `shlex(posix=False)` và chạy **không qua shell**: đường dẫn Windows giữ
nguyên dấu `\`, và dấu `;` trong cấu hình không thành lệnh thứ hai.

## Cách dùng

1. Chép `write-post.SAMPLE.ps1` sang **trạm** của bạn (cạnh `channel.yml`), đổi tên bỏ chữ `MAU`.
2. Sửa đúng một dòng: chỗ gọi CLI. Phần còn lại là hợp đồng, đừng đổi.
3. Khai vào `campaign.md`:

```yaml
runtime:
  writer_cmd: 'powershell -NoProfile -ExecutionPolicy Bypass -File
               D:\tram\<kênh>\viet-bai.ps1 -Bai "{post}"'
```

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
