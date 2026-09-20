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


# ══ REVIEW-P2 N15 — lỗi `brand:` phải là mã 2 ở MỌI nhánh ═══════════════════
# `BR.doc()` nằm trong `try` nên thiếu khoá bắt buộc ra mã 2 đúng như commit tuyên bố.
# Nhưng `BR.socials()` / `BR.icon()` chạy bên TRONG `build_html_full()`, và lời gọi đó
# nằm NGOÀI `try` — nên `icon: linkedin` (không có trong kho) hay `socials[0]` thiếu
# `url` cho exit 1 = "thử lại được", và lịch chạy retry mãi một lỗi `channel.yml`.

import json as _json  # noqa: E402
import subprocess as _sp  # noqa: E402
import sys as _sys  # noqa: E402

import pytest as _pt  # noqa: E402

_BBH = ROOT / "scripts" / "pipeline" / "build_blog_html.py"


def _du_an(tmp_path, brand_them: dict):
    brand = {"site_name": "Trang Thu", "author": "Nguoi Viet",
             "site_base": "https://vi-du.test", **brand_them}
    (tmp_path / "brand.json").write_text(_json.dumps({"brand": brand}), encoding="utf-8")
    (tmp_path / "bai.md").write_text("# Tieu de\n\nMot doan.\n", encoding="utf-8")
    (tmp_path / "meta.json").write_text(_json.dumps({"slug": "bai", "title": "Tieu de"}),
                                        encoding="utf-8")
    return _sp.run([_sys.executable, str(_BBH), "--blog-md", str(tmp_path / "bai.md"),
                    "--meta", str(tmp_path / "meta.json"),
                    "--brand", str(tmp_path / "brand.json"),
                    "--out", str(tmp_path / "ra.html")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")


@_pt.mark.parametrize("brand_them, vi_sao", [
    ({"socials": [{"icon": "linkedin", "url": "https://vi-du.test/x"}]}, "icon la"),
    ({"socials": [{"icon": "website"}]}, "socials thieu url"),
])
def test_brand_sai_o_socials_la_ma_2_khong_phai_1(tmp_path, brand_them, vi_sao):
    r = _du_an(tmp_path, brand_them)
    assert r.returncode == 2, f"{vi_sao}: mã {r.returncode}\n{r.stderr}"
    assert not (tmp_path / "ra.html").exists(), "đã hỏng mà vẫn ghi ra file"


def test_brand_du_thi_van_dung_duoc(tmp_path):
    r = _du_an(tmp_path, {"socials": [{"icon": "website", "url": "https://vi-du.test"}]})
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "ra.html").is_file()
