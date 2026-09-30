"""Upsert one Hot News entry into the website data file (hot-news.json).

The hot-today page is data-driven: it fetches hot-news.json and renders the list
client-side. This script adds/updates the entry for a given date (dedupe by date),
keeps the list sorted newest-first, and writes it back.

Usage:
  python update_hot_index.py --top-json <date>-top.json --data hot-news.json \
      --date 2026-06-14 --video-id ABC --short-id XYZ --published-at 2026-06-14T15:30:00

A missing/empty --video-id is allowed (entry stored without an embed; the page
shows a "đang xử lý" placeholder until the next run fills it in).
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _summary(story):
    # Prefer the short intro (tight), fall back to the long intro trimmed.
    txt = (story.get("intro_short") or story.get("intro") or "").strip()
    if len(txt) > 300:
        txt = txt[:297].rstrip() + "…"
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-json", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--video-id", default="")
    ap.add_argument("--short-id", default="")
    ap.add_argument("--published-at", required=True)
    args = ap.parse_args()

    with open(args.top_json, encoding="utf-8-sig") as f:
        d = json.load(f)
    story = d.get("top_story", {})

    entry = {
        "date": args.date,
        "display_date": (d.get("display_date") or "").strip(),
        "title": (story.get("headline") or "").strip(),
        "summary": _summary(story),
        "source": (story.get("source") or "").strip(),
        "video_id": args.video_id.strip(),
        "short_id": args.short_id.strip(),
        "published_at": args.published_at.strip(),
    }

    data = {"entries": []}
    if os.path.isfile(args.data):
        try:
            with open(args.data, encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {"entries": []}
    entries = [e for e in data.get("entries", []) if e.get("date") != args.date]
    entries.append(entry)
    # newest first by date, then published_at as tiebreaker
    entries.sort(key=lambda e: (e.get("date", ""), e.get("published_at", "")), reverse=True)
    data["entries"] = entries

    with open(args.data, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"index updated: {len(entries)} entries -> {args.data} (this: {args.date})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
