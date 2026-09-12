# -*- coding: utf-8 -*-
"""`scripts/pipeline/worker.py` — thợ nhặt việc và gọi agent.

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
import work_queue as HC      # noqa: E402
import event_log as SO    # noqa: E402
import worker as TV      # noqa: E402

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
    """Agent tự duyệt bài của chính nó là mất sạch ý nghĩa của cổng.

    ⚠️ **Chắn này có HAI LỚP, nên đột biến một lớp SỐNG SÓT — đó là đúng, không phải lỗi
    của test.** Đã kiểm 12/09/2026:

      · gỡ `if buoc in TT.CAN_NGUOI` → vẫn xanh, vì `LENH` không có mục cho `cho-G2`
        nên rơi vào nhánh *"chưa dựng bước này"* và cũng không gọi agent.
      · gỡ **CẢ HAI** (thêm `"cho-G2"` vào `LENH`) → **test này ĐỎ**.

    Đây là ca ③ *phòng thủ nhiều tầng* trong sổ cạm bẫy: đột biến sống hợp lệ, và cách kiểm
    đúng là gỡ hết các lớp rồi mới kết luận. Đừng thấy đột biến sống mà vội nói test vô nghĩa.
    """
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

def test_buoc_hong_thi_viec_quay_lai_work_queue(tmp_path):
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


def test_cham_cong_ra_DO_la_DA_CHAM_XONG_chu_khong_phai_hong(tmp_path):
    """`blog_gates.py` trả mã 1 khi kết luận ĐỎ. Đó là KẾT QUẢ, không phải sự cố.

    ĐÃ XẢY RA THẬT 12/09/2026 khi chạy thử trên NEN-002: `gates.json` được tạo đầy đủ
    (5.180 byte, chấm xong 23 cổng) nhưng thợ đọc mã thoát 1 rồi báo "bước hỏng". Hệ quả
    nếu không vá: mọi bài chấm ra đỏ đều bị chấm lại 3 lần rồi vứt vào `hong/`, và **không
    bao giờ đi tiếp tới `sua-loi-cong`** — tức đúng những bài cần sửa thì không ai sửa.

    Repo đã có luật *"mã thoát 0 không đủ để tính là xong"*. Đây là vế ngược của cùng một
    nguyên tắc: **mã thoát khác 0 không đủ để tính là hỏng.** Hỏi kết quả thật — có
    `gates.json` không — chứ đừng hỏi mã thoát.
    """
    cam = _cam(tmp_path)
    b = _bai(cam)                                  # đã viết, chưa có gates ⇒ `cham-cong`
    HC.them(cam, "tiep", bai="T-001")

    def chay_ra_do(cam_, buoc, cid):
        # y như blog_gates: GHI gates.json rồi trả mã khác 0 vì kết luận đỏ
        (b / "gates.json").write_text(
            json.dumps({"tong": 23, "ket_luan": "do", "do_chan": 7, "cong": []}),
            encoding="utf-8", newline="\n")
        return False, "7 cổng đỏ [chặn]"

    kq = TV.lam_mot_viec(cam, chay=chay_ra_do)
    assert not kq.get("hong"), f"chấm xong mà bị tính là hỏng: {kq}"
    assert HC.dem(cam)["hong"] == 0 and HC.dem(cam)["cho"] == 0


def test_tho_GIOI_HAN_dung_MOT_bai_khi_goi_buoc_soan(tmp_path, monkeypatch):
    """Việc theo từng bài, nhưng `soan` vốn quét cả chiến dịch — phải truyền `--bai`.

    ĐO THẬT 12/09/2026: một việc xếp cho NEN-002 chạy **27 phút** vì nó viết lại luôn
    NEN-001 và NEN-003. Hệ quả nặng hơn thời gian: số lần viết lại của từng bài bị đếm sai,
    nên trần chống-quay-tít không còn nghĩa gì; và với 90 bài thì một lượt có thể vượt trần
    2 giờ của Task Scheduler rồi bị giết giữa chừng.

    Đây là loại sai khớp mà unit test dùng `chay` giả KHÔNG bao giờ lộ — phải chạy thật.
    """
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001")

    ghi = {}

    def gia_subprocess(lenh, **kw):
        ghi["lenh"] = lenh

        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()

    monkeypatch.setattr(TV.subprocess, "run", gia_subprocess)
    TV.lam_mot_viec(cam)          # dùng `_chay_buoc` THẬT, chỉ chặn ở tầng subprocess

    assert "--bai" in ghi["lenh"], f"gọi soan mà không giới hạn bài: {ghi['lenh']}"
    assert ghi["lenh"][ghi["lenh"].index("--bai") + 1] == "T-001", ghi["lenh"]


def test_soan_viet_XONG_nhung_cong_DO_van_la_da_lam_duoc_viec(tmp_path):
    """`soan` trả mã khác 0 khi bài chưa qua cổng — nhưng bài ĐÃ ĐƯỢC VIẾT.

    ĐO THẬT 12/09/2026: một lượt chạy **27 phút**, viết xong ba bài, rồi bị tính là thất
    bại chỉ vì cổng chấm đỏ. Việc quay lại hàng chờ và sẽ đốt thêm 27 phút nữa cho đúng
    công việc vừa làm xong.

    Phép thử đúng là hỏi ARTEFACT: `content.md` đã có chữ thật chưa.
    """
    cam = _cam(tmp_path)
    b = _bai(cam, viet_that=False)                 # còn khuôn ⇒ bước kế là `soan`
    HC.them(cam, "tiep", bai="T-001")

    def viet_roi_bao_do(cam_, buoc, cid):
        (b / "content.md").write_text(
            "## post:blog_article\n\n# Tiêu đề\n\n" + "Câu chuyện đời thường. " * 60,
            encoding="utf-8", newline="\n")
        return False, "G01 độ dài 2079 luật 2500-4000 [chan]"

    kq = TV.lam_mot_viec(cam, chay=viet_roi_bao_do)
    assert not kq.get("hong"), f"viết xong mà bị tính là hỏng: {kq}"
    assert HC.dem(cam)["cho"] == 0, "việc quay lại hàng chờ ⇒ sẽ viết lại lần nữa vô ích"


def test_buoc_hong_THAT_su_thi_van_phai_bao_hong(tmp_path):
    """Mặt kia: nới phép thử artefact không được nuốt mất cái hỏng thật.

    Bộ viết chạy êm mà `content.md` vẫn trống thì vẫn là HỎNG — luật cũ của repo, giữ nguyên.
    """
    cam = _cam(tmp_path)
    _bai(cam, viet_that=False)
    HC.them(cam, "tiep", bai="T-001")
    kq = TV.lam_mot_viec(cam, chay=_chay_gia(ket=False, tin="bộ viết trả rỗng"))
    assert kq["hong"] is True, "hỏng thật mà lại tính là xong"


def test_tho_chay_duoc_buoc_dung_trang_sau_khi_qua_cong_2(tmp_path, monkeypatch):
    """Vòng phải khép QUA Cổng 2, không dừng lại ở đó.

    Trước giai đoạn 5, duyệt G2 xong thợ báo "chưa dựng bước dung-trang" rồi thôi.
    """
    cam = _cam(tmp_path)
    _bai(cam, gates="xanh")
    # đánh dấu đã qua Cổng 2 ⇒ bước kế phải là `dung-trang`
    s = (cam / "campaign.md").read_text(encoding="utf-8")
    (cam / "campaign.md").write_text(
        s.replace("| 2026-09-01 |  |", "| 2026-09-01 | 2026-09-02 |"),
        encoding="utf-8", newline="\n")
    HC.them(cam, "tiep", bai="T-001")

    ghi = {}

    def gia(lenh, **kw):
        ghi["lenh"] = lenh

        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()

    monkeypatch.setattr(TV.subprocess, "run", gia)
    kq = TV.lam_mot_viec(cam)

    assert kq["buoc"] == "dung-trang", kq
    assert "dung-trang" in ghi["lenh"], ghi["lenh"]
    assert "--bai" in ghi["lenh"], f"không giới hạn một bài: {ghi['lenh']}"
