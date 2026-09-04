#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo MỘT bài mới trong một chiến dịch: thư mục + meta.json + research.md + content.md,
rồi thêm dòng vào bảng Content của campaign.md.

Bài sinh ra ở trạng thái `proposed`. **Script không tự đặt `approved`** — Cổng 1 là của
người. Ô `g1` để trống cho tới khi người điền ngày.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import post_paths as PP  # noqa: E402
import studio_paths as SP  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TPL = REPO / "templates"

COT = ["content_id", "content_name", "pillar", "angle", "funnel", "priority",
       "status", "g1", "g2", "schedule", "published", "folder"]


def _tim_campaign(chi_dinh: str, station=None) -> Path:
    p = Path(chi_dinh)
    if (p / "campaign.md").is_file():
        return p.resolve()
    for c in SP.channels(station):
        q = c["dir"] / chi_dinh
        if (q / "campaign.md").is_file():
            return q.resolve()
    raise FileNotFoundError(f"không tìm ra chiến dịch {chi_dinh!r} — truyền đường dẫn "
                            f"hoặc id có trong một kênh của CHANNELS.md")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tạo bài mới trong một chiến dịch.")
    ap.add_argument("--campaign", required=True, help="đường dẫn thư mục chiến dịch, hoặc id")
    ap.add_argument("--id", required=True, help="content_id, vd AST-002")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--pillar", default="")
    ap.add_argument("--angle", default="")
    ap.add_argument("--funnel", default="awareness")
    ap.add_argument("--priority", default="medium")
    ap.add_argument("--schedule", default="")
    ap.add_argument("--audio", default="yes", choices=["yes", "no"])
    ap.add_argument("--video", default="yes", choices=["yes", "no"])
    ap.add_argument("--short", default="no", choices=["yes", "no"])
    ap.add_argument("--station", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not re.fullmatch(r"[a-z0-9-]+", a.slug):
        sys.stderr.write(f"--slug phải a-z0-9-: {a.slug!r}\n")
        return 2
    try:
        cam_dir = _tim_campaign(a.campaign, a.station)
    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        return 2

    fm_cam, body_cam = md_io.read_fm(cam_dir / "campaign.md")
    prefix = fm_cam.get("id_prefix", "")
    if prefix and not a.id.startswith(prefix + "-"):
        sys.stderr.write(f"--id {a.id!r} không khớp id_prefix {prefix!r} của chiến dịch\n")
        return 2

    dich = cam_dir / f"{a.id}_{a.slug}"
    if dich.exists():
        sys.stderr.write(f"đã có {dich} — dừng, không ghi đè\n")
        return 2
    if a.dry_run:
        print(f"  [dry-run] sẽ tạo {dich} và thêm dòng vào {cam_dir / 'campaign.md'}")
        return 0

    PP.tao_thu_muc(dich)

    # meta.json — định danh máy đọc. Giữ đúng hình dạng đang chạy.
    cat = {"powerbi": "bi", "fabric": "de", "ai-agent": "ai", "career": "strategy"}
    pillar = a.pillar or fm_cam.get("content_pillar", "")
    json.dump({
        "post_id": a.id, "campaign_id": fm_cam.get("id", ""),
        "title": a.title, "slug": a.slug,
        "pillar": pillar, "category": cat.get(pillar, "ai"),
        "angle": a.angle, "schedule_date": a.schedule,
        "hashtags": [],
    }, (dich / "meta.json").open("w", encoding="utf-8", newline="\n"),
        ensure_ascii=False, indent=2)

    # research.md — frontmatter mang brief chi tiết
    shutil.copy2(TPL / "research.md", PP.p(dich, "research"))
    fm_r, body_r = md_io.read_fm(PP.p(dich, "research"))
    fm_r.update({"content_id": a.id, "campaign_id": fm_cam.get("id", ""),
                 "audio": a.audio, "video": a.video, "short": a.short})
    body_r = body_r.replace("# research.md — XXX-001 · Tên bài",
                            f"# research.md — {a.id} · {a.title}")
    md_io.write_fm(PP.p(dich, "research"), fm_r, body_r)

    # content.md
    shutil.copy2(TPL / "content.md", PP.p(dich, "content"))
    fm_c, body_c = md_io.read_fm(PP.p(dich, "content"))
    fm_c.update({"content_id": a.id, "campaign_id": fm_cam.get("id", ""),
                 "content_name": a.title})
    md_io.write_fm(PP.p(dich, "content"), fm_c, body_c)

    # dòng trong bảng Content — status=proposed, g1 TRỐNG (Cổng 1 là của người)
    body_cam = md_io.upsert_row(body_cam, "CONTENT", "content_id", {
        "content_id": a.id, "content_name": a.title, "pillar": pillar,
        "angle": a.angle, "funnel": a.funnel, "priority": a.priority,
        "status": "proposed", "g1": "", "g2": "",
        "schedule": a.schedule, "published": "", "folder": f"./{dich.name}/"}, COT)
    md_io.write_fm(cam_dir / "campaign.md", fm_cam, body_cam)

    print(f"  bài  : {dich}")
    print(f"  sổ   : {cam_dir / 'campaign.md'} (bảng Content, status=proposed)")
    print(f"  ⚠️ Cổng 1 là của NGƯỜI: điền status=approved và ngày vào ô g1 rồi mới viết bài.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
