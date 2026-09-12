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
import work_queue as WQ      # noqa: E402
import event_log as EV    # noqa: E402
import worker as WK      # noqa: E402

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
        self.sent = []

    def gui(self, text, **kw):
        self.sent.append(text)
        return len(self.sent)


def _cam(tmp_path):
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")
    return tmp_path


def _bai(campaign, *, viet_that=True, gates=None, viet_lan=None):
    b = campaign / "T-001_bai"
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
            json.dumps({"total": 23, "verdict": gates, "fail_block": 0, "gate": []}),
            encoding="utf-8", newline="\n")
    if viet_lan is not None:
        (b / ".write-count.json").write_text(
            json.dumps({"attempts": viet_lan}), encoding="utf-8", newline="\n")
    return b


def _chay_gia(ket=True, msg="ok"):
    goi = []

    def run_cmd(campaign, step, cid):
        goi.append((step, cid))
        return ket, msg
    run_cmd.goi = goi
    return run_cmd


# ── đường chạy bình thường ──────────────────────────────────────────────────

def test_hang_rong_thi_thoat_EM(tmp_path):
    """Hàng rỗng là đường chạy BÌNH THƯỜNG — Task Scheduler gọi mỗi phút mà."""
    result = WK.run_one_job(_cam(tmp_path), run_cmd=_chay_gia())
    assert result["lam"] == 0 and result["reason"] == "hàng rỗng"


def test_nhat_viec_va_chay_dung_buoc(tmp_path):
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)                 # còn khuôn ⇒ bước kế là `soan`
    WQ.add(campaign, "next", post="T-001")
    c = _chay_gia()
    result = WK.run_one_job(campaign, run_cmd=c)
    assert result["lam"] == 1 and result["step"] == "write"
    assert c.goi == [("write", "T-001")]
    assert WQ.count(campaign)["done"] == 1


def test_buoc_duoc_SUY_LAI_luc_chay_chu_khong_tin_luc_xep_hang(tmp_path):
    """Giữa lúc xếp hàng và lúc chạy, trạng thái có thể đã đổi.

    Việc chỉ nói "bài này cần đụng tới"; bước cụ thể do thợ suy lại. Nhờ vậy thợ tự sửa
    được khi có thứ khác đã chạy trước, và không bao giờ chạy một bước đã lỗi thời.
    """
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001", buoc_doan="build-page")   # đoán SAI có chủ đích
    c = _chay_gia()
    assert WK.run_one_job(campaign, run_cmd=c)["step"] == "write"
    assert c.goi == [("write", "T-001")], "đã tin lời đoán lúc xếp hàng"


# ── thợ không được vượt quyền ───────────────────────────────────────────────

def test_THO_KHONG_DUOC_dung_vao_buoc_can_nguoi(tmp_path):
    """Agent tự duyệt bài của chính nó là mất sạch ý nghĩa của cổng.

    ⚠️ **Chắn này có HAI LỚP, nên đột biến một lớp SỐNG SÓT — đó là đúng, không phải lỗi
    của test.** Đã kiểm 12/09/2026:

      · gỡ `if buoc in TT.NEEDS_HUMAN` → vẫn xanh, vì `COMMANDS` không có mục cho `await-G2`
        nên rơi vào nhánh *"chưa dựng bước này"* và cũng không gọi agent.
      · gỡ **CẢ HAI** (thêm `"await-G2"` vào `COMMANDS`) → **test này ĐỎ**.

    Đây là ca ③ *phòng thủ nhiều tầng* trong sổ cạm bẫy: đột biến sống hợp lệ, và cách kiểm
    đúng là gỡ hết các lớp rồi mới kết luận. Đừng thấy đột biến sống mà vội nói test vô nghĩa.
    """
    campaign = _cam(tmp_path)
    _bai(campaign, gates="pass")                    # đã viết, cổng xanh ⇒ bước kế là `await-G2`
    WQ.add(campaign, "next", post="T-001")
    c = _chay_gia()
    result = WK.run_one_job(campaign, run_cmd=c)
    assert result["lam"] == 0 and result["step"] == "await-G2"
    assert c.goi == [], "thợ đã chạy một bước lẽ ra phải để người quyết"


def test_MOT_AGENT_MOT_LUC(tmp_path):
    """Đã có việc `running` thì không nhặt thêm.

    11/09/2026: duyệt cả lô sinh nhiều agent cùng lúc, mỗi con kéo theo cả bộ MCP —
    335 tiến trình, 16,4 GB RAM, máy sập.
    """
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001")
    WQ.claim(campaign)                                # giả vờ có thợ khác đang làm
    c = _chay_gia()
    result = WK.run_one_job(campaign, run_cmd=c)
    assert result["lam"] == 0 and "đang có việc khác" in result["reason"]
    assert c.goi == []


# ── hỏng và trần ────────────────────────────────────────────────────────────

def test_buoc_hong_thi_viec_quay_lai_work_queue(tmp_path):
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001")
    result = WK.run_one_job(campaign, run_cmd=_chay_gia(ket=False, msg="bộ viết trả rỗng"))
    assert result["failed"] is True and result["will_retry"] is True
    assert WQ.count(campaign)["pending"] == 1


def test_cham_TRAN_VIET_LAI_thi_dung_va_bao_nguoi(tmp_path):
    """Mỗi vòng viết lại đốt ~10 phút agent. Quay tít vô hạn là đốt tiền thật."""
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False, viet_lan=WK.MAX_REWRITES)
    WQ.add(campaign, "next", post="T-001")
    b = BotGia()
    c = _chay_gia()
    result = WK.run_one_job(campaign, bot=b, run_cmd=c)
    assert result["lam"] == 0 and result["reason"] == "chạm trần viết lại"
    assert c.goi == [], "vẫn gọi agent dù đã chạm trần"
    assert b.sent and "viết lại" in b.sent[0]


def test_bai_KHONG_CO_trong_bang_thi_viec_hong_ngay(tmp_path):
    campaign = _cam(tmp_path)
    WQ.add(campaign, "next", post="T-999")
    result = WK.run_one_job(campaign, run_cmd=_chay_gia())
    assert result["lam"] == 0 and "không có trong bảng" in result["reason"]
    assert WQ.count(campaign)["failed"] == 1


# ── báo người đúng lúc ──────────────────────────────────────────────────────

def test_xong_buoc_ma_buoc_SAU_can_nguoi_thi_GO_CUA(tmp_path):
    """Làm xong rồi im lặng thì người không biết tới lượt mình."""
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001")
    b = BotGia()

    def run_cmd(cam_, step, cid):
        _bai(cam_, viet_that=True, gates="pass")     # soạn xong ⇒ bước sau là `await-G2`
        return True, "ok"

    result = WK.run_one_job(campaign, bot=b, run_cmd=run_cmd)
    assert result["lam"] == 1 and result["buoc_sau"] == "await-G2"
    assert b.sent and "T-001" in b.sent[0]


def test_moi_viec_deu_VAO_SO_su_kien(tmp_path):
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001")
    WK.run_one_job(campaign, run_cmd=_chay_gia())
    job = [x["job"] for x in EV.read(campaign, post="T-001")]
    assert "job_started" in job and "job_done" in job, job


def test_cham_cong_ra_DO_la_DA_CHAM_XONG_chu_khong_phai_hong(tmp_path):
    """`blog_gates.py` trả mã 1 khi kết luận ĐỎ. Đó là KẾT QUẢ, không phải sự cố.

    ĐÃ XẢY RA THẬT 12/09/2026 khi chạy thử trên NEN-002: `gates.json` được tạo đầy đủ
    (5.180 byte, chấm xong 23 cổng) nhưng thợ đọc mã thoát 1 rồi báo "bước hỏng". Hệ quả
    nếu không vá: mọi bài chấm ra đỏ đều bị chấm lại 3 lần rồi vứt vào `failed/`, và **không
    bao giờ đi tiếp tới `fix-gates`** — tức đúng những bài cần sửa thì không ai sửa.

    Repo đã có luật *"mã thoát 0 không đủ để tính là xong"*. Đây là vế ngược của cùng một
    nguyên tắc: **mã thoát khác 0 không đủ để tính là hỏng.** Hỏi kết quả thật — có
    `gates.json` không — chứ đừng hỏi mã thoát.
    """
    campaign = _cam(tmp_path)
    b = _bai(campaign)                                  # đã viết, chưa có gates ⇒ `check-gates`
    WQ.add(campaign, "next", post="T-001")

    def chay_ra_do(cam_, step, cid):
        # y như blog_gates: GHI gates.json rồi trả mã khác 0 vì kết luận đỏ
        (b / "gates.json").write_text(
            json.dumps({"total": 23, "verdict": "fail", "fail_block": 7, "gate": []}),
            encoding="utf-8", newline="\n")
        return False, "7 cổng đỏ [chặn]"

    result = WK.run_one_job(campaign, run_cmd=chay_ra_do)
    assert not result.get("failed"), f"chấm xong mà bị tính là hỏng: {result}"
    assert WQ.count(campaign)["failed"] == 0 and WQ.count(campaign)["pending"] == 0


def test_tho_GIOI_HAN_dung_MOT_bai_khi_goi_buoc_soan(tmp_path, monkeypatch):
    """Việc theo từng bài, nhưng `soan` vốn quét cả chiến dịch — phải truyền `--post`.

    ĐO THẬT 12/09/2026: một việc xếp cho NEN-002 chạy **27 phút** vì nó viết lại luôn
    NEN-001 và NEN-003. Hệ quả nặng hơn thời gian: số lần viết lại của từng bài bị đếm sai,
    nên trần chống-quay-tít không còn nghĩa gì; và với 90 bài thì một lượt có thể vượt trần
    2 giờ của Task Scheduler rồi bị giết giữa chừng.

    Đây là loại sai khớp mà unit test dùng `chay` giả KHÔNG bao giờ lộ — phải chạy thật.
    """
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001")

    write = {}

    def gia_subprocess(cmd, **kw):
        write["cmd"] = cmd

        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()

    monkeypatch.setattr(WK.subprocess, "run", gia_subprocess)
    WK.run_one_job(campaign)          # dùng `_run_step` THẬT, chỉ chặn ở tầng subprocess

    assert "--post" in write["cmd"], f"gọi soan mà không giới hạn bài: {write['cmd']}"
    assert write["cmd"][write["cmd"].index("--post") + 1] == "T-001", write["cmd"]


def test_soan_viet_XONG_nhung_cong_DO_van_la_da_lam_duoc_viec(tmp_path):
    """`soan` trả mã khác 0 khi bài chưa qua cổng — nhưng bài ĐÃ ĐƯỢC VIẾT.

    ĐO THẬT 12/09/2026: một lượt chạy **27 phút**, viết xong ba bài, rồi bị tính là thất
    bại chỉ vì cổng chấm đỏ. Việc quay lại hàng chờ và sẽ đốt thêm 27 phút nữa cho đúng
    công việc vừa làm xong.

    Phép thử đúng là hỏi ARTEFACT: `content.md` đã có chữ thật chưa.
    """
    campaign = _cam(tmp_path)
    b = _bai(campaign, viet_that=False)                 # còn khuôn ⇒ bước kế là `soan`
    WQ.add(campaign, "next", post="T-001")

    def viet_roi_bao_do(cam_, step, cid):
        (b / "content.md").write_text(
            "## post:blog_article\n\n# Tiêu đề\n\n" + "Câu chuyện đời thường. " * 60,
            encoding="utf-8", newline="\n")
        return False, "G01 độ dài 2079 luật 2500-4000 [chan]"

    result = WK.run_one_job(campaign, run_cmd=viet_roi_bao_do)
    assert not result.get("failed"), f"viết xong mà bị tính là hỏng: {result}"
    assert WQ.count(campaign)["pending"] == 0, "việc quay lại hàng chờ ⇒ sẽ viết lại lần nữa vô ích"


def test_buoc_hong_THAT_su_thi_van_phai_bao_hong(tmp_path):
    """Mặt kia: nới phép thử artefact không được nuốt mất cái hỏng thật.

    Bộ viết chạy êm mà `content.md` vẫn trống thì vẫn là HỎNG — luật cũ của repo, giữ nguyên.
    """
    campaign = _cam(tmp_path)
    _bai(campaign, viet_that=False)
    WQ.add(campaign, "next", post="T-001")
    result = WK.run_one_job(campaign, run_cmd=_chay_gia(ket=False, msg="bộ viết trả rỗng"))
    assert result["failed"] is True, "hỏng thật mà lại tính là xong"


def test_tho_chay_duoc_buoc_dung_trang_sau_khi_qua_cong_2(tmp_path, monkeypatch):
    """Vòng phải khép QUA Cổng 2, không dừng lại ở đó.

    Trước giai đoạn 5, duyệt G2 xong thợ báo "chưa dựng bước build-page" rồi thôi.
    """
    campaign = _cam(tmp_path)
    _bai(campaign, gates="pass")
    # đánh dấu đã qua Cổng 2 ⇒ bước kế phải là `build-page`
    s = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(
        s.replace("| 2026-09-01 |  |", "| 2026-09-01 | 2026-09-02 |"),
        encoding="utf-8", newline="\n")
    WQ.add(campaign, "next", post="T-001")

    write = {}

    def gia(cmd, **kw):
        write["cmd"] = cmd

        class R:
            returncode, stdout, stderr = 0, "", ""
        return R()

    monkeypatch.setattr(WK.subprocess, "run", gia)
    result = WK.run_one_job(campaign)

    assert result["step"] == "build-page", result
    assert "build-page" in write["cmd"], write["cmd"]
    assert "--post" in write["cmd"], f"không giới hạn một bài: {write['cmd']}"
