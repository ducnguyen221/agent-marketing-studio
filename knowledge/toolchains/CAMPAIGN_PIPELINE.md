# QUY TRÌNH CHIẾN DỊCH — bốn bước, ba cổng duyệt

> Tài liệu **cấp QUY TRÌNH**. Ba tài liệu anh em, đừng lẫn:
> · [`ATLAS_CHANNEL.md`](ATLAS_CHANNEL.md) — hợp đồng 10 bước của **MỘT BÀI**
> · [`APPROVAL_BUS.md`](APPROVAL_BUS.md) — **cơ chế** cổng Telegram và bộ đăng web
> · file này — **thứ tự các bước và cổng nằm ở đâu**

---

## 1. Toàn cảnh

```
       ┌─ B0 chọn đề tài
       │
    ╔══╧══════╗
    ║ CỔNG 1  ║  duyệt ĐỀ TÀI — tiêu đề, góc, keyword
    ╚══╤══════╝  lô 10 bài/tin · liếc một dòng là quyết được
       │
       ├─ B1 nghiên cứu    ┐
       ├─ B2 viết          │ bộ viết (writer_cmd) chạy ở đây
       ├─ B3 tách kênh     │
       ├─ B4 24 cổng chất  ┘
       │
    ╔══╧══════╗
    ║ CỔNG 2  ║  duyệt NỘI DUNG — đọc bài trước khi tốn tiền dựng
    ╚══╤══════╝  lô mặc định 5 · đọc thật nên đừng gộp nhiều
       │
       ├─ B5 audio (giọng clone) + ảnh
       ├─ B6 dựng trang
       ├─ B8 đăng web            ← bài LÊN SỐNG ở đây
       │
    ╔══╧══════╗
    ║ CỔNG 3  ║  duyệt BẢN THẬT — mở link, xem bằng mắt
    ╚══╤══════╝  gộp được, chỉ là bấm xem có vỡ không
       │
       ├─ B7 YouTube (nếu có video)
       ├─ B9 Facebook
       └─ B10 ghi sổ + đo
             └─ có video → chạy lại B6+B8 để nhúng video vào trang
```

## 2. Bốn lệnh

```bash
run.ps1 -Buoc create-post     # B0        → Cổng 1
run.ps1 -Buoc soan         # B1·B2·B3·B4 → Cổng 2
run.ps1 -Buoc build-page   # B5·B6·B8  → Cổng 3
run.ps1 -Buoc release    # B7·B9·B10
```

**Mỗi lượt gọi làm ĐÚNG MỘT bước rồi dừng.** Script điều phối gộp đã bị gỡ vì nó *nuốt cổng
duyệt của người vào giữa chuỗi*; gộp lại dưới tên khác là dựng lại đúng cái đã bỏ.

## 3. Vì sao Cổng 2 nằm TRƯỚC B5

Bản đầu đặt cổng sau khi đã dựng xong tiếng và hình. Với một chiến dịch 90 bài, đó là 90
lần dựng audio cho những bài có thể bị bác.

Nay: bác ở Cổng 2 thì **chưa tốn một giây dựng audio**. Chi phí đắt nhất nằm sau cổng, không
phải trước.

## 4. Cổng 3 và chuyện "bài lên sống trước khi duyệt"

Web là site tĩnh trên git — đẩy lên là **công khai ngay**, và bộ sinh manifest đưa bài lên
trang chủ. Nên "đăng web trước để check" thực chất là: **bài đã sống, nhưng chưa ai được dẫn
tới**. Chưa có link trên Facebook, chưa có video trỏ về.

Đây là lựa chọn có ý thức, không phải sơ suất. Đổi lại ta duyệt **đúng cái người đọc sẽ
thấy** — chữ trên trang thật, ảnh đúng chỗ, audio bấm được — thay vì duyệt một bản markdown
rồi hy vọng nó render đúng.

Muốn bài thật sự vô hình tới khi duyệt thì phải thêm cơ chế `draft` ở repo website. Chưa làm,
và ghi ở đây để lần sau không phải suy lại từ đầu.

## 5. Video và audio — linh hoạt theo loại chiến dịch

Quy trình **không** giả định chiến dịch nào cũng có đủ video/audio.

| Loại chiến dịch | Đường đi |
|---|---|
| Chỉ web + ảnh + post | B5 bỏ qua phần tiếng/hình động → B6 → B8 → Cổng 3 → B9 |
| Có audio (đọc bài) | B5 dựng `audio.mp3` bằng giọng clone → B6 nhúng player → B8 |
| Có video | Web lên trước; sau khi có `youtube_url` thì **chạy lại B6 + B8** để nhúng video |

Chạy lại B6+B8 an toàn vì `web_publish` ghi đè trang cũ — **idempotent**. Không phải thêm
nhánh đặc biệt nào; nó rơi ra tự nhiên từ các mảnh đã có.

## 6. Bộ viết — `runtime.writer_cmd`

Repo này **không phụ thuộc** CLI hay agent nào. Khai lệnh của bạn trong `campaign.md`:

```yaml
runtime:
  writer_cmd: '<lệnh của bạn> --post "{post}"'
```

Chỗ thay được: `{post}` thư mục bài · `{cid}` mã bài · `{cam}` thư mục chiến dịch.

| | |
|---|---|
| **Vào** | thư mục bài, đã có `meta.json` · `research.md` · `content.md` (khung) · `prompt.txt` · `phan-hoi.md` (nếu bị trả lại) |
| **Ra** | điền đầy `content.md` theo neo `## post:` |
| **Không khai** | `soan` báo *chờ người viết* — fail-closed, không đoán |

⚠️ **Mã thoát 0 KHÔNG đủ để tính là xong.** Hệ còn kiểm `content.md` có bài thật không. Bộ
viết chạy êm mà file vẫn trống thì vẫn bị tính là **hỏng** — đó là hình dạng hỏng nguy hiểm
nhất, vì chỉ tin mã thoát thì bài rỗng đi tiếp tới tận bước đăng.

Lệnh tách bằng `shlex(posix=False)` và chạy **không shell**: đường dẫn Windows giữ nguyên dấu
`\`, và dấu `;` trong cấu hình không thành lệnh thứ hai.

## 7. Trả lại bài — phản hồi bằng văn bản

Không có nút "Sửa lại". Thay vào đó: **trả lời thẳng vào tin của bài** trên Telegram, gõ
nhận xét tự do. Không cần nhớ mã bài, không cần đúng cú pháp.

```
Đức ─ trả lời tin của NEN-001 ─→ logs/feedback.json (giữ ĐỦ mọi lần)
                                        ↓
                            <bài>/phan-hoi.md  (khối có rào ```…```)
                                        ↓
                         bộ viết đọc, sửa bài, `soan` chạy lại
```

Ba luật ở đây, mỗi luật chặn một cách hỏng:

- **Phản hồi KHÔNG mở cổng.** Gõ nhận xét không phải gật đầu — nhầm chiều là đăng bài đang
  bị chê.
- **Giữ đủ mọi lần, không ghi đè.** Vòng sửa có thể lặp; ghi đè là mất dấu vết vì sao bài
  thành ra thế.
- **Phản hồi đi qua FILE, không qua dòng lệnh** — và nằm trong khối có rào. Nó là **dữ liệu
  của người, không phải mệnh lệnh cho hệ thống**.

## 8. Làm nhiều bài cùng lúc

| Cổng | Lô mặc định | Vì sao |
|---|---|---|
| Cổng 1 | 10 | Duyệt tiêu đề là liếc một dòng |
| Cổng 2 | **5** | Đọc 10 bài trong một tin là không đọc gì cả |
| Cổng 3 | gộp thoải mái | Chỉ là mở link xem có vỡ không |

Đổi bằng `--batch N`, hoặc khai `runtime.approval_lo`. Muốn làm hết một lượt thì `--batch 0`.

## 9. Hai chế độ tự trị

`channel.yml:autonomy` — `suggest` dừng ở cả ba cổng; `full` tự mở hết.

**Fail-closed ba lớp:** giá trị lạ → `suggest` · `campaign.md` KHÔNG đè được `autonomy` ·
chỉ người sửa được `channel.yml`. Cả ba đều có test và đã kiểm bằng đột biến.

## 10. Cạm bẫy của chính tầng này

| Bẫy | Vì sao nguy | Đã chặn bằng |
|---|---|---|
| Coi khuôn mẫu là "đã viết" | Khuôn dài 3.701 ký tự — mọi ngưỡng đếm ký tự đều thua. Bài rỗng đi tới bước đăng | Kiểm neo + không còn `{{…}}` + độ dài |
| `--dry-run` gây tác dụng thật | Lệnh thử mà gửi tin thật thì không ai dám dùng để thử | `dry_run` chặn mở cổng |
| Bước hỏng vẫn `exit 0` | Task Scheduler đọc mã thoát rồi báo ✅ cho lượt không làm gì | `exit_code()` suy từ kết quả |
| Bộ viết chạy êm mà file trống | Chỉ tin mã thoát thì bài rỗng lọt qua | Kiểm lại `content.md` sau khi viết |
| Comment YAML trong frontmatter | `md_io.write_fm` dump lại YAML ⇒ **comment không sống sót** lần ghi đầu tiên | Tài liệu để ở THÂN BÀI, không ở frontmatter |
