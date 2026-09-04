# -*- coding: utf-8 -*-
"""Test cho md_io — lớp nền của mô hình Markdown-là-nguồn-thật.

Sai ở đây là hỏng lan sang mọi script, và hỏng kiểu im lặng: ghi đè mất chữ của người mà
không ai báo. Nên test tập trung vào đúng hai điều nguy hiểm nhất: (1) script có đụng vào
chữ ngoài marker không, (2) ô có ký tự đặc biệt có phá bảng không.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import md_io as M  # noqa: E402

THAN = """# Tiêu đề

Đoạn văn của NGƯỜI, script không được đụng.

<!-- CONTENT:BEGIN -->
| content_id | tên | status |
|---|---|---|
| AST-001 | Bài một | published |
<!-- CONTENT:END -->

## Ghi chú
Chữ của người ở SAU bảng.
"""


def test_doc_ghi_frontmatter_giu_nguyen_gia_tri(tmp_path):
    p = tmp_path / "a.md"
    M.write_fm(p, {"id": "CMP-2609-x", "kpi": {"blog": 500}, "channels": ["web_blog"]}, "# Thân\n")
    fm, body = M.read_fm(p)
    assert fm["id"] == "CMP-2609-x" and fm["kpi"]["blog"] == 500
    assert fm["channels"] == ["web_blog"]
    assert body == "# Thân\n"


def test_tieng_viet_khong_bi_escape(tmp_path):
    p = tmp_path / "a.md"
    M.write_fm(p, {"name": "Chiến dịch tháng chín"}, "")
    assert "Chiến dịch tháng chín" in p.read_text(encoding="utf-8"), \
        "allow_unicode phải bật, nếu không frontmatter đầy \\u1ea1 không ai đọc nổi"


def test_khong_co_frontmatter_thi_tra_ca_file(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("\n".join(["# Chỉ có thân", "không frontmatter", ""]), encoding="utf-8")
    fm, body = M.read_fm(p)
    assert fm == {} and body.startswith("# Chỉ có thân")


def test_doc_bang_giua_marker():
    cot, dong = M.read_table(THAN, "CONTENT")
    assert cot == ["content_id", "tên", "status"]
    assert len(dong) == 1 and dong[0]["content_id"] == "AST-001"


def test_upsert_KHONG_dung_chu_ngoai_marker():
    """Điểm quan trọng nhất của cả file này."""
    moi = M.upsert_row(THAN, "CONTENT", "content_id",
                       {"content_id": "AST-002", "tên": "Bài hai", "status": "proposed"})
    assert "Đoạn văn của NGƯỜI, script không được đụng." in moi
    assert "## Ghi chú" in moi and "Chữ của người ở SAU bảng." in moi
    assert moi.index("Đoạn văn của NGƯỜI") < moi.index("<!-- CONTENT:BEGIN -->")
    assert moi.index("## Ghi chú") > moi.index("<!-- CONTENT:END -->")
    _, dong = M.read_table(moi, "CONTENT")
    assert [d["content_id"] for d in dong] == ["AST-001", "AST-002"]


def test_upsert_la_TRON_khong_phai_ghi_de():
    """Cập nhật một cột không được xoá cột người tự điền."""
    moi = M.upsert_row(THAN, "CONTENT", "content_id",
                       {"content_id": "AST-001", "status": "archived"})
    _, dong = M.read_table(moi, "CONTENT")
    assert dong[0]["status"] == "archived"
    assert dong[0]["tên"] == "Bài một", "cột không nhắc tới phải giữ nguyên"


def test_o_co_dau_gach_dung_khong_pha_bang():
    moi = M.upsert_row(THAN, "CONTENT", "content_id",
                       {"content_id": "AST-003", "tên": "A | B | C", "status": "proposed"})
    _, dong = M.read_table(moi, "CONTENT")
    assert dong[-1]["tên"] == "A | B | C", "dấu | trong ô phải escape rồi đọc lại nguyên vẹn"
    # THAN có sẵn 1 dòng, thêm 1 thành 2. Nếu dấu | bị hiểu là vách cột thì dòng mới sẽ vỡ
    # thành nhiều ô và con số này lệch.
    assert len(dong) == 2, "ô có | không được tách thành nhiều cột"
    assert set(dong[-1]) == {"content_id", "tên", "status"}, "không được đẻ thêm cột"


def test_thieu_marker_thi_no_loi_chu_khong_ghi_bua():
    with pytest.raises(ValueError, match="marker"):
        M.upsert_row("# Không có bảng\n", "CONTENT", "id", {"id": "X"})


def test_ghi_nguyen_tu_khong_de_lai_file_tam(tmp_path):
    p = tmp_path / "a.md"
    M.write_fm(p, {"a": 1}, "x")
    assert [f.name for f in tmp_path.iterdir()] == ["a.md"], "còn sót .tmp"


def test_bang_rong_van_doc_duoc_cot():
    than = "<!-- T:BEGIN -->\n| a | b |\n|---|---|\n<!-- T:END -->\n"
    cot, dong = M.read_table(than, "T")
    assert cot == ["a", "b"] and dong == []
    moi = M.upsert_row(than, "T", "a", {"a": "1", "b": "2"})
    assert M.read_table(moi, "T")[1] == [{"a": "1", "b": "2"}]


def test_khoa_la_thi_NEM_LOI_chu_khong_nuot_im_lang():
    """Bug thật: register_publish ghi cột `web` vào bảng chưa có cột đó → biến mất, không báo."""
    body = ("<!-- T:BEGIN -->\n| id | x |\n|---|---|\n| a | 1 |\n<!-- T:END -->\n")
    with pytest.raises(ValueError, match="mất im lặng"):
        M.upsert_row(body, "T", "id", {"id": "a", "chua_co": "v"})

    ra = M.upsert_row(body, "T", "id", {"id": "a", "chua_co": "v"}, them_cot=True)
    cot, dong = M.read_table(ra, "T")
    assert cot == ["id", "x", "chua_co"]
    assert dong[0] == {"id": "a", "x": "1", "chua_co": "v"}


def test_chi_cap_nhat_thi_KHONG_de_dong_ma():
    """register_publish soi gương g2/URL về bảng Content. `content_id` lạ nghĩa là meta.json
    sai — thêm một dòng rỗng vào sổ chỉ giấu cái sai đó đi."""
    body = "<!-- T:BEGIN -->\n| id | x |\n|---|---|\n| a | 1 |\n<!-- T:END -->\n"
    with pytest.raises(KeyError, match="chỉ-cập-nhật"):
        M.upsert_row(body, "T", "id", {"id": "LA", "x": "9"}, chi_cap_nhat=True)

    # dòng có thật thì vẫn cập nhật bình thường
    ra = M.upsert_row(body, "T", "id", {"id": "a", "x": "9"}, chi_cap_nhat=True)
    assert M.read_table(ra, "T")[1][0]["x"] == "9"
