# -*- coding: utf-8 -*-
"""`doctor` — phần HAI TRẠM NĂNG LỰC của hợp đồng ba trạm (gói P2-G3).

Phần F17 (hai chế độ cài) đã có cổng riêng ở `test_gitignore_guard.py`. File này chỉ đo
phần nối thêm: trạm giọng (`agent-voice-studio`) và trạm video (`agent-video-studio`).

**Luật phân biệt — đây là chỗ dễ làm sai nhất và là lý do file này tồn tại:**

  chưa khai gì        → NHẮC, không đỏ. Một người chỉ viết blog không cần trạm giọng; bắt
                        họ nhìn "CHƯA CÀI XONG" sau mỗi lần cài là dạy họ bỏ qua `doctor`.
  đã khai mà chưa đủ  → ĐỎ mã 3. Có biến trỏ vào một trạm không có `station.json`, hoặc
                        một kênh khai `voice_profile`: người dùng ĐÃ nói mình cần, và
                        pipeline sẽ nổ giữa chừng lúc 18h thay vì lúc cài.
  khai sai            → ĐỎ mã 2. Profile khai trong `channel.yml` không có trong kho giọng:
                        không phải "cài tiếp", mà là "sửa cái đang sai".
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import doctor as DR  # noqa: E402
import studio_contract as SC  # noqa: E402

BIEN = ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "VOICES_DIR",
        "VIDEO_STATION", "VIDEO_ROOT", "MARKETING_STUDIO_DATA", "MARKETING_STUDIO_HOME")

# Package giả để `<python> -c "import voice_studio…"` trả về số phiên bản do test đặt.
GIA = "API_VERSION = {!r}\n"


@pytest.fixture
def may(tmp_path, monkeypatch):
    """Một máy giả: trạm nội dung hợp lệ, không trạm năng lực nào, môi trường sạch biến."""
    for b in BIEN:
        monkeypatch.delenv(b, raising=False)
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))
    tram = tmp_path / "tram"
    tram.mkdir()
    (tram / "CHANNELS.md").write_text("---\nschema: channels/1\nchannels: []\n---\n",
                                      encoding="utf-8")
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tram))
    return tram


def _kenh(tram, **khoa):
    """Thêm một kênh vào trạm giả, với các khoá tuỳ ý trong `channel.yml`."""
    d = tram / "kenh-a"
    d.mkdir(exist_ok=True)
    dong = ["schema: channel/1", "id: kenh-a"] + [f"{k}: {v}" for k, v in khoa.items()]
    (d / "channel.yml").write_text("\n".join(dong) + "\n", encoding="utf-8")
    (tram / "CHANNELS.md").write_text(
        "---\nschema: channels/1\nchannels:\n  - id: kenh-a\n    path: ./kenh-a\n---\n",
        encoding="utf-8")
    return d


def _tram_giong(tmp_path, monkeypatch, *, station_json=True, voice_ver="1.0.0",
                video_ver="1.0.0", profiles=("giong-mau",)):
    """Trạm giọng giả + một python thật biết trả lời câu hỏi phiên bản."""
    goc = tmp_path / "tram-giong"
    voices = goc / "omnivoice" / "voices"
    voices.mkdir(parents=True, exist_ok=True)
    for p in profiles:
        (voices / f"{p}.txt").write_text("lời mẫu", encoding="utf-8")
    if station_json:
        (goc / "station.json").write_text(json.dumps(
            {"contract": "1.0.0", "venv": "omnivoice/.venv", "engine_dir": "omnivoice"}),
            encoding="utf-8")
    pkg = tmp_path / "gia-pkg"
    pkg.mkdir(exist_ok=True)
    for ten, ver in (("voice_studio", voice_ver), ("video_studio", video_ver)):
        if ver is None:
            continue
        (pkg / ten).mkdir(exist_ok=True)
        (pkg / ten / "__init__.py").write_text(GIA.format(ver), encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(pkg))
    monkeypatch.setenv("VOICE_STATION", str(goc))
    monkeypatch.setenv("OMNIVOICE_PY", sys.executable)
    return goc


def _tram_video(tmp_path, monkeypatch, *, station_json=True):
    goc = tmp_path / "tram-video"
    goc.mkdir(exist_ok=True)
    if station_json:
        (goc / "station.json").write_text(json.dumps(
            {"contract": "1.0.0", "hyperframes_version": "0.7.94"}), encoding="utf-8")
    monkeypatch.setenv("VIDEO_STATION", str(goc))
    return goc


def _chu(kq):
    return "\n".join(kq["fail"] + kq["warn"] + kq["info"])


# ── cổng của cổng ────────────────────────────────────────────────────────────────────

def test_KHAM_THEM_that_su_duoc_noi_vao_luong():
    """Danh sách rỗng thì mọi test dưới đây xanh mà không đo gì."""
    assert DR.KHAM_THEM, "P2-G3 phải nối phần trạm giọng/video vào doctor.KHAM_THEM"


# ── chưa khai gì: nhắc, không đỏ ─────────────────────────────────────────────────────

def test_chua_khai_tram_nao_thi_CHI_NHAC(may):
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    chu = "\n".join(kq["warn"])
    assert "agent-voice-studio" in chu and "agent-video-studio" in chu


# ── đã khai mà chưa đủ: mã 3 ─────────────────────────────────────────────────────────

def test_khai_tram_giong_ma_chua_co_station_json_thi_MA_3_kem_huong_dan(
        may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, station_json=False)
    kq = DR.kham()
    assert kq["code"] == SC.STATION_MISSING
    chu = _chu(kq)
    assert "station.json" in chu and "voice-studio init" in chu


def test_ten_bien_CU_van_chay_nhung_co_canh_bao(may, tmp_path, monkeypatch):
    """`OMNIVOICE_DIR` trỏ thư mục ENGINE. Máy đang chạy lịch thật dùng tên này, nên nó
    phải còn hiệu lực — nhưng im lặng chấp nhận thì không ai đổi sang tên mới bao giờ."""
    goc = _tram_giong(tmp_path, monkeypatch)
    monkeypatch.delenv("VOICE_STATION")
    monkeypatch.setenv("OMNIVOICE_DIR", str(goc / "omnivoice"))
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert any("OMNIVOICE_DIR" in x and "VOICE_STATION" in x for x in kq["warn"]), kq["warn"]


def test_khai_tram_video_ma_chua_co_station_json_thi_MA_3(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch)
    _tram_video(tmp_path, monkeypatch, station_json=False)
    kq = DR.kham()
    assert kq["code"] == SC.STATION_MISSING
    assert any("video-studio init" in x for x in kq["fail"]), kq["fail"]


def test_kenh_khai_voice_profile_lam_tram_giong_thanh_BAT_BUOC(may):
    """Không biến nào được đặt, nhưng một kênh nói mình cần giọng ⇒ thiếu trạm là ĐỎ."""
    _kenh(may, voice_profile="giong-mau")
    kq = DR.kham()
    assert kq["code"] == SC.STATION_MISSING
    assert any("agent-voice-studio" in x and "clone" in x for x in kq["fail"]), kq["fail"]


# ── đủ: xanh ─────────────────────────────────────────────────────────────────────────

def test_du_ca_hai_tram_va_dung_phien_ban_thi_XANH(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch)
    _tram_video(tmp_path, monkeypatch)
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert any("voice_studio" in x and "1.0.0" in x for x in kq["info"]), kq["info"]


def test_kenh_khai_profile_CO_THAT_thi_xanh(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, profiles=("giong-mau",))
    _tram_video(tmp_path, monkeypatch)
    _kenh(may, voice_profile="giong-mau")
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]


# ── khai sai: mã 2 ───────────────────────────────────────────────────────────────────

def test_profile_khai_trong_channel_yml_KHONG_co_trong_kho_giong_thi_MA_2(
        may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, profiles=("giong-mau",))
    _tram_video(tmp_path, monkeypatch)
    _kenh(may, voice_profile="giong-khong-ton-tai")
    kq = DR.kham()
    assert kq["code"] == SC.CONTRACT_ERROR
    assert any("giong-khong-ton-tai" in x for x in kq["fail"]), kq["fail"]


def test_VOICES_DIR_doi_cho_kho_giong(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, profiles=())
    _tram_video(tmp_path, monkeypatch)
    kho = tmp_path / "kho-rieng"
    kho.mkdir()
    (kho / "giong-mau.txt").write_text("x", encoding="utf-8")
    monkeypatch.setenv("VOICES_DIR", str(kho))
    _kenh(may, voice_profile="giong-mau")
    assert DR.kham()["code"] == SC.OK


# ── phiên bản hợp đồng ───────────────────────────────────────────────────────────────

def test_phien_ban_hop_dong_THAP_HON_yeu_cau_thi_DO(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, voice_ver="0.9.0")
    _tram_video(tmp_path, monkeypatch)
    kq = DR.kham()
    assert kq["code"] == SC.STATION_MISSING
    assert any("0.9.0" in x and "voice_studio" in x for x in kq["fail"]), kq["fail"]


def test_chua_cai_package_vao_venv_thi_DO_kem_lenh_pip(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, video_ver=None)
    _tram_video(tmp_path, monkeypatch)
    kq = DR.kham()
    assert kq["code"] == SC.STATION_MISSING
    assert any("pip install" in x and "video_studio" in x for x in kq["fail"]), kq["fail"]


def test_yeu_cau_phien_ban_doc_tu_file_requirements():
    """Ngưỡng là DỮ LIỆU trong repo, không phải hằng số giấu trong mã: người nâng hợp đồng
    sửa một dòng văn bản, không phải đi tìm trong `doctor.py`."""
    for loai, goi in (("voice", "voice_studio"), ("video", "video_studio")):
        f = ROOT / f"requirements-{loai}.txt"
        assert f.is_file(), f"thiếu {f.name}"
        ten, nguong = SC.min_version(loai)
        assert ten == goi and nguong, f"{f.name} không khai ngưỡng nào đọc được"
        assert DR.CAN_PHIEN_BAN[goi] == nguong


# ── CLI ──────────────────────────────────────────────────────────────────────────────

def test_CLI_json_van_mot_dong_cuoi_va_ma_thoat_that(may, tmp_path, monkeypatch, capsys):
    _tram_giong(tmp_path, monkeypatch, station_json=False)
    ma = DR.main(["--json"])
    out, _ = capsys.readouterr()
    assert ma == SC.STATION_MISSING
    kq = json.loads(out.strip().splitlines()[-1])
    assert kq["ok"] is False and kq["code"] == SC.STATION_MISSING


def test_chay_that_bang_dong_lenh(may, tmp_path, monkeypatch):
    """Chạy `doctor.py` như người gõ tay: bắt được lỗi chỉ xuất hiện ngoài tiến trình test
    (thiếu `sys.path`, hỏng encoding console)."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "doctor.py")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == SC.OK, r.stderr
    assert "agent-voice-studio" in r.stderr
