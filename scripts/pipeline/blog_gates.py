#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""24 cổng đếm được cho một bài blog. Vào: thư mục bài. Ra: gates.json + JSON ra stdout.

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

# Ép UTF-8 cho stdout/stderr. Máy sạch trên Windows mặc định cp1252, và bảng chấm
# cổng in tiếng Việt — thiếu dòng này thì script CHẾT ngay ở lệnh in, sau khi đã làm
# xong việc. Đo thật 12/09/2026: lỗi này làm bước `check-gates` hỏng và vòng chạy
# quay tít vì artefact cũ vẫn còn nên không ai thấy bước đó chưa tiến.
from pathlib import Path
from urllib.parse import urlsplit

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_format as FF  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import post_paths as PP  # noqa: E402

CHAN, CANH_BAO = "block", "warn"

# ── Cổng nào thuộc BƯỚC nào ─────────────────────────────────────────────────
# Chấm trọn 24 cổng ngay sau khi soạn thì bài KHÔNG BAO GIỜ xanh được: bốn cổng dưới đây
# đo ảnh, trang HTML, sổ đăng bài và LINK THẬT — thứ chỉ có sau khi dựng trang và phát
# hành. Đo thật 12/09/2026: 3 bài kẹt ở `fix-gates` từ hôm trước vì bị chặn bởi đúng
# những cổng mà bước soạn không có cách nào làm cho xanh.
#
# Cổng chưa tới lượt phải báo `missing`, KHÔNG phải `fail` — cơ chế đó đã có sẵn cho
# G15–G18, chỉ là bốn cổng kia chưa được gắn bước.
GIAI_DOAN = ["write", "assets", "publish", "release"]
PLACEHOLDER_BUOC_DANG = {"{{BLOG_URL}}", "{{YOUTUBE_URL}}"}

# Prompt ảnh ngắn hơn chừng này thì không đủ chỗ viết sẵn từng chuỗi chữ cho năm vùng của
# khung infographic. `make_fb_image.py` đọc CÙNG hằng số này — hai nơi đo hai số là hai luật.
PROMPT_ANH_TOI_THIEU = 600

CONG_THUOC_BUOC = {
    "G14": "release",   # comment đầu phải có link web + YouTube → chỉ có sau khi đăng
    "G15": "assets", "G16": "assets", "G17": "assets",   # podcast · video · scene
    "G18": "publish",   # thẻ og: đọc atlas.html → do bước dựng trang sinh
    "G19": "assets",    # ảnh infographic + sidecar prompt
    "G20": "publish",   # summary/key-term trong publish.json → bước đăng ghi
}

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
# Khối chính kiến nhận HAI hình dạng: khối trích dẫn `> **Góc nhìn:**` hoặc một mục
# `## ...góc nhìn...`. Bắt bài đổi hình dạng chỉ để chiều cổng là bắt nội dung phục vụ
# phép đo — mà nội dung mới là thứ cổng tồn tại để bảo vệ.
_GOC_NHIN = re.compile(r"^>\s*\*\*Góc nhìn:", re.M)
_GOC_NHIN_H2 = re.compile(r"^##\s+.*góc nhìn.*$", re.M | re.I)
# Mục nguồn cuối bài — chỗ người đọc kiểm chứng được. Nhận vài cách gọi thường gặp.
_MUC_NGUON = re.compile(r"^##\s+(?:nguồn(?:\s+tham\s+khảo)?|tham\s+khảo|tài\s+liệu)\s*$",
                        re.M | re.I)
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


def _dem_goc_nhin(blog: str) -> tuple[int, int]:
    """Số khối chính kiến và số từ của khối DÀI NHẤT, nhận cả hai hình dạng.

    Đếm chữ THỰC SỰ có trong khối. Bản đầu chỉ khớp dòng tiêu đề, nên một khối rỗng hoàn
    toàn vẫn cho G06 xanh — tức cổng bảo đảm một thứ không tồn tại.
    """
    khoi = 0
    dai_nhat = 0

    for m in _GOC_NHIN.finditer(blog):
        khoi += 1
        dong = []
        for l in blog[m.start():].splitlines():
            if dong and not l.lstrip().startswith(">"):
                break
            dong.append(l.lstrip("> ").strip())
        dai_nhat = max(dai_nhat, len(" ".join(dong).split()) - 2)  # trừ "**Góc nhìn:**"

    for m in _GOC_NHIN_H2.finditer(blog):
        khoi += 1
        sau = blog[m.end():]
        het = re.search(r"(?m)^##\s", sau)
        than = sau[:het.start()] if het else sau
        dai_nhat = max(dai_nhat, _tu(than))

    return khoi, dai_nhat


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

    def __init__(self, stage: str = "write"):
        self.rows: list[dict] = []
        self.stage = stage if stage in GIAI_DOAN else "write"

    def _chua_toi_luot(self, job_id: str) -> str:
        """Cổng này thuộc bước nào, và bước đó đã chạy chưa. Trả tên bước nếu CHƯA."""
        thuoc = CONG_THUOC_BUOC.get(job_id, "write")
        return thuoc if GIAI_DOAN.index(thuoc) > GIAI_DOAN.index(self.stage) else ""

    def do(self, job_id, name, gia_tri, luat, dat, level=CHAN, note=""):
        sau = self._chua_toi_luot(job_id)
        if not dat and sau:
            # Không chặn bằng thứ bước hiện tại không tạo ra được. Vẫn ghi lại số đo để
            # người đọc thấy nó đang ở đâu, chỉ là không tính là đỏ.
            self.rows.append({"id": job_id, "name": name, "measured": gia_tri, "rule": luat,
                              "status": "missing", "level": "",
                              "note": f"chưa tới lượt — cổng của bước `{sau}`, "
                                      f"đang chấm ở bước `{self.stage}`"})
            return
        self.rows.append({"id": job_id, "name": name, "measured": gia_tri, "rule": luat,
                          "status": "pass" if dat else "fail",
                          "level": "" if dat else level, "note": note})

    def thieu(self, job_id, name, why):
        self.rows.append({"id": job_id, "name": name, "measured": None, "rule": "—",
                          "status": "missing", "level": "", "note": why})


def run_cmd(folder: Path, home_domain: str, kind: str = "full",
         allow: dict[str, str] | None = None, stage: str = "write") -> dict:
    """`allow` = {needle: lý do} — MIỄN TRỪ CÓ GHI LÝ DO cho G21.

    Vì sao cần: danh sách needle của G21 so khớp chuỗi thô, nên nó không phân biệt được
    "công cụ sản xuất nội bộ của mình bị lộ" với "tên sản phẩm của hãng khác, đang là
    chủ đề của bài". Ca thật: một bài viết VỀ bản phát hành của OpenAI buộc phải nhắc
    tên công cụ lập trình của họ, và cổng chặn thẳng.

    Cách xử lý CỐ Ý không phải là nới danh sách needle — nới một lần là nới mãi, và lần
    sau lộ thật thì không ai bắt được. Thay vào đó: vẫn phát hiện, vẫn IN RA báo cáo,
    nhưng kèm lý do do người nêu và không chặn. Miễn trừ nào cũng để lại dấu trong
    gates.json — im lặng bỏ qua và miễn trừ có ghi lý do là hai chuyện khác nhau.
    """
    allow = {k.lower(): v for k, v in (allow or {}).items()}
    d = folder
    s = SoKetQua(stage)

    # ---------------------------------------------------------------- blog.md
    blog = _doc(PP.p(d, "blog"))
    if blog is None:
        for job_id, name in [("G01", "Độ dài blog"), ("G02", "Số H2"), ("G03", "Bảng/list"),
                        ("G04", "Callout"), ("G05", "Nguồn ngoài"), ("G06", "Khối chính kiến"),
                        ("G07", "Fact vs opinion"), ("G08", "[KIỂM CHỨNG] còn mở")]:
            s.thieu(job_id, name, f"không có {PP.LAYOUT['blog']}")
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
        # ĐỔI 12/09/2026 — trước đó cổng này đếm link RẢI TRONG THÂN BÀI và đòi 3–7 cái.
        #
        # Kênh này viết kể chuyện cho người không chuyên; chèn link giữa dòng làm gãy mạch
        # đọc, và bộ viết vốn đã dẫn nguồn bằng TÊN + NGÀY ngay tại chỗ khẳng định. Đo thật
        # trên NEN-004: research.md có 5 nguồn thật, thân bài có 3 link nhưng đều là link
        # nội bộ sang bài khác ⇒ cổng đếm 0 và báo đỏ một bài có kỷ luật nguồn tốt.
        #
        # Nay đo ĐÚNG CHỖ người đọc kiểm chứng được: mục `## Nguồn tham khảo` cuối bài.
        # Link rải trong thân KHÔNG cấm, chỉ không còn bắt buộc.
        muc_nguon = _MUC_NGUON.search(blog)
        than_nguon = blog[muc_nguon.end():] if muc_nguon else ""
        ke = sorted({u for u in _URL.findall(than_nguon) if home_domain not in u})
        if not muc_nguon:
            s.do("G05", "Nguồn ngoài (kê ở mục Nguồn tham khảo)", "không có mục",
                 "3-7 và khớp research.md", False,
                 note="bài thiếu mục `## Nguồn tham khảo` — người đọc không kiểm chứng được")
        elif nc is None:
            s.do("G05", "Nguồn ngoài (kê ở mục Nguồn tham khảo)", len(ke),
                 "3-7", 3 <= len(ke) <= 7,
                 note="không đối chiếu được: thiếu research.md")
        else:
            # So theo host, không so nguyên URL: bài hay trích link sâu hơn bảng nguồn.
            def _host(u):
                # `urlsplit` chu KHONG `re.sub` voi nhom thay the: nhom `` di qua vai
                # tang cong cu la bi nuot thanh ky tu dieu khien, va khi ay MOI host tra
                # ve cung mot chuoi nen khong nguon nao bi tinh la lac. Fail-open, cam.
                # Dinh dung loi nay 12/09/2026 — test bat duoc.
                return urlsplit(u).netloc.lower().removeprefix("www.")
            host_nguon = {_host(u) for u in _URL.findall(nc)}
            lac = sorted({u for u in ke if _host(u) not in host_nguon})
            s.do("G05", "Nguồn ngoài (kê ở mục Nguồn tham khảo)",
                 f"{len(ke)} nguồn, {len(lac)} lạc", "3-7 và khớp research.md",
                 3 <= len(ke) <= 7 and not lac,
                 note=("URL không có trong research.md: " + "; ".join(lac[:4]))
                 if lac else "; ".join(ke[:5]))
        # ĐỔI 12/09/2026 — trước đó chỉ nhận khối trích dẫn `> **Góc nhìn:**`.
        # Đo thật trên NEN-004: bài có mục `## Góc nhìn của mình` dài 399 từ, gấp mười lần
        # ngưỡng, mà cổng báo 0 khối. Cổng đo VỎ chứ không đo chất. Nay nhận cả hai hình
        # dạng và vẫn đếm chữ thật — bắt bài đổi hình dạng chỉ để chiều cổng là bắt nội
        # dung phục vụ phép đo.
        gn, tu_gn = _dem_goc_nhin(blog)
        s.do("G06", "Khối chính kiến (H2 hoặc trích dẫn Góc nhìn)", f"{gn} khối / {tu_gn} từ",
             ">=1 khối và >=40 từ", gn >= 1 and tu_gn >= 40,
             note="" if tu_gn >= 40 else "khối chính kiến quá ngắn hoặc rỗng")
        tn, tm = len(_THEO_NGUON.findall(blog)), len(_THEO_MINH.findall(blog))
        s.do("G07", "Dẫn nguồn / nêu ý riêng", f"{tn} / {tm}", "mỗi loại >=1",
             tn >= 1 and tm >= 1, CANH_BAO)
        kc = len(_KIEM_CHUNG.findall(blog))
        s.do("G08", "[KIỂM CHỨNG] còn mở", kc, "= 0", kc == 0)

    # ---------------------------------------------------------------- facebook
    fb = _doc(PP.p(d, "fb_post"))
    cmt = _doc(PP.p(d, "fb_comment")) or ""
    if fb is None:
        for job_id, name in [("G09", "URL trong thân post"), ("G10", "Độ dài post"),
                        ("G11", "Ký tự Unicode bold"), ("G12", "Markdown literal"),
                        ("G13", "Hashtag"), ("G14", "Comment đầu")]:
            s.thieu(job_id, name, f"không có {PP.LAYOUT['fb_post']}")
    else:
        m = FF.check(fb, cmt)
        tran = [u for u in _URL_TRAN.findall(fb.split(FF.MARKER_COMMENT)[0])]
        tong_url = m["so_url_than_bai"] + len(tran)
        s.do("G09", "URL trong thân post (kể cả link trần)", tong_url, "= 0",
             tong_url == 0, note="; ".join(m["url_than_bai"] + tran[:3]))
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
                 note=f'phần thường có {m["so_chu_co_dau_ngoai_bold"]} chữ có dấu, '
                         f'phần đậm có 0 — nhiều khả năng gõ tay thay vì dùng '
                         f'fb_format.bold()')
        else:
            s.do("G11", "Ký tự Unicode bold", m["so_ky_tu_bold"], "> 0",
                 m["so_ky_tu_bold"] > 0,
                 note=f'{m["so_dau_trong_bold"]} dấu trong vùng đậm'
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
             note=("không thấy fb_comment.txt lẫn neo ### comment_1"
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
             note=f"~{n / 3.8:.0f}s khi đọc ở 3,8 từ/giây (đo thật, xem baseline)")

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
            can = 8 if kind == "full" else 4
            if not isinstance(js, list):
                # make_podcast_video.py làm `scenes = json.load(f)` rồi lặp thẳng, nên nó đòi
                # MẢNG ở cấp cao nhất. Bọc trong {"scenes": [...]} thì nó lặp qua các KHOÁ,
                # gặp chuỗi và chết bằng "'str' object has no attribute 'get'".
                # Cổng từng chấp nhận cả hai dạng và báo xanh trong khi renderer không chạy
                # được — cổng dễ dãi hơn công cụ thật thì tệ hơn là không có cổng, vì nó
                # cấp một lời bảo đảm sai. Nay cổng đo đúng hợp đồng của renderer.
                s.do("G17", "Số scene", f"JSON là {type(js).__name__}, không phải mảng",
                     "mảng ở cấp cao nhất", False,
                     note="renderer lặp thẳng trên JSON -> bọc trong {\"scenes\": [...]} sẽ vỡ")
            else:
                # Không chỉ ĐẾM. Scene rỗng {} vẫn qua phép đếm, rồi renderer dựng ra
                # slide trắng với nhãn mặc định của một dự án khác — video 8 cảnh trống
                # mà cổng báo xanh.
                HOP_LE = {"cover", "concept", "versus", "list", "image", "closing"}
                failed = [i for i, sc_ in enumerate(js)
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
                     f"{len(js)} scene, {len(failed)} thiếu nội dung, {len(mat_src)} mất ảnh src",
                     f"= {can} ({kind}), mọi scene có kind + nội dung, src tồn tại",
                     len(js) == can and not failed and not mat_src,
                     note="; ".join(filter(None, [
                         f"scene rỗng/sai kind ở vị trí {failed[:5]}" if failed else "",
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
             note=f"thiếu: {', '.join(sorted(thieu_og))}" if thieu_og else "")

    # ---------------------------------------------------------------- ảnh Facebook
    # Đọc KÍCH THƯỚC THẬT từ khối IHDR của PNG (8 byte tại offset 16) thay vì chỉ hỏi
    # "file có tồn tại không" — một ảnh 1x1 px cũng tồn tại. Và prompt rỗng thì cũng là
    # không có prompt: sidecar sinh ra để dựng lại được ảnh, rỗng thì dựng lại bằng gì.
    # infographic.png là tên chính thức từ 04/09: một ảnh vừa đăng Facebook vừa đặt đầu bài
    # blog, thay cho ảnh Facebook kiểu cũ (một nền + ba dòng chữ).
    # KHÔNG giữ tương thích tên ảnh cũ: "nới một lần là nới mãi" — cùng lý do
    # repo chọn --allow thay vì nới danh sách needle của G21.
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
         note="ảnh sinh bằng model KHÔNG tái lập - mất prompt là mất cách dựng lại")

    # ---------------------------------------------------------------- prompt ảnh Facebook
    # G19 đo ẢNH, nên nó thuộc bước `assets` và ở bước viết chỉ báo "chưa tới lượt". Nhưng
    # prompt là việc CỦA NGƯỜI VIẾT: nếu chỉ G19 canh thì thiếu prompt không bao giờ làm bài
    # đỏ ở bước viết, vòng viết lại không bao giờ được kích, và bước tạo ảnh đứng chờ một
    # thứ không ai được giao. G24 kéo phần prompt về đúng bước sinh ra nó.
    # Chỉ đo thứ máy đo được. Chữ tiếng Việt trên ẢNH đúng dấu hay không thì máy không đo
    # được — việc đó là phép soát bằng mắt ghi vào infographic.meta.json.
    if fb is None:
        s.thieu("G24", "Prompt ảnh Facebook", f"không có {PP.LAYOUT['fb_post']} — bài không đăng Facebook")
    else:
        pr = (_doc(f_prompt) or "").strip()
        ph_pr = re.findall(r"\{\{[^}\n]*\}\}", pr)
        s.do("G24", "Prompt ảnh Facebook (khối ### image_prompt)",
             f"{len(pr)} ký tự · {len(ph_pr)} chỗ trống",
             f">={PROMPT_ANH_TOI_THIEU} ký tự và 0 {{{{...}}}}",
             len(pr) >= PROMPT_ANH_TOI_THIEU and not ph_pr,
             note=("không có " + PP.LAYOUT["fb_prompt"] + " — thiếu khối ### image_prompt trong content.md"
                   if not pr else "; ".join(ph_pr[:4])))

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
    for name in FILE_CONG_KHAI:
        t = _doc(d / name)
        if t:
            cong_khai[name] = t
    if not cong_khai:
        s.thieu("G21", "Tên công cụ nội bộ", "chưa có file công khai nào để quét")
        s.thieu("G22", "Tên tổ chức trong bản công khai", "chưa có file công khai nào để quét")
        s.thieu("G23", "Placeholder {{...}}", "chưa có file công khai nào để quét")
    else:
        hit, mien = [], []
        for name, t in cong_khai.items():
            for x in TOOL_NOI_BO:
                if x not in t.lower():
                    continue
                label = f"{name}:{t.lower().count(x)}x'{x}'"
                (mien if x in allow else hit).append(
                    f"{label} — MIỄN TRỪ: {allow[x]}" if x in allow else label)
        s.do("G21", "Tên công cụ nội bộ", len(hit), "= 0", not hit,
             note="; ".join(hit[:6] + mien[:4]))
        # G23 — placeholder còn sót. Cả quy trình đăng (kể cả đăng tay) đứng trên giả định
        # "mọi {{...}} đã được thay bằng link thật". Vòng 1 chỉ nhìn placeholder GIÁN TIẾP
        # qua G14 ở comment, nên youtube_desc.txt và fb_desc.txt mang nguyên {{BLOG_URL}}
        # vẫn qua sạch — đo được ngày 04/09 trên chính bài này.
        # `{{BLOG_URL}}` và `{{YOUTUBE_URL}}` là CHỖ GIỮ hợp lệ cho tới bước đăng: hai
        # link đó chưa tồn tại lúc soạn. Không miễn ở bước soạn thì G23 và G14 chặn nhau —
        # điền link thì chưa có link, để chỗ giữ thì G23 đỏ. Không bài nào qua được cả hai.
        #
        # NHƯNG miễn theo BƯỚC, không miễn hẳn. Từ bước `publish` trở đi chúng phải biến
        # mất, và đó là bài học 04/09/2026: `youtube/description.txt` mang nguyên
        # `{{BLOG_URL}}` lọt qua cổng, người đăng tay dán nguyên văn lên YouTube.
        mien_ph = (PLACEHOLDER_BUOC_DANG
                   if GIAI_DOAN.index(s.stage) < GIAI_DOAN.index("publish") else set())
        ph = [f"{name}:{m}" for name, t in cong_khai.items()
              for m in re.findall(r"\{\{[^}\n]*\}\}", t) if m not in mien_ph]
        s.do("G23", "Placeholder {{...}} trong file công khai", len(ph), "= 0", not ph,
             note="; ".join(ph[:6]))

        hit2 = [name for name, t in cong_khai.items() if TEN_TO_CHUC.search(t)]
        s.do("G22", "Tên tổ chức trong bản công khai", len(hit2), "= 0 nếu bài sẽ vào repo",
             not hit2, CANH_BAO,
             note="; ".join(hit2) + " - bài đăng kênh nhà thì đây là bình thường"
             if hit2 else "")

    fail_block = [r for r in s.rows if r["status"] == "fail" and r["level"] == CHAN]
    return {
        "folder": str(d),
        "stage": s.stage,
        "waived": allow,
        "total": len(s.rows),
        "pass": sum(1 for r in s.rows if r["status"] == "pass"),
        "fail_block": len(fail_block),
        "fail_warn": sum(1 for r in s.rows if r["status"] == "fail" and r["level"] == CANH_BAO),
        "missing": sum(1 for r in s.rows if r["status"] == "missing"),
        "verdict": "fail" if fail_block else "pass",
        "gates": s.rows,
    }


def _in_vi_sao_bi_chan(result: dict) -> None:
    """Nói RÕ vì sao bài không đi tiếp được, và ai sửa được cái đó.

    Bảng 23 dòng ở trên là số đo thô. Người đọc phải tự lọc ra dòng nào đang chặn, dòng
    nào chỉ cảnh báo, dòng nào chưa tới lượt — và đó đúng là chỗ đã hiểu nhầm suốt một
    ngày: bảy cổng báo đỏ trong khi chỉ ba cổng thật sự thuộc bước đang chạy.
    """
    chan = [r for r in result["gates"] if r["status"] == "fail" and r["level"] == CHAN]
    hoan = [r for r in result["gates"]
            if r["status"] == "missing" and "chưa tới lượt" in (r["note"] or "")]

    if not chan:
        sys.stdout.write(f"\n  ✔ KHÔNG cổng nào chặn ở bước `{result['stage']}`.\n")
    else:
        sys.stdout.write(f"\n  ⛔ BỊ CHẶN bởi {len(chan)} cổng của chính bước "
                         f"`{result['stage']}` — sửa được bằng cách viết lại:\n")
        for r in chan:
            sys.stdout.write(f"     {r['id']} {r['name']}\n"
                             f"        đo được : {r['measured']}\n"
                             f"        luật    : {r['rule']}\n")
            if r["note"]:
                sys.stdout.write(f"        cụ thể  : {r['note'][:160]}\n")

    if hoan:
        sys.stdout.write(f"\n  ⏳ HOÃN {len(hoan)} cổng của bước sau, KHÔNG tính là đỏ: "
                         + ", ".join(r["id"] for r in hoan) + "\n"
                         "     (ảnh · trang web · link thật · sổ đăng bài — bước soạn "
                         "không tạo ra được nên không chặn ở đây)\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="24 cổng đếm được cho một bài blog.")
    ap.add_argument("folder", help="thư mục bài (chứa blog.md, fb_post.txt...)")
    ap.add_argument("--home-domain", default=None,
                    help="domain nhà, để loại khỏi phép đếm nguồn ngoài")
    ap.add_argument("--kind", choices=["full", "short"], default="full")
    ap.add_argument("--json-only", action="store_true", help="chỉ in JSON, không in bảng")
    ap.add_argument("--stage", choices=GIAI_DOAN, default="write",
                    help="đang chấm ở BƯỚC nào. Cổng của bước sau báo `missing`, "
                         "không chặn — mặc định `write`")
    ap.add_argument("--allow", action="append", default=[], metavar="TÊN=LÝ DO",
                    help="miễn trừ G21 cho một tên, BẮT BUỘC kèm lý do. Lặp lại được. "
                         "Miễn trừ vẫn được in ra báo cáo và ghi vào gates.json.")
    a = ap.parse_args(argv)

    d = Path(a.folder)
    if not d.is_dir():
        sys.stderr.write(f"không phải thư mục: {d}\n")
        return 2

    home = a.home_domain or re.sub(r"^https?://([^/]+).*$", r"\1",
                                   os.environ.get("ATLAS_BASE_URL", "https://ducnguyen.vn"))
    allow = {}
    for level in a.allow:
        name, _, reason = level.partition("=")
        if not reason.strip():
            sys.stderr.write(
                f"--allow {level!r} thiếu lý do.\n"
                "Đúng cú pháp: --allow \"tên=vì sao đây không phải rò rỉ\"\n"
                "Miễn trừ không kèm lý do thì sáu tháng sau không ai biết vì sao nó ở đó,\n"
                "và nó sẽ được sao chép sang bài tiếp theo mà không ai xét lại.\n")
            return 2
        allow[name.strip()] = reason.strip()
    result = run_cmd(d, home, a.kind, allow, a.stage)
    PP.p(d, "gates").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8", newline="\n")

    if a.json_only:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        label = {"pass": "OK  ", "fail": "DO  ", "missing": "--  "}
        for r in result["gates"]:
            level = f" [{r['level']}]" if r["level"] else ""
            gc = f"   {r['note']}" if r["note"] else ""
            sys.stdout.write(f"{label[r['status']]}{r['id']} {r['name']:<36} "
                             f"= {str(r['measured']):<13} luật {r['rule']}{level}{gc}\n")
        sys.stdout.write(f"\n  {result['pass']} xanh · {result['fail_block']} đỏ-chặn · "
                         f"{result['fail_warn']} đỏ-cảnh-báo · {result['missing']} hoãn/thiếu "
                         f"(trên {result['total']} cổng, chấm ở bước `{result['stage']}`)"
                         f"\n  -> gates.json\n")
        _in_vi_sao_bi_chan(result)
    return 1 if result["verdict"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
