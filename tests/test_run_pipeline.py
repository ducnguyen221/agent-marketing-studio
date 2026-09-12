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
import run_pipeline as RP  # noqa: E402
import approval_gate as AG  # noqa: E402

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
    campaign = tmp_path / "tram" / "kenh-thu" / "CD-THU"
    (campaign / "logs").mkdir(parents=True)
    (campaign / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")
    for c, slug in (("T-001", "bai-mot"), ("T-002", "bai-hai")):
        (campaign / f"{c}_{slug}").mkdir()
    return campaign


def _thu_muc(campaign, cid):
    return {"T-001": campaign / "T-001_bai-mot",
            "T-002": campaign / "T-002_bai-hai",
            "T-003": campaign / "T-003_bai-ba"}[cid]


def _chay_gia(campaign, cmd, cid):
    """Bộ chạy giả: `soan` viết bài, `__check_gates__` chấm xanh. Trả về (mã sạch, log)."""
    post = _thu_muc(campaign, cid)
    if cmd == "write":
        post.mkdir(exist_ok=True)
        (post / "content.md").write_text(f"## post:blog_article\n\n# Bài\n\n{THAN}\n",
                                        encoding="utf-8", newline="\n")
        return True, "đã viết"
    if cmd == "__check_gates__":
        (post / "gates.json").write_text(
            '{"tong": 23, "xanh": 23, "do_chan": 0, "ket_luan": "xanh", "cong": []}',
            encoding="utf-8", newline="\n")
        return True, "pass"
    return True, ""


# ── Không tự mở cổng ────────────────────────────────────────────────────────

def test_KHONG_BAO_GIO_tu_mo_cong(tmp_path):
    """Chạy hết đường ống cũng không được ghi một cổng nào. Cổng là của người."""
    campaign = _cam(tmp_path)
    RP.run(campaign, mode="tung-bai", post=["T-001"], run_step=_chay_gia)
    d = {x["content_id"]: x for x in AG.read_content_table(campaign)[3]}
    assert not (d["T-001"].get("g2") or "").strip(), "điều phối tự mở Cổng 2"
    assert not (d["T-003"].get("g1") or "").strip(), "điều phối tự mở Cổng 1"


def test_dung_dung_o_cong_va_KE_FILE_de_nguoi_mo(tmp_path):
    campaign = _cam(tmp_path)
    result = RP.run(campaign, mode="tung-bai", post=["T-001"], run_step=_chay_gia)
    assert "g2" in result["waiting"], result["waiting"]
    h = result["waiting"]["g2"][0]
    assert h["content_id"] == "T-001"
    assert h["file"]["bài"].endswith("content.md")
    assert h["file"]["chấm cổng"].endswith("gates.json")
    for p in h["file"].values():
        assert Path(p).is_file(), f"kê file không có thật: {p}"


def test_di_qua_NHIEU_buoc_trong_mot_luot(tmp_path):
    """Đi một bước rồi trả về là bắt agent gọi lại năm lần cho một bài."""
    campaign = _cam(tmp_path)
    result = RP.run(campaign, mode="tung-bai", post=["T-001"], run_step=_chay_gia)
    assert [r["step"] for r in result["ran"]] == ["write", "check-gates"]


# ── Artefact chứ không phải mã thoát ────────────────────────────────────────

def test_ma_thoat_KHAC_0_ma_CO_artefact_van_la_XONG(tmp_path):
    """`blog_gates` trả 1 khi cổng đỏ, `soan` trả khác 0 khi bài chưa đạt — đã làm xong việc.

    Đọc mã thoát rồi kết luận hỏng thì bài bị làm lại ba lần rồi vứt đi. Đo thật 12/09/2026:
    một lượt như thế đốt 27 phút agent.
    """
    campaign = _cam(tmp_path)

    def ban(cam_, cmd, cid):
        _chay_gia(cam_, cmd, cid)
        return False, "mã 1 — cổng đỏ"

    result = RP.run(campaign, mode="tung-bai", post=["T-001"], run_step=ban)
    assert result["failed"] == [], result["failed"]
    assert all(r["done"] for r in result["ran"])


def test_ma_thoat_0_ma_KHONG_ra_artefact_la_HONG(tmp_path):
    """Chiều kia của cùng một luật: bộ viết chạy êm mà file vẫn trống thì vẫn là hỏng."""
    campaign = _cam(tmp_path)
    result = RP.run(campaign, mode="tung-bai", post=["T-001"],
                run_step=lambda c, l, i: (True, "im lặng"))
    assert result["failed"], "mã 0 mà không sinh artefact vẫn được tính là xong"
    assert result["failed"][0]["step"] == "write"


def test_buoc_hong_thi_DUNG_khong_day_tiep(tmp_path):
    campaign = _cam(tmp_path)
    result = RP.run(campaign, mode="tung-bai", post=["T-001"],
                run_step=lambda c, l, i: (True, ""))
    assert len(result["ran"]) == 1, "bước hỏng rồi vẫn chạy bước sau"


# ── Chế độ theo giai đoạn ───────────────────────────────────────────────────

def test_theo_giai_doan_GOM_ca_lo_qua_tung_buoc(tmp_path):
    """Cả lô phải đi hết bước 1 rồi mới sang bước 2 — nếu không thì người bị hỏi N lần."""
    campaign = _cam(tmp_path)
    result = RP.run(campaign, mode="theo-giai-doan", post=["T-001", "T-002"], run_step=_chay_gia)
    thu_tu = [(r["post"], r["step"]) for r in result["ran"]]
    assert thu_tu == [("T-001", "write"), ("T-002", "write"),
                      ("T-001", "check-gates"), ("T-002", "check-gates")], thu_tu
    assert sorted(h["content_id"] for h in result["waiting"]["g2"]) == ["T-001", "T-002"]


def test_mot_bai_chi_vao_nhom_cho_cong_MOT_lan(tmp_path):
    campaign = _cam(tmp_path)
    result = RP.run(campaign, mode="theo-giai-doan", post=["T-001"], run_step=_chay_gia)
    assert len(result["waiting"]["g2"]) == 1


# ── Chọn bài ────────────────────────────────────────────────────────────────

def test_khong_chi_dinh_thi_BO_QUA_bai_dang_cho_cong(tmp_path):
    """T-003 chưa qua Cổng 1. Đưa nó vào lô là mời agent chạy bước nó không được phép chạy."""
    campaign = _cam(tmp_path)
    assert RP.pick_posts(campaign, post=None, count=0) == ["T-001", "T-002"]


def test_so_bai_gioi_han_dung_N(tmp_path):
    campaign = _cam(tmp_path)
    assert RP.pick_posts(campaign, post=None, count=1) == ["T-001"]


def test_bai_khong_co_trong_bang_thi_NEM_LOI(tmp_path):
    """Bỏ qua im lặng thì người tưởng đã chạy bài đó rồi."""
    campaign = _cam(tmp_path)
    with pytest.raises(ValueError):
        RP.pick_posts(campaign, post=["T-404"], count=None)


def test_che_do_la_thi_nem_loi(tmp_path):
    campaign = _cam(tmp_path)
    with pytest.raises(ValueError):
        RP.run(campaign, mode="tuy-hung", run_step=_chay_gia)


# ── dry-run và mã thoát ─────────────────────────────────────────────────────

def test_dry_run_KHONG_chay_gi(tmp_path):
    campaign = _cam(tmp_path)

    def no(*a, **k):
        raise AssertionError("dry-run mà vẫn gọi bước")

    result = RP.run(campaign, mode="tung-bai", post=["T-001"], dry_run=True, run_step=no)
    assert result["plan"] == [{"post": "T-001", "next_step": "write"}]
    assert not (_thu_muc(campaign, "T-001") / "content.md").exists()


def test_dung_o_cong_KHONG_phai_la_hong_ma_thoat_0(tmp_path, monkeypatch):
    """Dừng ở cổng là kết quả ĐÚNG của đường ống có cổng người, không phải sự cố.

    Trả khác 0 ở đây thì mọi lớp gọi bên ngoài (thợ, runner, notify-run) đều báo ❌ cho một
    lượt chạy hoàn hảo.
    """
    campaign = _cam(tmp_path)
    monkeypatch.setattr(RP.WK, "_run_step", _chay_gia)
    assert RP.main([str(campaign), "run", "--post", "T-001"]) == 0


def test_buoc_hong_thi_ma_thoat_3(tmp_path, monkeypatch):
    campaign = _cam(tmp_path)
    monkeypatch.setattr(RP.WK, "_run_step", lambda c, l, i: (True, ""))
    assert RP.main([str(campaign), "run", "--post", "T-001"]) == 3


def test_khong_thay_campaign_thi_ma_2(tmp_path):
    assert RP.main([str(tmp_path / "khong-co"), "status"]) == 2


# ── Tình hình ───────────────────────────────────────────────────────────────

def test_tinh_hinh_xep_theo_THU_TU_duong_ong(tmp_path):
    """Người cần thấy bài tắc ở đâu trên đường, không cần bảng chữ cái."""
    campaign = _cam(tmp_path)
    t = RP.overview(campaign)
    assert t["total"] == 3
    assert list(t["by_step"]) == ["await-G1", "write"], t["by_step"]
    assert t["by_step"]["await-G1"] == ["T-003"]
