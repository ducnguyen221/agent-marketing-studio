# CHANGELOG — agent-marketing-studio

Mỗi mục là một phiên bản. Mục đầu luôn là số trong `pyproject.toml`
(`tests/test_version_sync.py` giữ điều này). Phiên bản chưa gắn tag ghi rõ "chưa phát hành".

## 1.1.2 — 2026-09-30

Bản vá gói đổi máy (G7 của đợt Mac mini). Chỉ đổi `station.py export`; lượt chạy trên cả hai
máy không đổi.

- **P1-17** `export --for-machine <máy>` làm đủ ba việc RUNBOOK-DOI-MAY §5 trên
  `engines.json` đi theo gói: `_may.ten` = máy đích (`nen_tang` lấy từ `_may_khac.<máy>`,
  không khai thì bỏ); `order` + `_order_ly_do` lấy từ `_may_khac.<máy>`; mục máy đích bị
  xoá khỏi `_may_khac` và máy NGUỒN thành một mục mang thứ tự cũ. Trước đây chỉ đổi
  `order`, nên máy đích nhận file tự xưng là máy nguồn, mang lý do của máy nguồn và thứ tự
  của chính nó hai lần.
- **Gói đổi máy loại `subscribe.gs`**: bản Apps Script ở trạm mang `SECRET` thật trong mã
  nguồn; tên file không giống secret nên bộ lọc theo tên không bắt. Loại, không từ chối.
  RUNBOOK Bước 3 thêm cảnh báo: `--with-git` mang cả lịch sử, trạm từng commit secret thì
  không dùng khi khoá chưa xoay.

## 1.1.1 — 2026-09-30

Bản vá từ nghiệm thu 1.1.0 trên Mac (P5-1.1.0). Hành vi trên Windows không đổi: venv giọng
Windows đã có `lxml`/`requests`, trạm Windows dùng bản script kênh của chính nó (khuôn
`templates/station/_channel/` chỉ dùng cho kênh mới), và `daily_truyen.py` vẫn ép cùng token.

- **P0-7** `requirements-runners.txt` + `runner_deps.MODULES` thêm `lxml` (parser
  `BeautifulSoup(…, "lxml")` của `story/read_story.py` — giữ nguyên parser) và `requests`
  (`read_story.py` import thẳng). Cổng mới `test_runner_deps.py`: MỌI `import` bên thứ ba và
  mọi parser BeautifulSoup trong `scripts/runners/**` phải nằm trong `MODULES` — thứ nạp bằng
  tên chuỗi không còn lọt khỏi `doctor`.
- **P1-15** khuôn `send_newsletter.py`: `_cfg()` chép thêm `a`, `b`, `gh_repo`, `email_accent`
  (`brand:` thắng `theme:`) — thư gửi ra có tên kênh và link video trong Release.
- **P2-19** khuôn `build-index.ps1`: gradient nút đăng ký, nhịp sáng và chữ "đã đăng ký" qua
  `web_cta_from`/`web_cta_to` (khai ở `channel.yml:brand` hoặc `brand.md`); không khai = đúng
  hai màu cũ, trang ra giống từng byte. Cổng giữ mọi regex đường dẫn trong khuôn nhận cả `\`
  lẫn `/` (họ lỗi P1-16).
- **P2-20** `doctor`: không có `<trạm>/engine` nay in "runner chạy từ `<repo>/scripts/runners`"
  thay cho lời cũ về đường lùi.
- **P3-12** `truyen_publish.py --token` mặc định: `YT_TOKEN_PATH__NGHE_TIEN_TRUYEN` THẮNG
  `YT_TOKEN_PATH` chung (`truyen_paths.token_truyen`; biến chung không đọc registry).
- `AGENTS.md` §4 thêm điều 8: bộ chạy sửa trong repo qua PR có CI 2 OS, `.ps1` giữ BOM, đọc
  biến qua `Get-EnvVar`.

**Nâng cấp máy đang chạy:** cài lại gói bộ chạy vào venv giọng (thêm `lxml`):
`<python của venv giọng> -m pip install -r requirements-runners.txt`, rồi `doctor` phải báo
"venv giọng đủ gói".

## 1.1.0 — 2026-09-30

Bộ chạy tin/truyện vào repo, và mọi đường suy từ biến + thư mục cha của bản clone — Windows và
Mac chạy CÙNG một mã, lấy bằng `git`, không còn chép tay `engine/` giữa hai máy.

**Bộ chạy vào repo (P1-10).** 22 file của `<trạm>/engine` (7 `.ps1` + 15 `.py`) vào
`scripts/runners/` (phẳng — `run.ps1` đã tìm runner ở đây TRƯỚC `<trạm>/engine`), mã truyện vào
`scripts/runners/story/` (7 `.py`) kèm runner chung mới `run-daily-truyen.ps1`. Bộ test của
engine/truyện vào `tests/test_runner_*.py`, `tests/test_story_*.py` (hai file đọc nguồn truyện
cần venv giọng, tự bỏ qua trên CI). KHÔNG mang: `backfill_content.py` (công cụ chạy một lần),
runbook token Facebook, `pham_nhan_tu_tien_phan_1/`. Ba script cấp kênh (`send_newsletter.py`,
`build-index.ps1`, `build_yt_desc.py`) và `viet-bai.ps1`/`write-post.ps1` của kênh blog ở lại
trạm (nội dung + nhận diện của kênh); khuôn trung tính là `templates/station/_channel/`.
- **P0-1** runner đọc con trỏ bí mật qua `Get-EnvVar` (tiến trình → registry User CHỈ trên
  Windows → `<repo>/.env` embedded) — macOS không còn nhận chuỗi rỗng rồi bỏ upload mà vẫn ✅.
- **P0-2** `Join-Path` lồng từng đoạn (`hot-today/hot-news.json`) — trang Hot Today cập nhật được
  trên macOS.
- **P0-3** `requirements-runners.txt` (cài vào VENV GIỌNG); `doctor` kiểm từng module qua
  python đó và nêu đúng tên module thiếu + lệnh `pip install -r`.
- **P0-4** nhạc nền kiểm TRƯỚC `claude -p`: ép style không có mp3 thì dừng ngay; AI chỉ được
  chọn style có mp3; `doctor` nhắc style thiếu mp3 (không có lệnh sinh nhạc).
- **P0-6** `doctor` có dòng `NOT_CHECKED claude-cli` kèm lệnh tự kiểm đăng nhập.
- **last30days**: `L30_SCRIPT` → thư mục plugin Claude (hai OS) → runner dừng, nêu tên biến;
  `doctor` + `INSTALL.md` kiểm.
- **P1-5/P1-14** trạm, trạm giọng/video, python giọng, repo web: biến → `<repo>/.env` → repo anh
  em cùng thư mục cha (theo `pyproject.toml: name`) → đường cũ CHỈ khi có thật, kèm `WARN`.
  `Get-Cfg` hiểu `${TÊN}` và đường tương đối theo thư mục cha (như `studio_paths.duong_repo_web`).
  Sửa lỗi ẩn: `$Engine` (không phân biệt hoa thường với `$engine` của runner) nay là thư mục CODE,
  không phải `<trạm>/engine`.
- **P1-12** danh tính commit web lấy từ `channel.yml brand.git_author` ("Tên <email>"); không khai
  = tên "<site_name> Bot" + email git của máy. Tác giả/mô tả YouTube/link trang tin/thẻ YouTube
  lấy từ cấu hình kênh, không viết trong mã (cổng `test_no_leak`/`test_no_identity_leak` xanh).
- **P1-2** `launchd.json`: khoá `vars` (danh sách trắng biến đường dẫn: `L30_SCRIPT`,
  `TRUYEN_PUBLISH_PY`, `TRUYEN_FONT`, `VOICE_BGM_DIR`, `WEB_REPO_DIR`, …) và `env` dạng
  `{TÊN_TRONG_PLIST: TÊN_NGUỒN}`; mẫu plist gọi `--composer-dir __REPO__/scripts/runners`.
  **P2-9** ví dụ dùng tên thật `YT_TOKEN_PATH__NGHE_TIEN_TRUYEN`.
- **P1-9** `engines.json: ledger` tương đối tính từ gốc trạm, tuyệt đối ngoài trạm thì cảnh báo;
  `station.py export --for-machine <máy>` đổi `order` theo `_may_khac.<máy>` và bỏ ledger tuyệt đối.
- **P1-11** `notify_run.py` cùng hợp đồng với wrapper Windows: quá giờ trả **124** (⏳), mã **4**
  giữ nguyên + tin 🟡 HẾT HẠN MỨC (không triage); `which python3`.
- **P1-4** `doctor` so tên profile giọng ở dạng NFC (file NFD nhập từ Windows không còn đỏ giả).
- **P3-1/P3-11** file vào repo đều LF + BOM cho `.ps1`; cổng `tests/test_runners_portable.py`
  quét mọi thư mục runner + khuôn trạm (registry `'User'` phải sau điều kiện Windows, thư mục cũ
  chỉ ở nấc cuối có WARN, bộ chạy tối thiểu có trong repo). Mã truyện trong repo KHÔNG tự sửa
  mình (`heal_agent`) trừ khi `TRUYEN_HEAL=1`.

**Gộp PR #5 (Mac, P1-6/P1-7/P1-8/P2-10/P2-11).** `run.ps1` tìm repo bằng cách đi lên tới
`scripts/pipeline/campaign_cfg.py` (bỏ đường lùi `~/Code`); `studio_paths.repo_anh_em`/
`tram_anh_em`/`duong_repo_web`; `campaign_cfg` ghi `repo` tuyệt đối vào bản chụp; fixture
`repo_gia` + `collect_ignore` gốc + job CI "cài embedded rồi pytest"; cổng
`test_khong_gia_dinh_thu_muc_cha.py`.

**Nâng cấp — Windows (máy lịch hiện tại):** `git pull` bản này là đủ để `run.ps1` của trạm chạy
runner trong repo; biến User giữ nguyên. Khác biệt nhìn thấy được: commit web kênh Data mang
tên "Data News Bot" (trước là tên bot của kênh AI); thẻ YouTube thêm tên trang của kênh (khai
`runtime.yt_tags` để ép). Wrapper báo cáo của Task Scheduler vẫn đọc `compose_report.py`/
`triage.py` ở `-ComposerDir` đang khai (thường là `<trạm>/engine`): TRƯỚC khi xoá thư mục đó, đổi
`-ComposerDir` của các task sang `<repo>/scripts/runners`. Sau MỘT lượt xanh của mỗi task: xoá
`<trạm>/engine` (doctor nhắc).
Truyện: đổi `runtime.runner` trong `campaign.md` của phần đang chạy thành `run-daily-truyen.ps1`
khi muốn dùng mã trong repo (runner cũ trong thư mục chiến dịch vẫn chạy mã cũ tới lúc đó).
**Nâng cấp — Mac:** `git fetch --tags && git checkout v1.1.0`; `<OMNIVOICE_PY> -m pip install -r
requirements-runners.txt`; xoá `workspace/engine`; khai `L30_SCRIPT`/`TRUYEN_FONT`… qua `vars`
và con trỏ truyện qua `env` trong `launchd.json` (một lệnh cài); `install_launchd.py --dry-run
--no-load` rồi cài lại plist.

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
