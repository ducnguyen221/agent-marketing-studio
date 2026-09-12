# Chạy chiến dịch TRONG PHIÊN — hợp đồng của agent

> **Đây là quy trình MẶC ĐỊNH.** Agent ngồi cùng người trong một phiên chạy trọn đường ống
> từ đầu tới cuối, dừng ở ba cổng để hỏi người ngay tại chỗ.
>
> **Telegram là TUỲ CHỌN**, dùng khi người không ngồi trước máy. Nó là mặt tiền thứ hai của
> đúng cùng một kho cổng, không phải một quy trình khác. Xem
> [`TELEGRAM_BRIDGE.md`](TELEGRAM_BRIDGE.md).
>
> Bản mô tả máy đọc được của mọi thứ dưới đây:
> [`../data_model/pipeline.yaml`](../data_model/pipeline.yaml). Đổi một bên mà quên bên kia
> thì `tests/test_pipeline_spec.py` đỏ.

## 1. Một hình vẽ

```
create-post ─[ Cổng 1 ]─ soan ─ check-gates ─[ Cổng 2 ]─ build-page ─[ Cổng 3 ]─ release
                              └ fix-gates ┘
                                (tối đa 3 vòng)
```

Ba cổng là của **người**. Sáu bước còn lại agent chạy được hết.

| | Ai làm | Ai quyết |
|---|---|---|
| Bước máy | agent / script | — |
| Cổng | — | **người**, bằng một câu nói thật |

## 2. Agent làm gì, theo thứ tự

### Bước 0 — nhìn tình hình trước khi động vào gì

```
python scripts/pipeline/run_pipeline.py <chiến dịch> status
```

Trả về bài nào đang ở bước nào, xếp theo đúng thứ tự đường ống. **Đọc cái này trước** thay
vì nạp cả `campaign.md` — 90 dòng brief không giúp gì cho câu hỏi "giờ làm gì tiếp".

### Bước 1 — hỏi người muốn chạy kiểu nào

Đây là **câu hỏi bắt buộc**, không được tự quyết:

| Chế độ | Khi nào | Người bị hỏi mấy lần |
|---|---|---|
| `per-post` | bài quan trọng, hoặc đang dò xem quy trình chạy đúng chưa | mỗi bài một lần ở mỗi cổng |
| `by-stage` | chạy đều nhiều bài | **một lần cho cả lô** ở mỗi cổng |

Và hỏi luôn **bao nhiêu bài**: một bài cụ thể (`--post NEN-004`), N bài (`--count 5`), hay
làm hết (`--count 0`). Mặc định 5 nếu người không nói gì.

### Bước 2 — chạy tới cổng gần nhất

```
python scripts/pipeline/run_pipeline.py <chiến dịch> run \
       --mode by-stage --count 5
```

Lệnh này chạy **nhiều bước liên tiếp** rồi dừng khi đụng cổng. Nó **không bao giờ tự mở
cổng**. Thêm `--dry-run` để trình người xem kế hoạch trước khi chạy thật.

### Bước 3 — báo cáo lại cho người

Sau mỗi lượt chạy, agent **phải** nói đủ năm thứ. Bỏ thứ nào thì người mất khả năng kiểm,
và cổng thành con dấu cao su:

1. **bước vừa chạy, cho bài nào**
2. **artefact sinh ra, kèm ĐƯỜNG DẪN ĐẦY ĐỦ** để người bấm mở được ngay
3. **kết quả chấm cổng** nếu bước đó có chấm — xanh mấy, đỏ mấy, đỏ ở cổng nào
4. **bước kế tiếp** mà `status` suy ra
5. nếu đã tới cổng — **câu hỏi cần người trả lời**, và **danh sách file phải đọc** trước khi
   trả lời

`run_pipeline.py` in sẵn mục 5 dưới dạng bảng file. Agent chép lại vào câu trả lời của
mình, không bắt người tự đi lục thư mục.

### Bước 4 — người trả lời, agent GHI LẠI

Người nói "ok, duyệt bài 004 và 005" hay "bài 004 mở bài dài quá, cắt bớt". Agent ghi vào
kho cổng, **chép nguyên văn câu người vừa nói**:

```
python scripts/pipeline/approval_gate.py <chiến dịch> open --gate g2 \
       --post NEN-004,NEN-005 --by "Đức" --quote "ok, duyệt bài 004 và 005"

python scripts/pipeline/approval_gate.py <chiến dịch> reject --gate g2 \
       --post NEN-004 --by "Đức" --quote "mở bài dài quá, cắt bớt"
```

⚠️ **`--quote` không phải thủ tục giấy tờ.** Nó là thứ ngăn agent tự đóng dấu thay
người: chép được câu của người thì câu đó phải đã tồn tại. Thiếu nó, lệnh **từ chối chạy**.

Từ chối có kèm nhận xét thì nhận xét vào kho phản hồi, và vòng viết lại đọc đúng chỗ đó.

### Bước 5 — quay lại bước 2

Lặp cho tới khi bài `xong` hoặc người bảo dừng.

## 2b. Mỗi bước gọi script nào

Bảng tra nhanh. Bình thường agent chỉ gọi `run_pipeline.py` và nó tự chọn; bảng này để
**gỡ rối khi một bước hỏng** — biết bước đó thực ra chạy cái gì thì mới đọc log đúng chỗ.

| Bước | Script thi hành | Lệnh gọi thẳng | Sinh ra |
|---|---|---|---|
| `create-post` | `scripts/pipeline/new_post.py` | `campaign_step.py <cd> create-post` | thư mục bài + `meta.json` + `publish.json` + khung `content.md` |
| `write` | hook `runtime.writer_cmd` | `campaign_step.py <cd> write --post <mã>` | `research.md` · `content.md` · `atlas/` `facebook/` `youtube/` |
| `check-gates` | `scripts/pipeline/blog_gates.py` | `blog_gates.py <thư mục bài>` | `gates.json` |
| `fix-gates` | hook `runtime.writer_cmd` (đọc thêm `phan-hoi.md`) | `campaign_step.py <cd> write --post <mã>` | `content.md` viết lại |
| `build-page` | `build_blog_html.py` + `web_publish.py` (+ hook `audio_cmd`) | `campaign_step.py <cd> build-page --post <mã>` | `atlas/atlas.html` + URL vào cột `web` |
| `release` | hook `youtube_cmd` + `facebook_cmd` | `campaign_step.py <cd> release --post <mã>` | URL vào cột `youtube` / `facebook` |

Cổng và tra cứu:

| Việc | Script |
|---|---|
| Xem bài nào ở bước nào | `run_pipeline.py <cd> status` |
| Đẩy bài tới cổng gần nhất | `run_pipeline.py <cd> run --mode per-post\|by-stage` |
| Xem ai đang chờ cổng, kèm file để mở | `approval_gate.py <cd> waiting --gate g1\|g2\|g3` |
| Mở / từ chối cổng | `approval_gate.py <cd> open\|reject --gate … --post … --by … --quote …` |
| Gửi cổng qua Telegram (tuỳ chọn) | `approve_bus.py send --campaign <cd> --gate g1` |
| Sinh lại trang đọc | `build_views.py --campaign <cd>` |
| Xuất Excel | `export_excel.py --campaign <cd>` |
| Vì sao bài tới trạng thái này | đọc `logs/events.jsonl` |
| Di trú tên dữ liệu cũ sang mới | `migrate_names.py <cd> [--apply]` |

Chạy nền (không dùng trong phiên): `scripts/runners/run-worker.ps1` cho thợ,
`scripts/runners/run-approve-poller.ps1` cho poller Telegram,
`scripts/runners/run-blog-campaign.ps1 -Step create-post` cho task theo lịch.

⚠️ Bốn hook đều **không khoá CLI nào**: không khai thì bước đó bỏ qua chứ không phải lỗi.
Khai ở khối `runtime:` của `campaign.md`, và chỗ điền là `{post}` (đường dẫn thư mục bài).

## 3. Ba cổng hỏi gì, và mở file nào để trả lời

| Cổng | Câu hỏi | Người cần mở |
|---|---|---|
| **g1** — đề tài | Có làm bài này không? Tiêu đề và góc nhìn đã đúng chưa? | dòng trong bảng Content (chưa có file) |
| **g2** — trước khi đăng | Bài này đăng được chưa, hay cần sửa gì? | `content.md` · `gates.json` · `research.md` |
| **g3** — bản thật | Mở link xem bằng mắt rồi mới cho ra kênh ngoài | `atlas/atlas.html`, và **link web thật** |

**Cổng 2 fail-closed ba nhánh** — bài không được đem ra hỏi khi còn một trong ba:

- chưa viết
- chưa chấm cổng nào (thiếu `gates.json`) — *không đo được* nghĩa là *chưa biết*, không phải *đã qua*
- máy chấm ĐỎ — máy đã nói không thì đừng đem hỏi người

**Cổng 3 chỉ bật khi bảng Content có khai cột `g3`.** Bảng không có cột đó thì không có cổng
này, và chiến dịch cũ chạy y như trước.

## 4. Hai luật agent hay vi phạm nhất

### Mã thoát KHÔNG phải phép thử — sai cả hai chiều

- `blog_gates` trả mã 1 khi kết luận đỏ, `soan` trả khác 0 khi bài chưa đạt. **Cả hai đã làm
  xong việc.** Đọc mã thoát rồi báo hỏng thì bài bị làm lại ba lần rồi vứt đi — đúng những
  bài cần sửa thì không ai sửa.
- Chiều ngược lại: bộ viết chạy êm, mã 0, mà `content.md` vẫn là khuôn trống.

Cách chữa cho cả hai: **hỏi artefact** mà bước đó phải sinh ra. `run_pipeline.py` đã làm
sẵn; agent gọi tay từng lệnh con thì phải tự nhớ.

### Việc theo BÀI, đừng để bước quét cả chiến dịch

Các bước `soan`, `fix-gates`, `build-page`, `release` mặc định quét **cả chiến dịch**.
Chạy một bài thì phải truyền `--post <mã>`. Quên cờ đó thì một lượt cho NEN-002 viết lại luôn
NEN-001 và NEN-003: số lần viết lại đếm sai nên trần chống-quay-tít mất nghĩa, và lượt chạy
kéo hàng giờ.

## 5. Khi nào dùng Telegram

Ba trường hợp, không phải mặc định:

1. **Người không ngồi trước máy** mà vẫn muốn duyệt.
2. **Chạy theo lịch** — thợ `worker.py` chạy nền, tới cổng thì phải báo ai đó.
3. **Người chủ động xin** — "gửi lên Telegram cho tôi duyệt".

Trong phiên, agent **có thể đề nghị** gửi Telegram nếu thấy người sắp rời máy, nhưng mặc
định là hỏi thẳng trong phiên. Hai đường ghi vào cùng một chỗ, nên duyệt đường nào cũng để
lại cùng một dấu vết và không bao giờ lệch nhau.

## 6. Người xem tiến độ ở đâu

| Muốn gì | Mở cái gì |
|---|---|
| Nhìn nhanh trong phiên | `run_pipeline.py <cd> status` |
| Trang đọc, bấm đúp là mở | `campaign.html` — mục *Tiến độ đường ống* và *Đang chờ mình quyết*, có link mở thẳng từng file |
| Bảng để lọc / xoay / gửi người khác | `export_excel.py --campaign <cd>` — cột `pipeline_step` nói bài tắc ở đâu |
| Vì sao bài tới trạng thái này | `logs/events.jsonl` |

Sinh lại trang đọc: `python scripts/pipeline/build_views.py --campaign <cd>`.

## 7. Thứ agent KHÔNG được làm

- **Không tự mở cổng.** Kể cả khi chắc chắn người sẽ đồng ý.
- **Không bịa `--quote`.** Câu đó phải là câu người thật sự đã nói.
- **Không sửa tay bảng Content** để đánh dấu duyệt. Đi qua `approval_gate.py` để còn dấu vết
  trong sổ sự kiện và để giữ tính idempotent.
- **Không đọc `.xlsx` làm nguồn.** Nó là bản xuất một chiều; nguồn là `campaign.md`.
- **Không báo "đã đăng" khi kênh hỏng.** Báo phát hành trong khi chưa là cách hỏng tệ nhất —
  không ai đi kiểm lại và bài nằm im mãi ở trạng thái "xong".
