"""Build the DEDUP "already covered" list for the weekly news prompt.

Collects the N most-recent editions PUBLISHED BEFORE the reference date and
prints each card's title + URL as `- TITLE  (url)` lines for {{SEEN_LIST}}.

Editions live at <repo>/YYYY/MM/<name>.html where <name> is either a date
(legacy dailies, e.g. 2026-06-10) or an ISO week (weekly, e.g. w24 — its
publish date is taken as that week's Friday). The wrapper passes MONDAY of the
current week as the reference so the current week's own stories stay eligible.

Usage: python build_seen_list.py <repo_dir> <ref_yyyy-mm-dd> [editions=3]
"""
import datetime
import glob
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TITLE_RE = re.compile(r'<a class="title" href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")


def _strip(s: str) -> str:
    s = TAG_RE.sub("", s)
    s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
         .replace("&#39;", "'").replace("&quot;", '"'))
    return " ".join(s.split())


def file_date(year: int, name: str):
    """Publish date of an edition file name: ISO date, or wNN -> that week's Friday."""
    m = re.fullmatch(r"w(\d{2})", name, re.I)
    if m:
        jan4 = datetime.date(year, 1, 4)
        week1_mon = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
        return week1_mon + datetime.timedelta(weeks=int(m.group(1)) - 1, days=4)
    try:
        return datetime.date.fromisoformat(name)
    except ValueError:
        return None


def main() -> int:
    repo = sys.argv[1]
    ref = datetime.date.fromisoformat(sys.argv[2])
    n_editions = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    editions = []
    for fp in glob.glob(os.path.join(repo, "20*", "*", "*.html")):
        m = re.search(r"[\\/](\d{4})[\\/]\d{2}[\\/]([^\\/]+)\.html$", fp)
        if not m:
            continue
        d = file_date(int(m.group(1)), m.group(2))
        if d and d < ref:
            editions.append((d, fp))
    editions.sort(reverse=True)
    picked = [fp for _d, fp in editions[:n_editions]]

    seen, seen_urls = [], set()
    for fp in picked:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                html = fh.read()
        except OSError:
            continue
        for url, title in TITLE_RE.findall(html):
            url = url.strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)
            seen.append(f"- {_strip(title)[:140]}  ({url})")

    if not seen:
        print("(none — no prior editions found)")
    else:
        print("\n".join(seen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
