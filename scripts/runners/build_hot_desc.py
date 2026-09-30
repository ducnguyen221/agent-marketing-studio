"""Build the YouTube description for a Hot News (daily top-story) video.

Reads the /toptoday brief (<date>-top.json) and emits a description file:
  intro + danh sách nội dung chính (mỗi section 1 dòng) + nguồn + link trang
  + giới thiệu kênh + CTA + hashtags.

Usage:
  python build_hot_desc.py --top-json <date>-top.json --page-url URL --out desc.txt [--shorts]

Brand rule: NEVER name internal tools (OmniVoice/HyperFrames/last30days/"giọng AI").
Narrator/editor = --author (channel.yml brand.author). The NEWS SUBJECT (Anthropic/Claude/etc.)
may be named.
"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-json", required=True)
    ap.add_argument("--page-url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--site", default="", help="section root URL (site_root của kênh)")
    ap.add_argument("--author", default="", help="người biên tập/đọc (channel.yml brand.author)")
    ap.add_argument("--label", default="AI", help="AI hoặc Data (cho chữ + hashtag)")
    args = ap.parse_args()

    with open(args.top_json, encoding="utf-8-sig") as f:
        d = json.load(f)
    s = d.get("top_story", {})
    headline = (s.get("headline") or "").strip()
    source = (s.get("source") or "").strip()
    disp = (d.get("display_date") or d.get("date") or "").strip()
    intro = (s.get("intro_short") if args.shorts else s.get("intro")) or ""
    intro = intro.strip()
    sections = s.get("sections", [])

    lines = []
    if args.shorts:
        lines.append(f"🔥 Hot News {disp}: {headline}")
        lines.append("")
        if intro:
            lines.append(intro)
        lines.append("")
        lines.append(f"📺 Bản đầy đủ + các tin nóng khác: {args.page_url}")
    else:
        if intro:
            lines.append(intro)
            lines.append("")
        lines.append("📋 Nội dung chính trong video:")
        for sec in sections:
            title = (sec.get("title") or "").strip().rstrip("?").strip()
            # first concrete bullet of the section, else the lead
            detail = ""
            pts = sec.get("points") or []
            if pts:
                detail = (pts[0].get("text") or "").strip()
            if not detail:
                detail = (sec.get("lead") or "").strip()
                if len(detail) > 90:
                    detail = detail[:87].rstrip() + "…"
            lines.append(f"• {title} — {detail}" if detail else f"• {title}")
        lines.append("")
        if source:
            lines.append(f"🔗 Nguồn chính: {source}")
        lines.append(f"📺 Xem tất cả tin nóng theo ngày: {args.page_url}")

    lines.append("")
    lines.append("—")
    _disp = lambda u: u.replace("https://", "").replace("http://", "").rstrip("/")
    boi = f" by {args.author.strip()}" if args.author.strip() else ""
    lines.append(f"👤 Hot News{boi} — tin {args.label} NÓNG NHẤT mỗi ngày, "
                 "tuyển chọn, biên tập và đọc bằng tiếng Việt, giải thích dễ hiểu cho người không rành công nghệ.")
    if args.site:
        lines.append(f"🌐 {_disp(args.site)}  ·  Lưu trữ tin nóng: {_disp(args.page_url)}")
    else:
        lines.append(f"🌐 Lưu trữ tin nóng: {_disp(args.page_url)}")
    lines.append("")
    lines.append(f"👍 Thấy hữu ích thì Like & Subscribe để không bỏ lỡ tin {args.label} nóng mỗi ngày nhé!")
    lines.append("")
    lines.append("⚠️ Tin tức tổng hợp từ nguồn công khai, mang tính thông tin tham khảo.")
    lines.append("")
    tags = "#AI #AINews #TinTucAI" if args.label == "AI" else "#Data #DataNews #DuLieu"
    lines.append(tags + " #HotNews #CongNghe" + (" #Shorts" if args.shorts else ""))

    text = "\n".join(lines)[:4900]
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"desc written: {len(text)} chars -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
