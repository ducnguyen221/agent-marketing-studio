# -*- coding: utf-8 -*-
"""Chạy lượt truyện với trần giờ; quá trần mà dải chương còn dở thì tự chạy tiếp ĐÚNG MỘT LẦN.

    python resume_once.py [--title T] [--budget 30600] [--resume-budget 10800] [--mark F] \\
        -- <python> -u daily_truyen.py --state <truyen-state.json>

`run-daily-truyen.ps1` gọi file này thay vì gọi thẳng `daily_truyen.py`.

## Vì sao (P1-23, Mac mini 02/10/2026)

Lượt truyện 301–310 bị wrapper giết lúc 08:30 — mã 124, sau 9/10 chương: giọng `a-tun-v1` mất
~55 phút/chương nên 10 chương vượt trần 30600 s. Người phải `launchctl kickstart` tay; lượt chạy
tiếp dùng cache chương + `_resume.json` và xong sau 1 h 26. Đức chốt: runner TỰ chạy tiếp.

## Vì sao nằm ở runner, không ở wrapper báo cáo

Wrapper trên launchd là `notify_run.py` (repo); trên Task Scheduler của máy gốc là một wrapper
PowerShell NGOÀI repo. Đặt "chạy tiếp" vào wrapper thì chỉ một trong hai máy có nó. Đặt ở đây
thì cả hai chạy y hệt, và wrapper ngoài chỉ còn là lưới an toàn — nên trần của wrapper phải ≥
`--budget + --resume-budget` + biên (plist `daily-story`, `-Register` của runner; cổng:
`tests/test_resume_once.py`).

## Luật

· Lượt đầu chạy với trần `--budget`. Quá trần ⇒ giết CẢ CÂY tiến trình (`notify_run.chay_lenh`,
  cùng cách wrapper làm), coi như mã 124. Lệnh con tự thoát 124 cũng tính là quá trần.
· Mã 124 **và** `_resume.json` còn dải dở (`{slug,start,end,voice,cache_dir}` hợp lệ) ⇒ gửi tin ⏳
  "quá trần — đang chạy tiếp từ chương X", rồi chạy lại ĐÚNG lệnh đó MỘT lần với trần
  `--resume-budget`. `daily_truyen.py` thấy dấu khớp dải ⇒ chừa cache ⇒ `read_story` bỏ qua mọi
  chương đã có `Chuong_<n>.wav`: không đọc lại chương nào.
· Không còn `_resume.json` ⇒ KHÔNG chạy tiếp (dải đã xong, hoặc hỏng trước khi ghi dấu): trả 124.
· Lượt chạy tiếp lại 124 ⇒ DỪNG, không lặp. Cache vẫn nằm đó cho lượt theo lịch kế tiếp.
· Mã thoát = mã của lượt cuối cùng đã chạy. Tin ✅/❌ của lượt chạy tiếp do wrapper gửi như mọi
  lượt (nó thấy mã thoát + log, gồm hai dòng `RESUME_ONCE=…` cho `compose_report.py`).
· Tin ⏳ không bao giờ làm hỏng lượt chạy: thiếu cấu hình Telegram / lỗi mạng chỉ in cảnh báo.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # scripts/runners — notify_run
sys.path.insert(0, HERE)                           # truyen_paths
import notify_run  # noqa: E402

# Cùng tên với `daily_truyen.RESUME_MARK` (cổng: tests/test_resume_once.py). Không import
# daily_truyen: nó phân giải trạm giọng ngay lúc import và thoát nếu thiếu.
RESUME_MARK = "_resume.json"
MA_QUA_GIO = notify_run.MA_QUA_GIO          # 124 — một hợp đồng mã thoát cho cả hai máy
TRAN_DAU = 30600        # 8 h 30 — trần lượt đầu như trước (đo: lượt rảnh ~6 h 05 + crawl + dựng)
TRAN_TIEP = 10800       # 3 h — lượt tiếp chỉ còn phần dở: 1 chương a-tun-v1 ~55′ + dựng ~40′ + đăng


def duong_dau(env=None) -> str | None:
    """`<trạm giọng>/omnivoice/truyen-out/_resume.json`; None nếu chưa biết trạm giọng."""
    try:
        import truyen_paths
        return os.path.join(truyen_paths.engine_dir(env), "truyen-out", RESUME_MARK)
    except SystemExit:            # truyen_paths báo "không biết trạm giọng" bằng SystemExit
        return None


def dai_do(mark_path: str | None) -> dict | None:
    """Dấu dải đang dở, hoặc None nếu không có / không đọc được / thiếu dải hợp lệ."""
    if not mark_path or not os.path.isfile(mark_path):
        return None
    try:
        with open(mark_path, encoding="utf-8") as f:
            m = json.load(f)
        if isinstance(m, dict) and int(m["start"]) <= int(m["end"]):
            return m
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def chuong_tiep(mark: dict, mark_path: str) -> int | None:
    """Chương đầu tiên CHƯA có `Chuong_<n>.wav` trong cache của dải; None = đã đọc đủ dải."""
    thu_muc = os.path.join(os.path.dirname(mark_path), str(mark.get("cache_dir") or ""))
    for n in range(int(mark["start"]), int(mark["end"]) + 1):
        if not os.path.isfile(os.path.join(thu_muc, f"Chuong_{n}.wav")):
            return n
    return None


def tin_cho(title: str, budget: int, resume_budget: int, mark: dict, tiep: int | None) -> str:
    e = lambda s: html.escape(str(s), quote=False)  # noqa: E731
    tu = (f"từ chương <b>{tiep}</b>" if tiep is not None
          else "— đã đọc đủ chương, còn dựng video và đăng")
    return (f"⏳ <b>{e(title)}</b> — quá trần {budget}s ở lượt đầu; đang chạy tiếp {tu} "
            f"(dải {e(mark['start'])}–{e(mark['end'])}, giọng {e(mark.get('voice', '?'))}, dùng "
            f"cache chương đã đọc, trần {resume_budget}s). Tin ✅/❌ của lượt chạy tiếp sẽ tới sau.")


def chay(cmd: list[str], title: str, budget: int, resume_budget: int, mark_path: str | None,
         run=notify_run.chay_lenh, send=notify_run.gui) -> int:
    """Lõi: trả mã thoát. `run`/`send` mở cho test."""
    ma, _dong, qua = run(cmd, budget or None)
    if ma != MA_QUA_GIO and not qua:
        return ma
    mark = dai_do(mark_path)
    if mark is None:
        print(f"[resume] quá trần (mã {MA_QUA_GIO}) nhưng không còn dấu dải dở "
              f"({mark_path or 'chưa biết trạm giọng'}) — KHÔNG chạy tiếp.", flush=True)
        return MA_QUA_GIO
    tiep = chuong_tiep(mark, mark_path)
    print(f"[resume] ⏳ quá trần {budget}s — chạy tiếp MỘT lần từ chương "
          f"{tiep if tiep is not None else '(đủ chương, dựng video)'} "
          f"(dải {mark['start']}-{mark['end']}, trần {resume_budget}s)", flush=True)
    print(f"RESUME_ONCE=start from={tiep if tiep is not None else 'build'} "
          f"range={mark['start']}-{mark['end']}", flush=True)
    try:
        send(tin_cho(title, budget, resume_budget, mark, tiep))
    except Exception as e:  # noqa: BLE001 — tin báo hỏng không được chặn lượt chạy tiếp
        print(f"[resume] không gửi được tin ⏳ — {notify_run._che_token(e)}", flush=True)
    ma2, _dong2, qua2 = run(cmd, resume_budget or None)
    if ma2 == MA_QUA_GIO or qua2:
        print(f"[resume] lượt chạy tiếp CŨNG quá trần {resume_budget}s — DỪNG, không lặp "
              f"(cache chương còn nguyên cho lượt theo lịch kế tiếp).", flush=True)
        ma2 = MA_QUA_GIO
    print(f"RESUME_ONCE=done code={ma2}", flush=True)
    return ma2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(
        prog="resume_once.py",
        description="Chạy lượt truyện có trần giờ; quá trần mà dải còn dở thì chạy tiếp đúng 1 lần.",
        usage="%(prog)s [--title T] [--budget GIÂY] [--resume-budget GIÂY] [--mark FILE] "
              "-- LỆNH [ĐỐI SỐ…]")
    ap.add_argument("--title", default="Truyện", help="tên lượt trên tin ⏳")
    ap.add_argument("--budget", type=int, default=TRAN_DAU,
                    help=f"trần lượt đầu, giây (mặc định {TRAN_DAU}; 0 = không trần)")
    ap.add_argument("--resume-budget", type=int, default=TRAN_TIEP,
                    help=f"trần lượt chạy tiếp, giây (mặc định {TRAN_TIEP})")
    ap.add_argument("--mark", help="đường tới _resume.json (mặc định: trạm giọng)")
    if "--" in argv:
        i = argv.index("--")
        opts, cmd = argv[:i], argv[i + 1:]
    else:
        opts, cmd = argv, []
    a = ap.parse_args(opts)
    if not cmd:
        ap.error("thiếu lệnh con sau `--`")
    if a.budget < 0 or a.resume_budget < 1:
        ap.error("--budget phải ≥ 0 và --resume-budget phải ≥ 1")
    return chay(cmd, a.title, a.budget, a.resume_budget, a.mark or duong_dau())


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    sys.exit(main())
