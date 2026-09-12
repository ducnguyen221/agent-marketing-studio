#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Thợ — nhặt MỘT việc khỏi hàng chờ, chạy bước tương ứng, báo kết quả.

## Vì sao thợ tách hẳn khỏi poller

Poller giữ khoá đọc Telegram. Cho nó chạy agent viết bài (~10 phút) thì cổng duyệt **điếc**
suốt 10 phút đó, nhịp tim đứng lại, lượt sau tưởng nó chết rồi cướp khoá — đúng vòng lặp đã
làm sập máy ngày 11/09/2026.

Poller ghi việc (vài mili giây), thợ làm việc (mười phút). Hai tiến trình, hai nhịp.

## ĐÚNG MỘT VIỆC MỖI LƯỢT CHẠY

Làm xong một việc là **thoát**, để Task Scheduler gọi lại. Không có vòng `while` nào ở đây.

Vì sao: `MultipleInstances = IgnoreNew` chỉ chặn khi Windows còn thấy instance cũ. Thợ chạy
10 phút thì 10 lượt gọi kế tiếp bị chặn — **đó chính là giới hạn một-agent-một-lúc**, và nó
đến từ hệ điều hành chứ không từ code ta tự viết. Duyệt cả lô 10 bài thì 10 việc xếp hàng,
không phải 10 agent cùng sống. Hôm 11/09 đúng chỗ này đã thành 335 tiến trình và 16,4 GB.

Hàng rỗng thì thoát **ngay và êm** — đó là đường chạy bình thường, không phải lỗi.

## Thợ KHÔNG bao giờ tự mở cổng duyệt

`pipeline_state.CAN_NGUOI` đánh dấu `cho-G1` và `cho-G2`. Gặp hai bước đó thợ **trả việc về và
dừng**. Agent tự duyệt bài của chính nó là mất sạch ý nghĩa của cổng.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LIB))
import post_content            # noqa: E402
import work_queue as HC          # noqa: E402
import md_io                   # noqa: E402
import event_log as SO        # noqa: E402
import pipeline_state as TT        # noqa: E402

# Bước nào chạy bằng lệnh nào. `sua_lai` cũng chạy `soan` — bước đó tự đọc `phan-hoi.md`.
LENH = {
    "soan": ["soan"],
    "cham-cong": ["__cham_cong__"],
    "sua-loi-cong": ["soan"],
    "dung-trang": ["dung-trang"],
    "phat-hanh": ["phat-hanh"],
}

TRAN_VIET_LAI = 3      # bài bị trả lại quá ngần này lần thì dừng, hỏi người


def loi(m: str) -> None:
    sys.stderr.write(f"worker: {m}\n")


def _so_lan_viet(cam: Path, cid: str, dong: dict) -> int:
    f = (dong.get("folder") or "").strip()
    if not f:
        return 0
    p = Path(cam) / f.lstrip("./") / ".viet-lan.json"
    if not p.is_file():
        return 0
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("so_lan") or 0)
    except (json.JSONDecodeError, ValueError):
        return 0


def _dong_cua_bai(cam: Path, cid: str) -> dict | None:
    _, than = md_io.read_fm(Path(cam) / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    for d in dong:
        if d.get("content_id") == cid:
            return d
    return None


def _chay_buoc(cam: Path, buoc: str, cid: str) -> tuple[bool, str]:
    """Gọi `campaign_step.py <buoc>`. Trả `(xong, thông điệp)`."""
    if buoc == "__cham_cong__":
        script = Path(__file__).resolve().parent / "blog_gates.py"
        d = _dong_cua_bai(cam, cid) or {}
        bai = Path(cam) / (d.get("folder") or "").lstrip("./")
        lenh = [sys.executable, str(script), str(bai)]
    else:
        script = Path(__file__).resolve().parent / "campaign_step.py"
        lenh = [sys.executable, str(script), str(cam), buoc]
        # GIỚI HẠN ĐÚNG MỘT BÀI. Việc trong hàng chờ là theo từng bài, còn bước vốn quét cả
        # chiến dịch. Thiếu cờ này thì một việc cho NEN-002 viết lại luôn NEN-001 và
        # NEN-003: kế toán số lần viết lại thành vô nghĩa, và lượt chạy kéo hàng giờ.
        # Đo thật 12/09/2026 — một việc chạy 27 phút vì ôm ba bài.
        if buoc in ("soan", "sua-loi-cong", "dung-trang", "phat-hanh") and cid:
            lenh += ["--bai", cid]

    r = subprocess.run(lenh, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    ra = ((r.stdout or "") + (r.stderr or "")).strip()
    return r.returncode == 0, ra[-600:]


def _da_ra_artefact(buoc: str, bai: Path) -> bool:
    """Bước này lẽ ra phải sinh ra cái gì — cái đó có chưa?

    MÃ THOÁT KHÁC 0 KHÔNG ĐỦ ĐỂ TÍNH LÀ HỎNG. Hai bước trong đường ống trả mã khác 0 cho
    một KẾT QUẢ hợp lệ, không phải cho sự cố:

      · `blog_gates.py` trả 1 khi kết luận ĐỎ — nhưng nó đã chấm xong 23 cổng và ghi
        `gates.json` tử tế.
      · `soan` trả khác 0 khi bài viết ra chưa qua cổng — nhưng bài ĐÃ ĐƯỢC VIẾT.

    Đọc mã thoát rồi kết luận "hỏng" thì đúng những bài cần đi tiếp lại bị chấm/viết lại ba
    lần rồi vứt vào `hong/`. Đo thật 12/09/2026: một lượt như thế đốt 27 phút agent rồi bị
    tính là thất bại.

    Repo đã có luật ngược lại — *"mã thoát 0 không đủ để tính là xong"* (bộ viết chạy êm mà
    file vẫn trống thì vẫn là hỏng). Cùng một nguyên tắc, hai chiều: **hỏi artefact, đừng
    hỏi mã thoát.**
    """
    if buoc == "cham-cong":
        return (bai / "gates.json").is_file()
    if buoc in ("soan", "sua-loi-cong"):
        return post_content.da_viet(bai)
    if buoc == "dung-trang":
        # Trang đã dựng ra file thì bước đã làm được việc. URL có ghi được vào bảng hay
        # không là chuyện của `web_publish`, và nó tự fail-closed ở đó.
        return (bai / "atlas" / "atlas.html").is_file()
    return False


def lam_mot_viec(cam: Path, *, bot=None, chay=_chay_buoc) -> dict:
    """Nhặt một việc và làm. `chay` tiêm được để test không phải gọi agent thật."""
    cam = Path(cam)

    # Đã có việc đang làm thì thôi — một agent một lúc. Đây là lớp phụ; lớp chính là
    # `IgnoreNew` của Task Scheduler. Hai lớp vì lớp chính chỉ đúng khi Windows còn THẤY
    # tiến trình cũ, mà ta đã bị chính chỗ đó cắn một lần rồi.
    if HC.dem(cam)["dang-lam"] > 0:
        return {"lam": 0, "ly_do": "đang có việc khác chạy"}

    v = HC.nhat(cam)
    if not v:
        return {"lam": 0, "ly_do": "hàng rỗng"}

    ma, cid = v["ma"], v.get("bai") or ""
    d = _dong_cua_bai(cam, cid)
    if d is None:
        HC.hong(cam, ma, f"{cid} không có trong bảng Content", vinh_vien=True)
        SO.ghi(cam, "viec_hong", bai=cid, ly_do="không có trong bảng Content")
        return {"lam": 0, "ly_do": f"{cid} không có trong bảng Content"}

    buoc = TT.buoc_ke(cam, d)

    # Bước cần NGƯỜI thì thợ không được đụng vào.
    if buoc in TT.CAN_NGUOI:
        HC.xong(cam, ma, ket_qua="bỏ qua", buoc=buoc)
        SO.ghi(cam, "viec_bo_qua", bai=cid, buoc=buoc, ly_do="bước cần người duyệt")
        return {"lam": 0, "bai": cid, "buoc": buoc, "ly_do": "bước này cần người duyệt"}

    if buoc == "xong":
        HC.xong(cam, ma, ket_qua="đã xong từ trước", buoc=buoc)
        return {"lam": 0, "bai": cid, "buoc": buoc, "ly_do": "bài đã đi hết đường ống"}

    # Trần viết lại: mỗi vòng đốt ~10 phút agent. Quá trần thì DỪNG và hỏi người.
    if buoc in ("soan", "sua-loi-cong") and _so_lan_viet(cam, cid, d) >= TRAN_VIET_LAI:
        HC.hong(cam, ma, f"đã viết lại {TRAN_VIET_LAI} lần", vinh_vien=True)
        SO.ghi(cam, "cham_tran_viet_lai", bai=cid, so_lan=TRAN_VIET_LAI)
        if bot:
            try:
                bot.gui(f"🛑 {cid}: đã viết lại {TRAN_VIET_LAI} lần mà vẫn chưa đạt.\n"
                        f"Dừng tự động để anh xem tay.")
            except Exception as e:                      # noqa: BLE001
                loi(f"không báo được Telegram ({e})")
        return {"lam": 0, "bai": cid, "buoc": buoc, "ly_do": "chạm trần viết lại"}

    cac_lenh = LENH.get(buoc)
    if not cac_lenh:
        HC.hong(cam, ma, f"chưa có lệnh cho bước {buoc}", vinh_vien=True)
        SO.ghi(cam, "viec_hong", bai=cid, buoc=buoc, ly_do="chưa dựng bước này")
        return {"lam": 0, "bai": cid, "buoc": buoc, "ly_do": f"chưa dựng bước {buoc}"}

    SO.ghi(cam, "viec_bat_dau", bai=cid, buoc=buoc, ma_viec=ma)
    xong, tin = chay(cam, cac_lenh[0], cid)

    # MÃ THOÁT KHÁC 0 KHÔNG ĐỦ ĐỂ TÍNH LÀ HỎNG — hỏi KẾT QUẢ THẬT.
    #
    # `blog_gates.py` trả mã 1 khi kết luận ĐỎ. Đó là một KẾT QUẢ, không phải sự cố: nó đã
    # chấm xong 23 cổng và ghi `gates.json` tử tế. Đọc mã thoát rồi kết luận "hỏng" thì mọi
    # bài ra đỏ sẽ bị chấm lại 3 lần rồi vứt vào `hong/`, và KHÔNG BAO GIỜ đi tiếp tới
    # `sua-loi-cong` — tức đúng những bài cần sửa thì không ai sửa. (Bắt được 12/09/2026 khi
    # chạy thử thật trên NEN-002.)
    #
    # Repo đã có luật "mã thoát 0 không đủ để tính là xong". Đây là vế ngược của cùng một
    # nguyên tắc, và cách chữa giống hệt: kiểm ARTEFACT mà bước đó phải sinh ra.
    if not xong:
        d_lai = _dong_cua_bai(cam, cid) or d
        f = (d_lai.get("folder") or "").strip()
        bai_p = Path(cam) / f.lstrip("./") if f else None
        if bai_p and _da_ra_artefact(buoc, bai_p):
            xong = True

    if xong:
        HC.xong(cam, ma, buoc=buoc)
        SO.ghi(cam, "viec_xong", bai=cid, buoc=buoc)
        sau = TT.buoc_ke(cam, _dong_cua_bai(cam, cid) or d)
        if bot and sau in TT.CAN_NGUOI:
            # Bước kế cần người ⇒ đây là lúc gõ cửa, không phải lúc im lặng.
            try:
                bot.gui(f"✅ {cid}: xong bước `{buoc}`. Đang chờ anh duyệt ({sau}).")
            except Exception as e:                      # noqa: BLE001
                loi(f"không báo được Telegram ({e})")
        return {"lam": 1, "bai": cid, "buoc": buoc, "buoc_sau": sau}

    o = HC.hong(cam, ma, tin[:200])
    SO.ghi(cam, "viec_hong", bai=cid, buoc=buoc, ly_do=tin[:200], se_thu_lai=(o == "cho"))
    if bot and o == "hong":
        try:
            bot.gui(f"❌ {cid}: bước `{buoc}` hỏng {HC.TRAN_LAN} lần, đã dừng.\n{tin[:300]}")
        except Exception as e:                          # noqa: BLE001
            loi(f"không báo được Telegram ({e})")
    return {"lam": 0, "bai": cid, "buoc": buoc, "hong": True, "se_thu_lai": o == "cho"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Làm MỘT việc trong hàng chờ rồi thoát.")
    ap.add_argument("campaign")
    a = ap.parse_args()

    cam = Path(a.campaign).resolve()
    if not (cam / "campaign.md").is_file():
        loi(f"không thấy {cam / 'campaign.md'}")
        return 2

    bot = None
    try:
        import telegram_io
        bot = telegram_io.Bot()
    except Exception as e:                              # noqa: BLE001
        loi(f"không dựng được bot ({e}) — vẫn làm việc, chỉ không báo được.")

    kq = lam_mot_viec(cam, bot=bot)
    print(json.dumps(kq, ensure_ascii=False, indent=2))
    # Mã thoát suy TỪ KẾT QUẢ. Hàng rỗng là 0 (bình thường); việc hỏng là 1 để Task
    # Scheduler và người đọc log phân biệt được.
    return 1 if kq.get("hong") else 0


if __name__ == "__main__":
    raise SystemExit(main())
