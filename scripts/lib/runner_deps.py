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
           "requests", "bs4", "lxml", "yt_dlp", "openpyxl", "faster_whisper", "av")
# Runner tin/truyện của repo: chiến dịch khai một trong các tên này thì `doctor` kiểm bộ trên.
RUNNER_TIN = ("run-toptoday-hot.ps1", "run-weekly-news.ps1", "run-weekly-repo.ps1")
RUNNER_TRUYEN = ("run-daily-truyen.ps1",)
# Runner RIÊNG của chiến dịch (file `.ps1` nằm trong thư mục chiến dịch, vd truyện P2 khai
# `run-daily-truyen-p2.ps1`) là truyện khi nó gọi engine truyện. Không dò dấu này thì `doctor`
# không biết trạm có truyện, và mọi phép kiểm truyện bên dưới im lặng (P0-9 lọt như thế).
DAU_TRUYEN = ("daily_truyen", "run-daily-truyen")
# Điểm vào DUY NHẤT của mọi chiến dịch chạy theo lịch: plist launchd gọi
# `<trạm>/<kênh>/<chiến dịch>/run.ps1`; `run.ps1` đọc `runtime.runner` rồi gọi runner. Bản mẫu:
RUN_PS1 = "run.ps1"
MAU_RUN_PS1 = Path("templates") / "station" / "_channel" / "_campaign" / RUN_PS1
_DUOI_L30 = Path("skills") / "last30days" / "scripts" / "last30days.py"


def chien_dich_co_runner(station) -> list[dict]:
    """Mọi chiến dịch khai `runtime.runner` -> [{dir, runner, truyen}]. Trạm rỗng -> []."""
    ra: list[dict] = []
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
                ra.append({"dir": cd, "runner": r, "truyen": la_truyen(cd, r)})
    return ra


def la_truyen(cd: Path, runner: str) -> bool:
    """Runner của repo tên `run-daily-truyen.ps1`, hoặc runner riêng trong thư mục chiến dịch
    mà mã của nó gọi engine truyện (`DAU_TRUYEN`)."""
    if runner in RUNNER_TRUYEN:
        return True
    f = Path(cd) / runner
    try:
        ma = f.read_text(encoding="utf-8-sig", errors="replace") if f.is_file() else ""
    except OSError:
        return False
    return any(x in ma for x in DAU_TRUYEN)


def runner_dang_dung(station) -> set[str]:
    """Tên runner (`runtime.runner`) mà các chiến dịch của trạm đang khai, cộng
    `run-daily-truyen.ps1` khi có chiến dịch truyện dùng runner riêng. Trạm rỗng -> set()."""
    ra: set[str] = set()
    for c in chien_dich_co_runner(station):
        ra.add(c["runner"])
        if c["truyen"]:
            ra.add(RUNNER_TRUYEN[0])
    return ra


RUNNER_TUAN = "run-weekly-news.ps1"


def kenh_can_gh(station) -> list[str]:
    """Kênh có chiến dịch chạy `run-weekly-news.ps1` VÀ khai `brand.gh_repo` trong `channel.yml`.

    Bản tin tuần có nhánh dự phòng "YouTube không dùng được ⇒ đăng video lên GitHub Release" — nhánh
    đó gọi lệnh `gh`. Mac mini chưa cài `gh` (P4-RUNS P5-KIEM-TRA-LICH 03/10/2026): nhánh chưa từng
    chạy thật, nhưng chạy là hỏng. -> [id kênh]. Đọc hỏng gì thì bỏ qua kênh đó (check_tree báo).
    """
    try:
        import yaml
    except ImportError:
        return []
    tuan = {Path(c["dir"]).resolve() for c in chien_dich_co_runner(station) if c["runner"] == RUNNER_TUAN}
    if not tuan:
        return []
    ra = []
    try:
        kenh = SP.channels(station)
    except Exception:  # noqa: BLE001
        return []
    for c in kenh:
        d = Path(c.get("dir") or "")
        try:
            if not any(d.resolve() in cd.parents for cd in tuan):
                continue
            data = yaml.safe_load((d / SP.MOC_KENH).read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        brand = data.get("brand") if isinstance(data, dict) else None
        if isinstance(brand, dict) and str(brand.get("gh_repo") or "").strip():
            ra.append(str(c.get("id") or d.name))
    return ra


def lenh_scaffold_run_ps1(repo, dich: Path) -> str:
    """Lệnh chép `run.ps1` mẫu vào thư mục chiến dịch — theo shell của máy đang chạy."""
    mau = (Path(repo) / MAU_RUN_PS1) if repo else MAU_RUN_PS1
    if os.name == "nt":
        return f'Copy-Item "{mau}" "{Path(dich) / RUN_PS1}"'
    return f'cp "{mau}" "{Path(dich) / RUN_PS1}"'


# ══ ffmpeg — ĐỦ BỘ LỌC, không chỉ "có lệnh" (P0-9) ═══════════════════════════════════════
#
# Sự cố (Mac mini, 01/10/2026): `brew install ffmpeg` (core) không còn freetype/libass ⇒ không
# có `drawtext`/`subtitles`/`ass`. Lượt truyện đọc xong 10 chương (6 h 58) rồi chết ở
# `make_video.py` pass 1: `No such filter: 'drawtext'`. `doctor` khi đó chỉ hỏi có lệnh ffmpeg.
BO_LOC_TRUYEN = ("drawtext", "subtitles", "ass")
_DONG_BO_LOC = re.compile(r"^\s*[A-Z.|]{2,4}\s+([A-Za-z0-9_]+)\s+\S+->\S+", re.M)


def ten_bo_loc(van_ban: str) -> set[str]:
    """Tên bộ lọc trong đầu ra `ffmpeg -hide_banner -filters`."""
    return set(_DONG_BO_LOC.findall(van_ban or ""))


def ffmpeg_thieu_bo_loc(ffmpeg: str, can=BO_LOC_TRUYEN) -> list[str] | None:
    """Bộ lọc nào trong `can` mà `ffmpeg` KHÔNG có. None = không chạy được ffmpeg đó."""
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    co = ten_bo_loc(r.stdout)
    if r.returncode != 0 or not co:
        return None
    return [x for x in can if x not in co]


def lenh_cai_ffmpeg(he: str | None = None) -> str:
    """Cách cài ffmpeg CÓ libfreetype + libass theo hệ điều hành."""
    he = he or sys.platform
    if he == "darwin":
        return ("brew install ffmpeg-full — bản keg-only, KHÔNG tự lên PATH; repo tự dò "
                "/opt/homebrew/opt/ffmpeg-full/bin, hoặc đặt FFMPEG_DIR trỏ tới đó "
                "(launchd.json `vars`). `brew install ffmpeg` (core) thiếu drawtext/libass.")
    if he == "win32":
        return ("bản Gyan FULL: `winget install Gyan.FFmpeg` (hoặc `choco install ffmpeg-full`), "
                "rồi đặt FFMPEG_DIR trỏ tới thư mục bin nếu nó chưa lên PATH.")
    return "cài ffmpeg build kèm --enable-libfreetype --enable-libass (gói distro thường đủ)."


# ══ faster-whisper + PyAV — kiểm HÀNH VI, không chỉ import (P0-8) ═══════════════════════
#
# Import được không chứng minh chạy được: PyAV 19 import ngon, rồi `decode_audio` ném
# `TypeError` vì faster-whisper truyền tham số PyAV 19 đã bỏ. Phép kiểm dưới gọi đúng hàm
# `read_story.py` gọi, trên một wav 1 giây sinh bằng thư viện chuẩn (không cần ffmpeg).
_MA_DECODE = r"""
import os, sys, tempfile, wave, struct
from faster_whisper.audio import decode_audio
d = tempfile.mkdtemp()
f = os.path.join(d, "1s.wav")
w = wave.open(f, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
w.writeframes(struct.pack("<16000h", *([0] * 16000))); w.close()
try:
    a = decode_audio(f, sampling_rate=16000)
finally:
    os.remove(f); os.rmdir(d)
n = len(a)
print("DECODE_OK %d" % n if 15000 <= n <= 17000 else "DECODE_SAI %d mau" % n)
"""


def kiem_decode_audio(py: str) -> tuple[bool | None, str]:
    """-> (True, chi tiết) · (False, lỗi đọc được) · (None, không chạy nổi python đó)."""
    try:
        r = subprocess.run([py, "-c", _MA_DECODE], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"{e.__class__.__name__}: {e}"
    ra = (r.stdout or "").strip().splitlines()
    if r.returncode == 0 and ra and ra[-1].startswith("DECODE_OK"):
        return True, ra[-1]
    loi = [x for x in (r.stderr or "").strip().splitlines() if x.strip()]
    return False, (loi[-1] if loi else (ra[-1] if ra else f"mã {r.returncode}"))[:300]


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
