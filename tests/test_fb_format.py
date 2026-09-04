# -*- coding: utf-8 -*-
"""Test cho fb_format.py.

Luật của bộ test này: mỗi cổng phải **đỏ ĐÚNG LÝ DO**, không chỉ đỏ.
Một test chỉ khẳng định `ket_luan == "do"` là test vô dụng — bài trượt vì lý do A mà
cổng báo lý do B thì người sửa đi sai đường, và test vẫn xanh.
"""
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "pipeline"))
import fb_format as F  # noqa: E402


# ---------------------------------------------------------------- bold()

def test_dd_khong_tach_duoc():
    """Chốt lại SỰ THẬT nền tảng mà cả module dựa vào.

    Nếu một phiên bản Python/Unicode nào đó đổi hành vi này, mọi giả định trong
    fb_format.py sập theo — và ta muốn biết ở đây, chứ không phải khi bài đã đăng.
    """
    assert unicodedata.normalize("NFD", "Đ") == "Đ"      # không tách ra D + gạch
    assert len(unicodedata.normalize("NFD", "Ể")) == 3   # E + ̂ + ̉ thì tách được


def test_bold_giu_dau_tieng_viet():
    ra = F.bold("Ể")
    assert ra[0] == "\U0001D404"          # 𝐄 bold
    assert "̂" in ra and "̉" in ra  # còn đủ dấu mũ + dấu hỏi


def test_bold_khong_lam_vo_chu_D():
    """Ca lỗi thật đã ghi ở QA_ASSET.md: 'ĐIỂM CHUNG' -> '𝐄̆𝐈𝐄̂̉𝐌 𝐂𝐇𝐔𝐍𝐆'."""
    ra = F.bold("ĐIỂM CHUNG")
    assert ra.startswith("Đ"), "Đ phải giữ nguyên, không được biến thành ký tự khác"
    assert "Ĕ" not in ra, "Ĕ (E+breve) = đúng cái lỗi cũ, không được tái xuất hiện"
    assert F.unbold(ra) == "ĐIỂM CHUNG", "bold rồi unbold phải ra lại đúng chữ ban đầu"


def test_bold_so_va_chu_thuong():
    assert F.bold("a1") == "\U0001D41A\U0001D7CF"


def test_unbold_khu_hoi_quy():
    goc = "Vibe coding là gì? 2026"
    assert F.unbold(F.bold(goc)) == goc


def test_dem_dau_trong_va_ngoai_vung_dam():
    """Hai đơn vị đo khác nhau, cố ý — dùng chung một phép đếm là cổng vô dụng.

    Trong vùng đậm: đếm KÝ TỰ TỔ HỢP, vì bold() buộc phải tách NFD.
    Ngoài vùng đậm: đếm CHỮ CÓ DẤU DỰNG SẴN, vì văn bản thường ở dạng NFC ("ộ" là MỘT
    ký tự). Nếu đếm ký tự tổ hợp ở cả hai chỗ thì phần ngoài luôn ra 0.
    """
    m = F.check(F.bold("MỚI") + "\n\nNội dung có dấu.")
    assert m["so_dau_trong_bold"] > 0
    assert m["so_chu_co_dau_ngoai_bold"] > 0

    m2 = F.check(F.bold("MOI") + "\n\nNội dung có dấu.")
    assert m2["so_ky_tu_bold"] == 3, "vẫn có ký tự đậm — phép đếm số lượng KHÔNG thấy gì sai"
    assert m2["so_dau_trong_bold"] == 0, "nhưng không dấu nào trong vùng đậm"
    assert m2["so_chu_co_dau_ngoai_bold"] > 0, "trong khi phần thường rõ ràng là tiếng Việt"


# ---------------------------------------------------------------- split_link()

def test_split_theo_neo_khong_theo_thu_tu():
    post = "Thân bài.\n\n### comment_1\n\n> dòng hướng dẫn bỏ đi\nĐọc full: https://a.vn/x"
    than, cmt = F.split_link(post)
    assert "comment_1" not in than
    assert "https://a.vn/x" in cmt
    assert "dòng hướng dẫn" not in cmt, "dòng trích dẫn của template không được lọt vào comment thật"


def test_khong_co_neo_thi_comment_rong_chu_khong_doan():
    than, cmt = F.split_link("Thân bài có https://a.vn/x lạc trong đó.")
    assert cmt == "", "không được tự nhặt URL trong thân bài làm comment"


# ---------------------------------------------------------------- fixture ĐỎ CÓ CHỦ ĐÍCH

BAI_DO = (
    "Đọc bài đầy đủ: https://ducnguyen.vn/atlas/content/ai/x.html\n\n"   # vi phạm: URL trong thân
    "**Tiêu đề in đậm kiểu markdown**\n\n"                               # vi phạm: markdown literal
    "Nội dung ngắn ngủn.\n\n"                                            # vi phạm: quá ngắn
    "#AI #Data\n"                                                        # vi phạm: chỉ 2 hashtag
)                                                                        # vi phạm: 0 ký tự bold, 0 comment


def test_fixture_do_dung_ly_do():
    m = F.check(BAI_DO)
    loi = {x["chi_so"]: x for x in F.danh_gia(m)}

    assert loi["so_url_than_bai"]["do_duoc"] == 1
    assert loi["so_hashtag"]["do_duoc"] == 2
    assert loi["so_ky_tu_bold"]["do_duoc"] == 0
    assert loi["markdown_literal"]["do_duoc"] == 2   # cặp ** mở và đóng
    assert loi["so_url_comment"]["do_duoc"] == 0
    assert loi["so_ky_tu"]["muc"] == "canh_bao", "độ dài chỉ cảnh báo, không chặn"

    chan = [k for k, v in loi.items() if v["muc"] == "chan"]
    assert set(chan) == {"so_url_than_bai", "so_hashtag", "so_ky_tu_bold",
                         "markdown_literal", "so_url_comment"}


def test_bai_xanh_khong_bao_dong_gia():
    bai = (
        F.bold("Chuyện gì đang xảy ra") + "\n\n"
        + "Nội dung dài. " * 400 + "\n\n"
        + "#AI #Data #CongNghe #HocMai #Prompt #Agent\n\n"
        + "### comment_1\n\nBản đầy đủ: https://ducnguyen.vn/atlas/content/ai/x.html\n"
    )
    m = F.check(bai)
    assert F.danh_gia(m) == [], "bài hợp lệ không được sinh cổng đỏ nào"
    assert m["co_comment"] is True


# ---------------------------------------------------------------- CLI

def test_cli_exit_khac_0_khi_do(tmp_path):
    f = tmp_path / "fb_post.txt"
    f.write_text(BAI_DO, encoding="utf-8")
    assert F.main(["--check", str(f)]) == 1
