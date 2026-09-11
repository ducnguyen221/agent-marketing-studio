# -*- coding: utf-8 -*-
"""`scripts/pipeline/tho_viec.py` — thợ nhặt việc và gọi agent.

Thợ là chỗ DUY NHẤT trong hệ tự khởi động một agent mà không có người bấm nút. Hỏng ở đây
thì hoặc agent tự duyệt bài của chính nó (mất sạch ý nghĩa cổng), hoặc nhiều agent cùng
chạy (335 tiến trình như 11/09), hoặc quay tít đốt tiền.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import hang_cho as HC      # noqa: E402
import so_su_kien as SO    # noqa: E402
import tho_viec as TV      # noqa: E402

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
| T-001 | Bài một | ai-agent | explainer | awareness | high | approved | 2026-09-01 |  | 2026-09-15 |  | ./T-001_bai |  |
<!-- CONTENT:END -->
"""


class BotGia:
    def __init__(self):
        self.da_gui = []

    def gui(self, text, **kw):
        self.da_gui.append(text)
        return len(self.da_gui)


def _cam(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")
    return tmp_path


def _bai(cam, *, viet_that=True, gates=None, viet_lan=None):
    b = cam / "T-001_bai"
    b.mkdir(parents=True, exist_ok=True)
    if viet_that:
        (b / "content.md").write_text(
            "## post:blog_article\n\n# Tiêu đề\n\n" + "Câu chuyện đời thường. " * 60,
            encoding="utf-8", newline="\n")
    else:
        (b / "content.md").write_text(
            "## post:blog_article\n\n> Khuôn.\n\n# {{tieu_de}}\n\n{{than}}\n",
            encoding="utf-8", newline="\n")
    if gates:
        (b / "gates.json").write_text(
            json.dumps({"tong": 23, "ket_luan": gates, "do_chan": 0, "cong": []}),
            encoding="utf-8", newline="\n")
    if viet_lan is not None:
        (b / ".viet-lan.json").write_text(
            json.dumps({"so_lan": viet_lan}), encoding="utf-8", newline="\n")
    return b


def _chay_gia(ket=True, tin="ok"):
    goi = []

    def chay(cam, buoc, cid):
        goi.append((buoc, cid))
        return ket, tin
    chay.goi = goi
    return chay


# ── đường chạy bình thường ──────────────────────────────────────────────────

def test_hang_rong_thi_thoat_EM(tmp_path):
    """Hàng rỗng là đường chạy BÌNH THƯỜNG — Task Scheduler gọi mỗi phút mà."""
    kq = TV.lam_mot_viec(_cam(tmp_path), chay=_chay_gia())
    assert kq["lam"] == 0 and kq["ly_do"] == "hàng rỗng"


def test_nhat_viec_va_chay_dung_buoc(tmp_path):
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)                 # còn khuôn ⇒ bước kế là `soan`
    HC.them(cam, "tiep", bai="T-001")
    c = _chay_gia()
    kq = TV.lam_mot_viec(cam, chay=c)
    assert kq["lam"] == 1 and kq["buoc"] == "soan"
    assert c.goi == [("soan", "T-001")]
    assert HC.dem(cam)["xong"] == 1


def test_buoc_duoc_SUY_LAI_luc_chay_chu_khong_tin_luc_xep_hang(tmp_path):
    """Giữa lúc xếp hàng và lúc chạy, trạng thái có thể đã đổi.

    Việc chỉ nói "bài này cần đụng tới"; bước cụ thể do thợ suy lại. Nhờ vậy thợ tự sửa
    được khi có thứ khác đã chạy trước, và không bao giờ chạy một bước đã lỗi thời.
    """
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001", buoc_doan="dung-trang")   # đoán SAI có chủ đích
    c = _chay_gia()
    assert TV.lam_mot_viec(cam, chay=c)["buoc"] == "soan"
    assert c.goi == [("soan", "T-001")], "đã tin lời đoán lúc xếp hàng"


# ── thợ không được vượt quyền ───────────────────────────────────────────────

def test_THO_KHONG_DUOC_dung_vao_buoc_can_nguoi(tmp_path):
    """Agent tự duyệt bài của chính nó là mất sạch ý nghĩa của cổng."""
    cam = _cam(tmp_path)
    _bai(cam, gates="xanh")                    # đã viết, cổng xanh ⇒ bước kế là `cho-G2`
    HC.them(cam, "tiep", bai="T-001")
    c = _chay_gia()
    kq = TV.lam_mot_viec(cam, chay=c)
    assert kq["lam"] == 0 and kq["buoc"] == "cho-G2"
    assert c.goi == [], "thợ đã chạy một bước lẽ ra phải để người quyết"


def test_MOT_AGENT_MOT_LUC(tmp_path):
    """Đã có việc `dang-lam` thì không nhặt thêm.

    11/09/2026: duyệt cả lô sinh nhiều agent cùng lúc, mỗi con kéo theo cả bộ MCP —
    335 tiến trình, 16,4 GB RAM, máy sập.
    """
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001")
    HC.nhat(cam)                                # giả vờ có thợ khác đang làm
    c = _chay_gia()
    kq = TV.lam_mot_viec(cam, chay=c)
    assert kq["lam"] == 0 and "đang có việc khác" in kq["ly_do"]
    assert c.goi == []


# ── hỏng và trần ────────────────────────────────────────────────────────────

def test_buoc_hong_thi_viec_quay_lai_hang_cho(tmp_path):
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001")
    kq = TV.lam_mot_viec(cam, chay=_chay_gia(ket=False, tin="bộ viết trả rỗng"))
    assert kq["hong"] is True and kq["se_thu_lai"] is True
    assert HC.dem(cam)["cho"] == 1


def test_cham_TRAN_VIET_LAI_thi_dung_va_bao_nguoi(tmp_path):
    """Mỗi vòng viết lại đốt ~10 phút agent. Quay tít vô hạn là đốt tiền thật."""
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False, viet_lan=TV.TRAN_VIET_LAI)
    HC.them(cam, "tiep", bai="T-001")
    b = BotGia()
    c = _chay_gia()
    kq = TV.lam_mot_viec(cam, bot=b, chay=c)
    assert kq["lam"] == 0 and kq["ly_do"] == "chạm trần viết lại"
    assert c.goi == [], "vẫn gọi agent dù đã chạm trần"
    assert b.da_gui and "viết lại" in b.da_gui[0]


def test_bai_KHONG_CO_trong_bang_thi_viec_hong_ngay(tmp_path):
    cam = _cam(tmp_path)
    HC.them(cam, "tiep", bai="T-999")
    kq = TV.lam_mot_viec(cam, chay=_chay_gia())
    assert kq["lam"] == 0 and "không có trong bảng" in kq["ly_do"]
    assert HC.dem(cam)["hong"] == 1


# ── báo người đúng lúc ──────────────────────────────────────────────────────

def test_xong_buoc_ma_buoc_SAU_can_nguoi_thi_GO_CUA(tmp_path):
    """Làm xong rồi im lặng thì người không biết tới lượt mình."""
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001")
    b = BotGia()

    def chay(cam_, buoc, cid):
        _bai(cam_, viet_that=True, gates="xanh")     # soạn xong ⇒ bước sau là `cho-G2`
        return True, "ok"

    kq = TV.lam_mot_viec(cam, bot=b, chay=chay)
    assert kq["lam"] == 1 and kq["buoc_sau"] == "cho-G2"
    assert b.da_gui and "T-001" in b.da_gui[0]


def test_moi_viec_deu_VAO_SO_su_kien(tmp_path):
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001")
    TV.lam_mot_viec(cam, chay=_chay_gia())
    viec = [x["viec"] for x in SO.doc(cam, bai="T-001")]
    assert "viec_bat_dau" in viec and "viec_xong" in viec, viec
