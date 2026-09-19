#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cổng pre-commit của chế độ `embedded`: chặn commit nội dung trạm và thứ giống secret.

Chế độ `embedded` đặt trạm (`workspace/`) và `<repo>/.env` NGAY TRONG repo. `.gitignore`
đã chặn chúng, nhưng `.gitignore` chỉ là thói quen — `git add -f`, một dòng ignore bị sửa,
hay một công cụ tự stage là đủ để nội dung riêng đi lên một repo công khai. Hook này là
lớp rào thứ hai, và là lớp cuối còn sửa được.

Chặn hai thứ:
  · **đường dẫn**: bất cứ gì dưới `workspace/`, `.env` / `.env.*` (trừ `.env.example`),
    `studio.local.json`
  · **nội dung**: dòng THÊM MỚI trong diff trông giống token (GitHub, Hugging Face,
    OpenAI/Anthropic, AWS, Slack, Google, Facebook Graph, khoá riêng PEM) hoặc gán
    `token|secret|api_key|password = "<chuỗi dài>"`

Chỉ soi phần ĐÃ STAGE, và chỉ soi dòng thêm mới: dòng cũ đã nằm trong lịch sử rồi, chặn ở
đây không cứu được gì mà lại khiến người ta quen `--no-verify`.

Mã thoát: 0 cho commit chạy tiếp · 1 chặn. Cố ý vượt: `git commit --no-verify`.
"""
from __future__ import annotations

import re
import subprocess
import sys

CHAN_TIEN_TO = ("workspace/",)
CHAN_TEN = ("studio.local.json",)

MAU_TOKEN = [
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abpr]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"\bEAA[A-Za-z0-9]{40,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(token|secret|api[_-]?key|password)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"),
]


def _git(repo, *args) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip())
    return r.stdout


def duong_bi_chan(duong: str) -> bool:
    p = duong.replace("\\", "/")
    ten = p.rsplit("/", 1)[-1]
    if p.startswith(CHAN_TIEN_TO) or p in CHAN_TEN:
        return True
    return ten == ".env" or (ten.startswith(".env.") and ten != ".env.example")


def soi(repo=".") -> list[str]:
    """Danh sách vấn đề của phần đã stage (rỗng = cho commit)."""
    van_de = []
    for n in (t for t in _git(repo, "diff", "--cached", "--name-only", "-z").split("\0") if t):
        if duong_bi_chan(n):
            van_de.append(f"{n}: nội dung trạm / secret không được vào repo")
    dang_o = None
    for dong in _git(repo, "diff", "--cached", "-U0", "--no-color").splitlines():
        if dong.startswith("+++ "):
            dang_o = dong[6:] if dong.startswith("+++ b/") else dong[4:]
            continue
        if dong.startswith("+") and not dong.startswith("+++"):
            for mau in MAU_TOKEN:
                if mau.search(dong):
                    van_de.append(f"{dang_o}: dòng thêm mới trông giống token/secret")
                    break
    return van_de


def main(argv=None) -> int:
    try:
        van_de = soi(".")
    except (RuntimeError, OSError) as e:
        print(f"[pre-commit] không kiểm được: {e}", file=sys.stderr)
        return 1
    if not van_de:
        return 0
    print("[pre-commit] CHẶN commit:", file=sys.stderr)
    for v in van_de:
        print("  - " + v, file=sys.stderr)
    print("Gỡ khỏi stage: git restore --staged <file>. Cố ý thì: git commit --no-verify.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
