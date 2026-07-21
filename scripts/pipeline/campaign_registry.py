# -*- coding: utf-8 -*-
"""
Sổ chiến dịch — liệt kê mọi chiến dịch của một kênh, ở hai dạng.

  CAMPAIGNS.md   người đọc: đang chạy cái gì, tới đâu, kết quả sao
  campaigns.xlsx máy đọc: lịch sử đầy đủ để lọc, sắp xếp, nối vào dashboard

Quét thẳng `02_campaigns/*/brief.yml` + `calendar.csv` + workbook nên KHÔNG bao giờ
lệch với thực tế — không có sổ chép tay để quên cập nhật.

    campaign_registry.py --instance <content_root> [--md] [--xlsx]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Thiếu pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

COLS = ["campaign_id", "campaign_name", "campaign_type", "status", "automation_mode",
        "start_date", "end_date", "days_left", "owner",
        "assets_total", "assets_published", "assets_measured",
        "gate_topic", "gate_content", "gate_final",
        "primary_kpi", "pillars", "channels", "folder"]


def read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_true(v) -> bool:
    return str(v or "").strip().lower() in {"x", "true", "1", "yes", "y", "có", "✓", "v"}


def scan(inst: Path) -> list[dict]:
    rows = []
    cdir = inst / "02_campaigns"
    if not cdir.exists():
        return rows
    today = date.today()
    for d in sorted(p for p in cdir.iterdir() if p.is_dir()):
        brief_f = d / "brief.yml"
        b = {}
        if brief_f.exists():
            try:
                b = yaml.safe_load(brief_f.read_text(encoding="utf-8")) or {}
            except Exception as e:
                print(f"   ⚠ {d.name}/brief.yml không đọc được: {e}")
        # Cổng duyệt được tick TRONG WORKBOOK, không phải trong calendar.csv.
        # Đọc CSV cho tiện thì số cổng luôn bằng 0 — một con số sai còn tệ hơn không có.
        cal = read_csv(d / "calendar.csv")
        wbf = d / f"{d.name}.xlsx"
        source = "csv"
        if wbf.exists():
            try:
                from openpyxl import load_workbook
                wb = load_workbook(wbf, read_only=True, data_only=True)
                if "03_Calendar" in wb.sheetnames:
                    ws = wb["03_Calendar"]
                    it = ws.iter_rows(values_only=True)
                    hdr = [str(h or "").strip() for h in next(it)]
                    cal = [dict(zip(hdr, row)) for row in it if row and row[0]]
                    source = "workbook"
                wb.close()
            except Exception as e:
                print(f"   ⚠ {d.name}: không đọc được workbook ({e}) — dùng calendar.csv")
        st = Counter(str(r.get("status") or "?").strip() for r in cal)
        end = b.get("end_date")
        left = ""
        if end:
            try:
                left = (date.fromisoformat(str(end)) - today).days
            except ValueError:
                left = ""
        auto = (b.get("automation") or {}).get("mode", "hitl")
        rows.append({
            "campaign_id": b.get("campaign_id") or d.name,
            "campaign_name": b.get("campaign_name", ""),
            "campaign_type": b.get("campaign_type", ""),
            "status": b.get("status", ""),
            "automation_mode": auto,
            "start_date": b.get("start_date", ""), "end_date": end or "",
            "days_left": left,
            "owner": b.get("owner", ""),
            "assets_total": len(cal),
            "assets_published": st.get("published", 0) + st.get("measured", 0),
            "assets_measured": st.get("measured", 0),
            "gate_topic": sum(1 for r in cal if is_true(r.get("approve_topic"))),
            "gate_content": sum(1 for r in cal if is_true(r.get("approve_content"))),
            "gate_final": sum(1 for r in cal if is_true(r.get("approve_final"))),
            "primary_kpi": b.get("primary_kpi_label") or b.get("primary_kpi", ""),
            "pillars": ", ".join(map(str, b.get("pillars") or [])),
            "channels": ", ".join(map(str, b.get("channels") or [])),
            "folder": d.name,
        })
    return rows


def write_md(rows: list[dict], out: Path, inst_name: str) -> None:
    running = [r for r in rows if r["status"] in ("running", "active")]
    lines = [
        f"# Sổ chiến dịch — {inst_name}", "",
        f"> Sinh tự động bởi `campaign_registry.py` · cập nhật {date.today().isoformat()}",
        "> Đừng sửa tay file này — sửa `brief.yml` của chiến dịch rồi chạy lại.", "",
        f"**{len(rows)} chiến dịch** · {sum(r['assets_total'] for r in rows)} asset · "
        f"{sum(r['assets_published'] for r in rows)} đã đăng", "",
        "## Đang chạy", "",
    ]
    if running:
        lines += ["| Chiến dịch | Loại | Còn (ngày) | Asset | Đã đăng | Cổng duyệt (T/C/F) | Tự động |",
                  "|---|---|---:|---:|---:|---|---|"]
        for r in running:
            lines.append(f"| **{r['campaign_id']}** — {r['campaign_name']} | {r['campaign_type']} "
                         f"| {r['days_left']} | {r['assets_total']} | {r['assets_published']} "
                         f"| {r['gate_topic']}/{r['gate_content']}/{r['gate_final']} "
                         f"| `{r['automation_mode']}` |")
    else:
        lines.append("*Chưa có chiến dịch nào ở trạng thái `running`.*")

    lines += ["", "## Toàn bộ lịch sử", "",
              "| Chiến dịch | Tên | Loại | Thời gian | Trạng thái | Asset | Đã đăng | KPI chính |",
              "|---|---|---|---|---|---:|---:|---|"]
    for r in sorted(rows, key=lambda x: str(x["start_date"]), reverse=True):
        lines.append(f"| `{r['campaign_id']}` | {r['campaign_name']} | {r['campaign_type']} "
                     f"| {r['start_date']} → {r['end_date']} | {r['status']} "
                     f"| {r['assets_total']} | {r['assets_published']} | {r['primary_kpi']} |")

    lines += ["", "## Cách đọc", "",
              "- **Cổng duyệt (T/C/F)** = số asset đã tick `approve_topic` / `approve_content` "
              "/ `approve_final`. Chênh lệch lớn giữa T và C nghĩa là nội dung đang tắc ở khâu viết.",
              "- **Tự động**: `hitl` người duyệt từng bài · `batch` duyệt cả loạt theo điều kiện "
              "· `auto` máy tự tick khi thoả điều kiện trong `brief.automation.auto_if`.",
              "- Mỗi chiến dịch có thư mục riêng trong `02_campaigns/`, chứa cả nội dung và asset.", ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--xlsx", action="store_true")
    args = ap.parse_args()
    if not (args.md or args.xlsx):
        args.md = args.xlsx = True

    inst = Path(args.instance)
    rows = scan(inst)
    if not rows:
        print(f"Không thấy chiến dịch nào trong {inst / '02_campaigns'}", file=sys.stderr)
        return 1

    print(f"── sổ chiến dịch · {inst.name} · {len(rows)} chiến dịch")
    for r in rows:
        print(f"   {r['campaign_id']:<16} {r['status']:<10} {r['assets_total']:>3} asset "
              f"· cổng {r['gate_topic']}/{r['gate_content']}/{r['gate_final']} "
              f"· {r['automation_mode']}")

    if args.md:
        f = inst / "CAMPAIGNS.md"
        write_md(rows, f, inst.name)
        print(f"   ✅ {f}")
    if args.xlsx:
        f = inst / "campaigns.csv"
        with open(f, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            w.writerows(rows)
        print(f"   ✅ {f}")
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
            wb = Workbook()
            ws = wb.active
            ws.title = "Campaigns"
            for i, c in enumerate(COLS, start=1):
                cell = ws.cell(1, i, c)
                cell.font = Font(bold=True, size=10)
                cell.fill = PatternFill("solid", fgColor="E2EFDA")
                ws.column_dimensions[cell.column_letter].width = max(len(c) + 2, 14)
            for j, r in enumerate(rows, start=2):
                for i, c in enumerate(COLS, start=1):
                    ws.cell(j, i, r.get(c, ""))
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = f"A1:{ws.cell(1, len(COLS)).column_letter}{len(rows) + 1}"
            x = inst / "campaigns.xlsx"
            wb.save(x)
            print(f"   ✅ {x}")
        except ImportError:
            print("   ⚠ thiếu openpyxl — chỉ ra CSV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
