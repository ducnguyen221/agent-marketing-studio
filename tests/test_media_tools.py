# -*- coding: utf-8 -*-
"""`scripts/lib/media_tools.py` — tìm Chrome, ffmpeg/ffprobe, font trên CẢ Windows lẫn macOS.

Vì sao có file này: ba script dựng hình (`gen_infographic.py`, `make_podcast_video.py`,
`blog_gates.py`) chỉ biết đường của Windows. Trên Mac chúng hỏng theo ba kiểu khác nhau:

· **Chrome** chỉ dò `C:\\Program Files\\…\\chrome.exe` ⇒ ảnh bìa rơi về Pillow trong im
  lặng (vẫn ra PNG, chỉ xấu hơn — không ai thấy), còn video podcast nổ hẳn.
· **ffmpeg** dò `<thư mục>/ffmpeg.exe` ⇒ trên Mac không bao giờ có đuôi `.exe`.
· **font** dò `segoeuib.ttf`/`arialbd.ttf` theo TÊN — Pillow chỉ tự tìm theo tên trên
  Windows, nên Mac rơi về font bitmap mặc định, mất dấu tiếng Việt.

Test giả `platform.system()` thay vì cần một cái Mac thật: máy chạy CI Windows vẫn chặn
được lỗi quên nhánh macOS. Các đường tuyệt đối của Mac không tồn tại trên máy chạy test,
nên "file có tồn tại không" được giả qua `MT._la_file`.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import media_tools as MT  # noqa: E402

MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MAC_EDGE = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
MAC_ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

BIEN = ("CHROME_BIN", "FFMPEG_DIR", "FFPROBE", "VIDEO_FONT")


@pytest.fixture
def may(monkeypatch):
    """Giả một máy: hệ điều hành + tập file đang có + PATH. Gỡ sạch biến của đợt này."""
    for b in BIEN:
        monkeypatch.delenv(b, raising=False)

    class May:
        files: set = set()
        path: dict = {}

        def dung(self, he):
            monkeypatch.setattr(MT.platform, "system", lambda: he)
            return self

    m = May()
    m.files, m.path = set(), {}
    monkeypatch.setattr(MT, "_la_file", lambda p: str(p) in m.files)
    monkeypatch.setattr(MT, "_which", lambda n: m.path.get(n))
    return m


# ── Chrome ──────────────────────────────────────────────────────────────────

def test_mac_chon_chrome_trong_goi_app(may):
    may.dung("Darwin").files |= {MAC_CHROME, MAC_EDGE}
    assert MT.find_chrome() == MAC_CHROME


def test_mac_khong_co_chrome_thi_lui_ve_edge_app(may):
    may.dung("Darwin").files |= {MAC_EDGE}
    assert MT.find_chrome() == MAC_EDGE


def test_mac_KHONG_do_duong_windows(may):
    """Máy Mac có sẵn một file trùng tên đường Windows (không thể, nhưng chặn lỗi logic):
    danh sách dò phải theo hệ điều hành, không phải một danh sách chung."""
    may.dung("Darwin")
    assert not any(c.lower().endswith(".exe") for c in MT.chrome_candidates())


def test_CHROME_BIN_thang_moi_duong_do(may, monkeypatch):
    may.dung("Darwin").files |= {MAC_CHROME, "/opt/chrome-rieng"}
    monkeypatch.setenv("CHROME_BIN", "/opt/chrome-rieng")
    assert MT.find_chrome() == "/opt/chrome-rieng"


def test_CHROME_BIN_khai_ma_hong_thi_DUNG_khong_lang_le_doi(may, monkeypatch, capsys):
    """Khai biến là ý định. Biến trỏ sai mà lặng lẽ dùng Chrome khác thì người khai không
    bao giờ biết cấu hình của mình không có tác dụng."""
    may.dung("Darwin").files |= {MAC_CHROME}
    monkeypatch.setenv("CHROME_BIN", "/khong/co/chrome")
    assert MT.find_chrome() is None
    assert "CHROME_BIN" in capsys.readouterr().err


def test_CHROME_BIN_la_ten_lenh_tren_PATH(may, monkeypatch):
    may.dung("Linux").path["chromium"] = "/usr/bin/chromium"
    monkeypatch.setenv("CHROME_BIN", "chromium")
    assert MT.find_chrome() == "/usr/bin/chromium"


def test_windows_giu_nguyen_duong_cu(may):
    may.dung("Windows")
    c = MT.chrome_candidates()
    assert any(x.endswith("chrome.exe") for x in c) and any(x.endswith("msedge.exe") for x in c)


def test_khong_co_gi_thi_hoi_PATH(may):
    may.dung("Linux").path["google-chrome"] = "/usr/bin/google-chrome"
    assert MT.find_chrome() == "/usr/bin/google-chrome"


# ── ffmpeg / ffprobe ────────────────────────────────────────────────────────

def test_mac_FFMPEG_DIR_khong_them_duoi_exe(may, monkeypatch):
    may.dung("Darwin").files |= {str(Path("/opt/ff") / "ffmpeg")}
    monkeypatch.setenv("FFMPEG_DIR", "/opt/ff")
    assert MT.ff_tool("ffmpeg") == str(Path("/opt/ff") / "ffmpeg")


def test_windows_FFMPEG_DIR_them_duoi_exe(may, monkeypatch):
    dich = str(Path("D:/ff") / "ffprobe.exe")
    may.dung("Windows").files |= {dich}
    monkeypatch.setenv("FFMPEG_DIR", "D:/ff")
    assert MT.ff_tool("ffprobe") == dich


def test_mac_launchd_khong_co_homebrew_tren_PATH(may):
    """launchd chạy với PATH tối giản, không có `/opt/homebrew/bin` ⇒ phải tự dò."""
    may.dung("Darwin").files |= {"/opt/homebrew/bin/ffprobe"}
    assert MT.ff_tool("ffprobe") == "/opt/homebrew/bin/ffprobe"


def test_PATH_thang_duong_homebrew(may):
    may.dung("Darwin").files |= {"/opt/homebrew/bin/ffmpeg"}
    may.path["ffmpeg"] = "/usr/local/bin/ffmpeg"
    assert MT.ff_tool("ffmpeg") == "/usr/local/bin/ffmpeg"


def test_FFPROBE_thang_FFMPEG_DIR(may, monkeypatch):
    may.dung("Darwin").files |= {str(Path("/opt/ff") / "ffprobe")}
    monkeypatch.setenv("FFMPEG_DIR", "/opt/ff")
    monkeypatch.setenv("FFPROBE", "/x/ffprobe-rieng")
    assert MT.ff_tool("ffprobe") == "/x/ffprobe-rieng"


def test_khong_tim_thay_thi_tra_ten_tran(may):
    may.dung("Darwin")
    assert MT.ff_tool("ffmpeg") == "ffmpeg"


# ── font ────────────────────────────────────────────────────────────────────

def test_mac_font_Arial_trong_Supplemental(may):
    may.dung("Darwin")
    assert MT.font_candidates(bold=True)[0] == MAC_ARIAL_BOLD
    assert MT.font_candidates(bold=False)[0].endswith("Supplemental/Arial.ttf")


def test_VIDEO_FONT_dung_dau(may, monkeypatch):
    may.dung("Darwin")
    monkeypatch.setenv("VIDEO_FONT", "/fonts/Inter-Bold.ttf")
    assert MT.font_candidates(bold=True)[0] == "/fonts/Inter-Bold.ttf"


def test_windows_font_giu_ten_cu(may):
    may.dung("Windows")
    assert MT.font_candidates(bold=True)[:2] == ["segoeuib.ttf", "arialbd.ttf"]


# ── file:// URL ─────────────────────────────────────────────────────────────

def test_file_url_khong_bon_gach(tmp_path):
    """`"file:///" + "/var/…"` = `file:////var/…` trên Mac. Chrome có khi đọc được, có khi
    không — đúng kiểu hỏng không ai đoán ra."""
    p = tmp_path / "có dấu cách" / "s.html"
    u = MT.file_url(str(p))
    assert u.startswith("file:///") and not u.startswith("file:////"), u
    assert " " not in u


# ── Ba script dùng CHUNG module, không còn bản dò riêng ─────────────────────

def test_gen_infographic_tim_chrome_mac(may):
    import gen_infographic as GI
    may.dung("Darwin").files |= {MAC_CHROME}
    assert GI._find_chrome() == MAC_CHROME


def test_make_podcast_video_tim_chrome_va_ffmpeg_mac(may, monkeypatch):
    import make_podcast_video as MPV
    may.dung("Darwin").files |= {MAC_CHROME, str(Path("/opt/ff") / "ffmpeg")}
    monkeypatch.setenv("FFMPEG_DIR", "/opt/ff")
    assert MPV._find_chrome() == MAC_CHROME
    assert MPV._ff("ffmpeg") == str(Path("/opt/ff") / "ffmpeg")


def test_blog_gates_ffprobe_qua_FFMPEG_DIR(may, monkeypatch, tmp_path):
    import blog_gates as BG
    goi = []

    class Ra:
        returncode, stdout = 0, "12.5\n"

    monkeypatch.setattr(BG.subprocess, "run", lambda argv, **kw: goi.append(argv) or Ra())
    may.dung("Darwin").files |= {str(Path("/opt/ff") / "ffprobe")}
    monkeypatch.setenv("FFMPEG_DIR", "/opt/ff")
    assert BG._thoi_luong(tmp_path / "a.mp3") == 12.5
    assert goi[0][0] == str(Path("/opt/ff") / "ffprobe")


def test_khong_con_danh_sach_chrome_rieng_trong_script():
    """Một nguồn dò duy nhất. Hai bản dò song song là hai chỗ phải nhớ sửa khi có máy mới."""
    for ten in ("gen_infographic.py", "make_podcast_video.py"):
        t = (ROOT / "scripts" / "pipeline" / ten).read_text(encoding="utf-8")
        assert "CHROME_CANDIDATES" not in t and "chrome.exe" not in t, ten
