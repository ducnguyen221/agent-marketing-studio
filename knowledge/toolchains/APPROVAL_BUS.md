# APPROVAL_BUS — cổng duyệt qua Telegram, chế độ tự trị, và đăng web

> Ba mảnh nối nhau: **ai duyệt** (`approve_bus.py`) · **chạy tới đâu thì dừng**
> (`campaign_step.py`) · **bài đi đâu** (`web_publish.py`).
> Hợp đồng cấp BÀI của một bài blog nằm ở [`ATLAS_CHANNEL.md`](ATLAS_CHANNEL.md) — file này
> nói về tầng ĐIỀU PHỐI ở trên nó.

## 1. Ba bước rời, hai cổng ở giữa

```
dung-bai ──[ Cổng 1 ]── soan ──[ Cổng 2 ]── dang
   │                      │                   │
   │ new_post             │ gen_article       │ web_publish
   │ --dien-vao-dong      │ blog_gates (23)   │ fb_publish
   │                      │ register_publish  │ register_publish set
   │                      │   init            │
```

**Vì sao rời chứ không gộp.** Script điều phối gộp đã bị gỡ vì nó *gộp dựng và đăng vào một
lệnh, nên một bước hỏng là phải chạy lại từ đầu, và cổng duyệt của người bị nuốt vào giữa
chuỗi*. Mỗi bước ở đây chạy lại được độc lập, và hai cổng nằm **giữa** các bước chứ không
lẫn vào trong.

**Mỗi lượt gọi = một bước.** `run.ps1 -Buoc dung-bai` / `-Buoc soan` / `-Buoc dang`.

## 2. Cổng nằm ở đâu — KHÔNG có kho thứ hai

| Cổng | Chỗ ở THẬT | Ai ghi |
|---|---|---|
| **g1** duyệt đề tài | cột `g1` + `status` trong bảng Content của `campaign.md` | `approve_bus`, qua `md_io` |
| **g2** duyệt trước khi đăng | `publish.json → posts[].review` | `register_publish approve` |

`approve_bus.py` là **mặt tiền**, không phải kho. File trạng thái riêng của nó
(`logs/tg-approve.json`) chỉ giữ hai thứ của riêng Telegram: con trỏ `offset` và các token
đang chờ. Xoá nó đi thì tệ nhất là phải gửi lại tin — **không mất một dấu vết duyệt nào**.

## 3. Hai chế độ

`channel.yml:autonomy` quyết mỗi cổng dừng hay tự mở.

| Mức | Cổng 1 | Cổng 2 | Dùng khi |
|---|---|---|---|
| `suggest` *(mặc định)* | dừng, gửi Telegram | dừng, gửi Telegram | Nội dung có tên mình trên đó |
| `full` | tự mở | tự mở | Đã tin quy trình, chấp nhận không ai đọc trước khi đăng |

**Fail-closed ba lớp:** giá trị lạ → `suggest` · `campaign.md` không đè được `autonomy` ·
chỉ NGƯỜI sửa `channel.yml`. Cả ba đều có test, và test đã được kiểm bằng đột biến.

## 4. Duyệt qua Telegram

```
approve_bus.py gui  --campaign <đường dẫn> --cong g1|g2 [--lo N] [--che-do per_post|batch_gate]
approve_bus.py nhan --campaign <đường dẫn>
approve_bus.py trang-thai --campaign <đường dẫn>
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
trình duy nhất poll con bot đó. Thêm một bên tiêu thụ nữa là cả hai ăn trộm update của
nhau — **im lặng**, không bên nào báo lỗi. Cần thêm thì tách bot riêng.

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

## 6. Ba cái bẫy đã trả giá ở tầng này

| Bẫy | Hình dạng | Cách chặn |
|---|---|---|
| **Bước hỏng vẫn `exit=0`** | Task Scheduler đọc mã thoát rồi báo ✅ cho một lượt không làm được gì | `ma_thoat()` suy từ KẾT QUẢ, có test |
| **Lịch lập trước, `new_post` không điền được** | `new_post` giả định nó TẠO dòng nên gặp dòng có sẵn là dừng | chế độ `--dien-vao-dong`, chỉ ghi cột `folder` |
| **Hai chế độ lệch nhau** | dựng 3 bài mà tin xin duyệt hỏi 10 | `gui_cong(cids=…)` hỏi đúng những bài vừa xử lý |

Cả ba **không unit test nào bắt được** — chúng chỉ lộ khi chạy thật trên dữ liệu thật. Đó
là lý do UAT không phải bước thừa.

## 7. Chạy tay

```bash
export PYTHONIOENCODING=utf-8
python scripts/pipeline/campaign_step.py <chiến dịch> dung-bai --dry-run
python scripts/pipeline/approve_bus.py trang-thai --campaign <chiến dịch>
python scripts/pipeline/web_publish.py --bai <thư mục bài> --uat
```

`--uat` chép ra `.uat-web/` cạnh bài, **không đụng repo web**.
