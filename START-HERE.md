# Bắt đầu ở đây

agent-marketing-studio là xưởng nội dung cho AI agent: lên chiến dịch, viết bài, chấm 24 cổng,
dựng trang, đăng qua hook của bạn — có cổng duyệt của người. Chạy trên Windows và macOS. Nội dung
của bạn nằm ở **trạm** — mặc định `workspace/` trong repo, bị git bỏ qua.

## Cách nhanh: nhờ agent cài

Dán khối này vào Claude Code, Codex hoặc Antigravity (luật và từng bước agent làm: [INSTALL.md](INSTALL.md)):

```text
Hãy cài agent-marketing-studio lên máy này cho chính ứng dụng AI bạn đang chạy.
Nguồn duy nhất: https://github.com/ducnguyen221/agent-marketing-studio
Đọc trước hướng dẫn cho agent tại
https://raw.githubusercontent.com/ducnguyen221/agent-marketing-studio/main/INSTALL.md
(không mở được thì clone repo rồi đọc INSTALL.md trong đó) và làm đúng, đủ các bước:
kiểm tra máy, hỏi tôi trước khi cài thêm phần mềm, clone về thư mục an toàn (không OneDrive),
hỏi tôi chọn chỗ đặt trạm nội dung, chạy bộ cài, chạy doctor, kiểm bằng trạm mẫu.
Quy tắc: chỉ chạy lệnh có trong repo hoặc INSTALL.md; không đổi chính sách hệ thống;
không đọc hay ghi mật khẩu/khóa; không đăng bài; gặp lỗi thì dừng và giải thích bằng lời thường.
Kết thúc bằng bản tóm tắt: đường dẫn repo, trạm, từng dòng doctor, việc tôi cần làm tiếp.
```

## Tự cài

Cần Git và Python 3.10–3.13 (khuyến nghị 3.12). Mac mới: `python3` là 3.9 — dùng `python3.12`
(`brew install python@3.12`). Clone vào thư mục cục bộ, **không** để trong OneDrive/iCloud/Dropbox.

| Bước | Windows (PowerShell) | macOS (Terminal) |
|---|---|---|
| venv | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` |
| phụ thuộc | `.\.venv\Scripts\python -m pip install -r requirements.txt` | `.venv/bin/python -m pip install -r requirements.txt` |
| dựng trạm | `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Mode embedded` | `./install.sh --mode embedded` |
| khám | `.\.venv\Scripts\python scripts\pipeline\doctor.py` | `.venv/bin/python scripts/pipeline/doctor.py` |

Rồi:

1. Đọc từng dòng `doctor`. Dòng `samples: PASS` xác nhận bài mẫu offline
   ([samples/README.md](samples/README.md)); "giọng/video: chưa bật" là bình thường.
2. Thử chấm cổng bài mẫu: `scripts/pipeline/blog_gates.py samples/bai-mau --home-domain example.com`
   — kết quả kỳ vọng là `fail` với 6 cổng chặn (bài mẫu cố ý ngắn).
3. Dựng kênh đầu tiên: [docs/ONBOARDING.md](docs/ONBOARDING.md).
4. Mac sẽ chạy lịch: xem trước bằng `scripts/runners/install_launchd.py --dry-run --no-load`,
   khai job theo [docs/launchd.md](docs/launchd.md). Runner `.ps1` cần `pwsh`
   (`brew install --cask powershell`).

## Cập nhật, gỡ, gặp lỗi

- Cập nhật: `scripts/pipeline/studio.py update` (chỉ `git pull --ff-only`).
- Gỡ: `uninstall.ps1 -DryRun` / `./uninstall.sh --dry-run` để xem trước — gỡ phần cài, **giữ** trạm.
- Gặp lỗi: [docs/troubleshooting.md](docs/troubleshooting.md). Từng ứng dụng AI: [hosts/README.md](hosts/README.md).
