#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gọi một agent headless (`claude` / `codex` / `agy`) qua một hợp đồng duy nhất.

Đây là CLI mỏng; toàn bộ luật nằm ở `scripts/lib/agent_call.py` — đọc docstring ở đó để
biết vì sao lớp này tồn tại và vì sao skill được nhúng vào prompt thay vì để từng CLI tự
tìm.

    # thay cho `$prompt | claude -p --allowedTools …` trong script trạm
    agent_call.py --engine claude --tools web,read,write,shell:curl \
        --prompt-file prompt.txt --expect out/2026-09-20-top.json:800 --json

    # cổng chữ nội bộ chạy một mình (không gọi engine nào, không tốn hạn mức)
    agent_call.py --check-text bai.md --json

`--expect` nhận **cả hai họ đường dẫn** (`D:/kho/bai.md` và `/d/kho/bai.md` kiểu Git Bash);
đường tuyệt đối của họ kia mà không dịch được thì trả **mã 2 kèm chỉ dẫn**, không âm thầm
coi là thiếu artifact. `--stall` chỉ áp cho engine thật sự phát tiến độ ra stdout — với
engine im tới câu cuối (`claude`, `agy`) nó bị TẮT và có một dòng log nói rõ; lưới an toàn
lúc đó là `--timeout`. Lý do cả hai: `AGENT-CALL-DESIGN.md` và `BENCH-WRITER-2026-09-20.md` §7.

Mã thoát (0/1/2/3 là hợp đồng ba trạm, 4 là phần riêng của làn này):

    0  xong VÀ mọi `--expect` đạt
    1  lỗi engine tạm — timeout, CLI thoát ≠ 0, hoặc mã 0 mà artifact thiếu ⇒ lịch THỬ LẠI
    2  hợp đồng sai — engine/model lạ, skill không thấy, prompt quá trần argv ⇒ SỬA CẤU HÌNH
    3  trạm thiếu — CLI không có trên PATH, hoặc chưa đăng nhập ⇒ CÀI/ĐĂNG NHẬP
    4  hết hạn mức ở MỌI engine trong chuỗi ⇒ chạy lại SAU `resets_at` (có trong JSON)

Mã 4 là phần thêm, và nó có lý do cụ thể: tối 19–20/09 hai lượt lịch chết vì hết hạn mức
Claude, mỗi lượt thử lại 3 lần trong 30 giây trong khi giờ mở lại cách đó 1–2 tiếng. Mã 1
bảo lịch "thử lại ngay" (vô ích), mã 2 bảo "sửa cấu hình" (không có gì để sửa). `resets_at`
đi kèm để `notify-run.ps1` nói được "hết hạn mức, mở lại 19:50" thay vì "fail".
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import agent_call as AC  # noqa: E402
import studio_contract as SC  # noqa: E402

PROG = "agent-call"


def _parser():
    ap = argparse.ArgumentParser(prog=PROG, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=AC.ENGINES,
                    help="engine chạy lượt đầu; phần còn lại của chuỗi đọc từ engines.json "
                         "(bắt buộc, trừ khi chỉ chạy --check-text)")
    ap.add_argument("--model", default="best",
                    help="`best` = model tốt nhất mà trạm khai cho engine đó (mặc định)")
    ap.add_argument("--prompt-file", help="tệp prompt; bỏ trống ⇒ đọc stdin")
    ap.add_argument("--skills", default="",
                    help="tên skill, phân cách dấu phẩy (vd studio-skills:blog-writing)")
    ap.add_argument("--skills-mode", default="inline", choices=("inline", "native"),
                    help="inline = nhúng SKILL.md vào prompt cho MỌI engine (mặc định, công bằng)")
    ap.add_argument("--tools", default="read,write",
                    help="tập trừu tượng: web,read,write,shell:<lệnh> — map sang cờ từng engine")
    ap.add_argument("--cwd", help="thư mục làm việc của agent (mặc định: cwd hiện tại)")
    ap.add_argument("--timeout", type=int, default=1800, help="trần tổng, giây")
    # 600 chứ không phải 180: lượt thật đo được 250–440 s (bench 20/09), và đồng hồ này chỉ
    # được vũ trang cho engine thật sự phát tiến độ ra stdout — với engine im lặng nó bị
    # TẮT, vì đo sự im lặng của một tiến trình vốn im lặng là đo chính cái đồng hồ.
    ap.add_argument("--stall", type=int, default=600,
                    help="trần im lặng, giây (chỉ áp cho engine có phát tiến độ; 0 = tắt)")
    ap.add_argument("--expect", action="append", default=[], metavar="PATH[:MINBYTES]",
                    help="cổng artifact, lặp được; thiếu/nhỏ ⇒ mã 1 dù CLI trả 0")
    ap.add_argument("--no-content-gate", action="store_true",
                    help="tắt cổng chữ nội bộ trên các --expect là bản công khai (.md/.txt/.html)")
    ap.add_argument("--check-text", action="append", default=[], metavar="FILE",
                    help="CHỈ soi chữ nội bộ trong các tệp này rồi thoát (không gọi engine nào); "
                         "sạch ⇒ mã 0, có chữ cấm ⇒ mã 1")
    ap.add_argument("--on-quota", default="fallback", choices=("fallback", "wait", "fail"),
                    help="hết hạn mức thì: đổi engine (mặc định) | chờ tới giờ mở lại | trả mã 4")
    ap.add_argument("--fallback", help="đè chuỗi engine, vd `agy:claude-opus-4-6-thinking,codex:best`")
    ap.add_argument("--engines-config", help="đè đường dẫn engines.json")
    ap.add_argument("--ledger", help="đè đường dẫn sổ JSONL")
    ap.add_argument("--print-text", action="store_true",
                    help="in câu trả lời của agent ra stdout (khi lượt không ghi file)")
    ap.add_argument("--json", action="store_true", help="một dòng JSON cuối stdout")
    return ap


def _doc_prompt(args) -> str:
    if args.prompt_file:
        p = Path(args.prompt_file).expanduser()
        if not p.is_file():
            raise SC.ContractError(f"không có tệp prompt: {p}")
        return p.read_text(encoding="utf-8")
    if sys.stdin is None or sys.stdin.isatty():
        raise SC.ContractError("không có prompt — truyền --prompt-file hoặc đẩy qua stdin")
    return sys.stdin.read()


def _soi_chu(args) -> int:
    """`--check-text` — cổng chữ nội bộ chạy MỘT MÌNH, không gọi engine nào.

    Để `blog_gates`, hook trước khi đăng, hay một người đang rà bằng tay đều dùng được
    cùng MỘT danh sách chữ với lớp gọi. Hai nơi giữ hai danh sách là hai luật.
    """
    thieu = [f for f in args.check_text if not Path(f).expanduser().is_file()]
    if thieu:
        raise SC.ContractError("không có tệp để soi: " + ", ".join(thieu))
    ra = AC.quet_file_cong_khai([str(Path(f).expanduser()) for f in args.check_text],
                                loc_duoi=False)
    for h in ra:
        SC.log(f"[{PROG}] {h['path']}:{h['dong']} chữ nội bộ {h['chu']!r} — {h['trich']}")
    if args.json:
        SC.emit({"ok": not ra, "code": SC.OK if not ra else SC.ENGINE_ERROR,
                 "checked": list(args.check_text), "found": ra})
    if not ra:
        SC.log(f"[{PROG}] sạch: {len(args.check_text)} tệp, 0 chữ nội bộ")
    return SC.OK if not ra else SC.ENGINE_ERROR


def main(argv=None) -> int:
    args, ma = SC.parse(_parser(), argv)
    if args is None:
        return ma
    try:
        if args.check_text:
            return _soi_chu(args)
        if not args.engine:
            raise SC.ContractError("thiếu --engine (hoặc dùng --check-text để chỉ soi chữ)")
        prompt = _doc_prompt(args)
        if not prompt.strip():
            raise SC.ContractError("prompt rỗng")
        cfg = AC.load_config(args.engines_config)
        ra = AC.call(
            prompt, engine=args.engine, model=args.model, tools=args.tools,
            skills=args.skills, skills_mode=args.skills_mode, cwd=args.cwd,
            timeout=args.timeout, stall=args.stall, expect=args.expect,
            on_quota=args.on_quota, fallback=args.fallback, cfg=cfg, ledger=args.ledger,
            content_gate=not args.no_content_gate)
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001 — biên CLI: mọi lỗi phải thành mã thoát
        ma = SC.classify(exc)
        msg = str(exc) or exc.__class__.__name__
        SC.log(f"[{PROG}] LỖI ({ma}): {msg}")
        if args.json:
            SC.emit({"ok": False, "code": ma, "error": msg})
        return ma

    if ra.get("ok") and args.print_text and ra.get("text"):
        # Câu trả lời đi ra stdout TRƯỚC dòng JSON: hợp đồng chỉ đòi JSON là dòng cuối
        # đọc được, và `last_json_line` đọc ngược từ đáy nên phần văn bản phía trên
        # không làm hỏng parse của bên gọi.
        sys.stdout.write(ra["text"].rstrip() + "\n")
    if args.json:
        SC.emit(ra)
    if not ra.get("ok"):
        SC.log(f"[{PROG}] {ra.get('kind')}: {ra.get('error', '')}")
        if ra.get("resets_at"):
            SC.log(f"[{PROG}] hết hạn mức — chạy lại sau {ra['resets_at']}")
    return int(ra.get("code", SC.ENGINE_ERROR))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
