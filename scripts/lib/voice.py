# -*- coding: utf-8 -*-
"""Adapter gọi TRẠM GIỌNG (`agent-voice-studio`) — marketing GỌI, không import.

Đây là phía marketing của hợp đồng ba trạm (§2.4 của kế hoạch chuyển máy). Repo này
không biết gì về bên trong trạm giọng; nó chỉ biết bốn điều, và chỉ bốn điều đó được
phép thay đổi hành vi ở đây:

    1. lệnh      `<python của trạm giọng> -m voice_studio speak …`
    2. mã thoát  0 ok · 1 engine hỏng (thử lại được) · 2 hợp đồng sai · 3 trạm thiếu
    3. kết quả   một dòng JSON cuối stdout; log người đọc ở stderr
    4. biến      VOICE_STATION (tên cũ OMNIVOICE_DIR = thư mục engine) · OMNIVOICE_PY

**Vì sao subprocess chứ không `import voice_studio`:** engine giọng kéo theo torch (vài
GB) và một venv riêng. `import` ở tầng module trói CẢ repo marketing vào venv đó, kể cả
cho việc không dính dáng gì tới giọng — đúng cái bẫy mà bản trước mắc phải: nhét thư mục
engine của một máy vào `sys.path` rồi import module private trong đó.

**Ngoại lệ có chủ đích — `engine()`:** script đọc hàng trăm câu (truyện, beat-sync tin)
gọi CLI từng câu nghĩa là nạp lại model 3 GB từng câu. Những script đó chạy BẰNG python
của trạm giọng và dùng `engine()` để lấy module in-process. `engine()` từ chối khi tiến
trình đang chạy bằng python khác — im lặng nhặt một bản `voice_studio` khác trên máy là
cách tệ nhất để hỏng.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

PROG = "voice-studio"
MODULE = "voice_studio"
STATION_FILE = "station.json"

HUONG_DAN = (
    "Chưa có trạm giọng. Cài `agent-voice-studio` rồi trỏ biến vào nó:\n"
    "  1. git clone <url>/agent-voice-studio ~/Code/agent-voice-studio\n"
    "  2. python -m venv <trạm>/omnivoice/.venv   (trạm mặc định: ~/.voice)\n"
    "  3. <venv>/python -m pip install -e ~/Code/agent-voice-studio\n"
    "  4. <venv>/python -m voice_studio init --station <trạm>\n"
    "  5. đặt VOICE_STATION=<trạm>  (Windows: setx · macOS: khoá EnvironmentVariables "
    "trong plist)\n"
    "Hướng dẫn đầy đủ: skills/voice-routing/references/install-omnivoice.md của repo đó."
)


# ── tìm trạm và tìm python ───────────────────────────────────────────────────────────

def station() -> Path:
    """Gốc trạm giọng, hoặc `StationMissing` kèm hướng dẫn cài.

    Thứ tự phân giải nằm ở `studio_paths.voice_station()` — MỘT chỗ cho cả repo.
    """
    p = SP.voice_station()
    if p is None:
        raise SC.StationMissing(HUONG_DAN)
    return p


def station_config(goc: Path | None = None) -> dict:
    """Nội dung `station.json` của trạm giọng; {} khi chưa có (chưa chạy `init`)."""
    f = (goc or station()) / STATION_FILE
    if not f.is_file():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SC.ContractError(f"{f} hỏng: {e} — sửa tay hoặc chạy lại `voice-studio init`")
    return data if isinstance(data, dict) else {}


def python_in_venv(venv: Path) -> Path | None:
    for con in ("Scripts/python.exe", "Scripts/python", "bin/python3", "bin/python"):
        p = venv.joinpath(*con.split("/"))
        if p.is_file():
            return p
    return None


def python_exe(goc: Path | None = None) -> str:
    """Python của venv trạm giọng: `OMNIVOICE_PY` → `station.json: venv` → dò `omnivoice/.venv`.

    Biến đặt tay thắng `station.json`: máy đang chạy lịch thật khai đường tường minh, và
    một file cấu hình trong trạm không được phép đổi interpreter dưới chân nó.
    """
    bien = (os.environ.get("OMNIVOICE_PY") or "").strip()
    if bien:
        return str(Path(bien).expanduser())
    goc = goc or station()
    ung = []
    khai = str(station_config(goc).get("venv") or "").strip()
    if khai:
        q = Path(khai).expanduser()
        ung.append(q if q.is_absolute() else goc / q)
    ung.append(goc / "omnivoice" / ".venv")
    for venv in ung:
        py = python_in_venv(venv)
        if py:
            return str(py)
    raise SC.StationMissing(
        f"trạm giọng {goc} chưa có venv engine (đã tìm: "
        + ", ".join(str(x) for x in ung)
        + "). Tạo venv rồi `pip install -e agent-voice-studio`, hoặc đặt OMNIVOICE_PY trỏ "
          "đúng python. Xem `doctor`.")


def voices_dir(goc: Path | None = None) -> Path:
    """Kho giọng: `VOICES_DIR` → `<trạm>/<engine_dir>/voices`."""
    bien = (os.environ.get("VOICES_DIR") or "").strip()
    if bien:
        return Path(bien).expanduser()
    goc = goc or station()
    return goc / str(station_config(goc).get("engine_dir") or "omnivoice") / "voices"


# ── lệnh `speak` ─────────────────────────────────────────────────────────────────────

def speak(text: str | None = None, *, file: str | None = None, out: str,
          profile: str | None = None, lang: str | None = None, speed=None, seed=None,
          normalize: bool = False, timeout=None) -> dict:
    """Đọc `text` (hoặc nội dung `file`) thành một file audio tại `out` -> dict kết quả.

    Một lần gọi = một tiến trình = một lần nạp model. Dùng cho MỘT bài; đọc hàng trăm câu
    thì xem `engine()`.

    Không truyền `profile` thì trạm giọng dùng profile mặc định của kho — và nếu kho
    không có mặc định, nó trả mã 2 chứ không bao giờ lùi về một giọng ngẫu nhiên. Ở đây
    KHÔNG có tên profile mặc định: tên giọng là danh tính của người dùng, không phải
    hằng số của engine.
    """
    if bool(text) == bool(file):
        raise SC.ContractError("speak: truyền ĐÚNG MỘT trong `text` hoặc `file`")
    if text is not None and not (text or "").strip():
        raise SC.ContractError("speak: text rỗng")
    if file and not Path(file).is_file():
        raise SC.ContractError(f"speak: không thấy file kịch bản {file}")
    if not (out or "").strip():
        raise SC.ContractError("speak: thiếu `out` (đường file audio ra)")

    argv = [python_exe(), "-m", MODULE, "speak", "--out", str(out)]
    argv += ["--file", str(file)] if file else ["--text", text]
    for co, gia in (("--profile", profile), ("--lang", lang),
                    ("--speed", speed), ("--seed", seed)):
        if gia is not None and str(gia) != "":
            argv += [co, str(gia)]
    if normalize:
        argv.append("--normalize")
    argv.append("--json")
    return SC.call(argv, prog=f"{PROG} speak", timeout=timeout)


# ── ngoại lệ in-process ──────────────────────────────────────────────────────────────

def engine():
    """Module `voice_studio.engine` NGAY TRONG tiến trình này — chỉ cho script đọc nhiều câu.

    Điều kiện: tiến trình phải đang chạy bằng chính python của trạm giọng. Không thoả ⇒
    `ContractError` (sửa cách gọi), chứ không âm thầm `import` một bản khác.
    """
    can = python_exe()
    if Path(sys.executable).resolve() != Path(can).resolve():
        raise SC.ContractError(
            f"`engine()` chỉ dùng được khi chạy bằng python của trạm giọng.\n"
            f"  đang chạy : {sys.executable}\n"
            f"  cần chạy  : {can}  (OMNIVOICE_PY / station.json: venv)\n"
            f"Gọi lại script bằng python đó, hoặc dùng `speak()` (tiến trình con).")
    try:
        import importlib
        return importlib.import_module(f"{MODULE}.engine")
    except ImportError as e:
        raise SC.StationMissing(
            f"python của trạm giọng chưa có `{MODULE}`: {e}\n"
            f"  {can} -m pip install -e <đường dẫn>/agent-voice-studio") from e
