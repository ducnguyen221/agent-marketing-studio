# -*- coding: utf-8 -*-
"""truyen_paths.py — MỘT chỗ phân giải đường cho pipeline truyện, chạy được Windows + macOS.

Mọi khác biệt giữa hai máy của pipeline truyện gom về đây (runbook PORTING-WINDOWS-MACOS,
nguyên tắc 1). Các script khác chỉ gọi hàm, không tự ghép `Scripts\\python.exe` hay
`C:\\...` nữa.

    engine_dir()      gốc dữ liệu giọng (venv torch, assets, voices, truyen-out, _vtitles)
                      OMNIVOICE_DIR → <VOICE_STATION>/omnivoice → <trạm giọng theo
                      `studio_paths.voice_station()`: studio.local.json, repo anh em
                      `agent-voice-studio` cùng thư mục cha>/omnivoice → DỪNG, nêu tên biến.
                      OMNIVOICE_DIR thắng vì nó CỤ THỂ hơn (trỏ thẳng engine); test đặt nó
                      để trỏ vào sandbox — nếu VOICE_STATION thắng, test sẽ dọn trạm thật.
    venv_python()     python của venv torch: OMNIVOICE_PY → <engine>/.venv/{Scripts,bin}/python*
                      → `.venv` của repo anh em `agent-video-studio` rồi `agent-voice-studio`
                      → chính interpreter đang chạy (lượt đêm vốn đã chạy bằng venv đó).
    publish_python()  python cho bước đăng (cần google-api-python-client):
                      TRUYEN_PUBLISH_PY → python / python3 / py -3 trên PATH mà import được
                      googleapiclient và ≥ 3.10 → interpreter đang chạy.
    title_font()      font tiêu đề (phải có dấu tiếng Việt): TRUYEN_FONT → <engine>/assets/fonts/
                      title.ttf → font hệ thống theo OS → DỪNG, nói đặt TRUYEN_FONT.
    upload_engine_dir() thư mục chứa youtube_upload.py: `scripts/runners` của repo (cha của
                      thư mục này) → <MARKETING_STUDIO_DATA>/engine → <trạm chứa file này>/engine
                      (bản cũ; chỉ nhận thư mục CÓ youtube_upload.py). CHỈ trả đường — không
                      đọc token/secret nào.

Trên Windows, biến vừa `setx` không tới tiến trình đang chạy: nếu biến tiến trình rỗng thì
đọc thêm registry User (giống Get-EnvVar của engine/brand-paths.ps1). Trên macOS biến phải
khai trong plist launchd.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# `<repo>/scripts/lib` khi file này nằm ở `<repo>/scripts/runners/story/`. Bản cũ trong trạm
# không có repo cạnh bên -> các tầng dùng studio_paths tự bỏ qua.
_LIB = os.path.join(os.path.dirname(os.path.dirname(HERE)), "lib")


def _sp():
    """`studio_paths` của repo, hoặc None (bản cũ trong trạm / thiếu phụ thuộc)."""
    if not os.path.isfile(os.path.join(_LIB, "studio_paths.py")):
        return None
    if _LIB not in sys.path:
        sys.path.insert(0, _LIB)
    try:
        import studio_paths
        return studio_paths
    except Exception:  # noqa: BLE001 — thiếu pyyaml trong venv giọng thì bỏ tầng này, không chết
        return None


def _expand(p):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(str(p))))


def getenv(name, env=None, registry=True):
    """Biến tiến trình; rỗng thì (chỉ Windows) đọc registry HKCU\\Environment."""
    env = os.environ if env is None else env
    v = (env.get(name) or "").strip()
    if v or not registry or sys.platform != "win32":
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, name)
        return str(val or "").strip()
    except OSError:
        return ""


TOKEN_VAR_TRUYEN = "YT_TOKEN_PATH__NGHE_TIEN_TRUYEN"


def token_truyen(env=None, registry=True):
    """ĐƯỜNG token kênh truyện (không mở file): `YT_TOKEN_PATH__NGHE_TIEN_TRUYEN` (tiến trình →
    registry User chỉ trên Windows) THẮNG `YT_TOKEN_PATH` chung (chỉ tiến trình) → "".

    Vì sao biến riêng kênh phải thắng (P3-12): env plist/tác vụ truyện có thể mang
    `YT_TOKEN_PATH` của kênh KHÁC (kênh tin) — chạy tay `truyen_publish.py` trong env đó mà
    ưu tiên biến chung là đăng nhầm kênh. `YT_TOKEN_PATH` chung KHÔNG đọc registry: trên
    Windows registry giữ token của kênh tin, không phải kênh truyện."""
    env_ = os.environ if env is None else env
    v = getenv(TOKEN_VAR_TRUYEN, env, registry) or (env_.get("YT_TOKEN_PATH") or "").strip()
    return os.path.expanduser(v) if v else ""


def engine_dir(env=None, registry=True, sp=None):
    eng = getenv("OMNIVOICE_DIR", env, registry)
    if eng:
        return _expand(eng)
    st = getenv("VOICE_STATION", env, registry)
    if st:
        return os.path.join(_expand(st), "omnivoice")
    # Tầng repo: studio.local.json / repo anh em `agent-voice-studio` cùng thư mục cha. Chỉ
    # khi người gọi dùng môi trường THẬT — test truyền `env` giả thì không được rò ra máy thật.
    SP = sp if sp is not None else (_sp() if env is None else None)
    if SP is not None:
        try:
            goc = SP.voice_station()
        except Exception:  # noqa: BLE001
            goc = None
        if goc:
            return os.path.join(str(goc), "omnivoice")
    raise SystemExit("truyen_paths: không biết trạm giọng ở đâu — đặt VOICE_STATION (gốc trạm "
                     "giọng, vd <repo agent-voice-studio>/workspace) hoặc OMNIVOICE_DIR (thư mục "
                     "engine của trạm đó), ở biến môi trường hoặc <repo>/.env (embedded).")


def _venv_candidates(engine):
    v = os.path.join(engine, ".venv")
    return [os.path.join(v, "Scripts", "python.exe"),   # Windows
            os.path.join(v, "bin", "python3"),          # macOS / Linux
            os.path.join(v, "bin", "python")]


def venv_python(engine, env=None, sp=None):
    override = (os.environ if env is None else env).get("OMNIVOICE_PY")
    if override:
        return _expand(override)
    for c in _venv_candidates(engine):
        if os.path.isfile(c):
            return c
    # `.venv` của repo anh em (bố cục "giọng cài chung venv video" — cùng thứ tự với
    # `scripts/lib/voice.py: python_exe`).
    SP = sp if sp is not None else (_sp() if env is None else None)
    if SP is not None:
        for ten in ("agent-video-studio", "agent-voice-studio"):
            try:
                r = SP.repo_anh_em(ten)
            except Exception:  # noqa: BLE001
                r = None
            if r:
                for c in _venv_candidates(str(r)):
                    if os.path.isfile(c):
                        return c
    return sys.executable


def _probe(argv, timeout=60):
    """Ứng viên chạy được, ≥ 3.10, có googleapiclient? (Windows: python3 có thể là stub Store.)"""
    try:
        r = subprocess.run(argv + ["-c", "import sys, googleapiclient; "
                                         "sys.exit(0 if sys.version_info >= (3, 10) else 1)"],
                           capture_output=True, timeout=timeout)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def publish_python(env=None, probe=_probe):
    """-> argv tiền tố (list) để chạy truyen_publish.py."""
    override = (os.environ if env is None else env).get("TRUYEN_PUBLISH_PY")
    if override:
        return [_expand(override)]
    cands = []
    for name in ("python", "python3"):
        exe = shutil.which(name)
        if exe and [exe] not in cands:
            cands.append([exe])
    py = shutil.which("py")
    if py:
        cands.append([py, "-3"])
    for argv in cands:
        if probe(argv):
            return argv
    return [sys.executable]


def _system_fonts(env=None):
    env = os.environ if env is None else env
    if sys.platform == "win32":
        windir = env.get("WINDIR") or env.get("SystemRoot") or ""
        return [os.path.join(windir, "Fonts", "arialbd.ttf")] if windir else []
    if sys.platform == "darwin":
        return ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf"]
    return ["/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def title_font(engine, env=None, system_fonts=None):
    env = os.environ if env is None else env
    f = env.get("TRUYEN_FONT")
    if f:
        f = _expand(f)
        if os.path.isfile(f):
            return f
        raise SystemExit(f"truyen_paths: TRUYEN_FONT trỏ tới file không có: {f}")
    cands = [os.path.join(engine, "assets", "fonts", "title.ttf")]
    cands += _system_fonts(env) if system_fonts is None else system_fonts
    for c in cands:
        if os.path.isfile(c):
            return c
    raise SystemExit("truyen_paths: không tìm thấy font tiêu đề (cần font có dấu tiếng Việt). "
                     "Đặt TRUYEN_FONT trỏ tới một .ttf, hoặc chép vào <engine>/assets/fonts/title.ttf. "
                     "Đã thử: " + " | ".join(cands))


def upload_engine_dir(env=None, registry=True, home=None, here=None):
    cands = [os.path.normpath(os.path.join(here or HERE, ".."))]      # repo: scripts/runners
    data = getenv("MARKETING_STUDIO_DATA", env, registry)
    if data:
        cands.append(os.path.join(_expand(data), "engine"))
    cands.append(os.path.normpath(os.path.join(here or HERE, "..", "engine")))
    for c in cands:
        if os.path.isfile(os.path.join(c, "youtube_upload.py")):
            return c
    return cands[0]      # không có ở đâu: trả ứng viên đầu, import sẽ nổ nói rõ thiếu module
