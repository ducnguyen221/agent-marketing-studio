#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""22 cổng đếm được cho một bài blog. Vào: thư mục bài. Ra: gates.json + JSON ra stdout.

LUẬT PHÁT NGÔN — quan trọng hơn bản thân các con số:
Cổng chỉ được nói **cái nó đo được**, không được suy ra hậu quả.
  Đúng : "fb_post.txt có 2 URL trong thân bài (dòng 1, dòng 7); luật hiện hành = 0"
  Sai  : "bài này sẽ bị Facebook bóp reach"  — cổng không đo được reach.
Lý do: một cổng đoán sai nguyên nhân sẽ đẩy người sửa đi nhầm đường, và tệ hơn, làm người
ta mất tin vào toàn bộ cổng còn lại.

BA TRẠNG THÁI, không phải hai:
  xanh   — đo được, trong ngưỡng
  đỏ     — đo được, ngoài ngưỡng  (chan = chặn publish · canh_bao = ghi nhận, không chặn)
  thiếu  — KHÔNG đo được vì thiếu đầu vào
"thiếu" tuyệt đối không được coi là "xanh". Một bài không có video mà cổng video báo xanh
thì cổng đó đang nói dối. Ngược lại cũng không tự động chặn: bài chưa dựng video thì thiếu
video là đúng trạng thái của nó. Người đọc báo cáo phải thấy rõ 3 nhóm tách bạch.

Ngưỡng lấy từ fixtures/baseline/blog_baseline.md (3 bài thật), không lấy từ cảm giác.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_format as FF  # noqa: E402

CHAN, CANH_BAO = "chan", "canh_bao"

_URL = re.compile(r"https?://[^\s)>\]\"']+", re.I)
_H2 = re.compile(r"^##\s+\S", re.M)
_BANG = re.compile(r"^\s*\|.*\|\s*$", re.M)
_SO_THU_TU = re.compile(r"^\s*\d+\.\s+\S", re.M)
# Callout = dòng trích dẫn mở đầu bằng emoji. Cố ý KHÔNG quét cả Unicode: ký tự toán học
# đậm (U+1D400…) cũng nằm ngoài BMP và sẽ bị đếm nhầm là emoji.
_CALLOUT = re.compile("^>\\s*[\U0001F300-\U0001FAFF←-➿⬀-⯿]", re.M)
_GOC_NHIN = re.compile(r"^>\s*\*\*Góc nhìn:", re.M)
_THEO_NGUON = re.compile(r"\bTheo\s+(?!mình\b|tôi\b)[A-ZĐÀ-Ỹ]", re.U)
_THEO_MINH = re.compile(r"\bTheo\s+(?:mình|tôi)\b|\bmình\s+(?:nghĩ|cho rằng)\b", re.I | re.U)
_KIEM_CHUNG = re.compile(r"\[KIỂM CHỨNG\]")
_OG = re.compile(r'property\s*=\s*"og:', re.I)

# Tên công cụ nội bộ không được lộ ra bản công khai (G21).
TOOL_NOI_BO = ["omnivoice", "hyperframes", "claude code", "codex", "antigravity",
               "opcos", "giọng ai", "text-to-speech"]
TEN_TO_CHUC = re.compile(r"KPIM|COMPA|Tobi", re.I)

# Tên file bản công khai — thứ thật sự đến tay người đọc.
FILE_CONG_KHAI = ("blog.md", "fb_post.txt", "fb_comment.txt",
                  "youtube_desc.txt", "fb_desc.txt", "atlas.html")


def _doc(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def _tu(s: str) -> int:
    return len(s.split())


def _thoi_luong(p: Path) -> float | None:
    """Độ dài media bằng ffprobe. Không có ffprobe -> None (thiếu), KHÔNG phải 0."""
    ff = os.environ.get("FFPROBE") or "ffprobe"
    try:
        ra = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=nw=1:nk=1", str(p)],
                            capture_output=True, text=True, timeout=60)
        return float(ra.stdout.strip()) if ra.returncode == 0 and ra.stdout.strip() else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


class SoKetQua:
    """Sổ ghi kết quả. Mỗi dòng tự mang đủ: đo được gì, luật là gì, đạt hay không."""

    def __init__(self):
        self.rows: list[dict] = []

    def do(self, ma, ten, gia_tri, luat, dat, muc=CHAN, ghi_chu=""):
        self.rows.append({"ma": ma, "cong": ten, "do_duoc": gia_tri, "luat": luat,
                          "trang_thai": "xanh" if dat else "do",
                          "muc": "" if dat else muc, "ghi_chu": ghi_chu})

    def thieu(self, ma, ten, vi_sao):
        self.rows.append({"ma": ma, "cong": ten, "do_duoc": None, "luat": "—",
                          "trang_thai": "thieu", "muc": "", "ghi_chu": vi_sao})


def chay(thu_muc: Path, home_domain: str, loai: str = "full") -> dict:
    d = thu_muc
    s = SoKetQua()

    # ---------------------------------------------------------------- blog.md
    blog = _doc(d / "blog.md")
    if blog is None:
        for ma, ten in [("G01", "Độ dài blog"), ("G02", "Số H2"), ("G03", "Bảng/list"),
                        ("G04", "Callout"), ("G05", "Nguồn ngoài"), ("G06", "Khối chính kiến"),
                        ("G07", "Fact vs opinion"), ("G08", "[KIỂM CHỨNG] còn mở")]:
            s.thieu(ma, ten, "không có blog.md")
    else:
        n = _tu(blog)
        s.do("G01", "Độ dài blog (từ)", n, "2500-4000", 2500 <= n <= 4000)
        h2 = len(_H2.findall(blog))
        s.do("G02", "Số H2", h2, "6-12", 6 <= h2 <= 12)
        bang = len(_BANG.findall(blog)) + len(_SO_THU_TU.findall(blog))
        s.do("G03", "Bảng hoặc danh sách đánh số", bang, ">=1", bang >= 1)
        co = len(_CALLOUT.findall(blog))
        s.do("G04", "Callout emoji", co, "3-8", 3 <= co <= 8, CANH_BAO)
        ngoai = sorted({u for u in _URL.findall(blog) if home_domain not in u})
        s.do("G05", "Nguồn ngoài (domain khác)", len(ngoai), "3-7", 3 <= len(ngoai) <= 7,
             ghi_chu="; ".join(ngoai[:6]))
        gn = len(_GOC_NHIN.findall(blog))
        s.do("G06", "Khối > **Góc nhìn:**", gn, ">=1", gn >= 1)
        tn, tm = len(_THEO_NGUON.findall(blog)), len(_THEO_MINH.findall(blog))
        s.do("G07", "Dẫn nguồn / nêu ý riêng", f"{tn} / {tm}", "mỗi loại >=1",
             tn >= 1 and tm >= 1, CANH_BAO)
        kc = len(_KIEM_CHUNG.findall(blog))
        s.do("G08", "[KIỂM CHỨNG] còn mở", kc, "= 0", kc == 0)

    # ---------------------------------------------------------------- facebook
    fb = _doc(d / "fb_post.txt")
    cmt = _doc(d / "fb_comment.txt") or ""
    if fb is None:
        for ma, ten in [("G09", "URL trong thân post"), ("G10", "Độ dài post"),
                        ("G11", "Ký tự Unicode bold"), ("G12", "Markdown literal"),
                        ("G13", "Hashtag"), ("G14", "Comment đầu")]:
            s.thieu(ma, ten, "không có fb_post.txt")
    else:
        m = FF.check(fb, cmt)
        s.do("G09", "URL trong thân post", m["so_url_than_bai"], "= 0",
             m["so_url_than_bai"] == 0, ghi_chu="; ".join(m["url_than_bai"]))
        s.do("G10", "Độ dài post (ký tự)", m["so_ky_tu"], "4000-7500",
             4000 <= m["so_ky_tu"] <= 7500, CANH_BAO)
        s.do("G11", "Ký tự Unicode bold", m["so_ky_tu_bold"], "> 0", m["so_ky_tu_bold"] > 0)
        s.do("G12", "Markdown literal", m["markdown_literal"], "= 0",
             m["markdown_literal"] == 0)
        s.do("G13", "Hashtag", m["so_hashtag"], "6-13", 6 <= m["so_hashtag"] <= 13)
        s.do("G14", "Comment đầu có link", m["so_url_comment"], ">=1 URL",
             m["so_url_comment"] >= 1,
             ghi_chu="" if m["co_comment"] else "không thấy fb_comment.txt lẫn neo ### comment_1")

    # ---------------------------------------------------------------- audio / video
    pod = _doc(d / "podcast.txt")
    if pod is None:
        s.thieu("G15", "Độ dài podcast", "không có podcast.txt")
    else:
        n = _tu(pod)
        s.do("G15", "Độ dài podcast (từ)", n, "750-1000", 750 <= n <= 1000, CANH_BAO,
             ghi_chu=f"~{n / 3.8:.0f}s khi đọc ở 3,8 từ/giây (đo thật, xem baseline)")

    da, dv = _thoi_luong(d / "audio.mp3"), _thoi_luong(d / "video.mp4")
    if da is None or dv is None:
        thieu_gi = ", ".join(x for x, v in (("audio.mp3", da), ("video.mp4", dv)) if v is None)
        s.thieu("G16", "Video khớp audio", f"thiếu {thieu_gi} hoặc không gọi được ffprobe")
    else:
        s.do("G16", "|video - audio| (giây)", round(abs(dv - da), 2), "<=1", abs(dv - da) <= 1.0)

    sc = _doc(d / "scenes.json")
    if sc is None:
        s.thieu("G17", "Số scene", "không có scenes.json")
    else:
        try:
            js = json.loads(sc)
            arr = js if isinstance(js, list) else js.get("scenes", [])
            can = 8 if loai == "full" else 4
            s.do("G17", "Số scene", len(arr), f"= {can} ({loai})", len(arr) == can)
        except json.JSONDecodeError as e:
            s.do("G17", "Số scene", f"JSON hỏng: {e}", "đọc được", False)

    # ---------------------------------------------------------------- trang web
    html = _doc(d / "atlas.html")
    if html is None:
        s.thieu("G18", "Thẻ Open Graph", "không có atlas.html")
    else:
        og = len(_OG.findall(html))
        s.do("G18", "Thẻ og:", og, ">=6", og >= 6)

    # ---------------------------------------------------------------- ảnh Facebook
    anh, prompt = (d / "fb_image.png").exists(), (d / "fb_image.prompt.txt").exists()
    s.do("G19", "Ảnh FB + sidecar prompt", f"png={anh} prompt={prompt}", "cả hai",
         anh and prompt,
         ghi_chu="ảnh sinh bằng model KHÔNG tái lập - mất prompt là mất cách dựng lại")

    # ---------------------------------------------------------------- sổ continuity
    cont = _doc(d / "continuity.json")
    if cont is None:
        s.thieu("G20", "Bản ghi continuity", "không có continuity.json")
    else:
        try:
            c = json.loads(cont)
            tt = _tu(str(c.get("summary", "")))
            kt = len(c.get("key_terms_explained", []) or [])
            s.do("G20", "Continuity (tóm tắt từ / key-term)", f"{tt} / {kt}",
                 "<=60 va >=3", tt <= 60 and kt >= 3)
        except json.JSONDecodeError as e:
            s.do("G20", "Bản ghi continuity", f"JSON hỏng: {e}", "đọc được", False)

    # ---------------------------------------------------------------- lộ lọt
    cong_khai = {}
    for ten in FILE_CONG_KHAI:
        t = _doc(d / ten)
        if t:
            cong_khai[ten] = t
    if not cong_khai:
        s.thieu("G21", "Tên công cụ nội bộ", "chưa có file công khai nào để quét")
        s.thieu("G22", "Tên tổ chức trong bản công khai", "chưa có file công khai nào để quét")
    else:
        hit = [f"{ten}:{t.lower().count(x)}x'{x}'" for ten, t in cong_khai.items()
               for x in TOOL_NOI_BO if x in t.lower()]
        s.do("G21", "Tên công cụ nội bộ", len(hit), "= 0", not hit, ghi_chu="; ".join(hit[:6]))
        hit2 = [ten for ten, t in cong_khai.items() if TEN_TO_CHUC.search(t)]
        s.do("G22", "Tên tổ chức trong bản công khai", len(hit2), "= 0 nếu bài sẽ vào repo",
             not hit2, CANH_BAO,
             ghi_chu="; ".join(hit2) + " - bài đăng kênh nhà thì đây là bình thường"
             if hit2 else "")

    do_chan = [r for r in s.rows if r["trang_thai"] == "do" and r["muc"] == CHAN]
    return {
        "thu_muc": str(d),
        "tong": len(s.rows),
        "xanh": sum(1 for r in s.rows if r["trang_thai"] == "xanh"),
        "do_chan": len(do_chan),
        "do_canh_bao": sum(1 for r in s.rows if r["trang_thai"] == "do" and r["muc"] == CANH_BAO),
        "thieu": sum(1 for r in s.rows if r["trang_thai"] == "thieu"),
        "ket_luan": "do" if do_chan else "xanh",
        "cong": s.rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="22 cổng đếm được cho một bài blog.")
    ap.add_argument("thu_muc", help="thư mục bài (chứa blog.md, fb_post.txt...)")
    ap.add_argument("--home-domain", default=None,
                    help="domain nhà, để loại khỏi phép đếm nguồn ngoài")
    ap.add_argument("--loai", choices=["full", "short"], default="full")
    ap.add_argument("--json-only", action="store_true", help="chỉ in JSON, không in bảng")
    a = ap.parse_args(argv)

    d = Path(a.thu_muc)
    if not d.is_dir():
        sys.stderr.write(f"không phải thư mục: {d}\n")
        return 2

    home = a.home_domain or re.sub(r"^https?://([^/]+).*$", r"\1",
                                   os.environ.get("ATLAS_BASE_URL", "https://ducnguyen.vn"))
    kq = chay(d, home, a.loai)
    (d / "gates.json").write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.json_only:
        sys.stdout.write(json.dumps(kq, ensure_ascii=False, indent=2) + "\n")
    else:
        nhan = {"xanh": "OK  ", "do": "DO  ", "thieu": "--  "}
        for r in kq["cong"]:
            muc = f" [{r['muc']}]" if r["muc"] else ""
            gc = f"   {r['ghi_chu']}" if r["ghi_chu"] else ""
            sys.stdout.write(f"{nhan[r['trang_thai']]}{r['ma']} {r['cong']:<36} "
                             f"= {str(r['do_duoc']):<13} luật {r['luat']}{muc}{gc}\n")
        sys.stdout.write(f"\n  {kq['xanh']} xanh · {kq['do_chan']} đỏ-chặn · "
                         f"{kq['do_canh_bao']} đỏ-cảnh-báo · {kq['thieu']} thiếu "
                         f"(trên {kq['tong']} cổng)\n  -> gates.json\n")
    return 1 if kq["ket_luan"] == "do" else 0


if __name__ == "__main__":
    raise SystemExit(main())
