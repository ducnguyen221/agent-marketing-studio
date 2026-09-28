# -*- coding: utf-8 -*-
"""Cổng chống lộ HỆ THỐNG RIÊNG của người bảo trì vào repo PUBLIC.

`test_no_identity_leak.py` giữ danh tính người/máy (đường thư mục nhà, email, token, tên
thật). File này giữ một lớp khác: tên và đường dẫn của **hệ thống quản trị riêng** mà repo
từng dựa vào khi còn chạy trên một máy duy nhất — tên hệ điều phối agent, kho tri thức
cá nhân, đường nội bộ của cầu gọi agent. Chúng không phải secret, nhưng để trong repo
public thì hai hậu quả: lộ cấu trúc hệ thống riêng, và người clone về gặp mặc định trỏ tới
một thứ không tồn tại trên máy họ.

Luật:

1. Quét mọi file git-tracked dạng text (cùng nguồn `git ls-files` với cổng danh tính).
2. Miễn trừ theo SỐ ĐẾM CHÍNH XÁC, mỗi mục có lý do — thêm một chỗ vào file đã miễn cũng
   đỏ; mục miễn không còn khớp gì thì phải gỡ.
3. Chuỗi cấm dựng bằng mã ký tự: file này nằm trong vùng bị quét, cổng mang sẵn thứ nó đi
   tìm là cổng vô dụng.

Danh sách tên riêng ĐẦY ĐỦ (tên khách, đường máy, từ khoá nội bộ khác) KHÔNG nằm ở đây —
ghi nguyên danh sách đó vào test public là tự làm lộ. Cổng này chỉ giữ những mẫu đã từng
lọt vào repo; phần còn lại là việc của bộ kiểm riêng ngoài repo.
"""
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = "tests/test_no_leak.py"
NHI_PHAN = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".mp3", ".mp4", ".woff", ".woff2",
            ".pdf", ".xlsx", ".xls"}


def _s(*ma: int) -> str:
    return "".join(map(chr, ma))


_HE_DIEU_PHOI = _s(111, 112, 99, 111, 115)             # tên hệ điều phối agent riêng
_KHO_TRI_THUC = _s(66, 114, 97, 105, 110)              # tên kho tri thức cá nhân (viết hoa)
_CAU = _s(98, 114, 105, 100, 103, 101, 115) + "/"       # thư mục nội bộ của cầu gọi agent

MAU = {
    # `opc-os`, `opc_os` cũng là cùng một tên.
    "he-dieu-phoi": _HE_DIEU_PHOI[:3] + r"[-_]?" + _HE_DIEU_PHOI[3:],
    # Có ranh giới từ và PHÂN BIỆT hoa thường: "JetBrains Mono" (font) không phải rò rỉ.
    "kho-tri-thuc": r"(?<![A-Za-z])" + _KHO_TRI_THUC + r"(?![A-Za-z])",
    "duong-cau": re.escape(_CAU) + r"(?:lib|codex-bridge|claude-bridge|agy-bridge)\b",
}
KHONG_PHAN_BIET_HOA = {"he-dieu-phoi", "duong-cau"}

# (đường file, khoá) → số lần được phép. Mỗi dòng phải có LÝ DO.
MIEN_TRU: dict[tuple[str, str], int] = {}  # đang 0 miễn trừ: mọi chỗ khớp đều đỏ


def _tracked() -> list[Path]:
    ra = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / p for p in ra.stdout.decode("utf-8").split("\0") if p]


def _doc(p: Path) -> str:
    if p.suffix.lower() in NHI_PHAN:
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


FILES = [(p, _doc(p)) for p in _tracked()]


def dem() -> Counter:
    hits: Counter = Counter()
    for p, text in FILES:
        rel = p.relative_to(ROOT).as_posix()
        if rel == SELF or not text:
            continue
        for khoa, mau in MAU.items():
            co = re.IGNORECASE if khoa in KHONG_PHAN_BIET_HOA else 0
            n = len(re.findall(mau, text, flags=co))
            if n:
                hits[(rel, khoa)] = n
    return hits


def test_co_file_de_quet():
    """Cổng quét 0 file là cổng luôn xanh."""
    assert len([1 for _, t in FILES if t]) > 100, "quá ít file text git-tracked — nghi lỗi môi trường"


def test_khong_lo_he_thong_rieng():
    vuot = {k: n for k, n in dem().items() if n > MIEN_TRU.get(k, 0)}
    assert vuot == {}, "lộ tên/đường của hệ thống riêng vào repo public:\n  " + "\n  ".join(
        f"{f} [{k}] {n} > {MIEN_TRU.get((f, k), 0)}" for (f, k), n in sorted(vuot.items()))


def test_mien_tru_khong_han():
    hits = dem()
    han = [k for k in MIEN_TRU if k not in hits and (ROOT / k[0]).exists()]
    assert han == [], f"mục MIEN_TRU không còn khớp gì, gỡ đi: {han}"


def test_mau_bat_dung_muc_tieu():
    """Đột biến: mỗi mẫu bắt được chuỗi nó nhắm tới, và KHÔNG bắt chuỗi lành."""
    thu = {
        "he-dieu-phoi": ["~/." + _HE_DIEU_PHOI + "/x", _HE_DIEU_PHOI.upper() + "_BIEN",
                         _HE_DIEU_PHOI[:3] + "-" + _HE_DIEU_PHOI[3:]],
        "kho-tri-thuc": ["~/" + _KHO_TRI_THUC + "/INDEX.md"],
        "duong-cau": [_CAU + "lib/failure.mjs", _CAU + "codex-bridge/cli.mjs"],
    }
    for khoa, mau_list in thu.items():
        co = re.IGNORECASE if khoa in KHONG_PHAN_BIET_HOA else 0
        for m in mau_list:
            assert re.search(MAU[khoa], m, flags=co), (khoa, m)
    assert not re.search(MAU["kho-tri-thuc"], "font JetBrains Mono")
    assert not re.search(MAU["kho-tri-thuc"], "brainstorm")
    assert not re.search(MAU["duong-cau"], "cầu nối (bridge) giữa hai kênh", flags=re.I)
