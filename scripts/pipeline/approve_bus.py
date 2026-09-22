#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cổng duyệt hai chiều qua Telegram — MẶT TIỀN, không phải kho phê duyệt.

## Nó KHÔNG làm gì

Nó **không** giữ trạng thái duyệt của riêng nó, và từ 12/09/2026 nó cũng **không tự ghi
cổng** nữa. Mọi phép ghi nằm ở `approval_gate.py` — kho cổng dùng chung:

```
  approve_bus.py  (Telegram, tuỳ chọn) ─┐
                                        ├─► approval_gate.open_gate() ─► campaign.md · publish.json
  approval_gate.py   (trong phiên, MẶC ĐỊNH)┘
```

Vì sao tách: trước đó script này là **con đường DUY NHẤT** ghi được `g1` và `g3`, nên
Telegram không phải tuỳ chọn mà là điều kiện cần — không có điện thoại thì chiến dịch
đứng. Mà cách làm việc mặc định lại là người ngồi cùng agent trong một phiên.

Đẻ ra kho thứ hai nghĩa là hai nguồn sự thật, và sớm muộn chúng nói khác nhau. File trạng
thái duy nhất ở đây (`logs/tg-approve.json`) chỉ giữ hai thứ **của riêng Telegram**: con
trỏ `offset` và các token đang chờ. Xoá nó đi thì tệ nhất là phải gửi lại tin — không mất
một dấu vết duyệt nào.

## Bốn lớp bảo vệ

1. **Allowlist** — chỉ `chat_id` khai trong file secret mới mở được cổng. Ai cũng nhắn được
   cho một bot Telegram; biết tên bot là nhắn được.
2. **Token một lần** — sinh lúc gửi, xoá ngay khi dùng. Nút cũ nằm mãi trong lịch sử chat;
   không có lớp này thì bấm lại nút của tuần trước là mở lại cổng đã đóng.
3. **Hạn dùng 48 giờ** — token quá hạn coi như không tồn tại.
4. **Tin nhắn là DỮ LIỆU, không phải MỆNH LỆNH.** Không `eval`, không `exec`, không
   `shell=True`, không `os.system`. Chữ người gõ chỉ được so khớp với một mẫu chặt rồi ánh
   xạ sang đúng hai hành động đã khai. Cùng luật với output của agent khác: giữa hai tiến
   trình chạy cùng một tài khoản Windows KHÔNG có biên giới bảo mật nào.

## Lệnh

```
approve_bus.py send    --campaign <đường dẫn> --gate g1|g2|g3 [--batch N] [--mode per_post|batch_gate]
approve_bus.py receive --campaign <đường dẫn> [--follow GIAY]
approve_bus.py poller-status --campaign <đường dẫn>
```

⚠️ **`getUpdates` chỉ cho MỘT người đọc trên mỗi bot token.** Script này phải là tiến trình
duy nhất poll con bot đó.

Telegram báo xung đột này **to và rõ** — đo được 10/09/2026:
`Conflict: terminated by other getUpdates request; make sure that only one bot instance is
running`. Yêu cầu MỚI giết yêu cầu CŨ, nên hai poller đạp nhau liên tục và **cả hai cùng
hỏng ồn ào**. (Bản đầu của tài liệu này viết là "im lặng" — đó là suy đoán chưa đo, và
phép đo bác bỏ. Giữ ghi chú vì nó đổi cách phòng: chỉ cần ĐỌC LỖI, không cần dựng cổng
phát hiện ngầm.)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LIB))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_queue as WQ  # noqa: E402
import md_io  # noqa: E402
import event_log as EV  # noqa: E402
import telegram_io  # noqa: E402
import approval_gate as AG  # noqa: E402

# File này là MẶT TIỀN Telegram, không phải kho cổng. Mọi phép ghi cổng nằm ở
# `approval_gate.py` và mặt tiền trong phiên gọi vào đúng chỗ đó. Tách 12/09/2026 vì trước
# đó Telegram là con đường DUY NHẤT ghi được `g1`/`g3` — tức là nó không phải tuỳ chọn.
# Re-export để lời gọi cũ và test cũ không gãy; nơi định nghĩa thật là `approval_gate`.
waiting_at = AG.waiting_at
read_feedback = AG.read_feedback
FEEDBACK_FILE = AG.FEEDBACK_FILE
_doc_bang = AG.read_content_table
_da_viet_bai = AG.post_has_content
_vi_sao_chua_duoc_hoi = AG.why_not_ready
_ghi_phan_hoi = AG.write_feedback

TOKEN_TTL_HOURS = 48                      # token sống bao lâu
DEFAULT_BATCH = 10
STATE_FILE = "tg-approve.json"

# `content_id` chặt: 1–6 chữ, gạch, 3 số — khớp mọi `id_prefix` mà `new_campaign.py` cho
# phép (một ký tự cũng hợp lệ). Chặt vừa đủ để chữ từ tin nhắn không tự do đi tiếp; phần
# bảo vệ thật nằm ở chỗ `content_id` còn phải CÓ THẬT trong bảng Content.
RE_CID = re.compile(r"^[A-Z]{1,6}-\d{3}$")
RE_REPLY = re.compile(r"^\s*(duyet|duyệt|tu choi|từ chối)\s+([A-Za-z]{1,6}-\d{3})\s*(.*)$",
                        re.IGNORECASE)
RE_CALLBACK = re.compile(r"^(ok|no):([0-9a-f]{16})$")
# Lệnh TRẦN, không kèm mã bài. CHỈ dùng khi người TRẢ LỜI vào tin của một bài — lúc đó
# ngữ cảnh đã nói rõ bài nào, bắt gõ lại mã là thừa. Ngoài ngữ cảnh đó thì vô nghĩa và
# nguy hiểm: "duyet" trống không biết duyệt cái gì.
RE_BARE_COMMAND = re.compile(r"^\s*(duyet|duyệt|tu choi|từ chối)\s*(.*)$", re.IGNORECASE)
# Phần "lý do" đi kèm lệnh duyệt: CHỈ chữ, số, khoảng trắng và dấu câu hiền. Không có
# lệnh nào bị chạy từ chuỗi này (nó chỉ đi vào argv của register_publish, không qua shell)
# — nhưng vẫn chặn CHẶT, vì hai lẽ: (1) tin nhắn mang ký tự shell gần như chắc chắn không
# phải ý duyệt thật, từ chối thì người gõ lại là xong; (2) nó chặn sẵn cả lớp sai của
# tương lai, khi ai đó đem ghi chú này đi nối chuỗi vào một chỗ khác.
RE_REASON = re.compile(r"^[\w\s.,:!?\-–—/']*$", re.UNICODE)


def loi(m: str) -> None:
    sys.stderr.write(f"approve_bus: {m}\n")


# ── Trạng thái riêng của Telegram ───────────────────────────────────────────

def _state_path(campaign: Path) -> Path:
    return campaign / "logs" / STATE_FILE


def _read_state(campaign: Path) -> dict:
    p = _state_path(campaign)
    if not p.is_file():
        return {"offset": None, "pending": {}}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Hỏng file trạng thái KHÔNG được làm kẹt cổng duyệt. Tệ nhất là gửi lại tin.
        loi(f"{p} hỏng — bỏ qua, coi như chưa có token nào chờ.")
        return {"offset": None, "pending": {}}
    d.setdefault("offset", None)
    d.setdefault("pending", {})
    return d


def _write_state(campaign: Path, d: dict) -> None:
    _state_path(campaign).parent.mkdir(parents=True, exist_ok=True)
    md_io.write_atomic(_state_path(campaign), json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def _message_of_post(campaign: Path, cid: str) -> int | None:
    """`message_id` của tin đã gửi cho bài này — để tra ngược khi người TRẢ LỜI vào nó."""
    return (_read_state(campaign).get("post_message") or {}).get(cid)


def _post_of_message(campaign: Path, message_id: int) -> str | None:
    for cid, mid in (_read_state(campaign).get("post_message") or {}).items():
        if mid == message_id:
            return cid
    return None


def _reconcile_state(campaign: Path, da_tieu: set[str], offset_moi: int | None) -> None:
    """Ghi state bằng cách HOÀ GIẢI với đĩa, không ghi đè bằng bản trong bộ nhớ.

    ĐÃ TRẢ GIÁ 10/09/2026 — lỗi làm MẤT CÚ BẤM CỦA NGƯỜI:
      1. `nhan` nạp state vào bộ nhớ rồi long-poll **50 giây**
      2. giữa lúc đó `gui` (tiến trình khác) thêm token mới và ghi file
      3. `nhan` xong chu kỳ, ghi đè bằng bản cũ trong bộ nhớ -> token mới BIẾN MẤT
      4. người bấm nút -> không thấy token -> "đã dùng rồi", KHÔNG ghi gì

    Cửa sổ tranh chấp đúng bằng thời gian long-poll, nên nó xảy ra MỌI LẦN gửi cổng trong
    lúc poller chạy — tức là luôn luôn. Chạy tay từng lệnh thì không đời nào thấy.

    Nên chỉ ghi ĐÚNG HAI THAY ĐỔI của lượt này lên bản MỚI NHẤT trên đĩa: xoá token đã
    tiêu, và tiến `offset`. Mọi thứ khác giữ nguyên như đĩa đang có.
    """
    tren_dia = _read_state(campaign)          # `tin_bai` do `gui` ghi — giữ nguyên, không đụng
    for t in da_tieu:
        tren_dia["pending"].pop(t, None)
    if offset_moi is not None:
        cu = tren_dia.get("offset")
        # `max`: tiến trình khác có thể đã đọc xa hơn ta. Lùi offset là xử lý lại update cũ.
        tren_dia["offset"] = max(cu, offset_moi) if isinstance(cu, int) else offset_moi
    _write_state(campaign, tren_dia)


# ── Bảng Content ────────────────────────────────────────────────────────────

def _excerpt(post: Path, so_chu: int = 600) -> str:
    """Mấy dòng đầu của phần blog — để người duyệt liếc trên điện thoại là nắm được bài.

    File đính kèm mới là bản đầy đủ; đoạn trích này chỉ để khỏi phải tải file mới biết bài
    nói gì. Cắt ở `so_chu` vì Telegram giới hạn caption 1.024 ký tự.
    """
    p = Path(post) / "content.md"
    if not p.is_file():
        return ""
    raw = p.read_text(encoding="utf-8")
    m = re.search(r"(?m)^##\s+post:blog_article\s*$", raw)
    than = raw[m.end():] if m else raw
    ke = re.search(r"(?m)^##\s+post:", than)
    if ke:
        than = than[:ke.start()]
    than = re.sub(r"(?m)^\s*>.*$", "", than)          # khối chỉ dẫn của khuôn
    than = re.sub(r"<!--.*?-->", "", than, flags=re.S)
    than = "\n".join(x for x in (d.strip() for d in than.splitlines()) if x)
    return than[:so_chu] + ("…" if len(than) > so_chu else "")


# ── Gửi ─────────────────────────────────────────────────────────────────────

def _gate_label(gate: str) -> str:
    return {"g1": "Cổng 1 — duyệt đề tài",
            "g2": "Cổng 2 — duyệt trước khi đăng",
            "g3": "Cổng 3 — duyệt BẢN THẬT trên web"}.get(gate, gate)


def send_gate(campaign: Path, gate: str, *, bot, batch: int | None = None,
             mode: str | None = None, now: datetime | None = None,
             cids: list[str] | None = None) -> dict:
    """`cids` = hỏi ĐÚNG những bài này. Không truyền = tự lấy các bài đang chờ cổng.

    Vì sao cần tham số đó: `campaign_step` vừa dựng đúng 3 bài thì phải hỏi đúng 3 bài ấy.
    Để hàm tự truy vấn thì nó hỏi cả 10 bài đang chờ, trong khi `autonomy: full` lại chỉ
    tự duyệt 3 — HAI CHẾ ĐỘ HÀNH XỬ KHÁC NHAU trên cùng một bước. UAT 10/09 bắt được.
    """
    campaign = Path(campaign)
    now = now or datetime.now().astimezone()
    fm, _, _, _ = _doc_bang(campaign)
    rt = fm.get("runtime") or {}
    mode = mode or rt.get("approval_mode") or "batch_gate"
    batch = batch if batch is not None else int(rt.get("approval_lo") or DEFAULT_BATCH)

    dang_cho = waiting_at(campaign, gate)
    if cids is not None:
        # Lọc theo danh sách người gọi đưa, NHƯNG vẫn phải nằm trong nhóm đang chờ cổng:
        # hỏi duyệt một bài đã qua cổng rồi là mời người bấm lại vào việc đã xong.
        chon = set(cids)
        ds = [d for d in dang_cho if d["content_id"] in chon]
    else:
        ds = dang_cho[:batch] if batch else []
    # CỔNG 2 nghĩa là "đọc bài rồi quyết" — bài chưa có chữ thì không có gì để đọc.
    #
    # Vì sao lọc Ở ĐÂY chứ không trong `waiting_at`: `waiting_at` là truy vấn BẢNG thuần, và
    # còn hai chỗ khác dựa vào nó (định tuyến trả lời per-post ở `_cong_cua_bai`, và báo
    # trạng thái). Đổi nghĩa của nó là đổi cả ba. Chỗ gây hại chỉ có một: gửi tin mời người
    # bấm duyệt. 11/09/2026 đã gửi thật một tin mời duyệt 5 bài, 3 bài còn nguyên khuôn.
    if gate == "g2":
        giu = []
        for d in ds:
            why = _vi_sao_chua_duoc_hoi(campaign, d)
            if why:
                loi(f"cổng 2: bỏ qua {d['content_id']} — {why}")
            else:
                giu.append(d)
        ds = giu

    if not ds:
        return {"send": 0, "reason": "không có bài nào chờ cổng này"}

    st = _read_state(campaign)
    deadline = (now + timedelta(hours=TOKEN_TTL_HOURS)).isoformat()
    ten_cd = fm.get("id") or campaign.name

    # CỔNG 2 phải GỬI KÈM BÀI. Cổng bắt người duyệt NỘI DUNG mà chỉ chở mã bài + tiêu đề
    # thì là mời họ gật đầu về thứ không nhìn thấy — con dấu cao su, không phải cổng.
    # (Đức hỏi đúng chỗ này 11/09/2026.)
    #
    # Cổng 1 thì KHÔNG gửi: duyệt đề tài là liếc một dòng, đính file vào chỉ làm phiền.
    if gate == "g2":
        for d in ds:
            post = Path(campaign) / (d.get("folder") or "").lstrip("./")
            try:
                mid = bot.gui_tai_lieu(
                    post / "content.md",
                    f"{d['content_id']} — {d['content_name']}\n\n"
                    f"↩️ Trả lời thẳng vào tin này để gửi nhận xét cho bài.\n\n"
                    f"{_excerpt(post)}")
                # NEO NHẬN XÉT VÀO FILE BÀI. Trước 11/09/2026 `tin_bai` chỉ được ghi ở
                # nhánh `per_post`, nên ở chế độ LÔ người trả lời vào tin thì
                # `_post_of_message` trả None và nhận xét RƠI VÀO HƯ KHÔNG, không một lời báo.
                #
                # Tin gộp không neo được: nó liệt kê 5 bài, trả lời vào đó thì biết bài nào?
                # File bài mới là chỗ neo đúng — mỗi bài đúng một file.
                st.setdefault("post_message", {})[d["content_id"]] = mid
            except Exception as e:                       # noqa: BLE001
                # Gửi file hỏng KHÔNG được giết cả lượt gửi cổng: người vẫn cần thấy tin
                # duyệt. Nhưng phải nói to, vì họ sắp duyệt mà chưa đọc được bài.
                loi(f"{d['content_id']}: không gửi được bài ({e})")
                _ack(bot.gui,
                          f"⚠️ {d['content_id']}: không gửi được file bài. "
                          f"Mở tay: {post / 'content.md'}")

    def _issue_token(cids):
        tok = secrets.token_hex(8)         # 16 ký tự hex -> "ok:<16>" = 19 byte, dưới cap 64
        st["pending"][tok] = {"gate": gate, "content_ids": cids, "campaign": ten_cd,
                          "expires_at": deadline, "created_at": now.isoformat()}
        return tok

    gui = 0
    if mode == "per_post":
        for d in ds:
            tok = _issue_token([d["content_id"]])
            mid = bot.gui_kem_nut(
                f"{_gate_label(gate)} · {ten_cd}\n\n{d['content_id']} — {d['content_name']}\n"
                f"lịch: {d.get('schedule', '')}\n\n"
                f"Trả lời thẳng vào tin này để gửi nhận xét.",
                [[("✅ Duyệt", f"ok:{tok}"), ("❌ Từ chối", f"no:{tok}")]])
            # Nhớ tin nào thuộc bài nào — để khi người TRẢ LỜI vào nó, ta biết nhận xét đó
            # dành cho bài gì mà không bắt họ gõ lại mã bài.
            st.setdefault("post_message", {})[d["content_id"]] = mid
            gui += 1
    else:
        cids = [d["content_id"] for d in ds]
        tok = _issue_token(cids)
        # CỔNG 3 phải chở LINK BẢN THẬT. Cổng này nghĩa là "mở link, xem bằng mắt" — gửi
        # mỗi mã bài thì người duyệt không có gì để mở, và nó lại thành con dấu cao su y
        # như Cổng 2 từng bị ngày 11/09/2026.
        if gate == "g3":
            than = "\n".join(
                f"· {d['content_id']} — {d['content_name']}\n  {(d.get('web') or '').strip()}"
                for d in ds)
        else:
            than = "\n".join(f"· {d['content_id']} — {d['content_name']}" for d in ds)
        bot.gui_kem_nut(
            f"{_gate_label(gate)} · {ten_cd}\n{len(ds)} bài đang chờ:\n\n{than}\n\n"
            f"Trả lời `duyet {ds[0]['content_id']}` để duyệt lẻ từng bài.",
            [[("✅ Duyệt cả lô", f"ok:{tok}"), ("❌ Từ chối cả lô", f"no:{tok}")]])
        gui = 1

    _write_state(campaign, st)
    return {"send": gui, "count": len(ds), "mode": mode, "gate": gate}


# ── Nhận ────────────────────────────────────────────────────────────────────

def _ack(ham, *doi_so) -> None:
    """Gọi một bước PHỤ (ack / sửa tin) và NUỐT lỗi của nó.

    `answerCallbackQuery` chỉ để Telegram tắt vòng xoay trên nút — nó là mỹ quan, không
    phải việc. Telegram huỷ query đó sau ít phút, nên poll thưa là nó CHẮC CHẮN hỏng.

    ĐÃ TRẢ GIÁ 10/09/2026, đúng lượt đầu tiên có người bấm thật: lỗi ack ném ra ngoài làm
    chết cả lượt `nhan` SAU KHI đã ghi duyệt, và kéo theo `_write_state` không chạy — nên
    `offset` với token đã tiêu vẫn nguyên trên đĩa và lượt sau xử lý LẠI đúng update đó.
    Một bước phụ không bao giờ được giết lượt đã làm xong việc chính.
    """
    try:
        ham(*doi_so)
    except Exception as e:                 # noqa: BLE001 — nuốt CÓ CHỦ ĐÍCH, có ghi log
        loi(f"báo nhận Telegram hỏng (bỏ qua, việc chính đã xong) — {e}")


def _purge_expired(st: dict, now: datetime) -> None:
    for tok, y in list(st["pending"].items()):
        try:
            if datetime.fromisoformat(y["expires_at"]) < now:
                del st["pending"][tok]
        except (ValueError, KeyError):
            del st["pending"][tok]


def _apply(campaign: Path, gate: str, cids: list[str], *, by: str, note: str,
             now: datetime, via: str = "Telegram") -> list[str]:
    """Đường ghi cổng của MẶT TIỀN TELEGRAM — mỏng, chỉ uỷ quyền cho kho cổng.

    Giữ lại hàm này thay vì gọi thẳng `CD.open_gate` vì nó là ĐƯỜNG NỐI có ý nghĩa riêng:
    token chỉ được tiêu khi nó chạy xong (xem `_handle_one`), nên test bơm lỗi vào đúng
    đây để chứng minh cú bấm không rơi. Bỏ nó đi là mất chỗ bơm lỗi.
    """
    return AG.open_gate(campaign, gate, cids, by=by, quote=note,
                      via=via, now=now)


def _handle_one(u: dict, *, campaign: Path, st: dict, result: dict, bot,
               now: datetime) -> None:
    """Xử lý ĐÚNG MỘT update. Ném lỗi ở đây chỉ làm rơi update này, không rơi lô."""

    # ── Bấm nút ─────────────────────────────────────────────────────────
    if "callback_query" in u:
        cq = u["callback_query"]
        chat = (cq.get("message") or {}).get("chat", {}).get("id")
        m = RE_CALLBACK.match(str(cq.get("data") or ""))
        if not bot.duoc_phep(chat):
            loi(f"chat lạ {chat} bấm nút — bỏ qua.")
            result["bo_qua"] += 1
            return
        if not m:
            result["bo_qua"] += 1
            return
        hanh_dong, tok = m.group(1), m.group(2)
        y = st["pending"].pop(tok, None)      # POP khỏi bản trong bộ nhớ
        if y is None:
            _ack(bot.tra_loi_nut, cq["id"], "Nút này đã dùng rồi hoặc đã quá hạn.")
            result["bo_qua"] += 1
            return
        cids = y["content_ids"]
        if hanh_dong == "ok":
            # TIÊU token chỉ khi việc ĐÃ XONG.
            #
            # Đánh dấu tiêu TRƯỚC rồi mới ghi cổng là: ghi hỏng -> `except` nuốt lỗi ->
            # token vẫn mất -> CÚ BẤM RƠI VĨNH VIỄN, và người bấm lại chỉ nhận "đã dùng
            # rồi". Người dùng không có đường nào để tự cứu.
            #
            # Đây là chỗ ta thay cho "hàng đợi bền" của OpenClaw: rủi ro thật hẹp hơn kiến
            # trúc của họ nhiều, nên vá đúng chỗ hẹp đó thay vì nhập cả một tầng hàng đợi.
            done = _apply(campaign, y["gate"], cids, by="Đức (Telegram)",
                            note="duyệt qua Telegram", now=now)
            result.setdefault("_da_tieu", set()).add(tok)
            result["duyet"] += done
            for c in done:
                # Sổ sự kiện do `CD.open_gate` ghi — một chỗ cho MỌI mặt tiền. Ở đây chỉ còn
                # việc riêng của Telegram: xếp việc cho thợ chạy nền. Agent trong phiên
                # KHÔNG xếp việc vì nó chạy bước kế tiếp ngay.
                WQ.add(campaign, "next", post=c, source=f"{y['gate']}_approved")
            _ack(bot.tra_loi_nut, cq["id"], f"Đã duyệt {len(done)} bài.")
            _ack(bot.sua_tin, cq["message"]["message_id"],
                        f"✅ Đã duyệt {len(done)} bài: {', '.join(done) or '(không có)'}")
        else:
            result.setdefault("_da_tieu", set()).add(tok)   # từ chối cũng là đã xử lý xong
            result["reject"] += cids
            AG.reject(campaign, y["gate"], cids, by="Đức (Telegram)",
                       quote="từ chối bằng nút — không kèm lý do", via="nút")
            _ack(bot.tra_loi_nut, cq["id"], "Đã từ chối.")
            _ack(bot.sua_tin, cq["message"]["message_id"],
                        f"❌ Đã từ chối: {', '.join(cids)}")
        result["xu_ly"] += 1
        return

    # ── Trả lời bằng chữ ────────────────────────────────────────────────
    msg = u.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat = (msg.get("chat") or {}).get("id")
    if not text:
        return
    if not bot.duoc_phep(chat):
        loi(f"chat lạ {chat} nhắn tin — bỏ qua.")
        result["bo_qua"] += 1
        return
    # TRẢ LỜI vào tin của một bài = PHẢN HỒI, không phải lệnh duyệt.
    #
    # Nhánh này đặt TRƯỚC nhánh lệnh có chủ đích: nhận xét tự do gần như chắc chắn không
    # khớp mẫu `duyet <ID>`, mà rơi xuống dưới thì nó thành "bỏ qua" và LỜI CỦA NGƯỜI biến
    # mất không dấu vết.
    rep = (msg.get("reply_to_message") or {}).get("message_id")
    if rep:
        cid = _post_of_message(campaign, rep)
        if cid:
            # Trả lời vào bài rồi gõ "duyet"/"từ chối" là Ý QUYẾT, không phải lời góp ý —
            # và không bắt gõ lại mã bài, vì đang trả lời vào đúng bài đó rồi.
            #
            # Không có nhánh này thì mọi câu trả lời đều thành nhận xét: người gõ "duyet",
            # tưởng đã duyệt, cổng vẫn đóng, bài nằm im. Hỏng CÂM.
            ml = RE_BARE_COMMAND.match(text)
            if ml:
                return _execute_command(campaign, cid, ml.group(1), (ml.group(2) or "").strip(),
                                      bot=bot, result=result)
            _ghi_phan_hoi(campaign, cid, text)
            EV.write(campaign, "feedback", post=cid, by="Đức (Telegram)", text=text[:300])
            WQ.add(campaign, "next", post=cid, source="feedback")
            result.setdefault("feedback", []).append(cid)
            result["xu_ly"] += 1
            # Trước 12/09 câu này HỨA SUÔNG: nhận xét được ghi nhưng không gì chạy bước
            # viết lại. Nay đã có việc trong hàng chờ thật, nên câu này mới đúng.
            _ack(bot.gui, f"📝 {cid}: đã ghi nhận xét, bài vào hàng chờ viết lại.")
            return
        loi(f"trả lời vào tin {rep} nhưng không rõ của bài nào — bỏ qua.")
        result["bo_qua"] += 1
        return

    m = RE_REPLY.match(text)
    if not m:
        result["bo_qua"] += 1
        return
    # Chữ người gõ CHỈ đi tiếp sau khi khớp mẫu chặt và chuẩn hoá — không bao giờ
    # được đem đi chạy. `cid` phải qua RE_CID lần nữa sau khi viết hoa.
    cmd = m.group(1).lower()
    cid = m.group(2).upper()
    reason = m.group(3).strip()
    if not RE_CID.match(cid):
        result["bo_qua"] += 1
        return
    if not RE_REASON.match(reason):
        loi(f"lý do có ký tự lạ — bỏ qua cả tin nhắn: {text!r}")
        _ack(bot.gui, f"⚠️ Không hiểu tin nhắn. Gõ đúng dạng: `duyet {cid}` "
                f"hoặc `tu choi {cid} <lý do>` (chỉ chữ và dấu câu thường).")
        result["bo_qua"] += 1
        return
    _execute_command(campaign, cid, cmd, reason, bot=bot, result=result, now=now)


def _execute_command(campaign: Path, cid: str, cmd: str, reason: str, *, bot, result,
                   now: datetime | None = None) -> None:
    """Thi hành DUYỆT / TỪ CHỐI cho một bài. Dùng chung cho hai lối vào.

    Hai lối: gõ `duyet <mã>` như một tin thường, hoặc TRẢ LỜI vào tin của bài rồi gõ
    `duyet`. Tách ra đây để hai lối không trôi khỏi nhau — nếu chép logic duyệt lần thứ
    hai thì sớm muộn một lối ghi sổ còn lối kia không.
    """
    if not RE_REASON.match(reason or ""):
        loi(f"lý do có ký tự lạ — bỏ qua: {reason!r}")
        _ack(bot.gui, f"⚠️ {cid}: lý do có ký tự lạ, chưa ghi. Chỉ dùng chữ và dấu câu thường.")
        result["bo_qua"] += 1
        return
    gate = "g2" if (cid in {d["content_id"] for d in waiting_at(campaign, "g2")}) else "g1"
    if cmd.lower().startswith(("duy", "duyệt")):
        done = _apply(campaign, gate, [cid], by="Đức (Telegram)",
                        note=reason or "duyệt qua Telegram", now=now)
        result["duyet"] += done
        for c in done:
            # Xếp việc rồi ĐI TIẾP NGAY. Poller không được chạy bước nặng: nó đang giữ
            # khoá đọc Telegram, dừng lại 10 phút là cổng duyệt điếc 10 phút.
            WQ.add(campaign, "next", post=c, source=f"{gate}_approved")
        _ack(bot.gui, f"✅ {cid}: đã duyệt." if done else f"⚠️ {cid}: không ghi được (xem log).")
    else:
        result["reject"].append(cid)
        AG.reject(campaign, gate, [cid], by="Đức (Telegram)",
                   quote=reason or "từ chối qua Telegram — không kèm lý do", via="chữ")
        if reason:
            # Có lý do thì đó là chỉ dẫn sửa -> đưa vào vòng viết lại.
            WQ.add(campaign, "next", post=cid, source=f"{gate}_rejected")
        _ack(bot.gui, f"❌ {cid}: đã ghi từ chối. {reason}")
    result["xu_ly"] += 1

def receive(campaign: Path, *, bot, now: datetime | None = None) -> dict:
    campaign = Path(campaign)
    now = now or datetime.now().astimezone()
    st = _read_state(campaign)
    _purge_expired(st, now)

    # Long-poll: chặn tới ~50s chờ update thay vì hỏi-rồi-về-liền. Đây là thứ biến
    # "poll mỗi 5 phút" thành "gần như tức thì" mà không cần service thường trú.
    ds = bot.lay_cap_nhat(offset=st.get("offset"),
                          timeout=telegram_io.LONG_POLL_MAX)
    result = {"xu_ly": 0, "duyet": [], "reject": [], "bo_qua": 0}
    lon_nhat = None

    # Mỗi update một try RIÊNG: một cú bấm rác không được làm rơi những cú bấm hợp lệ
    # phía sau nó trong cùng lô.
    #
    # Và `_write_state` nằm trong `finally`: không lưu thì lượt sau xử lý LẠI update cũ và
    # token đã tiêu vẫn còn hiệu lực trên đĩa. Đã trả giá 10/09/2026 — một lỗi ack cosmetic
    # ném ra ngoài đúng SAU KHI đã ghi duyệt, kéo theo cả trạng thái poller không được lưu.
    try:
        for u in ds:
            lon_nhat = max(lon_nhat or 0, int(u.get("update_id", 0)))
            try:
                _handle_one(u, campaign=campaign, st=st, result=result, bot=bot, now=now)
            except Exception as e:  # noqa: BLE001
                loi(f"update {u.get('update_id')} hỏng, bỏ qua — {e}")
                result["bo_qua"] += 1
    finally:
        # HOÀ GIẢI với đĩa thay vì ghi đè: giữa lúc ta long-poll 50 giây, `gui` ở tiến
        # trình khác có thể đã thêm token. Ghi đè bằng bản trong bộ nhớ là xoá mất nó,
        # và cú bấm tương ứng của người sẽ rơi.
        _reconcile_state(campaign, result.pop("_da_tieu", set()),
                        lon_nhat + 1 if lon_nhat is not None else None)
    return result


HEARTBEAT_FILE = "tg-poll-alive.json"
# Bao lâu không có lượt `getUpdates` THÀNH CÔNG thì coi là poller đã chết câm.
# 3 chu kỳ 50s + dư — ngắn hơn thì báo động giả mỗi lần mạng chớp.
HEARTBEAT_STALE_SECONDS = 180


def _log_line(campaign: Path, m: str) -> None:
    """Một dòng vào `tg-poller-<ngày>.log`, ghi NGAY chứ không đợi tiến trình thoát.

    Vì sao cần: poller cố ý không đi qua `notify-run.ps1` (chạy liên tục, báo mỗi lượt là
    spam), nên file log là ĐƯỜNG DUY NHẤT để biết nó sống thế nào. Mà `--follow` chỉ in
    kết quả sau 55 phút, và stderr của Python bị block-buffer khi qua pipe của PowerShell
    — nên trong 55 phút đó không có gì để đọc. Đã mù hai lần vì đúng chỗ này 10/09/2026.
    """
    try:
        p = campaign / "logs" / f"tg-poller-{datetime.now().strftime('%Y-%m-%d')}.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')}  {m}\n")
    except OSError as e:                   # ghi log hỏng không được giết poller
        loi(f"không ghi được log ({e})")


def _write_heartbeat(campaign: Path, chu_ky: int) -> None:
    """Nhịp sống đo bằng chiều VÀO, không phải chiều RA.

    Bài học đắt nhất rút từ OpenClaw 2026.5.12: trước bản đó họ tính lời gọi API **đi ra**
    (gửi tin) là dấu hiệu "bot còn sống" — nên chiều VÀO chết mà không ai biết. Đúng hình
    dạng đó ở đây: `send_gate` vẫn gửi tin xin duyệt đều đặn trong khi `nhan` đã ngừng nhận,
    và mọi thứ nhìn vẫn bình thường cho tới lúc có người thắc mắc sao bấm không ăn.

    Nên chỉ ghi nhịp sau một lượt `getUpdates` THÀNH CÔNG. Gửi được tin KHÔNG tính.
    """
    md_io.write_atomic(campaign / "logs" / HEARTBEAT_FILE, json.dumps({
        "luot_vao_cuoi": datetime.now().astimezone().isoformat(),
        "chu_ky": chu_ky,
    }, ensure_ascii=False, indent=2) + "\n")


def _read_heartbeat(campaign: Path) -> dict:
    p = campaign / "logs" / HEARTBEAT_FILE
    if not p.is_file():
        return {"co_nhip": False, "tuoi_giay": None, "song": False}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        tuoi = (datetime.now().astimezone()
                - datetime.fromisoformat(d["luot_vao_cuoi"])).total_seconds()
    except (ValueError, KeyError):
        return {"co_nhip": False, "tuoi_giay": None, "song": False}
    return {"co_nhip": True, "tuoi_giay": round(tuoi),
            "song": tuoi <= HEARTBEAT_STALE_SECONDS, "chu_ky": d.get("chu_ky")}


LOCK_FILE = "tg-poller.lock"
# Lock coi như CHẾT nếu chủ nó không gia hạn trong ngần này. 3 chu kỳ long-poll 50s + dư.
# Ngắn hơn thì một chu kỳ chậm bị cướp lock; dài hơn thì poller chết làm kẹt cổng lâu.
LOCK_STALE = 180


def _lock_path(campaign: Path) -> Path:
    return campaign / "logs" / LOCK_FILE


def _read_lock(campaign: Path) -> dict | None:
    p = _lock_path(campaign)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # File lock hỏng KHÔNG được biến thành cổng chặn vĩnh viễn. Coi như không có.
        loi(f"{p} hỏng — coi như chưa ai giữ lock.")
        return None


def acquire_lock(campaign: Path, *, now: datetime | None = None) -> dict | None:
    """Giành quyền làm poller DUY NHẤT. Trả về thông tin lock, hoặc None nếu có người giữ.

    ## Vì sao phải TỰ cưỡng chế, không phó thác Task Scheduler

    `MultipleInstances = IgnoreNew` chỉ chặn khi Windows còn THẤY instance cũ. Instance chết
    sớm là lượt sau vào ngay — và ngày 10/09/2026 đã thành nhiều poller chồng nhau ghi đè
    trạng thái của nhau: `g1` ghi được nhưng `offset` và token bị tiến trình khác xoá mất.
    Task Scheduler không biết gì về `getUpdates`, cũng không thấy instance đang treo.

    ## Vì sao phép thử "còn sống" dùng NHỊP chứ không dùng PID

    Windows **tái dùng PID**. Một PID còn sống không chứng minh được đó là poller của ta —
    có thể là tiến trình khác vừa nhận đúng số đó. Kiểm cả thời điểm khởi động thì phải gọi
    `GetProcessTimes` qua ctypes, thêm một tầng phụ thuộc hệ điều hành cho một việc nhỏ.

    Nhịp thì không giả được: **chỉ chính poller đang chạy mới gia hạn được**. PID trong file
    chỉ để người đọc log biết mà tìm, không dùng làm phép thử.
    """
    now = now or datetime.now().astimezone()
    cu = _read_lock(campaign)
    if cu:
        try:
            tuoi = (now - datetime.fromisoformat(cu["nhip"])).total_seconds()
        except (ValueError, KeyError):
            tuoi = LOCK_STALE + 1        # lock méo mó -> coi như chết
        if tuoi <= LOCK_STALE:
            return None                    # có người giữ và còn sống

    # Ghi rồi ĐỌC LẠI để xác nhận mình thắng. Hai tiến trình khởi động cùng lúc thì kẻ ghi
    # sau thắng, và kẻ ghi trước đọc lại thấy không phải mình -> tự rút. Không hoàn hảo như
    # lock của HĐH, nhưng đủ cho cửa sổ vài mili-giây và không thêm phụ thuộc nào.
    ta = {"id": secrets.token_hex(8), "pid": os.getpid(),
          "bat_dau": now.isoformat(), "nhip": now.isoformat()}
    _lock_path(campaign).parent.mkdir(parents=True, exist_ok=True)
    md_io.write_atomic(_lock_path(campaign), json.dumps(ta, ensure_ascii=False, indent=2) + "\n")
    lai = _read_lock(campaign)
    return ta if lai and lai.get("id") == ta["id"] else None


def renew_lock(campaign: Path, chu_ky: int, *, now: datetime | None = None) -> None:
    d = _read_lock(campaign)
    if not d:
        return
    d["nhip"] = (now or datetime.now().astimezone()).isoformat()
    d["chu_ky"] = chu_ky
    md_io.write_atomic(_lock_path(campaign), json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def release_lock(campaign: Path) -> None:
    """Nhả trong `finally`. Không nhả được thì lock tự hết hạn sau LOCK_STALE."""
    try:
        _lock_path(campaign).unlink(missing_ok=True)
    except OSError as e:
        loi(f"không nhả được lock ({e}) — sẽ tự hết hạn sau {LOCK_STALE}s.")


def warn_two_pollers(campaign: Path) -> list[str]:
    """Cảnh báo TO nếu có chiến dịch khác trong trạm cũng đang giữ trạng thái poller.

    `getUpdates` chỉ cho MỘT người đọc trên mỗi bot token. Yêu cầu MỚI giết yêu cầu CŨ, nên
    hai poller sẽ đạp nhau liên tục và cả hai cùng hỏng — nhưng hỏng ỒN ÀO, không im lặng:
    Telegram trả thẳng `Conflict: terminated by other getUpdates request` (đo 10/09/2026).
    Hàm này cảnh báo TRƯỚC để khỏi phải đi dò từ thông điệp lỗi đó.

    Đây mới là CẢNH BÁO chứ chưa phải cổng chặn: trạng thái đang gắn theo chiến dịch, nên
    hai chiến dịch cùng muốn duyệt qua Telegram là một hạn chế THẬT của thiết kế hiện tại.
    Cách sửa đúng khi tới lúc: một poller cho CẢ TRẠM, định tuyến update theo token — chứ
    không phải mỗi chiến dịch một poller. Ghi ở đây để lúc đó không phải đi dò lại.
    """
    khac = []
    try:
        station = campaign.parent.parent            # <trạm>/<kênh>/<chiến dịch>
        for p in station.glob("*/*/logs/" + STATE_FILE):
            if p.parent.parent.resolve() != campaign.resolve():
                khac.append(p.parent.parent.name)
    except OSError:
        return []
    if khac:
        loi("⚠️ CÓ THỂ ĐANG CHẠY HAI POLLER. Chiến dịch khác cũng có trạng thái duyệt: "
            + ", ".join(khac) + ".\n"
            "  `getUpdates` chỉ cho MỘT người đọc trên mỗi bot token — hai poller sẽ ăn "
            "trộm update của nhau, IM LẶNG.\n"
            "  Tắt bớt một cái, hoặc tách bot riêng cho chiến dịch kia.")
    return khac


def receive_loop(campaign: Path, *, bot, seconds: int,
                  ngu=time.sleep, dong_ho=time.monotonic) -> dict:
    """Long-poll LẶP trong `giay` giây rồi thoát.

    Vì sao lặp thay vì xin timeout to hơn: Telegram chặn cứng ở ~50s (đo 10/09/2026), nên
    một lượt gọi chỉ phủ được ngần ấy. Muốn phủ liên tục thì phải nối nhiều lượt.

    Vì sao THOÁT chứ không chạy mãi: tiến trình sống mãi là thứ phải trông, và chết câm thì
    kẹt cổng duyệt. Thoát rồi để Task Scheduler dựng lại là tự lành — cùng lý do
    `notify-run.ps1` bọc từng lượt chạy chứ không dựng service.
    """
    # LOCK TRƯỚC MỌI THỨ. Task Scheduler bắn mỗi phút; nếu đã có poller sống thì lượt này
    # THOÁT ÊM — đó là đường chạy BÌNH THƯỜNG, không phải lỗi, nên không log ồn.
    if acquire_lock(campaign) is None:
        return {"chu_ky": 0, "xu_ly": 0, "duyet": [], "reject": [], "bo_qua": 0,
                "loi_lien_tiep": 0, "bo_qua_vi_lock": True}
    warn_two_pollers(campaign)
    end = dong_ho() + seconds
    tong = {"chu_ky": 0, "xu_ly": 0, "duyet": [], "reject": [], "bo_qua": 0, "loi_lien_tiep": 0}
    lien_tiep = 0
    try:
        while dong_ho() < end:
          tong["chu_ky"] += 1
          try:
              result = receive(campaign, bot=bot)
              lien_tiep = 0
              _write_heartbeat(campaign, tong["chu_ky"])       # CHỈ ghi sau lượt VÀO thành công
              renew_lock(campaign, tong["chu_ky"])    # giữ lock sống; đây là phép thử còn-sống
              # Ghi log THEO CHU KỲ, không chỉ lúc thoát. Chỉ ghi khi CÓ VIỆC — mỗi 50 giây
              # một dòng "không có gì" là 1.700 dòng/ngày, log thành rác không ai đọc.
              if result["xu_ly"] or result["bo_qua"]:
                  _log_line(campaign, f"chu kỳ {tong['chu_ky']}: xử lý={result['xu_ly']} "
                                     f"duyệt={','.join(result['duyet']) or '-'} "
                                     f"bỏ qua={result['bo_qua']}")
          except Exception as e:                    # noqa: BLE001
              lien_tiep += 1
              tong["loi_lien_tiep"] = max(tong["loi_lien_tiep"], lien_tiep)
              loi(f"chu kỳ {tong['chu_ky']} hỏng ({lien_tiep} lần liên tiếp) — {e}")
              _log_line(campaign, f"chu kỳ {tong['chu_ky']} HỎNG ({lien_tiep} liên tiếp): {e}")
              # Lùi dần: mạng chớp thì thử lại nhanh, hỏng thật thì đừng quay tít.
              ngu(min(2 ** lien_tiep, 60))
              if lien_tiep >= 5:
                  loi("5 chu kỳ hỏng liên tiếp — thoát để lượt sau dựng lại sạch.")
                  break
              continue
          for k in ("xu_ly", "bo_qua"):
              tong[k] += result[k]
          for k in ("duyet", "reject"):
              tong[k] += result[k]
    finally:
        # LUÔN nhả lock, kể cả khi lỗi. Không nhả được thì nó tự hết hạn sau LOCK_STALE
        # — nhưng để lock chết nằm lại là kẹt cổng duyệt tới lúc đó.
        release_lock(campaign)
    return tong


def poller_status(campaign: Path) -> dict:
    campaign = Path(campaign)
    st = _read_state(campaign)
    return {"cho_g1": [d["content_id"] for d in waiting_at(campaign, "g1")],
            "cho_g2": [d["content_id"] for d in waiting_at(campaign, "g2")],
            "token_dang_cho": len(st["pending"]), "offset": st.get("offset"),
            "nhip_vao": _read_heartbeat(campaign)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cổng duyệt hai chiều qua Telegram.")
    ap.add_argument("cmd", choices=["send", "receive", "poller-status"])
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--gate", choices=["g1", "g2", "g3"])
    ap.add_argument("--batch", type=int, default=None)
    ap.add_argument("--mode", choices=["per_post", "batch_gate"], default=None)
    ap.add_argument("--follow", type=int, default=0, metavar="GIAY",
                    help="long-poll LẶP trong N giây rồi thoát (Telegram chặn 50s/lượt)")
    a = ap.parse_args()

    campaign = Path(a.campaign).resolve()
    if not (campaign / "campaign.md").is_file():
        loi(f"không thấy {campaign / 'campaign.md'}")
        return 2

    if a.cmd == "poller-status":
        print(json.dumps(poller_status(campaign), ensure_ascii=False, indent=2))
        return 0

    bot = telegram_io.Bot()
    if a.cmd == "send":
        if not a.gate:
            loi("`gui` cần --gate g1|g2")
            return 2
        print(json.dumps(send_gate(campaign, a.gate, bot=bot, batch=a.batch, mode=a.mode),
                         ensure_ascii=False))
    else:
        result = (receive_loop(campaign, bot=bot, seconds=a.lien_tuc) if a.lien_tuc
              else receive(campaign, bot=bot))
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
