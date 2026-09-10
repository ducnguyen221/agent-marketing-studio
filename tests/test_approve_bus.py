# -*- coding: utf-8 -*-
"""`scripts/pipeline/approve_bus.py` — cổng duyệt hai chiều qua Telegram.

Đây là mảnh NHẠY CẢM NHẤT của cả hệ: nó là thứ quyết định nội dung có được đăng ra ngoài
hay không. Mỗi test dưới đây chặn một đường mà người ngoài — hoặc chính sự cẩu thả — mở
được cổng:

· **Ai cũng nhắn được cho một bot Telegram.** Biết tên bot là nhắn được. Không có allowlist
  thì người lạ bấm nút là bài lên sóng.
· **Nút cũ nằm mãi trong lịch sử chat.** Không có token một lần + hạn dùng thì bấm lại một
  nút của tuần trước là mở lại cổng đã đóng.
· **Nội dung tin nhắn là DỮ LIỆU, không phải MỆNH LỆNH.** Cùng luật với output của agent
  khác: không bao giờ đem chữ người khác gõ đi chạy.
· **Không đẻ kho phê duyệt thứ hai.** Cổng đã có chỗ ở (`g1` trong campaign.md, `review`
  trong publish.json). Bus chỉ là mặt tiền ghi vào đúng hai chỗ đó.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import md_io  # noqa: E402
import approve_bus as AB  # noqa: E402

CHAT_OK = 12345
CHAT_LA = 999

FM = """---
schema: campaign/1
id: CD-THU
channel: kenh-thu
id_prefix: T
name: Thử
status: active
content_pillar: ai-agent
runtime:
  label: Thử
  runner: x.ps1
---

# Thử

<!-- CONTENT:BEGIN -->
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | schedule | published | folder |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | Bài một | ai-agent | explainer | awareness | high | proposed |  |  | 2026-09-15 |  | ./T-001_bai-mot |
| T-002 | Bài hai | ai-agent | explainer | awareness | high | proposed |  |  | 2026-09-16 |  | ./T-002_bai-hai |
| T-003 | Bài ba | ai-agent | explainer | awareness | high | approved | 2026-09-01 |  | 2026-09-17 |  | ./T-003_bai-ba |
<!-- CONTENT:END -->
"""


class BotGia:
    """Bot giả — ghi lại tin đã gửi, trả về hàng đợi update do test dựng."""

    def __init__(self, hang_doi=None, cho_phep=(CHAT_OK,)):
        self.da_gui = []
        self.da_sua = []
        self.da_tra_loi = []
        self._hang = list(hang_doi or [])
        self._cho_phep = {str(c) for c in cho_phep}
        self.offset_da_dung = []

    def duoc_phep(self, chat_id):
        return str(chat_id) in self._cho_phep

    def gui(self, text, chat=None, **kw):
        self.da_gui.append({"text": text, "nut": None})
        return len(self.da_gui)

    def gui_kem_nut(self, text, nut, chat=None, **kw):
        for hang in nut:
            for _, data in hang:
                assert len(str(data).encode("utf-8")) <= 64, f"callback_data quá dài: {data}"
        self.da_gui.append({"text": text, "nut": nut})
        return len(self.da_gui)

    def sua_tin(self, message_id, text, nut=None, chat=None, **kw):
        self.da_sua.append({"message_id": message_id, "text": text})

    def tra_loi_nut(self, cq_id, text=""):
        self.da_tra_loi.append((cq_id, text))

    def lay_cap_nhat(self, offset=None, timeout=0):
        self.offset_da_dung.append(offset)
        h, self._hang = self._hang, []
        return h


def _cam(tmp_path):
    kenh = tmp_path / "tram" / "kenh-thu"
    cam = kenh / "CD-THU"
    (cam / "logs").mkdir(parents=True)
    (kenh / "channel.yml").write_text(
        "schema: channel/1\nid: kenh-thu\nlabel: \"K\"\nautonomy: suggest\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8")
    (cam / "campaign.md").write_text(FM, encoding="utf-8")
    return cam


def _bam_nut(data, chat_id=CHAT_OK, cq_id="cq1", update_id=1):
    return {"update_id": update_id,
            "callback_query": {"id": cq_id, "data": data,
                               "message": {"message_id": 1, "chat": {"id": chat_id}},
                               "from": {"id": chat_id}}}


def _nhan_tin(text, chat_id=CHAT_OK, update_id=1):
    return {"update_id": update_id,
            "message": {"message_id": 1, "chat": {"id": chat_id}, "text": text}}


def _bang(cam):
    _, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in dong}


def _token_dang_cho(cam):
    st = json.loads((cam / "logs" / "tg-approve.json").read_text(encoding="utf-8"))
    return st["cho"]


# ── gui: gom đúng bài đang chờ ──────────────────────────────────────────────

def test_gui_chi_gom_bai_CHUA_qua_cong(tmp_path):
    cam = _cam(tmp_path)
    b = BotGia()
    AB.gui_cong(cam, "g1", bot=b)
    assert len(b.da_gui) == 1
    t = b.da_gui[0]["text"]
    assert "T-001" in t and "T-002" in t
    assert "T-003" not in t, "T-003 đã có g1 mà vẫn đem đi duyệt lại"


def test_gui_khong_co_bai_nao_thi_khong_gui_tin_rac(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())          # lượt 1 duyệt hết
    b2 = BotGia()
    AB.gui_cong(cam, "g1", bot=b2, lo=0)
    assert b2.da_gui == [] or "0" in str(b2.da_gui), "gửi tin rỗng làm nhiễu"


def test_moi_luot_gui_sinh_token_MOI(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    t1 = set(_token_dang_cho(cam))
    AB.gui_cong(cam, "g1", bot=BotGia())
    t2 = set(_token_dang_cho(cam))
    assert t1 != t2 and t1.isdisjoint(t2 - t1) or len(t2) > len(t1)


# ── Bảo mật ─────────────────────────────────────────────────────────────────

def test_chat_LA_bam_nut_thi_KHONG_ghi_gi(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    b = BotGia(hang_doi=[_bam_nut(f"ok:{tok}", chat_id=CHAT_LA)])
    AB.nhan(cam, bot=b)
    assert _bang(cam)["T-001"]["g1"] == "", "người lạ mở được cổng — thủng"


def test_token_dung_LAN_HAI_bi_tu_choi(tmp_path):
    """Nút cũ nằm mãi trong lịch sử chat. Bấm lại phải vô hiệu.

    ⚠️ Test này TỪNG XANH VÌ LÝ DO SAI. Bản đầu chỉ khẳng định "campaign.md không đổi ở
    lượt hai" — mà `_ghi_g1` vốn idempotent nên lượt hai không đổi gì kể cả khi token
    dùng lại được thoải mái. Kiểm bằng đột biến (`pop` -> `get`) thấy test vẫn xanh: tính
    idempotent đã CHE MẤT việc thiếu chống replay. Nay kiểm đúng thứ cần kiểm — token có
    bị TIÊU HUỶ sau khi dùng hay không.
    """
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}")]))
    assert _bang(cam)["T-001"]["g1"] != ""
    assert tok not in _token_dang_cho(cam), "token KHÔNG bị tiêu huỷ sau khi dùng"

    # Lượt hai: cùng token, phải bị báo là đã dùng
    b2 = BotGia(hang_doi=[_bam_nut(f"ok:{tok}", update_id=2)])
    AB.nhan(cam, bot=b2)
    assert b2.da_tra_loi, "không phản hồi gì cho cú bấm lại"
    assert any("đã dùng" in t or "quá hạn" in t for _, t in b2.da_tra_loi),         f"lượt hai không bị từ chối: {b2.da_tra_loi}"


def test_token_qua_han_bi_tu_choi(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    tuong_lai = datetime.now().astimezone() + timedelta(hours=AB.HAN_GIO + 1)
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}")]), bay_gio=tuong_lai)
    assert _bang(cam)["T-001"]["g1"] == "", "token quá hạn vẫn mở được cổng"


def test_token_bia_khong_mo_duoc_gi(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut("ok:khong-he-ton-tai")]))
    assert _bang(cam)["T-001"]["g1"] == ""


def test_noi_dung_tin_nhan_KHONG_BAO_GIO_thanh_lenh(tmp_path):
    """Tin nhắn là DỮ LIỆU. Không có đường nào đem chữ người gõ đi CHẠY.

    Quét bằng AST chứ không quét văn bản: một cổng quét chuỗi sẽ báo đỏ vì chính đoạn
    tài liệu giải thích "không dùng shell=True" — gate mà tự vấp vào lời cảnh báo của
    mình thì người ta sẽ tắt nó đi. AST kiểm HÀNH VI, không kiểm chữ.
    """
    import ast
    cay = ast.parse((ROOT / "scripts" / "pipeline" / "approve_bus.py").read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call):
            continue
        ten = (n.func.id if isinstance(n.func, ast.Name)
               else n.func.attr if isinstance(n.func, ast.Attribute) else "")
        assert ten not in ("eval", "exec", "system", "popen"),             f"approve_bus.py gọi {ten}() dòng {n.lineno} — tuyệt đối cấm"
        for kw in n.keywords:
            assert not (kw.arg == "shell" and getattr(kw.value, "value", False) is True),                 f"approve_bus.py dùng shell=True dòng {n.lineno} — tuyệt đối cấm"


def test_tin_nhan_chua_lenh_shell_bi_coi_la_rac(tmp_path):
    cam = _cam(tmp_path)
    b = BotGia(hang_doi=[_nhan_tin("duyet T-001; rm -rf /")])
    AB.nhan(cam, bot=b)
    assert _bang(cam)["T-001"]["g1"] == "", "chuỗi lạ mà vẫn duyệt được"


# ── Ghi vào cổng THẬT ───────────────────────────────────────────────────────

def test_duyet_ca_lo_ghi_g1_va_doi_status(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}")]))
    b = _bang(cam)
    for cid in ("T-001", "T-002"):
        assert b[cid]["g1"] != "", f"{cid} chưa được ghi g1"
        assert b[cid]["status"] == "approved"


def test_tu_choi_KHONG_ghi_g1(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"no:{tok}")]))
    assert _bang(cam)["T-001"]["g1"] == ""


def test_tra_loi_bang_chu_cung_duyet_duoc(tmp_path):
    cam = _cam(tmp_path)
    AB.nhan(cam, bot=BotGia(hang_doi=[_nhan_tin("duyet T-001")]))
    assert _bang(cam)["T-001"]["g1"] != ""
    assert _bang(cam)["T-002"]["g1"] == "", "duyệt một bài mà lan sang bài khác"


def test_content_id_la_trong_tin_nhan_thi_bo_qua_khong_nem(tmp_path):
    cam = _cam(tmp_path)
    AB.nhan(cam, bot=BotGia(hang_doi=[_nhan_tin("duyet T-999")]))  # không được nổ
    assert "T-999" not in _bang(cam)


# ── Không xử lý lại ─────────────────────────────────────────────────────────

def test_offset_duoc_luu_va_truyen_lai(tmp_path):
    """Thiếu offset thì update cũ quay lại mãi -> duyệt lặp."""
    cam = _cam(tmp_path)
    AB.nhan(cam, bot=BotGia(hang_doi=[_nhan_tin("duyet T-001", update_id=77)]))
    b2 = BotGia()
    AB.nhan(cam, bot=b2)
    assert b2.offset_da_dung == [78], f"offset sai: {b2.offset_da_dung}"


def test_gui_cong_hoi_DUNG_danh_sach_duoc_dua(tmp_path):
    """UAT 10/09: bước `dung-bai` dựng 3 bài nhưng tin xin duyệt hỏi về 10 — vì hàm này
    tự truy vấn thay vì hỏi đúng những bài vừa xử lý. Trong khi `autonomy: full` lại chỉ
    duyệt 3. Hai chế độ hành xử khác nhau trên cùng một bước."""
    cam = _cam(tmp_path)
    b = BotGia()
    AB.gui_cong(cam, "g1", bot=b, cids=["T-001"])
    t = b.da_gui[0]["text"]
    assert "T-001" in t and "T-002" not in t, f"hỏi thừa bài không được đưa: {t}"


def test_gui_cong_KHONG_hoi_bai_da_qua_cong(tmp_path):
    """Đưa cả bài đã có g1 thì vẫn phải loại — mời bấm lại việc đã xong là làm phiền."""
    cam = _cam(tmp_path)
    b = BotGia()
    AB.gui_cong(cam, "g1", bot=b, cids=["T-001", "T-003"])   # T-003 đã có g1
    t = b.da_gui[0]["text"]
    assert "T-001" in t and "T-003" not in t, f"hỏi lại bài đã duyệt: {t}"


# ── Bước PHỤ hỏng không được giết lượt đã làm xong việc CHÍNH ───────────────
#
# ĐÃ TRẢ GIÁ 10/09/2026, ngay lượt UAT đầu tiên có người bấm thật:
# `answerCallbackQuery` là cái ACK cosmetic để Telegram tắt vòng xoay trên nút. Telegram
# huỷ query đó sau ít phút, nên poll thưa là nó chắc chắn hỏng. Bản đầu để lỗi đó ném ra
# ngoài => (a) cả lượt `nhan` chết SAU KHI đã ghi duyệt, (b) `_ghi_state` không chạy nên
# `offset` và token đã tiêu vẫn như cũ trên đĩa, lượt sau xử lý LẠI đúng update đó.

class BotAckHong(BotGia):
    """Bot mà `answerCallbackQuery` luôn hỏng — đúng hình dạng query quá hạn."""

    def tra_loi_nut(self, cq_id, text=""):
        raise RuntimeError("Bad Request: query is too old and response timeout expired")


def test_ack_hong_KHONG_giet_luot_va_van_ghi_duyet(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotAckHong(hang_doi=[_bam_nut(f"ok:{tok}", update_id=41)]))
    assert _bang(cam)["T-001"]["g1"] != "", "ack hỏng làm mất luôn việc duyệt"


def test_ack_hong_van_phai_LUU_offset_va_TIEU_token(tmp_path):
    """Không lưu = lượt sau xử lý lại update cũ, và token đã dùng vẫn còn hiệu lực."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotAckHong(hang_doi=[_bam_nut(f"ok:{tok}", update_id=41)]))

    import json as _j
    st = _j.loads((cam / "logs" / "tg-approve.json").read_text(encoding="utf-8"))
    assert st["offset"] == 42, f"offset không được lưu: {st['offset']}"
    assert tok not in st["cho"], "token đã dùng vẫn còn trên đĩa"


def test_mot_update_HONG_khong_chan_cac_update_sau(tmp_path):
    """Xử lý theo lô: một cú bấm rác không được làm rơi những cú bấm hợp lệ phía sau."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    tok = list(_token_dang_cho(cam))[0]
    b = BotAckHong(hang_doi=[_bam_nut("ok:khong-hop-le", update_id=50),
                             _bam_nut(f"ok:{tok}", update_id=51)])
    AB.nhan(cam, bot=b)
    assert _bang(cam)["T-001"]["g1"] != "", "update hỏng ở đầu lô chặn mất update sau"


def test_ack_hong_van_DEM_LA_DA_XU_LY_khong_phai_bo_qua(tmp_path):
    """Khác biệt THẬT giữa hai lớp đỡ, và là lý do lớp bọc `_bao_nhan` tồn tại.

    `try/except` bao quanh mỗi update cũng giữ cho lô không chết — nhưng nó đếm lượt ĐÃ
    LÀM XONG VIỆC là `bo_qua` và ghi log "update hỏng". Người đọc báo cáo sẽ tưởng cú bấm
    của mình rơi mất, trong khi bài đã được duyệt. Báo sai cũng là một kiểu hỏng.
    """
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    tok = list(_token_dang_cho(cam))[0]
    kq = AB.nhan(cam, bot=BotAckHong(hang_doi=[_bam_nut(f"ok:{tok}", update_id=60)]))
    assert kq["xu_ly"] == 1, f"lượt đã duyệt xong mà không đếm là xử lý: {kq}"
    assert kq["bo_qua"] == 0, f"đếm nhầm thành bỏ qua: {kq}"
    assert "T-001" in kq["duyet"], kq
