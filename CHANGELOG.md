# CHANGELOG — agent-marketing-studio

Mỗi mục là một phiên bản. Mục đầu luôn là số trong `pyproject.toml`
(`tests/test_version_sync.py` giữ điều này). Phiên bản chưa gắn tag ghi rõ "chưa phát hành".

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
