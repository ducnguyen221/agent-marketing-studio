# -*- coding: utf-8 -*-
r"""register_links.py — ghi/cập nhật link bài đã đăng vào HỒ SƠ campaign md (Mục 13 Lịch sử đăng tải).

Upsert 1 dòng theo post_id vào bảng dưới '## 13. Lịch sử đăng tải'.
Cột: post_id | blog_url | youtube_url | fb_permalink | Ngày đăng.

CLI:
  python register_links.py --campaign-md <NN_Ten.md> --post-id ID
      [--blog-url U] [--youtube-url U] [--fb-permalink U] [--date YYYY-MM-DD]
"""
from __future__ import annotations
import argparse, os, re, sys

HDR = "| post_id | blog_url | youtube_url | fb_permalink | Ngày đăng |"
SEP = "|---|---|---|---|---|"


def upsert(md_path, post_id, blog, yt, fb, date):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    cells = [post_id, blog or "", yt or "", fb or "", date or ""]
    newrow = "| " + " | ".join(cells) + " |"

    lines = text.split("\n")
    # tìm header bảng Mục 13
    hi = next((i for i, ln in enumerate(lines) if ln.strip().startswith("| post_id |")
               and "Ngày đăng" in ln), None)
    if hi is None:
        # không thấy -> thêm cả bảng ở cuối
        lines += ["", "## 13. Lịch sử đăng tải (auto)", HDR, SEP, newrow]
    else:
        # dòng dữ liệu bắt đầu sau header+sep
        start = hi + 2
        end = start
        while end < len(lines) and lines[end].strip().startswith("|"):
            end += 1
        # tìm dòng có post_id để cập nhật
        found = None
        for i in range(start, end):
            if re.match(r"^\|\s*" + re.escape(post_id) + r"\s*\|", lines[i]):
                found = i; break
        if found is not None:
            lines[found] = newrow
        else:
            lines.insert(end, newrow)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-md", required=True)
    ap.add_argument("--post-id", required=True)
    ap.add_argument("--blog-url", default="")
    ap.add_argument("--youtube-url", default="")
    ap.add_argument("--fb-permalink", default="")
    ap.add_argument("--date", default="")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.campaign_md):
        print(f"ERROR không thấy md: {a.campaign_md}", file=sys.stderr)
        return 1
    upsert(a.campaign_md, a.post_id, a.blog_url, a.youtube_url, a.fb_permalink, a.date)
    print(f"OK registered {a.post_id} -> {a.campaign_md}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
