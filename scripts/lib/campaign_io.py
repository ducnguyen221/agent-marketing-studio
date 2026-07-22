# -*- coding: utf-8 -*-
"""
Đọc dữ liệu chiến dịch — workbook là nguồn sự thật.

Một chiến dịch = một file `.xlsx`. Mọi script dùng chung bộ đọc này nên không còn cảnh
mỗi script tự mở CSV riêng rồi lệch nhau.

Vẫn nhận `.csv` / `.yml` để nhập dữ liệu cũ hoặc seed lần đầu, nhưng đó là đường phụ.
"""
from __future__ import annotations

from pathlib import Path

MARKS = ("🤖", "👤", "⚙️", "⚙")


def _clean(name) -> str:
    s = str(name or "")
    for m in MARKS:
        s = s.replace(m, "")
    return s.strip()


def read_sheet(workbook: str | Path, sheet: str) -> list[dict]:
    """Đọc một sheet thành list[dict]. Bỏ dòng không có giá trị ở cột đầu."""
    from openpyxl import load_workbook
    wb = load_workbook(workbook, read_only=True, data_only=True)
    try:
        if sheet not in wb.sheetnames:
            return []
        it = wb[sheet].iter_rows(values_only=True)
        try:
            hdr = [_clean(h) for h in next(it)]
        except StopIteration:
            return []
        rows = []
        for row in it:
            if not row or row[0] in (None, ""):
                continue
            rows.append({h: ("" if v is None else v) for h, v in zip(hdr, row) if h})
        return rows
    finally:
        wb.close()


def _read_csv(path: Path) -> list[dict]:
    import csv
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_calendar(source: str | Path) -> list[dict]:
    """Lịch nội dung từ workbook (sheet 03_Calendar) hoặc từ calendar.csv."""
    p = Path(source)
    if p.suffix.lower() == ".xlsx":
        return read_sheet(p, "03_Calendar")
    if p.is_dir():                       # đưa thư mục chiến dịch cũng được
        wb = next(p.glob("*.xlsx"), None)
        if wb:
            return read_sheet(wb, "03_Calendar")
        p = p / "calendar.csv"
    return _read_csv(p) if p.exists() else []


def load_brief(source: str | Path) -> dict:
    """Brief từ workbook (sheet 01_Brief, bố cục dọc) hoặc từ brief.yml."""
    p = Path(source)
    if p.is_dir():
        wb = next(p.glob("*.xlsx"), None)
        p = wb if wb else (p / "brief.yml")
    if p.suffix.lower() == ".xlsx":
        out: dict = {}
        for r in read_sheet(p, "01_Brief"):
            # sheet dọc: cột 1 = tên trường, cột 2 = giá trị
            keys = list(r.keys())
            if len(keys) < 2:
                continue
            k, v = str(r[keys[0]]).strip(), r[keys[1]]
            if k:
                out[k] = v
        # dựng lại các khối lồng nhau mà 01_Brief làm phẳng
        wr = {kk.replace("winner_rule_", ""): vv
              for kk, vv in out.items() if kk.startswith("winner_rule_")}
        if wr:
            out["winner_rule"] = wr
        if "commercial_cta_episodes" in out:
            raw = str(out["commercial_cta_episodes"])
            out["constraints"] = {"commercial_cta_episodes":
                                  [x.strip() for x in raw.replace("[", "").replace("]", "")
                                   .split(",") if x.strip()]}
        return out
    if p.exists():
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {}


def find_workbook(campaign_dir: str | Path) -> Path | None:
    """File .xlsx duy nhất của chiến dịch. Nhiều hơn một là sai quy ước — báo lỗi."""
    d = Path(campaign_dir)
    hits = [f for f in d.glob("*.xlsx") if not f.name.startswith("~$")]
    if len(hits) > 1:
        raise RuntimeError(
            f"{d.name} có {len(hits)} file .xlsx: {', '.join(h.name for h in hits)}. "
            f"Một chiến dịch chỉ được có MỘT file quản lý.")
    return hits[0] if hits else None
