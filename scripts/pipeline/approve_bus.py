#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cổng duyệt hai chiều qua Telegram — MẶT TIỀN, không phải kho phê duyệt.

## Nó KHÔNG làm gì

Nó **không** giữ trạng thái duyệt của riêng nó. Cổng duyệt đã có chỗ ở từ trước:

| Cổng | Chỗ ở thật | Ai ghi |
|---|---|---|
| **g1** — duyệt đề tài | cột `g1` + `status` trong bảng Content của `campaign.md` | script này, qua `md_io` |
| **g2** — duyệt trước khi đăng | `publish.json → posts[].review` | `register_publish.py approve` |

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
approve_bus.py gui  --campaign <đường dẫn> --cong g1|g2 [--lo N] [--che-do per_post|batch_gate]
approve_bus.py nhan --campaign <đường dẫn>
approve_bus.py trang-thai --campaign <đường dẫn>
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
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LIB))
import md_io  # noqa: E402
import telegram_io  # noqa: E402

HAN_GIO = 48                      # token sống bao lâu
LO_MAC_DINH = 10
TEN_STATE = "tg-approve.json"

# `content_id` chặt: 1–6 chữ, gạch, 3 số — khớp mọi `id_prefix` mà `new_campaign.py` cho
# phép (một ký tự cũng hợp lệ). Chặt vừa đủ để chữ từ tin nhắn không tự do đi tiếp; phần
# bảo vệ thật nằm ở chỗ `content_id` còn phải CÓ THẬT trong bảng Content.
RE_CID = re.compile(r"^[A-Z]{1,6}-\d{3}$")
RE_TRA_LOI = re.compile(r"^\s*(duyet|duyệt|tu choi|từ chối)\s+([A-Za-z]{1,6}-\d{3})\s*(.*)$",
                        re.IGNORECASE)
RE_CALLBACK = re.compile(r"^(ok|no):([0-9a-f]{16})$")
# Phần "lý do" đi kèm lệnh duyệt: CHỈ chữ, số, khoảng trắng và dấu câu hiền. Không có
# lệnh nào bị chạy từ chuỗi này (nó chỉ đi vào argv của register_publish, không qua shell)
# — nhưng vẫn chặn CHẶT, vì hai lẽ: (1) tin nhắn mang ký tự shell gần như chắc chắn không
# phải ý duyệt thật, từ chối thì người gõ lại là xong; (2) nó chặn sẵn cả lớp sai của
# tương lai, khi ai đó đem ghi chú này đi nối chuỗi vào một chỗ khác.
RE_LY_DO = re.compile(r"^[\w\s.,:!?\-–—/']*$", re.UNICODE)


def loi(m: str) -> None:
    sys.stderr.write(f"approve_bus: {m}\n")


# ── Trạng thái riêng của Telegram ───────────────────────────────────────────

def _p_state(cam: Path) -> Path:
    return cam / "logs" / TEN_STATE


def _doc_state(cam: Path) -> dict:
    p = _p_state(cam)
    if not p.is_file():
        return {"offset": None, "cho": {}}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Hỏng file trạng thái KHÔNG được làm kẹt cổng duyệt. Tệ nhất là gửi lại tin.
        loi(f"{p} hỏng — bỏ qua, coi như chưa có token nào chờ.")
        return {"offset": None, "cho": {}}
    d.setdefault("offset", None)
    d.setdefault("cho", {})
    return d


def _ghi_state(cam: Path, d: dict) -> None:
    _p_state(cam).parent.mkdir(parents=True, exist_ok=True)
    md_io.ghi_nguyen_tu(_p_state(cam), json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def _hoa_giai_state(cam: Path, da_tieu: set[str], offset_moi: int | None) -> None:
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
    tren_dia = _doc_state(cam)
    for t in da_tieu:
        tren_dia["cho"].pop(t, None)
    if offset_moi is not None:
        cu = tren_dia.get("offset")
        # `max`: tiến trình khác có thể đã đọc xa hơn ta. Lùi offset là xử lý lại update cũ.
        tren_dia["offset"] = max(cu, offset_moi) if isinstance(cu, int) else offset_moi
    _ghi_state(cam, tren_dia)


# ── Bảng Content ────────────────────────────────────────────────────────────

def _doc_bang(cam: Path):
    fm, than = md_io.read_fm(cam / "campaign.md")
    cot, dong = md_io.read_table(than, "CONTENT")
    return fm, than, cot, dong


def cho_cong(cam: Path, cong: str) -> list[dict]:
    """Bài đang chờ đúng cổng đó. g1: chưa có g1. g2: có g1, chưa có g2."""
    _, _, _, dong = _doc_bang(cam)
    if cong == "g1":
        return [d for d in dong if not (d.get("g1") or "").strip()]
    return [d for d in dong
            if (d.get("g1") or "").strip() and not (d.get("g2") or "").strip()]


def _ghi_g1(cam: Path, cids: list[str], ngay: str) -> list[str]:
    """Ghi cột g1 + status. IDEMPOTENT: bài đã có g1 thì bỏ qua, không ghi đè."""
    fm, than, _, dong = _doc_bang(cam)
    hien = {d["content_id"]: d for d in dong}
    xong = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        if (d.get("g1") or "").strip():
            continue                       # đã duyệt rồi, không ghi lại
        than = md_io.upsert_row(than, "CONTENT", "content_id",
                                {"content_id": cid, "g1": ngay, "status": "approved"},
                                chi_cap_nhat=True)
        xong.append(cid)
    if xong:
        md_io.write_fm(cam / "campaign.md", fm, than)
    return xong


def _ghi_g2(cam: Path, cids: list[str], boi: str, ghi_chu: str) -> list[str]:
    """Gọi ĐÚNG `register_publish approve` — giữ nguyên dấu vết duyệt đang có."""
    _, _, _, dong = _doc_bang(cam)
    hien = {d["content_id"]: d for d in dong}
    rp = Path(__file__).resolve().parent / "register_publish.py"
    xong = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        thu_muc = (d.get("folder") or "").strip().lstrip("./")
        bai = cam / thu_muc
        if not bai.is_dir():
            loi(f"{cid}: không thấy thư mục bài {bai} — bỏ qua.")
            continue
        r = subprocess.run(
            [sys.executable, str(rp), str(bai), "approve", "--by", boi, "--note", ghi_chu],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            loi(f"{cid}: register_publish approve thất bại — {r.stdout}{r.stderr}")
            continue
        xong.append(cid)
    return xong


# ── Gửi ─────────────────────────────────────────────────────────────────────

def _nhan_cong(cong: str) -> str:
    return "Cổng 1 — duyệt đề tài" if cong == "g1" else "Cổng 2 — duyệt trước khi đăng"


def gui_cong(cam: Path, cong: str, *, bot, lo: int | None = None,
             che_do: str | None = None, bay_gio: datetime | None = None,
             cids: list[str] | None = None) -> dict:
    """`cids` = hỏi ĐÚNG những bài này. Không truyền = tự lấy các bài đang chờ cổng.

    Vì sao cần tham số đó: `campaign_step` vừa dựng đúng 3 bài thì phải hỏi đúng 3 bài ấy.
    Để hàm tự truy vấn thì nó hỏi cả 10 bài đang chờ, trong khi `autonomy: full` lại chỉ
    tự duyệt 3 — HAI CHẾ ĐỘ HÀNH XỬ KHÁC NHAU trên cùng một bước. UAT 10/09 bắt được.
    """
    cam = Path(cam)
    bay_gio = bay_gio or datetime.now().astimezone()
    fm, _, _, _ = _doc_bang(cam)
    rt = fm.get("runtime") or {}
    che_do = che_do or rt.get("approval_mode") or "batch_gate"
    lo = lo if lo is not None else int(rt.get("approval_lo") or LO_MAC_DINH)

    dang_cho = cho_cong(cam, cong)
    if cids is not None:
        # Lọc theo danh sách người gọi đưa, NHƯNG vẫn phải nằm trong nhóm đang chờ cổng:
        # hỏi duyệt một bài đã qua cổng rồi là mời người bấm lại vào việc đã xong.
        chon = set(cids)
        ds = [d for d in dang_cho if d["content_id"] in chon]
    else:
        ds = dang_cho[:lo] if lo else []
    if not ds:
        return {"gui": 0, "ly_do": "không có bài nào chờ cổng này"}

    st = _doc_state(cam)
    han = (bay_gio + timedelta(hours=HAN_GIO)).isoformat()
    ten_cd = fm.get("id") or cam.name

    def _dat_token(cids):
        tok = secrets.token_hex(8)         # 16 ký tự hex -> "ok:<16>" = 19 byte, dưới cap 64
        st["cho"][tok] = {"cong": cong, "content_ids": cids, "campaign": ten_cd,
                          "het_han": han, "tao_luc": bay_gio.isoformat()}
        return tok

    gui = 0
    if che_do == "per_post":
        for d in ds:
            tok = _dat_token([d["content_id"]])
            bot.gui_kem_nut(
                f"{_nhan_cong(cong)} · {ten_cd}\n\n{d['content_id']} — {d['content_name']}\n"
                f"lịch: {d.get('schedule', '')}",
                [[("✅ Duyệt", f"ok:{tok}"), ("❌ Từ chối", f"no:{tok}")]])
            gui += 1
    else:
        cids = [d["content_id"] for d in ds]
        tok = _dat_token(cids)
        than = "\n".join(f"· {d['content_id']} — {d['content_name']}" for d in ds)
        bot.gui_kem_nut(
            f"{_nhan_cong(cong)} · {ten_cd}\n{len(ds)} bài đang chờ:\n\n{than}\n\n"
            f"Trả lời `duyet {ds[0]['content_id']}` để duyệt lẻ từng bài.",
            [[("✅ Duyệt cả lô", f"ok:{tok}"), ("❌ Từ chối cả lô", f"no:{tok}")]])
        gui = 1

    _ghi_state(cam, st)
    return {"gui": gui, "so_bai": len(ds), "che_do": che_do, "cong": cong}


# ── Nhận ────────────────────────────────────────────────────────────────────

def _bao_nhan(ham, *doi_so) -> None:
    """Gọi một bước PHỤ (ack / sửa tin) và NUỐT lỗi của nó.

    `answerCallbackQuery` chỉ để Telegram tắt vòng xoay trên nút — nó là mỹ quan, không
    phải việc. Telegram huỷ query đó sau ít phút, nên poll thưa là nó CHẮC CHẮN hỏng.

    ĐÃ TRẢ GIÁ 10/09/2026, đúng lượt đầu tiên có người bấm thật: lỗi ack ném ra ngoài làm
    chết cả lượt `nhan` SAU KHI đã ghi duyệt, và kéo theo `_ghi_state` không chạy — nên
    `offset` với token đã tiêu vẫn nguyên trên đĩa và lượt sau xử lý LẠI đúng update đó.
    Một bước phụ không bao giờ được giết lượt đã làm xong việc chính.
    """
    try:
        ham(*doi_so)
    except Exception as e:                 # noqa: BLE001 — nuốt CÓ CHỦ ĐÍCH, có ghi log
        loi(f"báo nhận Telegram hỏng (bỏ qua, việc chính đã xong) — {e}")


def _don_token_qua_han(st: dict, bay_gio: datetime) -> None:
    for tok, y in list(st["cho"].items()):
        try:
            if datetime.fromisoformat(y["het_han"]) < bay_gio:
                del st["cho"][tok]
        except (ValueError, KeyError):
            del st["cho"][tok]


def _ap_dung(cam: Path, cong: str, cids: list[str], *, boi: str, ghi_chu: str,
             bay_gio: datetime) -> list[str]:
    if cong == "g1":
        return _ghi_g1(cam, cids, bay_gio.date().isoformat())
    return _ghi_g2(cam, cids, boi, ghi_chu)




def _xu_ly_mot(u: dict, *, cam: Path, st: dict, kq: dict, bot,
               bay_gio: datetime) -> None:
    """Xử lý ĐÚNG MỘT update. Ném lỗi ở đây chỉ làm rơi update này, không rơi lô."""

    # ── Bấm nút ─────────────────────────────────────────────────────────
    if "callback_query" in u:
        cq = u["callback_query"]
        chat = (cq.get("message") or {}).get("chat", {}).get("id")
        m = RE_CALLBACK.match(str(cq.get("data") or ""))
        if not bot.duoc_phep(chat):
            loi(f"chat lạ {chat} bấm nút — bỏ qua.")
            kq["bo_qua"] += 1
            return
        if not m:
            kq["bo_qua"] += 1
            return
        hanh_dong, tok = m.group(1), m.group(2)
        y = st["cho"].pop(tok, None)      # POP: token là MỘT LẦN
        if y is not None:
            kq.setdefault("_da_tieu", set()).add(tok)   # để bước lưu hoà giải với đĩa
        if y is None:
            _bao_nhan(bot.tra_loi_nut, cq["id"], "Nút này đã dùng rồi hoặc đã quá hạn.")
            kq["bo_qua"] += 1
            return
        cids = y["content_ids"]
        if hanh_dong == "ok":
            xong = _ap_dung(cam, y["cong"], cids, boi="Đức (Telegram)",
                            ghi_chu="duyệt qua Telegram", bay_gio=bay_gio)
            kq["duyet"] += xong
            _bao_nhan(bot.tra_loi_nut, cq["id"], f"Đã duyệt {len(xong)} bài.")
            _bao_nhan(bot.sua_tin, cq["message"]["message_id"],
                        f"✅ Đã duyệt {len(xong)} bài: {', '.join(xong) or '(không có)'}")
        else:
            kq["tu_choi"] += cids
            _bao_nhan(bot.tra_loi_nut, cq["id"], "Đã từ chối.")
            _bao_nhan(bot.sua_tin, cq["message"]["message_id"],
                        f"❌ Đã từ chối: {', '.join(cids)}")
        kq["xu_ly"] += 1
        return

    # ── Trả lời bằng chữ ────────────────────────────────────────────────
    msg = u.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat = (msg.get("chat") or {}).get("id")
    if not text:
        return
    if not bot.duoc_phep(chat):
        loi(f"chat lạ {chat} nhắn tin — bỏ qua.")
        kq["bo_qua"] += 1
        return
    m = RE_TRA_LOI.match(text)
    if not m:
        kq["bo_qua"] += 1
        return
    # Chữ người gõ CHỈ đi tiếp sau khi khớp mẫu chặt và chuẩn hoá — không bao giờ
    # được đem đi chạy. `cid` phải qua RE_CID lần nữa sau khi viết hoa.
    lenh = m.group(1).lower()
    cid = m.group(2).upper()
    ly_do = m.group(3).strip()
    if not RE_CID.match(cid):
        kq["bo_qua"] += 1
        return
    if not RE_LY_DO.match(ly_do):
        loi(f"lý do có ký tự lạ — bỏ qua cả tin nhắn: {text!r}")
        _bao_nhan(bot.gui, f"⚠️ Không hiểu tin nhắn. Gõ đúng dạng: `duyet {cid}` "
                f"hoặc `tu choi {cid} <lý do>` (chỉ chữ và dấu câu thường).")
        kq["bo_qua"] += 1
        return
    cong = "g2" if (cid in {d["content_id"] for d in cho_cong(cam, "g2")}) else "g1"
    if lenh.startswith("duy"):
        xong = _ap_dung(cam, cong, [cid], boi="Đức (Telegram)",
                        ghi_chu=ly_do or "duyệt qua Telegram", bay_gio=bay_gio)
        kq["duyet"] += xong
        _bao_nhan(bot.gui, f"✅ {cid}: đã duyệt." if xong else f"⚠️ {cid}: không ghi được (xem log).")
    else:
        kq["tu_choi"].append(cid)
        _bao_nhan(bot.gui, f"❌ {cid}: đã ghi từ chối. {ly_do}")
    kq["xu_ly"] += 1

def nhan(cam: Path, *, bot, bay_gio: datetime | None = None) -> dict:
    cam = Path(cam)
    bay_gio = bay_gio or datetime.now().astimezone()
    st = _doc_state(cam)
    _don_token_qua_han(st, bay_gio)

    # Long-poll: chặn tới ~50s chờ update thay vì hỏi-rồi-về-liền. Đây là thứ biến
    # "poll mỗi 5 phút" thành "gần như tức thì" mà không cần service thường trú.
    ds = bot.lay_cap_nhat(offset=st.get("offset"),
                          timeout=telegram_io.LONG_POLL_MAX)
    kq = {"xu_ly": 0, "duyet": [], "tu_choi": [], "bo_qua": 0}
    lon_nhat = None

    # Mỗi update một try RIÊNG: một cú bấm rác không được làm rơi những cú bấm hợp lệ
    # phía sau nó trong cùng lô.
    #
    # Và `_ghi_state` nằm trong `finally`: không lưu thì lượt sau xử lý LẠI update cũ và
    # token đã tiêu vẫn còn hiệu lực trên đĩa. Đã trả giá 10/09/2026 — một lỗi ack cosmetic
    # ném ra ngoài đúng SAU KHI đã ghi duyệt, kéo theo cả trạng thái poller không được lưu.
    try:
        for u in ds:
            lon_nhat = max(lon_nhat or 0, int(u.get("update_id", 0)))
            try:
                _xu_ly_mot(u, cam=cam, st=st, kq=kq, bot=bot, bay_gio=bay_gio)
            except Exception as e:  # noqa: BLE001
                loi(f"update {u.get('update_id')} hỏng, bỏ qua — {e}")
                kq["bo_qua"] += 1
    finally:
        # HOÀ GIẢI với đĩa thay vì ghi đè: giữa lúc ta long-poll 50 giây, `gui` ở tiến
        # trình khác có thể đã thêm token. Ghi đè bằng bản trong bộ nhớ là xoá mất nó,
        # và cú bấm tương ứng của người sẽ rơi.
        _hoa_giai_state(cam, kq.pop("_da_tieu", set()),
                        lon_nhat + 1 if lon_nhat is not None else None)
    return kq


TEN_NHIP = "tg-poll-alive.json"
# Bao lâu không có lượt `getUpdates` THÀNH CÔNG thì coi là poller đã chết câm.
# 3 chu kỳ 50s + dư — ngắn hơn thì báo động giả mỗi lần mạng chớp.
NHIP_QUA_HAN_GIAY = 180


def _ghi_dong_log(cam: Path, m: str) -> None:
    """Một dòng vào `tg-poller-<ngày>.log`, ghi NGAY chứ không đợi tiến trình thoát.

    Vì sao cần: poller cố ý không đi qua `notify-run.ps1` (chạy liên tục, báo mỗi lượt là
    spam), nên file log là ĐƯỜNG DUY NHẤT để biết nó sống thế nào. Mà `--lien-tuc` chỉ in
    kết quả sau 55 phút, và stderr của Python bị block-buffer khi qua pipe của PowerShell
    — nên trong 55 phút đó không có gì để đọc. Đã mù hai lần vì đúng chỗ này 10/09/2026.
    """
    try:
        p = cam / "logs" / f"tg-poller-{datetime.now().strftime('%Y-%m-%d')}.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')}  {m}\n")
    except OSError as e:                   # ghi log hỏng không được giết poller
        loi(f"không ghi được log ({e})")


def _ghi_nhip(cam: Path, chu_ky: int) -> None:
    """Nhịp sống đo bằng chiều VÀO, không phải chiều RA.

    Bài học đắt nhất rút từ OpenClaw 2026.5.12: trước bản đó họ tính lời gọi API **đi ra**
    (gửi tin) là dấu hiệu "bot còn sống" — nên chiều VÀO chết mà không ai biết. Đúng hình
    dạng đó ở đây: `gui_cong` vẫn gửi tin xin duyệt đều đặn trong khi `nhan` đã ngừng nhận,
    và mọi thứ nhìn vẫn bình thường cho tới lúc có người thắc mắc sao bấm không ăn.

    Nên chỉ ghi nhịp sau một lượt `getUpdates` THÀNH CÔNG. Gửi được tin KHÔNG tính.
    """
    md_io.ghi_nguyen_tu(cam / "logs" / TEN_NHIP, json.dumps({
        "luot_vao_cuoi": datetime.now().astimezone().isoformat(),
        "chu_ky": chu_ky,
    }, ensure_ascii=False, indent=2) + "\n")


def _doc_nhip(cam: Path) -> dict:
    p = cam / "logs" / TEN_NHIP
    if not p.is_file():
        return {"co_nhip": False, "tuoi_giay": None, "song": False}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        tuoi = (datetime.now().astimezone()
                - datetime.fromisoformat(d["luot_vao_cuoi"])).total_seconds()
    except (ValueError, KeyError):
        return {"co_nhip": False, "tuoi_giay": None, "song": False}
    return {"co_nhip": True, "tuoi_giay": round(tuoi),
            "song": tuoi <= NHIP_QUA_HAN_GIAY, "chu_ky": d.get("chu_ky")}


LOCK_TEN = "tg-poller.lock"
# Lock coi như CHẾT nếu chủ nó không gia hạn trong ngần này. 3 chu kỳ long-poll 50s + dư.
# Ngắn hơn thì một chu kỳ chậm bị cướp lock; dài hơn thì poller chết làm kẹt cổng lâu.
LOCK_QUA_HAN = 180


def _p_lock(cam: Path) -> Path:
    return cam / "logs" / LOCK_TEN


def _doc_lock(cam: Path) -> dict | None:
    p = _p_lock(cam)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # File lock hỏng KHÔNG được biến thành cổng chặn vĩnh viễn. Coi như không có.
        loi(f"{p} hỏng — coi như chưa ai giữ lock.")
        return None


def gianh_lock(cam: Path, *, bay_gio: datetime | None = None) -> dict | None:
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
    bay_gio = bay_gio or datetime.now().astimezone()
    cu = _doc_lock(cam)
    if cu:
        try:
            tuoi = (bay_gio - datetime.fromisoformat(cu["nhip"])).total_seconds()
        except (ValueError, KeyError):
            tuoi = LOCK_QUA_HAN + 1        # lock méo mó -> coi như chết
        if tuoi <= LOCK_QUA_HAN:
            return None                    # có người giữ và còn sống

    # Ghi rồi ĐỌC LẠI để xác nhận mình thắng. Hai tiến trình khởi động cùng lúc thì kẻ ghi
    # sau thắng, và kẻ ghi trước đọc lại thấy không phải mình -> tự rút. Không hoàn hảo như
    # lock của HĐH, nhưng đủ cho cửa sổ vài mili-giây và không thêm phụ thuộc nào.
    ta = {"id": secrets.token_hex(8), "pid": os.getpid(),
          "bat_dau": bay_gio.isoformat(), "nhip": bay_gio.isoformat()}
    _p_lock(cam).parent.mkdir(parents=True, exist_ok=True)
    md_io.ghi_nguyen_tu(_p_lock(cam), json.dumps(ta, ensure_ascii=False, indent=2) + "\n")
    lai = _doc_lock(cam)
    return ta if lai and lai.get("id") == ta["id"] else None


def gia_han_lock(cam: Path, chu_ky: int, *, bay_gio: datetime | None = None) -> None:
    d = _doc_lock(cam)
    if not d:
        return
    d["nhip"] = (bay_gio or datetime.now().astimezone()).isoformat()
    d["chu_ky"] = chu_ky
    md_io.ghi_nguyen_tu(_p_lock(cam), json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def nha_lock(cam: Path) -> None:
    """Nhả trong `finally`. Không nhả được thì lock tự hết hạn sau LOCK_QUA_HAN."""
    try:
        _p_lock(cam).unlink(missing_ok=True)
    except OSError as e:
        loi(f"không nhả được lock ({e}) — sẽ tự hết hạn sau {LOCK_QUA_HAN}s.")


def canh_bao_hai_poller(cam: Path) -> list[str]:
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
        tram = cam.parent.parent            # <trạm>/<kênh>/<chiến dịch>
        for p in tram.glob("*/*/logs/" + TEN_STATE):
            if p.parent.parent.resolve() != cam.resolve():
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


def nhan_lien_tuc(cam: Path, *, bot, giay: int,
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
    if gianh_lock(cam) is None:
        return {"chu_ky": 0, "xu_ly": 0, "duyet": [], "tu_choi": [], "bo_qua": 0,
                "loi_lien_tiep": 0, "bo_qua_vi_lock": True}
    canh_bao_hai_poller(cam)
    het = dong_ho() + giay
    tong = {"chu_ky": 0, "xu_ly": 0, "duyet": [], "tu_choi": [], "bo_qua": 0, "loi_lien_tiep": 0}
    lien_tiep = 0
    try:
        while dong_ho() < het:
          tong["chu_ky"] += 1
          try:
              kq = nhan(cam, bot=bot)
              lien_tiep = 0
              _ghi_nhip(cam, tong["chu_ky"])       # CHỈ ghi sau lượt VÀO thành công
              gia_han_lock(cam, tong["chu_ky"])    # giữ lock sống; đây là phép thử còn-sống
              # Ghi log THEO CHU KỲ, không chỉ lúc thoát. Chỉ ghi khi CÓ VIỆC — mỗi 50 giây
              # một dòng "không có gì" là 1.700 dòng/ngày, log thành rác không ai đọc.
              if kq["xu_ly"] or kq["bo_qua"]:
                  _ghi_dong_log(cam, f"chu kỳ {tong['chu_ky']}: xử lý={kq['xu_ly']} "
                                     f"duyệt={','.join(kq['duyet']) or '-'} "
                                     f"bỏ qua={kq['bo_qua']}")
          except Exception as e:                    # noqa: BLE001
              lien_tiep += 1
              tong["loi_lien_tiep"] = max(tong["loi_lien_tiep"], lien_tiep)
              loi(f"chu kỳ {tong['chu_ky']} hỏng ({lien_tiep} lần liên tiếp) — {e}")
              _ghi_dong_log(cam, f"chu kỳ {tong['chu_ky']} HỎNG ({lien_tiep} liên tiếp): {e}")
              # Lùi dần: mạng chớp thì thử lại nhanh, hỏng thật thì đừng quay tít.
              ngu(min(2 ** lien_tiep, 60))
              if lien_tiep >= 5:
                  loi("5 chu kỳ hỏng liên tiếp — thoát để lượt sau dựng lại sạch.")
                  break
              continue
          for k in ("xu_ly", "bo_qua"):
              tong[k] += kq[k]
          for k in ("duyet", "tu_choi"):
              tong[k] += kq[k]
    finally:
        # LUÔN nhả lock, kể cả khi lỗi. Không nhả được thì nó tự hết hạn sau LOCK_QUA_HAN
        # — nhưng để lock chết nằm lại là kẹt cổng duyệt tới lúc đó.
        nha_lock(cam)
    return tong


def trang_thai(cam: Path) -> dict:
    cam = Path(cam)
    st = _doc_state(cam)
    return {"cho_g1": [d["content_id"] for d in cho_cong(cam, "g1")],
            "cho_g2": [d["content_id"] for d in cho_cong(cam, "g2")],
            "token_dang_cho": len(st["cho"]), "offset": st.get("offset"),
            "nhip_vao": _doc_nhip(cam)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cổng duyệt hai chiều qua Telegram.")
    ap.add_argument("lenh", choices=["gui", "nhan", "trang-thai"])
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--cong", choices=["g1", "g2"])
    ap.add_argument("--lo", type=int, default=None)
    ap.add_argument("--che-do", choices=["per_post", "batch_gate"], default=None)
    ap.add_argument("--lien-tuc", type=int, default=0, metavar="GIAY",
                    help="long-poll LẶP trong N giây rồi thoát (Telegram chặn 50s/lượt)")
    a = ap.parse_args()

    cam = Path(a.campaign).resolve()
    if not (cam / "campaign.md").is_file():
        loi(f"không thấy {cam / 'campaign.md'}")
        return 2

    if a.lenh == "trang-thai":
        print(json.dumps(trang_thai(cam), ensure_ascii=False, indent=2))
        return 0

    bot = telegram_io.Bot()
    if a.lenh == "gui":
        if not a.cong:
            loi("`gui` cần --cong g1|g2")
            return 2
        print(json.dumps(gui_cong(cam, a.cong, bot=bot, lo=a.lo, che_do=a.che_do),
                         ensure_ascii=False))
    else:
        kq = (nhan_lien_tuc(cam, bot=bot, giay=a.lien_tuc) if a.lien_tuc
              else nhan(cam, bot=bot))
        print(json.dumps(kq, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
