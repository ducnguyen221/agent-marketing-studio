# Telegram làm TRUNG GIAN giữa người và agent trên máy cục bộ

> Tài liệu **cấp HỆ THỐNG** — trả lời: *tin nhắn của người đi vào máy bằng đường nào, ai
> nghe, ai làm, và khi đứt thì nối lại ra sao.*
>
> Ba tài liệu anh em: [`CAMPAIGN_PIPELINE.md`](CAMPAIGN_PIPELINE.md) (thứ tự bước và
> cổng) · [`APPROVAL_BUS.md`](APPROVAL_BUS.md) (cơ chế cổng) · file này (**vòng đời tiến
> trình và tính bền**).

---

## 1. Vì sao Telegram, chứ không phải web hay CLI

Agent chạy trên máy để bàn ở nhà. Không có IP tĩnh, không có HTTPS công khai, không muốn
mở cổng ra Internet. Nhưng người duyệt thì đi lại, và phải duyệt được từ điện thoại.

Telegram giải đúng bài đó: **máy chủ động gọi ra, không ai gọi vào.** Không mở cổng, không
tunnel, không chứng chỉ. Điện thoại nói chuyện với Telegram, máy cũng nói chuyện với
Telegram, hai bên không bao giờ thấy nhau.

---

## 2. Chuyện "50 giây" — hiểu sai chỗ này là thiết kế sai cả hệ

Đây là câu hỏi hay gặp nhất: *"tôi trả lời sau 50 giây thì có bị mất không?"*

**Không.** Có bốn lớp phủ chồng nhau, và phải hỏng cả bốn mới mất tin.

```
lớp 1  MỘT LƯỢT getUpdates
       xin Telegram giữ kết nối tối đa 50 giây.
       ⚠️ TRẢ VỀ NGAY khi có tin — 50 giây chỉ là trần lúc KHÔNG có gì.
       ⇒ độ trễ thật ≈ một vòng mạng, cỡ 1 giây.

lớp 2  VÒNG LẶP nối lượt          (receive_loop)
       hết 50 giây mà không có gì → gọi lượt mới NGAY, không nghỉ.
       ⇒ không hề có "khe hở 50 giây". Phủ liên tục 55 phút.

lớp 3  TASK SCHEDULER mỗi phút
       poller chết vì bất cứ lý do gì → tối đa 60 giây sau có con mới.
       Đang sống thì Windows từ chối lượt mới (IgnoreNew) + khoá file chặn lớp hai.

lớp 4  TELEGRAM GIỮ UPDATE 24 GIỜ
       máy tắt cả đêm, mất mạng, poller chết hẳn → tin vẫn nằm trên server.
       Poller sống lại, gửi `offset` cũ, nhận đủ những gì đã bỏ lỡ.
```

**`offset` là thứ giữ cho không mất và không lặp.** Sau mỗi lô, ta ghi `update_id lớn
nhất + 1` xuống đĩa. Telegram hiểu đó là "đã nhận tới đây rồi". Thiếu `+1` thì update cuối
quay lại mãi; thiếu ghi đĩa thì lượt sau xử lý lại tin cũ.

> **Kết luận thực dụng:** anh trả lời sau 5 phút, sau 5 tiếng, hay sau khi máy khởi động
> lại — đều nhận được. Thứ duy nhất thật sự mất là tin gửi khi máy tắt **quá 24 giờ**.

### Vì sao KHÔNG xin timeout to hơn

Đo ngày 10/09/2026 trên chính bot này: xin `timeout=100` và `timeout=60`, **cả hai đều trả
về sau 50,7 giây**. Tài liệu Bot API không công bố trần này. Nên 50 là trần thật; xin hơn
chỉ tốn chữ. Muốn phủ lâu hơn thì **nối nhiều lượt**, đó chính là lớp 2.

### Vì sao poller THOÁT sau 55 phút thay vì chạy mãi

Tiến trình sống mãi là thứ phải trông, và **chết câm thì kẹt cổng duyệt** mà không ai biết.
Thoát chủ động rồi để Task Scheduler dựng lại là **tự lành**: mỗi giờ có một con mới tinh,
rò rỉ gì cũng bị dọn, và trạng thái "còn sống" được chứng minh lại mỗi phút.

---

## 3. Toàn cảnh: tin nhắn đi vào máy bằng đường nào

```
 ĐIỆN THOẠI                TELEGRAM                    MÁY ĐỂ BÀN
 ──────────                ────────                    ──────────
                                          ┌──────────────────────────────────┐
                                          │ Task Scheduler — mỗi 1 phút      │
                                          │ MultipleInstances = IgnoreNew    │
                                          └───────────────┬──────────────────┘
                                                          │ (54/55 lượt bị từ chối)
                                                          ▼
                                          ┌──────────────────────────────────┐
                                          │ run-approve-poller.ps1           │
                                          │  └ approve_bus.py nhan --follow│
                                          │                                  │
     duyệt / góp ý ──►  giữ 24h  ◄────────┤  getUpdates(offset, timeout=50)  │
                                 ────────►│  trả về NGAY khi có tin          │
                                          │                                  │
                                          │  ┌── khoá 1 tiến trình ─────────┐│
                                          │  │ tg-poller.lock, nhịp tim mỗi ││
                                          │  │ chu kỳ, hạn 180 giây         ││
                                          │  └──────────────────────────────┘│
                                          └───────────────┬──────────────────┘
                                                          │ PHÂN LOẠI (vài ms)
                                   ┌──────────────────────┼──────────────────────┐
                                   ▼                      ▼                      ▼
                            ✅ ĐI TIẾP            ❌ KHÔNG ĐI TIẾP        📝 CÓ NHẬN XÉT
                         ghi g1 / publish.json    lý do = chữ của người   nguyên văn vào
                                   │                      │               feedback.json
                                   └──────────────────────┴──────────────────────┘
                                                          │ ghi MỘT dòng việc
                                                          ▼
                                          ┌──────────────────────────────────┐
                                          │ HÀNG CHỜ trên đĩa                │
                                          │ bền qua crash, chạy lại được     │
                                          └───────────────┬──────────────────┘
                                                          ▼
                                          ┌──────────────────────────────────┐
                                          │ THỢ — task riêng, khoá riêng     │
                                          │ ĐÚNG MỘT việc tại một thời điểm  │
                                          └───────────────┬──────────────────┘
                                                          ▼
                                          ┌──────────────────────────────────┐
                                          │ runtime.writer_cmd               │
                                          │ agent headless (~10 phút)        │
                                          └───────────────┬──────────────────┘
                                                          │
                                          báo kết quả ◄────┘ rồi mở cổng kế tiếp
```

**Luật vàng của sơ đồ này: POLLER KHÔNG BAO GIỜ LÀM VIỆC NẶNG.** Nó nghe và ghi, xong trong
vài mili giây. Mọi thứ tốn thời gian đều đi qua hàng chờ.

Vì sao: poller đang giữ khoá đọc Telegram. Cho nó chạy agent 10 phút thì **cổng duyệt điếc
suốt 10 phút đó**, nhịp tim đứng lại, lượt sau tưởng nó chết rồi cướp khoá — và ta quay lại
đúng vòng lặp đã làm sập máy ngày 11/09/2026.

---

## 4. Chữ của người đi vào agent thế nào

Đây là đường DUY NHẤT chữ người đi vào prompt, nên nó có luật riêng.

```
người gõ trên Telegram
   └─► logs/feedback.json      giữ ĐỦ mọi lần, KHÔNG ghi đè
        └─► <bài>/phan-hoi.md      trong khối có rào ```…```
             └─► bộ viết ĐỌC FILE  không nhận qua dòng lệnh
```

Ba luật, mỗi luật chặn một cách hỏng:

| Luật | Chặn cách hỏng nào |
|---|---|
| Phản hồi **KHÔNG mở cổng** | Nhầm chiều là đăng đúng bài đang bị chê |
| **Giữ đủ mọi lần**, không ghi đè | Vòng sửa lặp lại; ghi đè là mất dấu vết vì sao bài thành ra thế |
| Đi qua **FILE trong khối có rào**, không qua dòng lệnh | Chữ người là **dữ liệu**, không phải mệnh lệnh cho hệ thống |

---

## 5. RỦI RO VÒNG LẶP — bốn kiểu, và cách chặn từng kiểu

Đây là phần đắt nhất của tài liệu, vì **ba trong bốn kiểu đã xảy ra thật**.

### 5.1 Vòng lặp KHỞI ĐỘNG LẠI — đã xảy ra 11/09/2026

```
poller chết ngay khi vừa dựng  ──►  Task Scheduler thấy sạch  ──►  60 giây sau dựng lại
        ▲                                                                   │
        └───────────────────────────────────────────────────────────────────┘
                          nháy cửa sổ mỗi phút, suốt đêm
```

**Gốc:** khoá không được gia hạn, hoặc không được nhả. Con đang sống trông như chết nên bị
cướp khoá; con chết để lại khoá còn mới nên mọi lượt sau đều bỏ qua rồi thoát.

**Chặn bằng:** nhịp tim ghi mỗi chu kỳ (`renew_lock`) + luôn nhả trong `finally`
(`release_lock`). Cả hai đều có test đi kèm, và cả hai đều **đã từng bị gỡ mất** bởi một đợt
mutation testing bỏ quên trong working tree.

⚠️ **Task Scheduler chạy THẲNG working tree.** Sửa dở hoặc đột biến còn nằm đó là nó nuốt
luôn. Cổng kết thúc phiên: `git status --short` phải sạch.

### 5.2 Vòng lặp SỬA BÀI vô hạn

```
agent viết  ──►  người chê  ──►  agent viết lại  ──►  người chê  ──►  …
```

Mỗi vòng đốt ~10 phút agent. Không ai cố ý, nhưng một bài "gần đúng" có thể quay 10 vòng.

**Chặn bằng:** trần số lần viết lại (đề xuất **3**), đếm trong `.write-count.json`. Quá trần
thì **dừng và báo người quyết tay**, không tự quay tiếp.

### 5.3 Vòng lặp NHÂN TIẾN TRÌNH — đã xảy ra 11/09/2026

```
mỗi lượt duyệt spawn một agent  ──►  duyệt cả lô 10 bài  ──►  10 agent cùng chạy
        └─► mỗi agent kéo theo cả bộ MCP ──► 335 tiến trình, 16,4 GB RAM ──► máy sập
```

**Chặn bằng:** thợ chạy **đúng một việc tại một thời điểm**, có khoá riêng. Duyệt 10 bài
thì 10 việc nằm xếp hàng, không phải 10 agent cùng sống.

### 5.4 Vòng lặp HAI POLLER cướp nhau

```
poller A getUpdates ──┐
                      ├──► Telegram: "Conflict: terminated by other getUpdates request"
poller B getUpdates ──┘     yêu cầu MỚI giết yêu cầu CŨ ⇒ cả hai cùng hỏng
```

**Chặn bằng:** khoá file một-tiến-trình. `IgnoreNew` của Windows là chưa đủ, vì nó chỉ chặn
khi Windows còn *thấy* instance cũ.

**Ghi chú đã đo:** xung đột này **kêu to**, không im lặng. Chỉ cần đọc lỗi, không cần dựng
cổng phát hiện ngầm.

---

## 6. VỠ VÒNG thì nối lại thế nào

Nguyên tắc chung: **mọi trạng thái nằm trên đĩa, không nằm trong RAM.** Nên "nối lại" luôn
chỉ là chạy lại, không phải khôi phục gì.

| Vỡ ở đâu | Triệu chứng | Tự lành? | Nối lại bằng |
|---|---|---|---|
| Poller chết giữa chừng | không ai nghe Telegram | **có**, ≤60 giây | Task Scheduler dựng lại; `offset` trên đĩa nên không mất tin |
| Máy tắt qua đêm | im lặng | **có**, khi bật máy | Telegram giữ update 24 giờ |
| Máy tắt > 24 giờ | tin cũ mất | không | Gửi lại cổng: `approve_bus.py gui --gate g2` |
| Khoá mồ côi (chủ đã chết) | mọi lượt in `bo_qua_vi_lock` rồi thoát | **có**, sau 180 giây | Hết hạn tự bị cướp. Gấp thì xoá `logs/tg-poller.lock` |
| Agent chết giữa bài | bài dở dang | **có** | Việc còn trong hàng chờ → thợ nhặt lại. `_da_viet` bắt bài rỗng nên không lọt |
| Thợ chết giữa việc | việc treo | **có** | Việc chưa đánh dấu xong → lượt sau nhặt lại |
| 5 chu kỳ hỏng liên tiếp | poller tự thoát | **có**, ≤60 giây | Có chủ đích: thoát sạch còn hơn quay tít. Lùi dần 2→4→…→60 giây trước khi bỏ |
| `tg-approve.json` hỏng | token chờ mất | một phần | Coi như chưa có token; gửi lại cổng. **Không mất dấu vết duyệt nào** vì duyệt ghi ở `campaign.md`/`publish.json` |
| Hàng chờ hỏng | việc không chạy | không | Duyệt lại bài đó trên Telegram |

**Vì sao hỏng ở đâu cũng không mất dấu vết duyệt:** bus Telegram **không phải kho phê
duyệt**. Nó chỉ là mặt tiền. Cổng 1 sống ở cột `g1` trong `campaign.md`, Cổng 2 sống ở
`publish.json → posts[].review`. Xoá sạch `logs/` thì tệ nhất là phải gửi lại tin.

### Kiểm tra sức khoẻ khi nghi ngờ

```
approve_bus.py poller-status --campaign <đường dẫn>
```

Đọc ba con số: `nhip_vao.song` (poller còn thở không) · `tuoi_giay` (thở lần cuối bao lâu
rồi, phải < 180) · `cho_g1`/`cho_g2` (bài nào đang chờ cổng nào).

---

## 6b. Đã dựng xong những gì (12/09/2026)

| Mảnh | File | Vì sao có nó |
|---|---|---|
| Sổ sự kiện | `lib/event_log.py` → `logs/events.jsonl` | Trả lời *vì sao* bài tới trạng thái đó. Chỉ nối thêm nên không có cuộc đua |
| Trạng thái suy ra | `lib/pipeline_state.py` → `status` | Agent nối lại việc tốn **~350 token** thay vì 9.555 |
| Hàng chờ | `lib/work_queue.py` → `logs/jobs/` | Poller ghi việc rồi đi tiếp; không bao giờ tự chạy bước nặng |
| Thợ | `pipeline/worker.py` | Nhặt MỘT việc, gọi agent, rồi thoát |

**Ba luật đã trả giá để có, đừng gỡ:**

1. **Thợ không bao giờ đụng vào `await-G1`/`await-G2`.** Agent tự duyệt bài của chính nó là mất
   sạch ý nghĩa cổng. Chắn này có **hai lớp**, gỡ một lớp thì test vẫn xanh — phải gỡ cả hai
   mới thấy đỏ.
2. **Hỏi ARTEFACT, đừng hỏi mã thoát.** `blog_gates` trả mã 1 khi cổng đỏ, `soan` trả khác 0
   khi bài chưa đạt — cả hai **đã làm xong việc**. Tin mã thoát thì đúng những bài cần đi
   tiếp lại bị vứt vào `failed/`. (Đây là vế ngược của luật *"mã thoát 0 không đủ để tính là
   xong"* — cùng một nguyên tắc.)
3. **Bước phải giới hạn ĐÚNG MỘT BÀI** (`--post`). Bước vốn quét cả chiến dịch; thiếu cờ này
   thì một việc cho NEN-002 viết lại luôn NEN-001 và NEN-003 — đo thật **27 phút** cho một
   việc, và kế toán số lần viết lại thành vô nghĩa.

**Đường ống nay ĐỦ 6 bước, 3 cổng** (12/09/2026):

```
create-post ─[ Cổng 1 ]─ soan ─[ Cổng 2 ]─ build-page ─[ Cổng 3 ]─ release
```

Cổng 3 **chỉ bật khi bảng Content có khai cột `g3`** — chiến dịch cũ chạy y như trước.

Ba hook cho phần phụ thuộc máy, cùng luật với `writer_cmd`: `audio_cmd` (giọng clone),
`youtube_cmd`, `facebook_cmd`. Không khai thì bỏ qua, **không phải lỗi** — chiến dịch chỉ
có web vẫn chạy trót lọt.

⚠️ `dang` là **tên cũ** của `build-page`. Bản cũ không ghi URL ngược vào bảng nên
`pipeline_state` không bao giờ biết bài đã lên trang, và lượt sau lại đăng lần nữa. Nay nó uỷ
quyền cho `build-page`; lệnh cũ vẫn chạy và được luôn phần ghi URL.

## 7. Bảng tra nhanh khi có sự cố

| Thấy gì | Làm gì TRƯỚC TIÊN |
|---|---|
| Cửa sổ nháy mỗi phút | `git status` trong repo — task chạy thẳng working tree |
| Bấm nút không ăn | So `nhip` trong `tg-poller.lock` với giờ hiện tại. Đứng yên = khoá không được gia hạn |
| Poller báo `Conflict` | Có hai người đọc cùng token. Tìm tiến trình thứ hai, đừng đổi timeout |
| RAM tăng vọt, nhiều `node`/`cmd` | Đếm tiến trình MCP. **Kiểm `ParentProcessId` trước khi giết** — app-server hợp lệ cũng không có cửa sổ |
| Duyệt rồi mà không thấy gì chạy | Xem hàng chờ có dòng việc không; xem task thợ có đang chạy không |
