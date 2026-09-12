#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Điều phối đường ống TRONG PHIÊN — lối vào một cửa cho agent.

## Nó là gì

Agent ngồi cùng người trong một phiên không cần biết mười trạng thái và năm lệnh con. Nó
gọi đúng một lệnh, và lệnh này:

1. suy bước kế tiếp của từng bài (`pipeline_state`),
2. chạy tới khi đụng **cổng người**,
3. **DỪNG** và trả về đúng thứ agent cần đọc cho người nghe: bài nào, chờ cổng nào, câu hỏi
   là gì, và **mở file nào để trả lời được câu hỏi đó**.

Nó **không bao giờ tự mở cổng**. Mở cổng cần câu nói của người, và câu đó phải đi qua
`approval_gate.open_gate(--quote ...)`.

## Khác gì `worker.py`

Cùng chạy một đường ống, khác chủ:

| | `worker.py` | `run_pipeline.py` |
|---|---|---|
| ai gọi | scheduled task, chạy nền | **agent, trong phiên** |
| lấy việc từ | hàng chờ (`logs/jobs/`) | người chỉ định, hoặc suy từ bảng |
| mỗi lượt | đúng MỘT việc rồi thoát | chạy tới khi đụng cổng |
| tới cổng thì | trả việc về, báo Telegram | **in ra cho agent hỏi người ngay** |

Hai đường dùng chung mọi thứ bên dưới — cùng `campaign_step`, cùng `pipeline_state`, cùng kho
cổng. Chạy đường nào cũng để lại cùng một dấu vết.

## Hai chế độ

- `tung-bai` — một bài đi trọn đường ống, dừng ở mỗi cổng. Dùng khi bài quan trọng, hoặc
  đang dò xem quy trình chạy đúng chưa.
- `theo-giai-doan` — chạy cùng một bước cho N bài rồi gom lại hỏi người MỘT LẦN ở cổng.
  Dùng khi chạy đều nhiều bài và không muốn bị ngắt liên tục.

## Lệnh

```
run_pipeline.py <chiến dịch> status [--json]
run_pipeline.py <chiến dịch> run [--mode tung-bai|theo-giai-doan]
                                    [--post A,B | --count N] [--until <bước>]
                                    [--json] [--dry-run]
```

`--dry-run` in ra kế hoạch sẽ chạy mà không chạy gì — dùng để trình người xem trước.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
sys.path.insert(0, str(_HERE))
import approval_gate as AG  # noqa: E402
import worker as WK  # noqa: E402
import pipeline_state as PS  # noqa: E402

MODES = ("tung-bai", "theo-giai-doan")
DEFAULT_POSTS = 5

# Trần an toàn cho MỘT lượt gọi. Không phải giới hạn nghiệp vụ — nó chặn ca vòng lặp: một
# bước báo xong mà `pipeline_state` vẫn suy ra đúng bước đó thì hai bên quay tít cho tới hết
# quota. Trần nhỏ hơn số bước của đường ống là hụt, nên lấy gấp đôi.
MAX_STEPS_PER_POST = 2 * len(PS.ORDER)

# Bước KHÔNG có artefact riêng của một bài để hỏi. Danh sách này phải ngắn và có lý do:
# mỗi tên trong đây là một chỗ ta buộc phải tin mã thoát, tức một chỗ có thể hỏng câm.
NO_ARTEFACT = {"create-post"}


def loi(m: str) -> None:
    sys.stderr.write(f"run_pipeline: {m}\n")


# ── Đọc tình hình ───────────────────────────────────────────────────────────

def _rows_by_id(campaign: Path) -> dict:
    return {d["content_id"]: d for d in AG.read_content_table(campaign)[3]}


def overview(campaign: Path) -> dict:
    """Bài nào đang ở bước nào — gộp theo bước để người nhìn một cái là nắm."""
    campaign = Path(campaign)
    by_step: dict[str, list[str]] = {}
    for d in AG.read_content_table(campaign)[3]:
        by_step.setdefault(PS.next_step(campaign, d), []).append(d["content_id"])
    return {"total": sum(len(v) for v in by_step.values()),
            # Theo ĐÚNG thứ tự đường ống, không theo thứ tự từ điển: người đọc cần thấy
            # bài đang tắc ở đâu trên đường, không cần bảng chữ cái.
            "by_step": {b: by_step[b] for b in PS.ORDER if b in by_step}}


def _gate_of_step(step: str) -> str | None:
    return step.replace("await-G", "g") if step in PS.NEEDS_HUMAN else None


def _gate_files(campaign: Path, cid: str, gate: str) -> dict:
    row = _rows_by_id(campaign).get(cid) or {}
    h = AG.post_files(campaign, row)
    h["gate"] = gate
    if gate == "g2":
        h["not_ready"] = AG.why_not_ready(campaign, row)
    return h


# ── Chọn bài ────────────────────────────────────────────────────────────────

def pick_posts(campaign: Path, *, post: list[str] | None, count: int | None) -> list[str]:
    """Người chỉ định bài nào thì đúng bài đó. Không chỉ định thì lấy N bài ĐANG CHẠY ĐƯỢC.

    "Chạy được" = bước kế tiếp không phải cổng và không phải `xong`. Lấy cả bài đang chờ
    cổng vào lô là mời agent chạy một bước mà nó không được phép chạy.
    """
    campaign = Path(campaign)
    hien = _rows_by_id(campaign)
    if post:
        thieu = [c for c in post if c not in hien]
        if thieu:
            raise ValueError(f"không có trong bảng Content: {', '.join(thieu)}")
        return list(post)
    chay_duoc = [d["content_id"] for d in AG.read_content_table(campaign)[3]
                 if PS.next_step(campaign, d) not in PS.NEEDS_HUMAN | {"done"}]
    n = DEFAULT_POSTS if count is None else count
    return chay_duoc if n <= 0 else chay_duoc[:n]


# ── Chạy ────────────────────────────────────────────────────────────────────

def _run_one_step(campaign: Path, cid: str, step: str, *, run) -> dict:
    """Chạy một bước cho một bài và kết luận theo ARTEFACT, không theo mã thoát.

    Cùng luật với `worker._has_artefact`: `blog_gates` trả mã 1 khi cổng đỏ và `soan`
    trả khác 0 khi bài chưa đạt — cả hai ĐÃ LÀM XONG VIỆC. Đọc mã thoát rồi kết luận hỏng
    thì đúng những bài cần đi tiếp lại bị làm lại rồi vứt đi.
    """
    row = _rows_by_id(campaign).get(cid) or {}
    folder = (row.get("folder") or "").strip().lstrip("./")
    post_dir = Path(campaign) / folder if folder else Path(campaign)

    cmd = WK.COMMANDS.get(step, [step])
    ok_tat_ca, message = True, []
    for l in cmd:
        ok, ra = run(campaign, l, cid)
        ok_tat_ca = ok_tat_ca and ok
        if ra:
            message.append(ra)

    has_artefact = WK._has_artefact(step, post_dir)
    return {"post": cid, "step": step,
            "clean_exit": ok_tat_ca,
            "has_artefact": has_artefact,
            # Xong hay chưa hỏi ARTEFACT. `create-post` là NGOẠI LỆ CÓ TÊN: nó tạo thư mục
            # cho nhiều bài cùng lúc nên không có artefact riêng của một bài để hỏi, đành
            # tin mã thoát. Ngoại lệ có tên khác hẳn với mặc định tin mã thoát.
            "done": has_artefact or (step in NO_ARTEFACT and ok_tat_ca),
            "message": "\n".join(message)[-800:]}


def run(campaign: Path, *, mode: str = "tung-bai", post: list[str] | None = None,
         count: int | None = None, until: str | None = None,
         dry_run: bool = False, run_step=None) -> dict:
    """Đẩy các bài đã chọn đi tới khi đụng cổng. KHÔNG BAO GIỜ tự mở cổng.

    `run_step=None` được giải nghĩa TẠI ĐÂY chứ không đặt sẵn ở chữ ký hàm: giá trị mặc
    định của tham số bị đóng băng lúc `def` chạy, nên vá `TV._run_step` sau đó không có
    tác dụng — test tưởng đang chạy bộ giả mà thật ra gọi tiến trình con thật.
    """
    campaign = Path(campaign)
    run_step = run_step or WK._run_step
    if mode not in MODES:
        raise ValueError(f"chế độ lạ: {mode!r} — chỉ có {', '.join(MODES)}")
    ds = pick_posts(campaign, post=post, count=count)
    result: dict = {"mode": mode, "post": ds, "ran": [], "failed": [],
                "waiting": {}, "finished": []}

    if dry_run:
        result["plan"] = [{"post": c,
                           "next_step": PS.next_step(campaign, _rows_by_id(campaign).get(c) or {})}
                          for c in ds]
        return result

    if mode == "tung-bai":
        for cid in ds:
            _advance_post(campaign, cid, result, until=until, run_step=run_step)
    else:
        # Theo giai đoạn: mỗi vòng đẩy CẢ LÔ đúng một bước, để các bài tới cổng cùng lúc
        # rồi hỏi người một lần. Đẩy lần lượt từng bài tới cổng thì người bị hỏi N lần —
        # đúng thứ chế độ này sinh ra để tránh.
        for _ in range(MAX_STEPS_PER_POST):
            da_lam = False
            for cid in list(ds):
                b = PS.next_step(campaign, _rows_by_id(campaign).get(cid) or {})
                if b in PS.NEEDS_HUMAN:
                    _mark_waiting(campaign, cid, _gate_of_step(b), result)
                    ds = [x for x in ds if x != cid]
                    continue
                if b == "done":
                    if cid not in result["finished"]:
                        result["finished"].append(cid)
                    ds = [x for x in ds if x != cid]
                    continue
                if until and b == until:
                    ds = [x for x in ds if x != cid]
                    continue
                r = _run_one_step(campaign, cid, b, run=run_step)
                result["ran"].append(r)
                da_lam = True
                if not r["done"]:
                    result["failed"].append(r)
                    ds = [x for x in ds if x != cid]     # bài hỏng thì thôi đẩy tiếp
            if not da_lam:
                break
    result["overview"] = overview(campaign)
    return result


def _mark_waiting(campaign: Path, cid: str, gate: str, result: dict) -> None:
    """Ghi một bài vào nhóm chờ cổng. KHÔNG ghi trùng: một bài chỉ hỏi người một lần."""
    ds = result["waiting"].setdefault(gate, [])
    if cid not in [h["content_id"] for h in ds]:
        ds.append(_gate_files(campaign, cid, gate))


def _advance_post(campaign: Path, cid: str, result: dict, *, until: str | None, run_step) -> None:
    for _ in range(MAX_STEPS_PER_POST):
        b = PS.next_step(campaign, _rows_by_id(campaign).get(cid) or {})
        if b in PS.NEEDS_HUMAN:
            _mark_waiting(campaign, cid, _gate_of_step(b), result)
            return
        if b == "done":
            result["finished"].append(cid)
            return
        if until and b == until:
            return
        r = _run_one_step(campaign, cid, b, run=run_step)
        result["ran"].append(r)
        if not r["done"]:
            result["failed"].append(r)
            return
    result["failed"].append({"post": cid, "step": "?",
                       "message": f"quá {MAX_STEPS_PER_POST} bước mà chưa tới cổng — "
                                     "nghi bước báo xong nhưng trạng thái không tiến"})


# ── In cho người ────────────────────────────────────────────────────────────

def _print_overview(t: dict) -> None:
    print(f"{t['total']} bài\n")
    for b, ds in t["by_step"].items():
        print(f"  {b:<14} {len(ds):>3}  {', '.join(ds[:12])}"
              + (" …" if len(ds) > 12 else ""))


def _print_result(result: dict) -> None:
    if result.get("plan") is not None:
        print("KẾ HOẠCH (chưa chạy gì):")
        for k in result["plan"]:
            print(f"  {k['post']:<10} → {k['next_step']}")
        return

    if result["ran"]:
        print("ĐÃ CHẠY")
        for r in result["ran"]:
            start = "✔" if r["done"] else "✘"
            print(f"  {start} {r['post']:<10} {r['step']}")
        print()
    if result["failed"]:
        print("HỎNG — dừng ở đây, cần xem log")
        for r in result["failed"]:
            print(f"  ✘ {r['post']} · {r.get('step')}")
            for d in (r.get("message") or "").splitlines()[-6:]:
                print(f"      {d}")
        print()
    for gate, ds in result["waiting"].items():
        print(f"⛔ DỪNG Ở {gate.upper()} — {len(ds)} bài chờ người quyết\n")
        for h in ds:
            print(f"  · {h['content_id']} — {h['content_name']}")
            if h.get("not_ready"):
                print(f"      ⚠️ chưa được đem ra hỏi: {h['not_ready']}")
            for label, p in h["file"].items():
                print(f"      {label:<16} {p}")
            if h.get("web"):
                print(f"      {'bản thật':<16} {h['web']}")
        print(f"\n  Duyệt:   approval_gate.py <chiến dịch> open --gate {gate} "
              f"--post <mã> --by \"<tên>\" --quote \"<câu người nói>\"")
        print(f"  Từ chối: approval_gate.py <chiến dịch> reject --gate {gate} "
              f"--post <mã> --by \"<tên>\" --quote \"<nhận xét>\"\n")
    if result["finished"]:
        print(f"✅ xong hẳn: {', '.join(result['finished'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Điều phối đường ống trong phiên — chạy tới cổng rồi dừng hỏi người.")
    ap.add_argument("campaign")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pt = sub.add_parser("status", help="bài nào đang ở bước nào")
    pt.add_argument("--json", action="store_true")

    pc = sub.add_parser("run", help="đẩy các bài tới cổng gần nhất")
    pc.add_argument("--mode", choices=list(MODES), default="tung-bai")
    pc.add_argument("--post", default=None, help="mã bài, phân tách bằng dấu phẩy")
    pc.add_argument("--count", type=int, default=None,
                    help=f"lấy N bài đang chạy được (mặc định {DEFAULT_POSTS}; 0 = hết)")
    pc.add_argument("--until", default=None, help="dừng TRƯỚC bước này")
    pc.add_argument("--dry-run", action="store_true")
    pc.add_argument("--json", action="store_true")

    a = ap.parse_args(argv)
    campaign = Path(a.campaign)
    if not (campaign / "campaign.md").is_file():
        loi(f"không thấy {campaign / 'campaign.md'}")
        return 2

    if a.cmd == "status":
        t = overview(campaign)
        print(json.dumps(t, ensure_ascii=False, indent=2) if a.json else "", end="")
        if not a.json:
            _print_overview(t)
        return 0

    try:
        result = run(campaign, mode=a.mode,
                  post=[x.strip() for x in a.post.split(",") if x.strip()] if a.post else None,
                  count=a.count, until=a.until, dry_run=a.dry_run)
    except ValueError as e:
        loi(str(e))
        return 2

    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_result(result)
    # Dừng ở cổng KHÔNG phải hỏng: đó là kết quả đúng của đường ống có cổng người.
    return 3 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
