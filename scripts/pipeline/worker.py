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

`pipeline_state.NEEDS_HUMAN` đánh dấu `await-G1` và `await-G2`. Gặp hai bước đó thợ **trả việc về và
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
import work_queue as WQ          # noqa: E402
import md_io                   # noqa: E402
import event_log as EV        # noqa: E402
import pipeline_state as PS        # noqa: E402

# Bước nào chạy bằng lệnh nào. `sua_lai` cũng chạy `soan` — bước đó tự đọc `phan-hoi.md`.
COMMANDS = {
    "write": ["write"],
    "check-gates": ["__check_gates__"],
    "fix-gates": ["write"],
    "build-page": ["build-page"],
    "release": ["release"],
}

MAX_REWRITES = 3      # bài bị trả lại quá ngần này lần thì dừng, hỏi người


def loi(m: str) -> None:
    sys.stderr.write(f"worker: {m}\n")


def _write_count(campaign: Path, cid: str, row: dict) -> int:
    f = (row.get("folder") or "").strip()
    if not f:
        return 0
    p = Path(campaign) / f.lstrip("./") / ".write-count.json"
    if not p.is_file():
        return 0
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("attempts") or 0)
    except (json.JSONDecodeError, ValueError):
        return 0


def _row_of_post(campaign: Path, cid: str) -> dict | None:
    _, than = md_io.read_fm(Path(campaign) / "campaign.md")
    _, row = md_io.read_table(than, "CONTENT")
    for d in row:
        if d.get("content_id") == cid:
            return d
    return None


def _run_step(campaign: Path, step: str, cid: str) -> tuple[bool, str]:
    """Gọi `campaign_step.py <buoc>`. Trả `(xong, thông điệp)`."""
    if step == "__check_gates__":
        script = Path(__file__).resolve().parent / "blog_gates.py"
        d = _row_of_post(campaign, cid) or {}
        post = Path(campaign) / (d.get("folder") or "").lstrip("./")
        cmd = [sys.executable, str(script), str(post)]
    else:
        script = Path(__file__).resolve().parent / "campaign_step.py"
        cmd = [sys.executable, str(script), str(campaign), step]
        # GIỚI HẠN ĐÚNG MỘT BÀI. Việc trong hàng chờ là theo từng bài, còn bước vốn quét cả
        # chiến dịch. Thiếu cờ này thì một việc cho NEN-002 viết lại luôn NEN-001 và
        # NEN-003: kế toán số lần viết lại thành vô nghĩa, và lượt chạy kéo hàng giờ.
        # Đo thật 12/09/2026 — một việc chạy 27 phút vì ôm ba bài.
        if step in ("write", "fix-gates", "build-page", "release") and cid:
            cmd += ["--post", cid]

    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    ra = ((r.stdout or "") + (r.stderr or "")).strip()
    return r.returncode == 0, ra[-600:]


def _has_artefact(step: str, post: Path) -> bool:
    """Bước này lẽ ra phải sinh ra cái gì — cái đó có chưa?

    MÃ THOÁT KHÁC 0 KHÔNG ĐỦ ĐỂ TÍNH LÀ HỎNG. Hai bước trong đường ống trả mã khác 0 cho
    một KẾT QUẢ hợp lệ, không phải cho sự cố:

      · `blog_gates.py` trả 1 khi kết luận ĐỎ — nhưng nó đã chấm xong 23 cổng và ghi
        `gates.json` tử tế.
      · `soan` trả khác 0 khi bài viết ra chưa qua cổng — nhưng bài ĐÃ ĐƯỢC VIẾT.

    Đọc mã thoát rồi kết luận "hỏng" thì đúng những bài cần đi tiếp lại bị chấm/viết lại ba
    lần rồi vứt vào `failed/`. Đo thật 12/09/2026: một lượt như thế đốt 27 phút agent rồi bị
    tính là thất bại.

    Repo đã có luật ngược lại — *"mã thoát 0 không đủ để tính là xong"* (bộ viết chạy êm mà
    file vẫn trống thì vẫn là hỏng). Cùng một nguyên tắc, hai chiều: **hỏi artefact, đừng
    hỏi mã thoát.**
    """
    if step == "check-gates":
        return (post / "gates.json").is_file()
    if step in ("write", "fix-gates"):
        return post_content.has_content(post)
    if step == "build-page":
        # Trang đã dựng ra file thì bước đã làm được việc. URL có ghi được vào bảng hay
        # không là chuyện của `web_publish`, và nó tự fail-closed ở đó.
        return (post / "atlas" / "atlas.html").is_file()
    return False


def run_one_job(campaign: Path, *, bot=None, run_cmd=_run_step) -> dict:
    """Nhặt một việc và làm. `chay` tiêm được để test không phải gọi agent thật."""
    campaign = Path(campaign)

    # Đã có việc đang làm thì thôi — một agent một lúc. Đây là lớp phụ; lớp chính là
    # `IgnoreNew` của Task Scheduler. Hai lớp vì lớp chính chỉ đúng khi Windows còn THẤY
    # tiến trình cũ, mà ta đã bị chính chỗ đó cắn một lần rồi.
    if WQ.count(campaign)["running"] > 0:
        return {"lam": 0, "reason": "đang có việc khác chạy"}

    v = WQ.claim(campaign)
    if not v:
        return {"lam": 0, "reason": "hàng rỗng"}

    job_id, cid = v["job_id"], v.get("post") or ""
    d = _row_of_post(campaign, cid)
    if d is None:
        WQ.failed(campaign, job_id, f"{cid} không có trong bảng Content", permanent=True)
        EV.write(campaign, "job_failed", post=cid, reason="không có trong bảng Content")
        return {"lam": 0, "reason": f"{cid} không có trong bảng Content"}

    step = PS.next_step(campaign, d)

    # Bước cần NGƯỜI thì thợ không được đụng vào.
    if step in PS.NEEDS_HUMAN:
        WQ.done(campaign, job_id, result="bỏ qua", step=step)
        EV.write(campaign, "job_skipped", post=cid, step=step, reason="bước cần người duyệt")
        return {"lam": 0, "post": cid, "step": step, "reason": "bước này cần người duyệt"}

    if step == "done":
        WQ.done(campaign, job_id, result="đã xong từ trước", step=step)
        return {"lam": 0, "post": cid, "step": step, "reason": "bài đã đi hết đường ống"}

    # Trần viết lại: mỗi vòng đốt ~10 phút agent. Quá trần thì DỪNG và hỏi người.
    if step in ("write", "fix-gates") and _write_count(campaign, cid, d) >= MAX_REWRITES:
        WQ.failed(campaign, job_id, f"đã viết lại {MAX_REWRITES} lần", permanent=True)
        EV.write(campaign, "rewrite_limit_hit", post=cid, attempts=MAX_REWRITES)
        if bot:
            try:
                bot.gui(f"🛑 {cid}: đã viết lại {MAX_REWRITES} lần mà vẫn chưa đạt.\n"
                        f"Dừng tự động để anh xem tay.")
            except Exception as e:                      # noqa: BLE001
                loi(f"không báo được Telegram ({e})")
        return {"lam": 0, "post": cid, "step": step, "reason": "chạm trần viết lại"}

    cac_lenh = COMMANDS.get(step)
    if not cac_lenh:
        WQ.failed(campaign, job_id, f"chưa có lệnh cho bước {step}", permanent=True)
        EV.write(campaign, "job_failed", post=cid, step=step, reason="chưa dựng bước này")
        return {"lam": 0, "post": cid, "step": step, "reason": f"chưa dựng bước {step}"}

    EV.write(campaign, "job_started", post=cid, step=step, job_id=job_id)
    done, msg = run_cmd(campaign, cac_lenh[0], cid)

    # MÃ THOÁT KHÁC 0 KHÔNG ĐỦ ĐỂ TÍNH LÀ HỎNG — hỏi KẾT QUẢ THẬT.
    #
    # `blog_gates.py` trả mã 1 khi kết luận ĐỎ. Đó là một KẾT QUẢ, không phải sự cố: nó đã
    # chấm xong 23 cổng và ghi `gates.json` tử tế. Đọc mã thoát rồi kết luận "hỏng" thì mọi
    # bài ra đỏ sẽ bị chấm lại 3 lần rồi vứt vào `failed/`, và KHÔNG BAO GIỜ đi tiếp tới
    # `fix-gates` — tức đúng những bài cần sửa thì không ai sửa. (Bắt được 12/09/2026 khi
    # chạy thử thật trên NEN-002.)
    #
    # Repo đã có luật "mã thoát 0 không đủ để tính là xong". Đây là vế ngược của cùng một
    # nguyên tắc, và cách chữa giống hệt: kiểm ARTEFACT mà bước đó phải sinh ra.
    if not done:
        d_lai = _row_of_post(campaign, cid) or d
        f = (d_lai.get("folder") or "").strip()
        post_dir = Path(campaign) / f.lstrip("./") if f else None
        if post_dir and _has_artefact(step, post_dir):
            done = True

    if done:
        WQ.done(campaign, job_id, step=step)
        EV.write(campaign, "job_done", post=cid, step=step)
        sau = PS.next_step(campaign, _row_of_post(campaign, cid) or d)
        if bot and sau in PS.NEEDS_HUMAN:
            # Bước kế cần người ⇒ đây là lúc gõ cửa, không phải lúc im lặng.
            try:
                bot.gui(f"✅ {cid}: xong bước `{step}`. Đang chờ anh duyệt ({sau}).")
            except Exception as e:                      # noqa: BLE001
                loi(f"không báo được Telegram ({e})")
        return {"lam": 1, "post": cid, "step": step, "buoc_sau": sau}

    o = WQ.failed(campaign, job_id, msg[:200])
    EV.write(campaign, "job_failed", post=cid, step=step, reason=msg[:200], will_retry=(o == "pending"))
    if bot and o == "failed":
        try:
            bot.gui(f"❌ {cid}: bước `{step}` hỏng {WQ.MAX_ATTEMPTS} lần, đã dừng.\n{msg[:300]}")
        except Exception as e:                          # noqa: BLE001
            loi(f"không báo được Telegram ({e})")
    return {"lam": 0, "post": cid, "step": step, "failed": True, "will_retry": o == "pending"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Làm MỘT việc trong hàng chờ rồi thoát.")
    ap.add_argument("campaign")
    a = ap.parse_args()

    campaign = Path(a.campaign).resolve()
    if not (campaign / "campaign.md").is_file():
        loi(f"không thấy {campaign / 'campaign.md'}")
        return 2

    bot = None
    try:
        import telegram_io
        bot = telegram_io.Bot()
    except Exception as e:                              # noqa: BLE001
        loi(f"không dựng được bot ({e}) — vẫn làm việc, chỉ không báo được.")

    result = run_one_job(campaign, bot=bot)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Mã thoát suy TỪ KẾT QUẢ. Hàng rỗng là 0 (bình thường); việc hỏng là 1 để Task
    # Scheduler và người đọc log phân biệt được.
    return 1 if result.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
