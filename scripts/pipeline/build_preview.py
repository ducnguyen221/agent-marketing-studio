# -*- coding: utf-8 -*-
"""
Dựng file HTML TỰ CHỨA để hình dung một bài blog + asset (stage preview).

Vấn đề: nếu HTML tham chiếu ảnh/video bằng đường dẫn (`<img src="thumbnail.png">`), chuyển
folder hoặc gửi file đi là VỠ hết. Cách giải: **nhúng asset vào chính file HTML dưới dạng
base64 data URI**. File thành một khối duy nhất, không phụ thuộc file ngoài — mở ở đâu,
gửi qua đâu, chuyển folder nào cũng nguyên vẹn.

  - Ảnh (png/jpg/svg/webp/gif): LUÔN nhúng.
  - Audio (mp3/wav): nhúng nếu ≤ --max-embed-mb (mặc định 12 MB); vượt thì bỏ, ghi chú.
  - Video: KHÔNG nhúng file mp4 cục bộ. Chỉ hiện video khi bài ĐÃ có `youtube_url` trong
    Sheet Result — dạng link YouTube. Chưa upload YouTube thì không đính kèm video gì cả.

    build_preview.py --campaign-dir <dir> --post-id TOBI-001 [--out preview.html]
                     [--max-embed-mb 12] [--workbook <wb.xlsx>]
"""
from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import re
import sys
from pathlib import Path

try:
    import markdown as md_lib
except ImportError:
    md_lib = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from campaign_io import find_workbook, read_sheet  # noqa: E402

IMG_EXT = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg"}

CSS = """
:root{--fg:#14161b;--muted:#565d69;--bg:#fff;--card:#f7f8fa;--border:#e4e8ef;--accent:#2f6df6}
@media(prefers-color-scheme:dark){:root{--fg:#e9ebef;--muted:#9aa3b2;--bg:#0e0f13;--card:#16181d;--border:#282c34;--accent:#5b8cff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.7 "Segoe UI",system-ui,-apple-system,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:32px 20px 80px}
.badge{display:inline-block;font-size:12px;color:var(--muted);border:1px solid var(--border);
border-radius:20px;padding:3px 12px;margin-bottom:14px}
h1{font-size:30px;line-height:1.25;margin:.2em 0 .5em}h2{font-size:22px;margin:1.6em 0 .5em}
h3{font-size:18px;margin:1.3em 0 .4em}p{margin:.8em 0}img{max-width:100%;height:auto;border-radius:10px;margin:1em 0}
a{color:var(--accent)}blockquote{border-left:3px solid var(--accent);margin:1em 0;padding:.3em 1em;
background:var(--card);border-radius:0 8px 8px 0}code{background:var(--card);padding:2px 6px;border-radius:5px;font-size:.9em}
table{border-collapse:collapse;width:100%;margin:1em 0}th,td{border:1px solid var(--border);padding:8px 10px;text-align:left}
.assetbox{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin:1.4em 0}
.assetbox h4{margin:0 0 10px;font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
audio{width:100%;margin:.5em 0}.note{color:var(--muted);font-size:14px;word-break:break-all}
.ytlink{display:inline-block;background:#ff0000;color:#fff;font-weight:600;text-decoration:none;
padding:9px 16px;border-radius:8px}
.foot{margin-top:48px;padding-top:16px;border-top:1px solid var(--border);color:var(--muted);font-size:13px}
"""


def data_uri(path: Path) -> str | None:
    mime = mimetypes.guess_type(path.name)[0]
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    if not mime:
        return None
    b = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b}"


def extract_blog(content_md: str) -> str:
    """Lấy phần <!-- BEGIN BLOG --> … <!-- END BLOG -->; không có thì lấy cả file."""
    m = re.search(r"<!--\s*BEGIN BLOG\s*-->(.*?)<!--\s*END BLOG\s*-->", content_md,
                  re.DOTALL | re.IGNORECASE)
    return (m.group(1) if m else content_md).strip()


def md_to_html(text: str) -> str:
    if md_lib:
        return md_lib.markdown(text, extensions=["tables", "fenced_code"])
    # fallback tối thiểu nếu thiếu lib
    out = []
    for para in text.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if p.startswith("### "):
            out.append(f"<h3>{html.escape(p[4:])}</h3>")
        elif p.startswith("## "):
            out.append(f"<h2>{html.escape(p[3:])}</h2>")
        elif p.startswith("# "):
            out.append(f"<h1>{html.escape(p[2:])}</h1>")
        else:
            out.append(f"<p>{html.escape(p)}</p>")
    return "\n".join(out)


def inline_images(html_body: str, base: Path, report: list) -> str:
    """Đổi mọi <img src="đường dẫn cục bộ"> thành data URI nhúng."""
    def repl(m):
        src = m.group(1)
        if src.startswith(("data:", "http://", "https://")):
            return m.group(0)
        f = (base / src).resolve()
        if f.exists() and f.suffix.lower() in IMG_EXT:
            uri = data_uri(f)
            if uri:
                report.append(("nhúng ảnh", src, f.stat().st_size))
                return m.group(0).replace(src, uri)
        report.append(("ảnh KHÔNG thấy", src, 0))
        return m.group(0)
    return re.sub(r'<img[^>]*\ssrc="([^"]+)"', repl, html_body)


def asset_blocks(folder: Path, max_bytes: int, youtube_url: str, report: list) -> str:
    """Nhúng ảnh + audio trong folder bài. Video: chỉ hiện link YouTube nếu đã upload."""
    blocks = []
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    imgs = [p for p in files if p.suffix.lower() in IMG_EXT and p.name != "preview.html"]
    auds = [p for p in files if p.suffix.lower() in AUDIO_EXT]

    for p in imgs:
        uri = data_uri(p)
        if uri:
            report.append(("nhúng ảnh asset", p.name, p.stat().st_size))
            blocks.append(f'<div class="assetbox"><h4>{html.escape(p.name)}</h4>'
                          f'<img src="{uri}" alt="{html.escape(p.name)}"></div>')
    for p in auds:
        size = p.stat().st_size
        if size <= max_bytes:
            uri = data_uri(p)
            report.append(("nhúng audio", p.name, size))
            blocks.append(f'<div class="assetbox"><h4>Audio · {html.escape(p.name)}</h4>'
                          f'<audio controls src="{uri}"></audio></div>')
        else:
            report.append(("audio quá lớn, bỏ", p.name, size))
            blocks.append(f'<div class="assetbox"><h4>Audio · {html.escape(p.name)}</h4>'
                          f'<p class="note">File {size/1e6:.1f} MB vượt ngưỡng nhúng — '
                          f'giữ riêng, không nhúng để preview không quá nặng.</p></div>')

    # Video: KHÔNG nhúng file cục bộ. Chỉ hiện khi đã có youtube_url (đã upload).
    if youtube_url:
        report.append(("video → link YouTube", youtube_url, 0))
        safe = html.escape(youtube_url)
        blocks.append(
            f'<div class="assetbox"><h4>Video</h4>'
            f'<p><a class="ytlink" href="{safe}" target="_blank" rel="noopener">'
            f'▶ Xem video trên YouTube</a></p>'
            f'<p class="note">{safe}</p></div>')
    else:
        report.append(("video", "chưa upload YouTube — không đính kèm", 0))
    return "\n".join(blocks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign-dir", required=True)
    ap.add_argument("--post-id", required=True)
    ap.add_argument("--out")
    ap.add_argument("--max-embed-mb", type=float, default=12)
    ap.add_argument("--workbook")
    args = ap.parse_args()

    cdir = Path(args.campaign_dir)
    # tìm folder bài: cột folder_path trong Post, hoặc assets/<post_id>*
    folder = None
    wb = args.workbook or find_workbook(cdir)
    title = args.post_id
    youtube_url = ""
    if wb:
        for r in read_sheet(wb, "Post"):
            if str(r.get("post_id")) == args.post_id:
                title = r.get("topic_title") or args.post_id
                fp = str(r.get("folder_path") or "").strip()
                if fp:
                    folder = (cdir / fp)
                break
        # video chỉ hiện nếu đã upload YouTube → lấy từ Sheet Result
        for r in read_sheet(wb, "Result"):
            if str(r.get("post_id")) == args.post_id:
                youtube_url = str(r.get("youtube_url") or "").strip()
                break
    if folder is None or not folder.exists():
        hits = list((cdir / "assets").glob(f"{args.post_id}*"))
        folder = hits[0] if hits else None
    if not folder or not folder.exists():
        print(f"Không thấy folder asset của {args.post_id} trong {cdir/'assets'}", file=sys.stderr)
        return 2

    content_md = folder / "content.md"
    blog_html = ""
    if content_md.exists():
        blog_html = md_to_html(extract_blog(content_md.read_text(encoding="utf-8")))

    report: list = []
    blog_html = inline_images(blog_html, folder, report)
    assets_html = asset_blocks(folder, int(args.max_embed_mb * 1e6), youtube_url, report)

    doc = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(str(title))} — preview</title>
<style>{CSS}</style></head><body><div class="wrap">
<span class="badge">Bản xem trước · {html.escape(args.post_id)}</span>
{blog_html}
<h2 style="margin-top:2em">Asset đính kèm</h2>
{assets_html or '<p class="note">Chưa có asset nào trong folder bài.</p>'}
<div class="foot">File này TỰ CHỨA — ảnh và asset đã nhúng base64. Chuyển folder, đổi tên,
gửi qua email đều không vỡ. Sinh bởi marketing-agent · build_preview.py.</div>
</div></body></html>"""

    out = Path(args.out) if args.out else (folder / "preview.html")
    out.write_text(doc, encoding="utf-8")
    total = out.stat().st_size

    print(f"── preview · {args.post_id}")
    for kind, name, sz in report:
        print(f"   {kind:<20} {name}" + (f"  ({sz/1e6:.2f} MB)" if sz else ""))
    print(f"   ✅ {out}  ({total/1e6:.2f} MB, tự chứa)")
    if not md_lib:
        print("   ⚠ thiếu thư viện markdown — dùng renderer tối thiểu; cài `pip install markdown` cho đẹp hơn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
