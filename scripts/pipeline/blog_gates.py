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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import post_paths as PP  # noqa: E402

CHAN, CANH_BAO = "chan", "canh_bao"

_URL = re.compile(r"https?://[^\s)>\]\"']+", re.I)
# URL TRẦN: Facebook tự biến "ducnguyen.vn/atlas/x" hay "www.abc.com" thành link, nên
# về mặt luật "thân bài 0 URL" chúng cũng là URL. Bản đầu chỉ bắt có scheme https:// nên
# bỏ link trần vào thân bài là qua được cổng G09.
_URL_TRAN = re.compile(r"(?<![\w/@.])(?:www\.[\w-]+|[\w-]+\.(?:vn|com|net|org|io|ai|dev))"
                       r"(?:\.[\w-]+)*/[^\s)>\]\"']*", re.I)
_H2 = re.compile(r"^##\s+\S", re.M)
_BANG = re.compile(r"^\s*\|.*\|\s*$", re.M)
_SO_THU_TU = re.compile(r"^\s*\d+\.\s+\S", re.M)
# Callout = dòng trích dẫn mở đầu bằng emoji. Cố ý KHÔNG quét cả Unicode: ký tự toán học
# đậm (U+1D400…) cũng nằm ngoài BMP và sẽ bị đếm nhầm là emoji.
_CALLOUT = re.compile("^>\\s*[\U0001F300-\U0001FAFF←-➿⬀-⯿]", re.M)
_GOC_NHIN = re.compile(r"^>\s*\*\*Góc nhìn:", re.M)
_THEO_NGUON = re.compile(r"\bTheo\s+(?!mình\b|tôi\b)[A-ZĐÀ-Ỹ]", re.U)
_THEO_MINH = re.compile(r"\bTheo\s+(?:mình|tôi)\b|\bmình\s+(?:nghĩ|cho rằng)\b", re.I | re.U)
# Bắt cả chữ thường và các biến thể. Bản đầu chỉ khớp đúng "[KIỂM CHỨNG]" hoa, nên
# "[kiểm chứng]", "[CẦN KIỂM]" hay "TODO:" lọt sạch — mà chúng cùng nghĩa: còn nợ.
_KIEM_CHUNG = re.compile(r"\[\s*(?:KIỂM\s*CHỨNG|CẦN\s*KIỂM|CHƯA\s*KIỂM)\s*\]|(?<!\w)TODO\s*:",
                         re.I | re.U)
_OG = re.compile(r'property\s*=\s*"og:', re.I)

# Tên công cụ nội bộ không được lộ ra bản công khai (G21).
TOOL_NOI_BO = ["omnivoice", "hyperframes", "claude code", "codex", "antigravity",
               "opcos", "giọng ai", "text-to-speech"]
TEN_TO_CHUC = re.compile(r"KPIM|COMPA|Tobi", re.I)

# Tên file bản công khai — thứ thật sự đến tay người đọc.
# Tên file lấy từ post_paths.LAYOUT — một nguồn sự thật cho cả pipeline.
FILE_CONG_KHAI = tuple(PP.LAYOUT[k] for k in PP.FILE_CONG_KHAI)


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


def chay(thu_muc: Path, home_domain: str, loai: str = "full",
         cho_phep: dict[str, str] | None = None) -> dict:
    """`cho_phep` = {needle: lý do} — MIỄN TRỪ CÓ GHI LÝ DO cho G21.

    Vì sao cần: danh sách needle của G21 so khớp chuỗi thô, nên nó không phân biệt được
    "công cụ sản xuất nội bộ của mình bị lộ" với "tên sản phẩm của hãng khác, đang là
    chủ đề của bài". Ca thật: một bài viết VỀ bản phát hành của OpenAI buộc phải nhắc
    tên công cụ lập trình của họ, và cổng chặn thẳng.

    Cách xử lý CỐ Ý không phải là nới danh sách needle — nới một lần là nới mãi, và lần
    sau lộ thật thì không ai bắt được. Thay vào đó: vẫn phát hiện, vẫn IN RA báo cáo,
    nhưng kèm lý do do người nêu và không chặn. Miễn trừ nào cũng để lại dấu trong
    gates.json — im lặng bỏ qua và miễn trừ có ghi lý do là hai chuyện khác nhau.
    """
    cho_phep = {k.lower(): v for k, v in (cho_phep or {}).items()}
    d = thu_muc
    s = SoKetQua()

    # ---------------------------------------------------------------- blog.md
    blog = _doc(PP.p(d, "blog"))
    if blog is None:
        for ma, ten in [("G01", "Độ dài blog"), ("G02", "Số H2"), ("G03", "Bảng/list"),
                        ("G04", "Callout"), ("G05", "Nguồn ngoài"), ("G06", "Khối chính kiến"),
                        ("G07", "Fact vs opinion"), ("G08", "[KIỂM CHỨNG] còn mở")]:
            s.thieu(ma, ten, f"không có {PP.LAYOUT['blog']}")
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
        # Không chỉ ĐẾM URL: đối chiếu với research.md. Đếm suông thì 6 đường dẫn bịa ra
        # cũng cho G05 xanh — mà cổng này tồn tại đúng để chặn việc bịa nguồn.
        # Không có research.md -> chỉ đếm được, và nói rõ là chỉ đếm được.
        nc = _doc(PP.p(d, "research"))
        if nc is None:
            s.do("G05", "Nguồn ngoài (chỉ đếm — không có research.md)", len(ngoai),
                 "3-7", 3 <= len(ngoai) <= 7,
                 ghi_chu="không đối chiếu được: thiếu research.md")
        else:
            # So theo host, không so nguyên URL: bài hay trích link sâu hơn bảng nguồn.
            def _host(u):
                return re.sub(r"^https?://(?:www\.)?([^/]+).*$", r"\1", u).lower()
            host_nguon = {_host(u) for u in _URL.findall(nc)}
            lac = sorted({u for u in ngoai if _host(u) not in host_nguon})
            s.do("G05", "Nguồn ngoài (có trong research.md)",
                 f"{len(ngoai)} nguồn, {len(lac)} lạc", "3-7 và không nguồn nào lạc",
                 3 <= len(ngoai) <= 7 and not lac,
                 ghi_chu=("URL không có trong research.md: " + "; ".join(lac[:4]))
                 if lac else "; ".join(ngoai[:5]))
        gn = len(_GOC_NHIN.findall(blog))
        # Đếm chữ THỰC SỰ có trong khối chính kiến. Bản đầu chỉ khớp dòng tiêu đề, nên
        # một khối rỗng hoàn toàn vẫn cho G06 xanh — tức cổng bảo đảm một thứ không tồn tại.
        tu_gn = 0
        for m_gn in _GOC_NHIN.finditer(blog):
            khoi = []
            for dong in blog[m_gn.start():].splitlines():
                if khoi and not dong.lstrip().startswith(">"):
                    break
                khoi.append(dong.lstrip("> ").strip())
            tu_gn = max(tu_gn, len(" ".join(khoi).split()) - 2)   # trừ "**Góc nhìn:**"
        s.do("G06", "Khối > **Góc nhìn:** (số từ)", f"{gn} khối / {tu_gn} từ",
             ">=1 khối và >=40 từ", gn >= 1 and tu_gn >= 40,
             ghi_chu="" if tu_gn >= 40 else "khối chính kiến quá ngắn hoặc rỗng")
        tn, tm = len(_THEO_NGUON.findall(blog)), len(_THEO_MINH.findall(blog))
        s.do("G07", "Dẫn nguồn / nêu ý riêng", f"{tn} / {tm}", "mỗi loại >=1",
             tn >= 1 and tm >= 1, CANH_BAO)
        kc = len(_KIEM_CHUNG.findall(blog))
        s.do("G08", "[KIỂM CHỨNG] còn mở", kc, "= 0", kc == 0)

    # ---------------------------------------------------------------- facebook
    fb = _doc(PP.p(d, "fb_post"))
    cmt = _doc(PP.p(d, "fb_comment")) or ""
    if fb is None:
        for ma, ten in [("G09", "URL trong thân post"), ("G10", "Độ dài post"),
                        ("G11", "Ký tự Unicode bold"), ("G12", "Markdown literal"),
                        ("G13", "Hashtag"), ("G14", "Comment đầu")]:
            s.thieu(ma, ten, f"không có {PP.LAYOUT['fb_post']}")
    else:
        m = FF.check(fb, cmt)
        tran = [u for u in _URL_TRAN.findall(fb.split(FF.MARKER_COMMENT)[0])]
        tong_url = m["so_url_than_bai"] + len(tran)
        s.do("G09", "URL trong thân post (kể cả link trần)", tong_url, "= 0",
             tong_url == 0, ghi_chu="; ".join(m["url_than_bai"] + tran[:3]))
        s.do("G10", "Độ dài post (ký tự)", m["so_ky_tu"], "4000-7500",
             4000 <= m["so_ky_tu"] <= 7500, CANH_BAO)
        # G11 hai tầng. Tầng 1: có chữ đậm không. Tầng 2: chữ đậm có GIỮ ĐƯỢC DẤU không.
        # Tầng 2 sinh ra vì bài AST-001 từng qua tầng 1 với 103 ký tự đậm mà cả 5 tiêu đề
        # đọc là "CAI THAT SU MOI KHONG PHAI DIEM SO" — người viết gõ tay chữ không dấu
        # thay vì gọi bold(). Cổng đếm số lượng thì không bao giờ thấy.
        mat_dau = (m["so_ky_tu_bold"] >= 20
                   and m["so_chu_co_dau_ngoai_bold"] >= 20
                   and m["so_dau_trong_bold"] == 0)
        if mat_dau:
            s.do("G11", "Ký tự Unicode bold",
                 f'{m["so_ky_tu_bold"]} đậm nhưng 0 dấu', "chữ đậm phải giữ dấu", False,
                 ghi_chu=f'phần thường có {m["so_chu_co_dau_ngoai_bold"]} chữ có dấu, '
                         f'phần đậm có 0 — nhiều khả năng gõ tay thay vì dùng '
                         f'fb_format.bold()')
        else:
            s.do("G11", "Ký tự Unicode bold", m["so_ky_tu_bold"], "> 0",
                 m["so_ky_tu_bold"] > 0,
                 ghi_chu=f'{m["so_dau_trong_bold"]} dấu trong vùng đậm'
                         if m["so_ky_tu_bold"] else "")
        s.do("G12", "Markdown literal", m["markdown_literal"], "= 0",
             m["markdown_literal"] == 0)
        s.do("G13", "Hashtag", m["so_hashtag"], "6-13", 6 <= m["so_hashtag"] <= 13)
        # Không chỉ đòi "có URL": đòi URL trỏ về NHÀ hoặc YouTube. Một comment dẫn sang
        # example.com vẫn thoả "có 1 URL" mà chẳng đưa ai về bài cả.
        url_cmt = _URL.findall(cmt)
        dung_dich = [u for u in url_cmt
                     if home_domain in u or "youtu" in u.lower()]
        s.do("G14", "Comment đầu có link về nhà/YouTube", len(dung_dich), ">=1",
             len(dung_dich) >= 1,
             ghi_chu=("không thấy fb_comment.txt lẫn neo ### comment_1"
                      if not m["co_comment"] else
                      f"có {len(url_cmt)} URL nhưng không URL nào về {home_domain}/YouTube"
                      if url_cmt and not dung_dich else ""))

    # ---------------------------------------------------------------- audio / video
    pod = _doc(PP.p(d, "podcast"))
    if pod is None:
        s.thieu("G15", "Độ dài podcast", f"không có {PP.LAYOUT['podcast']}")
    else:
        n = _tu(pod)
        s.do("G15", "Độ dài podcast (từ)", n, "750-1000", 750 <= n <= 1000, CANH_BAO,
             ghi_chu=f"~{n / 3.8:.0f}s khi đọc ở 3,8 từ/giây (đo thật, xem baseline)")

    da, dv = _thoi_luong(PP.p(d, "audio")), _thoi_luong(PP.p(d, "yt_video"))
    if da is None or dv is None:
        thieu_gi = ", ".join(x for x, v in (("audio.mp3", da), ("video.mp4", dv)) if v is None)
        s.thieu("G16", "Video khớp audio", f"thiếu {thieu_gi} hoặc không gọi được ffprobe")
    else:
        s.do("G16", "|video - audio| (giây)", round(abs(dv - da), 2), "<=1", abs(dv - da) <= 1.0)

    sc = _doc(PP.p(d, "scenes"))
    if sc is None:
        s.thieu("G17", "Số scene", f"không có {PP.LAYOUT['scenes']}")
    else:
        try:
            js = json.loads(sc)
            can = 8 if loai == "full" else 4
            if not isinstance(js, list):
                # make_podcast_video.py làm `scenes = json.load(f)` rồi lặp thẳng, nên nó đòi
                # MẢNG ở cấp cao nhất. Bọc trong {"scenes": [...]} thì nó lặp qua các KHOÁ,
                # gặp chuỗi và chết bằng "'str' object has no attribute 'get'".
                # Cổng từng chấp nhận cả hai dạng và báo xanh trong khi renderer không chạy
                # được — cổng dễ dãi hơn công cụ thật thì tệ hơn là không có cổng, vì nó
                # cấp một lời bảo đảm sai. Nay cổng đo đúng hợp đồng của renderer.
                s.do("G17", "Số scene", f"JSON là {type(js).__name__}, không phải mảng",
                     "mảng ở cấp cao nhất", False,
                     ghi_chu="renderer lặp thẳng trên JSON -> bọc trong {\"scenes\": [...]} sẽ vỡ")
            else:
                # Không chỉ ĐẾM. Scene rỗng {} vẫn qua phép đếm, rồi renderer dựng ra
                # slide trắng với nhãn mặc định của một dự án khác — video 8 cảnh trống
                # mà cổng báo xanh.
                HOP_LE = {"cover", "concept", "versus", "list", "image", "closing"}
                hong = [i for i, sc_ in enumerate(js)
                        if not isinstance(sc_, dict)
                        or sc_.get("kind") not in HOP_LE
                        or not (sc_.get("title") or sc_.get("lines")
                                or sc_.get("src") or sc_.get("img_query"))]
                # scene có "src" phải trỏ tới file CÓ THẬT. make_podcast_video phân giải
                # tương đối theo thư mục scenes.json; dời ảnh sang youtube/ mà quên sửa
                # src là cover rơi mất, video vẫn dựng ra và không ai báo.
                mat_src = [i for i, sc_ in enumerate(js)
                           if isinstance(sc_, dict) and sc_.get("src")
                           and not (d / sc_["src"]).exists()]
                s.do("G17", "Số scene (hình dạng + ảnh src có thật)",
                     f"{len(js)} scene, {len(hong)} thiếu nội dung, {len(mat_src)} mất ảnh src",
                     f"= {can} ({loai}), mọi scene có kind + nội dung, src tồn tại",
                     len(js) == can and not hong and not mat_src,
                     ghi_chu="; ".join(filter(None, [
                         f"scene rỗng/sai kind ở vị trí {hong[:5]}" if hong else "",
                         f"src không tồn tại ở vị trí {mat_src[:5]}" if mat_src else ""])))
        except json.JSONDecodeError as e:
            s.do("G17", "Số scene", f"JSON hỏng: {e}", "đọc được", False)

    # ---------------------------------------------------------------- trang web
    html = _doc(PP.p(d, "atlas_html"))
    if html is None:
        s.thieu("G18", "Thẻ Open Graph", f"không có {PP.LAYOUT['atlas_html']}")
    else:
        # Đếm thẻ KHÁC NHAU. Đếm tổng thì 6 lần og:title cũng ra 6 — mà bài vẫn không có
        # ảnh preview, tức mất đúng thứ cả cổng này sinh ra để bảo vệ.
        loai_og = set(re.findall(r'property\s*=\s*"og:([a-z_:]+)"', html, re.I))
        CAN_CO = {"title", "description", "image", "url", "type"}
        thieu_og = CAN_CO - loai_og
        s.do("G18", "Thẻ og: khác nhau", f"{len(loai_og)} loại",
             "đủ title/description/image/url/type", not thieu_og,
             ghi_chu=f"thiếu: {', '.join(sorted(thieu_og))}" if thieu_og else "")

    # ---------------------------------------------------------------- ảnh Facebook
    # Đọc KÍCH THƯỚC THẬT từ khối IHDR của PNG (8 byte tại offset 16) thay vì chỉ hỏi
    # "file có tồn tại không" — một ảnh 1x1 px cũng tồn tại. Và prompt rỗng thì cũng là
    # không có prompt: sidecar sinh ra để dựng lại được ảnh, rỗng thì dựng lại bằng gì.
    # infographic.png là tên chính thức từ 04/09: một ảnh vừa đăng Facebook vừa đặt đầu bài
    # blog, thay cho fb_image.png cũ (một nền + ba dòng chữ). Vẫn nhận tên cũ cho bài cũ.
    # KHÔNG giữ tương thích tên cũ (fb_image.png): "nới một lần là nới mãi" — cùng lý do
    # repo chọn --cho-phep thay vì nới danh sách needle của G21.
    f_anh, f_prompt = PP.p(d, "fb_image"), PP.p(d, "fb_prompt")
    kich_thuoc, prompt_len = None, 0
    if f_anh.exists():
        try:
            b = f_anh.read_bytes()[:24]
            # Chu ky PNG dung bang bytes([...]) chu khong viet literal: chuoi nay chua
            # ky tu dieu khien, ma moi tang cong cu tren duong di lai an mot lop escape
            # — da lam hong dung file nay mot lan.
            PNG_SIG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
            if len(b) >= 24 and b[:8] == PNG_SIG:
                kich_thuoc = (int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big"))
        except OSError:
            pass
    if f_prompt.exists():
        prompt_len = len((_doc(f_prompt) or "").strip())
    du_lon = bool(kich_thuoc) and kich_thuoc[0] >= 800 and kich_thuoc[1] >= 800
    s.do("G19", "Ảnh FB (kích thước) + sidecar prompt",
         f"{kich_thuoc or 'không có PNG'} · prompt {prompt_len} ký tự",
         ">=800x800 và prompt >=100 ký tự",
         du_lon and prompt_len >= 100,
         ghi_chu="ảnh sinh bằng model KHÔNG tái lập - mất prompt là mất cách dựng lại")

    # ---------------------------------------------------------------- sổ continuity
    cont = _doc(PP.p(d, "publish"))
    if cont is None:
        s.thieu("G20", "Bản ghi continuity", f"không có {PP.LAYOUT['publish']}")
    else:
        try:
            c = json.loads(cont)
            tt = _tu(str(c.get("summary", "")))
            # Đếm key-term CÓ NỘI DUNG. ["", "", ""] có 3 phần tử mà không giải thích gì.
            kt = len([x for x in (c.get("key_terms_explained") or [])
                      if len(str(x).split()) >= 2])
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
        s.thieu("G23", "Placeholder {{...}}", "chưa có file công khai nào để quét")
    else:
        hit, mien = [], []
        for ten, t in cong_khai.items():
            for x in TOOL_NOI_BO:
                if x not in t.lower():
                    continue
                nhan = f"{ten}:{t.lower().count(x)}x'{x}'"
                (mien if x in cho_phep else hit).append(
                    f"{nhan} — MIỄN TRỪ: {cho_phep[x]}" if x in cho_phep else nhan)
        s.do("G21", "Tên công cụ nội bộ", len(hit), "= 0", not hit,
             ghi_chu="; ".join(hit[:6] + mien[:4]))
        # G23 — placeholder còn sót. Cả quy trình đăng (kể cả đăng tay) đứng trên giả định
        # "mọi {{...}} đã được thay bằng link thật". Vòng 1 chỉ nhìn placeholder GIÁN TIẾP
        # qua G14 ở comment, nên youtube_desc.txt và fb_desc.txt mang nguyên {{BLOG_URL}}
        # vẫn qua sạch — đo được ngày 04/09 trên chính bài này.
        ph = [f"{ten}:{m}" for ten, t in cong_khai.items()
              for m in re.findall(r"\{\{[^}\n]*\}\}", t)]
        s.do("G23", "Placeholder {{...}} trong file công khai", len(ph), "= 0", not ph,
             ghi_chu="; ".join(ph[:6]))

        hit2 = [ten for ten, t in cong_khai.items() if TEN_TO_CHUC.search(t)]
        s.do("G22", "Tên tổ chức trong bản công khai", len(hit2), "= 0 nếu bài sẽ vào repo",
             not hit2, CANH_BAO,
             ghi_chu="; ".join(hit2) + " - bài đăng kênh nhà thì đây là bình thường"
             if hit2 else "")

    do_chan = [r for r in s.rows if r["trang_thai"] == "do" and r["muc"] == CHAN]
    return {
        "thu_muc": str(d),
        "mien_tru": cho_phep,
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
    ap.add_argument("--cho-phep", action="append", default=[], metavar="TÊN=LÝ DO",
                    help="miễn trừ G21 cho một tên, BẮT BUỘC kèm lý do. Lặp lại được. "
                         "Miễn trừ vẫn được in ra báo cáo và ghi vào gates.json.")
    a = ap.parse_args(argv)

    d = Path(a.thu_muc)
    if not d.is_dir():
        sys.stderr.write(f"không phải thư mục: {d}\n")
        return 2

    home = a.home_domain or re.sub(r"^https?://([^/]+).*$", r"\1",
                                   os.environ.get("ATLAS_BASE_URL", "https://ducnguyen.vn"))
    cho_phep = {}
    for muc in a.cho_phep:
        ten, _, ly_do = muc.partition("=")
        if not ly_do.strip():
            sys.stderr.write(
                f"--cho-phep {muc!r} thiếu lý do.\n"
                "Đúng cú pháp: --cho-phep \"tên=vì sao đây không phải rò rỉ\"\n"
                "Miễn trừ không kèm lý do thì sáu tháng sau không ai biết vì sao nó ở đó,\n"
                "và nó sẽ được sao chép sang bài tiếp theo mà không ai xét lại.\n")
            return 2
        cho_phep[ten.strip()] = ly_do.strip()
    kq = chay(d, home, a.loai, cho_phep)
    PP.p(d, "gates").write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")

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
