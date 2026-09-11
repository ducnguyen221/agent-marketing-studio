# -*- coding: utf-8 -*-
"""Transport Telegram — CHỖ DUY NHẤT gọi Bot API từ Python trong repo này.

## Vì sao có file này trong khi máy đã có `notify-run.ps1`

`~/.news/engine/notify-run.ps1` là hạ tầng **CỦA MỘT CÁI MÁY** — nó bọc mọi scheduled task
trên máy tác giả và nằm NGOÀI repo. Repo này là public: người clone về phải chạy được mà
không có file đó.

Nên hai bản là **CÓ CHỦ ĐÍCH**, không phải trùng lặp bỏ quên. Ai đọc tới đây và định "dọn
trùng lặp" bằng cách xoá một bên: đừng. Xoá bản Python là repo hết độc lập; sửa
`notify-run.ps1` để gọi sang đây là đụng vào file mà hàng chục scheduled task đang phụ thuộc.
Hai bản dùng CHUNG một hợp đồng secret (`~/.secret/<tài khoản>/config.json`) — đó mới là chỗ
không được để lệch.

## Vì sao tên là `telegram_io` chứ không phải `telegram`

`telegram` là tên gói trên PyPI (`python-telegram-bot`). Thư mục này được chèn vào đầu
`sys.path`, nên một file tên `telegram.py` sẽ **che mất gói thật** ở bất kỳ tiến trình nào
nạp lib này — và che một cách im lặng. Đuôi `_io` cũng khớp `md_io.py` cùng thư mục.

## Hợp đồng secret

Token CHỈ đến từ file. Không tham số, không biến môi trường giữ token — biến môi trường chỉ
giữ ĐƯỜNG DẪN (`TG_CONFIG`). Lý do đã trả giá: token trần trong biến user-scope thì mọi tiến
trình con của mọi phiên đọc được, `Get-ChildItem Env:` in nó ra, và nó lọt vào transcript.
Một token đã phải thu hồi vì đúng chuyện đó (08/09/2026).

```json
{ "bot_token": "…", "chats": { "mac_dinh": { "chat_id": 123 } } }
```
"""
from __future__ import annotations

import json
import secrets
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.telegram.org/bot{token}/{method}"

# Trần long-poll của Telegram, ĐO ĐƯỢC ngày 10/09/2026 trên chính bot này chứ không phải
# trích tài liệu: tài liệu Bot API **không công bố** giá trị lớn nhất cho `timeout`. Xin
# 100s và 60s đều trả về sau **50,7s**. Nên 50 là trần thật; xin hơn chỉ tốn chữ.
#
# Hệ quả thiết kế: một lượt gọi phủ tối đa ~50s. Muốn phủ liên tục thì lặp NHIỀU lượt
# trong một tiến trình (xem `approve_bus.py nhan --lien-tuc`), không phải xin timeout to hơn.
LONG_POLL_MAX = 50

# Telegram cắt cụt `callback_data` dài hơn 64 byte — và cắt IM LẶNG. Nút bấm vào không ăn,
# không có lỗi nào ở đâu cả. Chặn ở đây, lúc gửi, là chỗ duy nhất còn sửa được.
CAP_CALLBACK = 64


def duong_dan_cau_hinh() -> Path:
    """`TG_CONFIG` (chỉ ĐƯỜNG DẪN) → `~/.secret/telegram/config.json`."""
    return Path(os.environ.get("TG_CONFIG")
                or Path.home() / ".secret" / "telegram" / "config.json")


def cho_socket(payload: dict) -> int:
    """Thời gian chờ SOCKET, suy TỪ thời gian long-poll — không phải hằng số rời.

    ĐÃ TRẢ GIÁ 10/09/2026. Socket để cứng 30s trong khi `getUpdates` long-poll chặn 50s ⇒
    **mọi chu kỳ chết ở giây 30**, trước khi Telegram kịp trả lời. Rồi hậu quả nối nhau và
    trông như ba bệnh khác nhau:
      · 5 lỗi liên tiếp -> poller tự thoát
      · Task Scheduler dựng lại sau một phút
      · kết nối cũ vẫn treo phía Telegram -> lượt mới ăn `Conflict: terminated by other
        getUpdates request`, khiến ta đi tìm "poller thứ hai" không hề tồn tại
    Một hằng số lệch, ba triệu chứng, không cái nào trỏ vào gốc.

    Nên nó phải được SUY RA, đừng để hai con số cạnh nhau tự trôi khỏi nhau. Cộng 15s dư
    cho lúc Telegram trả lời chậm và cho độ trễ mạng.
    """
    return int(payload.get("timeout") or 0) + 15 if payload.get("timeout") else 30


def _goi_that(token: str, method: str, payload: dict) -> dict:
    """Lớp mạng thật. Tách riêng để test thay được mà không cần internet."""
    du_lieu = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(API.format(token=token, method=method), data=du_lieu)
    try:
        with urllib.request.urlopen(req, timeout=cho_socket(payload)) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Thân lỗi của Telegram có `description` nói rõ sai gì — đắt hơn mã HTTP nhiều.
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}


def _goi_file_that(token: str, method: str, truong: dict, ten_file: str,
                   noi_dung: bytes) -> dict:
    """Gửi FILE — `multipart/form-data`, không dùng chung đường với `_goi_that`.

    Vì sao phải có đường riêng: `_goi_that` mã hoá bằng `urlencode`, chỉ chở được chuỗi.
    Cổng 2 bắt người DUYỆT NỘI DUNG, nên bài phải tới được tay họ; nhét 40 KB markdown vào
    một tin nhắn thì Telegram cắt ở 4.096 ký tự và người duyệt đọc một bài cụt.
    """
    ranh = "----------boundary" + secrets.token_hex(12)
    dem = []
    for k, v in truong.items():
        dem.append(f"--{ranh}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
                   .encode("utf-8"))
    dem.append(
        f"--{ranh}\r\nContent-Disposition: form-data; name=\"document\"; "
        f"filename=\"{ten_file}\"\r\nContent-Type: text/markdown\r\n\r\n".encode("utf-8"))
    dem.append(noi_dung)
    dem.append(f"\r\n--{ranh}--\r\n".encode("utf-8"))
    than = b"".join(dem)

    req = urllib.request.Request(
        API.format(token=token, method=method), data=than,
        headers={"Content-Type": f"multipart/form-data; boundary={ranh}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}


class Bot:
    """Một bot Telegram. `goi` cho phép test thay lớp mạng."""

    def __init__(self, cau_hinh: Path | str | None = None, *, goi=None, goi_file=None):
        p = Path(cau_hinh) if cau_hinh else duong_dan_cau_hinh()
        if not p.is_file():
            raise FileNotFoundError(
                f"không thấy cấu hình Telegram: {p}\n"
                f"Đặt env TG_CONFIG nếu để chỗ khác. Xem knowledge/toolchains/SECRETS.md.")
        d = json.loads(p.read_text(encoding="utf-8"))

        self._token = d.get("bot_token") or ""
        if not self._token:
            raise ValueError(f"{p}: thiếu `bot_token`.")

        self._chats = d.get("chats") or {}
        if not self._chats:
            raise ValueError(f"{p}: thiếu `chats` — không biết gửi cho ai.")

        self._goi = goi or _goi_that
        self._goi_file = goi_file or _goi_file_that
        self.duong_dan = p

    # ── Danh tính & quyền ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        # KHÔNG in token. Một đối tượng bot sẽ bị in ra log sớm muộn.
        return f"<Bot cấu_hình={self.duong_dan.name} chats={list(self._chats)}>"

    __str__ = __repr__

    def _chat(self, ten: str | None = None):
        ten = ten or os.environ.get("TG_CHAT") or "mac_dinh"
        c = self._chats.get(ten)
        if not c:
            raise KeyError(f"không có chat {ten!r} trong {self.duong_dan}")
        return c["chat_id"]

    @property
    def chat_mac_dinh(self):
        return self._chat()

    def duoc_phep(self, chat_id) -> bool:
        """Allowlist: chỉ chat đã khai trong file secret mới mở được cổng duyệt.

        So sánh theo CHUỖI hai đầu có chủ đích: Telegram trả `chat_id` kiểu số, còn file
        cấu hình do người gõ tay có thể là chuỗi. So lệch kiểu thì hàm này luôn trả False
        và KHÔNG AI duyệt được gì — hỏng câm, đúng loại phải chặn từ đầu.
        """
        cho_phep = {str(c.get("chat_id")) for c in self._chats.values()}
        return str(chat_id) in cho_phep

    # ── Gọi API ─────────────────────────────────────────────────────────────

    def _api(self, method: str, payload: dict) -> dict:
        kq = self._goi(self._token, method, payload)
        if not kq.get("ok"):
            # Ném thay vì trả im lặng: `ok:false` mà đi tiếp nghĩa là lỗi lộ ra ở chỗ xa
            # hơn nhiều, lúc không còn biết vì sao.
            raise RuntimeError(f"Telegram {method} lỗi — {kq.get('description', kq)}")
        return kq

    # ── Gửi ─────────────────────────────────────────────────────────────────

    def gui(self, text: str, chat: str | None = None, *, html: bool = False) -> int:
        p = {"chat_id": self._chat(chat), "text": text, "disable_web_page_preview": "true"}
        if html:
            p["parse_mode"] = "HTML"
        return self._api("sendMessage", p)["result"]["message_id"]

    CAP_CHU_THICH = 1024          # Telegram cắt caption ở 1.024 ký tự

    def gui_tai_lieu(self, duong_dan, chu_thich: str = "", chat: str | None = None) -> int:
        """Gửi một FILE kèm chú thích. Trả `message_id`.

        Dùng cho Cổng 2: người duyệt phải ĐỌC ĐƯỢC bài thì cổng mới có nghĩa. Trước 11/09
        cổng chỉ gửi mã bài + tiêu đề, tức mời người gật đầu về thứ họ không nhìn thấy.

        Chú thích bị CẮT CHỦ ĐỘNG ở `CAP_CHU_THICH`: để Telegram tự cắt thì nó cắt giữa
        chừng và không báo gì.
        """
        d = Path(duong_dan)
        noi_dung = d.read_bytes()
        ct = chu_thich or ""
        if len(ct) > self.CAP_CHU_THICH:
            ct = ct[: self.CAP_CHU_THICH - 1] + "…"
        truong = {"chat_id": str(self._chat(chat))}
        if ct:
            truong["caption"] = ct
        kq = self._goi_file(self._token, "sendDocument", truong, d.name, noi_dung)
        if not kq.get("ok"):
            raise RuntimeError(f"Telegram sendDocument lỗi — {kq.get('description', kq)}")
        return kq["result"]["message_id"]

    @staticmethod
    def _ban_phim(nut) -> str:
        hang = []
        for h in nut:
            o = []
            for nhan, data in h:
                n = len(str(data).encode("utf-8"))
                if n > CAP_CALLBACK:
                    raise ValueError(
                        f"callback_data {n} byte, quá giới hạn {CAP_CALLBACK} của Telegram: "
                        f"{data!r}. Telegram sẽ cắt cụt IM LẶNG và nút bấm vào không ăn.")
                o.append({"text": nhan, "callback_data": data})
            hang.append(o)
        return json.dumps({"inline_keyboard": hang}, ensure_ascii=False)

    def gui_kem_nut(self, text: str, nut, chat: str | None = None,
                    *, html: bool = False) -> int:
        """`nut` = [[(nhãn, callback_data), …], …] — mỗi list con là một hàng."""
        p = {"chat_id": self._chat(chat), "text": text,
             "disable_web_page_preview": "true", "reply_markup": self._ban_phim(nut)}
        if html:
            p["parse_mode"] = "HTML"
        return self._api("sendMessage", p)["result"]["message_id"]

    def sua_tin(self, message_id: int, text: str, nut=None, chat: str | None = None,
                *, html: bool = False) -> None:
        """Sửa tin đã gửi — dùng để GỠ NÚT sau khi bấm, cho nút cũ không bấm lại được."""
        p = {"chat_id": self._chat(chat), "message_id": message_id, "text": text,
             "disable_web_page_preview": "true"}
        if html:
            p["parse_mode"] = "HTML"
        if nut is not None:
            p["reply_markup"] = self._ban_phim(nut)
        self._api("editMessageText", p)

    def tra_loi_nut(self, callback_query_id: str, text: str = "") -> None:
        """Telegram bắt buộc trả lời callback, nếu không nút quay vòng mãi trên máy người bấm."""
        self._api("answerCallbackQuery",
                  {"callback_query_id": callback_query_id, "text": text})

    # ── Nhận ────────────────────────────────────────────────────────────────

    def lay_cap_nhat(self, offset: int | None = None, timeout: int = 0) -> list:
        """`getUpdates`.

        ⚠️ **MỘT NGƯỜI ĐỌC DUY NHẤT trên mỗi bot token.** Telegram giao mỗi update cho tiến
        trình gọi TRƯỚC; tiến trình thứ hai thấy hàng đợi rỗng và không có lỗi nào. Cần thêm
        một bên tiêu thụ thì phải tách bot riêng, đừng chia nhau một token.

        `offset` bắt buộc truyền khi đã xử lý xong: thiếu nó thì update cũ quay lại mãi và
        cùng một nút được xử lý nhiều lần.
        """
        p = {"timeout": timeout}
        if offset is not None:
            p["offset"] = offset
        return self._api("getUpdates", p).get("result", [])
