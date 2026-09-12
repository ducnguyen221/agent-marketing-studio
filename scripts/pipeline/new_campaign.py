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
# Cây mẫu phản chiếu ĐÚNG hình dạng một trạm thật — mở `templates/station/` ra là thấy
# ngay kênh lồng chiến dịch lồng bài. Trước đây 15 file nằm phẳng một chỗ, đọc tên phải
# tự đoán cái nào lồng trong cái nào.
TPL_STATION = TPL / "station"
TPL_KENH    = TPL_STATION / "_channel"
TPL_CAM     = TPL_KENH / "_campaign"
TPL_BAI     = TPL_CAM / "_content"
# Hai kiểu mã hợp lệ, vì có hai loại chiến dịch khác nhau về bản chất:
#
#   CMP-YYMM-slug   chiến dịch marketing — có ngày bắt đầu/kết thúc, nên mã mang tháng.
#   slug            chiến dịch CHẠY THEO LỊCH (bản tin, series) — sống vô thời hạn, mã
#                   mang CHỨC NĂNG (`daily-ai-news`, `hot-repo`). Gắn tháng vào là nói dối:
#                   `CMP-2606-daily-ai-news` gợi ý một chiến dịch của tháng 6/2026, trong
#                   khi nó vẫn chạy và sẽ còn chạy.
#
# Điều kiện DUY NHẤT mà phần còn lại của hệ thống đòi: `id` == tên thư mục (check_tree.py).
MA = re.compile(r"^(CMP-\d{4}-[a-z0-9-]+|[a-z][a-z0-9_-]*)$")

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
    # Chiến dịch CHẠY THEO LỊCH (bản tin, series tự động) cần thêm hai file mà chiến dịch
    # marketing thường không có. Không bật mặc định: đẻ ra `run.ps1` cho một chiến dịch
    # viết tay là để lại một điểm vào không ai gọi, và sáu tháng sau không ai dám xoá.
    ap.add_argument("--runner", default="",
                    help="tên script engine (vd run-toptoday-hot.ps1) — sinh thêm run.ps1")
    ap.add_argument("--runner-args", default="",
                    help="tham số truyền cho runner, vd \"-Brand ai -Publish\"")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not MA.match(a.id):
        sys.stderr.write(f"--id phải dạng CMP-YYMM-slug (chữ thường): {a.id!r}\n")
        return 2
    if not re.fullmatch(r"[A-Z]{2,5}", a.prefix):
        sys.stderr.write(f"--prefix phải 2-5 chữ HOA: {a.prefix!r}\n")
        return 2

    try:
        channel = SP.channel_dir(a.channel, a.station)
    except KeyError as e:
        sys.stderr.write(f"{e}\n")
        return 2
    if not (channel / "channel.yml").is_file():
        sys.stderr.write(f"{channel} không phải thư mục kênh (thiếu channel.yml)\n")
        return 2

    # pillar phải nằm trong bộ của kênh — bắt sớm còn hơn để check_tree bắt muộn
    import yaml
    cfg = yaml.safe_load((channel / "channel.yml").read_text(encoding="utf-8")) or {}
    pillars = cfg.get("pillars") or []
    if a.pillar and pillars and a.pillar not in pillars:
        sys.stderr.write(f"--pillar {a.pillar!r} không có trong channel.yml:pillars {pillars}\n")
        return 2

    dest = channel / a.id
    if (dest / "campaign.md").exists():
        sys.stderr.write(f"đã có chiến dịch ở {dest} — dừng, không ghi đè\n")
        return 2
    if a.dry_run:
        print(f"  [dry-run] sẽ tạo {dest}/campaign.md và thêm dòng vào {channel / 'CAMPAIGNS.md'}")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TPL_CAM / "campaign.md", dest / "campaign.md")
    fm, body = md_io.read_fm(dest / "campaign.md")
    fm.update({"id": a.id, "channel": a.channel, "id_prefix": a.prefix, "name": a.name,
               "created": str(date.today()), "status": "proposed"})
    # `content_pillar` phải nằm trong `channel.yml:pillars`. Không truyền `--pillar` thì lấy
    # trụ ĐẦU TIÊN của kênh chứ không giữ chữ mẫu `tru-cot`: giữ lại là chiến dịch vừa sinh
    # ra đã ĐỎ ở check_tree — người dùng gặp lỗi trước khi kịp viết chữ nào. Cùng lý do với
    # `channels` ngay dưới: bản mẫu không được đoán hộ tên trụ của kênh thật.
    if a.pillar:
        fm["content_pillar"] = a.pillar
    elif pillars:
        fm["content_pillar"] = pillars[0]
    if a.start:
        fm["schedule_start"] = a.start
    if a.end:
        fm["schedule_end"] = a.end
    # Thu hẹp `channels` về đúng nền tảng kênh này có. Bản mẫu khai sẵn cả ba
    # (web_blog, youtube, facebook) nên kênh nào thiếu một nền tảng là chiến dịch vừa sinh
    # ra đã ĐỎ ở check_tree — người dùng gặp lỗi trước khi kịp viết chữ nào. Cổng đó đúng,
    # cái sai là để bản mẫu đoán hộ.
    plats = [p.get("channel") for p in (cfg.get("platforms") or []) if p.get("channel")]
    if plats:
        fm["channels"] = [c for c in (fm.get("channels") or []) if c in plats] or plats
    if a.runner:
        # Khối `runtime:` là thứ `campaign_cfg.py` đọc để dựng bản chụp cho engine.
        # `label` để trống có chủ đích: người điền, vì nó vào tên video và tiêu đề thật.
        fm["runtime"] = {"label": "", "runner": a.runner, "runner_args": a.runner_args}
        # run.ps1 GIỐNG HỆT NHAU ở mọi chiến dịch — chép nguyên bản mẫu, không sinh động.
        # BOM UTF-8 bắt buộc: PowerShell 5.1 đọc .ps1 không BOM sẽ hỏng dấu tiếng Việt và
        # parse-fail IM LẶNG, tức scheduled task "chạy" mà không làm gì.
        mau = TPL_CAM / "run.ps1"
        if mau.is_file():
            (dest / "run.ps1").write_bytes(mau.read_bytes())
        # `prompt.txt` cấp CHIẾN DỊCH = prompt bước CHỌN đề tài, chạy mỗi kỳ.
        # Khác `<bài>/prompt.txt` (bước VIẾT một bài cụ thể). Hai bước, hai prompt —
        # gộp lại thì lời dặn "chọn gì" và "viết thế nào" trộn vào nhau và cả hai cùng mờ.
        mau_p = TPL_CAM / "prompt.txt"
        if mau_p.is_file() and not (dest / "prompt.txt").exists():
            shutil.copy2(mau_p, dest / "prompt.txt")
    if cfg.get("kpi_default"):
        fm["kpi"] = dict(cfg["kpi_default"])
    if cfg.get("owner"):
        fm["owner"] = cfg["owner"]
    body = body.replace("# Hồ sơ chiến dịch — Tên chiến dịch", f"# Hồ sơ chiến dịch — {a.name}")
    md_io.write_fm(dest / "campaign.md", fm, body)

    so = channel / "CAMPAIGNS.md"
    fm2, body2 = md_io.read_fm(so)
    body2 = md_io.upsert_row(body2, "CAMPAIGNS", "campaign_id", {
        "campaign_id": a.id, "tên": a.name, "pillar": a.pillar or "",
        "status": "proposed", "bắt đầu": a.start, "kết thúc": a.end,
        "bài": "0", "đã đăng": "0", "thư mục": f"./{a.id}/"}, COT)
    fm2["updated"] = str(date.today())
    md_io.write_fm(so, fm2, body2)

    print(f"  chiến dịch: {dest / 'campaign.md'}")
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
