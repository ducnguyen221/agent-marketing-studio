# agent-marketing-studio với Google Antigravity

Muốn agent cài giúp: dán prompt trong [INSTALL.md](../../INSTALL.md#prompt-copy-dán) vào Antigravity.
Tự cài: làm theo mục 2–9 của [INSTALL.md](../../INSTALL.md).

- **Skill:** Antigravity đọc skill của workspace ở [`.agents/skills/`](../../.agents/skills/) — skill
  gốc, không bản sao.
- **Mở đúng chỗ:** mở thư mục repo làm workspace. Hỏi "liệt kê skill của repo này" để kiểm; phải thấy
  bốn skill. Không thấy thì bảo agent mở trực tiếp `.agents/skills/<tên>/SKILL.md` và ghi lại rằng
  phiên bản Antigravity đó chưa tự nạp skill của workspace.
- **Luật làm việc:** agent đọc [`AGENTS.md`](../../AGENTS.md) — ba cổng duyệt của người, không tự đăng.
