# -*- coding: utf-8 -*-
"""Cổng chống TÀI LIỆU TRÔI — chặn luật cũ và tên cũ hồi sinh.

Bài học ngày 04/09/2026: đợt đổi luật link Facebook sửa 7 file, nhưng
`output_styles/multichannel-style.md` có **hai** chỗ nói về link — mục "Facebook" (đã sửa)
và mục "Quy tắc format FB chung" (bị bỏ sót). Kết quả: một file mang hai luật trái nhau,
và agent đọc trúng dòng nào thì theo dòng đó.

Cổng này quét toàn cây git-tracked tìm những chuỗi CHỈ CÓ THỂ đến từ mô hình đã bỏ.
Nó không thay người đọc — nó chỉ đảm bảo cái đã bỏ thì không quay lại một cách im lặng.

So khớp bằng CHUỖI THẲNG, không regex — cùng lý do với test_dename: regex nuốt escape và
cho âm tính giả.
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Chuỗi cấm -> vì sao cấm. Chỉ liệt kê thứ KHÔNG CÒN ĐÚNG, không liệt kê thứ chỉ cũ.
CAM = {
    "Link đặt ĐẦU bài": "luật link Facebook đã đảo 04/09: thân bài 0 URL, link ở comment đầu",
    "post:youtube_video": "neo đã đổi thành post:youtube_desc (gen_article chỉ hiểu tên mới)",
    "fb_image.png": "đã gộp thành facebook/infographic.png — xem post_paths.LAYOUT",
    # KHÔNG cấm "tobi_excel.py": nó xuất hiện HỢP LỆ trong khối cảnh báo đầu hai file .ps1
    # (đang giải thích vì sao chúng chưa chạy được). Cấm một cái tên vì nó cũ là sai —
    # chỉ cấm thứ còn tự xưng là LUẬT HIỆN HÀNH.
}

# Nơi được phép nhắc tên cũ: chỗ GIẢI THÍCH lịch sử, và chính file này.
MIEN_TRU = ("tests/test_docs_khong_troi.py", "fixtures/baseline/", "templates/_archive/")

NHI_PHAN = {".png", ".jpg", ".jpeg", ".mp3", ".mp4", ".xlsx", ".ico", ".woff", ".woff2"}


def _tracked():
    ra = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    for ten in ra.stdout.decode().split("\0"):
        if not ten or ten.startswith(MIEN_TRU) or Path(ten).suffix.lower() in NHI_PHAN:
            continue
        try:
            yield ten, (ROOT / ten).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


FILES = list(_tracked())


def test_co_file_de_quet():
    assert len(FILES) > 50, f"chỉ thấy {len(FILES)} file — nghi lỗi môi trường, cổng sẽ luôn xanh"


@pytest.mark.parametrize("chuoi,vi_sao", list(CAM.items()))
def test_chuoi_cua_mo_hinh_da_bo(chuoi, vi_sao):
    dinh = []
    for ten, noi_dung in FILES:
        if chuoi in noi_dung:
            dong = noi_dung[:noi_dung.index(chuoi)].count("\n") + 1
            dinh.append(f"{ten}:{dong}")
    assert not dinh, f"{chuoi!r} — {vi_sao}. Còn ở: {dinh[:10]}"


def test_mot_file_khong_duoc_mang_hai_luat_link():
    """Ca cụ thể đã xảy ra: cùng một file vừa nói 'thân bài 0 URL' vừa nói 'link đầu bài'."""
    for ten, noi_dung in FILES:
        if "Thân bài không chứa URL" in noi_dung or "thân bài 0 URL" in noi_dung.lower():
            assert "đặt ĐẦU bài" not in noi_dung, \
                f"{ten} mang hai luật link trái nhau trong cùng một file"
