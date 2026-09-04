#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Định dạng & kiểm bài Facebook — Unicode bold, tách link ra comment, đếm cổng.

Vì sao cần file này: Facebook không có markdown. Viết `**Tiêu đề**` lên feed thì độc giả
đọc thấy đúng hai dấu sao. Cách in đậm duy nhất là dùng ký tự toán học đậm của Unicode.

BẪY TIẾNG VIỆT — lý do thật sự file này tồn tại:
Unicode KHÔNG có bản in đậm cho chữ có dấu. Không có "á đậm". Chỉ có A-Z, a-z, 0-9 đậm.
Nên phải tách dấu ra (NFD), bold chữ nền, rồi gắn dấu tổ hợp lại: 'Ể' = E + ̂ + ̉ -> 𝐄 + ̂ + ̉.
Trình duyệt dựng lại thành 𝐄̂̉ — nhìn đúng là Ể in đậm.

Riêng Đ/đ (U+0110/U+0111) là NGOẠI LỆ CỨNG: dấu gạch ngang nằm TRONG chữ cái, không phải
ký tự tổ hợp, nên NFD trả về chính nó (đã đo, xem test_dd_khong_tach_duoc). Hàm bold ngây
thơ kiểu `chr(0x1D400 + ord(c) - ord('A'))` sẽ đẩy Đ ra tận U+1D4CF — một ký hiệu toán
học không liên quan. Đó chính là lỗi 'ĐIỂM CHUNG' -> '𝐄̆𝐈𝐄̂̉𝐌 𝐂𝐇𝐔𝐍𝐆' đã ghi trong
.agents/checklists/QA_ASSET.md.
Xử lý ở đây: GIỮ NGUYÊN Đ/đ dạng thường. Một chữ Đ không đậm giữa dòng đậm thì hơi lệch,
nhưng đọc được; còn 'Ĕ' thì độc giả không đoán nổi đó là chữ gì. Cố ý chọn dễ đọc.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

BOLD_UPPER = 0x1D400   # 𝐀
BOLD_LOWER = 0x1D41A   # 𝐚
BOLD_DIGIT = 0x1D7CE   # 𝟎

# Ký tự bold nằm trong khối Mathematical Alphanumeric Symbols.
BOLD_RANGE = (0x1D400, 0x1D7FF)

# Đ/đ: không có bản bold, không tách được bằng NFD -> để nguyên (xem docstring).
KHONG_BOLD_DUOC = {"Đ", "đ"}

MARKER_COMMENT = "### comment_1"

_URL = re.compile(r"https?://\S+", re.I)
_HASHTAG = re.compile(r"(?<!\w)#\w+", re.U)
_MD_BOLD = re.compile(r"\*\*")
_MD_HEAD = re.compile(r"^#{1,6}\s", re.M)
_MD_USCORE = re.compile(r"__")
_NGAT = re.compile(r"^\s*(?:—{3,}|-{3,}|─{3,})\s*$", re.M)


def bold(s: str) -> str:
    """In đậm giữ nguyên dấu tiếng Việt. Ký tự không bold được thì trả lại chính nó."""
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if ch in KHONG_BOLD_DUOC:
            out.append(ch)
        elif "A" <= ch <= "Z":
            out.append(chr(BOLD_UPPER + ord(ch) - 65))
        elif "a" <= ch <= "z":
            out.append(chr(BOLD_LOWER + ord(ch) - 97))
        elif "0" <= ch <= "9":
            out.append(chr(BOLD_DIGIT + ord(ch) - 48))
        else:
            # Gồm cả ký tự tổ hợp (U+0300..U+036F) — PHẢI giữ, đó là dấu tiếng Việt.
            out.append(ch)
    return "".join(out)


def unbold(s: str) -> str:
    """Đảo ngược bold — dùng để đếm ký tự thật và để so bài với bản nguồn."""
    out = []
    for ch in s:
        o = ord(ch)
        if BOLD_UPPER <= o < BOLD_UPPER + 26:
            out.append(chr(65 + o - BOLD_UPPER))
        elif BOLD_LOWER <= o < BOLD_LOWER + 26:
            out.append(chr(97 + o - BOLD_LOWER))
        elif BOLD_DIGIT <= o < BOLD_DIGIT + 10:
            out.append(chr(48 + o - BOLD_DIGIT))
        else:
            out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def split_link(post: str) -> tuple[str, str]:
    """Cắt bài thành (thân post, comment đầu) theo neo '### comment_1'.

    Cắt theo NEO chứ không theo thứ tự khối: content.md do agent viết, số mục xê dịch
    theo từng bài, cắt theo vị trí là sớm muộn cũng lệch một khối mà không ai biết.
    Không có neo -> comment rỗng, và check() sẽ báo đỏ G14. KHÔNG tự đoán link nào là
    của comment: đoán sai thì bài đăng lên thiếu link, sửa được nhưng comment đã gửi rồi.
    """
    idx = post.find(MARKER_COMMENT)
    if idx < 0:
        return post.strip(), ""
    than = post[:idx].rstrip()
    cmt = post[idx + len(MARKER_COMMENT):].strip()
    # Bỏ các dòng trích dẫn hướng dẫn (> ...) mà template để lại.
    cmt = "\n".join(l for l in cmt.splitlines() if not l.lstrip().startswith(">")).strip()
    return than, cmt


def check(text: str, comment: str = "") -> dict:
    """Đếm các chỉ số định dạng FB. CHỈ đếm — không phán 'bài hay/dở', không đoán reach."""
    than, cmt_inline = split_link(text)
    cmt = comment or cmt_inline
    bold_chars = sum(1 for c in than if BOLD_RANGE[0] <= ord(c) <= BOLD_RANGE[1])
    urls = _URL.findall(than)
    md = len(_MD_BOLD.findall(than)) + len(_MD_HEAD.findall(than)) + len(_MD_USCORE.findall(than))
    return {
        "so_ky_tu": len(than),
        "so_url_than_bai": len(urls),
        "url_than_bai": urls[:5],
        "so_hashtag": len(_HASHTAG.findall(than)),
        "so_ky_tu_bold": bold_chars,
        "so_ngat_section": len(_NGAT.findall(than)),
        "markdown_literal": md,
        "co_comment": bool(cmt),
        "so_url_comment": len(_URL.findall(cmt)),
        "co_dd_khong_bold": any(c in KHONG_BOLD_DUOC for c in than),
    }


# Ngưỡng: lấy từ 3 bài đã đăng thật (fixtures/baseline/blog_baseline.md), không từ cảm giác.
NGUONG = {
    "so_ky_tu": (4000, 7500, "canh_bao"),
    "so_url_than_bai": (0, 0, "chan"),
    "so_hashtag": (6, 13, "chan"),
    "so_ky_tu_bold": (1, None, "chan"),
    "markdown_literal": (0, 0, "chan"),
    "so_url_comment": (1, None, "chan"),
}


def danh_gia(m: dict) -> list[dict]:
    """Đối chiếu số đo với ngưỡng. Mỗi dòng nói rõ ĐO ĐƯỢC GÌ, không diễn giải hậu quả."""
    ra = []
    for khoa, (lo, hi, muc) in NGUONG.items():
        v = m[khoa]
        ok = (lo is None or v >= lo) and (hi is None or v <= hi)
        if not ok:
            khoang = f"{lo}" if lo == hi else f"{lo}..{hi if hi is not None else '∞'}"
            ra.append({"chi_so": khoa, "do_duoc": v, "luat": khoang, "muc": muc})
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm định dạng bài Facebook.")
    ap.add_argument("--check", metavar="FILE", help="file bài (fb_post.txt hoặc content.md)")
    ap.add_argument("--comment", metavar="FILE", help="file comment (mặc định: lấy từ neo ### comment_1)")
    ap.add_argument("--bold", metavar="TEXT", help="in đậm một chuỗi rồi thoát")
    a = ap.parse_args(argv)

    if a.bold is not None:
        sys.stdout.write(bold(a.bold) + "\n")
        return 0
    if not a.check:
        ap.error("cần --check FILE hoặc --bold TEXT")

    with open(a.check, encoding="utf-8") as f:
        text = f.read()
    cmt = ""
    if a.comment:
        with open(a.comment, encoding="utf-8") as f:
            cmt = f.read()

    m = check(text, cmt)
    loi = danh_gia(m)
    ket = {"file": a.check, "do_duoc": m, "vi_pham": loi,
           "ket_luan": "do" if any(x["muc"] == "chan" for x in loi) else "xanh"}
    sys.stdout.write(json.dumps(ket, ensure_ascii=False, indent=2) + "\n")
    return 1 if ket["ket_luan"] == "do" else 0


if __name__ == "__main__":
    raise SystemExit(main())
