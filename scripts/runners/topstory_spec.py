# -*- coding: utf-8 -*-
"""topstory_spec.py — dựng file spec cho `video-studio render --project topstory`.

Runner tin (`run-toptoday-hot.ps1`, `run-weekly-repo.ps1`) có sẵn ba thứ: file nội dung
`<ngày>-top.json` do bước nghiên cứu viết, bản chụp cấu hình của chiến dịch (`-Config`), và
giọng/nhạc nền đã chọn. `video-studio` nhận MỘT file spec (`schema_version: 1`) gồm nội dung đó
cộng bốn khối hợp đồng `brand · voice · bgm · outputs` — file này ghép chúng lại.

Vì sao là Python chứ không làm ngay trong PowerShell: `ConvertTo-Json` của PS 5.1 bọc mảng
thành `{"value": [...], "Count": n}` trong vài trường hợp và cắt ở độ sâu 2 nếu quên `-Depth`
— một spec hỏng kiểu đó vẫn là JSON hợp lệ, nên chỉ lộ ra ở video. Python đọc/ghi JSON đúng
một cách trên cả Windows lẫn macOS.

Thương hiệu KHÔNG có mặc định ở đây — engine cũng không. Thiếu `a`, `b` hay `site` là mã 2
kèm tên khoá cần khai trong `campaign.md: identity`, không bao giờ lùi về tên của ai.

    python topstory_spec.py --top <ngày>-top.json --config <bản chụp> --date 2026-09-28 \
        --profile my-voice --bgm news-corporate --bgm-volume 0.10 --out <ngày>-spec.json

Mã thoát: 0 ok · 2 đầu vào sai (thiếu file, JSON hỏng, thiếu khoá thương hiệu).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SCHEMA_VERSION = 1
# Khối hợp đồng của spec — nội dung trong -top.json KHÔNG được mang các khoá này vào, vì spec
# do runner quyết (vd `bgm` trong -top.json là GỢI Ý của AI, runner đã chọn xong ở ngoài).
HOP_DONG = ("schema_version", "brand", "voice", "bgm", "outputs")

# (khoá trong bản chụp cấu hình, khoá trong spec.brand). Tên bên trái là tên `campaign_cfg.py`
# trải phẳng từ `campaign.md: identity` (brand_a -> topstory_brand_a, …).
BRAND_MAP = (
    ("topstory_brand_a", "a"),
    ("topstory_brand_b", "b"),
    ("topstory_site", "site"),
    ("topstory_kicker", "kicker"),
)


class Loi(Exception):
    """Đầu vào sai — mã 2."""


def _doc_json(path, ten):
    if not path or not os.path.isfile(path):
        raise Loi(f"không có file {ten}: {path}")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except ValueError as e:
        raise Loi(f"{ten} {path}: JSON hỏng — {e}") from e
    if not isinstance(data, dict):
        raise Loi(f"{ten} {path}: phải là một object JSON")
    return data


def brand_tu_cfg(cfg):
    """-> khối `brand` của spec, lấy từ bản chụp cấu hình. Thiếu a/b/site ⇒ Loi."""
    brand = {}
    for src, dst in BRAND_MAP:
        v = cfg.get(src)
        if isinstance(v, str) and v.strip():
            brand[dst] = v.strip()
    thieu = [dst for src, dst in BRAND_MAP[:3] if dst not in brand]
    if thieu:
        raise Loi(
            "cấu hình thiếu thương hiệu cho video: " + ", ".join(thieu) + ". Khai trong "
            "campaign.md khối `identity:` (brand_a, brand_b, site; tuỳ chọn kicker) — "
            "engine video không có thương hiệu mặc định.")
    acc = cfg.get("topstory_accents")
    if isinstance(acc, str) and acc.strip():
        brand["accent"] = [c.strip() for c in acc.split(",") if c.strip()]
    pron = cfg.get("pronounce")
    if pron:
        if not isinstance(pron, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in pron.items()):
            raise Loi("`pronounce` (channel.yml: brand) phải là bảng {regex: cách đọc}")
        brand["pronounce"] = dict(pron)
    return brand


def bgm_khoi(style, volume):
    """-> khối `bgm`. Rỗng / 'none' = tắt nhạc nền."""
    s = (style or "").strip()
    if not s or s.lower() == "none":
        return "none"
    out = {"style": s}
    if volume not in (None, ""):
        try:
            out["volume"] = float(volume)
        except (TypeError, ValueError) as e:
            raise Loi(f"--bgm-volume phải là số, nhận {volume!r}") from e
    return out


def dung_spec(top, cfg, date, profile="", bgm="", bgm_volume=None):
    if not (date or "").strip():
        raise Loi("thiếu --date (engine đặt tên file ra theo nó)")
    spec = {k: v for k, v in top.items() if k not in HOP_DONG}
    spec["date"] = date.strip()
    spec["schema_version"] = SCHEMA_VERSION
    spec["brand"] = brand_tu_cfg(cfg)
    spec["voice"] = {"profile": profile.strip()} if (profile or "").strip() else {}
    spec["bgm"] = bgm_khoi(bgm, bgm_volume)
    spec["outputs"] = {"long": True, "short": True}
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description="dựng spec cho video-studio render --project topstory")
    ap.add_argument("--top", required=True, help="<ngày>-top.json do bước nghiên cứu viết")
    ap.add_argument("--config", required=True, help="bản chụp cấu hình chiến dịch (JSON)")
    ap.add_argument("--date", required=True)
    ap.add_argument("--profile", default="")
    ap.add_argument("--bgm", default="", help="tên style / đường dẫn mp3 / 'none'")
    ap.add_argument("--bgm-volume", default=None)
    ap.add_argument("--out", required=True, help="nơi ghi spec — PHẢI cạnh -top.json "
                    "(đường dẫn ảnh/clip tương đối neo vào thư mục chứa spec)")
    a = ap.parse_args(argv)
    try:
        spec = dung_spec(_doc_json(a.top, "nội dung"), _doc_json(a.config, "cấu hình"),
                         a.date, a.profile, a.bgm, a.bgm_volume)
    except Loi as e:
        print(f"topstory_spec: {e}", file=sys.stderr)
        return 2
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    os.replace(tmp, a.out)
    print(f"topstory_spec: {a.out} (brand {spec['brand']['a']} {spec['brand']['b']}, "
          f"voice {spec['voice'].get('profile') or '-'}, bgm "
          f"{spec['bgm'] if isinstance(spec['bgm'], str) else spec['bgm']['style']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
