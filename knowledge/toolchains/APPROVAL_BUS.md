# APPROVAL_BUS — cổng duyệt qua Telegram, chế độ tự trị, và đăng web

> Ba mảnh nối nhau: **ai duyệt** (`approve_bus.py`) · **chạy tới đâu thì dừng**
> (`campaign_step.py`) · **bài đi đâu** (`web_publish.py`).
> Hợp đồng cấp BÀI của một bài blog nằm ở [`ATLAS_CHANNEL.md`](ATLAS_CHANNEL.md) — file này
> nói về tầng ĐIỀU PHỐI ở trên nó.

## 1. Các bước rời, cổng nằm ở giữa

```
create-post ─[ Cổng 1 ]─ write ─[ Cổng 2 ]─ build-page ─[ Cổng 3 ]─ release
   │                      │                   │                       │
   │ new_post             │ gen_article       │ build_blog_html       │ youtube_cmd
   │ --fill-row           │ blog_gates (24)   │ web_publish           │ facebook_cmd
   │                      │ register_publish  │ (+ audio_cmd)         │ (fb_publish)
   │                      │   init            │                       │
```

Cổng 3 chỉ có khi bảng Content khai cột `g3`. Bảng không có cột đó thì `release` chạy ngay
sau `build-page`.

**Vì sao rời chứ không gộp.** Script điều phối gộp đã bị gỡ vì nó *gộp dựng và đăng vào một
lệnh, nên một bước hỏng là phải chạy lại từ đầu, và cổng duyệt của người bị nuốt vào giữa
chuỗi*. Mỗi bước ở đây chạy lại được độc lập, và các cổng nằm **giữa** các bước chứ không
lẫn vào trong.

**Mỗi lượt gọi = một bước.** Theo lịch: `run.ps1 -Step create-post` / `-Step write` /
`-Step publish` (`publish` gọi `build-page`). Bước `release` chưa có trong runner — chạy
`campaign_step.py <chiến dịch> release`.

## 2. Cổng nằm ở đâu — KHÔNG có kho thứ hai

| Cổng | Chỗ ở THẬT | Ai ghi |
|---|---|---|
| **g1** duyệt đề tài | cột `g1` + `status` trong bảng Content của `campaign.md` | `approval_gate` (phiên) hoặc `approve_bus` (Telegram), qua `md_io` |
| **g2** duyệt trước khi đăng | `publish.json → posts[].review` (+ ô `g2` mirror) | `register_publish approve` |
| **g3** duyệt bản thật trên web | cột `g3` trong bảng Content | `approval_gate` hoặc `approve_bus` |

`approve_bus.py` là **mặt tiền**, không phải kho. File trạng thái riêng của nó
(`logs/tg-approve.json`) chỉ giữ hai thứ của riêng Telegram: con trỏ `offset` và các token
đang chờ. Xoá nó đi thì tệ nhất là phải gửi lại tin — **không mất một dấu vết duyệt nào**.

## 3. Hai chế độ

`channel.yml:autonomy` quyết Cổng 1 và Cổng 2 dừng hay tự mở. Dừng thì hỏi QUA ĐÂU do
`campaign.md: runtime.approval_via` quyết: `session` (mặc định — agent trong phiên hỏi người
ngay tại chỗ, không gửi gì) hoặc `telegram`.

| Mức | Cổng 1 | Cổng 2 | Cổng 3 | Dùng khi |
|---|---|---|---|---|
| `suggest` *(mặc định)* | dừng, hỏi người | dừng, hỏi người | người mở | Nội dung có tên mình trên đó |
| `auto_safe` | dừng, hỏi người | dừng, hỏi người | người mở | Ở tầng cổng giống `suggest` |
| `full` | tự mở | tự mở | người mở | Đã tin quy trình, chấp nhận không ai đọc trước khi đăng |

Cổng 3 **không** tự mở ở mức nào: `campaign_step` không gọi mở cổng này, nên `release` chờ
tới khi ô `g3` có ngày.

**Fail-closed ba lớp:** giá trị lạ → `suggest` · `campaign.md` không đè được `autonomy` ·
chỉ NGƯỜI sửa `channel.yml`. Cả ba đều có test, và test đã được kiểm bằng đột biến.

## 4. Duyệt qua Telegram

```
approve_bus.py send    --campaign <đường dẫn> --gate g1|g2|g3 [--batch N] [--mode per_post|batch_gate]
approve_bus.py receive --campaign <đường dẫn> [--follow GIAY]
approve_bus.py poller-status --campaign <đường dẫn>
```

Bấm nút, hoặc nhắn `duyet NEN-003` / `tu choi NEN-003 <lý do>`.

**Bốn lớp bảo vệ:**

1. **Allowlist** — chỉ `chat_id` khai trong file secret. Ai cũng nhắn được cho một bot Telegram.
2. **Token một lần** — sinh lúc gửi, xoá ngay khi dùng. Nút cũ nằm mãi trong lịch sử chat.
3. **Hạn 48 giờ.**
4. **Tin nhắn là DỮ LIỆU, không phải MỆNH LỆNH** — không `eval`/`exec`/shell; ghi chú chỉ
   nhận chữ, số và dấu câu hiền. Có test quét **AST** (không quét văn bản: một cổng quét
   chuỗi sẽ báo đỏ vì chính đoạn tài liệu này).

⚠️ **`getUpdates` chỉ cho MỘT người đọc trên mỗi bot token.** `approve_bus.py` phải là tiến
trình duy nhất poll con bot đó.

**Telegram báo xung đột này TO VÀ RÕ — ĐO ĐƯỢC 10/09/2026:**
`Conflict: terminated by other getUpdates request; make sure that only one bot instance
is running`. Yêu cầu MỚI giết yêu cầu CŨ, nên hai poller sẽ đạp nhau liên tục và **cả hai
cùng hỏng ồn ào**, chứ KHÔNG phải lặng lẽ ăn trộm update của nhau.

> Bản đầu của tài liệu này viết là "im lặng". Đó là **suy đoán chưa đo**, và phép đo bác
> bỏ nó. Giữ lại ghi chú này vì nó đổi cách phòng: không cần dựng cổng phát hiện ngầm,
> chỉ cần ĐỌC LỖI — `loi_lien_tiep` trong kết quả `receive --follow` là đủ để nhận ra.

## 5. Đăng web

Đích khai ở `channel.yml:web_target` (xem khuôn
[`templates/station/_channel/channel.yml`](../../templates/station/_channel/channel.yml)).
Không khai mà gọi `web_publish.py` thì nó **DỪNG** — không đoán đích đăng.

Trình tự: chép file → `post_cmd` → `git add` **đích danh** → commit → push →
**GET phải trả 200 TRƯỚC khi báo thành công**.

- `git push` xong không có nghĩa trang đã lên: trang tĩnh dựng lại mất vài chục giây và
  build có thể hỏng. Ghi `blog_url` trước khi kiểm là ghi một URL chết — nó chỉ lộ ra hàng
  tuần sau, lúc không còn nhớ bài nào hỏng vì sao.
- **Không bao giờ `git add -A`**: máy có thể chạy nhiều phiên agent cùng lúc, `-A` gom cả
  file của phiên khác vào commit của mình. Lệnh hậu kỳ sinh thêm file thì khai ở
  `post_cmd_outputs`.

## 5b. Chiều NHẬN chạy thế nào (distill từ OpenClaw 2026.5.12)

**Trần long-poll của Telegram là ~50 giây — ĐO ĐƯỢC, không phải trích tài liệu.** Bot API
không công bố giá trị lớn nhất cho `timeout`; xin 100s và 60s đều trả về sau **50,7s**.
Nên phủ liên tục thì phải **nối nhiều lượt**, không phải xin timeout to hơn.

### KHÔNG có "cửa sổ 50 giây" làm rơi cú bấm

Đọc kỹ chỗ này trước khi định thêm "cơ chế quét sau 50s" — **không có kẽ hở để quét.**

Telegram **giữ update 24 giờ** (Bot API: *"Incoming updates are stored on the server until
the bot receives them... not longer than 24 hours"*). Bấm ở giây thứ 51, giây thứ 3.000, hay
lúc máy đang tắt — update vẫn nằm đó và lượt `getUpdates` **kế tiếp** sẽ nhặt.

`timeout=50` **không phải cửa sổ nhận**. Nó là "chặn kết nối tối đa 50 giây rồi trả về dù có
gì hay không". Nối liên tiếp các lượt là phủ 100% thời gian.

⚠️ Thêm một bộ quét nữa = **hai `getUpdates` song song** = đúng cái bệnh mục dưới đang chữa.

### Kiến trúc

```
Task Scheduler (mỗi phút, IgnoreNew)
        │  đang chạy -> bỏ qua lượt gọi mới
        │  đã chết   -> dựng lại trong 60s
        ▼
run-approve-poller.ps1  ── sống ~55 phút rồi TỰ THOÁT
        ▼
approve_bus.py receive --follow 3300
        ├─ ① GIÀNH LOCK -> có người giữ thì THOÁT ÊM mã 0 (đường chạy bình thường mỗi phút)
        ├─ ② vòng lặp: getUpdates(timeout=50) -> xử lý -> ghi nhịp -> gia hạn lock -> log
        └─ ③ nhả lock trong `finally`
```

Phủ gần 100%, tự lành trong 60 giây, **không service nào phải trông**.

### Lock một-tiến-trình — vì sao KHÔNG phó thác Task Scheduler

`MultipleInstances = IgnoreNew` chỉ chặn khi Windows còn **thấy** instance cũ. Instance chết
sớm là lượt sau vào ngay. Ngày 10/09/2026 điều đó thành **nhiều poller chồng nhau ghi đè
trạng thái của nhau**: `g1` ghi được nhưng `offset` và token bị tiến trình khác xoá mất, nên
cú bấm của người **trông như rơi** dù việc đã làm xong một nửa.

**Phép thử "còn sống" dùng NHỊP, không dùng PID.** Windows tái dùng PID, nên một PID sống
không chứng minh được đó là poller của ta; kiểm cả thời điểm khởi động thì phải gọi
`GetProcessTimes` qua ctypes. Nhịp thì **không giả được** — chỉ chính poller đang chạy mới
gia hạn. PID trong file chỉ để người đọc log biết mà tìm.

Lock chết (không gia hạn quá 180s) → người sau chiếm được. File lock hỏng → coi như không
có. Cả hai đều fail-**open** có chủ đích: lock kẹt là kẹt cổng duyệt, tệ hơn nhiều so với
rủi ro trùng một nhịp.

**Ba thay đổi của OpenClaw 2026.5.12, và ta lấy gì:**

| Của họ | Ta | Vì sao |
|---|---|---|
| Worker polling tách khỏi runtime agent | **Đã có** | Poller là tiến trình riêng, không nằm trong runner chiến dịch |
| Spool bền: ghi update xuống đĩa TRƯỚC khi xử lý | **Lấy phần LÕI, bỏ phần vỏ** | Rủi ro thật hẹp hơn kiến trúc của họ nhiều: chỗ duy nhất mất dữ liệu là **token bị tiêu trước khi ghi cổng xong** — ghi hỏng thì cú bấm rơi vĩnh viễn và người bấm lại chỉ nhận "đã dùng rồi". Vá đúng chỗ hẹp đó (chỉ tiêu token SAU khi `_apply` trả về) rẻ hơn nhập cả một tầng hàng đợi |
| **Nhịp sống đo bằng chiều VÀO, không phải chiều RA** | **LẤY** | Đây là bài học đắt nhất |

Về cái thứ ba: trước bản đó OpenClaw tính lời gọi API **đi ra** (gửi tin) là dấu hiệu "bot
còn sống" — nên chiều **vào** chết mà không ai biết. Đúng hình dạng đó ở đây: `send_gate`
vẫn gửi tin xin duyệt đều đặn trong khi `receive` đã ngừng nhận, mọi thứ nhìn vẫn bình thường
cho tới lúc có người thắc mắc sao bấm không ăn. Nên nhịp CHỈ ghi sau một lượt `getUpdates`
thành công; gửi được tin **không tính**. Xem `logs/tg-poll-alive.json`, đọc bằng
`approve_bus.py poller-status`.

**Poller KHÔNG đi qua `notify-run.ps1`** (Đức chốt 10/09): nó chạy gần như liên tục, báo
mỗi lượt là hàng nghìn tin một ngày — và tin báo nhiều tới mức đó thì không ai đọc nữa,
tức là mất luôn tác dụng cảnh báo cho MỌI task khác. Bù lại nó tự chứng minh còn sống bằng
nhịp ở trên.

⚠️ **Nợ kiến trúc đã biết:** trạng thái poller gắn theo CHIẾN DỊCH, mà `getUpdates` chỉ cho
một người đọc trên mỗi bot token. Hai chiến dịch cùng duyệt qua Telegram là hai poller đạp
nhau — **ồn ào**, cả hai cùng nhận `Conflict` và không bên nào chạy êm.
`warn_two_pollers()` cảnh báo TRƯỚC khi tới nước đó. Cách sửa đúng khi thật sự cần hai
chiến dịch: **một poller cho cả trạm**, định tuyến update theo token.

## 6. Ba cái bẫy đã trả giá ở tầng này

| Bẫy | Hình dạng | Cách chặn |
|---|---|---|
| **Bước hỏng vẫn `exit=0`** | Task Scheduler đọc mã thoát rồi báo ✅ cho một lượt không làm được gì | `exit_code()` suy từ KẾT QUẢ, có test |
| **Lịch lập trước, `new_post` không điền được** | `new_post` giả định nó TẠO dòng nên gặp dòng có sẵn là dừng | chế độ `--fill-row`, chỉ ghi cột `folder` |
| **Hai chế độ lệch nhau** | dựng 3 bài mà tin xin duyệt hỏi 10 | `send_gate(cids=…)` hỏi đúng những bài vừa xử lý |

Cả ba **không unit test nào bắt được** — chúng chỉ lộ khi chạy thật trên dữ liệu thật. Đó
là lý do UAT không phải bước thừa.

## 7. Chạy tay

```bash
export PYTHONIOENCODING=utf-8
python scripts/pipeline/campaign_step.py <chiến dịch> create-post --dry-run
python scripts/pipeline/approve_bus.py poller-status --campaign <chiến dịch>
python scripts/pipeline/web_publish.py --post <thư mục bài> --uat
```

`--uat` chép ra `.uat-web/` cạnh bài, **không đụng repo web**.
