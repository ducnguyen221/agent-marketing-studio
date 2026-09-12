#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hợp nhất cấu hình một chiến dịch thành MỘT khối JSON, in ra stdout.

    python campaign_cfg.py --campaign <thư-mục-chiến-dịch> [--out config.json]

## Vì sao tồn tại

Người sửa `.md`; máy chạy là PowerShell 5.1 — nó **không đọc được YAML**: máy không có
`powershell-yaml`, không có `ConvertFrom-Yaml`, không có PowerShell 7. Tự viết parser bằng
regex đã đo thử: đọc được 27 khoá phẳng nhưng **sót 7/34 dòng** (list, khối lồng, dòng gấp
`>`), đúng chỗ đặt màu và khối `theme:`.

Nên chia việc theo đúng thứ mỗi bên làm được: **Python đọc `.md`, PowerShell đọc JSON.**
Script này là cây cầu, và là chỗ DUY NHẤT biết cách ghép các tầng cấu hình.

## Thứ tự đè (sau đè trước)

    1. channel.yml    → khối `brand:`      cấu hình máy cấp kênh
    2. brand.json     → toàn bộ khoá        (BẢN CŨ — còn đọc tới khi bỏ hẳn; xem ghi chú dưới)
    3. brand.md       → frontmatter         câu chữ cấp kênh (tagline, welcome)
    4. campaign.md    → `runtime/theme/identity/titles/hashtags`   cấu hình + câu chữ campaign

`brand.json` nằm ở tầng 2 chứ không phải tầng 1: nó là bản đang chạy thật hôm nay, còn khối
`brand:` trong `channel.yml` là đích đến. Khi mọi khoá đã sang `channel.yml` thì bỏ tầng 2,
và thứ tự đè không đổi nghĩa.

## Bản chụp mang CẢ TÊN CŨ LẪN TÊN MỚI — cố ý

Bốn runner + 2 `build-index.ps1` + 2 `send_newsletter.py` đang đọc **25 tên khoá phẳng**
(`$cfg.label`, `$cfg.yt_playlist_daily`…). Nếu bản chụp chỉ có tên mới thì phải sửa 25 chỗ
trong cùng một lượt — một chỗ sai là cả 5 pipeline chết mà chỉ phát hiện lúc 18h.

Vì vậy JSON ra có **hai lớp**: các khoá phẳng tên cũ (để engine hiện tại chạy y như trước)
và các khối lồng tên mới (`theme`, `identity`, `titles`). Chuyển dần từng file; khi không
còn ai đọc tên cũ thì bỏ lớp phẳng.

## FAIL-CLOSED

Thiếu `campaign.md`, frontmatter không phải ánh xạ, hoặc thiếu khoá bắt buộc → **exit 2**,
không in JSON. Lý do: một bản chụp thiếu khoá sẽ làm runner chạy tiếp với giá trị rỗng —
video không có tiêu đề, bài đăng không có playlist — và **không ai biết** cho tới khi xem
sản phẩm. Dừng hẳn ồn ào tốt hơn chạy tiếp im lặng.

Exit: 0 xong · 2 cấu hình sai/thiếu · 3 sai cách dùng.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402

import yaml  # noqa: E402

SCHEMA = "campaign-config/1"

# Khoá BẮT BUỘC phải có sau khi ghép xong. Thiếu = dừng.
# Ngắn có chủ đích: mỗi khoá ở đây là một thứ mà THIẾU NÓ thì sản phẩm ra sai mà không
# báo lỗi — tiêu đề rỗng, đăng nhầm playlist. Khoá chỉ làm đẹp thì không nằm ở đây.
BAT_BUOC = ("label", "runner")

# Khối lồng trong frontmatter `campaign.md` mà script này hiểu.
KHOI_CAMPAIGN = ("runtime", "theme", "identity", "titles", "hashtags")


def _doc_yaml(p: Path) -> dict:
    """Đọc một file YAML. Không có file -> {}. File hỏng -> ném lỗi, KHÔNG nuốt."""
    if not p.is_file():
        return {}
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d, dict):
        raise ValueError(f"{p}: phải là ánh xạ khoá-giá trị, đang là {type(d).__name__}")
    return d


def _doc_json(p: Path) -> dict:
    if not p.is_file():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError(f"{p}: phải là đối tượng JSON, đang là {type(d).__name__}")
    return d


def _doc_fm(p: Path) -> dict:
    """Frontmatter của một file .md. Không có file -> {}."""
    if not p.is_file():
        return {}
    fm, _ = md_io.read_fm(p)
    return fm


def gop(campaign_dir: Path) -> dict:
    """Ghép 4 tầng thành một dict phẳng + các khối lồng. Không ghi file nào."""
    cam_md = campaign_dir / SP.MOC_CHIEN_DICH
    if not cam_md.is_file():
        raise FileNotFoundError(
            f"không thấy {SP.MOC_CHIEN_DICH} trong {campaign_dir}.\n"
            f"Một thư mục chiến dịch được nhận ra BẰNG file này — thiếu nó thì cả "
            f"check_tree, build_views lẫn export_excel đều không thấy chiến dịch.")

    kenh_dir = SP.channel_of(cam_md)
    ra: dict = {}

    # ── tầng 1: channel.yml -> khối brand:
    kenh_yml = _doc_yaml(kenh_dir / SP.MOC_KENH)
    brand_block = kenh_yml.get("brand") or {}
    if not isinstance(brand_block, dict):
        raise ValueError(f"{kenh_dir / SP.MOC_KENH}: `brand:` phải là ánh xạ")
    ra.update(brand_block)

    # ── tầng 2: brand.json (bản đang chạy — bỏ khi mọi khoá đã sang channel.yml)
    ra.update(_doc_json(kenh_dir / "brand.json"))

    # ── tầng 3: brand.md -> câu chữ cấp kênh
    #
    # Lấy TẤT CẢ khoá frontmatter, trừ hai khoá chỉ để định danh file. Danh sách trắng cứng
    # từng khoá nghe an toàn hơn nhưng thực tế ngược lại: thêm một câu chữ vào brand.md mà
    # quên thêm tên nó vào đây thì nó im lặng không tới engine, và người sửa file cứ tưởng
    # đã sửa xong. Ai đọc khoá nào là việc của engine; ở đây chỉ chuyển tiếp trung thực.
    brand_md = _doc_fm(kenh_dir / "brand.md")
    for k, v in brand_md.items():
        if k not in ("schema", "channel"):
            ra[k] = v

    # ── tầng 4: campaign.md
    fm = _doc_fm(cam_md)
    la = [k for k in fm if k in KHOI_CAMPAIGN and not isinstance(fm[k], dict)
          and k != "hashtags"]
    if la:
        raise ValueError(f"{cam_md}: các khối {la} phải là ánh xạ khoá-giá trị")

    ra.update(fm.get("runtime") or {})

    # Khối lồng: giữ NGUYÊN hình dạng cho code mới, ĐỒNG THỜI trải phẳng tên cũ cho code
    # hiện tại. Trải phẳng chứ không thay thế — xem ghi chú "hai lớp" ở đầu file.
    for khoi in ("theme", "identity", "titles"):
        v = fm.get(khoi)
        if isinstance(v, dict):
            ra[khoi] = v
    if "hashtags" in fm:
        ra["hashtags"] = fm["hashtags"]

    ten_cu = {
        ("identity", "brand_a"): "topstory_brand_a",
        ("identity", "brand_b"): "topstory_brand_b",
        ("identity", "kicker"): "topstory_kicker",
        ("identity", "site"): "topstory_site",
        ("identity", "tagline_short"): "tagline_short",
        ("theme", "video_accents"): "topstory_accents",
        ("theme", "email_accent"): "email_accent",
        ("titles", "yt_prefix"): "yt_title_prefix",
        ("titles", "recap"): "weekly_recap_title",
        ("titles", "short"): "weekly_short_title",
    }
    for (khoi, con), cu in ten_cu.items():
        v = (fm.get(khoi) or {}).get(con) if isinstance(fm.get(khoi), dict) else None
        if v is not None:
            ra[cu] = v

    # ── Mức tự trị: SAU CÙNG, cố ý ──────────────────────────────────────────
    #
    # `autonomy` chỉ được đến từ `channel.yml` và KHÔNG khối nào phía trên đè lên nó được.
    # Nếu để `campaign.md` ghi đè thì một file chiến dịch tự nâng quyền cho chính nó lên
    # `full` là đăng thẳng ra ngoài — đúng kiểu leo thang mà cổng tự trị sinh ra để chặn.
    #
    # Vì sao phải nằm trong bản chụp: PowerShell 5.1 không đọc được YAML, nên runner KHÔNG
    # có cách nào tự biết mức tự trị. Không có dòng này thì cổng tự trị ở tầng runner không
    # tồn tại được — nó sẽ chỉ là một lời dặn trong tài liệu.
    ra["autonomy"] = (kenh_yml.get("autonomy") or "suggest").strip()

    # Suy ra khoá bỏ đi được, để engine cũ vẫn đọc thấy trong lúc chuyển tiếp.
    # KHÔNG ghi đè nếu đã có giá trị thật — suy luận là đường lùi, không phải nguồn.
    base = ra.get("site_base")
    if base:
        ra.setdefault("site", base)
        # `site_root` và `page_weekly_base` đều là site_base có dấu / cuối. Chúng từng là hai
        # khoá riêng trong brand.json và luôn bằng nhau — giữ cả hai tên vì
        # `run-weekly-news.ps1:91` ghép URL trang tuần từ `page_weekly_base`, bỏ nó đi là
        # mọi link tuần thành `.../w36.html` dính liền tên miền.
        ra.setdefault("site_root", base if base.endswith("/") else base + "/")
        ra.setdefault("page_weekly_base", base if base.endswith("/") else base + "/")
    for a, b in (("email_brand_a", "a"), ("email_brand_b", "b")):
        if b in ra:
            ra.setdefault(a, ra[b])

    # Ba tên playlist cũ trỏ về một khoá chung. Engine nào còn đọc tên cũ vẫn chạy.
    if "yt_playlist" in ra:
        ra.setdefault("yt_playlist_daily", ra["yt_playlist"])
        ra.setdefault("yt_playlist_weekly", ra["yt_playlist"])
    if "yt_title_prefix" in ra:
        ra.setdefault("yt_title_prefix_daily", ra["yt_title_prefix"])

    # ── Đường ra và log RIÊNG cho từng chiến dịch, đường tuyệt đối.
    #
    # Trước đây hai thứ này nằm ở CẤP KÊNH và dùng chung: `ai-news/daily-out` là của
    # daily, còn `ai-news/logs` chứa lẫn lộn log của cả daily lẫn weekly (42 file
    # `toptoday-AI-*` + 39 `hot-publish-AI-*` của daily nằm cạnh 11 file `<ngày>.log` của
    # weekly). Muốn biết một chiến dịch đã ra bao nhiêu số phải lọc theo TÊN FILE — tức
    # ranh giới giữa các chiến dịch chỉ tồn tại trong đầu người đọc.
    #
    # Tuyệt đối chứ không tương đối: runner `Set-Location` sang thư mục repo tin ở giữa
    # chừng (git pull/push), nên đường tương đối sẽ trỏ sai từ đó trở đi.
    ra["out_root"] = str(campaign_dir / (ra.get("out_dir") or "out"))
    ra["log_dir"] = str(campaign_dir / "logs")
    # Prompt cũng là thứ RIÊNG của chiến dịch, không phải của kênh: hai chiến dịch cùng
    # kênh (bản tin ngày và bản tin tuần) có cách viết khác hẳn nhau.
    ra["prompt_path"] = str(campaign_dir / (ra.get("prompt") or "prompt.txt"))

    thieu = [k for k in BAT_BUOC if not ra.get(k)]
    if thieu:
        raise ValueError(
            f"{cam_md}: thiếu khoá bắt buộc {thieu}.\n"
            f"Chúng phải nằm trong khối `runtime:` của frontmatter. Thiếu mà vẫn chạy thì "
            f"sản phẩm ra sai và KHÔNG có dòng lỗi nào — nên dừng ở đây.")

    ra["_meta"] = {
        "schema": SCHEMA,
        "campaign": campaign_dir.name,
        "channel": kenh_dir.name,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generated_from": [
            str((kenh_dir / SP.MOC_KENH).name),
            "brand.json" if (kenh_dir / "brand.json").is_file() else None,
            "brand.md" if (kenh_dir / "brand.md").is_file() else None,
            SP.MOC_CHIEN_DICH,
        ],
        "warn": "BẢN CHỤP SINH TỰ ĐỘNG — đừng sửa tay, lượt chạy sau ghi đè.",
    }
    ra["_meta"]["generated_from"] = [x for x in ra["_meta"]["generated_from"] if x]
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Hợp nhất cấu hình chiến dịch thành JSON.")
    ap.add_argument("--campaign", required=True, help="thư mục chiến dịch (có campaign.md)")
    ap.add_argument("--out", default="", help="ghi ra file thay vì stdout")
    a = ap.parse_args(argv)

    campaign = Path(a.campaign).expanduser().resolve()
    try:
        cfg = gop(campaign)
    except (FileNotFoundError, ValueError, yaml.YAMLError, json.JSONDecodeError) as e:
        sys.stderr.write(f"campaign_cfg: {e}\n")
        return 2

    txt = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    if a.out:
        # Nguyên tử: PowerShell có thể đọc file này ngay sau khi lệnh trả về; ghi thẳng
        # thì có cửa sổ đọc phải file viết dở.
        md_io.write_atomic(Path(a.out), txt)
    else:
        sys.stdout.write(txt)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
