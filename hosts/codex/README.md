# agent-marketing-studio với Codex

Muốn agent cài giúp: dán prompt trong [INSTALL.md](../../INSTALL.md#prompt-copy-dán) vào Codex (CLI
hoặc desktop). Tự cài: làm theo mục 2–9 của [INSTALL.md](../../INSTALL.md).

- **Skill:** Codex đọc skill của project ở [`.agents/skills/`](../../.agents/skills/) — chính là skill
  gốc, không có bản sao. Không cần chép vào `~/.codex/skills/`.
- **Mở đúng chỗ:** chạy `codex` trong thư mục repo; bản desktop thì mở repo làm project và tin cậy
  (trust) thư mục. Hỏi "liệt kê skill của repo này" để kiểm; phải thấy bốn skill.
- **Sandbox:** nếu sandbox của Codex chặn `winget`/`pip` hay ghi ra ngoài thư mục, đưa đúng lệnh cho
  người dùng tự chạy trong PowerShell — không đổi thiết lập sandbox.
- **Plugin (tuỳ chọn):** `.codex-plugin/plugin.json` trỏ `./.agents/skills/`; bản cài qua marketplace
  nằm trong cache và không tự theo `git pull`.
- **Luật làm việc:** agent đọc [`AGENTS.md`](../../AGENTS.md) — ba cổng duyệt của người, không tự đăng.
