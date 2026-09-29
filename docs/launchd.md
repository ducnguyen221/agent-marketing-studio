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
| `env` | không | danh sách **tên** con trỏ bí mật thêm cho job này, thường là tên có hậu tố tài khoản (`YT_TOKEN_PATH__TRUYEN`). Chỉ nhận tên thuộc bộ con trỏ bên dưới |
| `schedule` | không | thay lịch của mẫu: object (hoặc danh sách object) với khoá `Minute`, `Hour`, `Day`, `Weekday`, `Month` — đúng khoá của `StartCalendarInterval` |

Ví dụ đầy đủ (cổng `tests/test_launchd_templates.py` chạy chính ví dụ này qua bộ kiểm):

```json
{
  "studio.marketing.daily-news-a": "tin/hang-ngay",
  "studio.marketing.daily-news-b": { "channel": "tin", "campaign": "hang-ngay-b" },
  "studio.marketing.daily-story": {
    "channel": "truyen",
    "campaign": "hang-ngay",
    "runner": "run-daily-truyen-p2.ps1",
    "env": ["YT_TOKEN_PATH__TRUYEN"],
    "schedule": { "Hour": 0, "Minute": 30 }
  },
  "studio.marketing.worker": "tin/hang-ngay"
}
```

Lỗi hình dạng nào cũng là **mã 2** kèm tên label và khoá sai: khoá lạ, runner có đường dẫn,
`env` có tên không phải con trỏ bí mật, giờ ngoài khoảng, `schedule` cho job không chạy theo
lịch (`worker`, `approve-poller` chạy liên tục). Thiếu khai cho một label được chọn cũng là
mã 2 — bộ cài không đoán job nào thuộc chiến dịch nào.

`--map <label>=<kênh>/<chiến dịch>` đổi kênh/chiến dịch cho một lần chạy; `runner`, `env`,
`schedule` đã khai trong file vẫn giữ.

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

`approve-poller` chỉ khai hai biến Telegram: nó không đăng gì, nên không nhận đường tới token
đăng bài (quyền tối thiểu).

Giá trị lấy theo thứ tự của `studio_paths.secret_env`: **biến môi trường → `<repo>/.env`**
(chỉ ở chế độ embedded). Ba luật:

1. Giá trị phải là **đường dẫn** (tuyệt đối hoặc bắt đầu bằng `~`; `~` được mở rộng vì
   launchd không tự mở rộng). Trừ `TG_CHAT`, là tên chat. Giá trị không phải đường dẫn thì bộ
   cài dừng mã 2 và **không in** giá trị đó ra (nó có thể chính là bí mật).
2. Tên chưa có giá trị ở đâu thì **bỏ cả dòng** khỏi plist và in tên ra — không ghi chuỗi
   rỗng. Tên khai trong khoá `env` mà thiếu giá trị thì là mã 2: bạn đã nói job cần nó.
3. Log và dòng JSON kết quả chỉ mang **tên** (`secret_env`, `secret_env_missing`), không
   bao giờ mang giá trị. Plist ghi ra có quyền `600`.

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
