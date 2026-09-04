# -*- coding: utf-8 -*-
"""Test cho blog_gates.py — khẳng định cổng ĐỎ ĐÚNG LÝ DO, không chỉ đỏ.

Một bộ test chỉ chạy trên dữ liệu đẹp sẽ xanh mãi kể cả khi cổng đã hỏng hoàn toàn.
Nên ở đây có ba loại khẳng định, và thiếu loại nào cũng để lọt một kiểu hỏng:

  1. Trên `fixtures/bai_do/` — đỏ đúng TẬP mã cổng, và đúng SỐ ĐO. Nếu chỉ khẳng định
     "có đỏ" thì một cổng bắt nhầm lý do vẫn qua được.
  2. Trên bài hợp lệ dựng tại chỗ — KHÔNG cổng nào đỏ. Bắt ca cổng kêu oan, thứ khiến
     người ta tắt cổng đi và từ đó cổng thành đồ trang trí.
  3. Thiếu đầu vào phải ra trạng thái "thiếu", KHÔNG phải "xanh". Cổng báo xanh cho
     thứ nó chưa hề đo là cổng nói dối.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import blog_gates as G  # noqa: E402
import fb_format as FF  # noqa: E402

BAI_DO = ROOT / "fixtures" / "bai_do"
HOME = "ducnguyen.vn"


def _theo_ma(kq):
    return {r["ma"]: r for r in kq["cong"]}


# ------------------------------------------------------------------ 1. fixture đỏ

@pytest.fixture(scope="module")
def do():
    return _theo_ma(G.chay(BAI_DO, HOME))


def test_fixture_do_ton_tai():
    assert (BAI_DO / "blog.md").exists(), "fixture đỏ bị xoá -> mọi khẳng định dưới đây vô nghĩa"


def test_dung_tap_cong_bi_chan(do):
    chan = {ma for ma, r in do.items() if r["trang_thai"] == "do" and r["muc"] == G.CHAN}
    assert chan == {"G01", "G02", "G05", "G06", "G08", "G09", "G11",
                    "G12", "G13", "G14", "G17", "G18", "G19", "G20"}


def test_dung_tap_cong_canh_bao(do):
    cb = {ma for ma, r in do.items() if r["trang_thai"] == "do" and r["muc"] == G.CANH_BAO}
    assert cb == {"G04", "G07", "G10", "G15"}, "cảnh báo không được leo thành chặn"


def test_cong_xanh_khong_bi_do_lay(do):
    """Bài sai nhiều thứ nhưng CÓ bảng và KHÔNG lộ tên tool -> ba cổng này phải xanh."""
    assert do["G03"]["trang_thai"] == "xanh"
    assert do["G21"]["trang_thai"] == "xanh"
    assert do["G22"]["trang_thai"] == "xanh"


def test_so_do_dung_chu_khong_chi_do(do):
    """Đây là phần phân biệt 'đỏ' với 'đỏ đúng lý do'."""
    assert do["G02"]["do_duoc"] == 3            # 3 H2, ngưỡng 6-12
    assert do["G05"]["do_duoc"] == 0            # 0 nguồn ngoài
    assert do["G06"]["do_duoc"] == 0            # 0 khối chính kiến
    assert do["G08"]["do_duoc"] == 2            # 2 dấu [KIỂM CHỨNG] còn mở
    assert do["G09"]["do_duoc"] == 2            # 2 URL trong thân post
    assert do["G11"]["do_duoc"] == 0            # 0 ký tự bold
    assert do["G13"]["do_duoc"] == 2            # 2 hashtag, ngưỡng 6-13
    assert do["G17"]["do_duoc"] == 5            # 5 scene, cần 8
    assert do["G18"]["do_duoc"] == 0            # 0 thẻ og:
    assert do["G20"]["do_duoc"] == "95 / 1"     # tóm tắt 95 từ, 1 key-term


def test_cong_noi_ra_bang_chung_cu_the(do):
    """Cổng phải chỉ được chỗ sai, không chỉ nói 'sai'."""
    assert "https://" in do["G09"]["ghi_chu"], "G09 phải liệt kê chính các URL nó bắt được"


def test_khong_suy_dien_hau_qua(do):
    """Luật phát ngôn: cổng chỉ nói cái nó ĐO ĐƯỢC."""
    cam = ["reach", "bóp", "thuật toán", "sẽ bị", "chất lượng kém", "bài dở"]
    for ma, r in do.items():
        van_ban = f"{r['cong']} {r['ghi_chu']}".lower()
        for tu in cam:
            assert tu not in van_ban, f"{ma} suy diễn hậu quả thay vì báo số đo: {r}"


# ------------------------------------------------------------------ 2. bài hợp lệ

@pytest.fixture
def bai_xanh(tmp_path):
    d = tmp_path / "bai"
    d.mkdir()
    than = "\n\n".join(
        [f"## Mục {i}\n\nMột đoạn nội dung. " * 3 for i in range(1, 9)]
    )
    (d / "blog.md").write_text(
        "# Tiêu đề\n\n" + than + "\n\n"
        + "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        + "".join(f"> 💡 Callout số {i}\n\n" for i in range(1, 5))
        + "> **Góc nhìn:** chính kiến của tác giả.\n\n"
        + "Theo Reuters, số liệu như vậy. Theo mình thì khác.\n\n"
        + "\n".join(f"- Nguồn {i}: https://vidu{i}.com/bai-viet (truy cập 04/09/2026)"
                    for i in range(1, 5))
        # Đệm cho bài rơi vào dải 2500-4000 từ. Con số 500 chọn bằng cách ĐO rồi chỉnh:
        # 900 cho ra 4748 từ và làm G01 đỏ — tức fixture sai, không phải cổng sai.
        + "\n\n" + "thêm chữ cho đủ dài. " * 500,
        encoding="utf-8")
    (d / "fb_post.txt").write_text(
        FF.bold("Tiêu đề đậm") + "\n\n" + "Nội dung bài. " * 400 + "\n\n"
        + "#AI #Data #CongNghe #Prompt #Agent #HocMai\n", encoding="utf-8")
    (d / "fb_comment.txt").write_text(
        "Bản đầy đủ 👇\nhttps://ducnguyen.vn/atlas/content/ai/x.html\n", encoding="utf-8")
    (d / "podcast.txt").write_text("từ " * 850, encoding="utf-8")
    (d / "scenes.json").write_text(
        json.dumps({"scenes": [{"id": i} for i in range(8)]}), encoding="utf-8")
    (d / "atlas.html").write_text(
        "".join(f'<meta property="og:{k}" content="x">'
                for k in ("type", "title", "description", "url", "image", "site_name")),
        encoding="utf-8")
    (d / "continuity.json").write_text(
        json.dumps({"summary": "Tóm tắt ngắn gọn.",
                    "key_terms_explained": ["a", "b", "c"]}, ensure_ascii=False),
        encoding="utf-8")
    (d / "fb_image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (d / "fb_image.prompt.txt").write_text("prompt đã dùng để sinh ảnh", encoding="utf-8")
    return d


def test_bai_hop_le_khong_bi_keu_oan(bai_xanh):
    kq = G.chay(bai_xanh, HOME)
    do_ra = [(r["ma"], r["cong"], r["do_duoc"], r["luat"])
             for r in kq["cong"] if r["trang_thai"] == "do"]
    assert do_ra == [], f"cổng kêu oan trên bài hợp lệ: {do_ra}"


# ------------------------------------------------------------------ 3. thiếu ≠ xanh

def test_thieu_dau_vao_khong_duoc_bao_xanh(tmp_path):
    kq = G.chay(tmp_path, HOME)
    theo = _theo_ma(kq)
    assert theo["G01"]["trang_thai"] == "thieu"
    assert theo["G18"]["trang_thai"] == "thieu"
    assert kq["xanh"] == 0, "thư mục rỗng mà có cổng xanh = cổng đang nói dối"
    assert kq["thieu"] == 21


def test_cli_ghi_gates_json_va_exit_khac_0(tmp_path):
    d = tmp_path / "bai_do"
    shutil.copytree(BAI_DO, d)
    assert G.main([str(d), "--home-domain", HOME, "--json-only"]) == 1
    ghi = json.loads((d / "gates.json").read_text(encoding="utf-8"))
    assert ghi["tong"] == 22 and ghi["ket_luan"] == "do"
