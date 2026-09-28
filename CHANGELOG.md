# CHANGELOG — agent-marketing-studio

Mỗi mục là một phiên bản. Mục đầu luôn là số trong `pyproject.toml`
(`tests/test_version_sync.py` giữ điều này). Phiên bản chưa gắn tag ghi rõ "chưa phát hành".

## 0.9.0 — chưa phát hành

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
