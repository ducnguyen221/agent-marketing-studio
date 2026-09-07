"""Dựng phần mô tả YouTube cho một số của kênh.

Usage: python build_yt_desc.py --sidecar w24.html.json --page-url URL --out desc.txt
       [--chapters video/<d>/<d>.mp4.chapters.json] [--shorts]

Recap desc = giới thiệu + link bản tin + chapters (timestamps) hoặc danh sách
TOP-5 kèm ngày + tóm tắt tuần + giới thiệu tác giả + CTA like/subscribe.
Shorts desc = bản ngắn gọn.
"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sidecar", required=True)
    ap.add_argument("--page-url", required=True)
    ap.add_argument("--chapters", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--shorts", action="store_true")
    # Bản chụp cấu hình chiến dịch (campaign_cfg.py). Nhận diện kênh — tên, tagline, tác
    # giả, tên miền — đến từ đây. Ghi cứng chúng trong mã là biến mọi kênh dùng bản mẫu
    # này thành kênh của người viết ra nó.
    ap.add_argument("--config", default="", help="bản chụp JSON của chiến dịch")
    args = ap.parse_args()

    cfg = {}
    if args.config:
        with open(args.config, encoding="utf-8-sig") as f:
            cfg = json.load(f)
    brand = ((cfg.get("a") or "") + " " + (cfg.get("b") or "")).strip()
    author = cfg.get("author") or ""
    tagline = cfg.get("tagline") or ""
    home = cfg.get("home_url") or ""
    site = (cfg.get("site_base") or "").rstrip("/")
    if not brand or not author:
        # Thiếu nhận diện thì DỪNG. Mô tả video là thứ khán giả đọc; để trống hoặc để tên
        # người khác thì không ai phát hiện cho tới lúc video đã public.
        sys.stderr.write("build_yt_desc: thieu --config hoac thieu khoa nhan dien "
                         "(a, b, author) trong ban chup.\n")
        return 2

    with open(args.sidecar, encoding="utf-8-sig") as f:
        d = json.load(f)
    week_num = (d.get("week") or "").lstrip("Ww")
    rng = d.get("range", "")
    tldr = (d.get("tldr") or "").strip()
    top5 = sorted([i for i in d.get("items", []) if i.get("hot_rank")],
                  key=lambda i: i["hot_rank"])

    lines = []
    if args.shorts:
        lines.append(f"Top 5 tin nóng nhất tuần {week_num} ({rng}) trong 2 phút.")
        lines.append("")
        for it in top5:
            dd = "/".join(reversed((it.get("date") or "")[5:].split("-")))
            lines.append(f"▪ TOP {it['hot_rank']} ({dd}): {it['title']}")
        lines.append("")
        lines.append(f"📖 Bản tin đầy đủ ({len(d.get('items', []))} tin, kèm audio & video chi tiết):")
        lines.append(args.page_url)
    else:
        lines.append(f"{brand} tuần {week_num} ({rng}) — tóm tắt 5 tin nóng nhất tuần, "
                     f"tuyển chọn, biên tập và lồng tiếng bởi {author}.")
        lines.append("")
        lines.append(f"📖 Đọc bản tin đầy đủ ({len(d.get('items', []))} tin, kèm audio từng tin):")
        lines.append(args.page_url)
        lines.append("")
        chapters = []
        if args.chapters:
            try:
                with open(args.chapters, encoding="utf-8") as f:
                    chapters = json.load(f)
            except OSError:
                pass
        if chapters:
            lines.append("⏱️ Nội dung:")
            for c in chapters:
                lines.append(f"{_mmss(c['t'])} {c['label']}")
        else:
            lines.append("📋 Trong video:")
            for it in top5:
                dd = "/".join(reversed((it.get("date") or "")[5:].split("-")))
                lines.append(f"▪ TOP {it['hot_rank']} ({dd}): {it['title']}")
        if tldr:
            lines.append("")
            lines.append("📝 Tổng quan tuần:")
            lines.append(tldr)
    lines.append("")
    lines.append("—")
    lines.append(f"👤 {brand} — {tagline}, do {author} tuyển chọn, biên tập và đọc.")
    if home:
        lines.append(f"🌐 Website: {home} · Lưu trữ mọi số: {site}/")
    lines.append(f"📬 Nhận bản tin qua email: {site}/#subscribe")
    lines.append("")
    lines.append("👍 Thấy hữu ích thì Like & Subscribe để không bỏ lỡ bản tin tuần sau nhé!")
    lines.append("")
    lines.append("#AI #AINews #TinTucAI #CongNghe" + (" #Shorts" if args.shorts else ""))

    text = "\n".join(lines)[:4900]
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"desc written: {len(text)} chars -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
