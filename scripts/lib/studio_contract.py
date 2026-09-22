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
import re
import subprocess
import sys
import traceback
from pathlib import Path

OK, ENGINE_ERROR, CONTRACT_ERROR, STATION_MISSING = 0, 1, 2, 3

__all__ = [
    "OK", "ENGINE_ERROR", "CONTRACT_ERROR", "STATION_MISSING",
    "StudioError", "EngineError", "ContractError", "StationMissing",
    "log", "emit", "run", "parse", "classify",
    "last_json_line", "call", "min_version",
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


LOAI_LOI = {ENGINE_ERROR: EngineError, CONTRACT_ERROR: ContractError,
            STATION_MISSING: StationMissing}


def last_json_line(stdout: str):
    """Dòng JSON cuối của stdout -> dict, hoặc None khi không có dòng nào đọc được.

    Đi NGƯỢC từ cuối lên và lấy object JSON đầu tiên gặp được. Hợp đồng nói "dòng cuối",
    nhưng thư viện bên thứ ba vẫn in thanh tiến trình ra stdout, và đôi khi in SAU cả
    dòng kết quả. Đọc ngược chịu được cả hai phía; đọc đúng một dòng cuối thì một dòng
    rác duy nhất làm hỏng cả lượt render mất hàng giờ.
    """
    for dong in reversed((stdout or "").splitlines()):
        d = dong.strip()
        if not (d.startswith("{") and d.endswith("}")):
            continue
        try:
            data = json.loads(d)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def call(argv, *, prog: str, timeout=None, env=None, cwd=None) -> dict:
    """Gọi một CLI theo hợp đồng ba trạm -> dict kết quả; mã thoát ≠ 0 thành exception.

    `argv` là DANH SÁCH, không bao giờ là chuỗi: không `shell=True`, không tự ghép lệnh.
    Một đường dẫn có dấu cách hay dấu `&` đi qua shell là một lệnh khác hẳn lệnh ta định
    chạy, và đường dẫn ở đây do người dùng đặt.

    stderr KHÔNG gộp vào stdout: gộp là trộn log người đọc vào chỗ máy đọc, đúng cái
    hợp đồng tách ra.
    """
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env, cwd=cwd)
    except FileNotFoundError as e:
        raise StationMissing(f"không chạy được {argv[0]!r} ({prog}): {e}") from e
    except subprocess.TimeoutExpired as e:
        raise EngineError(f"{prog} quá {timeout}s chưa xong — đã giết tiến trình") from e
    except OSError as e:
        raise EngineError(f"không chạy được {prog}: {e}") from e

    data = last_json_line(p.stdout)
    if p.returncode == OK:
        if data is None:
            goi = argv[argv.index("-m") + 1] if "-m" in argv[:-1] else argv[0]
            raise ContractError(
                f"{prog} trả mã 0 nhưng stdout KHÔNG có dòng JSON nào — bản {goi} đang cài quá "
                f"cũ, hoặc chưa hiểu `--json`. Chạy `doctor` để so phiên bản hợp đồng.")
        return data
    msg = (data or {}).get("error") or _duoi_log(p.stderr) or f"{prog} thoát với mã {p.returncode}"
    loai = LOAI_LOI.get(p.returncode)
    if loai is None:
        raise EngineError(f"{prog} thoát với mã {p.returncode} (ngoài hợp đồng 0/1/2/3): {msg}")
    raise loai(msg)


def _duoi_log(stderr: str, dong=6) -> str:
    co = [d for d in (stderr or "").splitlines() if d.strip()]
    return "\n".join(co[-dong:])


_NGUONG = re.compile(r"^\s*([A-Za-z_][\w.-]*)\s*>=\s*([0-9][0-9A-Za-z.\-+]*)\s*$")


def min_version(loai: str):
    """-> (tên package, chuỗi phiên bản tối thiểu) đọc từ `requirements-<loai>.txt`.

    Ngưỡng hợp đồng là DỮ LIỆU trong repo, không phải hằng số nằm trong mã: nâng hợp đồng
    là sửa một dòng văn bản, và `git log` của file đó kể lại lịch sử ngưỡng.
    """
    f = Path(__file__).resolve().parents[2] / f"requirements-{loai}.txt"
    if not f.is_file():
        raise ContractError(f"thiếu {f.name} — không biết trạm {loai} phải từ bản nào trở lên")
    for dong in f.read_text(encoding="utf-8").splitlines():
        if dong.lstrip().startswith("#"):
            continue
        m = _NGUONG.match(dong)
        if m:
            return m.group(1), m.group(2)
    raise ContractError(f"{f.name} không có dòng `<package>>=<phiên bản>` nào")


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
