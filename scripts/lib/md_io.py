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
    write_atomic(path, txt)


# Trên Windows, đổi tên đè lên một file VỪA ghi xong có lúc bị từ chối (WinError 5) vì
# trình quét virus hoặc bộ lập chỉ mục đang mở nó trong khoảnh khắc. Đo được 14/09/2026:
# ghi file trạng thái Facebook hai lần liền nhau thì lần hai hỏng. Hỏng đúng lúc đó là tệ
# nhất — bài và comment đã lên, còn sổ không biết comment đã có, nên lượt sau comment lần
# nữa. Thử lại ngắn là cách Windows cần; quá trần thì vẫn ném lỗi, không nuốt.
_REPLACE_TRIES = 20
_REPLACE_WAIT = 0.05
# Buộc tên lúc import: test hay vá `time.sleep` thành hàm rỗng, và thử lại tức thì thì
# chính cái chờ này mất tác dụng.
_SLEEP = __import__("time").sleep


def _replace_retry(src, dst, *, tries: int = _REPLACE_TRIES, wait: float = _REPLACE_WAIT,
                   _sleep=None) -> None:
    _sleep = _sleep or _SLEEP
    for lan in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if lan == tries - 1:
                raise
            _sleep(wait)


def write_atomic(path, text: str) -> None:
    """Ghi một file bất kỳ, nguyên tử. Công khai vì build_views cũng cần:
    trang HTML ghi dở dang mà người vừa bấm mở là trang trắng."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        _replace_retry(tmp, p)      # đổi tên là nguyên tử trên cùng ổ đĩa
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- bảng giữa marker

def _moc(name: str) -> tuple[str, str]:
    return f"<!-- {name}:BEGIN -->", f"<!-- {name}:END -->"


def _tach_o(row: str) -> list[str]:
    """Tách một dòng bảng thành các ô. `\\|` là dấu | thật trong nội dung, không phải vách."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    o, count = [], []
    i = 0
    while i < len(row):
        if row[i] == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            count.append("|")
            i += 2
        elif row[i] == "|":
            o.append("".join(count).strip())
            count = []
            i += 1
        else:
            count.append(row[i])
            i += 1
    o.append("".join(count).strip())
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
    start, cuoi = _moc(ten_moc)
    i, j = body.find(start), body.find(cuoi)
    if i < 0 or j < 0 or j < i:
        return [], []
    khoi = [d for d in body[i + len(start):j].splitlines() if d.strip().startswith("|")]
    if not khoi:
        return [], []
    col = _tach_o(khoi[0])
    row = []
    for d in khoi[1:]:
        o = _tach_o(d)
        if all(re.fullmatch(r":?-{2,}:?", x.strip()) for x in o if x.strip()):
            continue                       # dòng phân cách |---|---|
        row.append({c: (o[k] if k < len(o) else "") for k, c in enumerate(col)})
    return col, row


def render_table(col: list[str], row: list[dict]) -> str:
    ra = ["| " + " | ".join(col) + " |",
          "|" + "|".join("---" for _ in col) + "|"]
    for d in row:
        ra.append("| " + " | ".join(_o_an_toan(d.get(c, "")) for c in col) + " |")
    return "\n".join(ra)


def upsert_row(body: str, ten_moc: str, khoa: str, dong_moi: dict,
               cot_mac_dinh: list[str] | None = None, them_cot: bool = False,
               chi_cap_nhat: bool = False) -> str:
    """Thêm hoặc cập nhật MỘT dòng theo `khoa`. Chỉ đụng vùng giữa marker.

    Cập nhật = trộn: khoá nào không có trong `dong_moi` thì giữ giá trị cũ. Nhờ vậy
    `register_publish` cập nhật cột `published` mà không xoá mất cột người tự điền.

    `chi_cap_nhat=True`: dòng không tồn tại thì NÉM LỖI thay vì thêm mới. Dùng cho các
    chỗ *soi gương* (register_publish ghi ngược g2/URL): ở đó `content_id` lạ nghĩa là
    `meta.json` sai, và thêm một dòng rỗng vào sổ chỉ giấu cái sai đó đi.

    Khoá KHÔNG có trong bảng: mặc định NÉM LỖI. Trước đây nó bị bỏ im lặng — người gọi
    tưởng đã ghi, giá trị bốc hơi, và không gì báo. `them_cot=True` để cố ý mở thêm cột
    (bảng cũ chưa có cột web/youtube/facebook thì register_publish tự nới ra).
    """
    start, cuoi = _moc(ten_moc)
    i, j = body.find(start), body.find(cuoi)
    if i < 0 or j < 0:
        raise ValueError(f"không thấy marker {start} … {cuoi} — file sai mẫu?")
    col, row = read_table(body, ten_moc)
    if not col:
        col = cot_mac_dinh or list(dong_moi)
    if khoa not in col:
        raise ValueError(f"bảng không có cột khoá {khoa!r}; có: {col}")

    la = [k for k in dong_moi if k not in col]
    if la:
        if not them_cot:
            raise ValueError(f"bảng {ten_moc} không có cột {la} — ghi vào sẽ mất im lặng. "
                             f"Cột đang có: {col}. Cố ý nới bảng thì truyền them_cot=True.")
        col = col + la
        for d in row:
            for k in la:
                d.setdefault(k, "")

    da_co = False
    for d in row:
        if d.get(khoa) == dong_moi.get(khoa):
            d.update({k: v for k, v in dong_moi.items() if v is not None})
            da_co = True
            break
    if not da_co:
        if chi_cap_nhat:
            raise KeyError(f"bảng {ten_moc} không có dòng {khoa}={dong_moi.get(khoa)!r} — "
                           f"không thêm dòng mới ở chế độ chỉ-cập-nhật. "
                           f"Kiểm lại meta.json/publish.json của bài.")
        row.append({c: dong_moi.get(c, "") for c in col})

    return body[:i + len(start)] + "\n" + render_table(col, row) + "\n" + body[j:]
