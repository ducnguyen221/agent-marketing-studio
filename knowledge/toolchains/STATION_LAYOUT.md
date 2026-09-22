# Bố cục ba trạm — ai giữ gì, ai gọi ai, biến nào trỏ đâu

> Tài liệu **bản đồ**: đọc khi bạn cần biết một thứ nằm ở đâu và ai được phép ghi vào nó.
> Dựng máy mới theo thứ tự: [`ONBOARDING.md`](../../docs/ONBOARDING.md).
> Chuyển máy: [`RUNBOOK-DOI-MAY.md`](../../docs/RUNBOOK-DOI-MAY.md).
> Từng thư mục trong trạm nội dung chứa gì: [`WORKSPACE.md`](../../docs/WORKSPACE.md).

## 1. Ba trạm, một repo mỗi trạm

| Trạm | Repo engine | Giữ gì | Biến định vị |
|---|---|---|---|
| **Trạm nội dung** | repo này | kênh, chiến dịch, bài, `engine/`, trạng thái đã đăng, `Auto Task.xlsx` | `MARKETING_STUDIO_DATA` |
| **Trạm giọng** | `agent-voice-studio` | profile giọng, thư viện nhạc nền, venv engine, trọng số mô hình | `VOICE_STATION` |
| **Trạm video** | `agent-video-studio` | project dựng hình, tài sản video, bản HyperFrames ghim | `VIDEO_STATION` |

Ba trạm là **dữ liệu**; ba repo là **máy**. Repo public và thay được; trạm là của bạn và
nằm ngoài git của repo (trạm nội dung có git riêng).

### Một trạm bắt buộc, hai trạm tuỳ chọn

**Chỉ trạm nội dung là bắt buộc.** Lõi — viết bài và đăng — chạy được với mình nó; bản cài
**không bắt buộc trạm giọng/video**. Hai trạm kia là **năng lực thêm**:

| | cần khi | thiếu thì `doctor` |
|---|---|---|
| trạm nội dung | luôn luôn | **mã 3** — chưa cài xong |
| trạm giọng | muốn lồng tiếng (podcast, video có giọng đọc) | **mã 0**, ghi *"giọng: chưa bật — cần khi bạn muốn …"* |
| trạm video | muốn dựng video | **mã 0**, ghi *"video: chưa bật — …"* |

Lời đề nghị cài hai trạm tuỳ chọn nằm ở **chỗ chạm**, không ở `doctor`: `voice.py` /
`video.py` ném `StationMissing` (**mã 3**) kèm đủ các bước cài, đúng lúc một bước thật sự
cần tới chúng. Hỏi lúc cài là bắt người chưa biết mình có làm audio hay không phải quyết
định ngay; báo đỏ lúc cài là dạy họ bỏ qua `doctor`.

### Ai gọi ai

```
trạm nội dung ──(subprocess, đọc dòng JSON cuối stdout)──► voice_studio   (đọc)
      │                                                     video_studio  (dựng hình)
      │                                                          │
      └── cả hai package cài vào CÙNG MỘT venv: venv của trạm giọng
          (torch là phụ thuộc nặng duy nhất, cả hai đều cần)
```

Phía trạm nội dung: `scripts/lib/voice.py` và `scripts/lib/video.py`. Chúng gọi
`OMNIVOICE_PY -m voice_studio …` / `-m video_studio …`, đọc **dòng JSON cuối** của stdout
(log người đọc đi stderr — không bao giờ `2>&1`), và dịch mã thoát thành exception có tên.

**Mã thoát chung cho cả ba trạm:** `0` ok · `1` engine/render hỏng (thử lại có thể qua) ·
`2` hợp đồng sai (thiếu biến, thiếu `brand`, thiếu profile — sửa cấu hình) · `3` trạm
thiếu (chạy `doctor`, cài tiếp). `notify_run.py` chuyển mã con **nguyên vẹn**, trừ đúng
một ca: quá `--timeout` thì nó trả `1` vì không còn mã con nào để trả.

## 2. Bên trong trạm nội dung

```
<trạm>/
  AUTHOR.md            người đứng tên, giọng chung          NGƯỜI viết
  CHANNELS.md          sổ kênh — nguồn sự thật DUY NHẤT     script ghi thêm
  MAY-DANG-CHAY.md     nhật ký máy nào đang chạy lịch       NGƯỜI nối thêm dòng
  launchd.json         khai kênh/chiến dịch cho từng job    NGƯỜI viết (macOS)
  engine/              mã chạy lịch, composer báo cáo        tên CỐ ĐỊNH
  logs/launchd/        log job launchd                      máy ghi
  <kênh>/
    channel.yml        hồ sơ kênh MÁY đọc (khối `brand:`)   NGƯỜI viết
    brand.md           nhận diện + giọng, NGƯỜI đọc         NGƯỜI viết
    assets/            ảnh/logo riêng của kênh              NGƯỜI bỏ vào
    <chiến dịch>/
      campaign.md      brief + cấu hình + bảng bài          NGƯỜI viết — NGUỒN SỰ THẬT
      run.ps1          điểm vào DUY NHẤT, giống hệt mọi nơi chép từ khuôn
      logs/            bản chụp cấu hình, hàng việc, sự kiện máy ghi, cấm sửa tay
      out/             sản phẩm + dấu đã đăng               máy ghi
      <bài>/           research.md · content.md · publish.json
```

`engine/` là **tên cố định**, luôn nằm ngay dưới gốc trạm. Bên trong chỉ có mã chạy lịch
của trạm nội dung — không tài sản video, không thư viện nhạc.

⚠️ **`engine/` mang ngữ nghĩa điều khiển, không chỉ là chỗ chứa file: hoặc nó KHÔNG tồn
tại, hoặc nó đủ bộ chạy.** `run.ps1` chỉ hỏi `Test-Path <trạm>/engine`; thấy thư mục là nó
bỏ đường lùi và đi tìm runner trong đó. Một thư mục rỗng — hay một thư mục ra đời vì có
lệnh ghi file vào `<trạm>/engine/x.json` và lệnh đó tự tạo thư mục cha — bật đúng nhánh
"đã dọn xong" trong khi chưa dọn gì, và **mọi** chiến dịch cùng chết một lúc ở lượt lịch kế
tiếp. Cấu hình theo máy để ở `<trạm>/_agent-call/`, không để trong `engine/`. Cổng canh:
`python scripts/pipeline/check_engine.py --check-station <đường>` (và `doctor` chạy cùng
luật đó); luật đầy đủ + sự cố đã trả giá nằm trong docstring `scripts/lib/engine_dir.py`.

`<kênh>/assets/` khác `out/`: `assets/` là nguyên liệu bạn bỏ vào và **luôn đi theo gói
chuyển máy**; `out/` là sản phẩm, chỉ có phần *dấu vết đã đăng* (`*-top.json`,
`*.published.json`) đi theo, còn mp4/ảnh thì không.

## 3. Gói chuyển máy — cái gì đi, cái gì ở lại

Danh sách **khai rõ**, không phải "chép tất trừ…": `scripts/lib/station_manifest.py`.
Docstring của file đó là nguồn sự thật cho ba vùng lọc (theo thư mục · theo tên file ·
danh sách từ chối). **Đừng chép luật đó sang đây** — đọc thẳng file.

Ba điều đáng nhớ:

- `export` **từ chối** đóng gói thứ trông như secret (`*token*.json`, `*client_secret*`,
  `*credentials*`, mọi đường trong kho secret). Secret đi đường riêng, do người chép tay.
- `import` **không đè** file đã có. Đích phải là thư mục trống, hoặc một trạm bạn cố ý gộp.
- `import` đổi đường Windows thành `~` trong `*.yml *.md *.py *.ps1 *.json` (trừ `out/`),
  và in một khối **SOÁT** liệt kê riêng các file `.py`/`.ps1` vừa bị đổi. `~` trong chuỗi
  Python **không tự nở** — đọc khối đó.

Lệnh cụ thể và thứ tự sáu bước: [`RUNBOOK-DOI-MAY.md`](../../docs/RUNBOOK-DOI-MAY.md).

## 4. Bảng biến môi trường — ba trạm, một chỗ tra

> Biến của **repo này** (ai đọc, không đặt thì sao) có bảng riêng, chi tiết hơn, ở
> [`SECRETS.md`](SECRETS.md). Bảng dưới đây là bản đồ **cả ba trạm**, kể cả biến mà repo
> này chỉ **truyền tiếp** qua plist chứ không tự đọc.

### 4a. Định vị

| Biến | Nghĩa | Không đặt thì |
|---|---|---|
| `MARKETING_STUDIO_DATA` | gốc trạm nội dung | `--station` → `studio.local.json` → `<repo>/workspace/` → `~/.marketing` |
| `MARKETING_STUDIO_HOME` | thư mục repo nội dung | `~/Code/agent-marketing-studio` |
| `MARKETING_STUDIO_PY` | Python chạy các `.ps1` | `<repo>/.venv` → `python` → `python3` → `py`; khai mà hỏng thì **DỪNG** |
| `VOICE_STATION` | gốc trạm giọng | tên cũ `OMNIVOICE_DIR` (trỏ **thư mục engine** bên trong, lùi một cấp là ra gốc) → `studio.local.json` → coi như chưa cài |
| `OMNIVOICE_PY` | Python venv trạm giọng — chỗ cài **cả hai** package | `station.json: venv` của trạm giọng (đường tương đối tính từ gốc trạm) → dò `omnivoice/.venv` |
| `VOICES_DIR` | kho profile giọng | `<trạm giọng>/<engine>/voices` |
| `VIDEO_STATION` | gốc trạm video | tên cũ `VIDEO_ROOT` → `studio.local.json` → coi như chưa cài |
| `HYPERFRAMES_VERSION` | bản HyperFrames trạm video ghim | `station.json` của trạm video |

### 4b. Công cụ dựng hình (repo nội dung đọc)

| Biến | Nghĩa | Không đặt thì |
|---|---|---|
| `CHROME_BIN` | Chrome/Edge/Chromium để dựng ảnh | dò đường quen của hệ điều hành → PATH |
| `FFMPEG_DIR` | thư mục chứa `ffmpeg` + `ffprobe` | Windows: thư mục WinGet → PATH · macOS: PATH → Homebrew |
| `FFPROBE` | đường `ffprobe` riêng | như `FFMPEG_DIR` |
| `VIDEO_FONT` | font `.ttf/.otf` khi tự vẽ chữ | font hệ thống |

### 4c. Biến của trạm giọng mà lịch phải khai hộ (macOS)

Repo này **không đọc** ba biến dưới; nó chỉ ghi chúng vào khối `EnvironmentVariables` của
plist để tiến trình con nhận được. Trên Apple Silicon, thiếu chúng là chạy `float32` trên
CPU — chậm gấp nhiều lần, hoặc nổ lúc nạp trọng số.

| Biến | Giá trị trên Apple Silicon | Vì sao |
|---|---|---|
| `OMNIVOICE_DEVICE` | `mps` | ép dùng GPU tích hợp; không đặt thì engine tự dò `cuda → mps → cpu` |
| `OMNIVOICE_DTYPE` | **theo pipeline** — xem bảng dưới | mặc định của engine là `float32` cho mọi thứ không phải CUDA |
| `HF_DEACTIVATE_ASYNC_LOAD` | **chỉ pipeline truyện** | tắt nạp trọng số bất đồng bộ — bắt buộc khi nạp fp16 trên MPS |

**Hai pipeline, hai cấu hình — không dùng chung một bộ:**

| | **TIN** (`daily-news-a/b`, `weekly-news-a/b`, `weekly-repo`) | **TRUYỆN** (`daily-story`) |
|---|---|---|
| `OMNIVOICE_DTYPE` | `float32` | `float16` |
| `HF_DEACTIVATE_ASYNC_LOAD` | **không khai** | `1` |
| Trần giờ wrapper | 2 h (ngày) · 3 h (tuần) | 30600 s (8 h 30) |

Lượt tin 4–12 phút trong cửa sổ 18:00–21:00 ⇒ thừa thời gian, đổi tốc độ lấy độ chính
xác; nó không đi nhánh fp16 nên vụ nổ mà `HF_DEACTIVATE_ASYNC_LOAD` vá không tồn tại ở
đây. Lượt truyện đọc 5 h 47 ⇒ thời gian mới là thứ khan hiếm, và fp16 trên MPS thì biến
kia là bắt buộc. `worker`/`approve-poller` không khai cái nào (không chạy TTS). Chi tiết
và cách nghiệm thu từng pipeline: [`../../docs/RUNBOOK-DOI-MAY.md`](../../docs/RUNBOOK-DOI-MAY.md)
mục *Hai pipeline, hai cấu hình*.

### 4d. Secret — luật ba tầng

> `channel.yml` khai **TÊN BIẾN** · biến giữ **ĐƯỜNG DẪN** · file JSON ngoài git giữ
> **GIÁ TRỊ**.

`TG_CONFIG`, `FB_CONFIG`, `YT_TOKEN_PATH`, `YT_CLIENT_SECRET`, `EMAIL_CONFIG` — tất cả
đều giữ *đường dẫn*. Chi tiết và cách lấy token: [`SECRETS.md`](SECRETS.md) +
[`PLATFORM_SETUP.md`](PLATFORM_SETUP.md).

### Đặt biến ở đâu

| Chế độ cài | Chỗ đặt |
|---|---|
| `separate` | cấp user: `setx` (Windows) · khối `EnvironmentVariables` trong plist (macOS) |
| `embedded` | `<repo>/.env` — được nạp bởi `studio_paths.secret_env()`, và **chỉ** khi `studio.local.json: mode = embedded`. Biến môi trường thật vẫn thắng file. |

⚠️ **launchd không đọc `~/.zshrc`.** Job theo lịch chỉ thấy biến khai trong plist của
chính nó. `scripts/runners/install_launchd.py` điền khối đó từ `studio_paths` — để nó
điền, đừng sửa tay plist đã nạp.

## 5. Lịch chạy

| | Windows | macOS |
|---|---|---|
| Bộ lập lịch | Task Scheduler | launchd |
| Mẫu | — | `templates/launchd/*.plist` (8 job) |
| Cài | `Register-ScheduledTask` | `scripts/runners/install_launchd.py` |
| Một bản chạy tại một lúc | `MultipleInstances = IgnoreNew` | launchd bảo đảm sẵn theo `Label` |
| Trần thời gian một lượt | `ExecutionTimeLimit` | **không có** ⇒ `notify_run.py --timeout` |
| "Mỗi N ngày" | `DaysInterval` | **không có** ⇒ chạy mỗi ngày, lượt chạy tự bỏ ngày lẻ |

Ba job **không** nạp mặc định (`worker`, `approve-poller`, `daily-story`): chúng hoặc chạy
liên tục, hoặc chạy hàng giờ giữa đêm. Bật chúng phải là một câu người ta gõ ra.

`worker` và `approve-poller` **không** bọc `notify_run`: chúng chạy mỗi phút, báo Telegram
mỗi lượt là hàng nghìn tin một ngày. Chúng tự báo khi có chuyện.
