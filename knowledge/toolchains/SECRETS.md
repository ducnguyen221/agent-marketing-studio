# Nối bí mật cho kênh và chiến dịch mới

> **Đọc trước khi dựng kênh mới, hoặc khi một script cần token/mật khẩu.**
>
> Một luật, và mọi thứ dưới đây chỉ là hệ quả của nó:
>
> **Cấu hình giữ TÊN BIẾN. Biến giữ ĐƯỜNG DẪN. File giữ GIÁ TRỊ.**
> Không bao giờ đảo thứ tự đó.

---

## Vì sao ba tầng chứ không phải một

| Nếu làm thế này | Cái gì hỏng |
|---|---|
| Ghi giá trị vào `channel.yml` | `channel.yml` nằm trong trạm, bị sao chép, bị chia sẻ, bị zip. Một bản sao là một bản rò rỉ. |
| Ghi đường dẫn cứng vào code | Đổi máy là gãy. Đổi chỗ file là gãy. Và tên người dùng nằm luôn trong code. |
| Ghi giá trị vào biến môi trường | Token Google **tự ghi đè file** mỗi lần làm mới — nó cần một file thật, không phải một chuỗi. Và biến môi trường thì không mở ra đọc được khi cần lấy tay. |
| **Ba tầng như trên** | Đổi chỗ file → sửa một biến. Đổi tài khoản → sửa một file. Chia sẻ cấu hình → không lộ gì. |

Chữ **`PATH`** trong `YT_TOKEN_PATH` là cố ý: biến giữ *đường dẫn tới file*, không giữ nội
dung. Nhờ vậy file vẫn mở ra đọc được — và thư viện Google vẫn ghi đè được khi làm mới token.

### Tầng "biến" đặt ở đâu — hai chế độ cài

| Chế độ cài | Đặt biến ở | `<repo>/.env` |
|---|---|---|
| `separate` (máy nhiều trạm, repo public của chính bạn) | cấp user: `setx` (Windows) · `EnvironmentVariables` trong plist launchd (macOS) | **không được nạp** — repo có thể là bản public của bạn, tự nạp một file lạ trong đó là mở cửa |
| `embedded` (mặc định cho người mới) | `<repo>/.env` | **được nạp**, bởi `studio_paths.secret_env()`, và chỉ khi `studio.local.json: mode = embedded` |

Biến môi trường thật luôn **thắng** `.env`. Và `.env` không phá luật ba tầng: nó nằm ở tầng
**biến**, nên nó giữ *đường dẫn* và cấu hình máy — **không bao giờ** giữ token. Rào cho nó:
`.gitignore` (`.env`, `.env.*`, trừ `.env.example`) + hook `templates/hooks/pre-commit` +
`doctor.py` (kiểm cả hai còn sống, và kiểm quyền 600 trên POSIX).

---

## Thư mục bí mật

Bí mật sống ở **một thư mục ngoài mọi kho git**, mặc định `~/.secret/`, gom theo **TÀI KHOẢN**
chứ không theo kênh:

```
~/.secret/
├── README.md                    ← MỤC LỤC: biến nào ↔ file nào ↔ ai đọc
├── <nền-tảng>-<tài-khoản>/      ← vd: youtube-kenh-a/, facebook-trang-b/
└── telegram/config.json         ← bot + danh sách chat
```

**Một tài khoản = một file, dù bao nhiêu kênh dùng chung.** Nhân bản là chỗ mà một bản được
cập nhật còn bản kia thì không — và bạn chỉ phát hiện lúc pipeline chạy lúc 19h.

Ba lý do thư mục này không được nằm trong kho git, kể cả kho riêng tư:

1. `.gitignore` là **một dòng text**; `git add -f` bỏ qua nó không cần hỏi.
2. Máy có thể chạy nhiều phiên agent song song — một `git add -A` sai chỗ là xong.
3. Riêng tư trên GitHub vẫn là **đã rời khỏi máy**; token vào lịch sử commit thì xoá không đơn giản.

Cắt kế thừa quyền **trước** khi copy byte đầu tiên vào đó. Copy trước rồi siết sau là để hở
một cửa sổ mà file nằm dưới quyền kế thừa của thư mục cha.

---

## Dựng kênh mới — bốn bước

### 1. Kênh dùng tài khoản ĐÃ CÓ (trường hợp thường gặp)

Mở `~/.secret/README.md`, tìm dòng của tài khoản đó, chép **tên biến** vào `channel.yml`:

```yaml
platforms:
  - channel: youtube
    handle: "Tên kênh · @handle"
    post_formats: [youtube_video]
    secrets_env: { token: YT_TOKEN_PATH, client: YT_CLIENT_SECRET }
  - channel: facebook
    handle: "Tên Page · id 1234567890"
    post_formats: [facebook_post]
    secrets_env: { config: FB_CONFIG }
```

Hết. Không tạo file mới, không `setx` gì thêm.

### 2. Kênh dùng tài khoản MỚI

```
① tạo ~/.secret/<nền-tảng>-<tài-khoản>/ và đặt file vào
② đặt biến <TÊN_BIẾN> = "<đường dẫn>" ở cấp user, để task theo lịch nhìn thấy
③ THÊM MỘT DÒNG vào bảng trong ~/.secret/README.md
④ khai tên biến đó trong channel.yml
```

Bước ② khác nhau theo hệ điều hành — **task theo lịch không đọc shell profile của bạn**:

| Hệ điều hành | Đặt biến | Task theo lịch thấy khi nào |
|---|---|---|
| Windows | `setx <TÊN_BIẾN> "<đường dẫn>"` (cấp user) | lượt chạy **sau** lệnh `setx`; tiến trình đang mở thì chưa thấy |
| macOS | khoá `EnvironmentVariables` trong file plist của job launchd (`~/Library/LaunchAgents/<job>.plist`) | sau khi nạp lại job (`launchctl bootout` rồi `bootstrap`) |

Trên macOS, biến đặt trong `~/.zshrc` chỉ có ở terminal bạn mở tay — job launchd **không**
thấy nó, nên chạy tay thì được mà chạy theo lịch thì hỏng.

**Bước ③ không được bỏ.** Bảng thiếu một dòng thì sáu tháng sau không ai biết file đó của ai,
và không ai dám xoá nó.

Tên biến: dùng **tên trần** (`YT_TOKEN_PATH`) cho tài khoản mặc định, **thêm hậu tố**
(`YT_TOKEN_PATH__NGHE_TIEN_TRUYEN`) cho tài khoản thứ hai trở đi. Không có sơ đồ bắt buộc —
điều duy nhất phải khớp là: **tên trong `channel.yml` == tên biến đã đặt**.

### 3. Bí mật KHÔNG có file

Đăng nhập trình duyệt, credential manager, token dịch vụ… **Đừng tạo file giả.** Thêm một
dòng vào bảng *"Bí mật KHÔNG có file"* của mục lục, kèm **cách lấy lại**.

Thiếu những thứ này thì pipeline hỏng **im lặng** — không có thông báo, trang web không cập
nhật — và không ai đoán ra vì sao. Đó là lý do chúng vẫn phải có mặt trong mục lục.

### 4. Chiến dịch mới trong kênh đã có

Không làm gì cả. Chiến dịch **thừa hưởng** bí mật của kênh; `campaign.md` không bao giờ khai
`secrets_env`. Chiến dịch cần tài khoản khác nghĩa là nó thuộc về một **kênh khác**.

---

## Biến môi trường code đang đọc — danh mục đầy đủ

Chỗ khai **duy nhất** các biến mà script trong repo đọc. Code đọc thêm một biến mà chưa có
dòng ở đây thì `tests/test_docs_drift.py` đỏ. Mọi biến đều **tuỳ chọn** — không đặt thì
script dùng đường lùi ghi ở cột cuối.

**Biến giữ đường dẫn tới file bí mật** (giá trị nằm trong file, không trong biến):

| Biến | Ai đọc | Không đặt thì |
|---|---|---|
| `YT_TOKEN_PATH`, `YT_CLIENT_SECRET` | script đăng YouTube của trạm (gọi qua hook `youtube_cmd`); repo chỉ ghi TÊN ở `channel.yml:secrets_env` | — |
| `FB_CONFIG` | script/hook Facebook của trạm; `fb_publish.py` nhận đường dẫn qua `--config` (hook chạy không qua shell nên không tự mở `$FB_CONFIG`) | — |
| `TG_CONFIG` | `scripts/lib/telegram_io.py` (mọi đường Telegram, kể cả `notify_run.py`) | `~/.secret/telegram/config.json` |
| `EMAIL_CONFIG` | `templates/station/_channel/send_newsletter.py` | `email-config.json` cạnh script |

**Token Telegram KHÔNG có biến riêng.** `TG_CONFIG` chỉ giữ đường dẫn; token chỉ nằm trong
file đó. Không có đường lùi đọc token từ biến môi trường — cố ý, vì token trần trong biến
user thì mọi tiến trình con đọc được và nó lọt vào log.

**Biến cấu hình máy** (không phải bí mật — chỉ chỉ chỗ):

| Biến | Ai đọc | Không đặt thì |
|---|---|---|
| `MARKETING_STUDIO_DATA` | `studio_paths.py`, `run.ps1` — gốc trạm | `~/.marketing` (`run.ps1` đi lên tìm `CHANNELS.md` trước) |
| `MARKETING_STUDIO_HOME` | `run.ps1` — thư mục repo | `~/Code/agent-marketing-studio` |
| `MARKETING_STUDIO_PY` | mọi `.ps1` gọi Python (`Find-Python`) | `<repo>/.venv` → `python` → `python3` → `py`; khai mà hỏng thì DỪNG |
| `TG_CHAT` | `telegram_io.py` — tên chat trong file cấu hình | `mac_dinh` |
| `WEB_REPO_DIR` | `scripts/pipeline/prune_media.py` — repo web để đối chiếu bản audio đã đăng (`<repo>/<kênh>/audio/<ngày>/<tên file>.*`, so theo TẪNG FILE) | không đối chiếu được ⇒ GIỮ mọi audio quá hạn, ghi lý do vào báo cáo. Luật đầy đủ: `docs/RETENTION.md` |
| `CHROME_BIN` | `scripts/lib/media_tools.py` — Chrome/Edge/Chromium dựng ảnh | dò đường quen thuộc của hệ điều hành (macOS: gói `.app`) → PATH |
| `FFMPEG_DIR` | `media_tools.py` — thư mục chứa `ffmpeg` + `ffprobe` | Windows: thư mục WinGet → PATH · macOS: PATH → `/opt/homebrew/bin`, `/usr/local/bin` |
| `FFPROBE` | `media_tools.py` — đường `ffprobe` riêng | như `FFMPEG_DIR` |
| `VIDEO_FONT` | `media_tools.py` — font `.ttf/.otf` khi Pillow tự vẽ chữ | Segoe/Arial (Windows) · Arial hệ thống (macOS) · DejaVu |
| `VOICE_STATION` | `studio_paths.voice_station()`, `scripts/lib/voice.py` — gốc trạm giọng (`agent-voice-studio`) | `OMNIVOICE_DIR` (tên cũ, lùi một cấp) → `studio.local.json: voice_station` → coi như chưa cài |
| `OMNIVOICE_DIR` | tên CŨ, trỏ thư mục **ENGINE** bên trong trạm giọng; `studio_paths` lùi một cấp để ra gốc trạm, `doctor` nhắc đổi sang tên mới | — |
| `OMNIVOICE_PY` | `scripts/lib/voice.py` — python của venv trạm giọng (chỗ cài `voice_studio` + `video_studio`) | `station.json: venv` của trạm giọng → `<trạm>/omnivoice/.venv/{Scripts,bin}/python*` |
| `VOICES_DIR` | `scripts/lib/voice.py`, `doctor` — kho profile giọng | `<trạm giọng>/<engine_dir>/voices` |
| `VIDEO_STATION` | `studio_paths.video_station()`, `scripts/lib/video.py` — gốc trạm video (`agent-video-studio`) | `VIDEO_ROOT` (tên cũ) → `studio.local.json: video_station` → coi như chưa cài |
| `VIDEO_ROOT` | tên CŨ của `VIDEO_STATION`, còn đọc được để không gãy máy đang chạy | — |
| `HYPERFRAMES_VERSION` | `scripts/lib/video.py` — bản HyperFrames trạm video ghim (chỉ để báo cáo; trạm video mới là nơi dùng nó) | `station.json: hyperframes_version` của trạm video |
| `OPCOS_CODEX_BRIDGE` | `make_fb_image.py make` — đường `cli.mjs` của cầu gọi Codex (hoặc cờ `--bridge`) | đường mặc định trong thư mục nhà |
| `MARKETING_STUDIO_REQUIRE_POWERSHELL` | `tests/conftest.py` — `=1` thì thiếu PowerShell là lỗi (CI đặt) | test `.ps1` tự bỏ qua khi máy không có PowerShell |

**Biến của TRẠM GIỌNG mà repo này chỉ truyền tiếp** — không script nào ở đây đọc chúng;
`scripts/runners/install_launchd.py` ghi chúng vào khối `EnvironmentVariables` của plist
để tiến trình con nhận được. Bảng đầy đủ ba trạm:
[`STATION_LAYOUT.md`](STATION_LAYOUT.md) mục 4c.

| Biến | Giá trị trên Apple Silicon | Không đặt thì |
|---|---|---|
| `OMNIVOICE_DEVICE` | `mps` | engine tự dò `cuda → mps → cpu` |
| `OMNIVOICE_DTYPE` | `float16` | engine dùng `float32` cho mọi thứ không phải CUDA — chậm gấp nhiều lần |
| `HF_DEACTIVATE_ASYNC_LOAD` | `1` | nạp trọng số bất đồng bộ, hỏng trên MPS |

> **Bỏ 20/09/2026 — `ATLAS_BASE_URL` · `ATLAS_SITE_NAME` · `ATLAS_AUTHOR`.** URL gốc, tên
> site và tác giả của trang blog nay đọc từ khối `brand:` trong `channel.yml` của kênh
> (`scripts/lib/brand.py`), và **thiếu là dừng với mã 2**. Ba biến cũ có giá trị mặc định
> ngay trong mã là danh tính thật của một chủ repo: ai clone về cũng xuất bản dưới danh
> nghĩa người đó mà không hề biết, vì chẳng có gì báo là mình chưa khai.

launchd chạy với PATH tối giản: ffmpeg cài qua Homebrew vẫn được dò ở thư mục Homebrew,
nhưng công cụ đặt chỗ khác thì phải khai biến ở plist (xem bước ② ở trên).

---

## Viết code đọc bí mật

Một khuôn duy nhất, dùng cho mọi ngôn ngữ: **biến trước, đường lùi sau, và nói ra đã dùng cái nào.**

```python
# Python
CFG = os.environ.get("FB_CONFIG") or os.path.join(THU_MUC_CU, "facebook_config.json")
```

```powershell
# PowerShell — đọc thẳng registry, đừng đọc $env:
# Biến vừa `setx` thì tiến trình đang chạy CHƯA thấy; đọc registry thì thấy ngay.
$moi = [Environment]::GetEnvironmentVariable('YT_TOKEN_PATH','User')
if ($moi -and (Test-Path $moi)) { $env:YT_TOKEN_PATH = $moi; $nguon = 'NEW' }
else { $env:YT_TOKEN_PATH = $duongCu; $nguon = 'OLD' }
Log ("secret: $nguon  " + $env:YT_TOKEN_PATH)
```

Ba điều trong khuôn đó, mỗi điều đổi lấy một lần hỏng:

- **Đường lùi** để lúc chuyển đổi không phải dừng pipeline.
- **Ghi lại đã dùng đường nào** — hỏng mà không biết hỏng bên nào là kiểu hỏng đắt nhất.
- **Không in giá trị.** Chỉ in đường dẫn. Một dòng log dính token là token đã lộ.

### Ba điều tuyệt đối không làm

1. **Không hardcode đường dẫn tuyệt đối.** Một đường dẫn bắt đầu bằng ổ đĩa và thư mục người
   dùng là code chỉ chạy trên đúng một máy, và nó **mang theo tên người dùng** vào mọi bản sao.
   Dùng biến môi trường hoặc thư mục nhà do hệ điều hành trả về.
   *(Ví dụ minh hoạ ở đây cố tình không viết ra đường dẫn thật — chính cổng `test_no_identity_leak` của
   repo này sẽ đỏ nếu ai viết, kể cả khi viết để làm ví dụ. Đã dính một lần 06/09/2026.)*
2. **Không `print` giá trị bí mật**, kể cả khi gỡ lỗi. Kể cả một phần. Log tồn tại lâu hơn
   phiên gỡ lỗi.
3. **Không liệt kê biến môi trường theo tiền tố rồi in ra.** Có biến giữ *đường dẫn*, có
   biến giữ *giá trị* — lọc theo tiền tố là sớm muộn in nhầm cái thứ hai.
   *(Đã trả giá: một `TG_BOT_TOKEN` lọt vào transcript ngày 05/09/2026 đúng theo cách này.)*

---

## Kiểm trước khi tin

```bash
# 1. biến trỏ vào file có thật chưa
python -c "import os;[print(f'{k:34} {os.path.isfile(os.environ.get(k,\"\"))}') for k in ('YT_TOKEN_PATH','YT_CLIENT_SECRET','FB_CONFIG','EMAIL_CONFIG')]"

# 2. chạy khô toàn tuyến — phải thấy dòng `secret: NEW` trong log
<runner> -Uat

# 3. quyền của thư mục bí mật: protected, KHÔNG có tài khoản sandbox
powershell -c "(Get-Acl ~/.secret).AreAccessRulesProtected"     # Windows
ls -ld ~/.secret                                                # macOS: phải là drwx------
```

Chỉ xoá bản gốc ở chỗ cũ **sau khi một chu kỳ chạy đầy đủ báo xanh**. Trước đó chúng là lưới
an toàn, không phải rác.
