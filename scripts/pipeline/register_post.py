# -*- coding: utf-8 -*-
r"""register_post.py — ghi TÓM TẮT + KEY-TERMS của bài đã chốt vào hồ sơ campaign md (Mục 12),
và đọc lại danh sách bài trước (PRIOR POSTS) để bài sau liên kết + tránh lặp thuật ngữ.

Mục 12 "Lịch sử bài đã chốt": | post_id | Tiêu đề | Tóm tắt | Key-terms | Ngày chốt |
Continuity: trước khi viết bài mới, đọc Mục 12 để nhắc lại bài trước, tránh giải thích lại
thuật ngữ đã viết sâu (chỉ tóm tắt + trỏ "xem bài trước"), tránh keyword rời rạc/lặp nhiều.

CLI:
  # ghi/cập nhật 1 bài (trích Tóm tắt/Key-terms từ content.md mục 7):
  python register_post.py --campaign-md <NN.md> --post-id ID --content-md <content.md>
      [--title T] [--date YYYY-MM-DD]
  # đọc lại danh sách bài trước (cho {{PRIOR_POSTS}}):
  python register_post.py --campaign-md <NN.md> --list
"""
from __future__ import annotations
import argparse, os, re, sys

HDR = "| post_id | Tiêu đề | Tóm tắt | Key-terms | Hồ sơ (content) | Ngày chốt |"
SEP = "|---|---|---|---|---|---|"


def _extract(content_md):
    """Trích 'Tóm tắt:' + 'Key-terms:' từ content.md (mục 7). Trả (summary, keyterms)."""
    if not content_md or not os.path.isfile(content_md):
        return "", ""
    t = open(content_md, encoding="utf-8").read()
    def grab(label):
        m = re.search(r"(?im)^[\s>*-]*" + label + r"\s*[:：]\s*(.+)$", t)
        return re.sub(r"\s+", " ", m.group(1)).strip(" *_`") if m else ""
    summary = grab(r"T[oó]m\s*t[aắ]t")
    keyterms = grab(r"Key[-\s]?terms?") or grab(r"T[uừ]\s*kh[oó]a")
    # rút gọn ô bảng (tránh ký tự | làm vỡ bảng)
    summary = summary.replace("|", "/")[:240]
    keyterms = keyterms.replace("|", "/")[:240]
    return summary, keyterms


def _find_table(lines):
    """Trả (hi, start, end) của bảng Mục 12 (bất kỳ header '| post_id |' — cũ 3 cột hay mới 6 cột)."""
    hi = next((i for i, ln in enumerate(lines) if ln.strip().startswith("| post_id |")), None)
    if hi is None:
        return None, None, None
    start = hi + 2
    end = start
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    return hi, start, end


def _migrate(lines, hi, start, end):
    """Nâng bảng cũ (3 cột post_id|Tiêu đề|Ngày chốt) lên 6 cột; pad ô trống."""
    lines[hi] = HDR
    lines[hi + 1] = SEP
    for i in range(start, end):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if len(cells) < 6:
            pid = cells[0] if len(cells) > 0 else ""
            ttl = cells[1] if len(cells) > 1 else ""
            dt = cells[-1] if len(cells) >= 3 else ""
            lines[i] = f"| {pid} | {ttl} |  |  |  | {dt} |"


def upsert(md, post_id, title, summary, keyterms, date, ref=""):
    text = open(md, encoding="utf-8").read()
    lines = text.split("\n")
    refcell = f"`{ref}`" if ref else ""
    row = f"| {post_id} | {title} | {summary} | {keyterms} | {refcell} | {date} |"
    hi, start, end = _find_table(lines)
    if hi is None:
        # bảng cũ (3 cột) hoặc chưa có -> thay/ thêm bảng 5 cột dưới Mục 12
        anchor = next((i for i, ln in enumerate(lines) if ln.strip().startswith("## 12.")), None)
        block = ["", HDR, SEP, row]
        if anchor is not None:
            # chèn ngay sau dòng chú thích (dòng '>' đầu tiên sau anchor) hoặc sau anchor
            ins = anchor + 1
            while ins < len(lines) and (lines[ins].strip().startswith(">") or not lines[ins].strip()):
                ins += 1
            lines[ins:ins] = block
        else:
            lines += ["", "## 12. Lịch sử bài đã chốt"] + block
    else:
        if lines[hi].strip() != HDR:  # bảng cũ 3 cột -> nâng lên 6 cột
            _migrate(lines, hi, start, end)
        found = next((i for i in range(start, end)
                      if re.match(r"^\|\s*" + re.escape(post_id) + r"\s*\|", lines[i])), None)
        if found is not None:
            lines[found] = row
        else:
            lines.insert(end, row)
    open(md, "w", encoding="utf-8").write("\n".join(lines))


def list_prior(md):
    lines = open(md, encoding="utf-8").read().split("\n")
    hi, start, end = _find_table(lines)
    if hi is None:
        return ""
    out = []
    for i in range(start, end):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] and not cells[0].startswith("{{"):
            ref = cells[4].strip("`") if len(cells) >= 6 else ""
            line = f"- {cells[0]} — {cells[1]}\n    Tóm tắt: {cells[2]}\n    Key-terms: {cells[3]}"
            if ref:
                line += f"\n    Đọc chi tiết (nếu cần): {ref}/content.md , {ref}/blog.md"
            out.append(line)
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-md", required=True)
    ap.add_argument("--post-id", default="")
    ap.add_argument("--content-md", default="")
    ap.add_argument("--meta", default="", help="meta.json (fallback summary = angle nếu thiếu Tóm tắt)")
    ap.add_argument("--title", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--folder", default="", help="đường dẫn tương đối folder content (refer campaign md -> content chi tiết)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.campaign_md):
        print(f"ERROR không thấy md: {a.campaign_md}", file=sys.stderr); return 1
    if a.list:
        print(list_prior(a.campaign_md))
        return 0
    if not a.post_id:
        print("ERROR cần --post-id để ghi", file=sys.stderr); return 1
    summary, keyterms = _extract(a.content_md)
    # fallback: thiếu Tóm tắt -> dùng angle trong meta.json
    if not summary and a.meta and os.path.isfile(a.meta):
        try:
            import json
            summary = (json.load(open(a.meta, encoding="utf-8-sig")).get("angle") or "")[:240]
        except Exception:
            pass
    title = a.title or a.post_id
    upsert(a.campaign_md, a.post_id, title, summary, keyterms, a.date, a.folder)
    print(f"OK registered post {a.post_id} -> Mục 12")
    print(f"  BACKFILL summary: {summary or '(trống)'}")
    print(f"  BACKFILL key-terms: {keyterms or '(trống)'}")
    print(f"  BACKFILL ref: {a.folder or '(trống)'}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
