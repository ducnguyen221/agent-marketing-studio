# -*- coding: utf-8 -*-
"""`scripts/lib/event_log.py` — sổ sự kiện chỉ-nối-thêm.

Mỗi test dưới đây chặn một cách hỏng đã có thật trong dự án này, hoặc một cách hỏng mà
hình dạng "gộp trạng thái + lịch sử vào một YAML" chắc chắn sẽ mở ra.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import event_log as EV  # noqa: E402


def _cam(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    return tmp_path


def test_ghi_hai_lan_thi_GIU_CA_HAI(tmp_path):
    """Chỉ-nối-thêm: lần ghi sau KHÔNG được đè lần trước.

    Đây là khác biệt cốt lõi với read-modify-write. `publish.json` hiện chỉ có MỘT ô
    `approved_at`, nên lần duyệt thứ hai xoá mất lần đầu — chính khoảng trống đó sinh ra
    file này.
    """
    campaign = _cam(tmp_path)
    EV.write(campaign, "g1_approved", post="T-001", by="Đức")
    EV.write(campaign, "g2_rejected", post="T-001", by="Đức", reason="mở bài dài")

    ds = EV.read(campaign, post="T-001")
    assert [x["job"] for x in ds] == ["g1_approved", "g2_rejected"], ds
    assert ds[-1]["reason"] == "mở bài dài"


def test_loc_dung_MOT_bai(tmp_path):
    campaign = _cam(tmp_path)
    EV.write(campaign, "g1_approved", post="T-001")
    EV.write(campaign, "g1_approved", post="T-002")
    EV.write(campaign, "soan_xong", post="T-001")
    assert [x["job"] for x in EV.read(campaign, post="T-001")] == ["g1_approved", "soan_xong"]


def test_dong_HONG_khong_lam_chet_ca_so(tmp_path):
    """Một dòng rách chỉ mất đúng dòng đó — khác hẳn YAML sai cú pháp là mất sạch."""
    campaign = _cam(tmp_path)
    EV.write(campaign, "g1_approved", post="T-001")
    with EV.log_path(campaign).open("a", encoding="utf-8") as f:
        f.write("{ dòng rách không phải JSON\n")
    EV.write(campaign, "soan_xong", post="T-001")

    ds = EV.read(campaign, post="T-001")
    assert [x["job"] for x in ds] == ["g1_approved", "soan_xong"], \
        f"dòng hỏng đã nuốt mất sự kiện hợp lệ: {ds}"


def test_chi_doc_DUOI_file_du_so_rat_to(tmp_path, monkeypatch):
    """Sổ to bao nhiêu cũng không đổi chi phí đọc — đó là lý do chọn JSONL.

    Đặt trần đuôi rất nhỏ rồi ghi nhiều hơn hẳn: hàm phải trả về các sự kiện CUỐI, và
    KHÔNG được nạp cả file.
    """
    campaign = _cam(tmp_path)
    monkeypatch.setattr(EV, "TAIL_BYTES", 2048)
    for i in range(400):
        EV.write(campaign, "nhip", post="T-001", so=i)

    co = EV.log_path(campaign).stat().st_size
    assert co > 2048 * 4, "fixture chưa đủ to để kiểm"

    # XIN NHIỀU HƠN HẲN sức chứa của cửa sổ đuôi. Đây mới là phép thử CƠ CHẾ:
    #   · đọc đuôi     -> chỉ có thể trả về số dòng nằm lọt trong 2 KB
    #   · đọc cả file  -> trả về đủ cả 400
    # Bản đầu của test này xin n=5 rồi khẳng định 5 sự kiện cuối — mà 5 cái cuối thì GIỐNG
    # NHAU ở cả hai cách, nên đột biến `seek(tail)` -> `seek(0)` SỐNG SÓT qua toàn bộ 8
    # test. Hệ quả bị che, đúng ca ① trong sổ cạm bẫy: assert vào cơ chế, đừng assert vào
    # hệ quả.
    tat_ca = EV.read(campaign, post="T-001", n=10_000)
    assert len(tat_ca) < 60, (
        f"đọc được {len(tat_ca)}/400 sự kiện từ cửa sổ đuôi 2 KB ⇒ đang nạp CẢ FILE")
    assert [x["so"] for x in tat_ca[-5:]] == [395, 396, 397, 398, 399], tat_ca[-5:]


def test_ghi_HONG_khong_lam_do_viec_chinh(tmp_path, monkeypatch, capsys):
    """Không ghi được sổ thì kêu, nhưng KHÔNG ném — sổ là thứ đọc lại sau.

    Đánh đổ cả lượt duyệt của người vì không ghi nổi một dòng nhật ký là sai thứ tự ưu tiên.
    """
    campaign = _cam(tmp_path)

    def failed(*a, **k):
        raise OSError("đĩa đầy")

    monkeypatch.setattr(Path, "open", failed)
    EV.write(campaign, "g1_approved", post="T-001")          # KHÔNG được ném
    assert "không ghi được sổ" in capsys.readouterr().err


def test_doc_so_chua_ton_tai_tra_ve_rong(tmp_path):
    """Chiến dịch mới tinh chưa có sổ — không phải lỗi."""
    assert EV.read(_cam(tmp_path)) == []


def test_giu_dung_thu_tu_thoi_gian(tmp_path):
    campaign = _cam(tmp_path)
    t0 = datetime.now().astimezone()
    for i in range(3):
        EV.write(campaign, f"buoc{i}", post="T-001", at=t0 + timedelta(minutes=i))
    ds = EV.read(campaign, post="T-001")
    assert [x["job"] for x in ds] == ["buoc0", "buoc1", "buoc2"]
    assert ds[0]["at"] < ds[-1]["at"]


def test_moi_dong_la_JSON_doc_lai_duoc_bang_tay(tmp_path):
    """Sổ phải đọc được bằng mắt và bằng `jq` — nó là thứ người sẽ mở lúc đang hoảng."""
    campaign = _cam(tmp_path)
    EV.write(campaign, "g2_approved", post="T-003", by="Đức (Telegram)")
    tho = EV.log_path(campaign).read_text(encoding="utf-8")
    assert tho.endswith("\n"), "thiếu xuống dòng cuối ⇒ dòng sau bị nối vào dòng này"
    o = json.loads(tho.strip())
    assert o["job"] == "g2_approved" and o["post"] == "T-003" and o["by"] == "Đức (Telegram)"
