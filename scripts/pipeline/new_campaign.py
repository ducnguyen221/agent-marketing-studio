# -*- coding: utf-8 -*-
"""
Dựng một chiến dịch mới từ khuôn có sẵn.

Bung `asset_pattern` của loại chiến dịch thành lịch đầy đủ, sinh brief + calendar +
workbook. Những gì chỉ người mới trả lời được thì để `<<HỎI NGƯỜI>>` — agent phải hỏi,
không được đoán.

    new_campaign.py --instance <content_root> --campaign-id DNA-C02 --type series \
                    --name "Tên" --start 2026-09-01 --owner "Duc Nguyen" [--cycles 4]
                    [--pillars A,B] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Thiếu pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / "agent" / "templates"

# format → mã dùng trong asset_id
CODE = {"long_video": "HERO", "short": "SHORT", "fb_post": "FB",
        "fb_reel": "REEL", "yt_community": "YTC", "blog": "BLOG", "newsletter": "NL"}

CAL_COLS = ["asset_id", "campaign_id", "series_id", "episode_no", "week_no",
            "parent_asset_id", "pillar_primary", "pillar_secondary", "persona_target",
            "format", "platform", "distribution_platforms", "funnel_stage",
            "funnel_goal_raw", "function_role", "title_draft", "title_variant_a",
            "title_variant_b", "hashtags", "hashtag_count", "cta_type",
            "has_commercial_cta", "approve_topic", "approve_content", "approve_final",
            "status", "owner", "approved_by", "approved_at", "tos_score", "hrs_score",
            "verification_open", "qa_passed", "blocked_reason",
            "planned_publish_date", "planned_publish_time", "timezone",
            "actual_publish_datetime", "platform_native_id", "live_url", "playlist_id",
            "recycle_source_id", "recycle_due_date", "doc_ref"]


def brand_code(brand: str) -> str:
    """ducnguyen-ai -> DNA · kpim -> KPI"""
    parts = [p for p in brand.replace("_", "-").split("-") if p]
    if len(parts) >= 3:
        return "".join(p[0] for p in parts[:3]).upper()
    if len(parts) == 2:
        return (parts[0][:2] + parts[1][0]).upper()
    return parts[0][:3].upper()


def build_rows(spec: dict, args, brand: str, pillars: list[str]) -> list[dict]:
    bc = brand_code(brand)
    start = date.fromisoformat(args.start)
    cycles = args.cycles or spec["cycles"]
    commercial = spec.get("commercial_cta_cycles", [])
    rows: list[dict] = []

    for c in range(1, cycles + 1):
        base = start + timedelta(days=(c - 1) * spec["cycle_days"])
        counter: dict[str, int] = {}
        hero_id = ""
        # hero trước để asset khác trỏ về được
        for pat in spec["asset_pattern"]:
            if pat.get("is_hero"):
                hero_id = f"{bc}-{args.campaign_id.split('-')[-1]}-C{c}-HERO"
                break
        for pat in spec["asset_pattern"]:
            fmt = pat["format"]
            code = CODE.get(fmt, fmt[:3].upper())
            if pat.get("is_hero"):
                aid = hero_id
            else:
                counter[code] = counter.get(code, 0) + 1
                aid = f"{bc}-{args.campaign_id.split('-')[-1]}-C{c}-{code}{counter[code]}"
            is_comm = commercial == "all" or c in (commercial or [])
            rows.append({
                **{k: "" for k in CAL_COLS},
                "asset_id": aid,
                "campaign_id": args.campaign_id,
                "series_id": args.series_id or "",
                "episode_no": c, "week_no": c,
                "parent_asset_id": "" if pat.get("is_hero") else hero_id,
                "pillar_primary": pillars[(c - 1) % len(pillars)] if pillars else "",
                "format": fmt,
                "platform": pat["platform"],
                "distribution_platforms": pat.get("distribution_platforms", pat["platform"]),
                "funnel_stage": pat["funnel_stage"],
                "function_role": pat["function_role"],
                "cta_type": pat.get("cta_type", ""),
                "has_commercial_cta": "TRUE" if is_comm else "FALSE",
                "status": "idea",
                "owner": args.owner,
                "verification_open": 0,
                "qa_passed": "FALSE",
                "planned_publish_date": (base + timedelta(days=pat["offset_days"])).isoformat(),
                "timezone": "Asia/Ho_Chi_Minh",
                "doc_ref": f"campaign-types.yml:{args.type}",
            })
    return rows


def render_brief(spec: dict, args, brand: str, pillars: list[str], end: date) -> str:
    tpl = (TPL / "brief.template.yml").read_text(encoding="utf-8")
    comm = spec.get("commercial_cta_cycles", [])
    repl = {
        "CAMPAIGN_ID": args.campaign_id, "CAMPAIGN_NAME": args.name, "BRAND": brand,
        "TYPE": args.type, "SERIES_ID": args.series_id or "",
        "START_DATE": args.start, "END_DATE": end.isoformat(),
        "CHANNELS": str(sorted({p["platform"] for p in spec["asset_pattern"]})),
        "PILLARS": str(pillars),
        "PRIMARY_KPI": spec["default_primary_kpi"],
        "SECONDARY_KPI": spec["default_secondary_kpi"],
        "GUARDRAIL_KPI": spec["default_guardrail_kpi"],
        "COMMERCIAL_CTA_EPISODES": "all" if comm == "all" else str(comm or []),
        "OWNER": args.owner, "CREATED": date.today().isoformat(),
    }
    for k, v in repl.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    return tpl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True, help="content_root của kênh")
    ap.add_argument("--campaign-id", required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--cycles", type=int)
    ap.add_argument("--series-id")
    ap.add_argument("--pillars", default="", help="danh sách pillar_code, phân cách dấu phẩy")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    types = yaml.safe_load((TPL / "campaign-types.yml").read_text(encoding="utf-8"))["types"]
    if args.type not in types:
        print(f"Loại '{args.type}' không có. Chọn: {', '.join(types)}", file=sys.stderr)
        return 2
    spec = types[args.type]

    inst_dir = Path(args.instance)
    inst_file = inst_dir / "instance.yml"
    brand = args.campaign_id.split("-")[0].lower()
    if inst_file.exists():
        brand = (yaml.safe_load(inst_file.read_text(encoding="utf-8")) or {}).get("name", brand)

    pillars = [p.strip() for p in args.pillars.split(",") if p.strip()]
    if not pillars:
        pf = inst_dir / "01_brand" / "pillars.csv"
        if pf.exists():
            with open(pf, encoding="utf-8-sig", newline="") as f:
                pillars = [r["pillar_code"] for r in csv.DictReader(f)]

    cycles = args.cycles or spec["cycles"]
    end = date.fromisoformat(args.start) + timedelta(days=cycles * spec["cycle_days"] - 1)
    rows = build_rows(spec, args, brand, pillars)

    cdir = inst_dir / "02_campaigns" / args.campaign_id
    print(f"── {args.campaign_id} · {spec['name']} · {cycles} chu kỳ · {len(rows)} asset")
    print(f"   {args.start} → {end.isoformat()} · pillar: {pillars or '(chưa có)'}")
    print(f"   KPI: {spec['default_primary_kpi']} (chính) · {spec['default_secondary_kpi']} (phụ)")
    if args.dry_run:
        for r in rows[:10]:
            print(f"      {r['asset_id']:<22} {r['planned_publish_date']} "
                  f"{r['format']:<12} {r['function_role']}")
        if len(rows) > 10:
            print(f"      … còn {len(rows) - 10} asset")
        print("   (dry-run — chưa ghi gì)")
        return 0

    (cdir / "drafts").mkdir(parents=True, exist_ok=True)
    cal = cdir / "calendar.csv"
    with open(cal, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAL_COLS)
        w.writeheader()
        w.writerows(rows)
    brief = cdir / "brief.yml"
    brief.write_text(render_brief(spec, args, brand, pillars, end), encoding="utf-8")

    wb = cdir / f"{args.campaign_id}.xlsx"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "workbook" / "build_workbook.py"),
                    "--campaign-id", args.campaign_id, "--out", str(wb),
                    "--brief", str(brief), "--calendar", str(cal)], check=True)

    print(f"\n   Bước tiếp theo — agent PHẢI hỏi người trước khi điền:")
    print(f"      1. Mở {brief.name}, thay mọi <<HỎI NGƯỜI>> (big_idea, objective, persona…)")
    print(f"      2. Chạy stage 'topics' để đề xuất tiêu đề + chấm TOS/HRS")
    print(f"      3. Người tick approve_topic trong {wb.name} thì mới viết được nội dung")
    return 0


if __name__ == "__main__":
    sys.exit(main())
