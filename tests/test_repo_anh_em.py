# -*- coding: utf-8 -*-
"""Nhận diện theo THƯ MỤC CHA — repo anh em, trạm của chúng, python của venv, repo web.

Vì sao có file này (Đức, 30/09/2026): "cài ở một máy tính mới ở folder bất kỳ nó vẫn phải
nhận diện được, không hard code mà phải theo folder cha — gọi là repo hay code đều phải
được". Máy Windows clone các repo vào thư mục `Code`, Mac vào `Repo`; bản trước viết cứng tên
`Code` ở năm chỗ và Mac phải ghi đè tay ba dòng `channel.yml` + khai `MARKETING_STUDIO_HOME`.

Mọi test đặt các repo dưới `tmp_path/xyz/` — một thư mục cha tên BẤT KỲ — và đặt tên thư
mục clone khác tên repo (`giong-cua-toi`): nhận diện phải đi bằng nội dung
(`pyproject.toml: name`), không bằng tên thư mục nào.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402
import voice as V  # noqa: E402

BIEN = ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "VIDEO_STATION", "VIDEO_ROOT",
        "WEB_REPO_DIR", "MARKETING_STUDIO_DATA")


@pytest.fixture(autouse=True)
def _sach_bien(monkeypatch):
    for b in BIEN:
        monkeypatch.delenv(b, raising=False)


def _anh_em(cha: Path, thu_muc: str, ten: str, *, workspace=True, venv=False,
            local: dict | None = None) -> Path:
    """Một bản clone giả của repo `ten`, đặt ở `<cha>/<thu_muc>`."""
    r = cha / thu_muc
    r.mkdir(parents=True)
    (r / "pyproject.toml").write_text(f'[project]\nname = "{ten}"\nversion = "0.0.0"\n',
                                      encoding="utf-8")
    if workspace:
        (r / "workspace").mkdir()
        (r / "workspace" / "station.json").write_text("{}", encoding="utf-8")
    if local is not None:
        (r / "studio.local.json").write_text(json.dumps(local), encoding="utf-8")
    if venv:
        con = "Scripts" if os.name == "nt" else "bin"
        ten_py = "python.exe" if os.name == "nt" else "python"
        (r / ".venv" / con).mkdir(parents=True)
        (r / ".venv" / con / ten_py).write_bytes(b"")
    return r


# ── repo anh em: nhận bằng NỘI DUNG, trong thư mục cha tên bất kỳ ─────────────────────

def test_tim_duoc_anh_em_ten_thu_muc_bat_ky(repo_gia):
    cha = repo_gia.parent
    assert cha.name == "xyz"
    g = _anh_em(cha, "giong-cua-toi", SP.REPO_GIONG)
    v = _anh_em(cha, "dung-hinh", SP.REPO_VIDEO)
    assert SP.repo_anh_em(SP.REPO_GIONG) == g.resolve()
    assert SP.repo_anh_em(SP.REPO_VIDEO) == v.resolve()


def test_thu_muc_TRUNG_TEN_ma_khong_phai_repo_do_thi_KHONG_nhan(repo_gia):
    _anh_em(repo_gia.parent, SP.REPO_GIONG, "mot-du-an-khac")
    assert SP.repo_anh_em(SP.REPO_GIONG) is None
    assert SP.voice_station() is None


def test_tram_giong_video_theo_anh_em_embedded(repo_gia):
    g = _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG,
                local={"mode": "embedded", "station_path": "workspace"})
    v = _anh_em(repo_gia.parent, "video", SP.REPO_VIDEO)
    assert SP.voice_station() == (g / "workspace").resolve()
    assert SP.video_station() == (v / "workspace").resolve()


def test_anh_em_chon_tram_NGOAI_thi_theo_lua_chon_do(repo_gia, tmp_path):
    ngoai = tmp_path / "tram-giong-o-cho-khac"
    ngoai.mkdir()
    _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG, workspace=False,
            local={"mode": "separate", "station_path": str(ngoai)})
    assert SP.voice_station() == ngoai.resolve()


def test_anh_em_CHUA_init_thi_chua_co_tram_khong_doan(repo_gia):
    _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG, workspace=False)
    assert SP.voice_station() is None


def test_bien_va_studio_local_DUNG_TRUOC_anh_em(repo_gia, tmp_path, monkeypatch):
    _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG)
    khai = tmp_path / "khai-trong-local"
    khai.mkdir()
    (repo_gia / "studio.local.json").write_text(json.dumps({"voice_station": str(khai)}),
                                               encoding="utf-8")
    assert SP.voice_station() == khai.resolve()
    bien = tmp_path / "khai-bang-bien"
    bien.mkdir()
    monkeypatch.setenv("VOICE_STATION", str(bien))
    assert SP.voice_station() == bien.resolve()


def test_KHONG_co_anh_em_thi_fail_closed_kem_huong_dan(repo_gia):
    """Không biến, không `.env`, không anh em ⇒ "chưa bật" + hướng dẫn clone vào CÙNG thư
    mục cha — không đoán một thư mục trong nhà, không nhắc tên thư mục của máy nào."""
    assert SP.voice_station() is None and SP.video_station() is None
    with pytest.raises(SC.StationMissing) as e:
        V.station()
    loi = str(e.value)
    assert "thư mục cha" in loi and "agent-voice-studio" in loi and "VOICE_STATION" in loi
    for cam in ("~/" + "Code", "~/.voice", "~/Repo"):     # ghép: cổng literal quét cả file này
        assert cam not in loi, loi


# ── OMNIVOICE_PY: python của venv anh em ──────────────────────────────────────────────

def test_python_giong_lay_venv_cua_anh_em_VIDEO_truoc(repo_gia):
    g = _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG, venv=True)
    v = _anh_em(repo_gia.parent, "video", SP.REPO_VIDEO, venv=True)
    py = Path(V.python_exe(g / "workspace"))
    assert v.resolve() in py.parents, py


def test_python_giong_khong_co_video_thi_lay_venv_cua_anh_em_GIONG(repo_gia):
    g = _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG, venv=True)
    py = Path(V.python_exe(g / "workspace"))
    assert g.resolve() in py.parents, py


def test_python_giong_OMNIVOICE_PY_thang_anh_em(repo_gia, monkeypatch):
    _anh_em(repo_gia.parent, "video", SP.REPO_VIDEO, venv=True)
    monkeypatch.setenv("OMNIVOICE_PY", sys.executable)
    assert V.python_exe(repo_gia) == sys.executable


def test_python_giong_khong_venv_nao_thi_StationMissing(repo_gia):
    g = _anh_em(repo_gia.parent, "giong", SP.REPO_GIONG)
    with pytest.raises(SC.StationMissing) as e:
        V.python_exe(g / "workspace")
    assert "OMNIVOICE_PY" in str(e.value)


# ── đường repo web: ${BIEN} và tương đối theo thư mục cha ──────────────────────────────

def test_repo_web_TUONG_DOI_tinh_theo_thu_muc_cha(repo_gia):
    assert SP.duong_repo_web("news/ai") == (repo_gia.parent / "news" / "ai").resolve()


def test_repo_web_bien_trong_moi_truong(repo_gia, tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_REPO_DIR", str(tmp_path / "web"))
    assert SP.duong_repo_web("${WEB_REPO_DIR}/ai") == (tmp_path / "web" / "ai").resolve()


def test_repo_web_bien_trong_env_cua_repo_embedded(repo_gia, tmp_path):
    (repo_gia / "studio.local.json").write_text(json.dumps({"mode": "embedded"}),
                                               encoding="utf-8")
    (repo_gia / ".env").write_text("WEB_REPO_DIR=" + (tmp_path / "w").as_posix() + "\n",
                                   encoding="utf-8")
    assert SP.duong_repo_web("${WEB_REPO_DIR}/data") == (tmp_path / "w" / "data").resolve()


def test_repo_web_bien_CHUA_DAT_thi_loi_neu_ten_bien(repo_gia):
    with pytest.raises(SP.StudioPathsError) as e:
        SP.duong_repo_web("${WEB_REPO_DIR}/ai", nguon="kenh/channel.yml: brand.repo")
    assert "WEB_REPO_DIR" in str(e.value) and "brand.repo" in str(e.value)


def test_repo_web_tuyet_doi_va_nha_giu_nguyen(repo_gia, tmp_path):
    assert SP.duong_repo_web(str(tmp_path / "abc")) == (tmp_path / "abc").resolve()
    assert SP.duong_repo_web("~/web-x") == (Path.home() / "web-x").resolve()


def _kenh_co_repo(tram: Path, repo_khai: str) -> Path:
    cam = tram / "kenh" / "cd"
    cam.mkdir(parents=True)
    (tram / "kenh" / "channel.yml").write_text(
        "schema: channel/1\nid: kenh\nlabel: K\nbrand:\n  repo: " + repo_khai + "\n",
        encoding="utf-8")
    (cam / "campaign.md").write_text(
        "---\nschema: campaign/1\nid: cd\nchannel: kenh\n"
        "runtime:\n  label: L\n  runner: r.ps1\n---\n", encoding="utf-8")
    return cam


def test_ban_chup_campaign_cfg_mang_repo_da_NO_cho_PowerShell(repo_gia, tmp_path):
    """Runner PowerShell đọc `repo` từ bản chụp — nó không phải tự hiểu `${…}` hay tương đối."""
    cam = _kenh_co_repo(tmp_path / "tram", "news/ai")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "campaign_cfg.py"),
                        "--campaign", str(cam)], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert Path(d["repo"]) == (repo_gia.parent / "news" / "ai").resolve()
    assert d["repo_khai"] == "news/ai"


def test_ban_chup_bien_chua_dat_thi_ma_2(repo_gia, tmp_path):
    cam = _kenh_co_repo(tmp_path / "tram", "${WEB_REPO_DIR}/ai")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "campaign_cfg.py"),
                        "--campaign", str(cam)], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 2 and "WEB_REPO_DIR" in r.stderr, r.stderr


def test_web_publish_repo_TUONG_DOI(repo_gia, tmp_path):
    web = repo_gia.parent / "trang-web"
    web.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=web, capture_output=True)
    post = tmp_path / "tram" / "kenh" / "cd" / "T-1_bai"
    (post / "atlas").mkdir(parents=True)
    (tmp_path / "tram" / "kenh" / "channel.yml").write_text(
        "schema: channel/1\nid: kenh\nlabel: K\nweb_target:\n  kind: git_static\n"
        "  repo: trang-web\n  content_dir: content/{category}\n"
        "  base_url: https://vi-du.test/content\n", encoding="utf-8")
    (post / "meta.json").write_text(json.dumps({"post_id": "T-1", "slug": "bai",
                                                "category": "ai"}), encoding="utf-8")
    (post / "atlas" / "atlas.html").write_text("<h1>x</h1>", encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "web_publish.py"),
                        "--post", str(post), "--dry-run"], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert Path(json.loads(r.stdout.strip().splitlines()[-1])["dich"]) == \
        (web / "content" / "ai").resolve()
