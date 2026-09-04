# -*- coding: utf-8 -*-
r"""make_podcast_video.py (v2) — Video = AUDIO PODCAST + slide xen kẽ ẢNH THẬT & INFOGRAPHIC.

- Lồng thẳng audio.mp3 (podcast my-voice), KHÔNG sinh narration mới.
- Slide xen kẽ: ~50% ẢNH THẬT (tải từ Openverse — CC, theo keyword, có credit) + ~50% INFOGRAPHIC/SmartArt
  (card on-brand style ai-news: Inter, near-black, grid+orb, accent cyan/teal).
- Slide đầu = thumbnail.png (hiện tiêu đề blog).
- Chuyển cảnh có XFADE (thấy rõ khác biệt khi sang slide).
Style tham khảo ai-news/data-news. Font Inter.

scenes.json item:
  infographic: {"kind":"concept|versus|list|closing","kick":"...","title":"...","lines":[...],"weight":1.0}
  ảnh thật:    {"kind":"image","kick":"...","caption":"...","img_query":"keyword en","weight":1.0}
  cover ảnh:   {"kind":"image","src":"thumbnail.png","raw":true,"weight":1.0}

CLI: python make_podcast_video.py --audio A\audio.mp3 --scenes scenes.json --meta meta.json
       --out A\video.mp4 [--size 1280x720] [--no-images]
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile, urllib.parse, urllib.request

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
]
FF_DIR = r"C:\Users\DucNguyen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
UA = "Mozilla/5.0 tobi-pipeline"
OPENVERSE = "https://api.openverse.org/v1/images/"


def _ff(name):
    p = os.path.join(FF_DIR, name + ".exe")
    return p if os.path.isfile(p) else (shutil.which(name) or name)


def _find_chrome():
    for c in CHROME_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    return shutil.which("chrome") or shutil.which("msedge")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def audio_duration(path):
    out = subprocess.run([_ff("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except Exception:
        return 0.0


# --------------------------------------------------------- Openverse ảnh thật

def fetch_image(query, out_png, want_w=1280):
    """Tải 1 ảnh CC (commercial) từ Openverse theo keyword. Trả (path, credit) hoặc (None, '')."""
    url = OPENVERSE + "?" + urllib.parse.urlencode(
        {"q": query, "page_size": 5, "license_type": "commercial", "mature": "false"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except Exception as e:
        print(f"[img] Openverse lỗi '{query}': {e}", file=sys.stderr)
        return None, ""
    for item in data.get("results", []):
        src = item.get("url") or ""
        if not src.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
            continue
        try:
            req = urllib.request.Request(src, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                blob = r.read()
            if len(blob) < 8000:
                continue
            with open(out_png, "wb") as f:
                f.write(blob)
            creator = item.get("creator") or ""
            lic = (item.get("license") or "").upper()
            credit = f"Ảnh: {creator} · {lic}".strip(" ·")
            print(f"[img] OK '{query}' -> {creator} ({lic})")
            return out_png, credit
        except Exception:
            continue
    print(f"[img] Không tải được ảnh cho '{query}'", file=sys.stderr)
    return None, ""


# --------------------------------------------------------- HTML slides

_HEAD = """<!doctype html><html lang="vi"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,"Segoe UI",Arial,sans-serif}}
:root{{--ac1:#38BDF8;--ac2:#2DD4BF;--tx:#F0F4FA;--mut:#9FB2C6;--bd:#243244;--pan:#121A26}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
#root{{width:{W}px;height:{H}px;position:relative;color:var(--tx);
 background:radial-gradient(1100px 680px at 76% 6%,#16243e 0%,#0a0f1a 56%,#070a12 100%)}}
.grid{{position:absolute;inset:-100px;opacity:.22;z-index:0;
 background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);background-size:70px 70px}}
.orb{{position:absolute;border-radius:50%;filter:blur(70px);opacity:.20;z-index:0}}
.o1{{width:420px;height:420px;left:-90px;top:80px;background:var(--ac1)}}
.o2{{width:380px;height:380px;right:-70px;bottom:-60px;background:var(--ac2)}}
.brand{{position:absolute;top:40px;left:64px;display:flex;align-items:center;gap:12px;z-index:6}}
.mark{{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,var(--ac1),#2563eb);box-shadow:0 0 18px rgba(56,189,248,.5);display:flex;align-items:center;justify-content:center}}
.mark svg{{width:21px;height:21px}}
.brand .n{{font-size:22px;font-weight:800}}.brand .n span{{color:var(--ac1)}}
.site{{position:absolute;bottom:34px;left:0;right:0;text-align:center;color:#5f7790;font-size:18px;z-index:6}}
.idx{{position:absolute;right:54px;bottom:30px;font-size:104px;font-weight:900;color:rgba(56,189,248,.10);z-index:1;line-height:1}}
.kick,.chip{{display:inline-flex;align-items:center;font-size:18px;font-weight:700;letter-spacing:1px;
 color:var(--ac1);background:rgba(56,189,248,.09);border:1px solid rgba(56,189,248,.4);border-radius:999px;padding:8px 22px;text-transform:uppercase}}
.cover{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 110px;z-index:4}}
.kc{{margin-bottom:30px}}
.cbig{{font-weight:900;letter-spacing:-1px;line-height:1.06;max-width:1080px;text-shadow:0 6px 34px rgba(0,0,0,.45)}}
.csub{{font-size:30px;color:var(--mut);margin-top:28px;max-width:880px;line-height:1.4}}
.cbar{{width:120px;height:5px;border-radius:3px;margin-top:36px;background:linear-gradient(90deg,var(--ac1),var(--ac2))}}
.quote{{font-size:38px;font-weight:800;line-height:1.28;margin-top:16px;max-width:980px;color:#fff}}
.sec{{position:absolute;left:64px;right:64px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;z-index:4}}
.sec .chip{{align-self:flex-start;margin-bottom:22px}}
.sec h1{{font-weight:900;line-height:1.12;letter-spacing:-.5px;margin-bottom:30px;max-width:1040px}}
.bul{{list-style:none;display:flex;flex-direction:column;gap:16px}}
.bul li{{position:relative;padding-left:38px;font-size:29px;font-weight:600;line-height:1.4;color:var(--tx);max-width:1000px}}
.bul li::before{{content:"";position:absolute;left:0;top:15px;width:22px;height:4px;border-radius:2px;background:linear-gradient(90deg,var(--ac1),var(--ac2))}}
.vs{{display:flex;align-items:stretch;gap:20px;max-width:1080px}}
.vcard{{flex:1;background:var(--pan);border:1px solid var(--bd);border-radius:18px;padding:26px 24px}}
.vcard.dl{{border-top:3px solid var(--ac1)}}.vcard.dr{{border-top:3px solid var(--ac2)}}
.vt{{font-size:26px;font-weight:600;line-height:1.42;color:var(--tx)}}
.vx{{align-self:center;font-size:28px;font-weight:900;color:var(--ac2)}}
/* image slide */
.photo{{position:absolute;inset:0;background-size:cover;background-position:center;z-index:0}}
.shade{{position:absolute;inset:0;z-index:1;
 background:linear-gradient(90deg,rgba(6,10,18,.92) 0%,rgba(6,10,18,.70) 38%,rgba(6,10,18,.20) 70%,rgba(6,10,18,.45) 100%)}}
.icap{{position:absolute;left:64px;right:360px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;z-index:4}}
.icap .chip{{align-self:flex-start;margin-bottom:22px}}
.icap h2{{font-size:60px;font-weight:900;line-height:1.1;letter-spacing:-.5px;text-shadow:0 6px 30px rgba(0,0,0,.6);max-width:760px}}
.credit{{position:absolute;right:24px;bottom:18px;font-size:14px;color:rgba(255,255,255,.55);z-index:5;
 background:rgba(0,0,0,.35);padding:4px 10px;border-radius:8px}}
</style></head><body><div id="root">"""

_TAIL = '<div class="site">COMPA Class · ducnguyen.vn/atlas</div></div></body></html>'


def infographic_html(scene, idx, W, H):
    kind = scene.get("kind", "concept")
    title = _esc(scene.get("title", ""))
    kick = _esc(scene.get("kick", "Vibe Coding"))
    lines = scene.get("lines", [])
    if kind in ("cover", "closing"):
        if kind == "cover":
            big = 118 if len(title) <= 28 else (98 if len(title) <= 46 else 80)
            sub = f'<div class="csub">{_esc(lines[0])}</div>' if lines else ""
            inner = f'<div class="kick kc">{kick}</div><div class="cbig" style="font-size:{big}px">{title}</div>{sub}<div class="cbar"></div>'
        else:
            big = 60 if len(title) <= 26 else 50
            ttl = f'<div class="cbig" style="font-size:{big}px">{title}</div>' if title else ""
            inner = ttl + "".join(f'<div class="quote">{_esc(x)}</div>' for x in lines) + '<div class="cbar"></div>'
        content = f'<div class="cover">{inner}</div>'
    else:
        if kind == "versus" and len(lines) >= 2:
            panel = (f'<div class="vs"><div class="vcard dl"><div class="vt">{_esc(lines[0])}</div></div>'
                     f'<div class="vx">vs</div><div class="vcard dr"><div class="vt">{_esc(lines[1])}</div></div></div>')
        else:
            panel = '<ul class="bul">' + "".join(f'<li>{_esc(x)}</li>' for x in lines) + '</ul>'
        hsize = 52 if len(title) <= 34 else 44
        content = f'<div class="sec"><div class="chip">{kick}</div><h1 style="font-size:{hsize}px">{title}</h1>{panel}</div>'
    head = _HEAD.format(W=W, H=H)
    deco = '<div class="grid"></div><div class="orb o1"></div><div class="orb o2"></div>'
    brand = '<div class="brand"><span class="mark"><svg viewBox="0 0 576 512" fill="#fff"><path d="M249.6 471.5c10.8 3.8 22.4-4.1 22.4-15.5V78.6c0-4.2-1.6-8.4-5-11C247.4 52 202.4 32 144 32C93.5 32 46.3 45.3 18.1 56.1C6.8 60.5 0 71.7 0 83.8V454.1c0 11.9 12.8 20.2 24.1 16.5C55.6 460.1 105.5 448 144 448c33.9 0 79 14 105.6 23.5zm76.8 0C353 462 398.1 448 432 448c38.5 0 88.4 12.1 119.9 22.6c11.3 3.8 24.1-4.6 24.1-16.5V83.8c0-12.1-6.8-23.3-18.1-27.6C529.7 45.3 482.5 32 432 32c-58.4 0-103.4 20-123 35.6c-3.3 2.6-5 6.8-5 11V456c0 11.4 11.7 19.3 22.4 15.5z"/></svg></span><div class="n">Học cùng <span>Tobi</span></div></div>'
    return head + deco + brand + f'<div class="idx">{idx:02d}</div>' + content + _TAIL


def image_html(scene, img_path, credit, idx, W, H):
    kick = _esc(scene.get("kick", ""))
    cap = _esc(scene.get("caption", scene.get("title", "")))
    head = _HEAD.format(W=W, H=H)
    fileurl = "file:///" + img_path.replace("\\", "/")
    brand = '<div class="brand"><span class="mark"><svg viewBox="0 0 576 512" fill="#fff"><path d="M249.6 471.5c10.8 3.8 22.4-4.1 22.4-15.5V78.6c0-4.2-1.6-8.4-5-11C247.4 52 202.4 32 144 32C93.5 32 46.3 45.3 18.1 56.1C6.8 60.5 0 71.7 0 83.8V454.1c0 11.9 12.8 20.2 24.1 16.5C55.6 460.1 105.5 448 144 448c33.9 0 79 14 105.6 23.5zm76.8 0C353 462 398.1 448 432 448c38.5 0 88.4 12.1 119.9 22.6c11.3 3.8 24.1-4.6 24.1-16.5V83.8c0-12.1-6.8-23.3-18.1-27.6C529.7 45.3 482.5 32 432 32c-58.4 0-103.4 20-123 35.6c-3.3 2.6-5 6.8-5 11V456c0 11.4 11.7 19.3 22.4 15.5z"/></svg></span><div class="n">Học cùng <span>Tobi</span></div></div>'
    cr = f'<div class="credit">{_esc(credit)}</div>' if credit else ""
    body = (f'<div class="photo" style="background-image:url(\'{fileurl}\')"></div><div class="shade"></div>'
            + brand
            + f'<div class="icap"><div class="chip">{kick}</div><h2>{cap}</h2></div>'
            + f'<div class="idx">{idx:02d}</div>' + cr)
    return head + body + _TAIL


def render_slide(html, out_png, W, H):
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError("Không tìm thấy Chrome")
    tmp = tempfile.mkdtemp(prefix="pv_")
    hp = os.path.join(tmp, "s.html")
    with open(hp, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           "--allow-file-access-from-files", "--force-device-scale-factor=1",
           f"--window-size={W},{H}", f"--screenshot={os.path.abspath(out_png)}",
           "file:///" + hp.replace("\\", "/")]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not (os.path.isfile(out_png) and os.path.getsize(out_png) > 1000):
        raise RuntimeError("Chrome không xuất PNG")


# --------------------------------------------------------- assemble (xfade)

def build_video(audio, scenes, out, base_dir, W, H, T=0.5, use_images=True):
    dur = audio_duration(audio)
    if dur <= 0:
        raise RuntimeError("Không đọc được thời lượng audio")
    work = tempfile.mkdtemp(prefix="pvbuild_")
    try:
        n = len(scenes)
        weights = [max(0.4, float(s.get("weight", 1.0))) for s in scenes]
        tw = sum(weights)
        # tổng clip = audio + (n-1)*T  (xfade ăn bớt T mỗi mối nối)
        total = dur + (n - 1) * T
        durs = [max(T + 1.2, total * w / tw) for w in weights]

        pngs = []
        for i, s in enumerate(scenes):
            p = os.path.join(work, f"s{i:02d}.png")
            kind = s.get("kind")
            if kind == "image":
                img = None
                credit = ""
                if s.get("src"):  # ảnh local sẵn (vd thumbnail)
                    src = s["src"]
                    if not os.path.isabs(src):
                        src = os.path.join(base_dir, src)
                    img = src if os.path.isfile(src) else None
                elif use_images and s.get("img_query"):
                    dl = os.path.join(work, f"img{i:02d}.jpg")
                    img, credit = fetch_image(s["img_query"], dl, W)
                if s.get("raw") and img:
                    # ảnh nguyên (vd thumbnail) — copy thẳng, scale ở ffmpeg
                    shutil.copyfile(img, p)
                elif img:
                    render_slide(image_html(s, img, credit, i + 1, W, H), p, W, H)
                else:  # fallback -> infographic nếu ảnh fail
                    s2 = dict(s); s2["kind"] = "concept"
                    s2.setdefault("title", s.get("caption", ""))
                    s2.setdefault("lines", [])
                    render_slide(infographic_html(s2, i + 1, W, H), p, W, H)
            else:
                render_slide(infographic_html(s, i + 1, W, H), p, W, H)
            pngs.append(p)

        # Chrome PNG có zlib stream làm ffmpeg lỗi "inflate -3" khi -loop -> convert sang JPG (không zlib).
        from PIL import Image
        frames_in = []
        for i, p in enumerate(pngs):
            jp = os.path.join(work, f"s{i:02d}.jpg")
            Image.open(p).convert("RGB").save(jp, "JPEG", quality=93)
            frames_in.append(jp)
        pngs = frames_in

        # PASS 1: mỗi JPG -> clip mp4 ngắn d_i (tránh lỗi png-in-xfade).
        clips = []
        for i, (p, d) in enumerate(zip(pngs, durs)):
            clip = os.path.join(work, f"c{i:02d}.mp4")
            # clip TĨNH (zoompan quá chậm); chuyển động/khác biệt đến từ xfade giữa slide.
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30,format=yuv420p"
            c1 = [_ff("ffmpeg"), "-y", "-loop", "1", "-t", f"{d:.3f}", "-i", p,
                  "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
                  "-tune", "stillimage", "-pix_fmt", "yuv420p", "-an", clip]
            r = subprocess.run(c1, capture_output=True, timeout=300)
            if r.returncode != 0 or not os.path.isfile(clip):
                raise RuntimeError(f"clip {i} lỗi: " + r.stderr.decode("utf-8", "ignore")[-500:])
            clips.append(clip)

        # PASS 2: xfade-chain các clip mp4 + audio
        cmd = [_ff("ffmpeg"), "-y"]
        for c in clips:
            cmd += ["-i", c]
        cmd += ["-i", audio]
        fc = [f"[{i}:v]setsar=1,fps=30[v{i}]" for i in range(n)]
        prev = "v0"
        acc = durs[0]
        for i in range(1, n):
            off = acc - T
            lbl = f"x{i}"
            fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={T}:offset={off:.3f}[{lbl}]")
            prev = lbl
            acc += durs[i] - T
        fc.append(f"[{prev}]fade=t=out:st={max(0,(dur-0.6)):.2f}:d=0.6[vout]")
        cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{n}:a",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                "-c:a", "aac", "-b:a", "160k", "-shortest", os.path.abspath(out)]
        r = subprocess.run(cmd, capture_output=True, timeout=1200)
        if r.returncode != 0:
            raise RuntimeError("ffmpeg xfade lỗi: " + r.stderr.decode("utf-8", "ignore")[-800:])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if not (os.path.isfile(out) and os.path.getsize(out) > 10000):
        raise RuntimeError("ffmpeg không tạo được video")
    return os.path.abspath(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--meta", required=False)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args(argv)
    W, H = (int(x) for x in a.size.lower().split("x"))
    with open(a.scenes, encoding="utf-8-sig") as f:
        scenes = json.load(f)
    base_dir = os.path.dirname(os.path.abspath(a.audio))
    out = build_video(a.audio, scenes, a.out, base_dir, W, H, use_images=not a.no_images)
    print(json.dumps({"out": out, "scenes": len(scenes)}, ensure_ascii=False))
    print(f"OK {out}")
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
