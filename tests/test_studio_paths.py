# -*- coding: utf-8 -*-
"""Test cho studio_paths — phân giải 4 tầng.

Điều quan trọng nhất phải giữ: KÊNH NẰM NGOÀI STATION vẫn tìm được. Nếu script dò thư mục
thay vì đọc CHANNELS.md thì kênh ngoài trở nên vô hình, và nó vô hình một cách IM LẶNG —
lệnh chạy xong, chỉ là không thấy kênh đó đâu.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import md_io as M  # noqa: E402
import studio_paths as SP  # noqa: E402


def _dung_cay(tmp_path, path_kenh_ngoai=None):
    """STATION có 1 kênh trong, tuỳ chọn thêm 1 kênh NGOÀI STATION."""
    station = tmp_path / "station"
    (station / "trong-nha").mkdir(parents=True)
    (station / "trong-nha" / "channel.yml").write_text("id: trong-nha\n", encoding="utf-8")
    ds = [{"id": "trong-nha", "label": "Trong nhà", "path": "./trong-nha", "status": "active"}]
    if path_kenh_ngoai:
        path_kenh_ngoai.mkdir(parents=True)
        (path_kenh_ngoai / "channel.yml").write_text("id: ngoai-nha\n", encoding="utf-8")
        ds.append({"id": "ngoai-nha", "label": "Ngoài nhà",
                   "path": str(path_kenh_ngoai).replace("\\", "/"), "status": "active"})
    M.write_fm(station / "CHANNELS.md", {"schema": "channels/1", "channels": ds}, "# Sổ kênh\n")
    return station


def test_tim_duoc_kenh_NGOAI_station(tmp_path):
    """Ca quan trọng nhất: kênh để ở ổ/thư mục khác."""
    ngoai = tmp_path / "noi-khac" / "ngoai-nha"
    station = _dung_cay(tmp_path, ngoai)
    ids = [c["id"] for c in SP.channels(station)]
    assert ids == ["trong-nha", "ngoai-nha"]
    assert SP.channel_dir("ngoai-nha", station) == ngoai.resolve()
    assert ngoai.resolve() not in station.resolve().parents, "kênh này thật sự nằm ngoài STATION"


def test_duong_tuong_doi_tinh_theo_CHANNELS_md(tmp_path):
    station = _dung_cay(tmp_path)
    assert SP.channel_dir("trong-nha", station) == (station / "trong-nha").resolve()


def test_station_rong_khong_phai_loi(tmp_path):
    assert SP.channels(tmp_path / "chua-co-gi") == []


def test_kenh_khong_khai_thi_bao_loi_ro_rang(tmp_path):
    station = _dung_cay(tmp_path)
    with pytest.raises(KeyError, match="CHANNELS"):
        SP.channel_dir("khong-ton-tai", station)


def test_di_len_tim_theo_FILE_MOC_khong_dem_cap(tmp_path):
    """Lồng thêm một cấp thư mục vẫn phải tìm ra — đếm cấp là giả định sẽ sai."""
    d = tmp_path / "k" / "CMP-1" / "BAI-001" / "facebook" / "sau" / "nua"
    d.mkdir(parents=True)
    (tmp_path / "k" / "channel.yml").write_text("id: k\n", encoding="utf-8")
    (tmp_path / "k" / "CMP-1" / "campaign.md").write_text("---\nid: CMP-1\n---\n", encoding="utf-8")
    assert SP.channel_of(d) == (tmp_path / "k").resolve()
    assert SP.campaign_of(d) == (tmp_path / "k" / "CMP-1").resolve()


def test_liet_ke_campaign_va_bai(tmp_path):
    k = tmp_path / "k"
    (k / "CMP-1" / "AST-001_x").mkdir(parents=True)
    (k / "channel.yml").write_text("id: k\n", encoding="utf-8")
    (k / "CMP-1" / "campaign.md").write_text("---\nid: CMP-1\n---\n", encoding="utf-8")
    (k / "CMP-1" / "AST-001_x" / "meta.json").write_text("{}", encoding="utf-8")
    (k / "CMP-1" / "khong-phai-bai").mkdir()          # không có meta.json
    assert [p.name for p in SP.campaigns(k)] == ["CMP-1"]
    assert [p.name for p in SP.posts(k / "CMP-1")] == ["AST-001_x"]


def test_post_id_theo_nen_tang():
    assert SP.post_id("AST-001", "youtube", "youtube_video") == "AST-001-yt"
    assert SP.post_id("AST-001", "facebook", "facebook_post") == "AST-001-fb"
    assert SP.post_id("AST-001", "web_blog", "blog_article") == "AST-001-web"


def test_cap_chua_khai_thi_no_loi_chu_khong_doan():
    with pytest.raises(KeyError, match="HAU_TO"):
        SP.post_id("AST-001", "tiktok", "tiktok_video")


# ══════════════════════════════════════════════════════════════════════════════════════
# F17.3 — MỘT thứ tự phân giải dùng chung cho mọi script (hai chế độ cài embedded/separate)
#
# Thứ tự phải đo được từng nhánh, vì mỗi nhánh là một cách người dùng có thể đã cài:
#   --station → MARKETING_STUDIO_DATA → studio.local.json → <repo>/workspace/ → ~/.marketing
# Nhánh nào lặng lẽ nhảy cóc thì người dùng mất trạm mà không có thông báo nào.
# ══════════════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def repo_gia(tmp_path, monkeypatch):
    """Một 'repo' giả + nhà giả. Mọi biến của hợp đồng bị gỡ sạch trước mỗi test."""
    repo = tmp_path / "repo"
    (repo / "scripts" / "lib").mkdir(parents=True)
    (repo / "install.ps1").write_text("", encoding="utf-8")
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(repo))
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))      # Path.home() trên Windows đọc cái này
    for b in ("MARKETING_STUDIO_DATA", "VOICE_STATION", "OMNIVOICE_DIR",
              "VIDEO_STATION", "VIDEO_ROOT"):
        monkeypatch.delenv(b, raising=False)
    return repo


def _ghi_local(repo, **kw):
    import json
    (repo / SP.LOCAL_CONFIG).write_text(json.dumps(kw, ensure_ascii=False), encoding="utf-8")


def test_repo_root_theo_MARKETING_STUDIO_HOME(repo_gia):
    assert SP.repo_root() == repo_gia.resolve()


def test_nhanh_1_tham_so_station_thang_tat_ca(repo_gia, tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tmp_path / "bien"))
    _ghi_local(repo_gia, mode="separate", station_path=str(tmp_path / "local"))
    (repo_gia / SP.WORKSPACE).mkdir()
    st, nguon = SP.resolve_station(tmp_path / "tay")
    assert st == (tmp_path / "tay").resolve() and nguon == "--station"
    assert SP.root(tmp_path / "tay") == (tmp_path / "tay").resolve()


def test_nhanh_2_bien_moi_truong_THANG_studio_local_json(repo_gia, tmp_path, monkeypatch):
    """Máy Đức: biến đã đặt từ trước; một studio.local.json lạc vào repo không được cướp trạm."""
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tmp_path / "bien"))
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE)
    (repo_gia / SP.WORKSPACE).mkdir()
    st, nguon = SP.resolve_station()
    assert st == (tmp_path / "bien").resolve() and nguon == "MARKETING_STUDIO_DATA"


def test_nhanh_3_studio_local_json(repo_gia, tmp_path):
    _ghi_local(repo_gia, mode="separate", station_path=str(tmp_path / "ngoai"))
    st, nguon = SP.resolve_station()
    assert st == (tmp_path / "ngoai").resolve() and nguon == SP.LOCAL_CONFIG


def test_nhanh_3b_station_path_tuong_doi_tinh_theo_REPO(repo_gia):
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE)
    st, nguon = SP.resolve_station()
    assert st == (repo_gia / SP.WORKSPACE).resolve() and nguon == SP.LOCAL_CONFIG


def test_nhanh_4_workspace_co_that(repo_gia):
    (repo_gia / SP.WORKSPACE).mkdir()
    st, nguon = SP.resolve_station()
    assert st == (repo_gia / SP.WORKSPACE).resolve() and nguon == SP.WORKSPACE


def test_nhanh_5_mac_dinh_home_marketing(repo_gia, tmp_path):
    st, nguon = SP.resolve_station()
    assert st == (tmp_path / "nha" / ".marketing").resolve() and nguon == "default"


def test_workspace_KHONG_ton_tai_thi_khong_chon(repo_gia, tmp_path):
    """Chỉ `workspace/` CÓ THẬT mới được chọn — không thì im lặng tạo trạm rỗng trong repo."""
    st, _ = SP.resolve_station()
    assert st != (repo_gia / SP.WORKSPACE).resolve()


def test_studio_local_json_hong_thi_bao_loi_chu_khong_nuot(repo_gia):
    (repo_gia / SP.LOCAL_CONFIG).write_text("{khong phai json", encoding="utf-8")
    with pytest.raises(SP.StudioPathsError, match=SP.LOCAL_CONFIG):
        SP.resolve_station()


# ── secret: biến môi trường → <repo>/.env (CHỈ embedded) → kho secret của máy ──────────

def test_secret_bien_moi_truong_thang_file_env(repo_gia, monkeypatch):
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE)
    (repo_gia / ".env").write_text("TG_CONFIG=tu-file\n", encoding="utf-8")
    monkeypatch.setenv("TG_CONFIG", "tu-bien")
    assert SP.secret_env("TG_CONFIG") == "tu-bien"


def test_secret_doc_file_env_khi_embedded(repo_gia, monkeypatch):
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE)
    (repo_gia / ".env").write_text(
        "# chu thich\n\nexport TG_CONFIG = \"D:/kho/tg.json\"  \nRONG=\n", encoding="utf-8")
    monkeypatch.delenv("TG_CONFIG", raising=False)
    assert SP.secret_env("TG_CONFIG") == "D:/kho/tg.json"
    assert SP.secret_env("RONG") is None
    assert SP.secret_env("KHONG_CO") is None


def test_secret_KHONG_doc_file_env_khi_separate(repo_gia, monkeypatch):
    """`separate` = repo có thể là repo public của chính người dùng: không bao giờ tự nạp .env."""
    _ghi_local(repo_gia, mode="separate", station_path="/noi/khac")
    (repo_gia / ".env").write_text("TG_CONFIG=tu-file\n", encoding="utf-8")
    monkeypatch.delenv("TG_CONFIG", raising=False)
    assert SP.secret_env("TG_CONFIG") is None
    assert SP.env_file() is None


def test_env_file_chi_co_khi_embedded_va_file_ton_tai(repo_gia):
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE)
    assert SP.env_file() is None                      # chưa có file
    (repo_gia / ".env").write_text("", encoding="utf-8")
    assert SP.env_file() == repo_gia / ".env"


# ── trạm giọng / trạm video (hợp đồng ba trạm §2.4a) ──────────────────────────────────

def test_voice_station_bien_moi_truong_roi_ten_cu_roi_local(repo_gia, tmp_path, monkeypatch):
    assert SP.voice_station() is None
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE,
               voice_station=str(tmp_path / "tu-local"))
    assert SP.voice_station() == (tmp_path / "tu-local").resolve()
    monkeypatch.setenv("OMNIVOICE_DIR", str(tmp_path / "giong" / "omnivoice"))
    assert SP.voice_station() == (tmp_path / "giong").resolve()   # tên CŨ = thư mục ENGINE
    monkeypatch.setenv("VOICE_STATION", str(tmp_path / "giong-moi"))
    assert SP.voice_station() == (tmp_path / "giong-moi").resolve()


def test_video_station_bien_moi_truong_roi_ten_cu_roi_local(repo_gia, tmp_path, monkeypatch):
    assert SP.video_station() is None
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE,
               video_station=str(tmp_path / "tu-local"))
    assert SP.video_station() == (tmp_path / "tu-local").resolve()
    monkeypatch.setenv("VIDEO_ROOT", str(tmp_path / "video-cu"))
    assert SP.video_station() == (tmp_path / "video-cu").resolve()
    monkeypatch.setenv("VIDEO_STATION", str(tmp_path / "video-moi"))
    assert SP.video_station() == (tmp_path / "video-moi").resolve()


def test_mode_doc_tu_studio_local_json(repo_gia):
    assert SP.mode() is None
    _ghi_local(repo_gia, mode="embedded", station_path=SP.WORKSPACE)
    assert SP.mode() == "embedded"


# ══ REVIEW-P2 N11 — chế độ `embedded` HỨA đọc `.env` thì phải đọc thật ══════
# Trước 20/09 chỉ `TG_CONFIG` đi qua `secret_env`; ~18 biến còn lại đọc thẳng `os.environ`.
# Người cài `embedded` điền `VOICE_STATION=` vào `.env`, `doctor` vẫn báo "chưa khai
# VOICE_STATION" và không gì giải thích vì sao. Fail-closed nên không mất dữ liệu — nhưng
# nó làm người dùng mất buổi chiều.

@pytest.fixture
def repo_embedded(tmp_path, monkeypatch):
    """Một bản clone giả ở chế độ `embedded`, có `.env`."""
    repo = tmp_path / "repo"
    (repo / "scripts" / "lib").mkdir(parents=True)
    (repo / "install.ps1").write_text("x", encoding="utf-8")
    (repo / SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "embedded"}), encoding="utf-8")
    for b in ("VOICE_STATION", "OMNIVOICE_DIR", "VIDEO_STATION", "VIDEO_ROOT",
              "OMNIVOICE_PY", "HYPERFRAMES_VERSION", "WEB_REPO_DIR", "VOICES_DIR"):
        monkeypatch.delenv(b, raising=False)
    return repo


@pytest.mark.parametrize("bien, doc", [
    ("VOICE_STATION", lambda r: SP.voice_station(r)),
    ("VIDEO_STATION", lambda r: SP.video_station(r)),
])
def test_bien_tram_nang_luc_doc_duoc_tu_env(repo_embedded, tmp_path, bien, doc):
    dich = tmp_path / "tram-ngoai"
    dich.mkdir()
    (repo_embedded / ".env").write_text(f"{bien}={dich}\n", encoding="utf-8")
    assert doc(repo_embedded) == dich.resolve(), f"{bien} khai trong .env mà không ai đọc"


def test_bien_moi_truong_van_THANG_env_file(repo_embedded, tmp_path, monkeypatch):
    """Thứ tự của `secret_env` không đổi: biến môi trường trước, `.env` là đường lùi."""
    a, b = tmp_path / "tu-bien", tmp_path / "tu-env"
    a.mkdir(); b.mkdir()
    (repo_embedded / ".env").write_text(f"VOICE_STATION={b}\n", encoding="utf-8")
    monkeypatch.setenv("VOICE_STATION", str(a))
    assert SP.voice_station(repo_embedded) == a.resolve()


def test_che_do_separate_KHONG_doc_env_cua_repo(repo_embedded, tmp_path):
    """`.env` là cơ chế của riêng `embedded`. Ở `separate`, repo có thể là bản public."""
    (repo_embedded / SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "separate",
                                                             "station": str(tmp_path / "t")}),
                                                 encoding="utf-8")
    (repo_embedded / ".env").write_text(f"VOICE_STATION={tmp_path}\n", encoding="utf-8")
    assert SP.voice_station(repo_embedded) is None


# ══ `embedded` phải THẬT SỰ "clone là chạy" (chỉ đạo 21/09/2026) ═══════════════════
#
# `.env.example` chia hai khối: "đường dẫn tới file bí mật" và "CẤU HÌNH MÁY". Bộ cài
# `embedded` chép nguyên file đó thành `<repo>/.env` và nói "điền vào đây là xong". Lời
# hứa đó chỉ đúng với biến đi qua `studio_paths.secret_env`; biến đọc thẳng `os.environ`
# thì điền vào `.env` **không có tác dụng gì** — và không có gì báo, vì mọi nhánh đều có
# đường lùi hợp lệ (dò Chrome trên PATH, dùng font hệ thống, engines.json mặc định).
# Người dùng chỉ biết khi sản phẩm ra sai font, hoặc lượt render dùng nhầm engine.
#
# Khối CẤU HÌNH MÁY nằm dưới đây. Khối bí mật (YT_TOKEN_PATH, FB_CONFIG, YT_CLIENT_SECRET)
# KHÔNG nằm ở đây có chủ đích: chúng do hook đăng bài của chính người dùng đọc, trong một
# tiến trình con nhận môi trường thật — `.env` không với tới được, và `doctor` nói thẳng
# điều đó thay vì để người dùng tự đoán.

CAU_HINH_MAY_QUA_ENV = ("CHROME_BIN", "FFMPEG_DIR", "FFPROBE", "VIDEO_FONT",
                        "AGENT_CALL_ENGINES", "TG_CHAT", "OPCOS_CODEX_BRIDGE")


@pytest.fixture
def repo_env(repo_embedded, monkeypatch):
    """`repo_embedded` + biến `MARKETING_STUDIO_HOME` trỏ vào nó, để các module khác
    (media_tools, agent_call…) tự tìm ra đúng bản clone này khi gọi `secret_env`."""
    for b in CAU_HINH_MAY_QUA_ENV:
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(repo_embedded))

    class Repo:
        goc = repo_embedded

        @staticmethod
        def viet(**khoa):
            noi_dung = "".join(f"{k}={v}\n" for k, v in khoa.items())
            (repo_embedded / ".env").write_text(noi_dung, encoding="utf-8")

    return Repo


@pytest.mark.parametrize("bien", CAU_HINH_MAY_QUA_ENV)
def test_moi_bien_CAU_HINH_MAY_deu_doc_duoc_tu_env(repo_env, bien):
    """Cổng của cổng: biến nào lọt khỏi `secret_env` thì đỏ ngay ở đây, trước khi ai kịp
    tin vào `.env`."""
    repo_env.viet(**{bien: "gia-tri-thu"})
    assert SP.secret_env(bien) == "gia-tri-thu"


def test_CHROME_BIN_khai_trong_env_thi_media_tools_dung_no(repo_env, tmp_path):
    chrome = tmp_path / "chrome-gia.exe"
    chrome.write_text("", encoding="utf-8")
    repo_env.viet(CHROME_BIN=str(chrome))
    import media_tools as MT
    assert MT.find_chrome() == str(chrome)


def test_FFPROBE_va_FFMPEG_DIR_khai_trong_env_thi_media_tools_dung_no(repo_env, tmp_path):
    import media_tools as MT
    duoi = ".exe" if MT._he() == "Windows" else ""
    thu_muc = tmp_path / "ff"
    thu_muc.mkdir()
    (thu_muc / ("ffmpeg" + duoi)).write_text("", encoding="utf-8")
    probe = tmp_path / ("ffprobe-rieng" + duoi)
    probe.write_text("", encoding="utf-8")
    repo_env.viet(FFMPEG_DIR=str(thu_muc), FFPROBE=str(probe))
    assert MT.ff_tool("ffprobe") == str(probe)
    assert MT.ff_tool("ffmpeg") == str(thu_muc / ("ffmpeg" + duoi))


def test_VIDEO_FONT_khai_trong_env_thi_dung_dau_danh_sach(repo_env):
    repo_env.viet(VIDEO_FONT="D:/fonts/Inter-Bold.ttf")
    import media_tools as MT
    assert MT.font_candidates()[0] == "D:/fonts/Inter-Bold.ttf"


def test_AGENT_CALL_ENGINES_khai_trong_env_thi_agent_call_dung_no(repo_env, tmp_path):
    f = tmp_path / "engines-cua-toi.json"
    repo_env.viet(AGENT_CALL_ENGINES=str(f))
    import agent_call as AC
    assert AC.config_path() == f


def test_TG_CHAT_khai_trong_env_thi_bot_chon_dung_chat(repo_env):
    repo_env.viet(TG_CHAT="kenh-rieng")
    import telegram_io as TI
    bot = TI.Bot.__new__(TI.Bot)
    bot._chats = {"mac_dinh": {"chat_id": 1}, "kenh-rieng": {"chat_id": 2}}
    bot.log_path = Path("x")
    assert bot._chat() == 2


def test_OPCOS_CODEX_BRIDGE_khai_trong_env_thi_thanh_mac_dinh_cua_co(repo_env):
    repo_env.viet(OPCOS_CODEX_BRIDGE="D:/cau/cli.mjs")
    sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import make_fb_image as MF
    assert str(MF._bridge_mac_dinh()) == str(Path("D:/cau/cli.mjs"))
