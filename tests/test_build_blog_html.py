# -*- coding: utf-8 -*-
"""Test cho bộ dựng markdown → HTML của trang atlas.

Ba lỗi dưới đây đều bị bắt trên bài thật AST-001, không phải nghĩ ra: trang xuất bản ra
có 6 khối <ol> cho 2 danh sách (mục nào cũng đánh số "1."), in nguyên hai dấu sao của mọi
cụm nghiêng, và có 2 đoạn văn chỉ chứa ba dấu gạch. Không cổng nào bắt được vì cổng chỉ
đếm thẻ og:, không đọc phần thân trang.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
from build_blog_html import md_to_html  # noqa: E402


def test_muc_list_xuong_dong_khong_bi_cat():
    """Một mục list dài xuống dòng phải nằm trong CÙNG <li>, không tách ra <p> lẻ."""
    h = md_to_html("1. **Một** dòng đầu\n   dòng nối\n2. Hai\n\nĐoạn sau.")
    assert h.count("<ol>") == 1, "danh sách bị cắt thành nhiều khối -> mọi mục đánh số 1."
    assert h.count("<li>") == 2
    assert "dòng đầu dòng nối" in h, "phần nối rơi ra ngoài <li>"
    assert "<p>Đoạn sau.</p>" in h, "đoạn văn sau danh sách vẫn phải là đoạn văn riêng"


def test_bullet_list_cung_gom_dong_noi():
    h = md_to_html("- Mục một\n  phần nối\n- Mục hai\n")
    assert h.count("<ul>") == 1 and h.count("<li>") == 2
    assert "Mục một phần nối" in h


def test_nghieng_don_va_duong_ke_ngang():
    h = md_to_html('Theo X: *"trích"* xong.\n\n---\n\n*Ghi chú.*')
    assert "<em>" in h, "cụm *nghiêng* in ra nguyên dấu sao trên trang xuất bản"
    assert "<hr>" in h
    assert "<p>---</p>" not in h, "dấu ngắt là đường kẻ, không phải đoạn văn ba dấu gạch"


def test_dau_sao_phep_nhan_khong_thanh_nghieng():
    """Ranh giới: đừng chữa một lỗi bằng cách tạo ra lỗi khác."""
    assert "<em>" not in md_to_html("2 * 3 * 4")
    assert "<em>" not in md_to_html("a*b*c")


def test_dam_van_chay_va_khong_bi_nghieng_an_mat():
    h = md_to_html("**đậm** và *nghiêng* trong một dòng")
    assert "<strong>đậm</strong>" in h and "<em>nghiêng</em>" in h
