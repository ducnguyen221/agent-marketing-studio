# -*- coding: utf-8 -*-
"""`scripts/pipeline/run_pipeline.py` — điều phối đường ống TRONG PHIÊN.

Đây là lối vào một cửa cho agent ngồi cùng người. Bốn thứ file này canh:

· **Không bao giờ tự mở cổng.** Agent chạy được mọi bước máy, nhưng cổng là của người. Một
  điều phối tự gật là toàn bộ ba cổng thành trang trí.
· **Tới cổng thì DỪNG và kê file.** Cổng mà không nói đọc ở đâu thì người gật bừa — đúng
  chỗ Cổng 2 đã dính 11/09/2026.
· **Kết luận theo ARTEFACT, không theo mã thoát.** Cả hai chiều: mã khác 0 mà có artefact
  là XONG; mã 0 mà không có artefact là HỎNG.
· **Chế độ theo giai đoạn phải gom bài lại.** Nếu nó đẩy lần lượt từng bài tới cổng thì
  người bị hỏi N lần — đúng thứ chế độ này sinh ra để tránh.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import run_pipeline as Q  # noqa: E402
import approval_gate as CD  # noqa: E402

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
| T-001 | Bài một | ai-agent | explainer | awareness | high | approved | 2026-09-01 |  | 2026-09-15 |  | ./T-001_bai-mot |  |
| T-002 | Bài hai | ai-agent | explainer | awareness | high | approved | 2026-09-01 |  | 2026-09-16 |  | ./T-002_bai-hai |  |
| T-003 | Bài ba | ai-agent | explainer | awareness | high | proposed |  |  | 2026-09-17 |  | ./T-003_bai-ba |  |
<!-- CONTENT:END -->
"""

THAN = "Câu chuyện đời thường mở bài. " * 60


def _cam(tmp_path):
    cam = tmp_path / "tram" / "kenh-thu" / "CD-THU"
    (cam / "logs").mkdir(parents=True)
    (cam / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")
    for c, slug in (("T-001", "bai-mot"), ("T-002", "bai-hai")):
        (cam / f"{c}_{slug}").mkdir()
    return cam


def _thu_muc(cam, cid):
    return {"T-001": cam / "T-001_bai-mot",
            "T-002": cam / "T-002_bai-hai",
            "T-003": cam / "T-003_bai-ba"}[cid]


def _chay_gia(cam, lenh, cid):
    """Bộ chạy giả: `soan` viết bài, `__cham_cong__` chấm xanh. Trả về (mã sạch, log)."""
    bai = _thu_muc(cam, cid)
    if lenh == "soan":
        bai.mkdir(exist_ok=True)
        (bai / "content.md").write_text(f"## post:blog_article\n\n# Bài\n\n{THAN}\n",
                                        encoding="utf-8", newline="\n")
        return True, "đã viết"
    if lenh == "__cham_cong__":
        (bai / "gates.json").write_text(
            '{"tong": 23, "xanh": 23, "do_chan": 0, "ket_luan": "xanh", "cong": []}',
            encoding="utf-8", newline="\n")
        return True, "xanh"
    return True, ""


# ── Không tự mở cổng ────────────────────────────────────────────────────────

def test_KHONG_BAO_GIO_tu_mo_cong(tmp_path):
    """Chạy hết đường ống cũng không được ghi một cổng nào. Cổng là của người."""
    cam = _cam(tmp_path)
    Q.chay(cam, che_do="tung-bai", bai=["T-001"], chay_buoc=_chay_gia)
    d = {x["content_id"]: x for x in CD.doc_bang(cam)[3]}
    assert not (d["T-001"].get("g2") or "").strip(), "điều phối tự mở Cổng 2"
    assert not (d["T-003"].get("g1") or "").strip(), "điều phối tự mở Cổng 1"


def test_dung_dung_o_cong_va_KE_FILE_de_nguoi_mo(tmp_path):
    cam = _cam(tmp_path)
    kq = Q.chay(cam, che_do="tung-bai", bai=["T-001"], chay_buoc=_chay_gia)
    assert "g2" in kq["dung_o_cong"], kq["dung_o_cong"]
    h = kq["dung_o_cong"]["g2"][0]
    assert h["content_id"] == "T-001"
    assert h["file"]["bài"].endswith("content.md")
    assert h["file"]["chấm cổng"].endswith("gates.json")
    for p in h["file"].values():
        assert Path(p).is_file(), f"kê file không có thật: {p}"


def test_di_qua_NHIEU_buoc_trong_mot_luot(tmp_path):
    """Đi một bước rồi trả về là bắt agent gọi lại năm lần cho một bài."""
    cam = _cam(tmp_path)
    kq = Q.chay(cam, che_do="tung-bai", bai=["T-001"], chay_buoc=_chay_gia)
    assert [r["buoc"] for r in kq["da_chay"]] == ["soan", "cham-cong"]


# ── Artefact chứ không phải mã thoát ────────────────────────────────────────

def test_ma_thoat_KHAC_0_ma_CO_artefact_van_la_XONG(tmp_path):
    """`blog_gates` trả 1 khi cổng đỏ, `soan` trả khác 0 khi bài chưa đạt — đã làm xong việc.

    Đọc mã thoát rồi kết luận hỏng thì bài bị làm lại ba lần rồi vứt đi. Đo thật 12/09/2026:
    một lượt như thế đốt 27 phút agent.
    """
    cam = _cam(tmp_path)

    def ban(cam_, lenh, cid):
        _chay_gia(cam_, lenh, cid)
        return False, "mã 1 — cổng đỏ"

    kq = Q.chay(cam, che_do="tung-bai", bai=["T-001"], chay_buoc=ban)
    assert kq["hong"] == [], kq["hong"]
    assert all(r["xong"] for r in kq["da_chay"])


def test_ma_thoat_0_ma_KHONG_ra_artefact_la_HONG(tmp_path):
    """Chiều kia của cùng một luật: bộ viết chạy êm mà file vẫn trống thì vẫn là hỏng."""
    cam = _cam(tmp_path)
    kq = Q.chay(cam, che_do="tung-bai", bai=["T-001"],
                chay_buoc=lambda c, l, i: (True, "im lặng"))
    assert kq["hong"], "mã 0 mà không sinh artefact vẫn được tính là xong"
    assert kq["hong"][0]["buoc"] == "soan"


def test_buoc_hong_thi_DUNG_khong_day_tiep(tmp_path):
    cam = _cam(tmp_path)
    kq = Q.chay(cam, che_do="tung-bai", bai=["T-001"],
                chay_buoc=lambda c, l, i: (True, ""))
    assert len(kq["da_chay"]) == 1, "bước hỏng rồi vẫn chạy bước sau"


# ── Chế độ theo giai đoạn ───────────────────────────────────────────────────

def test_theo_giai_doan_GOM_ca_lo_qua_tung_buoc(tmp_path):
    """Cả lô phải đi hết bước 1 rồi mới sang bước 2 — nếu không thì người bị hỏi N lần."""
    cam = _cam(tmp_path)
    kq = Q.chay(cam, che_do="theo-giai-doan", bai=["T-001", "T-002"], chay_buoc=_chay_gia)
    thu_tu = [(r["bai"], r["buoc"]) for r in kq["da_chay"]]
    assert thu_tu == [("T-001", "soan"), ("T-002", "soan"),
                      ("T-001", "cham-cong"), ("T-002", "cham-cong")], thu_tu
    assert sorted(h["content_id"] for h in kq["dung_o_cong"]["g2"]) == ["T-001", "T-002"]


def test_mot_bai_chi_vao_nhom_cho_cong_MOT_lan(tmp_path):
    cam = _cam(tmp_path)
    kq = Q.chay(cam, che_do="theo-giai-doan", bai=["T-001"], chay_buoc=_chay_gia)
    assert len(kq["dung_o_cong"]["g2"]) == 1


# ── Chọn bài ────────────────────────────────────────────────────────────────

def test_khong_chi_dinh_thi_BO_QUA_bai_dang_cho_cong(tmp_path):
    """T-003 chưa qua Cổng 1. Đưa nó vào lô là mời agent chạy bước nó không được phép chạy."""
    cam = _cam(tmp_path)
    assert Q.chon_bai(cam, bai=None, so_bai=0) == ["T-001", "T-002"]


def test_so_bai_gioi_han_dung_N(tmp_path):
    cam = _cam(tmp_path)
    assert Q.chon_bai(cam, bai=None, so_bai=1) == ["T-001"]


def test_bai_khong_co_trong_bang_thi_NEM_LOI(tmp_path):
    """Bỏ qua im lặng thì người tưởng đã chạy bài đó rồi."""
    cam = _cam(tmp_path)
    with pytest.raises(ValueError):
        Q.chon_bai(cam, bai=["T-404"], so_bai=None)


def test_che_do_la_thi_nem_loi(tmp_path):
    cam = _cam(tmp_path)
    with pytest.raises(ValueError):
        Q.chay(cam, che_do="tuy-hung", chay_buoc=_chay_gia)


# ── dry-run và mã thoát ─────────────────────────────────────────────────────

def test_dry_run_KHONG_chay_gi(tmp_path):
    cam = _cam(tmp_path)

    def no(*a, **k):
        raise AssertionError("dry-run mà vẫn gọi bước")

    kq = Q.chay(cam, che_do="tung-bai", bai=["T-001"], dry_run=True, chay_buoc=no)
    assert kq["ke_hoach"] == [{"bai": "T-001", "buoc_ke": "soan"}]
    assert not (_thu_muc(cam, "T-001") / "content.md").exists()


def test_dung_o_cong_KHONG_phai_la_hong_ma_thoat_0(tmp_path, monkeypatch):
    """Dừng ở cổng là kết quả ĐÚNG của đường ống có cổng người, không phải sự cố.

    Trả khác 0 ở đây thì mọi lớp gọi bên ngoài (thợ, runner, notify-run) đều báo ❌ cho một
    lượt chạy hoàn hảo.
    """
    cam = _cam(tmp_path)
    monkeypatch.setattr(Q.TV, "_chay_buoc", _chay_gia)
    assert Q.main([str(cam), "chay", "--bai", "T-001"]) == 0


def test_buoc_hong_thi_ma_thoat_3(tmp_path, monkeypatch):
    cam = _cam(tmp_path)
    monkeypatch.setattr(Q.TV, "_chay_buoc", lambda c, l, i: (True, ""))
    assert Q.main([str(cam), "chay", "--bai", "T-001"]) == 3


def test_khong_thay_campaign_thi_ma_2(tmp_path):
    assert Q.main([str(tmp_path / "khong-co"), "tinh-hinh"]) == 2


# ── Tình hình ───────────────────────────────────────────────────────────────

def test_tinh_hinh_xep_theo_THU_TU_duong_ong(tmp_path):
    """Người cần thấy bài tắc ở đâu trên đường, không cần bảng chữ cái."""
    cam = _cam(tmp_path)
    t = Q.tinh_hinh(cam)
    assert t["tong"] == 3
    assert list(t["theo_buoc"]) == ["cho-G1", "soan"], t["theo_buoc"]
    assert t["theo_buoc"]["cho-G1"] == ["T-003"]
