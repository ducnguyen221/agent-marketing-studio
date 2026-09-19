# -*- coding: utf-8 -*-
"""Hợp đồng gọi giữa ba trạm năng lực: mã thoát, lỗi có tên, một dòng JSON cuối stdout.

Ba repo — `agent-marketing-studio`, `agent-voice-studio`, `agent-video-studio` — gọi qua
lại nhau bằng tiến trình con. Bên gọi không đọc được ngăn xếp Python của bên kia; thứ duy
nhất nó thấy là **mã thoát** và **stdout**. Nên hai thứ đó phải là hợp đồng, giống nhau ở
cả ba repo (bản của trạm giọng: `voice_studio/contract.py`).

    0  ok
    1  lỗi engine / render — chạy lại có thể được (hết VRAM, ffmpeg sập, mạng chập)
    2  hợp đồng sai — thiếu tham số, thiếu `brand`, cần người chọn mà không có ai:
       phải SỬA CẤU HÌNH, chạy lại nguyên trạng là vô ích
    3  trạm thiếu — chưa có trạm, chưa cài repo kia: phải CÀI TIẾP (`doctor` chỉ bước còn lại)

Phân biệt 1 với 2 không phải chuyện thẩm mỹ: lịch chạy tự động **thử lại** mã 1 và **không**
thử lại mã 2. Trả nhầm là hoặc mất một lượt đáng lẽ cứu được, hoặc lặp vô ích một lỗi cấu hình.

Với `--json`: stdout kết thúc bằng ĐÚNG MỘT dòng JSON (`{"ok": true, …}` hoặc
`{"ok": false, "code": N, "error": "…"}`); mọi log cho người đọc đi ra **stderr**. Bên gọi
lấy dòng cuối không rỗng của stdout — log lạc vào stdout phía trước vẫn không làm hỏng parse.

Bẫy PowerShell 5.1: đừng `2>&1` khi gọi lệnh native — mỗi dòng stderr bị bọc thành lỗi và
`$?` thành False dù mã thoát là 0. Đọc `$LASTEXITCODE`.
"""
from __future__ import annotations

import json
import sys
import traceback

OK, ENGINE_ERROR, CONTRACT_ERROR, STATION_MISSING = 0, 1, 2, 3

__all__ = [
    "OK", "ENGINE_ERROR", "CONTRACT_ERROR", "STATION_MISSING",
    "StudioError", "EngineError", "ContractError", "StationMissing",
    "log", "emit", "run", "parse", "classify",
]


class StudioError(Exception):
    code = ENGINE_ERROR


class EngineError(StudioError):
    """Công cụ/render hỏng giữa chừng — thử lại có thể qua."""
    code = ENGINE_ERROR


class ContractError(StudioError):
    """Bên gọi truyền sai, hoặc cấu hình thiếu: sửa rồi mới chạy lại được."""
    code = CONTRACT_ERROR


class StationMissing(StudioError):
    """Trạm hoặc repo năng lực chưa cài — `doctor` chỉ ra bước còn thiếu."""
    code = STATION_MISSING


def log(*phan):
    """Log cho người đọc: LUÔN ra stderr, để stdout chỉ còn kết quả máy đọc."""
    print(*phan, file=sys.stderr, flush=True)


def emit(payload):
    """In một dòng JSON (UTF-8, không escape tiếng Việt) ra stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def classify(exc) -> int:
    """Map một exception về mã thoát của hợp đồng."""
    if isinstance(exc, StudioError):
        return exc.code
    if isinstance(exc, (FileNotFoundError, NotADirectoryError)):
        return STATION_MISSING
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return CONTRACT_ERROR
    return ENGINE_ERROR


def run(fn, args, as_json=False) -> int:
    """Chạy `fn(args) -> dict`, trả mã thoát; `as_json` ⇒ in dòng JSON cuối stdout."""
    try:
        ra = fn(args) or {}
    except KeyboardInterrupt:
        raise
    except Exception as exc:      # noqa: BLE001 — biên của CLI: mọi lỗi phải thành mã thoát
        ma = classify(exc)
        msg = str(exc) or exc.__class__.__name__
        log(f"[{getattr(args, 'prog', 'studio')}] LỖI ({ma}): {msg}")
        if ma == ENGINE_ERROR:
            log(traceback.format_exc().rstrip())
        if as_json:
            emit({"ok": False, "code": ma, "error": msg})
        return ma
    if as_json:
        emit({"ok": True, **ra})
    return OK


def parse(ap, argv=None):
    """argparse theo hợp đồng: -> (args, None) hoặc (None, mã thoát).

    `--help` ⇒ mã 0; tham số sai ⇒ mã 2 (kèm dòng JSON lỗi nếu người gọi xin `--json`),
    thay vì để `SystemExit` của argparse lọt ra ngoài và thành mã thoát 2 không có JSON.
    """
    try:
        return ap.parse_args(argv), None
    except SystemExit as e:
        if e.code in (0, None):
            return None, OK
        tho = sys.argv[1:] if argv is None else list(argv)
        if "--json" in tho:
            emit({"ok": False, "code": CONTRACT_ERROR, "error": "tham số không hợp lệ (xem stderr)"})
        return None, CONTRACT_ERROR
