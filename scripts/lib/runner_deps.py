# -*- coding: utf-8 -*-
"""Những gì BỘ CHẠY tin/truyện (`scripts/runners/`) cần mà repo không tự cài — một chỗ để
`doctor` KIỂM, không phải để cài.

Bộ chạy đứng trên bốn thứ ngoài repo, và cả bốn từng làm lượt thật chết giữa chừng trên máy
mới (Mac mini, 30/09/2026) sau khi đã tốn `claude -p` và TTS:

    1. gói Python trong VENV GIỌNG (`OMNIVOICE_PY`) — nơi runner gọi upload YouTube, đọc
       truyện, ghi Excel. Khai ở `requirements-runners.txt`; thiếu thì lượt đỏ ở bước đăng.
    2. script nghiên cứu `last30days` (plugin Claude) — lớp cài máy cài, repo này chỉ TÌM.
    3. thư viện nhạc nền — style khai trong `bgm-library.json` mà thiếu mp3 thì engine giọng
       ném lỗi ở bước dựng. KHÔNG có lệnh sinh nhạc: thiếu là việc của người vận hành.
    4. `claude` CLI — `doctor` không được gọi `claude -p` (tốn lượt, cần đăng nhập), nên đăng
       nhập là NOT_CHECKED kèm lệnh tự kiểm.

Mọi hàm ở đây CHỈ ĐỌC. Thứ tự tìm last30days giống hệt `Find-Last30Days` (brand-paths.ps1).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402

REQ_FILE = "requirements-runners.txt"
# Tên IMPORT (không phải tên gói pip) — đúng thứ runner `import`, KỂ CẢ thứ nạp bằng TÊN
# CHUỖI (parser `BeautifulSoup(…, "lxml")` — P0-7: thiếu `lxml` thì lượt truyện chết ở bước
# đọc chương mà doctor vẫn báo đủ). Giữ khớp REQ_FILE: cổng `tests/test_runner_deps.py` so hai
# danh sách và quét mã `scripts/runners/**` để không import/parser nào lọt ngoài danh sách.
MODULES = ("googleapiclient", "google_auth_oauthlib", "google_auth_httplib2", "httplib2",
           "requests", "bs4", "lxml", "yt_dlp", "openpyxl", "faster_whisper")
# Runner tin/truyện của repo: chiến dịch khai một trong các tên này thì `doctor` kiểm bộ trên.
RUNNER_TIN = ("run-toptoday-hot.ps1", "run-weekly-news.ps1", "run-weekly-repo.ps1")
RUNNER_TRUYEN = ("run-daily-truyen.ps1",)
_DUOI_L30 = Path("skills") / "last30days" / "scripts" / "last30days.py"


def runner_dang_dung(station) -> set[str]:
    """Tên runner (`runtime.runner`) mà các chiến dịch của trạm đang khai. Trạm rỗng -> set()."""
    ra: set[str] = set()
    try:
        kenh = SP.channels(station)
    except Exception:  # noqa: BLE001 — CHANNELS.md hỏng thì phần khác của doctor đã báo
        return ra
    for c in kenh:
        d = Path(c["dir"])
        if not d.is_dir():
            continue
        for cd in SP.campaigns(d):
            try:
                fm, _ = md_io.read_fm(cd / SP.MOC_CHIEN_DICH)
            except Exception:  # noqa: BLE001
                continue
            r = str(((fm or {}).get("runtime") or {}).get("runner") or "").strip()
            if r:
                ra.add(r)
    return ra


def tim_last30days(env=None, home=None) -> Path | None:
    """L30_SCRIPT (env → `<repo>/.env`) → `<CLAUDE_CONFIG_DIR|~/.claude>/plugins/marketplaces/*/
    skills/last30days/scripts/last30days.py` → `.../plugins/cache/*/last30days/<bản mới nhất>/...`."""
    env = os.environ if env is None else env
    v = (env.get("L30_SCRIPT") or (SP.secret_env("L30_SCRIPT") if env is os.environ else "")
         or "").strip()
    if v:
        p = Path(v).expanduser()
        return p if p.is_file() else None
    goc = (env.get("CLAUDE_CONFIG_DIR") or "").strip()
    plug = (Path(goc).expanduser() if goc else Path(home or Path.home()) / ".claude") / "plugins"
    mk = plug / "marketplaces"
    if mk.is_dir():
        for d in sorted(x for x in mk.iterdir() if x.is_dir()):
            if (d / _DUOI_L30).is_file():
                return d / _DUOI_L30
    ca = plug / "cache"
    ung = []
    if ca.is_dir():
        for d in ca.iterdir():
            l30 = d / "last30days"
            if l30.is_dir():
                for b in l30.iterdir():
                    if (b / _DUOI_L30).is_file():
                        ung.append((_ban(b.name), b / _DUOI_L30))
    return max(ung)[1] if ung else None


def _ban(ten: str) -> tuple:
    so = [int(x) for x in re.findall(r"\d+", ten)[:4]]
    return tuple(so + [0] * (4 - len(so)))


def thieu_module(py: str, modules=MODULES) -> list[str] | None:
    """Module nào python `py` KHÔNG import được. None = không chạy nổi python đó."""
    ma = ("import importlib.util, json\n"
          f"print(json.dumps([m for m in {list(modules)!r} "
          "if importlib.util.find_spec(m) is None]))\n")
    try:
        r = subprocess.run([py, "-c", ma], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        return list(json.loads((r.stdout or "").strip().splitlines()[-1]))
    except (ValueError, IndexError):
        return None


def thu_muc_nhac_nen() -> Path | None:
    """VOICE_BGM_DIR (env → `<repo>/.env`) → `<trạm video>/assets/news-bgm` — cùng thứ tự runner."""
    v = (SP.secret_env("VOICE_BGM_DIR") or "").strip()
    if v:
        return Path(v).expanduser()
    video = SP.video_station()
    return (video / "assets" / "news-bgm") if video else None


def kiem_nhac_nen(d: Path | None) -> dict:
    """-> {dir, co_thu_vien, styles, thieu_mp3}. Chỉ đọc."""
    ra = {"dir": str(d) if d else None, "co_thu_vien": False, "styles": [], "thieu_mp3": []}
    if not d:
        return ra
    f = Path(d) / "bgm-library.json"
    try:
        lib = json.loads(f.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ra
    ra["co_thu_vien"] = True
    for s in lib.get("styles") or []:
        ten = str((s or {}).get("name") or "").strip()
        if not ten:
            continue
        ra["styles"].append(ten)
        if not (Path(d) / f"{ten}.mp3").is_file():
            ra["thieu_mp3"].append(ten)
    return ra


def doc_requirements(repo: Path) -> list[str]:
    """Tên gói (chữ thường) trong `requirements-runners.txt`, bỏ chú thích và ràng buộc bản."""
    f = Path(repo) / REQ_FILE
    ra = []
    for dong in f.read_text(encoding="utf-8").splitlines():
        d = dong.split("#", 1)[0].strip()
        if d:
            ra.append(re.split(r"[<>=!~\[; ]", d, maxsplit=1)[0].strip().lower())
    return ra
