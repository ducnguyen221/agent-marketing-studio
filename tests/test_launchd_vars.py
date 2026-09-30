# -*- coding: utf-8 -*-
"""P1-2: khoá `vars` (biến đường dẫn KHÔNG bí mật) và `env` dạng ánh xạ của `launchd.json`.

Trước 1.1.0 runner cần `L30_SCRIPT`, `TRUYEN_PUBLISH_PY`, `TRUYEN_FONT`, `VOICE_BGM_DIR`,
`WEB_REPO_DIR` mà không có đường nào vào plist; và job truyện cần `YT_CLIENT_SECRET` KHÁC giá
trị của job tin — buộc Mac cài bằng hai lệnh bọc `env …`. Các ca dưới giữ cả hai cửa mới VÀ
rào của chúng: tên ngoài danh sách trắng / giá trị không phải đường dẫn là mã 2, log chỉ mang TÊN.
"""
from __future__ import annotations

import json
import plistlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "runners"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import install_launchd as IL  # noqa: E402
import studio_contract as SC  # noqa: E402

_NHA = "/" + "Users" + "/nguoi-dung"
TRUYEN = "studio.marketing.daily-story"
BIEN_MAY = ["TG_CONFIG", "TG_CHAT", "YT_CLIENT_SECRET", "YT_TOKEN_PATH", "FB_CONFIG",
            "EMAIL_CONFIG", "CODEX_BRIDGE", "YT_TOKEN_PATH__NGHE_TIEN_TRUYEN",
            "YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN", "MARKETING_STUDIO_DATA",
            "MARKETING_STUDIO_HOME", *IL.BIEN_DUONG_DAN]


@pytest.fixture
def sach(monkeypatch):
    for n in BIEN_MAY:
        monkeypatch.delenv(n, raising=False)


def _tram(tmp_path, khai):
    tram = tmp_path / "tram"
    tram.mkdir()
    (tram / "launchd.json").write_text(json.dumps({TRUYEN: khai}), encoding="utf-8")
    return IL._parser().parse_args(["--station", str(tram), "--dry-run", "--only", TRUYEN])


def test_vars_object_HOP_LE_vao_plist():
    muc = IL.muc_khai(TRUYEN, {"channel": "k", "campaign": "c",
                               "vars": {"L30_SCRIPT": "~/cong-cu/l30.py",
                                        "WEB_REPO_DIR": _NHA + "/web"}})
    bien = IL.gia_bien(muc["vars"])
    e = plistlib.loads(IL.render(TRUYEN, _bang(), bien=bien))["EnvironmentVariables"]
    assert e["L30_SCRIPT"] == str(Path("~/cong-cu/l30.py").expanduser()), "~ phải được mở rộng"
    assert e["WEB_REPO_DIR"] == str(Path(_NHA + "/web"))


@pytest.mark.parametrize("ten", ["PYTHONPATH", "DYLD_INSERT_LIBRARIES", "YT_TOKEN_PATH", "PATH"])
def test_vars_ten_ngoai_danh_sach_trang_la_ma_2(ten):
    with pytest.raises(SC.ContractError):
        IL.muc_khai(TRUYEN, {"channel": "k", "campaign": "c", "vars": {ten: "/x"}})


@pytest.mark.parametrize("gia", ["tuong-doi/l30.py", "123456:khong-phai-duong", ""])
def test_vars_gia_tri_khong_phai_duong_dan_la_ma_2(gia):
    with pytest.raises(SC.ContractError):
        IL.muc_khai(TRUYEN, {"channel": "k", "campaign": "c", "vars": {"L30_SCRIPT": gia}})


def test_vars_danh_sach_lay_gia_tri_tu_bien(monkeypatch, sach):
    monkeypatch.setenv("TRUYEN_FONT", _NHA + "/font.ttf")
    muc = IL.muc_khai(TRUYEN, {"channel": "k", "campaign": "c", "vars": ["TRUYEN_FONT"]})
    assert IL.gia_bien(muc["vars"]) == {"TRUYEN_FONT": str(Path(_NHA + "/font.ttf"))}


def test_vars_danh_sach_THIEU_gia_tri_la_ma_2(sach):
    muc = IL.muc_khai(TRUYEN, {"channel": "k", "campaign": "c", "vars": ["VOICE_BGM_DIR"]})
    with pytest.raises(SC.ContractError) as e:
        IL.gia_bien(muc["vars"])
    assert "VOICE_BGM_DIR" in str(e.value)


def test_env_anh_xa_THAY_gia_tri_dong_cua_mau_khong_chen_dong_thu_hai(tmp_path, monkeypatch, sach):
    """`YT_CLIENT_SECRET` của job truyện lấy từ `YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN`."""
    monkeypatch.setenv("YT_CLIENT_SECRET", _NHA + "/khoa/tin.json")
    monkeypatch.setenv("YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN", _NHA + "/khoa/truyen.json")
    monkeypatch.setenv("YT_TOKEN_PATH__NGHE_TIEN_TRUYEN", _NHA + "/khoa/tok.json")
    a = _tram(tmp_path, {"channel": "k", "campaign": "c",
                         "env": {"YT_CLIENT_SECRET": "YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN",
                                 "YT_TOKEN_PATH__NGHE_TIEN_TRUYEN":
                                     "YT_TOKEN_PATH__NGHE_TIEN_TRUYEN"},
                         "vars": {"L30_SCRIPT": _NHA + "/l30.py"}})
    job = IL.lam(a)["jobs"][0]
    assert job["secret_env_from"] == {"YT_CLIENT_SECRET": "YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN"}
    assert job["vars"] == ["L30_SCRIPT"]
    # Plist thật: một dòng YT_CLIENT_SECRET, mang giá trị của kênh truyện.
    out = tmp_path / "out"
    a.dry_run, a.no_load, a.out_dir = False, True, str(out)
    IL.lam(a)
    raw = (out / f"{TRUYEN}.plist").read_text(encoding="utf-8")
    assert raw.count("<key>YT_CLIENT_SECRET</key>") == 1
    e = plistlib.loads(raw.encode("utf-8"))["EnvironmentVariables"]
    assert e["YT_CLIENT_SECRET"] == str(Path(_NHA + "/khoa/truyen.json"))
    assert e["YT_TOKEN_PATH__NGHE_TIEN_TRUYEN"] == str(Path(_NHA + "/khoa/tok.json"))
    assert e["L30_SCRIPT"] == str(Path(_NHA + "/l30.py"))


def test_env_anh_xa_nguon_THIEU_la_ma_2_neu_ten_nguon(tmp_path, sach):
    a = _tram(tmp_path, {"channel": "k", "campaign": "c",
                         "env": {"YT_CLIENT_SECRET": "YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN"}})
    with pytest.raises(SC.ContractError) as e:
        IL.lam(a)
    assert "YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN" in str(e.value)


@pytest.mark.parametrize("khai", [{"PATH": "YT_TOKEN_PATH"}, {"YT_TOKEN_PATH": "PYTHONPATH"},
                                  "YT_TOKEN_PATH", {"YT_TOKEN_PATH": 3}])
def test_env_anh_xa_sai_hinh_dang_hoac_ten_la_ma_2(khai):
    with pytest.raises(SC.ContractError):
        IL.muc_khai(TRUYEN, {"channel": "k", "campaign": "c", "env": khai})


def test_mau_goi_composer_trong_REPO_khong_trong_tram():
    """compose_report.py / triage.py nay ở `<repo>/scripts/runners` (P1-10)."""
    for p in (ROOT / "templates" / "launchd").glob("*.plist"):
        t = p.read_text(encoding="utf-8")
        assert "__STATION__/engine" not in t, p.name
        if "--composer-dir" in t:
            assert "__REPO__/scripts/runners" in t, p.name
    assert (ROOT / "scripts" / "runners" / "compose_report.py").is_file()
    assert (ROOT / "scripts" / "runners" / "triage.py").is_file()


def _bang():
    return {"__HOME__": _NHA, "__REPO__": _NHA + "/repo", "__STATION__": _NHA + "/tram",
            "__PY__": _NHA + "/py", "__VOICE_STATION__": "", "__VIDEO_STATION__": "",
            "__OMNIVOICE_PY__": "", "__CHANNEL__": "k", "__CAMPAIGN__": "c",
            "__RUNNER__": "run.ps1"}
