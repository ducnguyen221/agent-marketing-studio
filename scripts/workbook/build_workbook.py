# -*- coding: utf-8 -*-
"""
Dựng workbook end-to-end của một chiến dịch từ schema/workbook_spec.yml.

Cột, kiểu và enum lấy ngược từ schema/model.yml + schema/enums.yml nên workbook
luôn khớp star schema — sửa schema là chạy lại script, không sửa Excel bằng tay.

    python build_workbook.py --campaign-id DNA-C01 --out <file.xlsx>
                             [--brief brief.yml] [--calendar calendar.csv]
                             [--kpi-target kpi_target.csv] [--metrics metrics.csv]
                             [--leads leads.csv]

Ô nền VÀNG ở hàng tiêu đề = cột của người, script không bao giờ ghi đè.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

try:
    import yaml
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError as e:
    print(f"Thiếu thư viện: {e}. Cần: pip install pyyaml openpyxl", file=sys.stderr)
    sys.exit(2)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
OWNER_MARK = {"agent": "🤖", "human": "👤", "script": "⚙️"}


def load(name: str) -> dict:
    with open(SCHEMA_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def enum_values(enums: dict, name: str) -> list[str]:
    node = enums.get(name) or {}
    vals = node.get("values", [])
    return list(vals.keys()) if isinstance(vals, dict) else list(vals)


def read_csv(path: str | None, campaign_id: str | None = None) -> list[dict]:
    """Đọc CSV; nếu file gộp nhiều chiến dịch thì lọc về đúng chiến dịch đang dựng."""
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        print(f"  ⚠ không thấy {p} — để trống sheet")
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if campaign_id and rows and "campaign_id" in rows[0]:
        kept = [r for r in rows if r.get("campaign_id") == campaign_id]
        if len(kept) != len(rows):
            print(f"  ℹ {p.name}: lọc {len(kept)}/{len(rows)} dòng theo campaign_id={campaign_id}")
        return kept
    return rows


class Builder:
    def __init__(self, spec: dict, model: dict, enums: dict, campaign_id: str):
        self.spec, self.model, self.enums = spec, model, enums
        self.campaign_id = campaign_id
        self.conv = spec["conventions"]
        self.fills = {k: PatternFill("solid", fgColor=v)
                      for k, v in self.conv["owner_fill"].items()}
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.dict_rows: list[list[str]] = []
        self.used_enums: dict[str, list[str]] = {}

    # ── phân giải cột ─────────────────────────────────────────────────────
    def resolve(self, sheet: dict) -> list[tuple[str, dict, str]]:
        """-> [(tên cột, spec cột, owner)]"""
        out: list[tuple[str, dict, str]] = []
        default_owner = sheet.get("owner", "agent")
        overrides = sheet.get("owner_overrides", {})
        table = sheet.get("from_table")
        tcols = self.model["tables"].get(table, {}).get("columns", {}) if table else {}

        names: list[str] = []
        if "column_groups" in sheet:
            for cols in sheet["column_groups"].values():
                names.extend(cols)
        elif sheet.get("columns") == "all":
            names = list(tcols.keys())
        elif isinstance(sheet.get("columns"), list):
            names = list(sheet["columns"])

        for n in names:
            cspec = dict(tcols.get(n, {}))
            out.append((n, cspec, overrides.get(n, cspec.get("owner", default_owner))))
        for n, cspec in (sheet.get("extra_columns") or {}).items():
            cspec = dict(cspec)
            out.append((n, cspec, overrides.get(n, cspec.get("owner", default_owner))))
        return out

    def validation_for(self, cspec: dict) -> str | None:
        """Tên danh sách enum cho cột này, đã ghi nhận để dựng sheet _Lists."""
        if cspec.get("type") == "bool":
            self.used_enums["bool"] = ["TRUE", "FALSE"]
            return "bool"
        name = cspec.get("enum")
        if name:
            vals = enum_values(self.enums, name)
            if vals:
                self.used_enums[name] = vals
                return name
        if cspec.get("type") == "enum" and isinstance(cspec.get("values"), list):
            key = "inline_" + "_".join(str(v) for v in cspec["values"])[:24]
            self.used_enums[key] = [str(v) for v in cspec["values"]]
            return key
        return None

    # ── dựng sheet ────────────────────────────────────────────────────────
    def build_table_sheet(self, sheet: dict, rows: list[dict]) -> None:
        ws = self.wb.create_sheet(sheet["name"])
        cols = self.resolve(sheet)
        for i, (name, cspec, owner) in enumerate(cols, start=1):
            c = ws.cell(row=1, column=i, value=f"{OWNER_MARK.get(owner,'')} {name}".strip())
            c.font = Font(bold=True, size=10)
            c.fill = self.fills.get(owner, self.fills["agent"])
            c.alignment = Alignment(vertical="center", wrap_text=True)
            note = cspec.get("note")
            if note:
                c.comment = None  # chú thích đầy đủ nằm ở _Dictionary, tránh workbook nặng
            width = cspec.get("width", 16)
            if cspec.get("type") == "text":
                width = max(width, 50)
            ws.column_dimensions[get_column_letter(i)].width = width

            vname = self.validation_for(cspec)
            if vname:
                ref = f"'_Lists'!${self._list_col(vname)}$2:${self._list_col(vname)}$200"
                dv = DataValidation(type="list", formula1=ref, allow_blank=True,
                                    showErrorMessage=True,
                                    error=f"Giá trị phải nằm trong danh sách {vname}",
                                    errorTitle="Ngoài enum")
                ws.add_data_validation(dv)
                dv.add(f"{get_column_letter(i)}2:{get_column_letter(i)}2000")

            self.dict_rows.append([
                sheet["name"], name, str(cspec.get("type", "")),
                str(cspec.get("enum") or (",".join(map(str, cspec["values"]))
                                          if isinstance(cspec.get("values"), list) else "")),
                "có" if cspec.get("required") else "", owner, str(note or ""),
            ])

        for r, row in enumerate(rows, start=2):
            for i, (name, _cspec, _o) in enumerate(cols, start=1):
                ws.cell(row=r, column=i, value=row.get(name, ""))

        ws.freeze_panes = self.conv.get("freeze", "A2")
        if cols:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(len(rows) + 1, 2)}"
        ws.row_dimensions[1].height = 30

    def build_vertical_sheet(self, sheet: dict, values: dict) -> None:
        ws = self.wb.create_sheet(sheet["name"])
        for i, h in enumerate(["Trường", "Giá trị", "Ghi chú", "Ai ghi"], start=1):
            c = ws.cell(row=1, column=i, value=h)
            c.font = Font(bold=True, size=10)
            c.fill = self.fills["agent"]
        tcols = self.model["tables"].get(sheet.get("source"), {}).get("columns", {})
        for r, entry in enumerate(sheet["fields"], start=2):
            field, owner = entry
            ws.cell(row=r, column=1, value=field).font = Font(bold=True, size=10)
            ws.cell(row=r, column=2, value=values.get(field, ""))
            ws.cell(row=r, column=3, value=str(tcols.get(field, {}).get("note", "")))
            ws.cell(row=r, column=4, value=f"{OWNER_MARK.get(owner,'')} {owner}")
            ws.cell(row=r, column=2).fill = self.fills.get(owner, self.fills["agent"])
            self.dict_rows.append([sheet["name"], field, "", "", "", owner,
                                   str(tcols.get(field, {}).get("note", ""))])
        for col, w in (("A", 32), ("B", 70), ("C", 46), ("D", 12)):
            ws.column_dimensions[col].width = w
        ws.column_dimensions["B"].width = 70
        for r in range(2, len(sheet["fields"]) + 2):
            ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"

    def build_readme(self, sheet: dict) -> None:
        ws = self.wb.create_sheet(sheet["name"], 0)
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 100
        lines = [
            ("Chiến dịch", self.campaign_id),
            ("Schema version", str(self.spec.get("version"))),
            ("Dựng bởi", "marketing-agent · scripts/workbook/build_workbook.py"),
            ("", ""),
            ("LUẬT VÀNG", "Ô nền VÀNG ở hàng tiêu đề là cột của bạn — agent không bao giờ ghi đè."),
            ("", "Ô nền XANH LÁ do script sinh — sửa tay sẽ bị ghi đè lần chạy sau."),
            ("", "Ô nền XANH DƯƠNG do agent sinh — bạn sửa thoải mái."),
            ("", ""),
            ("Ô rỗng nghĩa là gì", self.conv.get("na_policy", "").strip()),
            ("", ""),
        ]
        for s in self.spec["sheets"]:
            if s["name"].startswith("_") or s.get("kind") == "doc":
                continue
            lines.append((s["name"], f"{s.get('grain','')} — {s.get('purpose','') or s.get('note','')}".strip(" —")))
        lines += [("", ""), ("Làm mới workbook", "python scripts/workbook/build_workbook.py --campaign-id <ID> --out <file>")]
        for r, (a, b) in enumerate(lines, start=1):
            ws.cell(row=r, column=1, value=a).font = Font(bold=True, size=10)
            c = ws.cell(row=r, column=2, value=b)
            c.alignment = Alignment(wrap_text=True, vertical="top")

    def build_lists(self) -> None:
        ws = self.wb["_Lists"]
        for i, (name, vals) in enumerate(sorted(self.used_enums.items()), start=1):
            col = get_column_letter(i)
            ws.cell(row=1, column=i, value=name).font = Font(bold=True, size=10)
            ws.column_dimensions[col].width = max(len(name) + 2, 18)
            for r, v in enumerate(vals, start=2):
                ws.cell(row=r, column=i, value=v)
        ws.freeze_panes = "A2"

    def _list_col(self, enum_name: str) -> str:
        return get_column_letter(sorted(self.used_enums).index(enum_name) + 1)

    def build_dictionary(self) -> None:
        ws = self.wb["_Dictionary"]
        for i, h in enumerate(["sheet", "column", "type", "enum", "bắt buộc", "ai ghi", "ý nghĩa"], start=1):
            c = ws.cell(row=1, column=i, value=h)
            c.font = Font(bold=True, size=10)
            c.fill = self.fills["script"]
        for r, row in enumerate(self.dict_rows, start=2):
            for i, v in enumerate(row, start=1):
                ws.cell(row=r, column=i, value=v)
        for col, w in zip("ABCDEFG", (18, 26, 12, 26, 10, 10, 80)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:G{max(len(self.dict_rows) + 1, 2)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--brief")
    ap.add_argument("--calendar")
    ap.add_argument("--kpi-target")
    ap.add_argument("--metrics")
    ap.add_argument("--leads")
    ap.add_argument("--content")
    args = ap.parse_args()

    spec, model, enums = load("workbook_spec.yml"), load("model.yml"), load("enums.yml")
    b = Builder(spec, model, enums, args.campaign_id)

    brief_values: dict = {}
    if args.brief and Path(args.brief).exists():
        with open(args.brief, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        wr = raw.pop("winner_rule", {}) or {}
        cs = raw.pop("constraints", {}) or {}
        brief_values = {k: (", ".join(map(str, v)) if isinstance(v, list) else v)
                        for k, v in raw.items() if not isinstance(v, dict)}
        brief_values.update({
            "winner_rule_min_kpi_count": wr.get("min_kpi_count", ""),
            "winner_rule_baseline_source": wr.get("baseline_source", ""),
            "winner_rule_baseline_ready": wr.get("baseline_ready", ""),
            "commercial_cta_episodes": ", ".join(map(str, cs.get("commercial_cta_episodes", []))),
            "forbidden_terms": cs.get("forbidden_terms_note", ""),
            "hashtag_limits": cs.get("hashtag_limits", ""),
        })
    brief_values.setdefault("campaign_id", args.campaign_id)

    cid = args.campaign_id
    data = {
        "02_KPI_Target": read_csv(args.kpi_target, cid),
        "03_Calendar": read_csv(args.calendar, cid),
        "04_Content": read_csv(args.content, cid),
        "07_Metrics_Daily": read_csv(args.metrics, cid),
        "09_Leads": read_csv(args.leads, cid),
    }

    # _Lists và _Dictionary phải tồn tại trước để data-validation trỏ tới được
    b.wb.create_sheet("_Lists")
    b.wb.create_sheet("_Dictionary")

    for sheet in spec["sheets"]:
        name = sheet["name"]
        if name.startswith("_"):
            continue
        if sheet.get("kind") == "doc":
            b.build_readme(sheet)
        elif sheet.get("orientation") == "vertical":
            b.build_vertical_sheet(sheet, brief_values)
        else:
            b.build_table_sheet(sheet, data.get(name, []))

    b.build_lists()
    b.build_dictionary()
    b.wb.move_sheet("_Lists", offset=len(b.wb.sheetnames))
    b.wb.move_sheet("_Dictionary", offset=len(b.wb.sheetnames))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    b.wb.save(out)

    print(f"✅ {out}")
    print(f"   {len(b.wb.sheetnames)} sheet: {', '.join(b.wb.sheetnames)}")
    for k, v in data.items():
        if v:
            print(f"   {k}: {len(v)} dòng")
    print(f"   _Dictionary: {len(b.dict_rows)} cột · _Lists: {len(b.used_enums)} danh sách enum")
    return 0


if __name__ == "__main__":
    sys.exit(main())
