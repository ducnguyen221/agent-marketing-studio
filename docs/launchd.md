# Lịch chạy trên macOS — `launchd.json` và bộ cài lịch

Trang này mô tả **file khai job** `<trạm>/launchd.json` mà
[`scripts/runners/install_launchd.py`](../scripts/runners/install_launchd.py) đọc, và cách bộ
cài điền các con trỏ bí mật vào plist. Luật đổi máy (tắt lịch Windows trước, bật lịch Mac
sau): [`RUNBOOK-DOI-MAY.md`](RUNBOOK-DOI-MAY.md).

## Trạm nằm đâu

Bộ cài phân giải trạm theo đúng thứ tự của mọi script khác (`studio_paths.resolve_station`):

    --station → MARKETING_STUDIO_DATA → studio.local.json → <repo>/workspace/

Ở chế độ **embedded** (mặc định, không đặt biến trạm nào) trạm là `<repo>/workspace/`, nên
file khai là `<repo>/workspace/launchd.json`. Dòng đầu của mọi lần chạy in trạm và nguồn:
`[launchd] trạm: … (nguồn: workspace)`.

## Định dạng `launchd.json`

Một object: **khoá là label** (tên file mẫu trong `templates/launchd/`, xem `--list`), giá trị
là chuỗi rút gọn `"<kênh>/<chiến dịch>"` hoặc một object:

| Khoá | Bắt buộc | Nghĩa |
|---|---|---|
| `channel` | có | thư mục kênh trong trạm |
| `campaign` | có | thư mục chiến dịch trong kênh |
| `runner` | không | tên file `.ps1` trong thư mục chiến dịch mà job gọi. Mặc định `run.ps1`. Chỉ là **tên file** — không `/`, không `..` |
| `env` | không | con trỏ bí mật thêm cho job này. **Danh sách tên** (`["YT_TOKEN_PATH__NGHE_TIEN_TRUYEN"]`: plist mang đúng tên đó), hoặc **object `{TÊN_TRONG_PLIST: TÊN_NGUỒN}`**: plist mang tên trái, giá trị lấy từ tên phải — để job truyện nhận `YT_CLIENT_SECRET` (tên mã đọc) từ `YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN` trong khi job tin dùng `YT_CLIENT_SECRET` của kênh tin, cùng MỘT lệnh cài. Cả hai vế chỉ nhận tên thuộc bộ con trỏ bên dưới (kèm hậu tố) |
| `vars` | không | biến **đường dẫn không bí mật** runner cần: object `{TÊN: đường}` (viết thẳng) hoặc danh sách `[TÊN]` (giá trị lấy từ biến môi trường → `<repo>/.env`). Chỉ nhận danh sách trắng `L30_SCRIPT`, `TRUYEN_PUBLISH_PY`, `TRUYEN_FONT`, `VOICE_BGM_DIR`, `WEB_REPO_DIR`, `FFMPEG_DIR`, `NOTIFY_RUN`, `CLAUDE_CONFIG_DIR`; giá trị phải là đường dẫn |
| `schedule` | không | thay lịch của mẫu: object (hoặc danh sách object) với khoá `Minute`, `Hour`, `Day`, `Weekday`, `Month` — đúng khoá của `StartCalendarInterval` |

Ví dụ đầy đủ (cổng `tests/test_launchd_templates.py` chạy chính ví dụ này qua bộ kiểm):

```json
{
  "studio.marketing.daily-news-a": "tin/hang-ngay",
  "studio.marketing.daily-news-b": { "channel": "tin", "campaign": "hang-ngay-b" },
  "studio.marketing.daily-story": {
    "channel": "truyen",
    "campaign": "hang-ngay",
    "env": {
      "YT_TOKEN_PATH__NGHE_TIEN_TRUYEN": "YT_TOKEN_PATH__NGHE_TIEN_TRUYEN",
      "YT_CLIENT_SECRET": "YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN"
    },
    "vars": ["TRUYEN_FONT"],
    "schedule": { "Hour": 0, "Minute": 30 }
  },
  "studio.marketing.weekly-repo": {
    "channel": "tin",
    "campaign": "repo-tuan",
    "vars": { "L30_SCRIPT": "~/cong-cu/last30days/scripts/last30days.py" }
  },
  "studio.marketing.worker": "tin/hang-ngay"
}
```

Lỗi hình dạng nào cũng là **mã 2** kèm tên label và khoá sai: khoá lạ, runner có đường dẫn,
`env` có tên không phải con trỏ bí mật, `vars` có tên ngoài danh sách trắng hoặc giá trị không
phải đường dẫn (khoá này không phải cửa để đẩy `PYTHONPATH`/`DYLD_*` vào job), giờ ngoài khoảng, `schedule` cho job không chạy theo
lịch (`worker`, `approve-poller` chạy liên tục). Thiếu khai cho một label được chọn cũng là
mã 2 — bộ cài không đoán job nào thuộc chiến dịch nào. Ngoại lệ: `weekly-cleanup` là job của
**cả trạm** (mẫu không có chỗ trống kênh/chiến dịch) nên không cần khai; khai
`{"vars": {"WEB_REPO_DIR": "…"}}` cho nó nếu muốn đối chiếu audio đã lên web.

### Job dọn dung lượng tuần (từ 1.1.8) — tuỳ chọn, không nạp mặc định

Từ 1.1.9 **không cần** job này để giữ dung lượng có trần: log xoay vòng ngay trong lượt tin/truyện
(`scripts/lib/log_rotate.py`), media do từng quy trình tự dọn. Mac mini đã gỡ nó (03/10/2026). Giữ
lại như tuỳ chọn có tài liệu:

`studio.marketing.weekly-cleanup` — Chủ nhật 04:00, `ProcessType=Background`, trần 1 h. Chạy
`scripts/runners/run-weekly-cleanup.ps1` → `weekly_cleanup.py`: dời media **đã đăng** và quá 14
ngày sang `<trạm>/_trash/<ngày>` (`prune_media.py`, có kê khai), đổ thư mục `_trash` dời quá 30
ngày, xoay vòng log (`logs/launchd/` + `daily-logs/` của trạm giọng: xoá quá 60 ngày, cắt file
trên 5 MB giữ 1 MB cuối), báo dung lượng từng trạm qua Telegram. **Chỉ `--only` mới nạp** — kể
cả `--all` cũng bỏ qua: dời file theo lịch là quyết định của chủ máy. Xem trước, không chạm gì:
`pwsh scripts/runners/run-weekly-cleanup.ps1 -DryRun`. Windows: `-Register`.

### Lượt truyện: trần hai tầng (từ 1.1.8)

Runner truyện tự canh lượt đầu 30600 s; quá trần mà `_resume.json` còn dải dở thì tự chạy tiếp
**một lần** (trần 10800 s, dùng cache chương), tin ⏳ báo "đang chạy tiếp từ chương X"
(`scripts/runners/story/resume_once.py`). `--timeout` của mẫu `daily-story` (42300 s) chỉ còn là
lưới an toàn và phải ≥ tổng hai trần.

`--map <label>=<kênh>/<chiến dịch>` đổi kênh/chiến dịch cho một lần chạy; `runner`, `env`,
`vars`, `schedule` đã khai trong file vẫn giữ.

### Lượt truyện từ 1.1.0

Mã lượt truyện nằm trong repo (`scripts/runners/run-daily-truyen.ps1` + `scripts/runners/story/`).
Chiến dịch truyện khai `runtime.runner: run-daily-truyen.ps1` trong `campaign.md`; job launchd
để `runner` MẶC ĐỊNH (`run.ps1`) — `run.ps1` tìm thấy runner trong repo. Runner cũ trong thư
mục chiến dịch (`run-daily-truyen-p2.ps1`) chỉ còn cho máy chưa nâng cấp.

Báo cáo Telegram (`compose_report.py`, `triage.py`) cũng ở `scripts/runners/`: mẫu plist gọi
`notify_run.py --composer-dir __REPO__/scripts/runners`, không còn `<trạm>/engine`.

### Vì sao `runner` khai được

Mẫu gọi `<trạm>/<kênh>/<chiến dịch>/<runner>`. Chiến dịch tạo bằng bộ scaffold có `run.ps1`,
nhưng một trạm lâu năm có thể đặt tên khác cho runner thật (ví dụ lượt truyện gọi
`run-daily-truyen-p2.ps1`). Để mặc định mà tên thật khác thì job chạy đúng giờ và chết
ngay vì không thấy file — nên tên runner là thứ khai, không phải thứ đoán.

## Con trỏ bí mật: TÊN ở mẫu, GIÁ TRỊ từ máy

launchd **không** đọc `~/.zshrc` và **không** đọc `<repo>/.env`. Job chỉ thấy khối
`EnvironmentVariables` của plist. Mẫu khai **tên** biến, bộ cài điền **giá trị**:

| Tên | Job khai | Ai đọc |
|---|---|---|
| `TG_CONFIG`, `TG_CHAT` | mọi job | báo Telegram (`telegram_io.py`, `notify_run.py`) |
| `YT_CLIENT_SECRET`, `YT_TOKEN_PATH` | 5 job tin, lượt truyện, worker | bộ đăng YouTube của trạm (hook `youtube_cmd`) |
| `FB_CONFIG` | 5 job tin, lượt truyện, worker | hook Facebook (`fb_publish.py --config`) |
| `EMAIL_CONFIG` | 5 job tin, lượt truyện, worker | `send_newsletter.py` của kênh |
| `CODEX_BRIDGE` | 5 job tin, lượt truyện, worker | `make_fb_image.py make` |

`approve-poller` và `weekly-cleanup` chỉ khai hai biến Telegram: chúng không đăng gì, nên không
nhận đường tới token đăng bài (quyền tối thiểu).

Giá trị lấy theo thứ tự của `studio_paths.secret_env`: **biến môi trường → `<repo>/.env`**
(chỉ ở chế độ embedded). Ba luật:

1. Giá trị phải là **đường dẫn** (tuyệt đối hoặc bắt đầu bằng `~`; `~` được mở rộng vì
   launchd không tự mở rộng). Trừ `TG_CHAT`, là tên chat. Giá trị không phải đường dẫn thì bộ
   cài dừng mã 2 và **không in** giá trị đó ra (nó có thể chính là bí mật).
2. Tên chưa có giá trị ở đâu thì **bỏ cả dòng** khỏi plist và in tên ra — không ghi chuỗi
   rỗng. Tên khai trong khoá `env` mà thiếu giá trị thì là mã 2: bạn đã nói job cần nó.
3. Log và dòng JSON kết quả chỉ mang **tên** (`secret_env`, `secret_env_missing`,
   `secret_env_from` = ánh xạ tên → tên, `vars`), không bao giờ mang giá trị. Plist ghi ra có
   quyền `600`.

## Mã thoát của `notify_run.py` (một hợp đồng cho hai máy)

| Mã | Nghĩa | Tin Telegram |
|---|---|---|
| mã của lệnh con | 0 ok · 1 lỗi engine · 2 cấu hình sai · 3 thiếu trạm | ✅ / ❌ |
| 4 | hết hạn mức — mọi engine trong `order` hết lượt; **không phải hỏng**, không gọi triage | 🟡 HẾT HẠN MỨC |
| 5 | runner tin: **môi trường render kẹt** — `video-studio probe` báo `RENDER_STUCK` TRƯỚC nghiên cứu/TTS (P1-24); khởi động lại máy rồi chạy lại. Giả lập khi nghiệm thu: `RENDER_PROBE_TIMEOUT=1`. Rào render hỏng kiểu khác dừng với 1 (phép thử hỏng) / 2 (cấu hình render sai) / 3 (thiếu npx, Chromium, gói `video_studio`) — không phải 5 | ❌ MÔI TRƯỜNG RENDER KẸT |
| 124 | wrapper giết cả cây tiến trình vì quá `--timeout` (launchd không có `ExecutionTimeLimit`) — hoặc lượt truyện quá trần cả sau lượt chạy tiếp | ⏳ QUÁ TRẦN |

Wrapper của Task Scheduler trên Windows trả đúng các mã này — sổ Excel, `compose_report.py` và
`triage.py` phân loại theo mã, nên hai máy phải nói cùng một thứ tiếng.

## Chạy thử không đụng gì

```sh
python3.12 scripts/runners/install_launchd.py --list
python3.12 scripts/runners/install_launchd.py --dry-run --no-load
python3.12 scripts/runners/install_launchd.py --dry-run --no-load --all --json
```

`--dry-run` không ghi file và không gọi `launchctl`; dòng xem trước in label, đường plist,
kênh/chiến dịch/runner và **tên** con trỏ bí mật sẽ vào plist. Khi đã sẵn sàng bật thật:
bỏ `--dry-run` (vẫn giữ `--no-load` nếu chỉ muốn xem file trong `~/Library/LaunchAgents`).

PATH của mọi job: `~/.local/bin` (đã mở rộng) · `/opt/homebrew/bin` (Apple Silicon) ·
`/usr/local/bin` (Intel) · thư mục hệ thống. Lệnh nằm chỗ khác thì job không thấy — xem đầu
log của `notify_run.py`, nó in `which` của từng công cụ.
