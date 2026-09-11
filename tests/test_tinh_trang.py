# -*- coding: utf-8 -*-
"""`scripts/lib/tinh_trang.py` — bước kế tiếp SUY RA từ sự thật, không từ sổ riêng.

Mỗi test chốt MỘT nấc của đường ống. Nếu một nấc bị nhảy cóc thì agent nối lại việc sẽ
chạy sai bước — ví dụ đem đi đăng một bài chưa ai chấm cổng.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import tinh_trang as TT  # noqa: E402

FM = """---
schema: campaign/1
id: CD-THU
channel: kenh-thu
id_prefix: T
name: Thử
status: active
content_pillar: ai-agent
---

# Thử

<!-- CONTENT:BEGIN -->
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | schedule | published | folder | web |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | Bài một | ai-agent | explainer | awareness | high | proposed |  |  | 2026-09-15 |  |  |  |
<!-- CONTENT:END -->
"""


def _cam(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / "campaign.md").write_text(FM, encoding="utf-8")
    return tmp_path


def _dong(**ghi_de):
    d = {"content_id": "T-001", "g1": "", "g2": "", "folder": "", "web": "", "published": ""}
    d.update(ghi_de)
    return d


def _bai(cam, ten="T-001_bai", *, viet_that=True):
    b = cam / ten
    b.mkdir(parents=True, exist_ok=True)
    if viet_that:
        (b / "content.md").write_text(
            "## post:blog_article\n\n# Tiêu đề\n\n" + "Câu chuyện đời thường. " * 60,
            encoding="utf-8")
    else:
        (b / "content.md").write_text(
            "## post:blog_article\n\n> Chỉ dẫn khuôn.\n\n# {{tieu_de}}\n\n{{than}}\n",
            encoding="utf-8")
    return b


def _gates(bai, ket_luan):
    (bai / "gates.json").write_text(
        json.dumps({"tong": 23, "ket_luan": ket_luan, "do_chan": 0, "cong": []}),
        encoding="utf-8")


# ── từng nấc của đường ống ──────────────────────────────────────────────────

def test_chua_duyet_de_tai_thi_cho_G1(tmp_path):
    assert TT.buoc_ke(_cam(tmp_path), _dong()) == "cho-G1"


def test_duyet_de_tai_nhung_chua_co_thu_muc_thi_dung_bai(tmp_path):
    cam = _cam(tmp_path)
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01")) == "dung-bai"


def test_khai_folder_nhung_thu_muc_KHONG_TON_TAI_van_la_dung_bai(tmp_path):
    """Khai trong bảng không chứng minh thư mục có thật. Fail-closed, không nhảy cóc."""
    cam = _cam(tmp_path)
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", folder="./T-001_khong-co")) == "dung-bai"


def test_co_thu_muc_nhung_con_KHUON_thi_soan(tmp_path):
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", folder="./T-001_bai")) == "soan"


def test_viet_xong_nhung_CHUA_CHAM_thi_cham_cong(tmp_path):
    """Ca thật NEN-002: gọi thẳng bộ viết, nhảy cóc bước chấm, file bài trông hoàn hảo."""
    cam = _cam(tmp_path)
    _bai(cam)
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", folder="./T-001_bai")) == "cham-cong"


def test_cham_roi_ma_DO_thi_sua_loi_cong(tmp_path):
    cam = _cam(tmp_path)
    _gates(_bai(cam), "do")
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", folder="./T-001_bai")) == "sua-loi-cong"


def test_gates_HONG_coi_nhu_chua_cham(tmp_path):
    """Sổ cổng rách thì lùi về chấm lại, KHÔNG được coi là đã qua."""
    cam = _cam(tmp_path)
    b = _bai(cam)
    (b / "gates.json").write_text("{ rách", encoding="utf-8")
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", folder="./T-001_bai")) == "cham-cong"


def test_cong_xanh_nhung_chua_duyet_noi_dung_thi_cho_G2(tmp_path):
    cam = _cam(tmp_path)
    _gates(_bai(cam), "xanh")
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", folder="./T-001_bai")) == "cho-G2"


def test_duyet_noi_dung_roi_thi_dung_trang(tmp_path):
    cam = _cam(tmp_path)
    _gates(_bai(cam), "xanh")
    assert TT.buoc_ke(
        cam, _dong(g1="2026-09-01", g2="2026-09-02", folder="./T-001_bai")) == "dung-trang"


def test_len_web_roi_thi_phat_hanh(tmp_path):
    cam = _cam(tmp_path)
    _gates(_bai(cam), "xanh")
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", g2="2026-09-02",
                                 folder="./T-001_bai", web="https://x/y")) == "phat-hanh"


def test_dang_roi_thi_xong(tmp_path):
    cam = _cam(tmp_path)
    _gates(_bai(cam), "xanh")
    assert TT.buoc_ke(cam, _dong(g1="2026-09-01", g2="2026-09-02", folder="./T-001_bai",
                                 web="https://x/y", published="2026-09-03")) == "xong"


# ── tính chất của cả bản ────────────────────────────────────────────────────

def test_KHONG_GHI_GI_ra_dia(tmp_path):
    """Module này chỉ ĐỌC. Ghi ra đĩa là đẻ nguồn sự thật thứ hai — thứ cả hệ đang tránh."""
    cam = _cam(tmp_path)
    truoc = {p.name: p.stat().st_mtime_ns for p in cam.rglob("*") if p.is_file()}
    TT.tinh(cam)
    TT.tom_tat(cam)
    TT.dang_chu(cam, chi_tiet=True)
    sau = {p.name: p.stat().st_mtime_ns for p in cam.rglob("*") if p.is_file()}
    assert truoc == sau, f"đã ghi/sửa file: {set(sau) ^ set(truoc)}"


def test_buoc_can_nguoi_duoc_danh_dau(tmp_path):
    """Thợ chỉ được nhặt việc MÁY làm được. Nhầm chỗ này là agent tự mở cổng duyệt."""
    cam = _cam(tmp_path)
    x = TT.tinh(cam)[0]
    assert x["buoc"] == "cho-G1" and x["can_nguoi"] is True
    assert TT.CAN_NGUOI == {"cho-G1", "cho-G2", "cho-G3"}


def test_ban_suy_ra_RE_HON_HAN_doc_ca_campaign(tmp_path):
    """Lý do tồn tại của module: rẻ hơn nạp cả `campaign.md`.

    Số đo thật 11/09/2026 trên chiến dịch 90 bài: cả file 38.220 ký tự, bản suy ra 1.390.
    Test giữ cho tỉ lệ đó không âm thầm xấu đi khi ai đó thêm cột vào bản in.
    """
    cam = _cam(tmp_path)
    ca_file = (cam / "campaign.md").read_text(encoding="utf-8")
    assert len(TT.dang_chu(cam, chi_tiet=True)) < len(ca_file) / 3, "bản suy ra phình quá"


def test_tom_tat_sap_theo_THU_TU_duong_ong(tmp_path):
    cam = _cam(tmp_path)
    assert list(TT.tom_tat(cam)) == ["cho-G1"]
    assert TT.THU_TU.index("soan") < TT.THU_TU.index("cho-G2") < TT.THU_TU.index("xong")


# ── CỔNG 3: chỗ ở, và tương thích ngược ─────────────────────────────────────

FM_CO_G3 = FM.replace(
    "| priority | status | g1 | g2 | schedule | published | folder | web |",
    "| priority | status | g1 | g2 | g3 | schedule | published | folder | web |"
).replace(
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
).replace(
    "| high | proposed |  |  | 2026-09-15 |  |  |  |",
    "| high | proposed |  |  |  | 2026-09-15 |  |  |  |")


def _cam_g3(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / "campaign.md").write_text(FM_CO_G3, encoding="utf-8", newline="\n")
    return tmp_path


def test_BANG_CU_khong_co_cot_g3_thi_bo_qua_Cong_3(tmp_path):
    """Tương thích ngược: chiến dịch cũ không có cột `g3` phải chạy y như trước.

    Thêm một cổng mà làm đứng hết các chiến dịch đang chạy là cái giá không đáng trả. Không
    khai cột = không bật Cổng 3, đi thẳng tới phát hành.
    """
    cam = _cam(tmp_path)
    _gates(_bai(cam), "xanh")
    d = _dong(g1="2026-09-01", g2="2026-09-02", folder="./T-001_bai", web="https://x/y")
    assert TT.buoc_ke(cam, d) == "phat-hanh"


def test_CO_cot_g3_nhung_TRONG_thi_dung_o_cho_G3(tmp_path):
    """Khai cột = bật cổng. Trang đã sống nhưng chưa ai mở link xem bằng mắt."""
    cam = _cam_g3(tmp_path)
    _gates(_bai(cam), "xanh")
    d = _dong(g1="2026-09-01", g2="2026-09-02", g3="", folder="./T-001_bai",
              web="https://x/y")
    assert TT.buoc_ke(cam, d) == "cho-G3"


def test_g3_da_duyet_thi_di_tiep_phat_hanh(tmp_path):
    cam = _cam_g3(tmp_path)
    _gates(_bai(cam), "xanh")
    d = _dong(g1="2026-09-01", g2="2026-09-02", g3="2026-09-03",
              folder="./T-001_bai", web="https://x/y")
    assert TT.buoc_ke(cam, d) == "phat-hanh"


def test_cho_G3_la_buoc_CAN_NGUOI(tmp_path):
    """Thợ không được tự mở Cổng 3. Nó là chỗ người mở link xem bằng mắt."""
    assert "cho-G3" in TT.CAN_NGUOI


def test_chua_len_web_thi_KHONG_hoi_Cong_3(tmp_path):
    """Cổng 3 duyệt BẢN THẬT. Chưa có trang thật thì chưa có gì để xem."""
    cam = _cam_g3(tmp_path)
    _gates(_bai(cam), "xanh")
    d = _dong(g1="2026-09-01", g2="2026-09-02", g3="", folder="./T-001_bai", web="")
    assert TT.buoc_ke(cam, d) == "dung-trang"
