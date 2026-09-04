# -*- coding: utf-8 -*-
"""Test cho gen_article.py — tách content.md thành file từng kênh.

Bối cảnh: trước bản vá 04/09, script CHỈ hiểu heading có đánh số ("## 3) Blog"), trong khi
`templates/CONTENT_TEMPLATE.md` của chính repo này dùng neo "## post:facebook_post".
Cho nó ăn đúng template của repo thì tách ra **0 khối**. Đây là rủi ro R3 trong plan:
tách theo SỐ MỤC thì số mục xê dịch theo từng bài, sớm muộn cũng lệch mà không ai biết.

Bộ test này giữ ba điều: neo mới chạy · kiểu số cũ KHÔNG bị phá · và link không lọt từ
comment ngược vào thân post (nếu lọt thì bài vi phạm luật "thân bài 0 URL" ngay từ khâu tách).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import gen_article as G  # noqa: E402

TEMPLATE = ROOT / "templates" / "CONTENT_TEMPLATE.md"


@pytest.fixture(scope="module")
def theo_template():
    return G.split_content(TEMPLATE.read_text(encoding="utf-8"))


def test_tach_duoc_template_cua_chinh_repo(theo_template):
    """Ca hỏng gốc: script không đọc nổi template của repo mình."""
    assert set(theo_template) >= {"blog", "fb_post", "fb_comment", "youtube_desc", "fb_desc"}


def test_moi_khoi_deu_co_noi_dung(theo_template):
    rong = [k for k, v in theo_template.items() if not v.strip()]
    assert not rong, f"khối rỗng sẽ ghi ra file 0 byte mà script vẫn báo OK: {rong}"


def test_link_khong_lot_tu_comment_vao_than_post(theo_template):
    """`### comment_1` lồng bên trong `## post:facebook_post`.

    Bắt hụt nó thì link bị nuốt vào thân post — đúng cái lỗi mà cổng G09 tồn tại để chặn,
    nhưng lần này lỗi phát sinh ngay từ khâu tách chứ không phải do người viết.
    """
    assert "BLOG_URL" not in theo_template["fb_post"]
    assert "BLOG_URL" in theo_template["fb_comment"]


def test_bo_dau_ngat_cuoi_khoi():
    """`---` là ký hiệu CỦA content.md, không thuộc bản giao cho kênh.

    Để sót thì ba dấu gạch lên thẳng phần mô tả YouTube và vào comment Facebook nguyên văn.
    Đã xảy ra thật trên AST-001: 3/5 file kênh kết thúc bằng "---".
    """
    # Dựng bằng join thay vì chuỗi có escape: nguồn này đi qua nhiều tầng công cụ, mỗi
    # tầng ăn một lớp escape — đã làm hỏng đúng file test này một lần.
    nguon = "\n".join(["## post:blog_article", "", "Nội dung.", "", "---", "",
                       "## post:reel", "", "Caption.", ""])
    ra = G.split_content(nguon)
    import tempfile
    d = Path(tempfile.mkdtemp())
    da_ghi = G.write_outputs(ra, str(d))
    for k, f in da_ghi.items():
        cuoi = Path(f).read_text(encoding="utf-8").rstrip().splitlines()[-1].strip()
        assert not cuoi.startswith("---"), f"{k} còn dấu ngắt cuối file: {cuoi!r}"


def test_kieu_danh_so_cu_van_chay():
    """Bài cũ viết theo Mục 3/4/5/6 phải tách được y như trước — không phá bản cũ."""
    cu = "## 3) Blog\n\nNội dung blog.\n\n## 4) FB post\n\nNội dung fb.\n"
    ra = G.split_content(cu)
    assert ra["blog"].strip() == "Nội dung blog."
    assert ra["fb_post"].strip() == "Nội dung fb."


def test_heading_danh_so_khong_phai_kenh_thi_dong_khoi():
    ra = G.split_content("## 3) Blog\n\nA\n\n## 7) Ghi chú\n\nKHÔNG được lọt vào blog\n")
    assert "KHÔNG được lọt" not in ra["blog"]


def test_ghi_file_va_bao_thieu(tmp_path):
    parts = G.split_content(TEMPLATE.read_text(encoding="utf-8"))
    da_ghi = G.write_outputs(parts, str(tmp_path))
    assert set(da_ghi) >= {"blog", "fb_post", "fb_comment"}
    for k, p in da_ghi.items():
        assert Path(p).stat().st_size > 0, f"{k} ghi ra file 0 byte"
