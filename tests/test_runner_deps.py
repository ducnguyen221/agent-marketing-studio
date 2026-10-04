# -*- coding: utf-8 -*-
"""`doctor` kiểm thứ BỘ CHẠY cần mà repo không tự cài (P0-3, P0-4, P0-6, last30days) và so
tên profile giọng ở dạng NFC (P1-4). Không mạng, không `claude -p`, không venv giọng thật.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import runner_deps as RD  # noqa: E402
import doctor as DR  # noqa: E402

# Tên gói pip -> tên import (đúng thứ runner `import`).
PIP_SANG_IMPORT = {"google-api-python-client": "googleapiclient",
                   "google-auth-oauthlib": "google_auth_oauthlib",
                   "google-auth-httplib2": "google_auth_httplib2", "httplib2": "httplib2",
                   "requests": "requests", "beautifulsoup4": "bs4", "lxml": "lxml",
                   "yt-dlp": "yt_dlp", "openpyxl": "openpyxl",
                   "faster-whisper": "faster_whisper", "av": "av"}


def test_requirements_runners_KHOP_danh_sach_module_doctor_kiem():
    goi = RD.doc_requirements(ROOT)
    assert set(goi) == set(PIP_SANG_IMPORT), goi
    assert {PIP_SANG_IMPORT[g] for g in goi} == set(RD.MODULES)


# ── Cổng P0-7: MỌI thứ bên thứ ba mà `scripts/runners/**` nạp phải nằm trong MODULES ─────────
#
# Sự cố (Mac mini, 30/09/2026): `read_story.py` gọi `BeautifulSoup(…, "lxml")` — `lxml` được
# nạp bằng TÊN CHUỖI, không phải `import`, nên cổng quét import (`test_gia_dinh_moi_truong`)
# không thấy; venv giọng Mac không có `lxml`, `doctor` vẫn báo "đủ gói", lượt truyện chết ở bước
# đọc chương (`FeatureNotFound`). Cổng dưới đo CẢ HAI đường nạp — `import` và tên parser — và
# đòi mỗi thứ nằm trong `runner_deps.MODULES` (tức cũng trong `requirements-runners.txt`, cổng
# ngay trên giữ hai danh sách khớp nhau).

RUNNERS = ROOT / "scripts" / "runners"
# Đến cùng `voice_studio` khi cài trạm giọng (`pip install -e`), không cài qua requirements-runners.
DO_VENV_GIONG_CAP = {"voice_studio", "numpy", "soundfile", "torch"}
# Tên import ≠ tên module trong MODULES: `google.oauth2`/`google.auth` là của google-auth, gói
# mà google-api-python-client kéo theo (và `googleapiclient` nằm trong MODULES).
BI_DANH_IMPORT = {"google": "googleapiclient"}
# Parser của BeautifulSoup -> module phải có. `html.parser` là thư viện chuẩn.
PARSER_BS4 = {"lxml": "lxml", "lxml-xml": "lxml", "xml": "lxml", "html5lib": "html5lib",
              "html.parser": None}


def _thu_ben_thu_ba_runner_nap():
    """-> {tên module: {file:dòng, …}} cho mọi `import` tuyệt đối và mọi parser BeautifulSoup
    trong `scripts/runners/**.py`, đã bỏ thư viện chuẩn và module nội bộ của repo."""
    import ast
    noi_bo = {p.stem for p in (ROOT / "scripts").rglob("*.py")}
    ra: dict[str, set[str]] = {}

    def them(ten, f, nut):
        ra.setdefault(ten, set()).add(f"{f.relative_to(ROOT).as_posix()}:{nut.lineno}")

    for f in sorted(RUNNERS.rglob("*.py")):
        cay = ast.parse(f.read_text(encoding="utf-8-sig"), filename=str(f))
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Import):
                for a in nut.names:
                    them(a.name.split(".")[0], f, nut)
            elif isinstance(nut, ast.ImportFrom) and nut.module and not nut.level:
                them(nut.module.split(".")[0], f, nut)
            elif isinstance(nut, ast.Call):
                ham = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                       else getattr(nut.func, "id", ""))
                if ham != "BeautifulSoup":
                    continue
                gt = [k.value for k in nut.keywords if k.arg == "features"]
                gt += nut.args[1:2]
                for g in gt:
                    assert isinstance(g, ast.Constant) and isinstance(g.value, str), (
                        f"{f.name}:{nut.lineno}: parser BeautifulSoup phải là chuỗi hằng để "
                        f"cổng đo được module nó cần")
                    assert g.value in PARSER_BS4, f"{f.name}:{nut.lineno}: parser lạ {g.value!r}"
                    if PARSER_BS4[g.value]:
                        them(PARSER_BS4[g.value], f, nut)
    return {k: v for k, v in ra.items()
            if k not in sys.stdlib_module_names and k not in noi_bo}


def test_MOI_import_va_parser_ben_thu_ba_cua_runner_deu_nam_trong_MODULES():
    dung = _thu_ben_thu_ba_runner_nap()
    assert "lxml" in dung, "cổng không thấy parser lxml của read_story.py — cổng đang không đo gì"
    lot = {k: v for k, v in dung.items()
           if k not in DO_VENV_GIONG_CAP and BI_DANH_IMPORT.get(k, k) not in RD.MODULES}
    assert not lot, ("runner nạp thứ KHÔNG có trong runner_deps.MODULES / requirements-runners"
                     ".txt — venv giọng máy mới sẽ thiếu mà doctor vẫn báo đủ: "
                     + "; ".join(f"{k} ({', '.join(sorted(v))})" for k, v in sorted(lot.items())))


def test_thieu_module_neu_dung_ten(tmp_path):
    assert RD.thieu_module(sys.executable, ["json", "khong_co_module_xyz_123"]) == \
        ["khong_co_module_xyz_123"]
    assert RD.thieu_module(str(tmp_path / "khong-co-python")) is None


def _l30(goc: Path) -> Path:
    p = goc / "skills" / "last30days" / "scripts" / "last30days.py"
    p.parent.mkdir(parents=True)
    p.write_text("#", encoding="utf-8")
    return p


def test_last30days_theo_thu_tu_bien_marketplace_cache(tmp_path):
    nha = tmp_path / "nha"
    assert RD.tim_last30days(env={}, home=nha) is None
    cu = _l30(nha / ".claude" / "plugins" / "cache" / "mk" / "last30days" / "3.2.0")
    moi = _l30(nha / ".claude" / "plugins" / "cache" / "mk" / "last30days" / "3.10.1")
    assert RD.tim_last30days(env={}, home=nha) == moi, "cache: bản MỚI NHẤT theo số, không theo chữ"
    mk = _l30(nha / ".claude" / "plugins" / "marketplaces" / "last30days-skill")
    assert RD.tim_last30days(env={}, home=nha) == mk, "marketplace thắng cache"
    rieng = tmp_path / "rieng.py"
    rieng.write_text("#", encoding="utf-8")
    assert RD.tim_last30days(env={"L30_SCRIPT": str(rieng)}, home=nha) == rieng
    assert RD.tim_last30days(env={"L30_SCRIPT": str(tmp_path / "vang.py")}, home=nha) is None
    assert cu.is_file()


def test_nhac_nen_bao_style_thieu_mp3(tmp_path):
    (tmp_path / "bgm-library.json").write_text(
        '{"default": "a", "styles": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}',
        encoding="utf-8")
    (tmp_path / "a.mp3").write_bytes(b"x")
    kq = RD.kiem_nhac_nen(tmp_path)
    assert kq["co_thu_vien"] and kq["styles"] == ["a", "b", "c"] and kq["thieu_mp3"] == ["b", "c"]
    assert RD.kiem_nhac_nen(tmp_path / "vang")["co_thu_vien"] is False


def _tram(tmp_path, runner: str) -> Path:
    t = tmp_path / "tram"
    (t / "kenh" / "cd").mkdir(parents=True)
    (t / "CHANNELS.md").write_text("---\nchannels:\n  - id: kenh\n    path: ./kenh\n---\n",
                                   encoding="utf-8")
    (t / "kenh" / "channel.yml").write_text("id: kenh\n", encoding="utf-8")
    (t / "kenh" / "cd" / "campaign.md").write_text(
        f"---\nid: cd\nruntime:\n  runner: {runner}\n---\n", encoding="utf-8")
    return t


def test_runner_dang_dung_doc_tu_campaign(tmp_path):
    assert RD.runner_dang_dung(_tram(tmp_path, "run-toptoday-hot.ps1")) == {"run-toptoday-hot.ps1"}


def test_doctor_KHONG_kiem_runner_khi_khong_chien_dich_nao_dung(tmp_path):
    so = DR.So()
    DR.kham_runner(so, _tram(tmp_path, "run.ps1"))
    assert so.warn == [] and so.not_checked == [] and so.fail == []


def test_doctor_bao_module_thieu_lenh_pip_claude_NOT_CHECKED_va_nhac_nen(tmp_path, monkeypatch):
    tram = _tram(tmp_path, "run-toptoday-hot.ps1")
    giong = tmp_path / "giong"
    giong.mkdir()
    bgm = tmp_path / "bgm"
    bgm.mkdir()
    (bgm / "bgm-library.json").write_text('{"styles": [{"name": "x"}]}', encoding="utf-8")
    monkeypatch.setattr(DR.SP, "voice_station", lambda *a, **k: giong)
    monkeypatch.setattr(DR.VOICE, "python_exe", lambda *a, **k: "/py-giong")
    monkeypatch.setattr(DR.RD, "thieu_module", lambda py, *a: ["googleapiclient", "bs4"])
    monkeypatch.setattr(DR.RD, "tim_last30days", lambda *a, **k: None)
    monkeypatch.setattr(DR.RD, "thu_muc_nhac_nen", lambda: bgm)
    monkeypatch.setattr(DR.shutil, "which", lambda ten: None)
    so = DR.So()
    DR.kham_runner(so, tram)
    chu = "\n".join(so.warn)
    assert "googleapiclient, bs4" in chu and "-m pip install -r" in chu and RD.REQ_FILE in chu
    assert "last30days" in chu and "L30_SCRIPT" in chu
    assert "x" in chu and "thiếu mp3" in chu
    assert "không thấy lệnh `claude`" in chu
    assert any("claude-cli" in x and "claude -p" in x for x in so.not_checked)
    assert so.fail == [], "thiếu phụ thuộc runner chỉ NHẮC, không đỏ"


def test_doctor_so_profile_NFD_voi_khai_NFC_KHONG_do_gia(tmp_path, monkeypatch):
    """P1-4: file giọng nhập từ Windows sang macOS mang tên NFD, channel.yml viết NFC."""
    ten = "Giọng tiên hiệp"
    kho = tmp_path / "voices"
    kho.mkdir()
    (kho / (unicodedata.normalize("NFD", ten) + ".wav")).write_bytes(b"x")
    monkeypatch.setattr(DR.VOICE, "voices_dir", lambda *a, **k: kho)
    so = DR.So()
    DR._kham_profile(so, tmp_path, [("kenh", {"voice_profile": unicodedata.normalize("NFC", ten)})])
    assert so.fail == [], so.fail
    so = DR.So()
    DR._kham_profile(so, tmp_path, [("kenh", {"voice_profile": "khong-co"})])
    assert so.fail, "profile thật sự thiếu vẫn phải ĐỎ"


# ── `gh` cho nhánh dự phòng của bản tin tuần (SUBTASK-WIN-RUNTIME-3 §5) ────────────────

def _tram_tuan(tmp_path, gh_repo="owner/news"):
    t = _tram(tmp_path, "run-weekly-news.ps1")
    (t / "kenh" / "channel.yml").write_text(
        "id: kenh\nbrand:\n  gh_repo: " + gh_repo + "\n", encoding="utf-8")
    return t


def _kham_gh(tmp_path, monkeypatch, tram, co_gh):
    monkeypatch.setattr(DR.SP, "voice_station", lambda *a, **k: None)
    monkeypatch.setattr(DR.RD, "tim_last30days", lambda *a, **k: tmp_path / "l30.py")
    monkeypatch.setattr(DR.RD, "thu_muc_nhac_nen", lambda: None)
    monkeypatch.setattr(DR.shutil, "which",
                        lambda ten: ("/opt/homebrew/bin/gh" if co_gh else None) if ten == "gh" else "/x/" + ten)
    so = DR.So()
    DR.kham_runner(so, tram)
    return so


def test_kenh_can_gh_chi_khi_co_ban_tin_tuan_VA_khai_gh_repo(tmp_path):
    assert RD.kenh_can_gh(_tram_tuan(tmp_path)) == ["kenh"]
    assert RD.kenh_can_gh(_tram_tuan(tmp_path / "b", gh_repo='""')) == []
    assert RD.kenh_can_gh(_tram(tmp_path / "c", "run-toptoday-hot.ps1")) == []


def test_doctor_THIEU_gh_thi_NHAC_kem_lenh_cai_ca_hai_he(tmp_path, monkeypatch):
    so = _kham_gh(tmp_path, monkeypatch, _tram_tuan(tmp_path), co_gh=False)
    chu = "\n".join(so.warn)
    assert "gh_repo" in chu and "brew install gh" in chu and "gh auth login" in chu
    assert "winget install --id GitHub.cli" in chu and "KHÔNG có video" in chu
    assert so.fail == [], "thiếu gh chỉ NHẮC — nhánh đó là dự phòng"


def test_doctor_CO_gh_thi_dang_nhap_la_NOT_CHECKED(tmp_path, monkeypatch):
    so = _kham_gh(tmp_path, monkeypatch, _tram_tuan(tmp_path), co_gh=True)
    assert not any("gh_repo" in w for w in so.warn)
    assert any("gh auth status" in x for x in so.not_checked)


def test_runner_tuan_thieu_gh_BO_nhanh_Release_truoc_khi_goi_gh():
    t = (ROOT / "scripts" / "runners" / "run-weekly-news.ps1").read_text(encoding="utf-8-sig")
    rao = t.index("-not (Get-Command gh -ErrorAction SilentlyContinue)")
    assert rao < t.index("& gh release view"), "phải rẽ nhánh TRƯỚC lệnh gh đầu tiên"
    assert "KHONG co lenh gh" in t



# ── P1-27: doctor đối chiếu tên model agy với `agy models` ─────────────────────────────

MODELS = ["gemini-3.8-flash-high", "claude-opus-5-5-high", "claude-opus-5-5-medium"]


@pytest.fixture
def khong_bien(monkeypatch):
    for k in ("TRUYEN_HOOK_ENGINE", "AGENT_CALL_ENGINES"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(DR.SP, "secret_env", lambda ten, *a, **k: None)


def _tram_engines(tmp_path, order, best="gemini-*-flash-high"):
    import json as _j
    t = tmp_path / "tram"
    (t / "_agent-call").mkdir(parents=True)
    (t / "CHANNELS.md").write_text("---\nchannels: []\n---\n", encoding="utf-8")
    (t / "_agent-call" / "engines.json").write_text(
        _j.dumps({"order": order, "engines": {"agy": {"best": best}}}), encoding="utf-8")
    return t


def test_doctor_model_agy_CU_thi_NHAC_kem_goi_y(tmp_path, khong_bien):
    so = DR.So()
    DR.kham_agy_model(so, _tram_engines(tmp_path, ["agy:claude-opus-4-6-thinking", "claude:best"]),
                      models=MODELS)
    chu = "\n".join(so.warn)
    assert "claude-opus-4-6-thinking" in chu and "claude-opus-5-5-high" in chu
    assert "claude-opus-*-high" in chu and so.fail == []


def test_doctor_mau_khop_thi_ghi_ban_phan_giai(tmp_path, khong_bien):
    so = DR.So()
    DR.kham_agy_model(so, _tram_engines(tmp_path, ["agy:claude-opus-*-high", "agy:best"]), models=MODELS)
    assert so.warn == []
    assert any("claude-opus-5-5-high" in x for x in so.info)
    assert any("gemini-3.8-flash-high" in x for x in so.info), "`agy:best` phải được đổi ra tên best"


def test_doctor_khong_hoi_duoc_agy_models_la_NOT_CHECKED(tmp_path, khong_bien, monkeypatch):
    monkeypatch.setattr(DR.shutil, "which", lambda ten: "/x/" + ten)
    monkeypatch.setattr(DR.AC, "agy_models", lambda *a, **k: None)
    so = DR.So()
    DR.kham_agy_model(so, _tram_engines(tmp_path, ["agy:claude-opus-*-high"]))
    assert so.not_checked and so.warn == [] and so.fail == []


def test_doctor_khong_dung_agy_thi_im(tmp_path, khong_bien):
    so = DR.So()
    DR.kham_agy_model(so, _tram_engines(tmp_path, ["claude:best", "codex:best"], best=""), models=MODELS)
    assert so.warn == so.info == so.not_checked == so.fail == []
