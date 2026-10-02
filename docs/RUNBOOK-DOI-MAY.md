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
    --with-git --include-logs-state --for-machine <tên máy đích>

# 3b. Gói giọng cá nhân (chạy bằng python của venv trạm giọng)
<OMNIVOICE_PY> -m voice_studio export --personal --out <…>/voice.zip

# 3c. Gói video cá nhân (tuỳ chọn)
<OMNIVOICE_PY> -m video_studio export --personal --out <…>/video.zip
```

- `--out` phải nằm **ngoài** trạm, nếu không gói tự nuốt chính nó.
- `--with-git` kèm `.git/` — một gói, đủ lịch sử. Bỏ cờ này là bỏ luôn lịch sử. Lịch sử
  mang theo **mọi** thứ trạm từng commit: trạm nào từng commit secret (vd `subscribe.gs`
  trước khi bị gỡ khỏi git) thì **đừng** dùng cờ này khi khoá đó chưa được xoay.
- `--for-machine <tên>` đổi sẵn `engines.json` cho máy đích (mục *Thứ tự engine* ở bước 5).
- `--include-logs-state` kèm trạng thái trong `logs/` (tin đang chờ duyệt, hàng việc, nhật
  ký sự kiện). **Đổi máy thì luôn bật cờ này**; sao lưu định kỳ thì không cần.
- `export` **từ chối** đóng gói thứ trông như secret (`*token*.json`, `*client_secret*`,
  `*credentials*`, mọi đường trong kho secret) và **loại** `subscribe.gs` (mã Apps Script mang
  secret thật, máy đích không cần). Đó là chủ đích: secret đi đường riêng, do chính bạn chép
  tay (bước 5).
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
| Repo web đích | `git -C <thư mục cha chứa các repo>/<repo web> pull` (hoặc `clone` nếu chưa có). `channel.yml` nên ghi `repo:` TƯƠNG ĐỐI (`news/ai`) hoặc `${WEB_REPO_DIR}/ai` để không phải sửa theo máy | bạn |
| Biến môi trường | `separate`: `setx` (Windows) / khoá `EnvironmentVariables` trong plist (macOS) · `embedded`: `<repo>/.env` | bạn |
| `run.ps1` cho MỌI chiến dịch chạy theo lịch | plist launchd gọi `<trạm>/<kênh>/<chiến dịch>/run.ps1`. Chiến dịch máy nguồn gọi thẳng runner (vd truyện P2 gọi `run-daily-truyen-p2.ps1`) chưa từng có file này: chép `templates/station/_channel/_campaign/run.ps1` của repo vào đó — nó đọc `runtime.runner` của `campaign.md` rồi gọi đúng runner. `station.py export` liệt kê chiến dịch thiếu; `install_launchd.py` (kể cả `--dry-run`) và `doctor` báo **mã 2** cho job đã khai mà thiếu file (P1-19) | bạn |
| Công cụ chạy thật: ffmpeg **có libfreetype + libass**, `requirements-runners.txt` vào venv giọng | macOS: `brew install ffmpeg-full` (keg-only — repo tự dò `/opt/homebrew/opt/ffmpeg-full/bin`; `brew install ffmpeg` bản core thiếu `drawtext`/`subtitles`) · Windows: Gyan full. Rồi `<OMNIVOICE_PY> -m pip install -r requirements-runners.txt`. `doctor` đỏ khi có chiến dịch truyện mà thiếu bộ lọc hoặc `decode_audio` vỡ (P0-8, P0-9) | bạn |

⚠️ **launchd KHÔNG đọc `~/.zshrc`, `~/.zprofile` hay `~/.bash_profile`.** Biến bạn đặt
trong shell chỉ tồn tại trong shell. Job theo lịch chỉ thấy những gì khai trong
`EnvironmentVariables` của plist — và `install_launchd.py` điền sẵn khối đó từ
`studio_paths`, nên hãy để nó điền thay vì sửa tay plist.

### Thứ tự engine — gói mang theo thứ tự của máy NGUỒN, không phải của máy này

`<trạm>/_agent-call/engines.json` đi theo gói bàn giao (nó là JSON nhỏ ở gốc trạm, và luật
lọc mặc định là *giữ*). Nghĩa là máy đích vừa import xong đang chạy **thứ tự engine của máy
cũ** — im lặng, mã 0, không có gì đỏ. Máy nguồn có thể đặt Claude đứng đầu vì tài khoản
Claude ở đó rỗi; máy đích có thể muốn engine chạy bằng credit khác đứng đầu.

Mỗi máy có **một** `engines.json` riêng trên đĩa, không sync, không dùng chung — nên khoá
`order` trong file của máy nào là nguồn sự thật của **máy đó**, và không có lớp chọn theo
hostname nào cả (thêm một lớp như vậy chỉ thêm một chỗ có thể chọn sai âm thầm mà không bỏ
được bước nào). Thứ tự của các máy khác nằm ở khoá ghi chú `_may_khac` — lúc chạy **không**
dòng mã nào đọc nó; chỉ `station.py export --for-machine` đọc khi đóng gói.

`export --for-machine <tên máy đích>` làm sẵn ba việc dưới đây trong bản đi theo gói
(`_may_khac.<tên>` khai `order`, và tuỳ chọn `nen_tang`, `_ly_do`). Gói xuất **không** có cờ
đó thì sau khi import, mở `<trạm>/_agent-call/engines.json` và tự làm đúng ba việc:

1. Sửa `_may.ten` / `_may.nen_tang` cho đúng máy đang đứng.
2. Thay mảng `order` bằng mảng `order` trong `_may_khac.<tên máy này>` (nếu có mục đó).
3. Xoá mục `_may_khac.<tên máy này>` vừa dùng, và thêm vào `_may_khac` một mục cho **máy
   nguồn** với thứ tự cũ. Thứ tự của mỗi máy chỉ được xuất hiện đúng một lần trong cả hệ.

Kiểm bằng một lượt không tốn hạn mức:

```sh
python -c "import sys; sys.path.insert(0,'scripts/lib'); import agent_call as AC; \
cfg=AC.load_config(); print(AC.config_path()); print(cfg['order']); \
print(AC.build_chain('claude','best',cfg))"
```

Còn phải kiểm riêng trên máy mới: `engines.<tên>.cmd` — đường cài `claude`/`codex`/`agy`
trên macOS khác Windows, và một `cmd` sai chỉ lộ ra ở lượt lịch đầu tiên.

### Hai pipeline, hai cấu hình — đừng gộp

Tin và truyện chạy **cùng một engine giọng** nhưng **không** dùng chung cấu hình. Đây là
chỗ dễ sai nhất khi dựng trạm trên Mac, và sai thì cả hai bên vẫn báo ✅:

| | **TIN** (`daily-news-a/b`, `weekly-news-a/b`, `weekly-repo`) | **TRUYỆN** (`daily-story`) |
|---|---|---|
| `OMNIVOICE_DTYPE` | **`float32`** | **`float16`** |
| `HF_DEACTIVATE_ASYNC_LOAD` | **không khai** | **`1`, bắt buộc** |
| Trần giờ | wrapper: 2 h (ngày) · 3 h (tuần) | runner: **30600 s = 8 h 30** + chạy tiếp 1 lần 10800 s · wrapper (lưới an toàn): 42300 s |
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
- **Quá trần thì runner tự chạy tiếp MỘT lần (P1-23):** `run-daily-truyen.ps1` chạy
  `daily_truyen.py` qua `story/resume_once.py`. Mã 124 mà `_resume.json` còn dải dở ⇒ tin ⏳
  "quá trần — đang chạy tiếp từ chương X" ⇒ chạy lại dùng cache chương (trần 3 h) ⇒ ✅/❌ như
  thường. Lượt chạy tiếp lại 124 ⇒ dừng, không lặp. Không còn ai phải `launchctl kickstart`
  tay. Trần của wrapper (plist 42300 s; Windows `ExecutionTimeLimit` do `-Register` tính) phải
  ≥ tổng hai trần, nếu không nó giết luôn lượt chạy tiếp. **Windows đã có task truyện cũ**
  (tạo tay, trần 6 h): `run-daily-truyen.ps1 -Register -Campaign <thư mục> -TaskName '<tên task
  cũ>'` để GHI ĐÈ đúng task đó; `-Register` in WARN nếu thấy task khác trỏ cùng chiến dịch — hai
  task cùng giờ chạy song song cùng dải và xoá `_work` của nhau.
- **Không tự chạy tiếp khi bị giết lúc ĐANG ĐĂNG:** `daily_truyen.py` ghi `phase: publish` vào
  `_resume.json` ngay trước khi upload; quá trần từ đó trở đi thì bộ canh KHÔNG chạy tiếp (video
  có thể đã lên mà chưa ghi state — chạy tiếp là đăng trùng). Lượt theo lịch đêm sau cũng DỪNG
  (`PUBLISH_GUARD=blocked`) cho tới khi người gỡ — log in sẵn lệnh: kênh ĐÃ có tập ⇒
  `<python giọng> scripts/runners/story/daily_truyen.py --state <truyen-state.json>
  --confirm-published` (ghi đúng `last_end`/`next_url`); CHƯA có ⇒ `--clear-publish-guard`.
  Đừng sửa `truyen-state.json` tay: `last_end` đúng là chương THẬT cuối (manifest), và nguồn
  pntt2 cần cả `next_url`.
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
  `--map <label>=<kênh>/<chiến dịch>`. Thiếu khai ⇒ dừng ở **mã 2**, không đoán. Định dạng
  đầy đủ (runner khác `run.ps1`, con trỏ bí mật theo kênh, đổi lịch): [`launchd.md`](launchd.md).
- `worker`, `approve-poller`, `daily-story` **không** nằm trong bộ mặc định: phải gọi đích
  danh bằng `--only`, hoặc `--all`. Ba job đó hoặc chạy liên tục, hoặc chạy hàng giờ giữa
  đêm — bật chúng phải là một câu bạn gõ ra.
- `weekly-cleanup` (dọn dung lượng tuần) **chỉ** `--only` — `--all` cũng bỏ qua. Trước khi bật:
  `pwsh scripts/runners/run-weekly-cleanup.ps1 -DryRun` và đọc báo cáo (sẽ dời gì, giữ gì vì
  thiếu bằng chứng). Windows: `run-weekly-cleanup.ps1 -Register` (cần `NOTIFY_RUN`).
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
   (2 h cho lượt ngày, 3 h cho lượt tuần, 1 h cho dọn tuần; lượt truyện 42300 s là **lưới an
   toàn** — runner truyện tự canh 8 h 30 rồi tự chạy tiếp một lần 3 h, xem mục hai pipeline). Quá giờ thì wrapper giết
   **cả nhóm tiến trình con** (không chỉ cái vỏ — `run.ps1` đẻ ra ffmpeg, node, python),
   gửi tin ❌ ghi rõ "QUÁ GIỜ", và thoát mã 1. Đây là **ngoại lệ duy nhất** của luật "mã
   thoát = mã của lệnh con": khi bị giết thì không có mã con nào để trả.
2. **Job sống dài thì tự đặt trần của nó.** `run-approve-poller.ps1` thoát sau
   `-AliveSeconds` (mặc định 3300 s) rồi để `KeepAlive` dựng lại; `run-worker.ps1` làm một
   việc rồi thoát. Hai job này **không** bọc `notify_run` — chúng chạy mỗi phút, báo
   Telegram mỗi lượt là hàng nghìn tin một ngày.
3. **Nhìn được từ ngoài:** `launchctl print gui/$UID/<label>` in `state = running` kèm PID.
   Một job theo lịch mà còn `running` sau giờ cao nhất của nó là dấu hiệu treo.

## Khởi động lại định kỳ máy chạy lịch — Đức quyết, CHƯA bật

**Vì sao nghĩ tới (P1-24, Mac mini 02/10/2026):** Hot AI 18:00 hỏng sau 42 phút vì môi trường
render của macOS kẹt (`Navigation timeout` ở frame 0 với mọi project; `WindowServer` 21 % và
`coreaudiod` 14 % CPU lúc máy rảnh). Khởi động lại máy là hết. Từ 1.1.8 runner tin **phát hiện
sớm** (`video-studio probe` trước nghiên cứu/TTS, mã 5, tin ❌ "khởi động lại máy rồi chạy lại")
— nhưng phát hiện vẫn mất một lượt. Khởi động lại định kỳ là cách **phòng**.

Repo **không** tự làm việc này: macOS cần quyền admin, và khởi động lại một máy là quyết định của
chủ máy. Nếu bật, làm tay một lần:

```sh
sudo pmset repeat restart U 05:00:00      # Chủ nhật 05:00 (U = Sunday trong pmset)
pmset -g sched                            # kiểm lịch đã đặt
sudo pmset repeat cancel                  # bỏ (xoá MỌI lịch repeat của pmset)
```

Ba điều phải kiểm TRƯỚC khi bật:

1. **Job lịch là LaunchAgent của người dùng** — sau khởi động lại chúng chỉ chạy khi người dùng
   đã đăng nhập. Máy phải bật tự đăng nhập (FileVault bật thì không tự đăng nhập được). Dấu hiệu
   đạt: sau lần mất điện 01/10 cả 6 plist tự nạp lại. Kiểm lại sau lần khởi động lại đầu tiên:
   `launchctl print gui/$UID/studio.marketing.daily-news-a`.
2. **Không cắt ngang lượt đang chạy.** Truyện bắt đầu 00:00 và có thể kéo tới ~11:30 nếu quá
   trần rồi chạy tiếp (8 h 30 + 3 h). Khởi động lại 05:00 CN sẽ giết lượt đó: hoặc chọn giờ khác,
   hoặc chấp nhận mất lượt truyện Chủ nhật (cache chương + `_resume.json` vẫn còn, lượt thứ Hai
   đọc tiếp đúng dải đó). Dọn tuần CN 04:00 xong trong vài phút — nằm trước 05:00.
3. **Windows** (nếu máy lịch là Windows): một task Task Scheduler `shutdown /r /t 60` với cùng
   lưu ý — task chạy "chỉ khi người dùng đăng nhập" sẽ không chạy cho tới khi có người đăng nhập.

Ghi quyết định (bật/không, giờ nào) vào `<trạm>/MAY-DANG-CHAY.md`.

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
