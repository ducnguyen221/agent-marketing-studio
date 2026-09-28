#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh adapter skill cho Claude Code từ skill gốc ở `.agents/skills/`.

Skill gốc sống ở `.agents/skills/<tên>/SKILL.md` — Codex và Antigravity đọc thẳng thư mục
đó. Claude Code đọc skill của project ở `.claude/skills/`, nên mỗi skill gốc có một adapter
MỎNG ở đó: cùng `name`/`description` (để Claude định tuyến), thân chỉ bảo đọc file gốc. Không
chép nội dung skill: hai bản sửa tay là hai bản trôi khỏi nhau.

    python scripts/build_host_adapters.py           # sinh/cập nhật adapter
    python scripts/build_host_adapters.py --check   # chỉ kiểm; lệch thì mã 1 (CI, doctor)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills"
CLAUDE = ROOT / ".claude" / "skills"


def _frontmatter(skill: Path) -> str:
    """Khối frontmatter nguyên văn (giữa hai dòng `---`). Thiếu name/description → lỗi."""
    parts = skill.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{skill}: thiếu frontmatter")
    fm = parts[1].strip("\n")
    keys = {line.split(":", 1)[0] for line in fm.splitlines() if line and not line[0].isspace()}
    if not {"name", "description"} <= keys:
        raise ValueError(f"{skill}: frontmatter thiếu name hoặc description")
    return fm


def adapter(skill: Path) -> str:
    name = skill.parent.name
    return (
        f"---\n{_frontmatter(skill)}\n---\n\n"
        f"# {name} — adapter nguồn\n\n"
        f"Đọc toàn bộ [SKILL.md gốc](../../../.agents/skills/{name}/SKILL.md) trong repo trước "
        "khi làm. Mọi script, quy trình, template và tài liệu mà skill dẫn tới phải mở trực "
        "tiếp từ repo này; không dùng bản chép trong cache hay trong trạm nội dung. Không mở "
        "được file gốc thì báo thiếu nguồn và dừng tác vụ này.\n"
    )


def expected() -> dict[Path, str]:
    skills = sorted(SOURCE.glob("*/SKILL.md"))
    if not skills:
        raise ValueError(f"không thấy skill gốc nào trong {SOURCE}")
    return {CLAUDE / s.parent.name / "SKILL.md": adapter(s) for s in skills}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sinh adapter .claude/skills từ .agents/skills.")
    ap.add_argument("--check", action="store_true", help="chỉ kiểm, không ghi; lệch thì mã 1")
    a = ap.parse_args(argv)
    try:
        want = expected()
    except ValueError as e:
        print(f"build_host_adapters: {e}", file=sys.stderr)
        return 2
    drift = [p for p, t in want.items()
             if not p.is_file() or p.read_text(encoding="utf-8") != t]
    # Adapter mồ côi: skill gốc đã xoá/đổi tên mà adapter còn — Claude vẫn thấy một skill
    # trỏ vào file không có.
    orphans = sorted(p for p in CLAUDE.glob("*/SKILL.md") if p not in want)
    if a.check:
        for p in drift:
            print(f"lệch nguồn: {p.relative_to(ROOT).as_posix()}")
        for p in orphans:
            print(f"mồ côi (skill gốc không còn): {p.relative_to(ROOT).as_posix()}")
        return 1 if drift or orphans else 0
    for p in drift:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(want[p], encoding="utf-8", newline="\n")
        print(f"đã ghi: {p.relative_to(ROOT).as_posix()}")
    for p in orphans:
        print(f"mồ côi, xoá tay nếu đúng: {p.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    raise SystemExit(main())
