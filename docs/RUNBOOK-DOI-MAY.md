# Runbook — đổi máy chạy trạm (Windows ↔ macOS)

> Viết cho **người không nhớ gì về đợt chuyển này**. Mỗi bước có: làm gì · gõ gì · nhìn gì
> để biết đã xong · lùi ra sao. Đọc hết một lượt trước khi gõ lệnh đầu tiên.
>
> Bố cục ba trạm, tên biến, ai gọi ai: [`STATION_LAYOUT.md`](../knowledge/toolchains/STATION_LAYOUT.md).
> Thư mục nào trong trạm chứa gì: [`WORKSPACE.md`](WORKSPACE.md).

## Luật số 0 — MỘT MÁY CHẠY TẠI MỘT THỜI ĐIỂM

Hai máy cùng bật lịch trên cùng bộ nội dung thì cả hai cùng đúng và cùng sai:

- cùng lấy một đề tài, dựng hai video, **đăng hai lần** lên cùng một kênh;
- `*.published.json`, `covered-repos.json`, `truyen-state.json` mỗi bên ghi một nửa sự
  thật, và bên nào import sau sẽ **xoá dấu vết của bên kia** trong lần đồng bộ tiếp theo;
- bot Telegram nhận duyệt hai lần (`getUpdates` chỉ giao một bản — bên kia mất cú bấm).

Không có khoá kỹ thuật nào chặn chuyện đó. Thứ duy nhất chặn là **nhật ký máy đang chạy**
ở bước 0 và việc bạn làm đúng thứ tự dưới đây.

### Nhật ký máy đang chạy

File `<trạm>/MAY-DANG-CHAY.md` — đi theo gói export nên hai máy luôn thấy cùng một bản.
Mỗi lần chuyển, **nối thêm một dòng**, không sửa dòng cũ:

```
2026-11-03 21:40  TẮT   may-windows   (5 job Ready -> Disabled, hàng việc rỗng)
2026-11-03 22:15  BẬT   mac-mini      (import xong, 5 job đã bootstrap)
```

Dòng cuối cùng nói máy nào đang chạy. **Nếu dòng cuối là "BẬT" của một máy khác máy bạn
đang ngồi: DỪNG.** Đi tắt bên đó trước.

---

## Bước 0 — Trước khi động vào gì (máy NGUỒN)

| Kiểm | Lệnh | Đạt khi |
|---|---|---|
| Đang ở đúng máy | đọc `<trạm>/MAY-DANG-CHAY.md` | dòng cuối là "BẬT" của chính máy này |
| Cây trạm liền mạch | `python scripts/pipeline/check_tree.py` | `0 đỏ` |
| Bản cài đủ | `python scripts/pipeline/doctor.py` | mã 0 — và **đọc các dòng nhắc**: "giọng/video chưa bật" là bình thường, "chưa dùng được" nghĩa là máy nguồn đang làm audio/video mà máy đích chưa bật xong |
| Repo sạch | `git -C <trạm> status --short` | rỗng (trạm có git từ P0) |

Chưa đạt thì sửa **trước**, đừng mang một cây gãy sang máy mới: sang bên kia bạn sẽ không
biết chỗ gãy là do chuyển máy hay đã gãy sẵn.

---

## Bước 1 — Tắt lịch ở máy NGUỒN

**Windows**

```powershell
# Xem trạng thái trước khi đổi — chụp lại để còn biết cái gì vốn đang bật
Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' } | Select-Object TaskName, State

Disable-ScheduledTask -TaskName '<tên task>'      # từng task một, không dùng ký tự đại diện
```

**macOS**

```sh
launchctl print gui/$UID | grep studio.marketing   # xem cái gì đang nạp
python scripts/runners/install_launchd.py --uninstall --only studio.marketing.daily-news-a
```

Gỡ đủ **mọi** job của trạm, kể cả `worker`, `approve-poller`, `daily-story` nếu bạn từng
bật chúng (`install_launchd.py --list` in đủ danh sách).

**Đạt khi:** không job nào còn ở trạng thái chạy được. Trên Windows mọi task liên quan là
`Disabled`; trên macOS `launchctl print gui/$UID` không còn nhãn `studio.marketing.*`.

**Lùi:** `Enable-ScheduledTask -TaskName '<tên>'` · `install_launchd.py --only <label>`.

---

## Bước 2 — Chờ lượt đang chạy kết thúc

Tắt lịch **không** giết lượt đang chạy. Cắt ngang giữa chừng là cách chắc chắn nhất để có
một video đã upload mà chưa kịp ghi `*.published.json` — lần sau nó upload lại.

```powershell
# Hàng việc của chiến dịch: phải RỖNG
Get-ChildItem "<trạm>\<kênh>\<chiến dịch>\logs\jobs\running" -ErrorAction SilentlyContinue
```

```sh
ls "<trạm>/<kênh>/<chiến dịch>/logs/jobs/running"        # phải rỗng
```

**Đạt khi:** `logs/jobs/running/` rỗng ở **mọi** chiến dịch, và không còn tiến trình
`pwsh`/`python`/`ffmpeg` nào của trạm.

Việc nằm lại `running/` quá 30 phút được coi là mồ côi và tự quay về `pending/` — đó là
hành vi bình thường, không phải lỗi. Nhưng đừng export lúc nó đang nửa vời: chờ, hoặc để
nó về `pending/` rồi mới export.

Ghi dòng "TẮT" vào `<trạm>/MAY-DANG-CHAY.md` **ngay tại đây**, trước khi export — có thế
nó mới nằm trong gói.

---

## Bước 3 — Đóng gói (máy NGUỒN)

Ba gói độc lập. Làm đủ cả ba nếu máy đích chưa có gì; bỏ gói giọng/video nếu bạn **không**
đổi profile giọng và tài sản video.

```sh
# 3a. Trạm nội dung — kênh, chiến dịch, engine, trạng thái đã đăng, lịch sử git
python scripts/pipeline/station.py export \
    --station <trạm> --out <thư mục ngoài trạm>/marketing.zip \
    --with-git --include-logs-state

# 3b. Gói giọng cá nhân (chạy bằng python của venv trạm giọng)
<OMNIVOICE_PY> -m voice_studio export --personal --out <…>/voice.zip

# 3c. Gói video cá nhân (tuỳ chọn)
<OMNIVOICE_PY> -m video_studio export --personal --out <…>/video.zip
```

- `--out` phải nằm **ngoài** trạm, nếu không gói tự nuốt chính nó.
- `--with-git` kèm `.git/` — một gói, đủ lịch sử. Bỏ cờ này là bỏ luôn lịch sử.
- `--include-logs-state` kèm trạng thái trong `logs/` (tin đang chờ duyệt, hàng việc, nhật
  ký sự kiện). **Đổi máy thì luôn bật cờ này**; sao lưu định kỳ thì không cần.
- `export` **từ chối** đóng gói thứ trông như secret (`*token*.json`, `*client_secret*`,
  `*credentials*`, mọi đường trong kho secret). Đó là chủ đích: secret đi đường riêng, do
  chính bạn chép tay (bước 5).
- Muốn xem trước mà không ghi gì: thêm `--dry-run`.

**Đạt khi:** ba lệnh đều in số file và đường zip; `marketing.zip` **dưới 250 MB**. Lớn hơn
thì mở manifest ra xem cái gì chui vào (`unzip -l`), đừng gửi đi một gói bạn không hiểu.

**Lùi:** xoá file zip. `export` chỉ đọc, không đụng vào trạm.

---

## Bước 4 — Mở gói (máy ĐÍCH)

Trước hết máy đích phải có **repo + Python + phụ thuộc**. Chưa có thì đọc
[`ONBOARDING.md`](ONBOARDING.md) phần "Máy mới" rồi quay lại đây.

```sh
python scripts/pipeline/station.py import <…>/marketing.zip --station <trạm đích>
<OMNIVOICE_PY> -m voice_studio import <…>/voice.zip
<OMNIVOICE_PY> -m video_studio import --in <…>/video.zip
```

Ba lệnh ba kiểu nhận file khác nhau (vị trí · vị trí · cờ `--in`) — đọc kỹ, đừng gõ theo
trí nhớ.

**Ba điều phải biết trước khi gõ:**

1. **`import` KHÔNG đè.** File đã có ở trạm đích thì được giữ nguyên và báo là bỏ qua. Nên
   `--station` phải trỏ vào **thư mục trống** (hoặc một trạm bạn cố ý gộp thêm). Muốn làm
   lại từ đầu: xoá thư mục đích rồi import lại — đừng import chồng hai lần và hy vọng.
2. **Đường dẫn quá sâu.** Windows chặn ở 259 ký tự; `station.py` kiểm trước và báo, nhưng
   hãy tự chọn một đích ngắn (`C:\tram` chứ không phải một cây lồng năm tầng).
3. **`import` đổi đường Windows thành `~`** trong `*.yml *.md *.py *.ps1 *.json` (trừ
   `out/`). Cuối báo cáo có một khối **SOÁT** liệt kê riêng các file `.py`/`.ps1` vừa bị
   đổi — **đọc khối đó**. `~` trong một chuỗi Python **không tự nở**: một hằng đường dẫn
   trong `.py` sau khi đổi sẽ hỏng, chỉ khác là bây giờ nó hỏng nhìn thấy được.

**Đạt khi:** báo cáo `import` nói đủ số file §4, `check_tree.py` in `0 đỏ`, và `doctor`
chỉ còn đỏ ở những thứ bạn biết là chưa cài. Máy vừa nhận gói thường chưa cài xong trạm
giọng/video; từ 21/09/2026 việc đó **không** làm `doctor` đỏ nữa — nó ghi *"giọng: chưa
bật …"* và trả mã 0, vì viết bài và đăng chạy được mà không cần hai trạm ấy. `import`
vẫn **cố tình không** lấy mã thoát của `doctor`: chuyện còn đỏ ở máy đích là chuyện của
bước sau, không phải thước đo cho việc gói đã bung đúng hay chưa.

**Lùi:** xoá thư mục trạm đích, import lại từ zip. Gói zip là bản gốc, giữ nó cho tới khi
máy đích chạy trót lọt một lượt thật.

---

## Bước 5 — Secret, repo phụ, biến môi trường (máy ĐÍCH)

| Thứ | Cách | Ai làm |
|---|---|---|
| Kho secret (`~/.secret/<tài khoản>/`) | chép tay từ máy cũ; đặt quyền `700` cho thư mục, `600` cho file | **người**, không phải script |
| Repo web đích | `git -C ~/Code/<repo web> pull` (hoặc `clone` nếu chưa có) | bạn |
| Biến môi trường | `separate`: `setx` (Windows) / khoá `EnvironmentVariables` trong plist (macOS) · `embedded`: `<repo>/.env` | bạn |

⚠️ **launchd KHÔNG đọc `~/.zshrc`, `~/.zprofile` hay `~/.bash_profile`.** Biến bạn đặt
trong shell chỉ tồn tại trong shell. Job theo lịch chỉ thấy những gì khai trong
`EnvironmentVariables` của plist — và `install_launchd.py` điền sẵn khối đó từ
`studio_paths`, nên hãy để nó điền thay vì sửa tay plist.

### Hai pipeline, hai cấu hình — đừng gộp

Tin và truyện chạy **cùng một engine giọng** nhưng **không** dùng chung cấu hình. Đây là
chỗ dễ sai nhất khi dựng trạm trên Mac, và sai thì cả hai bên vẫn báo ✅:

| | **TIN** (`daily-news-a/b`, `weekly-news-a/b`, `weekly-repo`) | **TRUYỆN** (`daily-story`) |
|---|---|---|
| `OMNIVOICE_DTYPE` | **`float32`** | **`float16`** |
| `HF_DEACTIVATE_ASYNC_LOAD` | **không khai** | **`1`, bắt buộc** |
| Trần giờ của wrapper | 2 h (ngày) · 3 h (tuần) | **30600 s = 8 h 30** |
| Mỗi lượt | 4–12 phút · bản tuần ~41 phút | TTS 5 h 47 · cả lượt ≈ 6 h 05 |

- **Vì sao tin dùng fp32:** lượt tin nằm gọn trong cửa sổ 18:00–21:00 và thừa thời gian,
  nên đổi tốc độ lấy độ chính xác là đáng. Nó không đi nhánh fp16, mà vụ nổ lúc nạp trọng
  số bất đồng bộ trên MPS **chỉ xảy ra ở nhánh fp16** — nên `HF_DEACTIVATE_ASYNC_LOAD`
  không có việc gì để làm ở đây, và khai thừa chỉ làm người sau tưởng hai bên giống nhau.
- **Vì sao truyện dùng fp16:** với 5 h 47 chỉ riêng TTS thì **thời gian** mới là thứ khan
  hiếm. Đã fp16 trên MPS thì `HF_DEACTIVATE_ASYNC_LOAD=1` là bắt buộc — thiếu là crash
  ngay lúc nạp model.
- **Trần giờ truyện không được hạ sát 6 h:** 6 h 05 là số đo trên máy **rảnh**; lượt hằng
  đêm còn crawl và dựng video chen vào. Trần cũ 21600 s (6 h) giết lượt đúng lúc nó vừa
  đọc xong mà chưa kịp dựng video — mất trọn 6 tiếng đã chạy.
- `worker` và `approve-poller` **không khai** cả hai biến: chúng không chạy TTS.

Cấu hình này nằm trong `templates/launchd/*.plist`; `tests/test_launchd_templates.py`
(bảng `GIONG`, `TRAN_GIO`) đỏ nếu có ai gộp hai bộ lại làm một. **Nghiệm thu trên Mac phải
chạy từng pipeline một**, không dùng chung một cấu hình cho cả hai.

**Đạt khi:** `python scripts/pipeline/doctor.py` trả mã **0**.

---

## Bước 6 — Bật lịch ở máy ĐÍCH, từng job một

> **Cấm bật lịch khi chưa import trạng thái.** Job chạy trên một trạm thiếu
> `*.published.json` sẽ coi mọi bài là chưa đăng và đăng lại tất cả.

**macOS**

```sh
python scripts/runners/install_launchd.py --list                 # xem có những job nào
python scripts/runners/install_launchd.py --dry-run              # xem sẽ ghi gì, không ghi
python scripts/runners/install_launchd.py --only studio.marketing.daily-news-a
```

- Khai kênh/chiến dịch một lần trong `<trạm>/launchd.json`, hoặc từng lần bằng cờ
  `--map <label>=<kênh>/<chiến dịch>`. Thiếu khai ⇒ dừng ở **mã 2**, không đoán.
- `worker`, `approve-poller`, `daily-story` **không** nằm trong bộ mặc định: phải gọi đích
  danh bằng `--only`, hoặc `--all`. Ba job đó hoặc chạy liên tục, hoặc chạy hàng giờ giữa
  đêm — bật chúng phải là một câu bạn gõ ra.
- Kiểm một job: `launchctl print gui/$UID/<label>`; log ở `<trạm>/logs/launchd/<label>.*.log`.

**Windows**

```powershell
Enable-ScheduledTask -TaskName '<tên task>'
Start-ScheduledTask  -TaskName '<tên task>'      # chạy thử NGAY một lượt
```

**Bật từng cái một, chờ một lượt thật xong rồi mới bật cái tiếp theo.** Bật cả năm cùng
lúc rồi Telegram im lặng thì bạn không biết cái nào hỏng.

**Đạt khi:** mỗi job đã chạy **một lượt thật**, Telegram nhận tin ✅ kèm đủ link sản phẩm.
❌ thì đọc tin: nó nói hỏng ở bước nào và đã xong bước nào.

Ghi dòng "BẬT" vào `<trạm>/MAY-DANG-CHAY.md`.

**Lùi:** `install_launchd.py --uninstall --only <label>` · `Disable-ScheduledTask`. Rồi
bật lại máy cũ theo đúng runbook này chạy ngược.

---

## launchd không có giới hạn thời gian — và bạn phải tự canh

Task Scheduler của Windows có `ExecutionTimeLimit`: quá giờ thì **bộ lập lịch** giết lượt
chạy. **launchd không có khoá tương đương.** `ExitTimeOut` chỉ là thời gian ân hạn giữa
SIGTERM và SIGKILL *sau khi đã bảo job dừng*; nó không đặt trần cho một lượt bình thường.

Hậu quả nếu bỏ qua: một lượt treo (mạng chết giữa lúc tải, ffmpeg chờ stdin, một tiến
trình con đợi mãi) sẽ treo **vô hạn**. launchd coi nhãn đó là "đang chạy", nên lượt kế
tiếp theo lịch **bị bỏ qua lặng lẽ** — và không có gì báo, vì chẳng lượt nào kết thúc để
mà báo. Sáng hôm sau bạn chỉ thấy: hôm qua không có bài.

**Cách canh, theo thứ tự nên dùng:**

1. **`notify_run.py --timeout <giây>`** — cách chính, và là thứ các plist mẫu đã bật sẵn
   (2 h cho lượt ngày, 3 h cho lượt tuần, **8 h 30 cho lượt truyện**). Quá giờ thì wrapper giết
   **cả nhóm tiến trình con** (không chỉ cái vỏ — `run.ps1` đẻ ra ffmpeg, node, python),
   gửi tin ❌ ghi rõ "QUÁ GIỜ", và thoát mã 1. Đây là **ngoại lệ duy nhất** của luật "mã
   thoát = mã của lệnh con": khi bị giết thì không có mã con nào để trả.
2. **Job sống dài thì tự đặt trần của nó.** `run-approve-poller.ps1` thoát sau
   `-AliveSeconds` (mặc định 3300 s) rồi để `KeepAlive` dựng lại; `run-worker.ps1` làm một
   việc rồi thoát. Hai job này **không** bọc `notify_run` — chúng chạy mỗi phút, báo
   Telegram mỗi lượt là hàng nghìn tin một ngày.
3. **Nhìn được từ ngoài:** `launchctl print gui/$UID/<label>` in `state = running` kèm PID.
   Một job theo lịch mà còn `running` sau giờ cao nhất của nó là dấu hiệu treo.

### Và launchd cũng không dịch được "cách ngày"

Hai lượt tin hằng ngày trên Windows đặt `DaysInterval = 2`. launchd **không có** khái niệm
đó: `StartCalendarInterval` là lịch theo giờ/phút/thứ/ngày-trong-tháng, còn `StartInterval`
đếm từ lúc nạp job nên nó trôi mỗi lần khởi động máy và bắn ngay khi nạp.

Plist mẫu chọn: chạy **mỗi ngày** đúng giờ, và để chính lượt chạy quyết định có làm hay
không. **Trước khi bật hai job đó, hãy kiểm lượt chạy có tự bỏ ngày lẻ không** — nếu không
thì nó ra bài gấp đôi bản Windows. Ghi chú này cũng nằm ngay trong hai file plist mẫu.

---

## Bảng lùi nhanh

| Hỏng ở đâu | Lùi thế nào |
|---|---|
| Export ra gói sai/thiếu | xoá zip, chạy lại — `export` không đụng trạm |
| Import vào nhầm chỗ | xoá thư mục đích, import lại từ zip |
| Import đã đổi hỏng một đường trong `.py`/`.ps1` | đọc khối **SOÁT** trong báo cáo, sửa tay đúng file đó |
| Bật nhầm job trên macOS | `install_launchd.py --uninstall --only <label>` |
| Máy đích chạy sai, muốn về máy cũ | chạy runbook này theo chiều ngược: tắt đích → chờ → export đích → import nguồn → bật nguồn |
| Hai máy lỡ cùng bật | tắt **cả hai** ngay, so `MAY-DANG-CHAY.md` và `*.published.json` hai bên trước khi chọn bên nào là bản thật |
