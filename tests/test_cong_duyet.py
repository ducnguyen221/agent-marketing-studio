# -*- coding: utf-8 -*-
"""`scripts/pipeline/cong_duyet.py` — kho cổng dùng chung + mặt tiền TRONG PHIÊN.

Trước 12/09/2026 chỉ Telegram ghi được `g1` và `g3`. Nghĩa là cách làm việc MẶC ĐỊNH —
người ngồi cùng agent trong một phiên, mở file trên máy rồi gật — không có đường ghi cổng
nào cả. File này canh bốn thứ của đường mới:

· **Cổng phải có chứng nhân.** Thiếu `boi` hoặc `nguyen_van` là ném lỗi, không phải ghi
  kèm cảnh báo. Một cổng ghi được mà không ai duyệt thì hồ sơ nói dối và không gì bắt được.
· **Idempotent.** Chạy lại không đổi gì và không sinh sự kiện thứ hai.
· **KHÔNG xếp việc.** Xếp việc là chính sách của MẶT TIỀN. Gộp vào kho thì Telegram xếp
  một lần, mặt tiền phiên xếp lần nữa, và bài chạy hai lượt.
· **Kê file CÓ THẬT.** Cổng mà không nói đọc ở đâu thì người chỉ còn cách gật bừa.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import cong_duyet as CD  # noqa: E402
import hang_cho as HC  # noqa: E402
import so_su_kien as SO  # noqa: E402

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
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | schedule | published | folder |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | Bài một | ai-agent | explainer | awareness | high | proposed |  |  | 2026-09-15 |  | ./T-001_bai-mot |
| T-002 | Bài hai | ai-agent | explainer | awareness | high | proposed |  |  | 2026-09-16 |  | ./T-002_bai-hai |
<!-- CONTENT:END -->
"""


def _cam(tmp_path):
    cam = tmp_path / "tram" / "kenh-thu" / "CD-THU"
    (cam / "logs").mkdir(parents=True)
    (cam / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")
    return cam


def _g1(cam, cid):
    return {d["content_id"]: d for d in CD.doc_bang(cam)[3]}[cid].get("g1", "").strip()


# ── Chứng nhân ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("boi,nguyen_van", [
    ("", "duyệt nhé"),
    ("   ", "duyệt nhé"),
    ("Đức", ""),
    ("Đức", "   "),
])
def test_thieu_chung_nhan_thi_KHONG_ghi_cong(tmp_path, boi, nguyen_van):
    """Không có tên người duyệt, hoặc không có câu người nói, thì cổng không mở."""
    cam = _cam(tmp_path)
    with pytest.raises(ValueError):
        CD.mo_cong(cam, "g1", ["T-001"], boi=boi, nguyen_van=nguyen_van, qua="phiên")
    assert _g1(cam, "T-001") == "", "ném lỗi rồi mà cổng vẫn ghi — fail-open"


def test_cong_la_thi_nem_loi(tmp_path):
    cam = _cam(tmp_path)
    with pytest.raises(ValueError):
        CD.mo_cong(cam, "g9", ["T-001"], boi="Đức", nguyen_van="ok", qua="phiên")


# ── Ghi cổng ────────────────────────────────────────────────────────────────

def test_mo_g1_ghi_cot_va_doi_status(tmp_path):
    cam = _cam(tmp_path)
    xong = CD.mo_cong(cam, "g1", ["T-001"], boi="Đức", nguyen_van="ok làm bài này",
                      qua="phiên")
    assert xong == ["T-001"]
    d = {x["content_id"]: x for x in CD.doc_bang(cam)[3]}["T-001"]
    assert d["g1"].strip(), "không ghi ngày qua cổng"
    assert d["status"].strip() == "approved"


def test_mo_cong_VAO_SO_SU_KIEN(tmp_path):
    """Sổ sự kiện là thứ duy nhất trả lời được *ai* duyệt và *qua đường nào*."""
    cam = _cam(tmp_path)
    CD.mo_cong(cam, "g1", ["T-001"], boi="Đức", nguyen_van="ok", qua="phiên")
    ds = [x for x in SO.doc(cam) if x["viec"] == "g1_duyet"]
    assert ds, [x["viec"] for x in SO.doc(cam)]
    assert ds[-1]["qua"] == "phiên", "không ghi lại đi qua mặt tiền nào"


def test_mo_lai_KHONG_ghi_de_va_KHONG_sinh_su_kien_thu_hai(tmp_path):
    """Idempotent: mặt tiền có thể gọi lại (bấm hai lần, chạy lại lệnh) — không được nhân đôi."""
    cam = _cam(tmp_path)
    CD.mo_cong(cam, "g1", ["T-001"], boi="Đức", nguyen_van="ok", qua="phiên")
    ngay_dau = _g1(cam, "T-001")
    lan_hai = CD.mo_cong(cam, "g1", ["T-001"], boi="ai đó", nguyen_van="ok lần nữa",
                         qua="phiên")
    assert lan_hai == [], "bài đã qua cổng vẫn báo là vừa mở"
    assert _g1(cam, "T-001") == ngay_dau, "ghi đè ngày duyệt cũ"
    assert len([x for x in SO.doc(cam) if x["viec"] == "g1_duyet"]) == 1


def test_bai_khong_co_trong_bang_thi_bo_qua_khong_no(tmp_path):
    cam = _cam(tmp_path)
    xong = CD.mo_cong(cam, "g1", ["T-001", "T-404"], boi="Đức", nguyen_van="ok",
                      qua="phiên")
    assert xong == ["T-001"]


def test_mo_cong_KHONG_xep_viec(tmp_path):
    """Xếp việc là chính sách của mặt tiền, không phải của kho cổng.

    Nếu kho tự xếp thì Telegram (vốn đã xếp) sẽ xếp hai lần, và agent trong phiên — vốn
    chạy bước kế tiếp NGAY — bỏ lại một việc thừa cho thợ chạy lại đúng việc vừa xong.
    """
    cam = _cam(tmp_path)
    truoc = HC.dem(cam)["cho"]
    CD.mo_cong(cam, "g1", ["T-001"], boi="Đức", nguyen_van="ok", qua="phiên")
    assert HC.dem(cam)["cho"] == truoc


# ── Từ chối ─────────────────────────────────────────────────────────────────

def test_tu_choi_ghi_phan_hoi_va_KHONG_mo_cong(tmp_path):
    cam = _cam(tmp_path)
    CD.tu_choi(cam, "g1", ["T-001"], boi="Đức", nguyen_van="mở bài dài quá", qua="phiên")
    assert _g1(cam, "T-001") == "", "từ chối mà cổng vẫn mở"
    ph = CD.doc_phan_hoi(cam, "T-001")
    assert ph and "dài quá" in ph[-1]["noi_dung"]
    assert any(x["viec"] == "g1_tu_choi" for x in SO.doc(cam))


def test_tu_choi_GIU_DU_phan_hoi_cu(tmp_path):
    """Vòng viết lại lặp được, nên ghi đè lần trước là mất dấu vết vì sao bài thành thế."""
    cam = _cam(tmp_path)
    CD.tu_choi(cam, "g1", ["T-001"], boi="Đức", nguyen_van="lần một", qua="phiên")
    CD.tu_choi(cam, "g1", ["T-001"], boi="Đức", nguyen_van="lần hai", qua="phiên")
    assert [x["noi_dung"] for x in CD.doc_phan_hoi(cam, "T-001")] == ["lần một", "lần hai"]


# ── Hồ sơ file để người mở kiểm ─────────────────────────────────────────────

def test_ho_so_chi_ke_file_CO_THAT(tmp_path):
    """Kê đường dẫn không có thật còn tệ hơn không kê: người mở không được sẽ tưởng máy hỏng."""
    cam = _cam(tmp_path)
    bai = cam / "T-001_bai-mot"
    bai.mkdir()
    (bai / "content.md").write_text("# x\n", encoding="utf-8", newline="\n")
    dong = {d["content_id"]: d for d in CD.doc_bang(cam)[3]}["T-001"]

    h = CD.ho_so_bai(cam, dong)
    assert "bài" in h["file"] and h["file"]["bài"].endswith("content.md")
    assert "nghiên cứu" not in h["file"], "kê research.md trong khi file không tồn tại"
    for p in h["file"].values():
        assert Path(p).is_file()


def test_ho_so_bai_chua_co_thu_muc_thi_rong(tmp_path):
    cam = _cam(tmp_path)
    dong = {d["content_id"]: d for d in CD.doc_bang(cam)[3]}["T-001"]
    dong = dict(dong, folder="")
    assert CD.ho_so_bai(cam, dong)["file"] == {}


# ── CLI trong phiên ─────────────────────────────────────────────────────────

def test_CLI_thieu_nguyen_van_thi_khong_chay(tmp_path):
    cam = _cam(tmp_path)
    with pytest.raises(SystemExit) as e:
        CD.main([str(cam), "mo", "--cong", "g1", "--bai", "T-001", "--boi", "Đức"])
    assert e.value.code == 2
    assert _g1(cam, "T-001") == ""


def test_CLI_mo_roi_chay_lai_van_ma_0(tmp_path, capsys):
    """Idempotent nghĩa là chạy lại vẫn 0. Trả khác 0 thì thợ tưởng hỏng và thử lại 3 lần."""
    cam = _cam(tmp_path)
    args = [str(cam), "mo", "--cong", "g1", "--bai", "T-001",
            "--boi", "Đức", "--nguyen-van", "ok"]
    assert CD.main(args) == 0
    assert CD.main(args) == 0


def test_CLI_cho_in_JSON_doc_duoc_bang_may(tmp_path, capsys):
    cam = _cam(tmp_path)
    bai = cam / "T-001_bai-mot"
    bai.mkdir()
    (bai / "content.md").write_text("# x\n", encoding="utf-8", newline="\n")
    assert CD.main([str(cam), "cho", "--cong", "g1", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["cong"] == "g1" and d["so_bai"] == 2
    t1 = [b for b in d["bai"] if b["content_id"] == "T-001"][0]
    assert t1["file"]["bài"].endswith("content.md")


def test_CLI_khong_thay_campaign_thi_ma_2(tmp_path):
    assert CD.main([str(tmp_path / "khong-co"), "cho", "--cong", "g1"]) == 2


def test_CLI_cho_TACH_bai_san_sang_khoi_bai_chua_the_hoi(tmp_path, capsys):
    """Cổng 2 gọi là "đang chờ" cả bài mới chỉ có dòng trong bảng — chúng không có file nào.

    Trộn chung thì một lô 20 bài đổ ra 20 mục dài và người phải tự dò xem mục nào cần đọc.
    Bản JSON vẫn giữ cả hai nhóm: máy không cần được chiều, người thì cần.
    """
    cam = _cam(tmp_path)
    # T-001 đã viết và chấm xanh; T-002 mới có dòng trong bảng.
    CD.mo_cong(cam, "g1", ["T-001", "T-002"], boi="Đức", nguyen_van="ok", qua="phiên")
    bai = cam / "T-001_bai-mot"
    bai.mkdir()
    (bai / "content.md").write_text(
        "## post:blog_article" + "\n\n" + ("Câu chuyện đời thường mở bài. " * 60),
        encoding="utf-8", newline="\n")
    (bai / "gates.json").write_text('{"ket_luan": "xanh", "cong": []}',
                                    encoding="utf-8", newline="\n")

    CD.main([str(cam), "cho", "--cong", "g2"])
    ra = capsys.readouterr().out
    assert "1/2 bài sẵn sàng hỏi" in ra, ra
    assert "Chưa được đem ra hỏi (1 bài)" in ra, ra
    # Bài chưa viết KHÔNG được kê file — kê đường dẫn không có thật là mời người mở hụt.
    dau_t002 = ra.index("T-002")
    assert "content.md" not in ra[dau_t002:], ra[dau_t002:]
