# Bộ chạy tin/truyện — `scripts/runners/`

Từ 1.1.0 bộ chạy của các chiến dịch tin (hằng ngày, hằng tuần, repo tuần) và lượt truyện sống
trong repo, không còn chép vào `<trạm>/engine`. Máy nào cũng lấy CÙNG một mã bằng `git`
(Windows: `git pull`; máy lịch Mac: `git checkout <tag>`). Nội dung và cấu hình của từng kênh vẫn
ở trạm: `channel.yml`, `campaign.md`, prompt, `build-index.ps1`/`build_yt_desc.py`/`send_newsletter.py`
của kênh, state truyện.

## Ai gọi ai

`run.ps1` của chiến dịch (khuôn: `templates/station/_channel/_campaign/run.ps1`) đọc
`runtime.runner` trong `campaign.md`, sinh bản chụp cấu hình, rồi tìm runner theo thứ tự
**thư mục chiến dịch → `<repo>/scripts/runners/` → `<trạm>/engine/` (bản cũ)**.

| Runner | Chiến dịch | Việc |
|---|---|---|
| `run-toptoday-hot.ps1` | tin nóng hằng ngày (`-Brand ai|data -Publish`) | nghiên cứu (`claude -p` + last30days) → dựng video (`video-studio render`) → `publish-hot-news.ps1` |
| `run-weekly-news.ps1` | bản tin tuần | nghiên cứu → media (audio + recap + short) → YouTube → web → email → Facebook |
| `run-weekly-repo.ps1` | repo tuần | nghiên cứu một repo → video → YouTube → Facebook → sổ chống lặp |
| `run-daily-truyen.ps1` | truyện hằng ngày | `story/daily_truyen.py --state <chiến dịch>/truyen-state.json` |

`brand-paths.ps1` là chỗ DUY NHẤT phân giải đường cho mọi runner PowerShell; `paths.py` và
`story/truyen_paths.py` là bản Python của cùng luật.

## Luật đường dẫn

Không ổ đĩa, không tên người dùng, không tên thư mục chứa repo (`Code`, `Repo`…) nào được viết
sẵn làm câu trả lời. Thứ tự, cho mọi đường:

    biến môi trường (Windows: + registry User) → <repo>/.env (chỉ embedded)
    → repo anh em cùng thư mục cha (nhận bằng pyproject.toml: name)
    → thư mục cũ trong thư mục nhà — CHỈ khi có thật, kèm dòng WARN
    → DỪNG, nêu tên biến

| Cần gì | Nguồn |
|---|---|
| Trạm | đi lên từ bản chụp `-Config` tới `CHANNELS.md` → `MARKETING_STUDIO_DATA` → `studio.local.json` → `<repo>/workspace` |
| Trạm giọng / video | `VOICE_STATION` (`OMNIVOICE_DIR`) / `VIDEO_STATION` (`VIDEO_ROOT`) → `studio.local.json` → repo anh em |
| Python giọng | `OMNIVOICE_PY` → `station.json: venv` → `<trạm giọng>/omnivoice/.venv` → `.venv` của repo anh em video, rồi giọng |
| Repo web | `repo` của `channel.yml` (hiểu `${TÊN}`, `~`, đường tương đối theo thư mục cha) |
| last30days | `L30_SCRIPT` → thư mục plugin của Claude |
| Nhạc nền | `VOICE_BGM_DIR` → `<trạm video>/assets/news-bgm` |
| Con trỏ bí mật | `YT_TOKEN_PATH`, `YT_CLIENT_SECRET`, `FB_CONFIG`, `EMAIL_CONFIG` (+ hậu tố kênh) — chỉ ĐƯỜNG DẪN |

Bảng biến đầy đủ: `knowledge/toolchains/SECRETS.md`. Cổng giữ luật: `tests/test_runners_portable.py`,
`tests/test_ps1_portable.py`, `tests/test_khong_gia_dinh_thu_muc_cha.py`.

## Phụ thuộc ngoài repo (`doctor` kiểm, không cài)

- gói Python của bộ chạy trong **venv giọng**: `requirements-runners.txt`;
- script `last30days` (plugin Claude);
- mp3 của từng style trong `bgm-library.json` — style thiếu mp3 thì AI không được chọn;
- `claude` CLI đã đăng nhập (`NOT_CHECKED`: doctor không gọi `claude -p`).

## Chạy tay / UAT

```
pwsh -File <trạm>/<kênh>/<chiến dịch>/run.ps1 -Uat -SkipResearch -Date <yyyy-mm-dd>
```

`-Uat`: không upload YouTube, không git push, Facebook dry-run, Excel ghi sheet `UAT *`.

## Sửa mã

Sửa ở repo, qua PR có CI hai hệ điều hành — không sửa bản trong trạm. `.ps1` có tiếng Việt phải
giữ BOM (PS 5.1). Mã truyện trong repo không tự sửa mình (`heal_agent`) trừ khi `TRUYEN_HEAL=1`.
