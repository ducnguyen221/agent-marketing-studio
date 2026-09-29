# CHANGELOG — agent-marketing-studio

Mỗi mục là một phiên bản. Mục đầu luôn là số trong `pyproject.toml`
(`tests/test_version_sync.py` giữ điều này). Phiên bản chưa gắn tag ghi rõ "chưa phát hành".

## 1.0.1 — 2026-09-29

Bản vá cho Mac mini chạy tự động ở chế độ `embedded` (không biến trạm, trạm là
`<repo>/workspace/`, cấu hình ở `<repo>/.env`). Không đổi hành vi trên máy Windows đang chạy lịch.

- **Bài mẫu offline** `samples/`: một bài ngắn + kết quả kỳ vọng cố định của 24 cổng
  (`samples/gates-expected.json`). `doctor` chấm lại trong bộ nhớ và in `samples: PASS`, `WARN`
  khi lệch, `NOT_CHECKED` khi không có `samples/`. Cổng `tests/test_samples.py`.
- **launchd:** PATH của mọi plist có `~/.local/bin` (đã mở rộng), `/opt/homebrew/bin`,
  `/usr/local/bin`. Tên con trỏ bí mật (`TG_CONFIG`, `TG_CHAT`, `YT_CLIENT_SECRET`,
  `YT_TOKEN_PATH`, `FB_CONFIG`, `EMAIL_CONFIG`, `CODEX_BRIDGE`; poller chỉ hai biến Telegram)
  khai ở mẫu, giá trị bộ cài điền từ biến môi trường → `<repo>/.env`; chưa có thì bỏ dòng và nêu
  tên, không phải đường dẫn thì mã 2 mà không in giá trị; plist ghi ra quyền 600.
- **`launchd.json`** nhận object `{channel, campaign, runner, env, schedule}`: runner khác
  `run.ps1` (vd lượt truyện), con trỏ bí mật theo kênh (`YT_TOKEN_PATH__<KÊNH>`), đổi lịch. Tài
  liệu và ví dụ: `docs/launchd.md`.
- **Con trỏ bí mật một thứ tự:** `studio_paths.secret_path()` (thiếu thì nêu tên biến) và
  `studio_paths.hook_env()` — hook đăng bài của bước `release` nhận con trỏ khai ở `.env`.
- **Tài liệu:** `START-HERE.md`, `docs/troubleshooting.md`, trang `docs/install/`; `INSTALL.md`
  bổ sung Mac mới tinh (`python3.12`, Xcode CLT, Homebrew do người dùng cài, `/opt/homebrew/bin`,
  `pwsh`, `zsh -lic`) và bước xem trước lịch `install_launchd.py --dry-run --no-load`.
- **CI:** ma trận Windows + macOS × Python 3.10/3.12/3.13, `fail-fast: false`, chạy mọi nhánh,
  mọi action ghim SHA.
- **Ghi công:** `NOTICE` + `upstream.json` (hash của từng file chưng cất từ repo MIT ngoài);
  cổng `tests/test_upstream_provenance.py`.

## 1.0.0 — 2026-09-29 (phát hành đầu)

Đợt chuẩn hóa repo: chạy chuẩn trên Windows, mã sẵn sàng cho macOS, bộ cài/gỡ/kiểm có đủ.

- **Một nguồn phiên bản:** `pyproject.toml` + manifest `.claude-plugin/` và `.codex-plugin/`
  trỏ bốn skill ở `.agents/skills/`; cổng `tests/test_version_sync.py`.
- **Không còn đường mặc định của một máy cụ thể:** `make_fb_image.py make` cần cầu Codex khai
  rõ (`--bridge` hoặc biến `CODEX_BRIDGE`), thiếu thì dừng mã 3 và nêu tên biến. Biến cũ đổi
  tên thành `CODEX_BRIDGE`.
- **Cổng G21** chỉ giữ tên công cụ công khai trong mã; tên hệ thống riêng của bạn khai ở
  `channel.yml` → `brand.internal_tools`.
- **Cổng mới** `tests/test_no_leak.py`: chặn tên và đường nội bộ của hệ thống riêng lọt vào
  repo public.
- **Trạm mặc định là `<repo>/workspace/`:** không đặt biến, không chọn gì thì script dùng
  `workspace/` trong repo — không còn tự lùi về một thư mục trong nhà. Trạm ngoài repo chỉ khi
  bạn chỉ định (biến `MARKETING_STUDIO_DATA`, `--station`, hoặc chọn `separate` lúc cài).
- **Gỡ cài đặt:** `uninstall.ps1` / `uninstall.sh` (lõi `studio.py uninstall`, có `--dry-run`) gỡ
  đúng `studio.local.json` và hook pre-commit của bộ cài; giữ trạm, `.env`, repo.
- **`studio.py update`** dừng trước khi kéo nếu checkout có file sửa chưa commit.
- **`doctor`** khám skill gốc + adapter Claude; việc host nạp skill ghi `NOT_CHECKED`.
- **Cài đặt agent-first:** `INSTALL.md` (prompt copy-dán VI/EN), `hosts/` cho Claude Code,
  Codex, Antigravity; adapter `.claude/skills/` sinh bằng `scripts/build_host_adapters.py`.
- **Nâng cấp từ bản cũ:** máy từng cài plugin `auto-marketing` (tiền thân của repo này) thì gỡ
  nó **sau khi** skill của studio đã nạp được, để hai bộ skill không trùng việc — cách gỡ ở
  `INSTALL.md` §11.
