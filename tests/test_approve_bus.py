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
        self.da_file = []
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

    def gui_tai_lieu(self, duong_dan, chu_thich="", chat=None, **kw):
        from pathlib import Path as _P
        self.da_file.append({"ten": _P(duong_dan).name,
                             "duong_dan": str(duong_dan), "chu_thich": chu_thich})
        return len(self.da_gui) + len(self.da_file)

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


# ── Chế độ liên tục + nhịp sống ─────────────────────────────────────────────
#
# Distill từ OpenClaw 2026.5.12. Ba thay đổi của họ, và ta lấy gì:
#   ① worker tách riêng          -> ĐÃ CÓ (poller là tiến trình riêng, không nằm trong runner)
#   ② spool bền trước khi xử lý  -> KHÔNG lấy: ta chỉ tiến `offset` SAU khi xử lý xong, nên
#                                   chết giữa chừng là replay, và mọi thao tác ghi idempotent.
#                                   Spool thêm một tầng cho lợi ích cận biên ở quy mô này.
#   ③ nhịp sống đo bằng chiều VÀO -> LẤY. Đây là cổng chống chết câm, test bên dưới.

def test_nhip_song_CHI_ghi_khi_chieu_VAO_thanh_cong(tmp_path):
    """Bài học đắt nhất: OpenClaw từng tính lời gọi ĐI RA là 'bot còn sống', nên chiều VÀO
    chết mà không ai biết. Ở đây `gui_cong` vẫn gửi tin đều trong khi `nhan` đã ngừng nhận."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())          # ĐI RA thành công nhiều lần
    AB.gui_cong(cam, "g1", bot=BotGia())
    assert AB._doc_nhip(cam)["co_nhip"] is False, \
        "gửi tin được mà đã tính là poller còn sống — đúng cái bẫy phải tránh"


class BotVaoHong(BotGia):
    def lay_cap_nhat(self, offset=None, timeout=0):
        raise RuntimeError("mạng hỏng")


def test_nhip_song_ghi_sau_luot_VAO_thanh_cong(tmp_path):
    cam = _cam(tmp_path)
    AB.nhan_lien_tuc(cam, bot=BotGia(), giay=0.01, ngu=lambda s: None)
    n = AB._doc_nhip(cam)
    assert n["co_nhip"] and n["song"], n


def test_nhip_qua_han_thi_bao_CHET(tmp_path):
    cam = _cam(tmp_path)
    (cam / "logs").mkdir(exist_ok=True)
    cu = (datetime.now().astimezone() - timedelta(seconds=AB.NHIP_QUA_HAN_GIAY + 60))
    (cam / "logs" / AB.TEN_NHIP).write_text(
        json.dumps({"luot_vao_cuoi": cu.isoformat(), "chu_ky": 9}), encoding="utf-8")
    n = AB._doc_nhip(cam)
    assert n["co_nhip"] and not n["song"], f"nhịp quá hạn mà vẫn báo sống: {n}"


def test_chieu_VAO_hong_thi_KHONG_ghi_nhip(tmp_path):
    cam = _cam(tmp_path)
    AB.nhan_lien_tuc(cam, bot=BotVaoHong(), giay=0.01, ngu=lambda s: None)
    assert AB._doc_nhip(cam)["co_nhip"] is False, "chiều vào hỏng mà vẫn ghi là còn sống"


def test_hong_LIEN_TIEP_thi_thoat_som_khong_quay_tit(tmp_path):
    """Hỏng thật thì đừng quay vòng đốt CPU — thoát để lượt sau dựng lại sạch."""
    cam = _cam(tmp_path)
    da_ngu = []
    kq = AB.nhan_lien_tuc(cam, bot=BotVaoHong(), giay=9999,
                          ngu=da_ngu.append, dong_ho=lambda: 0)
    assert kq["chu_ky"] <= 5, f"không thoát sớm: {kq}"
    assert da_ngu == sorted(da_ngu), f"không lùi dần: {da_ngu}"
    assert max(da_ngu) <= 60, f"lùi quá lâu: {da_ngu}"


def test_canh_bao_khi_co_chien_dich_KHAC_cung_giu_trang_thai_poller(tmp_path, capsys):
    """`getUpdates` một-người-đọc: hai poller ăn trộm update của nhau IM LẶNG, triệu chứng
    là 'bấm lúc ăn lúc không' — gần như không chẩn đoán được nếu không biết trước."""
    cam = _cam(tmp_path)
    khac = cam.parent / "CD-KHAC" / "logs"
    khac.mkdir(parents=True)
    (khac / AB.TEN_STATE).write_text('{"offset": null, "cho": {}}', encoding="utf-8")

    ds = AB.canh_bao_hai_poller(cam)
    assert "CD-KHAC" in ds, ds
    assert "HAI POLLER" in capsys.readouterr().err


def test_mot_minh_thi_KHONG_canh_bao_nham(tmp_path, capsys):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())          # tự nó có state, không được tự tố mình
    assert AB.canh_bao_hai_poller(cam) == []
    assert "HAI POLLER" not in capsys.readouterr().err


# ── Tranh chấp trạng thái giữa `gui` và `nhan` ──────────────────────────────
#
# ĐÃ TRẢ GIÁ 10/09/2026 — lỗi làm MẤT CÚ BẤM CỦA NGƯỜI, kiểu tệ nhất:
#   1. `nhan` nạp state vào bộ nhớ rồi long-poll **50 giây**
#   2. giữa lúc đó `gui` thêm token mới và ghi file
#   3. `nhan` kết thúc chu kỳ, `_ghi_state` ghi đè bằng bản trong bộ nhớ -> token mới BIẾN MẤT
#   4. người bấm nút -> không tìm thấy token -> "đã dùng rồi hoặc quá hạn", KHÔNG ghi gì
#
# Cửa sổ tranh chấp đúng bằng thời gian long-poll, nên nó xảy ra MỌI LẦN gửi cổng trong lúc
# poller chạy — tức là luôn luôn. Chạy tay từng lệnh thì không bao giờ thấy.

class BotChenGiua(BotGia):
    """Giả lập `gui` chen vào giữa lúc `nhan` đang long-poll."""

    def __init__(self, cam, **kw):
        super().__init__(**kw)
        self._cam = cam

    def lay_cap_nhat(self, offset=None, timeout=0):
        # Trong lúc "long-poll", một tiến trình khác thêm token vào file.
        st = AB._doc_state(self._cam)
        st["cho"]["cheninnnn123456ab"] = {
            "cong": "g1", "content_ids": ["T-002"], "campaign": "CD-THU",
            "het_han": (datetime.now().astimezone() + timedelta(hours=1)).isoformat(),
            "tao_luc": datetime.now().astimezone().isoformat()}
        AB._ghi_state(self._cam, st)
        return super().lay_cap_nhat(offset=offset, timeout=timeout)


def test_nhan_KHONG_duoc_xoa_token_do_tien_trinh_khac_vua_them(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    AB.nhan(cam, bot=BotChenGiua(cam, hang_doi=[]))
    assert "cheninnnn123456ab" in _token_dang_cho(cam), \
        "token do `gui` thêm giữa chừng bị `nhan` ghi đè mất — CÚ BẤM CỦA NGƯỜI SẼ RƠI"


def test_nhan_van_TIEU_dung_token_no_da_dung(tmp_path):
    """Hoà giải chứ không phải bỏ ghi: token mình vừa dùng vẫn phải biến mất."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    tok = [t for t in _token_dang_cho(cam)][0]
    AB.nhan(cam, bot=BotChenGiua(cam, hang_doi=[_bam_nut(f"ok:{tok}", update_id=80)]))
    con = _token_dang_cho(cam)
    assert tok not in con, "token đã dùng vẫn còn — chống replay thủng"
    assert "cheninnnn123456ab" in con, "vẫn xoá mất token của tiến trình khác"
    assert _bang(cam)["T-001"]["g1"] != ""


# ── T1 · Lock một-tiến-trình ────────────────────────────────────────────────
#
# GỐC của bệnh 10/09: Task Scheduler bắn mỗi phút, `MultipleInstances=IgnoreNew` chỉ chặn
# khi Windows còn THẤY instance cũ. Instance chết sớm là lượt sau vào ngay ⇒ nhiều poller
# chồng nhau ghi đè trạng thái của nhau.
#
# Phép thử "còn sống" dùng NHỊP trong lock, KHÔNG dùng PID:
# Windows tái dùng PID, nên một PID sống không chứng minh được đó là poller của ta. Còn
# nhịp thì chỉ chính poller đang chạy mới gia hạn được — không ai giả được nó.

def test_gianh_duoc_lock_khi_chua_ai_giu(tmp_path):
    cam = _cam(tmp_path)
    assert AB.gianh_lock(cam) is not None


def test_NGUOI_THU_HAI_khong_gianh_duoc(tmp_path):
    cam = _cam(tmp_path)
    assert AB.gianh_lock(cam) is not None
    assert AB.gianh_lock(cam) is None, "hai poller cùng giành được — đúng bệnh phải chặn"


def test_lock_CHET_thi_nguoi_sau_chiem_duoc(tmp_path):
    """Poller bị kill giữa chừng không được làm kẹt cổng duyệt vĩnh viễn."""
    cam = _cam(tmp_path)
    AB.gianh_lock(cam)
    sau = datetime.now().astimezone() + timedelta(seconds=AB.LOCK_QUA_HAN + 30)
    assert AB.gianh_lock(cam, bay_gio=sau) is not None, "lock chết vẫn chặn — kẹt vĩnh viễn"


def test_gia_han_giu_lock_song(tmp_path):
    cam = _cam(tmp_path)
    AB.gianh_lock(cam)
    sau = datetime.now().astimezone() + timedelta(seconds=AB.LOCK_QUA_HAN + 30)
    AB.gia_han_lock(cam, chu_ky=7, bay_gio=sau)
    xa = sau + timedelta(seconds=10)
    assert AB.gianh_lock(cam, bay_gio=xa) is None, "gia hạn rồi mà vẫn bị chiếm"


def test_nha_lock_thi_nguoi_sau_vao_ngay(tmp_path):
    cam = _cam(tmp_path)
    AB.gianh_lock(cam)
    AB.nha_lock(cam)
    assert AB.gianh_lock(cam) is not None


def test_lock_hong_file_thi_KHONG_lam_ket(tmp_path):
    """File lock hỏng không được biến thành cổng chặn vĩnh viễn."""
    cam = _cam(tmp_path)
    (cam / "logs").mkdir(exist_ok=True)
    (cam / "logs" / AB.LOCK_TEN).write_text("{ hỏng", encoding="utf-8")
    assert AB.gianh_lock(cam) is not None


def test_nhan_lien_tuc_THOAT_NGAY_khi_da_co_poller(tmp_path):
    """Đường chạy BÌNH THƯỜNG mỗi phút: có poller rồi thì thoát êm, không log ồn."""
    cam = _cam(tmp_path)
    AB.gianh_lock(cam)
    # Đồng hồ giả TIẾN thật: bỏ cổng lock thì test phải ĐỎ NHANH, không được TREO.
    # Bản đầu dùng đồng hồ thật + giay=9999 nên khi đột biến gỡ lock, nó chạy 9999 giây —
    # "treo" cũng là một dạng đỏ, nhưng nó làm cả bộ test đứng và không ai chờ nổi.
    t = iter(range(0, 100))
    kq = AB.nhan_lien_tuc(cam, bot=BotGia(), giay=3, ngu=lambda s: None,
                          dong_ho=lambda: next(t))
    assert kq.get("bo_qua_vi_lock") is True, kq
    assert kq["chu_ky"] == 0, f"đã có poller mà vẫn poll: {kq}"


def test_vong_lap_PHAI_gia_han_lock_moi_chu_ky(tmp_path):
    """Kiểm hàm `gia_han_lock` chạy đúng là CHƯA đủ — phải kiểm vòng lặp có GỌI nó.

    Không gia hạn thì lock của một poller sống lâu sẽ hết hạn sau LOCK_QUA_HAN và tiến
    trình khác chiếm mất, quay lại đúng bệnh nhiều-poller.
    """
    cam = _cam(tmp_path)
    t = iter(range(0, 100))
    AB.nhan_lien_tuc(cam, bot=BotGia(), giay=4, ngu=lambda s: None,
                     dong_ho=lambda: next(t))
    # Lock đã nhả lúc thoát, nên soi qua nhịp mà vòng lặp ghi lại
    assert AB._doc_nhip(cam)["chu_ky"] >= 1
    # Giành lại rồi chạy tiếp, lần này chặn nhả để soi lock
    goc = AB.nha_lock
    AB.nha_lock = lambda c: None
    try:
        t2 = iter(range(0, 100))
        AB.nhan_lien_tuc(cam, bot=BotGia(), giay=4, ngu=lambda s: None,
                         dong_ho=lambda: next(t2))
        d = AB._doc_lock(cam)
        assert d is not None and d.get("chu_ky", 0) >= 1, \
            f"vòng lặp không gia hạn lock: {d}"
    finally:
        AB.nha_lock = goc


def test_thoat_thi_PHAI_nha_lock(tmp_path):
    """Không nhả thì lượt sau phải chờ hết LOCK_QUA_HAN mới vào được — kẹt cổng 3 phút."""
    cam = _cam(tmp_path)
    t = iter(range(0, 100))
    AB.nhan_lien_tuc(cam, bot=BotGia(), giay=3, ngu=lambda s: None,
                     dong_ho=lambda: next(t))
    assert AB._doc_lock(cam) is None, "thoát rồi mà lock còn nằm lại"
    assert AB.gianh_lock(cam) is not None, "lượt sau không vào được ngay"


# ── T4 · Log theo CHU KỲ, không chỉ lúc thoát ───────────────────────────────

def test_chu_ky_CO_VIEC_thi_ghi_log_NGAY(tmp_path):
    """`--lien-tuc` chạy 55 phút mà chỉ in kết quả ở cuối ⇒ lỗi vô hình tới 55 phút."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    tok = list(_token_dang_cho(cam))[0]
    t = iter(range(0, 100))
    AB.nhan_lien_tuc(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}", update_id=90)]),
                     giay=3, ngu=lambda s: None, dong_ho=lambda: next(t))
    logs = list((cam / "logs").glob("tg-poller-*.log"))
    assert logs, "không ghi log nào dù đã xử lý một cú bấm"
    assert "T-001" in logs[0].read_text(encoding="utf-8")


def test_chu_ky_RONG_thi_KHONG_ghi_log_rac(tmp_path):
    """Mỗi 50 giây một dòng 'không có gì' = 1.700 dòng/ngày, log thành rác không ai đọc."""
    cam = _cam(tmp_path)
    t = iter(range(0, 100))
    AB.nhan_lien_tuc(cam, bot=BotGia(), giay=5, ngu=lambda s: None, dong_ho=lambda: next(t))
    logs = list((cam / "logs").glob("tg-poller-*.log"))
    assert not logs or not logs[0].read_text(encoding="utf-8").strip(), \
        "chu kỳ rỗng mà vẫn ghi log"


def test_chu_ky_HONG_thi_ghi_log_NGAY(tmp_path):
    cam = _cam(tmp_path)
    AB.nhan_lien_tuc(cam, bot=BotVaoHong(), giay=99, ngu=lambda s: None, dong_ho=lambda: 0)
    logs = list((cam / "logs").glob("tg-poller-*.log"))
    assert logs and "HỎNG" in logs[0].read_text(encoding="utf-8"), \
        "lỗi không được ghi ra log — sẽ vô hình tới lúc tiến trình thoát"


# ── T2 · Token chỉ TIÊU khi việc đã XONG ────────────────────────────────────
#
# Thay cho "hàng đợi bền" của OpenClaw. Rủi ro thật hẹp hơn kiến trúc của họ nhiều: token
# bị đánh dấu đã tiêu TRƯỚC khi `_ap_dung` chạy, nên ghi cổng hỏng là cú bấm rơi vĩnh viễn
# — người bấm lại thì nút báo "đã dùng rồi". Sửa đúng chỗ đó rẻ hơn nhập cả hàng đợi.

def test_ghi_cong_HONG_thi_token_KHONG_bi_tieu(tmp_path, monkeypatch):
    """Cú bấm chỉ được tính là đã dùng khi cổng ĐÃ ghi. Hỏng thì phải bấm lại được."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    tok = list(_token_dang_cho(cam))[0]

    def hong(*a, **k):
        raise RuntimeError("đĩa đầy")
    monkeypatch.setattr(AB, "_ap_dung", hong)

    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}", update_id=95)]))
    assert tok in _token_dang_cho(cam), \
        "ghi cổng hỏng mà token vẫn bị tiêu — cú bấm rơi vĩnh viễn, bấm lại báo 'đã dùng'"


def test_ghi_cong_XONG_thi_token_BI_TIEU(tmp_path):
    """Mặt kia của cùng một luật: xong việc rồi thì token phải chết, chống replay."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"])
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}", update_id=96)]))
    assert tok not in _token_dang_cho(cam)
    assert _bang(cam)["T-001"]["g1"] != ""


# ── Phản hồi bằng VĂN BẢN, gắn với bài qua reply ────────────────────────────
#
# Thay cho nút "Sửa lại" (Đức chốt 10/09): Đức TRẢ LỜI thẳng vào tin của bài, gõ nhận xét
# tự do. Không phải nhớ mã bài — Telegram cho biết tin nào đang được trả lời, ta tra ngược
# `message_id -> content_id` từ lúc gửi.
#
# ⚠️ Văn bản đó sẽ được đưa vào prompt viết lại. Nó là DỮ LIỆU của người, không phải mệnh
# lệnh cho hệ thống: lưu vào file, chèn vào prompt trong khối có rào rõ ràng, không nối
# chuỗi thành chỉ thị.

def _tra_loi_tin(text, msg_id, chat_id=CHAT_OK, update_id=1):
    return {"update_id": update_id,
            "message": {"message_id": 500, "chat": {"id": chat_id}, "text": text,
                        "reply_to_message": {"message_id": msg_id}}}


def test_tra_loi_vao_tin_cua_bai_thi_ghi_PHAN_HOI(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"], che_do="per_post")
    mid = AB._tra_tin_bai(cam, "T-001")
    assert mid, "gửi per_post mà không ghi lại message_id -> không tra ngược được"

    AB.nhan(cam, bot=BotGia(hang_doi=[
        _tra_loi_tin("Mở bài dài quá, cắt còn 2 câu. Thiếu ví dụ doanh nghiệp Việt.", mid)]))
    ph = AB.doc_phan_hoi(cam, "T-001")
    assert ph and "cắt còn 2 câu" in ph[-1]["noi_dung"]


def test_phan_hoi_KHONG_duoc_coi_la_duyet(tmp_path):
    """Gõ nhận xét không phải là gật đầu. Nhầm chiều là đăng bài đang bị chê."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"], che_do="per_post")
    mid = AB._tra_tin_bai(cam, "T-001")
    AB.nhan(cam, bot=BotGia(hang_doi=[_tra_loi_tin("viết lại đoạn hai", mid)]))
    assert _bang(cam)["T-001"]["g1"] == "", "phản hồi mà lại mở cổng — sai chiều nguy hiểm"


def test_phan_hoi_giu_DU_nhieu_lan(tmp_path):
    """Vòng viết lại có thể lặp. Ghi đè lần trước là mất dấu vết vì sao bài thành ra thế."""
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"], che_do="per_post")
    mid = AB._tra_tin_bai(cam, "T-001")
    AB.nhan(cam, bot=BotGia(hang_doi=[_tra_loi_tin("lần một", mid, update_id=1)]))
    AB.nhan(cam, bot=BotGia(hang_doi=[_tra_loi_tin("lần hai", mid, update_id=2)]))
    ph = AB.doc_phan_hoi(cam, "T-001")
    assert len(ph) == 2 and ph[0]["noi_dung"] == "lần một"


def test_tra_loi_tin_LA_thi_bo_qua(tmp_path):
    cam = _cam(tmp_path)
    AB.nhan(cam, bot=BotGia(hang_doi=[_tra_loi_tin("gì đó", 99999)]))
    assert AB.doc_phan_hoi(cam, "T-001") == []


def test_chat_LA_gui_phan_hoi_thi_bo_qua(tmp_path):
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia(), cids=["T-001"], che_do="per_post")
    mid = AB._tra_tin_bai(cam, "T-001")
    AB.nhan(cam, bot=BotGia(hang_doi=[_tra_loi_tin("phá hoại", mid, chat_id=CHAT_LA)]))
    assert AB.doc_phan_hoi(cam, "T-001") == []


# --------------------------------------------------------------------------------------
# CỔNG 2 KHÔNG ĐƯỢC MỜI DUYỆT BÀI CHƯA VIẾT
# --------------------------------------------------------------------------------------

def _dung_bai(cam, folder, *, viet_that):
    """Dựng thư mục bài. `viet_that=False` để nguyên KHUÔN (còn `{{...}}`)."""
    d = cam / folder
    d.mkdir(parents=True, exist_ok=True)
    if viet_that:
        than = "Mở bài bằng một câu chuyện đời thường. " * 60
        (d / "content.md").write_text(f"## post:blog_article\n\n# Tiêu đề\n\n{than}\n",
                                      encoding="utf-8")
    else:
        (d / "content.md").write_text(
            "## post:blog_article\n\n> Hướng dẫn của khuôn.\n\n# {{tieu_de}}\n\n{{noi_dung}}\n",
            encoding="utf-8")
    return d


def test_g2_KHONG_duoc_moi_duyet_bai_chua_viet(tmp_path):
    """Cổng 2 nghĩa là "đọc bài rồi quyết". Bài chưa có chữ thì không có gì để đọc.

    ĐÃ XẢY RA THẬT 11/09/2026: gọi `approve_bus gui --cong g2 --lo 5` gửi đi một tin mời
    duyệt 5 bài, trong đó 3 bài `content.md` vẫn còn nguyên khuôn. Người bấm "Duyệt cả lô"
    là mở cổng cho ba bài rỗng đi tiếp tới bước đăng.

    Cùng họ với lỗi `_da_viet` fail-open hôm 10/09 — lần đó vá ở `soan`, nhưng cổng G2 gọi
    thẳng `cho_cong()` (truy vấn BẢNG thuần) nên đi vòng qua chỗ đã vá.
    """
    cam = _cam(tmp_path)
    # T-003 đã qua g1, đang chờ g2 — nhưng để nguyên khuôn, chưa ai viết.
    _dung_bai(cam, "T-003_bai-ba", viet_that=False)

    b = BotGia()
    kq = AB.gui_cong(cam, "g2", bot=b)

    assert kq["gui"] == 0, f"đã gửi tin mời duyệt bài chưa viết: {kq}"
    assert not b.da_gui, f"không được nhắn gì cả, nhưng đã gửi: {b.da_gui}"


def test_g2_VAN_moi_duyet_bai_da_viet_that(tmp_path):
    """Mặt kia của cổng: vá xong không được chặn nhầm bài đã viết tử tế."""
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")   # G2 nay fail-closed: chua cham = khong duoc hoi

    b = BotGia()
    kq = AB.gui_cong(cam, "g2", bot=b)

    assert kq["gui"] == 1, f"bài đã viết mà không được mời duyệt: {kq}"


def test_cong2_PHAI_gui_KEM_BAI_chu_khong_chi_tieu_de(tmp_path):
    """Cổng 2 bắt người DUYỆT NỘI DUNG — nội dung phải tới được tay họ.

    ĐÃ XẢY RA THẬT 11/09/2026: Đức nhận tin cổng 2 rồi hỏi lại *"nếu đã có nội dung tại sao
    tôi không thấy file gửi lên telegram"*. Tin chỉ chở mã bài + tiêu đề; `telegram_io` lúc
    đó **không có hàm gửi file nào cả**.

    Một cổng mời người gật đầu về thứ họ không nhìn thấy thì không phải cổng — nó là con
    dấu cao su. Cùng họ với `_da_viet` fail-open: hình thức có cổng, thực chất không chặn gì.

    Cổng 1 thì KHÔNG cần, và test dưới khẳng định điều đó: duyệt đề tài chỉ cần tiêu đề.
    """
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")   # G2 nay fail-closed: chua cham = khong duoc hoi

    b = BotGia()
    AB.gui_cong(cam, "g2", bot=b)

    assert b.da_file, "cổng 2 không gửi file nào — người duyệt không có gì để đọc"
    assert any("T-003" in f["duong_dan"] for f in b.da_file),         f"không thấy bài T-003 trong các file đã gửi: {b.da_file}"


def test_cong1_KHONG_gui_file(tmp_path):
    """Mặt kia: cổng 1 duyệt ĐỀ TÀI, liếc một dòng là quyết. Gửi file là làm phiền."""
    cam = _cam(tmp_path)
    b = BotGia()
    AB.gui_cong(cam, "g1", bot=b)
    assert not b.da_file, f"cổng 1 không nên gửi file: {b.da_file}"


# --------------------------------------------------------------------------------------
# CỔNG 2 FAIL-CLOSED THEO 23 CỔNG MÁY  ·  TRẢ LỜI VÀO FILE BÀI
# --------------------------------------------------------------------------------------

def _cham_diem(cam, folder, ket_luan, do_chan=0):
    import json as _j
    (cam / folder / "gates.json").write_text(_j.dumps({
        "tong": 23, "xanh": 23 - do_chan, "do_chan": do_chan,
        "do_canh_bao": 0, "thieu": 0, "ket_luan": ket_luan,
        "cong": [{"ma": "G01", "cong": "Độ dài blog (từ)", "do_duoc": 2079,
                  "luat": "2500-4000", "trang_thai": "do", "muc": "chan"}] * do_chan,
    }, ensure_ascii=False), encoding="utf-8")


def test_g2_CHAN_bai_truot_cong_may(tmp_path):
    """Máy đã chấm ĐỎ thì đừng hỏi người. Đức chốt 11/09/2026: chặn hẳn.

    ĐÃ XẢY RA THẬT: NEN-001 trượt 7 cổng chặn (thiếu 400 từ, 0 nguồn, còn 2 placeholder)
    mà vẫn được gửi lên Telegram xin duyệt, không một lời cảnh báo. Người duyệt không có
    cách nào biết — họ đâu có chạy lại 23 cổng trong đầu.
    """
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "do", do_chan=7)

    b = BotGia()
    kq = AB.gui_cong(cam, "g2", bot=b)

    assert kq["gui"] == 0, f"đã mời duyệt bài máy chấm ĐỎ: {kq}"
    assert not b.da_file, "không được gửi cả file của bài đỏ"


def test_g2_CHAN_bai_chua_cham_bao_gio(tmp_path):
    """Không có `gates.json` = CHƯA ĐO, không phải ĐÃ QUA. Fail-closed.

    Ca thật: NEN-002 được viết bằng cách gọi thẳng bộ viết, nhảy cóc qua bước chấm B4 —
    có `content.md` đầy đủ nhưng chưa một cổng nào chạy.
    """
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)      # cố tình KHÔNG có gates.json

    b = BotGia()
    kq = AB.gui_cong(cam, "g2", bot=b)
    assert kq["gui"] == 0, f"đã mời duyệt bài chưa chấm cổng nào: {kq}"


def test_g2_CHO_QUA_bai_xanh(tmp_path):
    """Mặt kia: chặt tay rồi thì đừng chặn nhầm bài đã xanh."""
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")

    b = BotGia()
    assert AB.gui_cong(cam, "g2", bot=b)["gui"] == 1


def test_tra_loi_vao_FILE_BAI_ghi_duoc_nhan_xet_o_che_do_LO(tmp_path):
    """Trả lời vào file bài = nhận xét cho ĐÚNG bài đó, kể cả khi duyệt theo LÔ.

    ĐÃ HỎNG TỚI 11/09/2026: `tin_bai` chỉ được ghi ở nhánh `per_post`. Chiến dịch chạy
    `batch_gate` nên bảng tra rỗng, người trả lời vào tin thì `_bai_cua_tin` trả None và
    nhận xét **rơi vào hư không, không một lời báo**.

    Tin gộp cũng không phải chỗ neo được: nó liệt kê 5 bài, trả lời vào đó thì biết là bài
    nào? File bài mới là chỗ neo đúng — mỗi bài một file.
    """
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")

    b = BotGia()
    AB.gui_cong(cam, "g2", bot=b, che_do="batch_gate")

    mid = AB._tra_tin_bai(cam, "T-003")
    assert mid is not None, "không nhớ tin nào thuộc bài nào ⇒ trả lời sẽ rơi vào hư không"

    b2 = BotGia([{"update_id": 7, "message": {
        "message_id": 99, "chat": {"id": CHAT_OK},
        "reply_to_message": {"message_id": mid},
        "text": "Mở bài dài quá, cắt bớt đoạn thứ hai."}}])
    AB.nhan(cam, bot=b2)

    ghi = AB.doc_phan_hoi(cam, "T-003")
    assert ghi and "cắt bớt" in ghi[-1]["noi_dung"], f"không ghi được nhận xét: {ghi}"


def _tra_loi(mid, text, update_id=8):
    return {"update_id": update_id, "message": {
        "message_id": 500 + update_id, "chat": {"id": CHAT_OK},
        "reply_to_message": {"message_id": mid}, "text": text}}


def test_tra_loi_vao_bai_bang_chu_DUYET_thi_phai_DUYET_chu_khong_phai_ghi_nhan_xet(tmp_path, monkeypatch):
    """Trả lời vào bài rồi gõ "duyet" là Ý DUYỆT, không phải lời góp ý.

    Bẫy có thật: nhánh ghi nhận xét đứng TRƯỚC nhánh lệnh và `return` sớm, nên mọi câu trả
    lời — kể cả "duyet" — đều bị ghi thành nhận xét. Người dùng gõ "duyet" rồi tưởng đã
    duyệt, trong khi cổng vẫn đóng và bài nằm im. Hỏng CÂM, đúng loại tệ nhất.

    Không cần gõ lại mã bài: đang trả lời vào đúng bài đó rồi.
    """
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")

    b = BotGia()
    AB.gui_cong(cam, "g2", bot=b, che_do="batch_gate")
    mid = AB._tra_tin_bai(cam, "T-003")

    # Assert vào CƠ CHẾ (tin này được định tuyến thành LỆNH hay thành NHẬN XÉT), không vào
    # hệ quả ghi `publish.json` — hệ quả đó còn phụ thuộc `register_publish init` đã chạy
    # chưa, nên nó có thể xanh/đỏ vì lý do chẳng liên quan gì tới thứ đang kiểm.
    goi = []
    that = AB._thi_hanh_lenh

    def ghi_lai(cam_, cid_, lenh_, ly_do_, **kw):
        goi.append((cid_, lenh_))
        return that(cam_, cid_, lenh_, ly_do_, **kw)

    # `monkeypatch` tự hoàn nguyên cuối test. Gán thẳng `AB._thi_hanh_lenh = ...` thì bản
    # vá SỐNG SANG các test sau trong cùng phiên — rò rỉ kiểu đó gây đỏ ở chỗ chẳng liên quan.
    monkeypatch.setattr(AB, "_thi_hanh_lenh", ghi_lai)

    b2 = BotGia([_tra_loi(mid, "duyet")])
    AB.nhan(cam, bot=b2)

    assert goi, "gõ 'duyet' mà KHÔNG đi vào nhánh lệnh — nó bị nuốt thành nhận xét"
    assert goi[0][0] == "T-003", f"duyệt nhầm bài: {goi}"
    assert goi[0][1].lower().startswith("duy"), f"hiểu sai lệnh: {goi}"
    assert not AB.doc_phan_hoi(cam, "T-003"), "không được ghi 'duyet' thành nhận xét"


def test_tra_loi_vao_bai_bang_chu_thuong_van_la_nhan_xet(tmp_path):
    """Mặt kia: câu chữ bình thường vẫn phải vào sổ nhận xét, không được nhầm thành lệnh."""
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")

    b = BotGia()
    AB.gui_cong(cam, "g2", bot=b, che_do="batch_gate")
    mid = AB._tra_tin_bai(cam, "T-003")

    b2 = BotGia([_tra_loi(mid, "Đoạn mở bài dài quá, cắt bớt giúp mình")])
    kq = AB.nhan(cam, bot=b2)

    assert not kq["duyet"], f"câu góp ý bị hiểu thành lệnh duyệt: {kq}"
    assert AB.doc_phan_hoi(cam, "T-003"), "nhận xét không được ghi"


# --------------------------------------------------------------------------------------
# VÒNG KHÉP: duyệt / góp ý trên Telegram PHẢI sinh ra việc trong hàng chờ
# --------------------------------------------------------------------------------------

def _hc():
    import work_queue
    return work_queue


def test_DUYET_sinh_ra_VIEC_trong_work_queue(tmp_path):
    """Duyệt xong mà không gì chạy tiếp thì cổng chỉ là cái nút trang trí.

    Trước 12/09/2026 poller ghi cột `g1` rồi DỪNG — không task nào chạy bước kế, nên bài
    duyệt xong nằm im vô thời hạn.
    """
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}")]))

    assert _hc().dem(cam)["cho"] >= 1, "duyệt rồi mà hàng chờ vẫn rỗng ⇒ vòng chưa khép"


def test_PHAN_HOI_sinh_ra_VIEC_viet_lai(tmp_path):
    """Bot nói "bài sẽ được viết lại" thì phải có thứ thật sự làm việc đó.

    Câu đó từng là LỜI HỨA SUÔNG: nhận xét được ghi, nhưng không gì chạy bước viết lại.
    """
    cam = _cam(tmp_path)
    _dung_bai(cam, "T-003_bai-ba", viet_that=True)
    _cham_diem(cam, "T-003_bai-ba", "xanh")
    b = BotGia()
    AB.gui_cong(cam, "g2", bot=b, che_do="batch_gate")
    mid = AB._tra_tin_bai(cam, "T-003")

    truoc = _hc().dem(cam)["cho"]
    AB.nhan(cam, bot=BotGia([_tra_loi(mid, "Mở bài dài quá, cắt bớt giúp mình")]))
    assert _hc().dem(cam)["cho"] == truoc + 1, "góp ý xong không có việc nào được xếp"


def test_moi_quyet_dinh_deu_VAO_SO_SU_KIEN(tmp_path):
    """Sổ sự kiện là thứ duy nhất trả lời được *vì sao* bài tới trạng thái hiện tại."""
    import event_log
    cam = _cam(tmp_path)
    AB.gui_cong(cam, "g1", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}")]))

    ds = event_log.doc(cam)
    assert any(x["viec"] == "g1_duyet" for x in ds), [x["viec"] for x in ds]


# --------------------------------------------------------------------------------------
# CỔNG 3 — duyệt BẢN THẬT trên web
# --------------------------------------------------------------------------------------

FM_G3 = FM.replace(
    "| status | g1 | g2 | schedule | published | folder |",
    "| status | g1 | g2 | g3 | schedule | published | folder | web |"
).replace(
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
).replace(
    "| approved | 2026-09-01 |  | 2026-09-17 |  | ./T-003_bai-ba |",
    "| approved | 2026-09-01 | 2026-09-02 |  | 2026-09-17 |  | ./T-003_bai-ba | https://x.vn/bai-ba |"
).replace(
    "| proposed |  |  | 2026-09-15 |  | ./T-001_bai-mot |",
    "| proposed |  |  |  | 2026-09-15 |  | ./T-001_bai-mot |  |"
).replace(
    "| proposed |  |  | 2026-09-16 |  | ./T-002_bai-hai |",
    "| proposed |  |  |  | 2026-09-16 |  | ./T-002_bai-hai |  |")


def _cam_g3(tmp_path):
    cam = _cam(tmp_path)
    (cam / "campaign.md").write_text(FM_G3, encoding="utf-8", newline="\n")
    return cam


def test_cong3_PHAI_cho_LINK_ban_that(tmp_path):
    """Cổng 3 nghĩa là "mở link, xem bằng mắt". Gửi mã bài thôi thì không có gì để mở.

    Đây đúng là lỗi con-dấu-cao-su mà Cổng 2 đã dính hôm 11/09: mời người gật đầu về thứ
    họ không nhìn thấy.
    """
    cam = _cam_g3(tmp_path)
    b = BotGia()
    kq = AB.gui_cong(cam, "g3", bot=b)
    assert kq["gui"] == 1, kq
    assert "https://x.vn/bai-ba" in b.da_gui[0]["text"], b.da_gui[0]["text"]


def test_cong3_chi_hoi_bai_DA_len_web(tmp_path):
    """Chưa có trang thật thì chưa có bản thật để duyệt."""
    cam = _cam_g3(tmp_path)
    ds = AB.cho_cong(cam, "g3")
    assert [d["content_id"] for d in ds] == ["T-003"], [d["content_id"] for d in ds]


def test_duyet_cong3_ghi_vao_cot_g3(tmp_path):
    cam = _cam_g3(tmp_path)
    AB.gui_cong(cam, "g3", bot=BotGia())
    tok = list(_token_dang_cho(cam))[0]
    AB.nhan(cam, bot=BotGia(hang_doi=[_bam_nut(f"ok:{tok}")]))
    assert _bang(cam)["T-003"]["g3"] != "", "duyệt Cổng 3 mà cột g3 vẫn trống"


def test_bang_KHONG_khai_cot_g3_thi_khong_co_cong_3(tmp_path):
    """Tương thích ngược: chiến dịch cũ không bị mọc thêm một cổng."""
    cam = _cam(tmp_path)          # bảng gốc, không có cột g3
    assert AB.cho_cong(cam, "g3") == []
    assert AB.gui_cong(cam, "g3", bot=BotGia())["gui"] == 0
