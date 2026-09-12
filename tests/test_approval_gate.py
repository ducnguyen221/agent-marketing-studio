# -*- coding: utf-8 -*-
"""`scripts/pipeline/approval_gate.py` — kho cổng dùng chung + mặt tiền TRONG PHIÊN.

Trước 12/09/2026 chỉ Telegram ghi được `g1` và `g3`. Nghĩa là cách làm việc MẶC ĐỊNH —
người ngồi cùng agent trong một phiên, mở file trên máy rồi gật — không có đường ghi cổng
nào cả. File này canh bốn thứ của đường mới:

· **Cổng phải có chứng nhân.** Thiếu `boi` hoặc `quote` là ném lỗi, không phải ghi
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
import approval_gate as AG  # noqa: E402
import work_queue as WQ  # noqa: E402
import event_log as EV  # noqa: E402

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
    campaign = tmp_path / "tram" / "kenh-thu" / "CD-THU"
    (campaign / "logs").mkdir(parents=True)
    (campaign / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")
    return campaign


def _g1(campaign, cid):
    return {d["content_id"]: d for d in AG.read_content_table(campaign)[3]}[cid].get("g1", "").strip()


# ── Chứng nhân ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("by,quote", [
    ("", "duyệt nhé"),
    ("   ", "duyệt nhé"),
    ("Đức", ""),
    ("Đức", "   "),
])
def test_thieu_chung_nhan_thi_KHONG_ghi_cong(tmp_path, by, quote):
    """Không có tên người duyệt, hoặc không có câu người nói, thì cổng không mở."""
    campaign = _cam(tmp_path)
    with pytest.raises(ValueError):
        AG.open_gate(campaign, "g1", ["T-001"], by=by, quote=quote, via="phiên")
    assert _g1(campaign, "T-001") == "", "ném lỗi rồi mà cổng vẫn ghi — fail-open"


def test_cong_la_thi_nem_loi(tmp_path):
    campaign = _cam(tmp_path)
    with pytest.raises(ValueError):
        AG.open_gate(campaign, "g9", ["T-001"], by="Đức", quote="ok", via="phiên")


# ── Ghi cổng ────────────────────────────────────────────────────────────────

def test_mo_g1_ghi_cot_va_doi_status(tmp_path):
    campaign = _cam(tmp_path)
    done = AG.open_gate(campaign, "g1", ["T-001"], by="Đức", quote="ok làm bài này",
                      via="phiên")
    assert done == ["T-001"]
    d = {x["content_id"]: x for x in AG.read_content_table(campaign)[3]}["T-001"]
    assert d["g1"].strip(), "không ghi ngày qua cổng"
    assert d["status"].strip() == "approved"


def test_mo_cong_VAO_SO_SU_KIEN(tmp_path):
    """Sổ sự kiện là thứ duy nhất trả lời được *ai* duyệt và *qua đường nào*."""
    campaign = _cam(tmp_path)
    AG.open_gate(campaign, "g1", ["T-001"], by="Đức", quote="ok", via="phiên")
    ds = [x for x in EV.read(campaign) if x["job"] == "g1_approved"]
    assert ds, [x["job"] for x in EV.read(campaign)]
    assert ds[-1]["via"] == "phiên", "không ghi lại đi qua mặt tiền nào"


def test_mo_lai_KHONG_ghi_de_va_KHONG_sinh_su_kien_thu_hai(tmp_path):
    """Idempotent: mặt tiền có thể gọi lại (bấm hai lần, chạy lại lệnh) — không được nhân đôi."""
    campaign = _cam(tmp_path)
    AG.open_gate(campaign, "g1", ["T-001"], by="Đức", quote="ok", via="phiên")
    ngay_dau = _g1(campaign, "T-001")
    lan_hai = AG.open_gate(campaign, "g1", ["T-001"], by="ai đó", quote="ok lần nữa",
                         via="phiên")
    assert lan_hai == [], "bài đã qua cổng vẫn báo là vừa mở"
    assert _g1(campaign, "T-001") == ngay_dau, "ghi đè ngày duyệt cũ"
    assert len([x for x in EV.read(campaign) if x["job"] == "g1_approved"]) == 1


def test_bai_khong_co_trong_bang_thi_bo_qua_khong_no(tmp_path):
    campaign = _cam(tmp_path)
    done = AG.open_gate(campaign, "g1", ["T-001", "T-404"], by="Đức", quote="ok",
                      via="phiên")
    assert done == ["T-001"]


def test_mo_cong_KHONG_xep_viec(tmp_path):
    """Xếp việc là chính sách của mặt tiền, không phải của kho cổng.

    Nếu kho tự xếp thì Telegram (vốn đã xếp) sẽ xếp hai lần, và agent trong phiên — vốn
    chạy bước kế tiếp NGAY — bỏ lại một việc thừa cho thợ chạy lại đúng việc vừa xong.
    """
    campaign = _cam(tmp_path)
    lookahead = WQ.count(campaign)["pending"]
    AG.open_gate(campaign, "g1", ["T-001"], by="Đức", quote="ok", via="phiên")
    assert WQ.count(campaign)["pending"] == lookahead


# ── Từ chối ─────────────────────────────────────────────────────────────────

def test_tu_choi_ghi_phan_hoi_va_KHONG_mo_cong(tmp_path):
    campaign = _cam(tmp_path)
    AG.reject(campaign, "g1", ["T-001"], by="Đức", quote="mở bài dài quá", via="phiên")
    assert _g1(campaign, "T-001") == "", "từ chối mà cổng vẫn mở"
    ph = AG.read_feedback(campaign, "T-001")
    assert ph and "dài quá" in ph[-1]["text"]
    assert any(x["job"] == "g1_rejected" for x in EV.read(campaign))


def test_tu_choi_GIU_DU_phan_hoi_cu(tmp_path):
    """Vòng viết lại lặp được, nên ghi đè lần trước là mất dấu vết vì sao bài thành thế."""
    campaign = _cam(tmp_path)
    AG.reject(campaign, "g1", ["T-001"], by="Đức", quote="lần một", via="phiên")
    AG.reject(campaign, "g1", ["T-001"], by="Đức", quote="lần hai", via="phiên")
    assert [x["text"] for x in AG.read_feedback(campaign, "T-001")] == ["lần một", "lần hai"]


# ── Hồ sơ file để người mở kiểm ─────────────────────────────────────────────

def test_ho_so_chi_ke_file_CO_THAT(tmp_path):
    """Kê đường dẫn không có thật còn tệ hơn không kê: người mở không được sẽ tưởng máy hỏng."""
    campaign = _cam(tmp_path)
    post = campaign / "T-001_bai-mot"
    post.mkdir()
    (post / "content.md").write_text("# x\n", encoding="utf-8", newline="\n")
    row = {d["content_id"]: d for d in AG.read_content_table(campaign)[3]}["T-001"]

    h = AG.post_files(campaign, row)
    assert "bài" in h["file"] and h["file"]["bài"].endswith("content.md")
    assert "nghiên cứu" not in h["file"], "kê research.md trong khi file không tồn tại"
    for p in h["file"].values():
        assert Path(p).is_file()


def test_ho_so_bai_chua_co_thu_muc_thi_rong(tmp_path):
    campaign = _cam(tmp_path)
    row = {d["content_id"]: d for d in AG.read_content_table(campaign)[3]}["T-001"]
    row = dict(row, folder="")
    assert AG.post_files(campaign, row)["file"] == {}


# ── CLI trong phiên ─────────────────────────────────────────────────────────

def test_CLI_thieu_nguyen_van_thi_khong_chay(tmp_path):
    campaign = _cam(tmp_path)
    with pytest.raises(SystemExit) as e:
        AG.main([str(campaign), "open", "--gate", "g1", "--post", "T-001", "--by", "Đức"])
    assert e.value.code == 2
    assert _g1(campaign, "T-001") == ""


def test_CLI_mo_roi_chay_lai_van_ma_0(tmp_path, capsys):
    """Idempotent nghĩa là chạy lại vẫn 0. Trả khác 0 thì thợ tưởng hỏng và thử lại 3 lần."""
    campaign = _cam(tmp_path)
    args = [str(campaign), "open", "--gate", "g1", "--post", "T-001",
            "--by", "Đức", "--quote", "ok"]
    assert AG.main(args) == 0
    assert AG.main(args) == 0


def test_CLI_cho_in_JSON_doc_duoc_bang_may(tmp_path, capsys):
    campaign = _cam(tmp_path)
    post = campaign / "T-001_bai-mot"
    post.mkdir()
    (post / "content.md").write_text("# x\n", encoding="utf-8", newline="\n")
    assert AG.main([str(campaign), "waiting", "--gate", "g1", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["gate"] == "g1" and d["count"] == 2
    t1 = [b for b in d["post"] if b["content_id"] == "T-001"][0]
    assert t1["file"]["bài"].endswith("content.md")


def test_CLI_khong_thay_campaign_thi_ma_2(tmp_path):
    assert AG.main([str(tmp_path / "khong-co"), "waiting", "--gate", "g1"]) == 2


def test_CLI_cho_TACH_bai_san_sang_khoi_bai_chua_the_hoi(tmp_path, capsys):
    """Cổng 2 gọi là "đang chờ" cả bài mới chỉ có dòng trong bảng — chúng không có file nào.

    Trộn chung thì một lô 20 bài đổ ra 20 mục dài và người phải tự dò xem mục nào cần đọc.
    Bản JSON vẫn giữ cả hai nhóm: máy không cần được chiều, người thì cần.
    """
    campaign = _cam(tmp_path)
    # T-001 đã viết và chấm xanh; T-002 mới có dòng trong bảng.
    AG.open_gate(campaign, "g1", ["T-001", "T-002"], by="Đức", quote="ok", via="phiên")
    post = campaign / "T-001_bai-mot"
    post.mkdir()
    (post / "content.md").write_text(
        "## post:blog_article" + "\n\n" + ("Câu chuyện đời thường mở bài. " * 60),
        encoding="utf-8", newline="\n")
    (post / "gates.json").write_text('{"ket_luan": "xanh", "cong": []}',
                                    encoding="utf-8", newline="\n")

    AG.main([str(campaign), "waiting", "--gate", "g2"])
    ra = capsys.readouterr().out
    assert "1/2 bài sẵn sàng hỏi" in ra, ra
    assert "Chưa được đem ra hỏi (1 bài)" in ra, ra
    # Bài chưa viết KHÔNG được kê file — kê đường dẫn không có thật là mời người mở hụt.
    dau_t002 = ra.index("T-002")
    assert "content.md" not in ra[dau_t002:], ra[dau_t002:]
