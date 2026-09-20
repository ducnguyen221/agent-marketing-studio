# -*- coding: utf-8 -*-
"""Adapter gọi TRẠM VIDEO (`agent-video-studio`) — marketing GỌI, không import.

Cùng hợp đồng với `voice.py` (§2.4): lệnh ổn định · mã thoát 0/1/2/3 · một dòng JSON
cuối stdout · biến môi trường định vị trạm. Một người viết script chỉ phải học một lần.

    <python> -m video_studio render --project <tên> --input spec.json --out <thư mục>
             [--brand brand.json] [--voice-profile <tên>] --json

**Python nào chạy nó:** mặc định là python của TRẠM GIỌNG. `video_studio` được cài
`pip install -e` vào chính venv đó, vì torch là phụ thuộc nặng duy nhất và cả hai đều
cần (phương án A của §2.4b). Ai cố ý tách venv riêng cho render câm thì khai khoá `venv`
trong `station.json` của trạm video, và adapter theo khai báo đó.

**Spec là hợp đồng dữ liệu, không phải tham số dòng lệnh:** marketing sinh một file JSON
(có `schema_version`, `brand`, `voice`, `outputs`…) rồi đưa đường dẫn. `brand` là BẮT
BUỘC ở phía trạm video — thiếu là mã 2, không có đường lùi im lặng, vì một mặc định ở
đây nghĩa là video mang danh tính của người khác.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402
import voice as V  # noqa: E402

PROG = "video-studio"
MODULE = "video_studio"
STATION_FILE = "station.json"

HUONG_DAN = (
    "Chưa có trạm video. Cài `agent-video-studio` rồi trỏ biến vào nó:\n"
    "  1. git clone <url>/agent-video-studio ~/Code/agent-video-studio\n"
    "  2. <python của trạm giọng> -m pip install -e ~/Code/agent-video-studio\n"
    "     (cùng venv với trạm giọng — xem docs/INSTALL.md của repo đó)\n"
    "  3. <python đó> -m video_studio init --station <trạm>   (trạm mặc định: ~/.video)\n"
    "  4. đặt VIDEO_STATION=<trạm>  (Windows: setx · macOS: khoá EnvironmentVariables "
    "trong plist)\n"
    "Cần thêm: Node ≥ 22 (npx), ffmpeg + ffprobe. `video-studio doctor` liệt kê đủ."
)


def station() -> Path:
    """Gốc trạm video, hoặc `StationMissing` kèm hướng dẫn cài."""
    p = SP.video_station()
    if p is None:
        raise SC.StationMissing(HUONG_DAN)
    return p


def station_config(goc: Path | None = None) -> dict:
    f = (goc or station()) / STATION_FILE
    if not f.is_file():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SC.ContractError(f"{f} hỏng: {e} — sửa tay hoặc chạy lại `video-studio init`")
    return data if isinstance(data, dict) else {}


def python_exe(goc: Path | None = None) -> str:
    """`station.json: venv` của trạm video (nếu khai) → python của trạm giọng.

    Không có biến `VIDEO_STUDIO_PY`: thêm một biến nữa cho cùng một câu hỏi là thêm một
    chỗ để hai câu trả lời trôi khỏi nhau.
    """
    goc = goc or station()
    khai = str(station_config(goc).get("venv") or "").strip()
    if khai:
        q = Path(khai).expanduser()
        venv = q if q.is_absolute() else goc / q
        py = V.python_in_venv(venv)
        if py:
            return str(py)
        raise SC.StationMissing(
            f"{goc / STATION_FILE} khai venv {khai!r} nhưng không thấy python trong {venv}")
    return V.python_exe()


def render(project: str, spec_path: str, out_dir: str, *, brand: str | None = None,
           voice_profile: str | None = None, timeout=None) -> dict:
    """Render một spec JSON thành video -> dict kết quả (`outputs`, `timings`, `engine`).

    `project` là tên template của trạm video (`news`, `news-weekly`, `topstory`,
    `repo-today`). Adapter KHÔNG kiểm tên đó theo một danh sách chép tay: danh sách
    template thuộc về trạm video và sẽ dài thêm ở đó, nên chép sang đây là tự hẹn một
    ngày "project hợp lệ" bị chặn bởi bản sao lạc hậu. Tên lạ ⇒ trạm video trả mã 2.
    """
    if not (project or "").strip():
        raise SC.ContractError("render: thiếu `project` (tên template của trạm video)")
    if not (spec_path or "").strip() or not Path(spec_path).is_file():
        raise SC.ContractError(f"render: không thấy file spec {spec_path!r}")
    if not (out_dir or "").strip():
        raise SC.ContractError("render: thiếu `out_dir`")
    if brand and not Path(brand).is_file():
        raise SC.ContractError(f"render: không thấy file brand {brand!r}")

    argv = [python_exe(), "-m", MODULE, "render", "--project", str(project),
            "--input", str(spec_path), "--out", str(out_dir)]
    if brand:
        argv += ["--brand", str(brand)]
    if voice_profile:
        argv += ["--voice-profile", str(voice_profile)]
    argv.append("--json")
    return SC.call(argv, prog=f"{PROG} render", timeout=timeout)


def hyperframes_version(goc: Path | None = None) -> str | None:
    """Bản HyperFrames trạm video đang ghim (`HYPERFRAMES_VERSION` → `station.json`).

    Để `doctor` và báo cáo nói được "engine nào đã dựng video này" mà không phải gọi
    tiến trình con.
    """
    bien = (SP.secret_env("HYPERFRAMES_VERSION") or "").strip()
    if bien:
        return bien
    try:
        v = station_config(goc).get("hyperframes_version")
    except SC.StudioError:
        return None
    return str(v) if v else None
