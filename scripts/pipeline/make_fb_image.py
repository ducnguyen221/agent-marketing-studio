#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo ảnh đính kèm bài Facebook bằng Codex qua cầu A2A, rồi giữ hồ sơ soát chữ.

Hai lệnh:

    make   --post <thư mục bài>
        đọc facebook/infographic.prompt.txt → nhờ Codex sinh ảnh → facebook/infographic.png
        + facebook/infographic.meta.json (text_check = pending)

    verify --post <thư mục bài> --by <tên> --quote "<câu người soát nói nguyên văn>" [--failed]
        ghi kết quả soát chữ trên ảnh, gắn với ĐÚNG các byte ảnh đã soát

## Vì sao phải có bước soát

Model sinh ảnh vẫn vỡ dấu tiếng Việt, và ảnh đã đăng thì không sửa được. Máy không đo được
dấu trên ảnh, nên kết quả soát là DẤU VẾT CỦA NGƯỜI, cùng luật với cổng duyệt: phải có ai
soát và người đó nói gì. `fb_publish.py` từ chối đăng ảnh chưa soát, hoặc ảnh đã bị đổi sau
khi soát (so bằng sha256 của file).

## Vì sao Codex ghi vào repo rồi script mới chuyển sang bài

Cầu chỉ cho Codex làm việc trong vùng thư mục đã khai, và thư mục trạm không nằm trong đó.
Codex lưu ảnh vào `.tmp/` của repo này (đã gitignore), script kiểm ảnh rồi chuyển sang bài.
Không nới vùng của cầu: vùng đó gác mọi lượt gọi chéo trên máy, không riêng việc tạo ảnh.

## Ba điều không bao giờ

1. Không ghi đè ảnh đã có. Muốn sinh lại phải `--force`, và ảnh cũ được giữ lại cạnh bên.
   Model không tái lập: mất ảnh cũ là mất ảnh có thể đã được duyệt.
2. Không retry khi cầu trả mã 2. Mã 2 là BỊ CHẶN — gọi lại y hệt cũng bị chặn.
3. Không tin đường dẫn Codex tự báo. Script tự kiểm file ở đúng chỗ nó đã chỉ định.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
sys.path.insert(0, str(_HERE))
import md_io  # noqa: E402
import post_paths as PP  # noqa: E402
import studio_paths as SP  # noqa: E402
from blog_gates import PROMPT_ANH_TOI_THIEU  # noqa: E402

REPO = _HERE.parents[1]
CAU_MAC_DINH = Path.home() / ".opcos" / "bridges" / "codex-bridge" / "cli.mjs"


def _bridge_mac_dinh() -> Path:
    """Đường cầu Codex mặc định cho cờ `--bridge`: `OPCOS_CODEX_BRIDGE` → đường quen.

    Đọc qua `secret_env` nên chế độ cài `embedded` khai được trong `<repo>/.env`;
    `os.environ` thẳng thì dòng trong `.env` không ai đọc, và không gì báo vì đã có
    sẵn một đường mặc định trông hợp lệ."""
    khai = (SP.secret_env("OPCOS_CODEX_BRIDGE") or "").strip()
    return Path(khai).expanduser() if khai else CAU_MAC_DINH
# Cầu tự có trần thời gian cho mỗi lượt. Trần này chỉ chặn tiến trình con treo hẳn.
TRAN_CHO_GIAY = 900
ANH_TOI_THIEU = 800            # cùng ngưỡng với G19
FB_TOI_DA_BYTE = 8 * 1024 * 1024

PNG_SIG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])

VIEC_CHO_CODEX = """Việc: dùng công cụ tạo ảnh (image_gen) sinh ĐÚNG MỘT ảnh theo prompt bên dưới, rồi lưu
thành file PNG vào đúng đường dẫn:
{out}

Luật của lượt này:
- Chỉ tạo đúng một ảnh. Không sửa, không tạo file nào khác ngoài file PNG trên.
- Lưu định dạng PNG, khổ ngang, cỡ gần 1920x1080 nhất có thể.
- Không thêm hay đổi chữ nào trên ảnh ngoài những chuỗi prompt cho phép.
- Xong thì trả lời đúng MỘT dòng JSON: {{"path": "<đường dẫn đã lưu>"}}
- Không làm được thì trả lời đúng MỘT dòng JSON: {{"error": "<lý do>"}}

===== PROMPT ẢNH — gửi nguyên văn cho công cụ tạo ảnh =====
{prompt}
===== HẾT PROMPT ẢNH =====
"""


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kich_thuoc_png(p: Path) -> tuple[int, int] | None:
    """(rộng, cao) đọc từ khối IHDR. None nếu không phải PNG."""
    try:
        b = p.read_bytes()[:24]
    except OSError:
        return None
    if len(b) < 24 or b[:8] != PNG_SIG:
        return None
    return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")


def meta_cua(anh: Path) -> Path:
    """Hồ sơ nằm cạnh ảnh, cùng tên gốc: infographic.png → infographic.meta.json."""
    return anh.with_name(anh.stem + ".meta.json")


def _doc_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _ghi_json(p: Path, d: dict) -> None:
    md_io.write_atomic(p, json.dumps(d, ensure_ascii=False, indent=2))


def kiem_prompt(prompt: str) -> str:
    """Lý do KHÔNG được gửi prompt này đi, hoặc chuỗi rỗng. Cùng luật với G24."""
    import re
    if len(prompt) < PROMPT_ANH_TOI_THIEU:
        return f"prompt {len(prompt)} ký tự, cần từ {PROMPT_ANH_TOI_THIEU} (cổng G24)"
    ph = re.findall(r"\{\{[^}\n]*\}\}", prompt)
    if ph:
        return f"prompt còn {len(ph)} chỗ trống chưa điền: {ph[:3]}"
    return ""


def trang_thai_soat(anh: Path) -> tuple[bool, str]:
    """(được đăng chưa, lý do). `fb_publish.py` gọi đúng hàm này trước khi đăng thật."""
    m = _doc_json(meta_cua(anh))
    tc = m.get("text_check") or {}
    if not m:
        return False, f"không có {meta_cua(anh).name} — ảnh chưa qua bước soát chữ"
    if tc.get("status") != "passed":
        return False, f"soát chữ trên ảnh: {tc.get('status') or 'chưa soát'}"
    if not anh.is_file() or tc.get("image_sha256") != _sha(anh):
        return False, "ảnh đã bị đổi SAU khi soát — byte đang đăng không phải byte đã soát"
    return True, f"chữ trên ảnh đã soát bởi {tc.get('by')} lúc {tc.get('at')}"


def make(post: Path, *, cau: Path = CAU_MAC_DINH, force: bool = False,
         run=None, now: datetime | None = None) -> tuple[int, dict]:
    """Trả (mã thoát, kết quả). 0 xong hoặc đã có · 1 hỏng · 2 cầu chặn · 3 thiếu đầu vào."""
    run = run or (lambda cmd, **kw: subprocess.run(cmd, **kw))
    now = now or datetime.now()
    f_prompt, anh = PP.p(post, "fb_prompt"), PP.p(post, "fb_image")

    if anh.is_file() and not force:
        return 0, {"status": "exists", "image": str(anh),
                   "note": "đã có ảnh — không ghi đè; muốn sinh lại dùng --force"}
    if not f_prompt.is_file():
        return 3, {"status": "failed", "reason": f"không có {f_prompt} — thiếu khối ### image_prompt"}
    prompt = f_prompt.read_text(encoding="utf-8").strip()
    vi_sao = kiem_prompt(prompt)
    if vi_sao:
        return 3, {"status": "failed", "reason": vi_sao}
    if not Path(cau).is_file():
        return 3, {"status": "failed", "reason": f"không thấy cầu Codex: {cau}"}

    tam_dir = REPO / ".tmp" / "fb-images"
    tam_dir.mkdir(parents=True, exist_ok=True)
    nhan = f"{post.name[:40]}-{now.strftime('%Y%m%d%H%M%S')}"
    out = tam_dir / f"{nhan}.png"
    viec = tam_dir / f"{nhan}.task.md"
    viec.write_text(VIEC_CHO_CODEX.format(out=str(out), prompt=prompt),
                    encoding="utf-8", newline="\n")

    cmd = ["node", str(cau), "ask", "--origin", "human", "--access", "workspace",
           "--cwd", str(REPO), "--json"]
    try:
        with open(viec, "rb") as vao:
            r = run(cmd, stdin=vao, capture_output=True, timeout=TRAN_CHO_GIAY)
    except subprocess.TimeoutExpired:
        return 1, {"status": "failed", "reason": f"cầu không trả lời sau {TRAN_CHO_GIAY} giây"}
    finally:
        viec.unlink(missing_ok=True)

    ra = (r.stdout or b"").decode("utf-8", "replace") if isinstance(r.stdout, bytes) else (r.stdout or "")
    loi = (r.stderr or b"").decode("utf-8", "replace") if isinstance(r.stderr, bytes) else (r.stderr or "")
    try:
        cau_tra = json.loads(ra) if ra.strip() else {}
    except json.JSONDecodeError:
        cau_tra = {}
    if r.returncode == 2:
        return 2, {"status": "blocked", "reason": cau_tra.get("code") or cau_tra.get("error") or loi[-300:],
                   "note": "cầu CHẶN lượt này — gọi lại y hệt cũng bị chặn, đừng retry"}
    if r.returncode != 0 or not cau_tra.get("ok", True):
        return 1, {"status": "failed", "reason": cau_tra.get("error") or cau_tra.get("code")
                   or loi[-300:] or f"cầu trả mã {r.returncode}"}

    # Không tin đường dẫn Codex báo về: kiểm đúng file ở đúng chỗ đã chỉ định.
    kt = kich_thuoc_png(out) if out.is_file() else None
    if not kt:
        return 1, {"status": "failed",
                   "reason": f"Codex báo xong nhưng không có PNG hợp lệ ở {out}",
                   "codex_said": str(cau_tra.get("result") or "")[-300:]}
    if kt[0] < ANH_TOI_THIEU or kt[1] < ANH_TOI_THIEU:
        return 1, {"status": "failed", "reason": f"ảnh {kt[0]}x{kt[1]} nhỏ hơn {ANH_TOI_THIEU}px (G19)"}

    anh.parent.mkdir(parents=True, exist_ok=True)
    m_cu = _doc_json(meta_cua(anh))
    lich_su = list(m_cu.pop("history", []) or [])
    if anh.is_file():
        giu = anh.with_name(f"{anh.stem}.{now.strftime('%Y%m%d%H%M%S')}.old.png")
        os.replace(anh, giu)
        if m_cu:
            m_cu["kept_as"] = giu.name
            lich_su.append(m_cu)
    shutil.copyfile(out, anh)
    if _sha(anh) != _sha(out):
        return 1, {"status": "failed", "reason": "chép ảnh sang bài bị lệch byte"}
    out.unlink()

    m = {"schema": "fb-image/1", "generated_at": now.isoformat(timespec="seconds"),
         "generator": "codex qua cầu A2A", "bridge_call_id": cau_tra.get("call_id", ""),
         "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
         "width": kt[0], "height": kt[1], "bytes": anh.stat().st_size,
         "text_check": {"status": "pending", "by": "", "quote": "", "at": "", "image_sha256": ""},
         "history": lich_su}
    _ghi_json(meta_cua(anh), m)
    kq = {"status": "made", "image": str(anh), "width": kt[0], "height": kt[1],
          "text_check": "pending"}
    if m["bytes"] > FB_TOI_DA_BYTE:
        kq["warning"] = "ảnh lớn hơn 8 MB — Facebook hay từ chối, nén trước khi đăng"
    return 0, kq


def verify(post: Path, *, by: str, quote: str, failed: bool = False,
           now: datetime | None = None) -> tuple[int, dict]:
    if not (by or "").strip() or not (quote or "").strip():
        return 3, {"status": "failed", "reason": "thiếu --by hoặc --quote: soát chữ phải biết AI soát và người đó nói gì"}
    anh = PP.p(post, "fb_image")
    m = _doc_json(meta_cua(anh))
    if not anh.is_file() or not m:
        return 3, {"status": "failed", "reason": f"chưa có ảnh hoặc hồ sơ ảnh ở {anh.parent}"}
    f_prompt = PP.p(post, "fb_prompt")
    if f_prompt.is_file():
        hien = hashlib.sha256(f_prompt.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest()
        if m.get("prompt_sha256") and hien != m["prompt_sha256"]:
            return 1, {"status": "failed",
                       "reason": "prompt đã đổi SAU khi sinh ảnh — ảnh này không còn khớp nội dung; "
                                 "sinh lại bằng make --force rồi mới soát"}
    now = now or datetime.now()
    m["text_check"] = {"status": "failed" if failed else "passed", "by": by.strip(),
                       "quote": quote.strip(), "at": now.isoformat(timespec="seconds"),
                       "image_sha256": _sha(anh)}
    _ghi_json(meta_cua(anh), m)
    return 0, {"status": m["text_check"]["status"], "image": str(anh)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tạo ảnh Facebook qua Codex và ghi hồ sơ soát chữ.")
    sub = ap.add_subparsers(dest="lenh", required=True)
    a_make = sub.add_parser("make", help="sinh ảnh từ facebook/infographic.prompt.txt")
    a_make.add_argument("--post", required=True, type=Path)
    a_make.add_argument("--bridge", type=Path,
                        default=_bridge_mac_dinh())
    a_make.add_argument("--force", action="store_true", help="sinh lại; ảnh cũ được giữ cạnh bên")
    a_ver = sub.add_parser("verify", help="ghi kết quả soát chữ trên ảnh")
    a_ver.add_argument("--post", required=True, type=Path)
    a_ver.add_argument("--by", required=True)
    a_ver.add_argument("--quote", required=True)
    a_ver.add_argument("--failed", action="store_true", help="soát thấy sai chữ/số")
    a = ap.parse_args(argv)

    if a.lenh == "make":
        code, kq = make(a.post, cau=a.bridge, force=a.force)
    else:
        code, kq = verify(a.post, by=a.by, quote=a.quote, failed=a.failed)
    print(json.dumps(kq, ensure_ascii=False))
    return code


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
