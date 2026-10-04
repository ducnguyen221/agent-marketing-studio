# CHANGELOG — agent-marketing-studio

Mỗi mục là một phiên bản. Mục đầu luôn là số trong `pyproject.toml`
(`tests/test_version_sync.py` giữ điều này). Phiên bản chưa gắn tag ghi rõ "chưa phát hành".

## 1.1.9 — 2026-10-04

Năm việc Mac mini giao ngày 04/10 (SUBTASK-WIN-RUNTIME-3; P4-RUNS: P5-02/10-TOI, P5-03/10-TOI,
P5-KIEM-TRA-LICH, P5-WEEKLY-DATA-LUOT-1, P5-DOI-GIO-2). Mọi thay đổi chạy giống nhau dưới Task
Scheduler lẫn launchd. Lịch chạy KHÔNG đổi trong repo (Mac tự chỉnh bằng `launchd.json`).

- **Lượt "bỏ qua theo nhịp" không còn tin ✅ gây nhầm.** Hot AI/Hot Data cách ngày nhưng lịch gọi
  mỗi ngày: ngày lệch nhịp runner thoát 0 sau 0 s, trước đây vẫn ra "✅ … chạy 0 giây". Runner in
  thêm `RUN_SKIPPED=cadence`; `notify_run.py` (launchd) thấy mã 0 + dấu đó ⇒ **không gửi**, chỉ
  ghi một dòng log; `compose_report.py` soạn một dòng "⏭ … bỏ qua theo nhịp … không phải lỗi" —
  đó là thứ wrapper Task Scheduler (ngoài repo) gửi. Mã khác 0 thì dấu đó không che tin lỗi.
- **P1-26 — bản tin tuần chạy được bằng agy.** Prompt tuần 45 402 ký tự > trần argv 30 000 của agy
  ⇒ trước đây cả hai mẫu agy bị bỏ, rơi xuống codex. Nay `agent_call` ghi prompt quá trần vào một
  thư mục tạm riêng (không vào cwd), `--add-dir` thư mục đó, và `--print=` chỉ còn câu dẫn "đọc HẾT
  tệp … tới dòng `=== HẾT TỆP NHIỆM VỤ ===` rồi làm theo"; xoá tệp ngay sau lượt gọi (cả khi lỗi).
  Chỉ khi lượt gọi có tool (agy headless tự từ chối `read_file` nếu không tự duyệt tool — không tự
  nới quyền cho lượt chỉ-trả-lời); không tool thì giữ hành vi cũ (bỏ qua agy). Sổ ghi
  `prompt_via: file|argv|stdin`. Đo thật trên Windows (agy 1.2.15): prompt 40 577 ký tự qua tệp,
  agy đọc hết và làm đúng chỉ dẫn ở dòng cuối, 16 s.
- **P1-25 — render kẹt: tự chữa + chụp chứng cứ trước khi bắt khởi động lại.** `Invoke-RenderPreflight`
  gọi `video-studio probe --heal --heal-waits 60,600 --diag-dir <log chiến dịch>/render-stuck`
  (agent-video-studio **0.2.7**): kẹt ⇒ gói chẩn đoán `render-stuck/<giờ>/` (top CPU, tiến trình
  Chrome/HyperFrames + mồ côi, profile tạm, lỗi probe; macOS thêm `pmset -g assertions/therm`, 10′
  `log show` WindowServer/coreaudiod; không env, không dòng lệnh tiến trình, che token) ⇒ giết
  Chrome/HyperFrames mồ côi ⇒ xoá profile tạm > 1 h ⇒ chờ 60 s probe lại ⇒ chờ 600 s probe cuối ⇒
  hết thang mới mã 5 "khởi động lại máy" kèm đường gói. Tự chữa được ⇒ đi tiếp, tin ✅ kèm dòng "đã
  tự chữa (lần N) — gói chẩn đoán: …" và KHÔNG nói "khởi động lại máy". `RENDER_HEAL_WAITS` đổi nhịp
  chờ (giả lập: `RENDER_PROBE_TIMEOUT=1 RENDER_HEAL_WAITS=1,1`), `RENDER_HEAL=0` tắt thang;
  video-studio 0.2.5/0.2.6 (chưa biết `--heal`) ⇒ nhắc một dòng rồi probe như cũ, không đọc nhầm
  thành "cấu hình sai". RUNBOOK: giờ khởi động lại định kỳ nên sau truyện (~07:00), trước 17:00.
- **Log xoay vòng trong lượt chạy** (Đức đã gỡ `weekly-cleanup` trên Mac). `scripts/lib/log_rotate.py`
  (mã chung, job dọn tuần cũng dùng): `*.log` sửa quá 60 ngày ⇒ xoá, trên 5 MB ⇒ cắt giữ 1 MB cuối
  tại chỗ, file vừa ghi trong 1 h không cắt, tên bắt đầu `_` (state/sổ của heal_agent) và file
  không phải log không đụng, thư mục con `render-stuck/<giờ>` quá 60 ngày ⇒ xoá; không bao giờ làm
  hỏng lượt. Gắn ở: ba runner tin (sau kiểm nhịp, trước rào render — log chiến dịch +
  `<trạm>/logs/launchd`), runner truyện (`<trạm>/logs/launchd`) và `daily_truyen.py` (`daily-logs/`,
  ngay trước `sweep_old`). `weekly-cleanup` + `prune_media.py` giữ trong repo như **tuỳ chọn có tài
  liệu, không nạp mặc định** (RETENTION, launchd.md, RUNBOOK nói rõ).
- **`gh` không có trên Mac.** `run-weekly-news.ps1`: YouTube không dùng được mà thiếu lệnh `gh` ⇒
  bỏ nhánh dự phòng GitHub Release (trang tuần lên không có video, log WARN nói rõ) thay vì hỏng ở
  lệnh `gh` đầu tiên. `doctor`: kênh có bản tin tuần + khai `brand.gh_repo` mà thiếu `gh` ⇒ cảnh
  báo kèm lệnh cài (`brew install gh` + người dùng tự `gh auth login`; Windows `winget`); có `gh`
  ⇒ đăng nhập là NOT_CHECKED. INSTALL thêm dòng `gh`.
- **Sau review độc lập (04/10)** — 1 Chặn + 1 Phải sửa ở repo này: `compose_report.py` có biểu
  thức f-string chứa gạch ngược (chỉ hợp lệ từ Python 3.12 — 3.10/3.11 mất cả tầng soạn tin, CI
  ma trận 3.10 đỏ) ⇒ tách ra biến; lượt tự chữa ở preflight rồi KẸT LẠI khi dựng thật từng ra tin
  "đã tự chữa — chạy tiếp bình thường" ⇒ nay chỉ xét phần log SAU `RENDER_PREFLIGHT=ok`, kẹt lại
  thì báo "KẸT LẠI khi dựng thật — khởi động lại máy". Phía video-studio 0.2.7 sửa cách nhận/giết
  tiến trình mồ côi, đối chiếu SID chủ trên Windows và che secret ba lớp (xem CHANGELOG của repo đó).
- **Wrapper Task Scheduler giữ nguyên (Đức chọn 04/10):** wrapper báo Telegram của Task Scheduler (hạ tầng máy, `notify-run.ps1`) nằm
  ngoài repo; lượt bỏ qua theo nhịp trên Windows vẫn ra MỘT dòng "⏭ … bỏ qua theo nhịp … không phải
  lỗi" (văn do `compose_report.py` soạn), không còn ✅. launchd thì không gửi gì. Các task tin trên
  Windows hiện đều Disabled (lịch đã chuyển sang Mac).
- **Lịch**: RUNBOOK-DOI-MAY ghi giờ chạy là cấu hình theo máy (Mac: `launchd.json` khoá `schedule`)
  và lịch đang dùng (Hot 17:00, tuần 19:00, truyện 00:00) — Windows không sửa mẫu lịch.

## 1.1.8 — 2026-10-03

Ba việc Mac mini giao ngày 02/10 (SUBTASK-WIN-RUNTIME-2; P4-RUNS: P5-1.1.7, P5-VIEC-CHO-WINDOWS,
P5-02/10-TOI). Mọi thay đổi chạy giống nhau dưới Task Scheduler lẫn launchd.

- **P1-23 — truyện tự chạy tiếp khi quá trần.** `run-daily-truyen.ps1` chạy `daily_truyen.py` qua
  `story/resume_once.py`: lượt đầu trần `-Budget` 30600 s; mã 124 (quá trần — bộ canh giết cả
  cây tiến trình, hoặc lệnh con tự trả 124) mà `<trạm giọng>/omnivoice/truyen-out/_resume.json`
  còn dải dở ⇒ tin ⏳ "quá trần — đang chạy tiếp từ chương X" ⇒ chạy lại ĐÚNG MỘT LẦN với trần
  `-ResumeBudget` 10800 s, dùng cache chương (không đọc lại chương nào). Không còn `_resume.json`
  ⇒ không chạy tiếp; lượt chạy tiếp lại 124 ⇒ dừng, không lặp. Tin ✅/❌ của lượt chạy tiếp do
  wrapper gửi như thường, kèm dòng "đã tự chạy tiếp từ chương X" (`compose_report.py` đọc
  `RESUME_ONCE=…`). Đặt ở runner, không ở wrapper, để wrapper Task Scheduler ngoài repo cũng có.
  Mẫu `daily-story`: `--timeout` 30600 → **42300** (lưới an toàn ≥ tổng hai trần). Windows:
  `run-daily-truyen.ps1 -Register` (qua `NOTIFY_RUN`, `ExecutionTimeLimit` = hai trần + 1800 s).
  Lượt 301–310 (02/10) bị giết 08:30 sau 9/10 chương, người phải `launchctl kickstart` tay.
- **Job dọn dung lượng hằng tuần** `studio.marketing.weekly-cleanup` (CN 04:00, `Background`,
  trần 1 h): `run-weekly-cleanup.ps1` → `weekly_cleanup.py`. (1) `prune_media.py
  --video-policy published --audio-policy web-first --days 14 --move-to <trạm>/_trash/<ngày>`
  trên thư mục của trạm marketing + giọng + video (DỜI, có kê khai; tự nhặt `truyen-state.json`/
  `playlist-youtube.json` làm bằng chứng); (2) đổ `_trash/<ngày>` dời quá 30 ngày (theo ngày dời,
  không theo mtime); (3) xoay vòng log `logs/launchd/` + `daily-logs/` của trạm giọng: xoá quá 60
  ngày, cắt file trên 5 MB giữ 1 MB cuối tại chỗ; (4) báo dung lượng từng trạm — tin Telegram do
  `compose_report.py` soạn từ dòng `CLEANUP_*`, nên hai wrapper (launchd/Task Scheduler) cùng nội
  dung. `-DryRun` không chạm một byte. **`install_launchd.py --all` KHÔNG nạp job này** (mới:
  `CHI_DICH_DANH`, chỉ `--only`); mẫu không có chỗ trống kênh/chiến dịch nên không cần khai.
  Windows: `run-weekly-cleanup.ps1 -Register`.
- **P1-24 — rào render trước các bước tốn kém.** `Invoke-RenderPreflight` (`brand-paths.ps1`) gọi
  `video-studio probe` (agent-video-studio 0.2.5 — render thật một trang 320×180 dài 0,5 s, vài
  giây) trong `run-toptoday-hot.ps1`, `run-weekly-news.ps1`, `run-weekly-repo.ps1`: SAU kiểm nhịp
  + nhạc nền, TRƯỚC nghiên cứu (agent) và TTS. Kẹt (`RENDER_STUCK`) hoặc hỏng ⇒ dừng **mã 5**,
  tin ❌ "MÔI TRƯỜNG RENDER KẸT (HyperFrames không mở được trang) — khởi động lại máy rồi chạy
  lại" (`compose_report.py` + định dạng dự phòng của `notify_run.py`); thiếu npx ⇒ mã 3;
  video-studio cũ chưa có `probe` ⇒ nhắc rồi đi tiếp. `RENDER_PROBE_TIMEOUT` (giây, mặc định 30)
  đổi trần — đặt 1 để giả lập máy kẹt khi nghiệm thu. Render hỏng vì `Navigation timeout` cũng
  được `compose_report` gắn gợi ý khởi động lại. Hot AI 02/10 18:00 hỏng sau 42 phút vì môi trường
  macOS kẹt; khởi động lại máy là hết.
- **Khởi động lại định kỳ**: chỉ ghi thành bước tài liệu cho Đức quyết (`docs/RUNBOOK-DOI-MAY.md`
  mục "Khởi động lại định kỳ máy chạy lịch") — `pmset repeat restart` cần admin, kèm ba điều phải
  kiểm (tự đăng nhập, không cắt ngang lượt truyện, Windows).
- **Sau review độc lập (02/10)** — 4 Phải sửa + các Nên sửa:
  - rào render: chỉ `RENDER_STUCK` mới là mã 5; `probe` mã 2 KÈM JSON = cấu hình sai ⇒ dừng mã 2
    (trước đó bị coi là "video-studio cũ" và cho qua); thiếu gói `video_studio` ⇒ 3; hỏng khác ⇒ 1;
    runner kiểm `$ovpy` (thiếu ⇒ 3) và ép `$pf` là số — `exit $null` từng ra mã 0 (✅ giả);
  - truyện: `daily_truyen.py` ghi `phase: publish` vào `_resume.json` TRƯỚC khi upload ⇒ bộ canh
    KHÔNG chạy tiếp lượt bị giết lúc đang đăng (chống video trùng công khai); `read_story.py` ghi
    `Chuong_<n>.wav` nguyên tử (tên tạm + `os.replace`) — file cụt không còn bị dùng lại như chương
    xong; bộ canh bắt SIGTERM/SIGHUP để giết nhóm con (macOS: session riêng, wrapper không với tới);
    tin báo lượt chạy tiếp lại quá trần / quá trần không còn dấu / quá trần lúc đăng;
  - job dọn: không cắt log vừa ghi trong 1 h (lượt truyện có thể đang chạy lúc CN 04:00); kê khai
    mang giờ (hai lượt cùng ngày không ghi đè); mỗi bước bọc riêng; `prune_media` có trần 2400 s;
    trạm giọng/video chưa phân giải ⇒ `CLEANUP_SKIP` + cảnh báo thay vì ✅ im lặng; `prune_media`
    hỏng giữa chừng ⇒ tin nói "chưa rõ đã dời bao nhiêu" + đường kê khai; số ngày thùng rác theo cờ;
  - `install_launchd.py --uninstall --all` gỡ cả job chỉ-đích-danh; `-Register` của truyện cảnh
    báo task cũ trỏ cùng chiến dịch.
  - vòng 2: lượt THEO LỊCH gặp dấu `phase: publish` của chính dải đó thì `daily_truyen.py` DỪNG
    (`PUBLISH_GUARD=blocked`, mã 1, mỗi đêm cho tới khi người xử lý) — trước đó nó ghi đè dấu rồi
    upload lần hai; job dọn: cầu dao từ chối ⇒ "KHÔNG dời gì" (không còn "chưa rõ đã dời").
  - vòng 3: gỡ chặn bằng LỆNH, không sửa JSON tay — `daily_truyen.py --state … --confirm-published`
    (kênh ĐÃ có tập: ghi `last_end` = act_end THẬT + `next_url` mới, lấy từ dấu ghi lúc vào pha
    publish — sửa tay `last_end=end` từng làm pntt2 crawl lại đúng dải vừa đăng) hoặc
    `--clear-publish-guard` (CHƯA có: lượt sau dựng + đăng lại); chặn so theo slug + dải (không
    theo giọng); dấu publish của chiến dịch KHÁC trên cùng trạm cũng chặn (`_resume.json` dùng chung
    cả trạm); ghi pha publish hỏng ⇒ KHÔNG đăng; job dọn nhận "từ chối" theo việc chưa có kê khai
    kế hoạch; probe giết cây con cả khi bị Ctrl-C.
- Test mới: `test_resume_once.py`, `test_weekly_cleanup.py`, `test_render_preflight.py`; cập nhật
  `test_launchd_templates.py` (9 mẫu, trần truyện, job chỉ-đích-danh), `test_runner_agent_chain.py`.
- **Còn mở (không làm đợt này):** `truyen_publish.py` chưa tự chống đăng trùng (đợt này chặn ở
  tầng resume); `RENDER_PROBE_TIMEOUT` chỉ giả lập nhánh quá giờ của phép thử.

**Mac cần làm:** checkout `v1.1.8` (+ video `v0.2.5`); cài lại plist `daily-story`
(`install_launchd.py --only studio.marketing.daily-story`); chạy `run-weekly-cleanup.ps1 -DryRun`,
đọc báo cáo, rồi `--only studio.marketing.weekly-cleanup`; giả lập preflight hỏng bằng
`RENDER_PROBE_TIMEOUT=1` để thấy tin ❌ đúng.

## 1.1.7 — 2026-10-01

Ba lỗi Mac mini báo tối 01/10 (P4-RUNS: P5-01/10-TOI, P5-AGENT-CHAIN).

- **P0-10 — job nặng chạy `ProcessType=Interactive`.** Sáu mẫu `templates/launchd/`
  (daily-news-a/b, daily-story, weekly-news-a/b, weekly-repo) khai `Background` ⇒ macOS hãm CPU
  + I/O, dồn sang nhân tiết kiệm: dựng 10 chương mất 5 h 16 thay vì ~40 phút (tải trung bình 2,1
  suốt 7 h, 0 cảnh báo nhiệt). Worker + approve-poller (nhẹ, chạy liên tục) giữ `Background`.
  Cổng `tests/test_runner_agent_chain.py` xếp loại MỌI mẫu. **Mac**: cài lại plist bằng
  `install_launchd.py` để bỏ bản vá tay.
- **P1-21 — runner tin đi qua `agent_call` theo `order`.** `run-toptoday-hot.ps1`,
  `run-weekly-news.ps1`, `run-weekly-repo.ps1` không còn gọi `claude -p` thô: bước nghiên cứu đi
  qua `Invoke-AgentCall` (`brand-paths.ps1`) → `agent_call.py --engine order --expect <json>`.
  Tool giữ tương đương allowlist cũ (`web,read,write,shell:curl,shell:python[,shell:<python
  giọng>]`). Hết hạn mức ở MỌI engine ⇒ runner thoát **mã 4** (🟡). Lỗi khác sau khi `agent_call`
  đã lùi hết chuỗi ⇒ abort ngay (không lặp lại cả chuỗi ba lần). Hot Data 01/10 chết vì hạn mức
  `claude` dùng chung với phiên tương tác, trong khi agy (đầu `order`) chạy được.
  `agent_call.py` nhận `--engine order` (= mục đầu của `order`). Trang tuần (`.html`) chạy với
  `--no-content-gate` để giữ nguyên hành vi cũ.
- **P1-22 — chuỗi lùi bắt cả lỗi engine/mạng TẠM.** `network`/`engine` (ERROR rỗng, timeout của
  agy, CLI thoát ≠ 0, mã 0 mà thiếu artifact) ⇒ thử lại chính engine đó MỘT lần (nghỉ 15 s), rồi
  sang engine kế; hết trần `--timeout` thì sang thẳng. `content` (lọt chữ nội bộ) vẫn dừng. Prompt
  vượt trần argv của agy (30 000 ký tự) mà chuỗi còn engine khác ⇒ bỏ qua agy thay vì mã 2. Lượt
  truyện 01/10 20:59: agy `timeout waiting for response` sau 7 s ⇒ trước đây dừng, hook YouTube
  rơi về mô tả tĩnh dù codex/claude chạy được.

## 1.1.6 — 2026-10-01

Repo tự khai và tự kiểm ĐỦ công cụ + thư viện mà lượt truyện dùng. Lượt truyện đầu trên Mac
mini (01/10) hỏng 3 lần liên tiếp, cả ba vì một thứ bắt buộc repo không khai hoặc không kiểm;
Windows không lộ vì đã cài tay từ trước. Lượt chạy thật trên máy đã đủ không đổi.

- **P0-8 — ghim cặp `faster-whisper` + `av`** trong `requirements-runners.txt`:
  `faster-whisper>=1.2,<1.3`, `av>=15,<19` (PyAV 19 bỏ `metadata_errors` mà
  `faster_whisper.audio.decode_audio` truyền ⇒ `TypeError` ở bước căn phụ đề). `av` vào
  `runner_deps.MODULES`. `doctor` thêm phép kiểm **hành vi**: gọi `decode_audio` trên wav 1 giây
  bằng `OMNIVOICE_PY` — hỏng là **ĐỎ** khi trạm có chiến dịch truyện.
- **P0-9 — ffmpeg đủ bộ lọc**: `doctor` chạy `ffmpeg -hide_banner -filters` trên ĐÚNG file
  pipeline truyện gọi và đòi `drawtext`, `subtitles`, `ass`; thiếu là **ĐỎ** kèm lệnh cài theo
  OS (macOS `brew install ffmpeg-full`, Windows Gyan full). Dò ffmpeg gom về
  `truyen_paths.ff_exe`: `FFMPEG_DIR` → (macOS) keg-only `ffmpeg-full` → PATH; keg thắng
  ffmpeg core trên PATH, nên không cần symlink tay. `make_video.py` dùng đúng hàm đó.
- **P1-19 — `run.ps1`**: `install_launchd.py` (cả `--dry-run`) trả **mã 2** khi job sẽ gọi
  `<trạm>/<kênh>/<chiến dịch>/<runner|run.ps1>` không có, kèm lệnh chép `run.ps1` mẫu.
  `doctor` đỏ cho cùng lỗi với label khai trong `<trạm>/launchd.json`; chiến dịch khai
  `runtime.runner` mà thiếu `run.ps1` (máy gọi thẳng runner) là *nhắc*. `station.py export`
  liệt kê chiến dịch thiếu `run.ps1` (`missing_run_ps1`); RUNBOOK-DOI-MAY §5 thêm hai dòng.
- **Nhận diện truyện**: chiến dịch dùng runner RIÊNG (vd `run-daily-truyen-p2.ps1`) gọi engine
  truyện giờ được tính là truyện — trước đây `doctor` bỏ qua mọi phép kiểm truyện với trạm này.
- **Cổng CI `runtime-truyen`** (Windows + macOS): cài ffmpeg đúng như INSTALL (macOS
  `ffmpeg-full` KHÔNG thêm vào PATH) + `requirements-runners.txt`, rồi CHẠY THẬT `make_video.py`
  (video 5 giây: tiêu đề `drawtext` + font + phụ đề libass, đo phụ đề bằng điểm ảnh) và
  `decode_audio`. `MARKETING_STUDIO_REQUIRE_RUNTIME=1` biến skip thành đỏ.
- **Nâng cấp máy đang chạy**: `<OMNIVOICE_PY> -m pip install -r requirements-runners.txt` (đưa
  `av` về trong khoảng ghim); macOS cài `ffmpeg-full` rồi gỡ symlink tạm ở `~/.local/bin` nếu
  có; chép `run.ps1` vào chiến dịch mà `doctor` nhắc.

## 1.1.5 — 2026-09-30

Dọn gọn theo review 30/09 — chỉ mục rủi ro không/thấp. Hành vi chạy không đổi (runner, lịch,
đăng, mã thoát `doctor`).

- **`.gitignore`** chặn thêm thứ công cụ tự sinh: `.claude/settings.local.json`,
  `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, `.idea/`, `.vscode/`, `*.log`.
  Không file tracked nào khớp. Canh từng dòng + `git check-ignore` trong
  `tests/test_gitignore_guard.py`.
- **`doctor` nhắc clone quá sâu trên Windows**: đường repo + đường tracked dài nhất
  (`DUONG_TRACKED_DAI_NHAT = 110`, thực tế 107) vượt 259 ký tự ⇒ một dòng *nhắc* gợi ý
  `core.longpaths` hoặc clone vào đường ngắn hơn. Không đỏ, mã thoát không đổi; macOS/Linux
  không nhắc. Test giả đường dài bằng monkeypatch + test canh hằng không tụt dưới thực tế.
  Thêm dòng ở `docs/troubleshooting.md` mục *Khi cài*.
- **CI**: `actions/checkout` v4.2.2 → v5.1.0, `actions/setup-python` v5.6.0 → v6.3.0 (Node 24;
  Node 20 bị GitHub báo deprecated), vẫn ghim SHA kèm tag.

## 1.1.4 — 2026-09-30

Bộ test cô lập khỏi secret thật của máy đang chạy. Lượt chạy thật không đổi (biến chốt chỉ
bộ test đặt).

- **P1-18** Máy chạy lịch `embedded` điền `<repo>/.env` (con trỏ tới `~/.secret/**`) thì
  `pytest` trần đỏ 5 ca, một assert in ra mẩu cấu hình Telegram thật, và
  `test_notify_run::test_chay_nhu_lenh_that…` chạy `notify_run.py` như tiến trình con đọc
  được `TG_CONFIG` thật (có đường gửi tin thật). Sửa: `tests/conftest.py` autouse gỡ mọi biến
  con trỏ bí mật + `TG_*`, và đặt `studio_paths.BIEN_CHAN_ENV_FILE`
  (`MARKETING_STUDIO_TEST_NO_DOTENV`) = bản clone đang test ⇒ `.env` của nó không được đọc,
  kể cả trong tiến trình con. Test `test_co_lap_secret.py`.
- **Cổng CI**: job "cài embedded rồi pytest" dựng `.env` + `~/.secret` GIẢ trước `pytest` trần
  — trước bản sửa đỏ đúng 5 ca trên cả hai OS.

## 1.1.3 — 2026-09-30

Hai lỗi Mac báo khi nghiệm thu 1.1.2. Lượt đăng truyện thật không đổi.

- **P2-21** `story/truyen_publish.py --dry-run` không gọi agent nữa: `build()` trước đây gọi
  `gen_hook()` (agent_call → agy/codex/claude, lùi `claude -p`) TRƯỚC khi xét `--dry-run`, nên
  "xem trước" vẫn tốn hạn mức và ghi ledger. Nay dry-run đi nhánh mô tả tĩnh; muốn xem cả hook
  thì thêm `--with-hook`. `main(argv)` nhận danh sách tham số (để test). Test
  `test_story_publish_dryrun.py`.
- **P3-15** `export --for-machine`: `_may._doc` của máy nguồn (hay nêu đường trạm máy đó, vd
  `tram = ~/.marketing`) thay bằng lời không gắn máy `station.DOC_MAY`.

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
