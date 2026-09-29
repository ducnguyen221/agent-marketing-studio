# agent-marketing-studio với Claude Code

Muốn agent cài giúp: dán prompt trong [INSTALL.md](../../INSTALL.md#prompt-copy-dán) vào Claude Code.
Tự cài: làm theo mục 2–9 của [INSTALL.md](../../INSTALL.md).

- **Skill:** Claude Code đọc skill của project ở [`.claude/skills/`](../../.claude/skills/). Mỗi file ở
  đó là adapter mỏng trỏ về skill gốc trong [`.agents/skills/`](../../.agents/skills/); script, quy
  trình, template đều đọc thẳng từ repo. Không cần chép skill vào `~/.claude/skills/`.
- **Mở đúng chỗ:** khởi động Claude Code **trong thư mục repo**. Hỏi "liệt kê skill của repo này" để
  kiểm; phải thấy bốn skill.
- **Plugin (tuỳ chọn):** `.claude-plugin/plugin.json` trỏ `./.agents/skills/`. Cài dạng plugin thì
  Claude giữ bản sao trong cache, không tự theo `git pull` — chỉ dùng khi bạn hiểu đánh đổi đó.
- **Sau `git pull`:** mở phiên mới để Claude đọc lại skill.
- **Luật làm việc:** agent đọc [`AGENTS.md`](../../AGENTS.md) — ba cổng duyệt của người, không tự đăng.
