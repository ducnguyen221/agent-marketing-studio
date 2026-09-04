# -*- coding: utf-8 -*-
"""Đọc/ghi file Markdown có frontmatter, và bảng nằm giữa hai marker.

Từ 04/09/2026 Markdown là NGUỒN THẬT của repo này, không phải Excel. Mọi script đọc/ghi
`campaign.md`, `CAMPAIGNS.md`, `CHANNELS.md`, `research.md` đều đi qua đây — một chỗ.

HAI LUẬT THIẾT KẾ, cả hai đến từ lỗi đã trả giá:

1. **Chỉ đụng vùng giữa marker.** Bảng nằm giữa `<!-- X:BEGIN -->` và `<!-- X:END -->`;
   script không bao giờ regex cả file. Lý do: một lần thay-thế-cả-file từng xoá mất phần
   governance vì cái mốc ĐẦU khớp nhầm. Ngoài marker là chữ của người, script không chạm.

2. **Ghi bằng file tạm rồi đổi tên.** Ghi đè trực tiếp mà tiến trình chết giữa chừng thì
   mất cả file gốc lẫn file mới. `campaign.md` là bản duy nhất, không có bản sao nào khác.

GIỚI HẠN ĐÃ BIẾT — nói trước để không ai ngạc nhiên: PyYAML **không giữ comment**. Ghi lại
frontmatter là mất mọi dòng `#` trong đó. Vì thế comment hướng dẫn chỉ đặt ở file template
(`templates/*.md`), không đặt trong frontmatter của file thật đang chạy.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import yaml

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def read_fm(path) -> tuple[dict, str]:
    """Trả về (frontmatter, thân bài). Không có frontmatter -> ({}, cả file)."""
    raw = Path(path).read_text(encoding="utf-8")
    m = _FM.match(raw)
    if not m:
        return {}, raw
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict):
        raise ValueError(f"{path}: frontmatter phải là ánh xạ khoá-giá trị, đang là "
                         f"{type(fm).__name__}")
    return fm, raw[m.end():]


def write_fm(path, fm: dict, body: str) -> None:
    """Ghi lại file. Nguyên tử: ghi .tmp rồi đổi tên."""
    txt = ("---\n"
           + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=100)
           + "---\n" + body)
    _ghi_nguyen_tu(path, txt)


def _ghi_nguyen_tu(path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, p)          # đổi tên là nguyên tử trên cùng ổ đĩa
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- bảng giữa marker

def _moc(ten: str) -> tuple[str, str]:
    return f"<!-- {ten}:BEGIN -->", f"<!-- {ten}:END -->"


def _tach_o(dong: str) -> list[str]:
    """Tách một dòng bảng thành các ô. `\\|` là dấu | thật trong nội dung, không phải vách."""
    dong = dong.strip()
    if dong.startswith("|"):
        dong = dong[1:]
    if dong.endswith("|") and not dong.endswith("\\|"):
        dong = dong[:-1]
    o, dem = [], []
    i = 0
    while i < len(dong):
        if dong[i] == "\\" and i + 1 < len(dong) and dong[i + 1] == "|":
            dem.append("|")
            i += 2
        elif dong[i] == "|":
            o.append("".join(dem).strip())
            dem = []
            i += 1
        else:
            dem.append(dong[i])
            i += 1
    o.append("".join(dem).strip())
    return o


def _o_an_toan(v) -> str:
    """Escape để một ô không phá vỡ bảng."""
    if v is None:
        return ""
    return str(v).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def read_table(body: str, ten_moc: str) -> tuple[list[str], list[dict]]:
    """Đọc bảng giữa marker. Trả về (cột, danh sách dòng dạng dict).

    Bảng rỗng (chỉ có header) -> (cột, []). Không có marker -> ([], []).
    """
    dau, cuoi = _moc(ten_moc)
    i, j = body.find(dau), body.find(cuoi)
    if i < 0 or j < 0 or j < i:
        return [], []
    khoi = [d for d in body[i + len(dau):j].splitlines() if d.strip().startswith("|")]
    if not khoi:
        return [], []
    cot = _tach_o(khoi[0])
    dong = []
    for d in khoi[1:]:
        o = _tach_o(d)
        if all(re.fullmatch(r":?-{2,}:?", x.strip()) for x in o if x.strip()):
            continue                       # dòng phân cách |---|---|
        dong.append({c: (o[k] if k < len(o) else "") for k, c in enumerate(cot)})
    return cot, dong


def render_table(cot: list[str], dong: list[dict]) -> str:
    ra = ["| " + " | ".join(cot) + " |",
          "|" + "|".join("---" for _ in cot) + "|"]
    for d in dong:
        ra.append("| " + " | ".join(_o_an_toan(d.get(c, "")) for c in cot) + " |")
    return "\n".join(ra)


def upsert_row(body: str, ten_moc: str, khoa: str, dong_moi: dict,
               cot_mac_dinh: list[str] | None = None) -> str:
    """Thêm hoặc cập nhật MỘT dòng theo `khoa`. Chỉ đụng vùng giữa marker.

    Cập nhật = trộn: khoá nào không có trong `dong_moi` thì giữ giá trị cũ. Nhờ vậy
    `register_publish` cập nhật cột `published` mà không xoá mất cột người tự điền.
    """
    dau, cuoi = _moc(ten_moc)
    i, j = body.find(dau), body.find(cuoi)
    if i < 0 or j < 0:
        raise ValueError(f"không thấy marker {dau} … {cuoi} — file sai mẫu?")
    cot, dong = read_table(body, ten_moc)
    if not cot:
        cot = cot_mac_dinh or list(dong_moi)
    if khoa not in cot:
        raise ValueError(f"bảng không có cột khoá {khoa!r}; có: {cot}")

    da_co = False
    for d in dong:
        if d.get(khoa) == dong_moi.get(khoa):
            d.update({k: v for k, v in dong_moi.items() if v is not None})
            da_co = True
            break
    if not da_co:
        dong.append({c: dong_moi.get(c, "") for c in cot})

    return body[:i + len(dau)] + "\n" + render_table(cot, dong) + "\n" + body[j:]
