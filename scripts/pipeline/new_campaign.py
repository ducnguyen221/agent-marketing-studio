#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo MỘT chiến dịch mới trong một kênh: campaign.md + dòng trong CAMPAIGNS.md.

Chiến dịch chỉ có một bài lẻ vẫn là một chiến dịch — vẫn có thư mục, vẫn có dòng trong sổ.
Không có "bài mồ côi ngoài chiến dịch": thứ không nằm trong sổ thì sáu tháng sau không ai
biết nó từng tồn tại, và bài sau không nối mạch được với nó.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TPL = REPO / "templates"
MA = re.compile(r"^CMP-\d{4}-[a-z0-9-]+$")

COT = ["campaign_id", "tên", "pillar", "status", "bắt đầu", "kết thúc", "bài", "đã đăng", "thư mục"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tạo chiến dịch mới trong một kênh.")
    ap.add_argument("--channel", required=True, help="id kênh (phải có trong CHANNELS.md)")
    ap.add_argument("--id", required=True, help="CMP-YYMM-slug")
    ap.add_argument("--name", required=True)
    ap.add_argument("--prefix", required=True, help="tiền tố content_id, vd AST")
    ap.add_argument("--pillar", default="")
    ap.add_argument("--start", default="")
    ap.add_argument("--end", default="")
    ap.add_argument("--station", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not MA.match(a.id):
        sys.stderr.write(f"--id phải dạng CMP-YYMM-slug (chữ thường): {a.id!r}\n")
        return 2
    if not re.fullmatch(r"[A-Z]{2,5}", a.prefix):
        sys.stderr.write(f"--prefix phải 2-5 chữ HOA: {a.prefix!r}\n")
        return 2

    try:
        kenh = SP.channel_dir(a.channel, a.station)
    except KeyError as e:
        sys.stderr.write(f"{e}\n")
        return 2
    if not (kenh / "channel.yml").is_file():
        sys.stderr.write(f"{kenh} không phải thư mục kênh (thiếu channel.yml)\n")
        return 2

    # pillar phải nằm trong bộ của kênh — bắt sớm còn hơn để check_tree bắt muộn
    import yaml
    cfg = yaml.safe_load((kenh / "channel.yml").read_text(encoding="utf-8")) or {}
    pillars = cfg.get("pillars") or []
    if a.pillar and pillars and a.pillar not in pillars:
        sys.stderr.write(f"--pillar {a.pillar!r} không có trong channel.yml:pillars {pillars}\n")
        return 2

    dich = kenh / a.id
    if (dich / "campaign.md").exists():
        sys.stderr.write(f"đã có chiến dịch ở {dich} — dừng, không ghi đè\n")
        return 2
    if a.dry_run:
        print(f"  [dry-run] sẽ tạo {dich}/campaign.md và thêm dòng vào {kenh / 'CAMPAIGNS.md'}")
        return 0

    dich.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TPL / "campaign.md", dich / "campaign.md")
    fm, body = md_io.read_fm(dich / "campaign.md")
    fm.update({"id": a.id, "channel": a.channel, "id_prefix": a.prefix, "name": a.name,
               "created": str(date.today()), "status": "proposed"})
    if a.pillar:
        fm["content_pillar"] = a.pillar
    if a.start:
        fm["schedule_start"] = a.start
    if a.end:
        fm["schedule_end"] = a.end
    if cfg.get("kpi_default"):
        fm["kpi"] = dict(cfg["kpi_default"])
    if cfg.get("owner"):
        fm["owner"] = cfg["owner"]
    body = body.replace("# Hồ sơ chiến dịch — Tên chiến dịch", f"# Hồ sơ chiến dịch — {a.name}")
    md_io.write_fm(dich / "campaign.md", fm, body)

    so = kenh / "CAMPAIGNS.md"
    fm2, body2 = md_io.read_fm(so)
    body2 = md_io.upsert_row(body2, "CAMPAIGNS", "campaign_id", {
        "campaign_id": a.id, "tên": a.name, "pillar": a.pillar or "",
        "status": "proposed", "bắt đầu": a.start, "kết thúc": a.end,
        "bài": "0", "đã đăng": "0", "thư mục": f"./{a.id}/"}, COT)
    fm2["updated"] = str(date.today())
    md_io.write_fm(so, fm2, body2)

    print(f"  chiến dịch: {dich / 'campaign.md'}")
    print(f"  sổ        : {so}")
    print(f"  tiếp      : điền frontmatter + Mục 1-3, rồi new_post.py --campaign {a.id} "
          f"--id {a.prefix}-001 --slug … --title \"…\"")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
