# Chọn ứng dụng AI (host)

"Host" là ứng dụng chạy AI agent. Cách dễ nhất: dán prompt trong
[INSTALL.md](../INSTALL.md#prompt-copy-dán) vào ứng dụng bạn đang dùng; agent tự làm theo.

| Bạn dùng | Skill đọc từ | Hướng dẫn |
|---|---|---|
| Claude Code | `.claude/skills/` — adapter mỏng trỏ về skill gốc | [Claude Code](claude/README.md) |
| Codex (CLI và desktop) | `.agents/skills/` — skill gốc | [Codex](codex/README.md) |
| Google Antigravity | `.agents/skills/` — skill gốc | [Antigravity](antigravity/README.md) |
| Claude Desktop (tab chat) | — | [Không hỗ trợ](claude-desktop/README.md) |

## Cách repo này gắn với host

- **Không đăng ký gì vào cấu hình toàn máy.** Repo không có máy chủ MCP; bộ cài không ghi vào
  `~/.claude*`, `~/.codex/` hay `~/.gemini/`. Host thấy skill khi bạn **mở chính thư mục repo**.
- **Một nguồn skill.** Skill gốc ở [`../.agents/skills/`](../.agents/skills/). Adapter cho Claude ở
  [`../.claude/skills/`](../.claude/skills/) chỉ chứa `name`/`description` và dòng "đọc file gốc";
  sinh lại bằng `python scripts/build_host_adapters.py`, kiểm bằng `--check` (CI và `doctor` chạy).
- **Plugin (tuỳ chọn).** Repo có manifest `.claude-plugin/` và `.codex-plugin/` trỏ cùng thư mục
  skill gốc. Cài qua marketplace thì host có thể giữ **bản sao trong cache** — bản đó không tự cập
  nhật theo `git pull`. Đường khuyến nghị vẫn là mở thư mục repo.
- **Kiểm thật chỉ có trong phiên mới.** `doctor` ghi `NOT_CHECKED` cho từng host: nó không mở ứng
  dụng AI được. Mở phiên mới tại thư mục repo và hỏi danh sách skill — phải có `campaign-pipeline`,
  `content-production`, `hook-writer`, `thread-writer`.
- **Script chạy từ repo, nội dung ở trạm.** Mọi skill gọi script trong `scripts/` của bản clone; kênh,
  chiến dịch, bài nằm ở trạm (`workspace/` hoặc thư mục bạn chỉ định) — xem
  [docs/WORKSPACE.md](../docs/WORKSPACE.md).
