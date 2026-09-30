# Gỡ vướng — tra theo triệu chứng

Bắt đầu luôn bằng `doctor` (Windows: `.\.venv\Scripts\python scripts\pipeline\doctor.py`, macOS:
`.venv/bin/python scripts/pipeline/doctor.py`; thêm `--json` nếu một chương trình khác đọc). Dòng
`ĐỎ` chặn, dòng `nhắc` không chặn, dòng `NOT_CHECKED` **không phải lỗi**: doctor nói thẳng điều nó
không đo được từ đây. Trang này giải thích những trường hợp dòng đó chưa đủ.

## Khi cài

| Triệu chứng | Nguyên nhân | Sửa |
|---|---|---|
| Bộ cài dừng **mã 2** ngay, không hỏi gì | phiên agent không có ai trả lời dấu nhắc | hỏi người dùng chọn `embedded` hay `separate`, rồi chạy lại có cờ (INSTALL.md mục 6) |
| Script `.ps1` bị chặn dù đã `-ExecutionPolicy Bypass` | chính sách nhóm của tổ chức | dừng, nhờ IT — **không** đổi ExecutionPolicy toàn máy |
| `python --version` mở Microsoft Store | máy chỉ có "Python giả" của Store | cài `Python.Python.3.12` (INSTALL.md mục 3) |
| macOS: `Khong tim thay Python 3.10+` / venv dựng bằng 3.9 | `python3` của Mac mới là 3.9 (kèm Command Line Tools) | `brew install python@3.12`, xoá `.venv`, dựng lại bằng `python3.12 -m venv .venv` |
| macOS: `brew: command not found` | chưa cài Homebrew, hoặc `/opt/homebrew/bin` chưa lên `PATH` | người dùng tự cài theo brew.sh; kiểm `zsh -lic 'echo $PATH'` |
| macOS: agent không thấy `brew`/`python3.12`/một biến mà người dùng thấy | shell của agent không nạp `~/.zprofile`/`~/.zshrc` | kiểm bằng `zsh -lic 'echo $TÊN_BIẾN'`; gọi bằng đường đầy đủ (`/opt/homebrew/bin/python3.12`) |
| macOS: `pwsh: command not found` khi chạy runner `.ps1` | chưa cài PowerShell 7 | `brew install --cask powershell` |
| `studio.py update` không chạy được | tải ZIP thay vì `git clone` | cài Git rồi clone lại; chép `workspace/` (nếu có) sang bản clone mới |
| `doctor` nhắc repo/trạm nằm trong thư mục đồng bộ | clone vào OneDrive/iCloud/Dropbox | clone lại vào thư mục cục bộ; đồng bộ đám mây làm hỏng git và `.venv` |
| Windows: `git clone`/`git pull` báo `Filename too long`, hoặc `doctor` nhắc "bản clone nằm sâu" | clone vào thư mục có đường dài (~150 ký tự trở lên); file tracked dài nhất của repo ~107 ký tự nên đường đầy đủ vượt 259 ký tự của Windows | `git config --global core.longpaths true` rồi clone lại, hoặc clone vào đường ngắn hơn (ví dụ `C:\src\agent-marketing-studio`) |

## Dòng `doctor`

| Dòng | Nghĩa | Sửa |
|---|---|---|
| `ĐỎ … chưa có trạm` (mã 3) | chưa chạy bộ cài | INSTALL.md mục 6 |
| `ĐỎ hai nguồn sự thật` (mã 2) | vừa có `<repo>/workspace/` vừa có trạm ở chỗ khác | giữ **một** trạm: dời `workspace/` đi, hoặc gỡ biến/`studio.local.json` đang trỏ chỗ kia |
| `ĐỎ git KHÔNG bỏ qua …` (mã 2) | dòng bắt buộc trong `.gitignore` bị xoá | khôi phục dòng đó — nội dung riêng sắp commit được |
| `nhắc … biến ĐÃ ĐIỀN trong .env mà KHÔNG script Python nào đọc` | biến của `.ps1` (`MARKETING_STUDIO_*`) hoặc tên gõ sai | biến `.ps1` đặt ở cấp user / plist; bảng đủ ở [WORKSPACE.md](WORKSPACE.md) mục `.env` |
| `nhắc .env đang mở cho người khác đọc` | quyền file quá rộng (macOS/Linux) | `chmod 600 .env` |
| `nhắc samples: WARN — lệch kỳ vọng ở …` | bài mẫu bị sửa, hoặc luật cổng đổi mà chưa cập nhật kỳ vọng | `git status samples/`; đổi luật cổng thì cập nhật `samples/gates-expected.json` cùng commit ([samples/README.md](../samples/README.md)) |
| `NOT_CHECKED samples` | bản cài không kèm `samples/` | không bắt buộc |
| `NOT_CHECKED host …` | doctor không mở ứng dụng AI | mở phiên **mới** của host tại thư mục repo, hỏi danh sách skill |
| "giọng/video: chưa bật" | năng lực thêm chưa cài | bình thường — viết bài và đăng vẫn chạy |

## Lịch chạy trên macOS (launchd)

| Triệu chứng | Nguyên nhân | Sửa |
|---|---|---|
| `install_launchd.py` dừng mã 2 "chưa khai kênh/chiến dịch cho: …" | máy mới chưa có `<trạm>/launchd.json` | khai theo [launchd.md](launchd.md), hoặc `--map <label>=<kênh>/<chiến dịch>` |
| Job chạy đúng giờ rồi chết "không thấy file" `run.ps1` | runner thật của chiến dịch tên khác | khai `runner` cho label đó trong `launchd.json` ([launchd.md](launchd.md)) |
| Chạy tay được, chạy lịch thì "thiếu token"/"thiếu biến YT_TOKEN_PATH" | launchd không đọc `~/.zshrc` hay `.env`; biến chưa vào plist | đặt biến (đường dẫn) ở `.env` (embedded) hoặc biến môi trường, rồi **chạy lại bộ cài**; dòng `nhắc` của bộ cài nêu tên biến còn thiếu |
| Bộ cài dừng mã 2 "`TÊN` phải là ĐƯỜNG DẪN" | giá trị trong `.env`/biến không phải đường dẫn tới file | sửa thành đường tới file bí mật (tuyệt đối hoặc `~/…`) |
| Log job: `pwsh`/`ffmpeg`/`claude` not found | lệnh nằm ngoài PATH của plist | PATH plist gồm `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`; cài lệnh vào đó, hoặc sửa mẫu trong `templates/launchd/` rồi chạy lại bộ cài |
| Không biết job có chạy không | — | `launchctl print gui/$UID/<label>`; log ở `<trạm>/logs/launchd/<label>.*.log` |

Gỡ một job: `install_launchd.py --uninstall --only <label>`. Đổi máy đúng thứ tự:
[RUNBOOK-DOI-MAY.md](RUNBOOK-DOI-MAY.md).

## Đăng bài

| Triệu chứng | Nguyên nhân | Sửa |
|---|---|---|
| Bước `release` báo `youtube: … không trả URL` | hook đăng không in dòng JSON có khoá `url`, hoặc thiếu con trỏ bí mật | chạy hook tay xem stderr; kiểm biến bằng `zsh -lic 'echo $YT_TOKEN_PATH'` (macOS) |
| Bài hẹn tương lai bị từ chối đăng | lệnh hook không nhận ô ngày (`{publish_at}`/`{publish_ts}`) | thêm ô ngày vào lệnh trong `campaign.md: runtime` |

Không thấy triệu chứng của bạn: chép nguyên output `doctor` và lỗi, dừng lại, hỏi người phụ trách —
đừng sửa file mẫu hay xoá trạm cho "hết đỏ".
