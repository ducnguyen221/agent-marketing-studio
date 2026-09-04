# -*- coding: utf-8 -*-
r"""build_blog_html.py — blog.md + meta + infographic.png → atlas.html self-contained.

Bắt chước cấu trúc databricks-genai.html: topbar (brand Tobi), hero có infographic,
nội dung bài (H2/H3, bullet, callout, bảng), footer tác giả + social. Dark theme,
font Be Vietnam Pro / Outfit / JetBrains Mono, dark tokens. Ảnh nhúng base64 để
file chạy độc lập (mở trực tiếp được).

CLI (theo PIPELINE_CONTRACT):
  python build_blog_html.py --blog-md F --meta meta.json --infographic PNG --out FOLDER\atlas.html
→ in dòng cuối `OK <abs_path html>`.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import html as _html

# Atlas category map (CONTRACT). meta.category override được.
PILLAR_CAT = {"powerbi": "bi", "fabric": "de", "ai-agent": "ai", "career": "strategy"}
PILLAR_LABEL = {"powerbi": "Power BI", "fabric": "Microsoft Fabric",
                "ai-agent": "AI Agent", "career": "Sự nghiệp Data"}


def _read(path, optional=False):
    if not path or not os.path.isfile(path):
        if optional:
            return ""
        raise FileNotFoundError(f"Không thấy file: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _esc(s):
    return _html.escape(str(s), quote=True)


def _inline(s):
    """Render inline markdown an toàn: escape trước, rồi bật **bold**, `code`, [link](url)."""
    s = _esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    # *nghiêng* — phải chạy SAU **đậm**, và không được ăn dấu sao của phép nhân.
    # Trước bản vá này, mọi cụm *"trích dẫn"* in ra nguyên hai dấu sao trên trang.
    s = re.sub(r"(?<![\w*])\*(?![\s*])([^*]+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


# Dòng MỞ một block mới (heading / list / trích dẫn / bảng / hr). Dùng để biết dòng kế tiếp
# có phải phần NỐI của mục list đang mở hay không. Thiếu nó, một mục list dài xuống dòng bị
# cắt thành <ol> một phần tử + <p> lẻ, và mọi mục đều đánh số "1." — bài AST-001 dính đúng
# lỗi này: 2 danh sách in ra thành 6 khối <ol>.
_MO_BLOCK = re.compile(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>|\||-{3,}$)")
_EMOJI_LEAD = re.compile(r"^\s*([\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿])")


def md_to_html(md_text):
    """Chuyển blog markdown → HTML body (H1 bỏ qua, đã ở hero)."""
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    i, n = 0, len(lines)

    def is_row(s):
        return s.strip().startswith("|") and s.strip().endswith("|")

    def is_sep(s):
        return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", s)) and "-" in s

    while i < n:
        s = lines[i].strip()
        # bảng
        if is_row(s) and i + 1 < n and is_sep(lines[i + 1]):
            header = [c.strip() for c in s.strip("|").split("|")]
            body = []
            j = i + 2
            while j < n and is_row(lines[j].strip()):
                body.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            th = "".join(f"<th>{_inline(c)}</th>" for c in header)
            trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>"
                          for row in body)
            out.append(f'<div class="tbl-wrap"><table><thead><tr>{th}</tr></thead>'
                       f"<tbody>{trs}</tbody></table></div>")
            i = j
            continue

        if not s:
            i += 1
            continue

        # Dấu ngắt "---" là đường kẻ ngang, không phải đoạn văn có ba dấu gạch.
        if re.match(r"^(?:-{3,}|\*{3,}|_{3,})$", s):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2).strip()
            if lvl == 1:
                i += 1  # title đã ở hero
                continue
            tag = "h2" if lvl == 2 else ("h3" if lvl == 3 else "h4")
            out.append(f"<{tag}>{_inline(txt)}</{tag}>")
            i += 1
            continue

        # callout: "> " hoặc emoji đầu dòng
        if s.startswith(">") or _EMOJI_LEAD.match(s):
            txt = s[1:].strip() if s.startswith(">") else s
            buf = [txt]
            i += 1
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f'<div class="callout">{_inline(" ".join(buf))}</div>')
            continue

        # bullet list
        if re.match(r"^[-*+]\s+", s):
            items = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                buf = [re.sub(r"^[-*+]\s+", "", lines[i].strip())]
                i += 1
                while i < n and lines[i].strip() and not _MO_BLOCK.match(lines[i].strip()):
                    buf.append(lines[i].strip())
                    i += 1
                items.append(_inline(" ".join(buf)))
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue

        # numbered list
        if re.match(r"^\d+[.)]\s+", s):
            items = []
            while i < n and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                buf = [re.sub(r"^\d+[.)]\s+", "", lines[i].strip())]
                i += 1
                while i < n and lines[i].strip() and not _MO_BLOCK.match(lines[i].strip()):
                    buf.append(lines[i].strip())
                    i += 1
                items.append(_inline(" ".join(buf)))
            out.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            continue

        # đoạn văn (gộp dòng)
        buf = [s]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>|\|)", lines[i].strip()) \
                and not _EMOJI_LEAD.match(lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")
    return "\n".join(out)


def _title(md_text, meta):
    for ln in md_text.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^#\s+(.*)$", ln.strip())
        if m:
            return re.sub(r"\*\*(.+?)\*\*", r"\1", m.group(1)).strip()
    return meta.get("title", "Học cùng Tobi")


def _img_data_uri(png_path):
    if not png_path or not os.path.isfile(png_path):
        return ""
    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------- template (atlas dark)
_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · Học cùng Tobi</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{page_url}">
<meta name="author" content="{author}">
<!-- Open Graph — BAT BUOC. Thieu la Facebook/Zalo scrape ra bai TRAN TRUI, mat phan lon suc hut.
     Ca VC-001/002/003 deu thieu (do 04/09: 0/3 bai co the og:) => bo sung tan goc tai day. -->
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:site_name" content="{site_name}">
<meta property="article:published_time" content="{published}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og_image}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#0b1020;--bg-elev:#0f1530;--surface:#151b3d;--surface-2:#1c244d;
  --border:#2a3470;--border-soft:#1f2654;
  --accent:#7c83ff;--accent-2:#a5acff;--accent-soft:#3d3e9c;--violet:#c4a8ff;
  --green:#34d399;--amber:#fbbf24;--sky:#38bdf8;
  --text:#e8ecff;--text-2:#a8b0d6;--text-3:#6b75a8;
  --shadow-lg:0 4px 8px rgba(0,0,0,.35),0 24px 48px rgba(0,0,0,.3);
}}
html{{scroll-behavior:smooth;overflow-x:hidden}}
h1,h2,h3,h4{{font-family:'Outfit','Be Vietnam Pro',sans-serif}}
body{{font-family:'Be Vietnam Pro',system-ui,-apple-system,sans-serif;
  background:radial-gradient(1200px 600px at 20% -10%,rgba(124,131,255,.12),transparent 60%),
             radial-gradient(900px 500px at 90% 10%,rgba(196,168,255,.08),transparent 60%),var(--bg);
  color:var(--text);min-height:100vh;line-height:1.7;-webkit-font-smoothing:antialiased;
  overflow-x:hidden;overflow-wrap:break-word}}
::selection{{background:var(--accent);color:#fff}}
img{{max-width:100%}}
a{{color:var(--accent-2);text-decoration:none;border-bottom:1px dashed var(--accent-soft)}}
a:hover{{border-bottom-style:solid}}

.topbar{{position:sticky;top:0;z-index:100;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);
  background:rgba(11,16,32,.78);border-bottom:1px solid var(--border-soft)}}
.topbar-inner{{max-width:920px;margin:0 auto;display:flex;align-items:center;gap:14px;padding:14px 28px}}
.brand{{display:flex;align-items:center;gap:12px;text-decoration:none;color:inherit;border:none}}
.brand-mark{{width:40px;height:40px;border-radius:12px;flex-shrink:0;
  background:linear-gradient(135deg,#7c83ff,#c4a8ff);box-shadow:0 4px 16px rgba(124,131,255,.35);
  display:flex;align-items:center;justify-content:center}}
.brand-mark svg{{width:22px;height:22px}}
.brand-text h1{{font-size:.95rem;font-weight:800;line-height:1.2}}
.brand-text h1 span{{color:var(--accent-2)}}
.brand-text p{{font-size:.72rem;color:var(--text-3);font-weight:500;margin-top:1px}}
.topbar .pill{{margin-left:auto;font-size:.74rem;font-weight:700;color:var(--accent-2);
  background:rgba(124,131,255,.12);border:1px solid var(--accent-soft);border-radius:999px;padding:6px 16px}}

.container{{max-width:920px;margin:0 auto;padding:40px 28px 80px}}

.hero{{display:grid;grid-template-columns:1fr;gap:28px;margin-bottom:44px;align-items:center}}
.hero.has-art{{grid-template-columns:1.1fr .9fr}}
.hero .kick{{display:inline-block;font-size:.78rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--accent-2);background:rgba(124,131,255,.12);border:1px solid var(--accent-soft);
  border-radius:999px;padding:7px 18px;margin-bottom:18px}}
.hero h1.title{{font-size:2.5rem;font-weight:900;letter-spacing:-1px;line-height:1.12;margin-bottom:14px}}
.hero .angle{{color:var(--text-2);font-size:1.05rem;line-height:1.6}}
.hero-art{{border-radius:20px;overflow:hidden;border:1px solid var(--border-soft);box-shadow:var(--shadow-lg)}}
.hero-art img{{display:block;width:100%;height:auto}}

.article h2{{font-size:1.5rem;font-weight:800;margin:42px 0 14px;padding-bottom:10px;
  border-bottom:1px solid var(--border-soft);color:var(--text)}}
.article h3{{font-size:1.18rem;font-weight:700;margin:30px 0 10px;color:var(--accent-2)}}
.article h4{{font-size:1.02rem;font-weight:700;margin:22px 0 8px;color:var(--violet)}}
.article p{{color:var(--text-2);margin:14px 0;font-size:1.02rem}}
.article strong{{color:var(--text);font-weight:700}}
.article code{{font-family:'JetBrains Mono',monospace;font-size:.85em;background:var(--bg-elev);
  padding:2px 7px;border-radius:5px;color:var(--violet);border:1px solid var(--border-soft)}}
.article ul,.article ol{{margin:14px 0 14px 8px;padding-left:22px;color:var(--text-2)}}
.article li{{margin:8px 0;font-size:1.02rem}}
.article ul li::marker{{color:var(--accent)}}
.callout{{background:linear-gradient(180deg,rgba(124,131,255,.08),transparent);
  border:1px solid var(--border-soft);border-left:4px solid var(--accent);
  border-radius:4px 14px 14px 4px;padding:16px 20px;margin:22px 0;color:var(--text);font-size:1.02rem}}
.tbl-wrap{{overflow-x:auto;margin:22px 0;border:1px solid var(--border-soft);border-radius:14px}}
table{{width:100%;border-collapse:collapse;font-size:.95rem}}
th,td{{padding:11px 16px;text-align:left;border-bottom:1px solid var(--border-soft)}}
thead th{{background:var(--surface);color:var(--text);font-weight:700}}
tbody tr:hover{{background:var(--surface)}}
td{{color:var(--text-2)}}

.author-card{{margin-top:54px;background:linear-gradient(135deg,rgba(124,131,255,.06),rgba(196,168,255,.04));
  border:1px solid var(--border-soft);border-radius:18px;padding:28px;
  display:grid;grid-template-columns:auto 1fr auto;gap:26px;align-items:center}}
.author-avatar{{width:84px;height:84px;border-radius:50%;overflow:hidden;flex-shrink:0;
  border:3px solid var(--accent-soft);box-shadow:0 8px 32px rgba(124,131,255,.3)}}
.author-avatar img{{width:100%;height:100%;object-fit:cover;display:block}}
.author-info .kicker{{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  color:var(--text-3);margin-bottom:6px}}
.author-info h3{{font-size:1.3rem;font-weight:800;margin-bottom:4px;
  background:linear-gradient(90deg,var(--accent-2),var(--violet));-webkit-background-clip:text;
  background-clip:text;-webkit-text-fill-color:transparent;color:transparent}}
.author-info p{{color:var(--text-2);font-size:.88rem;line-height:1.6;max-width:520px}}
.social-grid{{display:grid;grid-template-columns:repeat(4,40px);gap:8px}}
.social-btn{{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  background:var(--surface);border:1px solid var(--border-soft);color:var(--text-2);transition:all .15s}}
.social-btn svg{{width:18px;height:18px}}
.social-btn:hover{{transform:translateY(-2px);box-shadow:0 6px 16px rgba(0,0,0,.3)}}

@media(max-width:780px){{
  .hero.has-art{{grid-template-columns:1fr}}
  .hero h1.title{{font-size:1.9rem}}
}}
.media{{margin:0 0 44px}}
.media .media-label{{font-size:.8rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);margin:0 0 12px}}
.video-embed{{position:relative;width:100%;aspect-ratio:16/9;border-radius:18px;overflow:hidden;
  border:1px solid var(--border-soft);box-shadow:var(--shadow-lg);margin-bottom:20px;background:#000}}
.video-embed iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}}
.media.cover{{margin:0 0 40px}}
.cover-art{{border-radius:18px;overflow:hidden;border:1px solid var(--border-soft);box-shadow:var(--shadow-lg);margin-bottom:20px}}
.cover-art img{{display:block;width:100%;height:auto}}
.sr-only{{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}}
.audio-embed{{display:flex;align-items:center;gap:14px;padding:14px 18px;border-radius:14px;
  border:1px solid var(--border-soft);background:var(--surface)}}
.audio-embed .ic{{font-size:1.3rem}}
.audio-embed audio{{flex:1;width:100%}}
@media (max-width:720px){{
  .hero.has-art{{grid-template-columns:1fr}}
  .author-card{{grid-template-columns:1fr;text-align:center;gap:18px;padding:22px}}
  .author-avatar{{margin:0 auto}}.author-info p{{margin:0 auto}}.social-grid{{justify-content:center;margin:0 auto}}
}}
</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="https://ducnguyen.vn/atlas/" target="_blank" rel="noopener">
      <div class="brand-mark"><svg viewBox="0 0 576 512" fill="#fff"><path d="M249.6 471.5c10.8 3.8 22.4-4.1 22.4-15.5V78.6c0-4.2-1.6-8.4-5-11C247.4 52 202.4 32 144 32C93.5 32 46.3 45.3 18.1 56.1C6.8 60.5 0 71.7 0 83.8V454.1c0 11.9 12.8 20.2 24.1 16.5C55.6 460.1 105.5 448 144 448c33.9 0 79 14 105.6 23.5zm76.8 0C353 462 398.1 448 432 448c38.5 0 88.4 12.1 119.9 22.6c11.3 3.8 24.1-4.6 24.1-16.5V83.8c0-12.1-6.8-23.3-18.1-27.6C529.7 45.3 482.5 32 432 32c-58.4 0-103.4 20-123 35.6c-3.3 2.6-5 6.8-5 11V456c0 11.4 11.7 19.3 22.4 15.5z"/></svg></div>
      <div class="brand-text"><h1>Học cùng <span>Tobi</span></h1><p>COMPA Class · KPIM Academy</p></div>
    </a>
    <span class="pill">{badge}</span>
  </div>
</header>

<main class="container">
  {media}
  <article class="article">
    {body}
  </article>

  <footer class="author-card" aria-labelledby="author-name">
    <div class="author-avatar">
      <img src="https://ducnguyen221.github.io/profile/assets/images/KPIM-Duc-Nguyen.png" alt="Nguyễn Quang Đức" loading="lazy" width="84" height="84">
    </div>
    <div class="author-info">
      <div class="kicker">Tác giả · Author</div>
      <h3 id="author-name">Nguyễn Quang Đức (Tobi)</h3>
      <p>Data &amp; AI Engineer · Trainer tại KPIM Academy &amp; COMPA Class. Trang cá nhân tại
        <a href="https://ducnguyen.vn" target="_blank" rel="noopener">ducnguyen.vn</a>.</p>
    </div>
    <nav class="social-grid" aria-label="Liên kết tác giả">
      <a class="social-btn" href="https://ducnguyen.vn" target="_blank" rel="noopener" aria-label="Website" title="ducnguyen.vn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>
      </a>
      <a class="social-btn" href="https://www.facebook.com/TobiNguyenData/" target="_blank" rel="noopener" aria-label="Facebook" title="Facebook">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"/></svg>
      </a>
      <a class="social-btn" href="https://www.youtube.com/@PowerBIHeroVn" target="_blank" rel="noopener" aria-label="YouTube" title="YouTube">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
      </a>
      <a class="social-btn" href="https://ducnguyen221.github.io/profile/" target="_blank" rel="noopener" aria-label="E-Profile" title="E-Profile">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>
      </a>
    </nav>
  </footer>
</main>
</body>
</html>"""


def _yt_id(url):
    """Trích video id từ youtu.be/<id> hoặc watch?v=<id>."""
    if not url:
        return ""
    m = re.search(r"(?:youtu\.be/|[?&]v=|/embed/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else ""


def _cover_block(title, youtube_url, audio_src, cover_uri=""):
    """Khối ĐẦU TRANG (thay hero): tiêu đề ẩn cho SEO + video YouTube (đã có tiêu đề+ảnh ở cover);
    nếu chưa có video thì fallback ảnh thumbnail. Audio mp3 ngay dưới."""
    inner = [f'<h1 class="sr-only">{_esc(title)}</h1>']
    vid = _yt_id(youtube_url)
    if vid:
        inner.append(
            f'<div class="video-embed"><iframe src="https://www.youtube.com/embed/{vid}" '
            f'title="{_esc(title)}" loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; '
            f'gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>')
    elif cover_uri:
        inner.append(f'<div class="cover-art"><img src="{cover_uri}" alt="{_esc(title)}"></div>')
    if audio_src:
        inner.append(
            f'<div class="audio-embed"><span class="ic">🎧</span>'
            f'<audio controls preload="none" src="{_esc(audio_src)}"></audio></div>')
    return '<section class="media cover">' + "".join(inner) + '</section>'


def build_html_full(md_text, meta, infographic_png, youtube_url="", audio_src=""):
    title = _title(md_text, meta)
    pillar = (meta.get("pillar") or "").strip().lower()
    badge = PILLAR_LABEL.get(pillar, meta.get("pillar") or "COMPA Class")
    angle = meta.get("angle", "") or title
    body = md_to_html(md_text)
    img_uri = _img_data_uri(infographic_png)
    # Cover ở ĐẦU trang = video (đã có tiêu đề+ảnh) hoặc fallback ảnh thumbnail. Bỏ hero trùng lặp.
    media = _cover_block(title, youtube_url or meta.get("youtube_url", ""), audio_src, img_uri)
    # --- Open Graph: can URL TUYET DOI. Anh nhung data-URI khong dung duoc cho og:image
    # (Facebook phai tai duoc anh qua HTTP), nen tro toi cover .jpg nam canh bai tren Pages.
    # Quy uoc da xac minh tren atlas that: <slug>.html / <slug>.jpg / <slug>.mp3 cung thu muc.
    site = os.environ.get("ATLAS_BASE_URL", "https://ducnguyen.vn/atlas").rstrip("/")
    cat  = (meta.get("category") or PILLAR_CAT.get(pillar, "ai")).strip()
    slug = (meta.get("slug") or "").strip()
    page_url = f"{site}/content/{cat}/{slug}.html" if slug else site
    og_image = f"{site}/content/{cat}/{slug}.jpg" if slug else ""
    return _TEMPLATE.format(
        title=_esc(title), desc=_esc(angle), badge=_esc(badge), angle=_esc(angle),
        hero_cls="", hero_img="", media=media, body=body,
        page_url=_esc(page_url), og_image=_esc(og_image),
        author=_esc(os.environ.get("ATLAS_AUTHOR", "Nguyen Quang Duc")),
        site_name=_esc(os.environ.get("ATLAS_SITE_NAME", "Hoc cung Tobi")),
        published=_esc(meta.get("schedule_date") or meta.get("published_date") or ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description="blog.md + meta + infographic → atlas.html self-contained")
    ap.add_argument("--blog-md", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--infographic", default="")
    ap.add_argument("--youtube-url", default="", help="link YouTube để nhúng iframe (hoặc lấy từ meta.youtube_url)")
    ap.add_argument("--audio-src", default="", help="đường dẫn tương đối tới mp3 trong atlas (vd <slug>.mp3)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    md_text = _read(args.blog_md)
    with open(args.meta, encoding="utf-8-sig") as f:
        meta = json.load(f)

    html = build_html_full(md_text, meta, args.infographic, args.youtube_url, args.audio_src)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    pillar = (meta.get("pillar") or "").strip().lower()
    cat = meta.get("category") or PILLAR_CAT.get(pillar, "ai")
    print(json.dumps({"out": os.path.abspath(args.out), "category": cat,
                      "slug": meta.get("slug", "")}, ensure_ascii=False, indent=2))
    print(f"OK {os.path.abspath(args.out)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
