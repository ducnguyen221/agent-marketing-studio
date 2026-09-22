# -*- coding: utf-8 -*-
"""Adapter gọi TRẠM GIỌNG (`scripts/lib/voice.py`) — đo bằng CLI GIẢ, không cần engine thật.

Vì sao test bằng CLI giả chứ không mock `subprocess.run`: thứ dễ hỏng nhất ở đây không
phải logic Python mà là **đường ranh giới tiến trình** — argv đi ra có đúng không, dòng
JSON cuối đọc lại được không khi có log lạc vào stdout, mã thoát của tiến trình con có
thành đúng loại lỗi bên này không. Mock `subprocess` là tự trả lời hộ cả ba câu đó.

CLI giả là một package `voice_studio/` thật trong thư mục tạm, đặt lên `PYTHONPATH`, nên
lệnh chạy vẫn là `<python> -m voice_studio speak …` y như thật.
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
import voice as V  # noqa: E402

# Thân của CLI giả: ghi lại argv, in log rác ra cả hai luồng, rồi in dòng JSON và thoát
# đúng mã mà bài test đặt hàng trong `<gốc>/dat-hang.json`.
CLI_GIA = '''# -*- coding: utf-8 -*-
import json, os, sys
goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
don = json.load(open(os.path.join(goc, "dat-hang.json"), encoding="utf-8"))
json.dump(sys.argv[1:], open(os.path.join(goc, "argv.json"), "w", encoding="utf-8"))
sys.stderr.write("[gia] log cho nguoi doc\\n")
for dong in don.get("rac", []):
    sys.stdout.write(dong + "\\n")
if don.get("json") is not None:
    sys.stdout.write(json.dumps(don["json"], ensure_ascii=False) + "\\n")
sys.exit(don.get("code", 0))
'''


@pytest.fixture
def tram(tmp_path, monkeypatch):
    """Trạm giọng giả: có `station.json`, có python (= python đang chạy test) và CLI giả.

    Trả về một đối tượng nhỏ có `.dat(...)` để đặt hàng kết quả cho lượt gọi kế tiếp và
    `.argv()` để đọc lại argv mà adapter đã gửi đi.
    """
    for b in ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "VOICES_DIR",
              "VIDEO_STATION", "VIDEO_ROOT", "MARKETING_STUDIO_DATA"):
        monkeypatch.delenv(b, raising=False)

    goc = tmp_path / "tram-giong"
    (goc / "omnivoice" / "voices").mkdir(parents=True)
    (goc / "station.json").write_text(json.dumps(
        {"contract": "1.0.0", "venv": "omnivoice/.venv", "engine_dir": "omnivoice",
         "bgm_dir": "assets/bgm"}), encoding="utf-8")

    pkg = tmp_path / "gia"
    (pkg / "voice_studio").mkdir(parents=True)
    (pkg / "voice_studio" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "voice_studio" / "__main__.py").write_text(CLI_GIA, encoding="utf-8")

    monkeypatch.setenv("VOICE_STATION", str(goc))
    monkeypatch.setenv("OMNIVOICE_PY", sys.executable)      # bỏ qua venv chưa tồn tại
    monkeypatch.setenv("PYTHONPATH", str(pkg))

    class Tram:
        station = goc
        pkg_dir = pkg                      # `dat-hang.json` / `argv.json` nằm ở đây

        @staticmethod
        def dat(code=0, ra=None, rac=()):
            (pkg / "dat-hang.json").write_text(json.dumps(
                {"code": code, "json": ra, "rac": list(rac)}), encoding="utf-8")

        @staticmethod
        def argv():
            return json.loads((pkg / "argv.json").read_text(encoding="utf-8"))

    Tram.dat(0, {"ok": True, "outputs": [{"kind": "audio", "path": "a.wav", "duration": 1.0}]})
    return Tram


# ── đường vui: mã 0 ──────────────────────────────────────────────────────────────────

def test_speak_ma_0_tra_dict_va_gui_dung_argv(tram, tmp_path):
    ra = V.speak(text="Xin chào", profile="mau", out=str(tmp_path / "a.wav"))
    assert ra["outputs"][0]["path"] == "a.wav"
    argv = tram.argv()
    assert argv[0] == "speak"
    assert "--json" in argv
    for co, gia in (("--text", "Xin chào"), ("--profile", "mau")):
        assert argv[argv.index(co) + 1] == gia
    assert argv[argv.index("--out") + 1] == str(tmp_path / "a.wav")


def test_tham_so_tuy_chon_chi_di_ra_khi_duoc_khai(tram, tmp_path):
    V.speak(text="x", out=str(tmp_path / "a.wav"))
    argv = tram.argv()
    assert "--profile" not in argv and "--speed" not in argv and "--seed" not in argv
    V.speak(text="x", out=str(tmp_path / "a.wav"), speed=1.2, seed=7, lang="Vietnamese",
            normalize=True)
    argv = tram.argv()
    assert argv[argv.index("--speed") + 1] == "1.2"
    assert argv[argv.index("--seed") + 1] == "7"
    assert argv[argv.index("--lang") + 1] == "Vietnamese"
    assert "--normalize" in argv


def test_speak_nhan_ca_file_thay_cho_text(tram, tmp_path):
    kich = tmp_path / "kich-ban.txt"
    kich.write_text("nội dung", encoding="utf-8")
    V.speak(file=str(kich), out=str(tmp_path / "a.wav"))
    argv = tram.argv()
    assert argv[argv.index("--file") + 1] == str(kich) and "--text" not in argv


def test_stdout_co_log_rac_truoc_JSON_van_parse_duoc(tram, tmp_path):
    """Tiến trình con in nhầm log ra stdout là chuyện xảy ra thật (thư viện bên thứ ba).
    Hợp đồng nói "dòng JSON CUỐI", nên rác phía trước không được làm hỏng việc đọc."""
    tram.dat(0, {"ok": True, "outputs": []},
             rac=["Loading model...", "  50%|####", "{ không phải json"])
    assert V.speak(text="x", out=str(tmp_path / "a.wav"))["outputs"] == []


def test_lay_dong_JSON_CUOI_chu_khong_phai_dong_JSON_DAU_TIEN(tram, tmp_path):
    """Rác phía trước có thể CŨNG là JSON — thanh tiến trình của nhiều thư viện in ra
    đúng hình dạng đó. Lấy dòng đầu tiên trông giống JSON là lấy nhầm tiến độ làm kết quả,
    và cái nhầm đó im lặng: `outputs` thiếu, nơi khác nổ vì `KeyError`."""
    tram.dat(0, {"ok": True, "outputs": [{"kind": "audio", "path": "that.wav"}]},
             rac=['{"progress": 0.1}', '{"progress": 0.9, "outputs": []}'])
    ra = V.speak(text="x", out=str(tmp_path / "a.wav"))
    assert ra["outputs"][0]["path"] == "that.wav" and "progress" not in ra


# ── mã thoát → đúng loại lỗi ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("code,loai", [
    (1, SC.EngineError),
    (2, SC.ContractError),
    (3, SC.StationMissing),
])
def test_ma_thoat_thanh_dung_loai_ngoai_le(tram, tmp_path, code, loai):
    tram.dat(code, {"ok": False, "code": code, "error": "lời lẽ từ trạm giọng"})
    with pytest.raises(loai) as e:
        V.speak(text="x", out=str(tmp_path / "a.wav"))
    assert "lời lẽ từ trạm giọng" in str(e.value)
    assert e.value.code == code


def test_ma_la_ngoai_hop_dong_thi_thanh_loi_engine(tram, tmp_path):
    """Tiến trình bị giết (mã 9, 137, -1…) không phải "hợp đồng sai" — nó là hỏng lúc
    chạy, và lịch chạy được phép thử lại."""
    tram.dat(9, None, rac=["boom"])
    with pytest.raises(SC.EngineError) as e:
        V.speak(text="x", out=str(tmp_path / "a.wav"))
    assert "9" in str(e.value)


def test_ma_0_ma_khong_co_JSON_la_HONG_HOP_DONG(tram, tmp_path):
    """Mã 0 mà không có dòng JSON nghĩa là bên kia không hiểu `--json` (bản quá cũ, hoặc
    gọi nhầm lệnh). Nuốt im lặng ở đây là trả về `{}` rồi để nơi khác nổ vì thiếu khoá."""
    tram.dat(0, None, rac=["xong rồi"])
    with pytest.raises(SC.ContractError) as e:
        V.speak(text="x", out=str(tmp_path / "a.wav"))
    assert "JSON" in str(e.value) and "voice_studio" in str(e.value)


# ── kiểm TRƯỚC khi đẻ tiến trình con ─────────────────────────────────────────────────

def test_thieu_out_thi_loi_ngay_khong_goi_tien_trinh_con(tram):
    with pytest.raises(SC.ContractError):
        V.speak(text="x", out="")
    assert not (tram.pkg_dir / "argv.json").exists()


def test_vua_text_vua_file_la_loi(tram, tmp_path):
    with pytest.raises(SC.ContractError):
        V.speak(text="x", file=str(tmp_path / "k.txt"), out=str(tmp_path / "a.wav"))


def test_text_rong_la_loi(tram, tmp_path):
    with pytest.raises(SC.ContractError):
        V.speak(text="   ", out=str(tmp_path / "a.wav"))


def test_file_kich_ban_khong_co_that_la_loi(tram, tmp_path):
    with pytest.raises(SC.ContractError) as e:
        V.speak(file=str(tmp_path / "khong-co.txt"), out=str(tmp_path / "a.wav"))
    assert "khong-co.txt" in str(e.value)


# ── tìm trạm và tìm python ───────────────────────────────────────────────────────────

def test_chua_cai_tram_giong_thi_StationMissing_kem_HUONG_DAN_CAI(tmp_path, monkeypatch):
    for b in ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "MARKETING_STUDIO_HOME"):
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(tmp_path))     # repo giả, không có studio.local.json
    with pytest.raises(SC.StationMissing) as e:
        V.station()
    loi = str(e.value)
    assert "agent-voice-studio" in loi and "clone" in loi and "VOICE_STATION" in loi


def test_loi_de_nghi_CAI_noi_ro_day_la_NANG_LUC_CHUA_BAT(tmp_path, monkeypatch):
    """Đây là chỗ DUY NHẤT được phép hỏi người dùng có muốn cài trạm giọng không, và nó
    chỉ nói khi một bước THẬT SỰ chạm tới giọng.

    `doctor` lúc cài không hỏi gì (chỉ đạo 21/09): hỏi vu vơ ở đó là bắt người chưa biết
    mình có cần audio hay không phải quyết định ngay. Ở đây thì câu hỏi tự trả lời — người
    dùng vừa gọi một lệnh đọc thành tiếng. Nên thông điệp phải nói đủ ba thứ: cần GÌ, cài
    BẰNG LỆNH NÀO, và rằng lõi (viết bài + đăng) không hề cần cái này."""
    for b in ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "MARKETING_STUDIO_HOME"):
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(tmp_path))
    with pytest.raises(SC.StationMissing) as e:
        V.station()
    loi = str(e.value).lower()
    assert "chưa bật" in loi, loi
    assert "lồng tiếng" in loi, loi
    assert "viết bài và đăng" in loi, loi
    assert SC.StationMissing.code == 3


def test_python_lay_tu_station_json_khoa_venv(tmp_path, monkeypatch):
    for b in ("OMNIVOICE_PY", "OMNIVOICE_DIR"):
        monkeypatch.delenv(b, raising=False)
    goc = tmp_path / "v"
    py = goc / "omnivoice" / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    py.mkdir(parents=True)
    that = py / ("python.exe" if os.name == "nt" else "python")
    that.write_text("", encoding="utf-8")
    (goc / "station.json").write_text(json.dumps({"venv": "omnivoice/.venv"}), encoding="utf-8")
    monkeypatch.setenv("VOICE_STATION", str(goc))
    assert Path(V.python_exe()) == that


def test_bien_OMNIVOICE_PY_thang_station_json(tmp_path, monkeypatch):
    goc = tmp_path / "v"
    (goc / "omnivoice").mkdir(parents=True)
    (goc / "station.json").write_text(json.dumps({"venv": "omnivoice/.venv"}), encoding="utf-8")
    monkeypatch.setenv("VOICE_STATION", str(goc))
    monkeypatch.setenv("OMNIVOICE_PY", sys.executable)
    assert V.python_exe() == sys.executable


def test_khong_thay_python_nao_thi_StationMissing_chi_ro_cho_thieu(tmp_path, monkeypatch):
    for b in ("OMNIVOICE_PY", "OMNIVOICE_DIR"):
        monkeypatch.delenv(b, raising=False)
    goc = tmp_path / "v"
    goc.mkdir()
    (goc / "station.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VOICE_STATION", str(goc))
    with pytest.raises(SC.StationMissing) as e:
        V.python_exe()
    assert "venv" in str(e.value).lower()


def test_ten_cu_OMNIVOICE_DIR_van_dung_duoc_va_lui_MOT_cap(tmp_path, monkeypatch):
    """`OMNIVOICE_DIR` trỏ thư mục ENGINE (`<trạm>/omnivoice`), không phải gốc trạm — máy
    đang chạy lịch thật đặt tên cũ này, đọc sai một cấp là mất cả trạm."""
    for b in ("VOICE_STATION", "OMNIVOICE_PY"):
        monkeypatch.delenv(b, raising=False)
    goc = tmp_path / "v"
    (goc / "omnivoice").mkdir(parents=True)
    (goc / "station.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("OMNIVOICE_DIR", str(goc / "omnivoice"))
    assert V.station() == goc


# ── alias in-process cho script đọc hàng trăm câu ────────────────────────────────────

def test_engine_TU_CHOI_khi_python_dang_chay_khong_phai_venv_giong(tmp_path, monkeypatch):
    """`engine()` là ngoại lệ có chủ đích của hợp đồng (truyện đọc hàng trăm câu, gọi CLI
    từng câu là nạp lại model từng câu). Ngoại lệ đó chỉ hợp lệ khi tiến trình ĐANG chạy
    bằng chính python của trạm giọng — không thì `import voice_studio` hoặc sập, hoặc tệ
    hơn: nhặt được một bản khác trên máy."""
    goc = tmp_path / "v"
    (goc / "omnivoice" / ".venv").mkdir(parents=True)
    (goc / "station.json").write_text(json.dumps({"venv": "omnivoice/.venv"}), encoding="utf-8")
    monkeypatch.setenv("VOICE_STATION", str(goc))
    monkeypatch.setenv("OMNIVOICE_PY", str(goc / "khong-phai-python"))
    with pytest.raises(SC.ContractError) as e:
        V.engine()
    assert "OMNIVOICE_PY" in str(e.value)


def test_engine_cho_qua_khi_dung_python_cua_tram(tram, monkeypatch):
    """Đúng python (OMNIVOICE_PY = python đang chạy) thì nó mới đi tới bước import thật —
    và ở đây package giả không có `engine`, nên lỗi phải là "chưa cài", không phải mã 2."""
    with pytest.raises(SC.StationMissing):
        V.engine()


# ── không bao giờ đi qua shell ───────────────────────────────────────────────────────

def test_KHONG_dung_shell_va_KHONG_ghep_chuoi_lenh():
    """`shell=True` + đường dẫn có dấu cách/`&` là cách cổ điển để một tên file thành lệnh."""
    src = (ROOT / "scripts" / "lib" / "voice.py").read_text(encoding="utf-8")
    assert "shell=True" not in src


def test_adapter_khong_import_engine_cua_tram_kia():
    """Marketing gọi, KHÔNG import: `import voice_studio` ở tầng module trói cả repo vào
    venv giọng, kể cả cho việc không cần giọng."""
    src = (ROOT / "scripts" / "lib" / "voice.py").read_text(encoding="utf-8")
    assert "\nimport voice_studio" not in src and "\nfrom voice_studio" not in src


def test_chay_that_bang_dong_lenh_CLI_gia(tram, tmp_path):
    """Chạy adapter trong một tiến trình python KHÁC (giống runner `.ps1` gọi vào): thứ
    duy nhất đi qua là argv + môi trường, nên test này bắt được lỗi phụ thuộc trạng thái
    của tiến trình test."""
    ma = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'%s'); import voice; "
         "print(voice.speak(text='x', out=r'%s')['outputs'])"
         % (str(ROOT / "scripts" / "lib"), str(tmp_path / "a.wav"))],
        capture_output=True, text=True, encoding="utf-8")
    assert ma.returncode == 0, ma.stderr
