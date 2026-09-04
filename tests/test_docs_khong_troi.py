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


def test_moi_cho_ghi_file_deu_ep_xuong_dong_LF():
    """Windows tự đổi \n thành CRLF nếu không ép — và mỗi lần sinh lại là cả file 'đổi'.

    Trong một repo lấy git làm lịch sử, diff giả làm mất luôn khả năng nhìn ra diff thật.
    """
    import re
    thieu = []
    for f in (ROOT / "scripts").rglob("*.py"):
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\.write_text\((.*?)\)\n", s, re.S):
            goi = m.group(1)
            if "encoding=" in goi and "newline=" not in goi:
                dong = s[:m.start()].count("\n") + 1
                thieu.append(f"{f.relative_to(ROOT)}:{dong}")
        for m in re.finditer(r"\bopen\((?!.*['\"]rb?['\"])(.*?)\)", s):
            goi = m.group(1)
            if '"w"' in goi and "newline=" not in goi:
                dong = s[:m.start()].count("\n") + 1
                thieu.append(f"{f.relative_to(ROOT)}:{dong} (open w)")
    assert not thieu, "ghi file mà không ép newline='\n': " + ", ".join(thieu)


def test_tai_lieu_KHONG_tro_vao_file_ma():
    """README từng trỏ vào `schema/` và workflows trỏ vào `scripts/workbook/new_campaign.py`
    — cả hai đã bị xoá từ lâu. Đó là cách tài liệu chết: không sai một chữ nào, chỉ là chỗ
    nó chỉ tới không còn ở đó nữa.

    Quét mọi đường dẫn trông-như-file trong tài liệu và kiểm nó tồn tại thật.
    """
    import re
    MAU = re.compile(r"`((?:scripts|templates|knowledge|workflows|output_styles|tests|"
                     r"\.agents|examples|docs|schema)/[A-Za-z0-9_./-]*)`")
    hong = []
    for f in list(ROOT.glob("*.md")) + list(ROOT.glob("workflows/*.md")) \
            + list(ROOT.glob(".agents/**/*.md")) + list(ROOT.glob("knowledge/**/*.md")) \
            + list(ROOT.glob("examples/*.md")):
        for m in MAU.finditer(f.read_text(encoding="utf-8")):
            d = m.group(1)
            if "<" in d or "*" in d or d.endswith("/"):
                continue          # mẫu có chỗ trống, hoặc chỉ là thư mục — bỏ qua
            if not (ROOT / d).exists():
                hong.append(f"{f.relative_to(ROOT)} → {d}")
    assert not hong, "tài liệu trỏ vào file không tồn tại:\n  " + "\n  ".join(hong)


def test_so_cong_trong_tai_lieu_KHOP_so_cong_thuc_te():
    """`blog_gates.py` tự ghi '22 cổng' trong khi phát 23 mã — và 3 tài liệu chép theo.

    Con số này người ta trích dẫn khắp nơi (README, trang chủ, checklist). Sai một con số
    đếm được là dấu hiệu rõ nhất rằng tài liệu đã ngừng theo kịp code.
    """
    import re
    ma = re.findall(r'"(G\d{2})\b', (ROOT / "scripts/pipeline/blog_gates.py")
                    .read_text(encoding="utf-8"))
    that = len(set(ma))
    assert that >= 20, f"không đếm được mã cổng (thấy {that}) — regex hỏng?"

    sai = []
    for f in list(ROOT.glob("*.md")) + list(ROOT.glob("**/*.md")):
        if ".git" in f.parts:
            continue
        for m in re.finditer(r"(\d{2}) cổng", f.read_text(encoding="utf-8")):
            if int(m.group(1)) != that:
                sai.append(f"{f.relative_to(ROOT)} nói {m.group(1)}, thực tế {that}")
    for m in re.finditer(r"(\d{2}) cổng",
                         (ROOT / "scripts/pipeline/blog_gates.py").read_text(encoding="utf-8")):
        if int(m.group(1)) != that:
            sai.append(f"blog_gates.py tự nói {m.group(1)}, thực tế {that}")
    assert not sai, "số cổng lệch:\n  " + "\n  ".join(sai)


def test_DATA_MODEL_dinh_nghia_DU_moi_cot_dang_chay():
    """DATA_MODEL tự xưng CANONICAL. Vậy thì mọi cột đang chạy phải có mặt trong đó.

    Đo 05/09: 11 trong 15 cột của bảng Content (`g1 g2 web youtube facebook pillar angle
    funnel schedule published folder`) KHÔNG được định nghĩa ở đâu cả, trong khi file vẫn
    mô tả `approved_date`, `folder_path`… của mô hình Excel cũ. Agent đọc file này rồi đi
    ghi `approved_date` vào bảng Content là ghi vào hư không.
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "lib"))
    _s.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import new_post

    doc = (ROOT / "knowledge/data_model/DATA_MODEL.md").read_text(encoding="utf-8")
    thieu = [c for c in new_post.COT if f"`{c}`" not in doc]
    assert not thieu, ("DATA_MODEL không định nghĩa cột đang chạy: " + ", ".join(thieu))

    for k in new_post.BAT_BUOC:
        assert f"`{k}`" in doc, f"trường bắt buộc {k} không có trong DATA_MODEL"
