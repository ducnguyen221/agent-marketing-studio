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
                   "beautifulsoup4": "bs4", "yt-dlp": "yt_dlp", "openpyxl": "openpyxl",
                   "faster-whisper": "faster_whisper"}


def test_requirements_runners_KHOP_danh_sach_module_doctor_kiem():
    goi = RD.doc_requirements(ROOT)
    assert set(goi) == set(PIP_SANG_IMPORT), goi
    assert {PIP_SANG_IMPORT[g] for g in goi} == set(RD.MODULES)


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
