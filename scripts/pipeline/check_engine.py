#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`check_engine` — một câu hỏi, một câu trả lời: `<trạm>/engine` có đang nói dối không?

Luật, hậu quả nếu vi phạm, và lý do mã thoát là 2: xem `scripts/lib/engine_dir.py`. File
này chỉ là vỏ dòng lệnh để chạy được **độc lập** — trên máy thật, trong CI, hay gõ tay
trước khi đụng vào một trạm:

    python scripts/pipeline/check_engine.py                       # trạm đang phân giải
    python scripts/pipeline/check_engine.py --check-station <đường>
    python scripts/pipeline/check_engine.py --station <đường> --json

Mã thoát: 0 hợp lệ · 2 trạm đang ở trạng thái làm chết đường lùi của mọi chiến dịch.

Chỉ ĐỌC: không tạo, không xoá, không sửa gì trong trạm. Một cổng tự sửa là một cổng che
mất chuyện máy đã hỏng cái gì — và ở đây "sửa" có hai cách trái ngược nhau, chỉ người mới
chọn được.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import engine_dir as ED  # noqa: E402
import studio_contract as SC  # noqa: E402

PROG = "check_engine"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog=PROG,
        description="Kiểm luật: <trạm>/engine hoặc KHÔNG tồn tại, hoặc đủ bộ chạy "
                    f"({', '.join(ED.RUNNER_BAT_BUOC)}).")
    # Hai tên cùng trỏ một chỗ: `--station` đồng bộ với `doctor`/`check_tree`, còn
    # `--check-station` là cách gõ tay tự nói ra mình đang làm gì.
    ap.add_argument("--station", "--check-station", dest="station",
                    help="gốc trạm cần khám (mặc định: trạm đang phân giải)")
    ap.add_argument("--json", action="store_true")
    args, ma = SC.parse(ap, argv)
    if args is None:
        return ma

    kq = ED.kiem(args.station)
    SC.log(f"  {PROG}: {kq['engine']}  [{kq['state']}]")
    for x in kq["fail"]:
        SC.log(f"  ĐỎ   {x}")
    if kq["ok"]:
        SC.log("  hợp lệ — " + ("không có thư mục engine, đường lùi còn sống"
                                if kq["state"] == "vang" else "engine đủ bộ chạy"))
    if args.json:
        SC.emit(kq)
    return kq["code"]


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
