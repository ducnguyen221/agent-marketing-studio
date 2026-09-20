# -*- coding: utf-8 -*-
"""Adapter gọi TRẠM VIDEO (`scripts/lib/video.py`) — đo bằng CLI giả, cùng khuôn với
`test_voice_adapter.py`.

Điểm khác đáng kiểm nhất so với trạm giọng: **python nào chạy nó**. `video_studio` được
cài `pip install -e` vào CHÍNH venv của trạm giọng (hợp đồng ba trạm, §2.4 phương án A),
vì torch là phụ thuộc nặng duy nhất và cả hai đều cần. Nên trạm video có `station.json`
KHÔNG có khoá `venv` — nếu adapter đòi khoá đó thì mọi máy cài đúng đều hỏng.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import studio_contract as SC  # noqa: E402
import video as VD  # noqa: E402

CLI_GIA = '''# -*- coding: utf-8 -*-
import json, os, sys
goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
don = json.load(open(os.path.join(goc, "dat-hang.json"), encoding="utf-8"))
json.dump(sys.argv[1:], open(os.path.join(goc, "argv.json"), "w", encoding="utf-8"))
sys.stderr.write("[gia] dang render\\n")
for dong in don.get("rac", []):
    sys.stdout.write(dong + "\\n")
if don.get("json") is not None:
    sys.stdout.write(json.dumps(don["json"], ensure_ascii=False) + "\\n")
sys.exit(don.get("code", 0))
'''

XONG = {"ok": True, "project": "topstory", "out": "d",
        "outputs": [{"kind": "long", "path": "a.mp4", "duration": 12.0}]}


@pytest.fixture
def tram(tmp_path, monkeypatch):
    for b in ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "VOICES_DIR",
              "VIDEO_STATION", "VIDEO_ROOT", "MARKETING_STUDIO_DATA"):
        monkeypatch.delenv(b, raising=False)

    giong = tmp_path / "tram-giong"
    (giong / "omnivoice").mkdir(parents=True)
    (giong / "station.json").write_text(json.dumps({"venv": "omnivoice/.venv"}), encoding="utf-8")
    video = tmp_path / "tram-video"
    (video / "projects").mkdir(parents=True)
    # Đúng như `video-studio init` viết ra: KHÔNG có khoá `venv`.
    (video / "station.json").write_text(json.dumps(
        {"contract": "1.0.0", "mode": "separate", "hyperframes_version": "0.7.94",
         "projects_dir": "projects"}), encoding="utf-8")

    pkg = tmp_path / "gia"
    (pkg / "video_studio").mkdir(parents=True)
    (pkg / "video_studio" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "video_studio" / "__main__.py").write_text(CLI_GIA, encoding="utf-8")

    monkeypatch.setenv("VOICE_STATION", str(giong))
    monkeypatch.setenv("VIDEO_STATION", str(video))
    monkeypatch.setenv("OMNIVOICE_PY", sys.executable)
    monkeypatch.setenv("PYTHONPATH", str(pkg))

    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"schema_version": 1, "brand": {"a": "A", "b": "B", "site": "x"}}),
                    encoding="utf-8")

    class Tram:
        station = video
        pkg_dir = pkg
        spec_file = spec

        @staticmethod
        def dat(code=0, ra=None, rac=()):
            (pkg / "dat-hang.json").write_text(json.dumps(
                {"code": code, "json": ra, "rac": list(rac)}), encoding="utf-8")

        @staticmethod
        def argv():
            return json.loads((pkg / "argv.json").read_text(encoding="utf-8"))

    Tram.dat(0, XONG)
    return Tram


def test_render_ma_0_tra_dict_va_gui_dung_argv(tram, tmp_path):
    ra = VD.render("topstory", str(tram.spec_file), str(tmp_path / "ra"))
    assert ra["outputs"][0]["kind"] == "long"
    argv = tram.argv()
    assert argv[0] == "render" and "--json" in argv
    assert argv[argv.index("--project") + 1] == "topstory"
    assert argv[argv.index("--input") + 1] == str(tram.spec_file)
    assert argv[argv.index("--out") + 1] == str(tmp_path / "ra")
    assert "--brand" not in argv and "--voice-profile" not in argv


def test_brand_va_voice_profile_di_ra_khi_duoc_khai(tram, tmp_path):
    bra = tmp_path / "brand.json"
    bra.write_text(json.dumps({"a": "A", "b": "B", "site": "x"}), encoding="utf-8")
    VD.render("news", str(tram.spec_file), str(tmp_path / "ra"),
              brand=str(bra), voice_profile="mau")
    argv = tram.argv()
    assert argv[argv.index("--brand") + 1] == str(bra)
    assert argv[argv.index("--voice-profile") + 1] == "mau"


def test_stdout_co_log_rac_truoc_JSON_van_parse_duoc(tram, tmp_path):
    tram.dat(0, XONG, rac=["npx hyperframes...", "[####    ] 40%"])
    assert VD.render("news", str(tram.spec_file), str(tmp_path / "ra"))["ok"] is True


@pytest.mark.parametrize("code,loai", [
    (1, SC.EngineError),
    (2, SC.ContractError),
    (3, SC.StationMissing),
])
def test_ma_thoat_thanh_dung_loai_ngoai_le(tram, tmp_path, code, loai):
    tram.dat(code, {"ok": False, "code": code, "error": "lời lẽ từ trạm video"})
    with pytest.raises(loai) as e:
        VD.render("news", str(tram.spec_file), str(tmp_path / "ra"))
    assert "lời lẽ từ trạm video" in str(e.value) and e.value.code == code


def test_ma_0_ma_khong_co_JSON_la_HONG_HOP_DONG(tram, tmp_path):
    tram.dat(0, None, rac=["render xong"])
    with pytest.raises(SC.ContractError) as e:
        VD.render("news", str(tram.spec_file), str(tmp_path / "ra"))
    assert "JSON" in str(e.value) and "video_studio" in str(e.value)


# ── kiểm trước khi đẻ tiến trình con ─────────────────────────────────────────────────

def test_spec_khong_co_that_thi_loi_ngay(tram, tmp_path):
    with pytest.raises(SC.ContractError) as e:
        VD.render("news", str(tmp_path / "khong-co.json"), str(tmp_path / "ra"))
    assert "khong-co.json" in str(e.value)
    assert not (tram.pkg_dir / "argv.json").exists()


def test_project_rong_thi_loi_ngay(tram, tmp_path):
    with pytest.raises(SC.ContractError):
        VD.render("", str(tram.spec_file), str(tmp_path / "ra"))


# ── tìm trạm, tìm python ─────────────────────────────────────────────────────────────

def test_chua_cai_tram_video_thi_StationMissing_kem_HUONG_DAN_CAI(tmp_path, monkeypatch):
    for b in ("VIDEO_STATION", "VIDEO_ROOT"):
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(tmp_path))
    with pytest.raises(SC.StationMissing) as e:
        VD.station()
    loi = str(e.value)
    assert "agent-video-studio" in loi and "clone" in loi and "VIDEO_STATION" in loi


def test_python_MAC_DINH_la_python_cua_tram_GIONG(tram):
    """`video_studio` cài chung venv với `voice_studio` — nên không có `venv` riêng."""
    assert VD.python_exe() == sys.executable


def test_station_json_cua_tram_video_co_venv_rieng_thi_ton_trong(tmp_path, monkeypatch):
    """Ai cố ý tách venv riêng cho render câm (không cần torch) thì khai `venv` trong
    `station.json` của trạm video, và adapter phải theo — nếu không, lựa chọn đó vô hiệu
    trong im lặng."""
    monkeypatch.delenv("OMNIVOICE_PY", raising=False)
    video = tmp_path / "v"
    rieng = video / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
    rieng.mkdir(parents=True)
    that = rieng / ("python.exe" if sys.platform == "win32" else "python")
    that.write_text("", encoding="utf-8")
    (video / "station.json").write_text(json.dumps({"venv": ".venv"}), encoding="utf-8")
    monkeypatch.setenv("VIDEO_STATION", str(video))
    assert Path(VD.python_exe()) == that


def test_KHONG_dung_shell():
    src = (ROOT / "scripts" / "lib" / "video.py").read_text(encoding="utf-8")
    assert "shell=True" not in src


def test_adapter_khong_import_engine_cua_tram_kia():
    src = (ROOT / "scripts" / "lib" / "video.py").read_text(encoding="utf-8")
    assert "\nimport video_studio" not in src and "\nfrom video_studio" not in src
