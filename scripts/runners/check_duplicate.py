# -*- coding: utf-8 -*-
"""check_duplicate.py — chống đăng TRÙNG tin daily-hot.

So tiêu đề của tin vừa sinh (<new_top_json>.top_story.headline) với TẤT CẢ tiêu đề
đã đăng thành công trong <hot_news_json> (entries có date < <date>). Dùng độ tương
đồng tập-từ (max của Jaccard và containment). In đúng 1 dòng:

  DUP=yes sim=0.57 match=2026-06-14|Mỹ buộc Anthropic gỡ Claude Fable 5 và Mythos 5
  DUP=no  sim=0.18

Usage: python check_duplicate.py <new_top_json> <hot_news_json> <date> [threshold=0.5]
Exit luôn 0 (best-effort; runner đọc DUP=yes/no).
"""
import json
import re
import sys

STOP = {"và", "của", "cho", "một", "các", "trong", "khi", "đã", "sẽ", "là", "với",
        "này", "đó", "ra", "mắt", "về", "giờ", "bằng", "đến", "từ", "the", "for"}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return set(w for w in s.split() if len(w) > 2 and w not in STOP)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 4:
        print("DUP=no sim=0.00 (bad args)")
        return 0
    new_json, hot_json, date = sys.argv[1], sys.argv[2], sys.argv[3]
    thr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5

    try:
        d = json.load(open(new_json, encoding="utf-8-sig"))
    except Exception as e:
        print(f"DUP=no sim=0.00 (cannot read new json: {type(e).__name__})")
        return 0
    a = norm((d.get("top_story") or {}).get("headline", ""))
    if not a:
        print("DUP=no sim=0.00 (empty headline)")
        return 0
    try:
        hd = json.load(open(hot_json, encoding="utf-8-sig"))
    except Exception:
        print("DUP=no sim=0.00 (no history)")
        return 0

    best = (0.0, "", "")
    for e in hd.get("entries", []):
        if str(e.get("date", "")) >= str(date):
            continue  # chỉ so với tin ĐĂNG TRƯỚC ngày hiện tại
        b = norm(e.get("title", ""))
        if not b:
            continue
        sim = max(len(a & b) / len(a | b), len(a & b) / min(len(a), len(b)))
        if sim > best[0]:
            best = (sim, str(e.get("date", "")), str(e.get("title", "")))
    if best[0] >= thr:
        print(f"DUP=yes sim={best[0]:.2f} match={best[1]}|{best[2]}")
    else:
        print(f"DUP=no sim={best[0]:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
