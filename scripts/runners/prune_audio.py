"""Prune old weekly audio (mp3) to bound the GitHub Pages site size.

WHY: weekly mp3 MUST stay on GitHub Pages (same-origin, Content-Type audio/mpeg,
range support) so the <audio> player works on every device incl. mobile — GitHub
*Releases* serve octet-stream + attachment + nosniff and phones refuse them, so
moving mp3 off Pages is not an option. The only safe lever is to keep just the
newest N editions and drop older ones.

WHAT it does, per brand-repo:
  * keep the newest --keep editions' audio/<date>/ folders untouched;
  * for older editions: DELETE audio/<date>/ AND "degrade" that edition's HTML so
    the article/blog still renders but the now-broken read controls are gone:
      - remove the injected <!--MEDIA_INJECTED-->...</script> audio player,
      - hide the read buttons (#readAll, #readStop, .readbtn) via a small style,
      - leave a <!--MEDIA_PRUNED--> marker (idempotent).
  * the recap VIDEO (YouTube embed) is never touched.

Audio→HTML mapping comes from the injected player itself (var base=
"../../audio/<date>/"), so it is exact regardless of ISO-week math.

Deletions happen in the working tree only; the caller stages them (git add -A)
and commits. Idempotent: re-running prunes nothing already pruned.

Usage:
  python prune_audio.py --repo <brand-repo> [--keep 54] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BASE_RE = re.compile(r'audio/(\d{4}-\d{2}-\d{2})/')
INJECTED_RE = re.compile(r"<!--MEDIA_INJECTED-->.*?</script>", re.S)
PRUNED_MARKER = "<!--MEDIA_PRUNED-->"
# Khi xoá mp3: gỡ player + ẩn mọi nút đọc (đọc chung + đọc từng tin). Nội dung giữ nguyên.
HIDE_BLOCK = (
    PRUNED_MARKER + "\n"
    "<style>#readAll,#readStop,.readbtn{display:none!important}</style>"
)


def _map_date_to_html(repo):
    """Scan edition HTMLs -> {audio_date: html_path} via the injected base URL."""
    out = {}
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    html = f.read()
            except Exception:
                continue
            m = BASE_RE.search(html)
            if m:
                out.setdefault(m.group(1), p)
    return out


def _degrade(html_path, dry):
    """Remove the audio player + hide read buttons. Returns a status string."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    if PRUNED_MARKER in html:
        return "already-pruned"
    if INJECTED_RE.search(html):
        new = INJECTED_RE.sub(HIDE_BLOCK, html, count=1)
    elif "</body>" in html:
        new = html.replace("</body>", HIDE_BLOCK + "\n</body>", 1)
    else:
        new = html + HIDE_BLOCK
    if new == html:
        return "no-change"
    if not dry:
        with open(html_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
    return "degraded"


def _dir_mb(path):
    if not os.path.isdir(path):
        return 0.0
    total = 0
    for fn in os.listdir(path):
        fp = os.path.join(path, fn)
        if os.path.isfile(fp):
            total += os.path.getsize(fp)
    return total / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="brand repo path (holds audio/ + edition HTMLs)")
    ap.add_argument("--keep", type=int, default=54, help="số bản tin mới nhất giữ lại mp3 (default 54 ~ 1 năm)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo cáo, không xoá/sửa gì")
    a = ap.parse_args()

    audio_root = os.path.join(a.repo, "audio")
    if not os.path.isdir(audio_root):
        print(f"[prune] no audio/ in {a.repo} — nothing to do")
        return 0

    eds = sorted(
        (d for d in os.listdir(audio_root)
         if DATE_RE.match(d) and os.path.isdir(os.path.join(audio_root, d))),
        reverse=True,
    )
    keep, prune = eds[: a.keep], eds[a.keep:]
    tag = " [DRY-RUN]" if a.dry_run else ""
    print(f"[prune] {len(eds)} editions; keep newest {a.keep} -> {len(keep)} kept, {len(prune)} to prune{tag}")
    if not prune:
        print("[prune] nothing to prune.")
        return 0

    dmap = _map_date_to_html(a.repo)
    freed = 0.0
    for d in prune:
        html = dmap.get(d)
        st = _degrade(html, a.dry_run) if html else "no-html-found"
        adir = os.path.join(audio_root, d)
        mb = _dir_mb(adir)
        freed += mb
        rel = os.path.relpath(html, a.repo) if html else "(html not found)"
        print(f"  prune {d}: html={rel} [{st}], audio {mb:.1f} MB")
        if not a.dry_run and os.path.isdir(adir):
            shutil.rmtree(adir, ignore_errors=True)
    print(f"[prune] {'would free' if a.dry_run else 'freed'} ~{freed:.1f} MB"
          + (" (dry-run, nothing written)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
