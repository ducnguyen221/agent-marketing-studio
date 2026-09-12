# -*- coding: utf-8 -*-
"""`scripts/lib/work_queue.py` — hàng chờ dùng thư mục làm trạng thái.

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
import work_queue as WQ  # noqa: E402


def _cam(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    return tmp_path


# ── xếp hàng và giành lượt ──────────────────────────────────────────────────

def test_viec_xep_theo_thu_tu_vao_truoc_ra_truoc(tmp_path):
    campaign = _cam(tmp_path)
    m1 = WQ.add(campaign, "write", post="T-001")
    time.sleep(0.01)
    m2 = WQ.add(campaign, "write", post="T-002")
    assert WQ.claim(campaign)["job_id"] == m1
    assert WQ.claim(campaign)["job_id"] == m2
    assert WQ.claim(campaign) is None


def test_HAI_THO_khong_bao_gio_giat_cung_mot_viec(tmp_path):
    """Nguyên tử hay không nằm ở đây. Hai thợ cùng nhặt = hai agent cùng viết một bài.

    Hàng có 3 việc, gọi `nhat` 6 lần: phải ra ĐÚNG 3 mã khác nhau rồi hết, không lặp lại.
    """
    campaign = _cam(tmp_path)
    for i in range(3):
        WQ.add(campaign, "write", post=f"T-00{i}")
        time.sleep(0.01)
    lay = [WQ.claim(campaign) for _ in range(6)]
    job_id = [x["job_id"] for x in lay if x]
    assert len(job_id) == 3, f"lấy được {len(job_id)} việc từ hàng 3 việc"
    assert len(set(job_id)) == 3, f"CÙNG một việc bị giành hai lần: {job_id}"


def test_hang_rong_tra_ve_None(tmp_path):
    assert WQ.claim(_cam(tmp_path)) is None


def test_viec_da_nhat_KHONG_con_trong_work_queue(tmp_path):
    campaign = _cam(tmp_path)
    WQ.add(campaign, "write", post="T-001")
    WQ.claim(campaign)
    assert WQ.count(campaign)["pending"] == 0 and WQ.count(campaign)["running"] == 1


# ── bền qua sập máy ─────────────────────────────────────────────────────────

def test_viec_SONG_qua_khoi_dong_lai(tmp_path):
    """Việc nằm trên đĩa, không trong RAM. Máy sập thì bật lại là còn."""
    campaign = _cam(tmp_path)
    WQ.add(campaign, "write", post="T-001", note="đừng mất tôi")
    # không giữ gì trong bộ nhớ — đọc lại từ đĩa như một tiến trình mới tinh
    v = WQ.claim(campaign)
    assert v["post"] == "T-001" and v["note"] == "đừng mất tôi"


def test_tho_CHET_giua_chung_thi_viec_duoc_tra_lai(tmp_path):
    """Việc kẹt ở `running` quá hạn = thợ đã chết. Phải tự trả về hàng chờ.

    Không có tiến trình nào canh việc này — chính `nhat()` dọn, nên không đẻ thêm thứ
    phải trông.
    """
    campaign = _cam(tmp_path)
    WQ.add(campaign, "write", post="T-001")
    v = WQ.claim(campaign)                                   # thợ nhận rồi "chết"
    assert WQ.count(campaign)["running"] == 1
    assert WQ.claim(campaign) is None                        # chưa quá hạn thì chưa trả

    sau = time.time() + WQ.STALE_SECONDS + 60
    lai = WQ.claim(campaign, now=sau)
    assert lai is not None and lai["job_id"] == v["job_id"], "việc mồ côi không được trả lại"


def test_viec_RACH_khong_chan_ca_hang(tmp_path):
    """Một file JSON rách không được làm đứng cả hàng chờ."""
    campaign = _cam(tmp_path)
    (WQ._box(campaign, "pending") / "20260101T000000-rach.json").write_text("{ rách", encoding="utf-8")
    time.sleep(0.01)
    job_id = WQ.add(campaign, "write", post="T-001")
    v = WQ.claim(campaign)
    assert v is not None and v["job_id"] == job_id, "việc rách đã chặn mất việc hợp lệ"
    assert WQ.count(campaign)["failed"] == 1


# ── không quay tít ──────────────────────────────────────────────────────────

def test_hong_thi_thu_lai_nhung_CO_TRAN(tmp_path):
    """Mỗi vòng viết lại đốt ~10 phút agent. Quay tít vô hạn là đốt tiền thật."""
    campaign = _cam(tmp_path)
    job_id = WQ.add(campaign, "write", post="T-001")

    for lan in range(1, WQ.MAX_ATTEMPTS):
        assert WQ.claim(campaign)["job_id"] == job_id
        assert WQ.failed(campaign, job_id, f"lỗi lần {lan}") == "pending", "còn lượt mà đã bỏ cuộc"

    assert WQ.claim(campaign)["job_id"] == job_id
    assert WQ.failed(campaign, job_id, "lỗi lần cuối") == "failed", "hết lượt mà vẫn quay tiếp"
    assert WQ.claim(campaign) is None, "việc đã bỏ cuộc vẫn quay lại hàng chờ"
    assert WQ.count(campaign)["failed"] == 1


def test_so_lan_duoc_dem_va_ly_do_duoc_giu(tmp_path):
    campaign = _cam(tmp_path)
    job_id = WQ.add(campaign, "write", post="T-001")
    WQ.claim(campaign)
    WQ.failed(campaign, job_id, "bộ viết trả về rỗng")
    d = json.loads((WQ._box(campaign, "pending") / f"{job_id}.json").read_text(encoding="utf-8"))
    assert d["attempts"] == 1 and d["error"] == "bộ viết trả về rỗng"


def test_xong_thi_sang_o_xong_va_giu_ket_qua(tmp_path):
    campaign = _cam(tmp_path)
    job_id = WQ.add(campaign, "write", post="T-001")
    WQ.claim(campaign)
    WQ.done(campaign, job_id, so_chu=2400)
    assert WQ.count(campaign) == {"pending": 0, "running": 0, "done": 1, "failed": 0}
    d = json.loads((WQ._box(campaign, "done") / f"{job_id}.json").read_text(encoding="utf-8"))
    assert d["so_chu"] == 2400 and d["finished_at"]
