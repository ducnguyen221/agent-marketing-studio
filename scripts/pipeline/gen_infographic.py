# -*- coding: utf-8 -*-
r"""gen_infographic.py — meta.json + blog.md → thumbnail.png (ảnh bìa landscape).

Dựng 1 HTML cover on-brand (dark theme khớp atlas + style ai-news/compaclass,
gradient xanh→teal, mark có icon cuốn sách mở), khổ ngang 1280x720. Render PNG bằng Chrome headless.
Nếu Chrome lỗi/không có → fallback vẽ bằng Pillow (title + bullet).

CLI (theo PIPELINE_CONTRACT):
  python gen_infographic.py --meta meta.json --blog-md F --out FOLDER\infographic.png
→ in dòng cuối `OK <abs_path png>`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

W, H = 1280, 720   # cover landscape 16:9 (kiểu hero compaclass + thumbnail YouTube)

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("PROGRAMFILES", ""), r"Microsoft\Edge\Application\msedge.exe"),
]


# ================================================================ trích nội dung

def _read(path, optional=False):
    if not path or not os.path.isfile(path):
        if optional:
            return ""
        raise FileNotFoundError(f"Không thấy file: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _strip_md(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", s)
    return s.strip()


def extract_points(md_text, n=5):
    """Lấy 3-5 ý chính: ưu tiên các H2/H3, rồi bullet, rồi câu đầu đoạn."""
    lines = md_text.replace("\r\n", "\n").split("\n")
    heads, bullets = [], []
    for ln in lines:
        s = ln.strip()
        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if m:
            t = _strip_md(m.group(2))
            if t and t.lower() not in ("mở đầu", "kết luận", "intro", "outro"):
                heads.append(t)
            continue
        mb = re.match(r"^[-*+]\s+(.*)$", s)
        if mb:
            bullets.append(_strip_md(mb.group(1)))
    pts = heads[:n] if heads else bullets[:n]
    if len(pts) < 3:
        pts += bullets[: (n - len(pts))]
    # rút gọn để khít infographic
    out = []
    for p in pts[:n]:
        if len(p) > 80:
            p = p[:80].rsplit(" ", 1)[0] + "…"
        out.append(p)
    return out or ["(chưa có ý chính)"]


def extract_title(md_text, meta):
    for ln in md_text.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^#\s+(.*)$", ln.strip())
        if m:
            return _strip_md(m.group(1))
    return meta.get("title", "Học cùng Tobi")


# ================================================================ HTML on-brand

_PILLAR_LABEL = {"powerbi": "Power BI", "fabric": "Microsoft Fabric",
                 "ai-agent": "AI Agent", "career": "Sự nghiệp Data"}


def build_html(title, points, meta):
    """Cover landscape kiểu hero compaclass: gradient xanh dương→teal, hình khối/network
    trừu tượng, tiêu đề tích hợp + subtitle (angle). KHÔNG list đánh số."""
    pillar = (meta.get("pillar") or "").strip().lower()
    badge = _PILLAR_LABEL.get(pillar, meta.get("pillar") or "COMPA Class")
    subtitle = _strip_md(meta.get("angle") or (points[0] if points else ""))
    if len(subtitle) > 96:
        subtitle = subtitle[:96].rsplit(" ", 1)[0] + "…"
    tlen = len(title)
    tsize = 92 if tlen <= 22 else (78 if tlen <= 40 else (66 if tlen <= 60 else 54))
    return f"""<!doctype html><html lang="vi"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,"Segoe UI",Arial,sans-serif}}
:root{{--ac1:#38BDF8;--ac2:#2DD4BF;--tx:#F0F4FA;--mut:#9FB2C6}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
#root{{width:{W}px;height:{H}px;position:relative;color:var(--tx);
 background:radial-gradient(1100px 680px at 76% 6%,#16243e 0%,#0a0f1a 56%,#070a12 100%)}}
.grid{{position:absolute;inset:-100px;opacity:.22;z-index:0;
 background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);
 background-size:70px 70px}}
.orb{{position:absolute;border-radius:50%;filter:blur(70px);opacity:.20;z-index:0}}
.o1{{width:440px;height:440px;left:-90px;top:70px;background:var(--ac1)}}
.o2{{width:400px;height:400px;right:-80px;bottom:-70px;background:var(--ac2)}}
.brand{{position:absolute;top:42px;left:64px;display:flex;align-items:center;gap:12px;z-index:6}}
.mark{{width:40px;height:40px;border-radius:11px;background:linear-gradient(135deg,var(--ac1),#2563eb);box-shadow:0 0 18px rgba(56,189,248,.5);display:flex;align-items:center;justify-content:center}}
.mark svg{{width:22px;height:22px}}
.brand .n{{font-size:23px;font-weight:800}}.brand .n span{{color:var(--ac1)}}
.cover{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 120px;z-index:4}}
.kick{{display:inline-flex;align-items:center;font-size:18px;font-weight:700;letter-spacing:1px;
 color:var(--ac1);background:rgba(56,189,248,.09);border:1px solid rgba(56,189,248,.4);
 border-radius:999px;padding:9px 24px;text-transform:uppercase;margin-bottom:30px}}
h1{{font-size:{tsize}px;font-weight:900;letter-spacing:-1px;line-height:1.07;max-width:1060px;
 text-shadow:0 6px 34px rgba(0,0,0,.45)}}
.sub{{font-size:29px;line-height:1.4;color:var(--mut);margin-top:26px;max-width:860px}}
.bar{{width:120px;height:5px;border-radius:3px;margin-top:34px;background:linear-gradient(90deg,var(--ac1),var(--ac2))}}
.foot{{position:absolute;z-index:6;bottom:36px;left:0;right:0;text-align:center;color:#5f7790;font-size:19px}}
</style></head><body>
<div id="root">
 <div class="grid"></div><div class="orb o1"></div><div class="orb o2"></div>
 <div class="brand"><span class="mark"><svg viewBox="0 0 576 512" fill="#fff"><path d="M249.6 471.5c10.8 3.8 22.4-4.1 22.4-15.5V78.6c0-4.2-1.6-8.4-5-11C247.4 52 202.4 32 144 32C93.5 32 46.3 45.3 18.1 56.1C6.8 60.5 0 71.7 0 83.8V454.1c0 11.9 12.8 20.2 24.1 16.5C55.6 460.1 105.5 448 144 448c33.9 0 79 14 105.6 23.5zm76.8 0C353 462 398.1 448 432 448c38.5 0 88.4 12.1 119.9 22.6c11.3 3.8 24.1-4.6 24.1-16.5V83.8c0-12.1-6.8-23.3-18.1-27.6C529.7 45.3 482.5 32 432 32c-58.4 0-103.4 20-123 35.6c-3.3 2.6-5 6.8-5 11V456c0 11.4 11.7 19.3 22.4 15.5z"/></svg></span><div class="n">Học cùng <span>Tobi</span></div></div>
 <div class="cover">
  <div class="kick">{_esc(badge)}</div>
  <h1>{_esc(title)}</h1>
  <div class="sub">{_esc(subtitle)}</div>
  <div class="bar"></div>
 </div>
 <div class="foot">COMPA Class · ducnguyen.vn/atlas</div>
</div>
</body></html>"""


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ================================================================ render Chrome

def _find_chrome():
    for c in CHROME_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    found = shutil.which("chrome") or shutil.which("msedge")
    return found


def render_chrome(html, out_png):
    """Render HTML→PNG bằng Chrome headless. Trả True nếu thành công."""
    chrome = _find_chrome()
    if not chrome:
        print("[infographic] Chrome/Edge không tìm thấy → fallback Pillow", file=sys.stderr)
        return False
    tmpdir = tempfile.mkdtemp(prefix="tobi_infg_")
    html_path = os.path.join(tmpdir, "infographic.html")
    with open(html_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           f"--window-size={W},{H}",
           f"--screenshot={os.path.abspath(out_png)}",
           "--default-background-color=00000000",
           "file:///" + html_path.replace("\\", "/")]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except Exception as e:
        print(f"[infographic] Chrome lỗi ({type(e).__name__}: {e}) → fallback Pillow",
              file=sys.stderr)
        return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    ok = os.path.isfile(out_png) and os.path.getsize(out_png) > 1000
    if not ok:
        print("[infographic] Chrome không xuất PNG hợp lệ → fallback Pillow", file=sys.stderr)
    return ok


# ================================================================ fallback Pillow

def render_pillow(title, points, meta, out_png):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), (11, 16, 32))
    d = ImageDraw.Draw(img)

    def font(sz, bold=True):
        for name in (("segoeuib.ttf" if bold else "segoeui.ttf"),
                     "arialbd.ttf" if bold else "arial.ttf"):
            try:
                return ImageFont.truetype(name, sz)
            except OSError:
                continue
        return ImageFont.load_default()

    # accent bar
    d.rectangle([0, 0, W, 14], fill=(124, 131, 255))
    pad = 80
    y = 90
    # brand
    d.rounded_rectangle([pad, y, pad + 56, y + 56], 16, fill=(124, 131, 255))
    d.text((pad + 74, y + 8), "Học cùng Tobi", font=font(34), fill=(232, 236, 255))
    y += 110
    # badge
    badge = _PILLAR_LABEL.get((meta.get("pillar") or "").lower(), meta.get("pillar") or "COMPA Class")
    d.text((pad, y), badge.upper(), font=font(26), fill=(165, 172, 255))
    y += 60
    # title (wrap)
    for line in _wrap(d, title, font(60), W - 2 * pad):
        d.text((pad, y), line, font=font(60), fill=(232, 236, 255))
        y += 74
    y += 40
    # points
    for i, p in enumerate(points, 1):
        d.text((pad, y), f"{i:02d}", font=font(40), fill=(124, 131, 255))
        ty = y
        for line in _wrap(d, p, font(32, bold=False), W - 2 * pad - 90):
            d.text((pad + 90, ty), line, font=font(32, bold=False), fill=(200, 205, 230))
            ty += 42
        y = max(ty, y + 56) + 22
    # footer
    d.line([pad, H - 90, W - pad, H - 90], fill=(31, 38, 84), width=2)
    d.text((pad, H - 70), "COMPA Class · KPIM Academy", font=font(24, bold=False), fill=(107, 117, 168))
    d.text((W - pad - 220, H - 70), "ducnguyen.vn", font=font(24), fill=(165, 172, 255))

    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    img.save(out_png)
    return out_png


def _wrap(draw, text, font, maxw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


# ================================================================ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="meta + blog.md → infographic.png (dọc, on-brand)")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--blog-md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--force-pillow", action="store_true", help="bỏ qua Chrome, dùng Pillow")
    args = ap.parse_args(argv)

    with open(args.meta, encoding="utf-8-sig") as f:
        meta = json.load(f)
    md_text = _read(args.blog_md, optional=True)
    title = extract_title(md_text, meta)
    points = extract_points(md_text, n=5)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)

    used = "pillow"
    if not args.force_pillow:
        html = build_html(title, points, meta)
        if render_chrome(html, args.out):
            used = "chrome"
    if used != "chrome":
        render_pillow(title, points, meta, args.out)

    print(json.dumps({"out": os.path.abspath(args.out), "renderer": used,
                      "title": title, "points": points},
                     ensure_ascii=False, indent=2))
    print(f"OK {os.path.abspath(args.out)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
