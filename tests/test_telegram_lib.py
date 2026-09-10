# -*- coding: utf-8 -*-
"""`scripts/lib/telegram_io.py` — transport Telegram, CHỖ DUY NHẤT gọi Bot API từ Python.

Vì sao mỗi test dưới đây tồn tại — mỗi cái chặn một cách hỏng cụ thể:

· **Token không được rời khỏi file secret.** Nó chỉ sống trong bộ nhớ một lượt chạy. Lọt vào
  tham số dòng lệnh là lọt vào `Get-CimInstance Win32_Process`; lọt vào biến môi trường là
  mọi tiến trình con đọc được. Đã có một token bị thu hồi vì đúng chuyện này (08/09/2026).
· **`getUpdates` chỉ cho MỘT người đọc trên mỗi bot token.** Không truyền `offset` thì update
  cũ quay lại mãi và cùng một nút được xử lý nhiều lần.
· **Allowlist là cổng, không phải lời dặn.** Bất kỳ ai biết tên bot đều nhắn được cho nó.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import telegram_io as tg  # noqa: E402


def _cfg(tmp_path, chats=None):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "bot_token": "111:AAA-token-gia-dinh-khong-that",
        "chats": chats if chats is not None else {"mac_dinh": {"chat_id": 12345}},
    }, ensure_ascii=False), encoding="utf-8")
    return p


class GoiGia:
    """Thay lớp mạng. Ghi lại mọi lượt gọi để test soi được."""

    def __init__(self, tra_ve=None):
        self.lan = []
        self._tra_ve = tra_ve or {}

    def __call__(self, token, method, payload):
        self.lan.append({"token": token, "method": method, "payload": payload})
        return self._tra_ve.get(method, {"ok": True, "result": {"message_id": 99}})


# ── Đọc cấu hình ────────────────────────────────────────────────────────────

def test_doc_token_tu_file_secret(tmp_path):
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=GoiGia())
    assert b.chat_mac_dinh == 12345


def test_thieu_file_thi_dung_han_khong_doan(tmp_path):
    with pytest.raises(FileNotFoundError):
        tg.Bot(cau_hinh=tmp_path / "khong-co.json", goi=GoiGia())


def test_thieu_bot_token_thi_dung_han(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"chats": {"mac_dinh": {"chat_id": 1}}}), encoding="utf-8")
    with pytest.raises(ValueError) as e:
        tg.Bot(cau_hinh=p, goi=GoiGia())
    assert "bot_token" in str(e.value)


def test_token_khong_bao_gio_lot_vao_repr_hay_str(tmp_path):
    """In một Bot ra log là chuyện sẽ xảy ra. Token không được đi cùng."""
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=GoiGia())
    assert "111:AAA" not in repr(b)
    assert "111:AAA" not in str(b)


def test_khong_nhan_token_qua_tham_so(tmp_path):
    """Hợp đồng: token CHỈ đến từ file. Không có cửa nào khác."""
    import inspect
    tham = inspect.signature(tg.Bot.__init__).parameters
    assert not any("token" in t.lower() for t in tham), \
        f"Bot.__init__ có tham số nhận token: {list(tham)}"


# ── Gửi ─────────────────────────────────────────────────────────────────────

def test_gui_tin_thuong(tmp_path):
    g = GoiGia()
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=g)
    assert b.gui("chào") == 99
    assert g.lan[0]["method"] == "sendMessage"
    assert g.lan[0]["payload"]["chat_id"] == 12345
    assert g.lan[0]["payload"]["text"] == "chào"


def test_gui_kem_nut_dung_hinh_dang_inline_keyboard(tmp_path):
    g = GoiGia()
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=g)
    b.gui_kem_nut("duyệt?", [[("✅ Duyệt", "ok:1"), ("❌ Từ chối", "no:1")]])
    kb = json.loads(g.lan[0]["payload"]["reply_markup"])["inline_keyboard"]
    assert kb == [[{"text": "✅ Duyệt", "callback_data": "ok:1"},
                   {"text": "❌ Từ chối", "callback_data": "no:1"}]]


def test_callback_data_qua_64_byte_thi_dung_han(tmp_path):
    """Telegram cắt cụt `callback_data` > 64 byte. Cắt cụt = nút bấm vào không ăn,
    và KHÔNG có lỗi nào — đúng kiểu hỏng câm phải chặn ở đây."""
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=GoiGia())
    with pytest.raises(ValueError) as e:
        b.gui_kem_nut("x", [[("nhãn", "d" * 65)]])
    assert "64" in str(e.value)


def test_tieng_viet_khong_vo_dau(tmp_path):
    g = GoiGia()
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=g)
    b.gui("Đủ ngữ cảnh rồi mà agent vẫn làm sai việc")
    assert g.lan[0]["payload"]["text"] == "Đủ ngữ cảnh rồi mà agent vẫn làm sai việc"


# ── Nhận ────────────────────────────────────────────────────────────────────

def test_lay_cap_nhat_truyen_offset(tmp_path):
    """Không có offset thì update đã xử lý quay lại mãi -> duyệt lặp."""
    g = GoiGia(tra_ve={"getUpdates": {"ok": True, "result": [{"update_id": 7}]}})
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=g)
    assert b.lay_cap_nhat(offset=5) == [{"update_id": 7}]
    assert g.lan[0]["payload"]["offset"] == 5


def test_api_tra_ok_false_thi_nem_loi(tmp_path):
    """`ok: false` là thất bại. Trả im lặng là để hỏng đi tiếp tới chỗ xa hơn."""
    g = GoiGia(tra_ve={"sendMessage": {"ok": False, "description": "chat not found"}})
    b = tg.Bot(cau_hinh=_cfg(tmp_path), goi=g)
    with pytest.raises(RuntimeError) as e:
        b.gui("x")
    assert "chat not found" in str(e.value)


# ── Allowlist ───────────────────────────────────────────────────────────────

def test_chi_chat_da_khai_moi_duoc_phep(tmp_path):
    b = tg.Bot(cau_hinh=_cfg(tmp_path, {"mac_dinh": {"chat_id": 12345},
                                        "phu": {"chat_id": 777}}), goi=GoiGia())
    assert b.duoc_phep(12345) and b.duoc_phep(777)
    assert not b.duoc_phep(999), "chat lạ mà được phép — cổng thủng"


def test_duoc_phep_so_sanh_theo_SO_khong_theo_CHUOI(tmp_path):
    """Telegram trả `chat_id` là số; cấu hình người gõ tay có thể là chuỗi.
    So sánh lệch kiểu thì allowlist luôn trả False và KHÔNG ai duyệt được gì."""
    b = tg.Bot(cau_hinh=_cfg(tmp_path, {"mac_dinh": {"chat_id": "12345"}}), goi=GoiGia())
    assert b.duoc_phep(12345), "chat_id chuỗi trong file mà số từ API -> phải khớp"


# ── Thời gian chờ socket phải LỚN HƠN thời gian long-poll ───────────────────
#
# ĐÃ TRẢ GIÁ 10/09/2026: socket để cứng 30s trong khi long-poll chặn 50s ⇒ MỌI chu kỳ chết
# ở giây 30. Hậu quả nối nhau và trông như ba bệnh khác nhau: poller tự thoát sau 5 lỗi ·
# Task Scheduler dựng lại mỗi phút · kết nối cũ treo phía Telegram làm lượt mới ăn
# `Conflict`, khiến ta đi tìm một "poller thứ hai" không hề tồn tại.
#
# Hai con số đặt cạnh nhau mà không ràng buộc thì sớm muộn trôi khỏi nhau. Cổng này giữ
# ràng buộc đó.

def test_cho_socket_LON_HON_thoi_gian_long_poll():
    for t in (1, 10, 30, tg.LONG_POLL_MAX, 100):
        assert tg.cho_socket({"timeout": t}) > t, \
            f"socket chờ {tg.cho_socket({'timeout': t})}s mà long-poll chặn {t}s — chết chắc"


def test_cho_socket_du_du_cho_TRAN_that_cua_telegram():
    """Trần đo được là ~50s. Socket phải dư đủ cho lúc Telegram trả lời chậm."""
    assert tg.cho_socket({"timeout": tg.LONG_POLL_MAX}) >= tg.LONG_POLL_MAX + 10


def test_khong_long_poll_thi_van_co_han_hop_ly():
    """Gọi thường (sendMessage…) không được chờ vô hạn."""
    n = tg.cho_socket({})
    assert 10 <= n <= 60, n
