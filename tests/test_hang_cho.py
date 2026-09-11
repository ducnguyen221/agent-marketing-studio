# -*- coding: utf-8 -*-
"""`scripts/lib/hang_cho.py` — hàng chờ dùng thư mục làm trạng thái.

Hàng chờ là thứ đứng giữa "người bấm nút" và "agent chạy 10 phút". Hỏng ở đây thì hoặc
việc rơi mất (người bấm rồi chẳng thấy gì), hoặc việc chạy hai lần (hai agent cùng viết
một bài), hoặc quay tít vô hạn (đốt tiền thật).
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import hang_cho as HC  # noqa: E402


def _cam(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    return tmp_path


# ── xếp hàng và giành lượt ──────────────────────────────────────────────────

def test_viec_xep_theo_thu_tu_vao_truoc_ra_truoc(tmp_path):
    cam = _cam(tmp_path)
    m1 = HC.them(cam, "soan", bai="T-001")
    time.sleep(0.01)
    m2 = HC.them(cam, "soan", bai="T-002")
    assert HC.nhat(cam)["ma"] == m1
    assert HC.nhat(cam)["ma"] == m2
    assert HC.nhat(cam) is None


def test_HAI_THO_khong_bao_gio_giat_cung_mot_viec(tmp_path):
    """Nguyên tử hay không nằm ở đây. Hai thợ cùng nhặt = hai agent cùng viết một bài.

    Hàng có 3 việc, gọi `nhat` 6 lần: phải ra ĐÚNG 3 mã khác nhau rồi hết, không lặp lại.
    """
    cam = _cam(tmp_path)
    for i in range(3):
        HC.them(cam, "soan", bai=f"T-00{i}")
        time.sleep(0.01)
    lay = [HC.nhat(cam) for _ in range(6)]
    ma = [x["ma"] for x in lay if x]
    assert len(ma) == 3, f"lấy được {len(ma)} việc từ hàng 3 việc"
    assert len(set(ma)) == 3, f"CÙNG một việc bị giành hai lần: {ma}"


def test_hang_rong_tra_ve_None(tmp_path):
    assert HC.nhat(_cam(tmp_path)) is None


def test_viec_da_nhat_KHONG_con_trong_hang_cho(tmp_path):
    cam = _cam(tmp_path)
    HC.them(cam, "soan", bai="T-001")
    HC.nhat(cam)
    assert HC.dem(cam)["cho"] == 0 and HC.dem(cam)["dang-lam"] == 1


# ── bền qua sập máy ─────────────────────────────────────────────────────────

def test_viec_SONG_qua_khoi_dong_lai(tmp_path):
    """Việc nằm trên đĩa, không trong RAM. Máy sập thì bật lại là còn."""
    cam = _cam(tmp_path)
    HC.them(cam, "soan", bai="T-001", ghi_chu="đừng mất tôi")
    # không giữ gì trong bộ nhớ — đọc lại từ đĩa như một tiến trình mới tinh
    v = HC.nhat(cam)
    assert v["bai"] == "T-001" and v["ghi_chu"] == "đừng mất tôi"


def test_tho_CHET_giua_chung_thi_viec_duoc_tra_lai(tmp_path):
    """Việc kẹt ở `dang-lam` quá hạn = thợ đã chết. Phải tự trả về hàng chờ.

    Không có tiến trình nào canh việc này — chính `nhat()` dọn, nên không đẻ thêm thứ
    phải trông.
    """
    cam = _cam(tmp_path)
    HC.them(cam, "soan", bai="T-001")
    v = HC.nhat(cam)                                   # thợ nhận rồi "chết"
    assert HC.dem(cam)["dang-lam"] == 1
    assert HC.nhat(cam) is None                        # chưa quá hạn thì chưa trả

    sau = time.time() + HC.QUA_HAN_GIAY + 60
    lai = HC.nhat(cam, bay_gio=sau)
    assert lai is not None and lai["ma"] == v["ma"], "việc mồ côi không được trả lại"


def test_viec_RACH_khong_chan_ca_hang(tmp_path):
    """Một file JSON rách không được làm đứng cả hàng chờ."""
    cam = _cam(tmp_path)
    (HC._o(cam, "cho") / "20260101T000000-rach.json").write_text("{ rách", encoding="utf-8")
    time.sleep(0.01)
    ma = HC.them(cam, "soan", bai="T-001")
    v = HC.nhat(cam)
    assert v is not None and v["ma"] == ma, "việc rách đã chặn mất việc hợp lệ"
    assert HC.dem(cam)["hong"] == 1


# ── không quay tít ──────────────────────────────────────────────────────────

def test_hong_thi_thu_lai_nhung_CO_TRAN(tmp_path):
    """Mỗi vòng viết lại đốt ~10 phút agent. Quay tít vô hạn là đốt tiền thật."""
    cam = _cam(tmp_path)
    ma = HC.them(cam, "soan", bai="T-001")

    for lan in range(1, HC.TRAN_LAN):
        assert HC.nhat(cam)["ma"] == ma
        assert HC.hong(cam, ma, f"lỗi lần {lan}") == "cho", "còn lượt mà đã bỏ cuộc"

    assert HC.nhat(cam)["ma"] == ma
    assert HC.hong(cam, ma, "lỗi lần cuối") == "hong", "hết lượt mà vẫn quay tiếp"
    assert HC.nhat(cam) is None, "việc đã bỏ cuộc vẫn quay lại hàng chờ"
    assert HC.dem(cam)["hong"] == 1


def test_so_lan_duoc_dem_va_ly_do_duoc_giu(tmp_path):
    cam = _cam(tmp_path)
    ma = HC.them(cam, "soan", bai="T-001")
    HC.nhat(cam)
    HC.hong(cam, ma, "bộ viết trả về rỗng")
    d = json.loads((HC._o(cam, "cho") / f"{ma}.json").read_text(encoding="utf-8"))
    assert d["so_lan"] == 1 and d["ly_do_hong"] == "bộ viết trả về rỗng"


def test_xong_thi_sang_o_xong_va_giu_ket_qua(tmp_path):
    cam = _cam(tmp_path)
    ma = HC.them(cam, "soan", bai="T-001")
    HC.nhat(cam)
    HC.xong(cam, ma, so_chu=2400)
    assert HC.dem(cam) == {"cho": 0, "dang-lam": 0, "xong": 1, "hong": 0}
    d = json.loads((HC._o(cam, "xong") / f"{ma}.json").read_text(encoding="utf-8"))
    assert d["so_chu"] == 2400 and d["xong_luc"]
