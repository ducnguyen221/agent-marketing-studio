# -*- coding: utf-8 -*-
"""`doctor` — phần HAI TRẠM NĂNG LỰC của hợp đồng ba trạm (gói P2-G3, sửa 21/09/2026).

Phần F17 (hai chế độ cài) đã có cổng riêng ở `test_gitignore_guard.py`. File này chỉ đo
phần nối thêm: trạm giọng (`agent-voice-studio`) và trạm video (`agent-video-studio`).

**PHÂN TẦNG NĂNG LỰC — luật hiện hành, và là lý do file này tồn tại:**

  LÕI            viết bài + đăng. Luôn chạy, không cần trạm nào ngoài trạm nội dung.
                 Lõi hỏng ⇒ `doctor` ĐỎ: mã 2 (cấu hình sai) hoặc mã 3 (chưa cài xong).
  NĂNG LỰC THÊM  giọng · video. Thiếu ⇒ **chưa bật**, KHÔNG phải hỏng:
                 `doctor` ghi một dòng thông tin/nhắc và trả **mã 0**.

Bản trước trả **mã 3** khi một kênh khai `voice_profile` mà máy chưa có trạm giọng. Nó
làm đúng một việc: bảo người mới clone repo về rằng bản cài của họ "CHƯA CÀI XONG" trong
khi họ chỉ định viết bài. Mã 3 nay chỉ xuất hiện **đúng lúc chạm bước cần giọng/video**
(xem `test_voice_adapter.py`, `test_make_podcast.py`), không phải lúc khám máy.

  khai sai  → VẪN ĐỎ mã 2, nhưng chỉ khi năng lực ĐÃ BẬT: profile khai trong `channel.yml`
              mà kho giọng có thật lại không có. Đó là mâu thuẫn trong cấu hình của chính
              người dùng — "sửa cái đang sai", không phải "cài tiếp".
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
        # Một profile = `<tên>.wav` (clip mẫu) + `<tên>.txt` (lời của clip). Engine giọng
        # chỉ đếm `.wav`, nên fixture phải dựng đúng cặp đó.
        (voices / f"{p}.wav").write_bytes(b"RIFF")
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


# ── chưa khai gì: một dòng thông tin "chưa bật", mã 0 ────────────────────────────────

def test_chua_khai_tram_nao_thi_CHUA_BAT_chu_khong_phai_HONG(may):
    """Chỉ đạo 21/09: cài xong là viết bài và đăng được ngay. Người chưa làm audio/video
    không được nhìn thấy một chữ đỏ nào vì thứ họ chưa cần."""
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert not kq["fail"]
    chu = "\n".join(kq["info"])
    for phai_co in ("giọng: chưa bật", "video: chưa bật", "cần khi bạn muốn",
                    "agent-voice-studio", "agent-video-studio"):
        assert phai_co in chu, f"dòng thông tin thiếu {phai_co!r}:\n{chu}"


def test_dong_CHUA_BAT_noi_ro_LOI_van_chay(may):
    """Không nói "viết bài và đăng không cần nó" thì dòng "chưa bật" vẫn đọc như một lỗi."""
    chu = "\n".join(DR.kham()["info"])
    assert chu.count("KHÔNG cần nó") >= 2, chu


# ── đã khai mà chưa đủ: NHẮC, vẫn mã 0 ───────────────────────────────────────────────

def test_khai_tram_giong_ma_chua_co_station_json_thi_NHAC_chu_KHONG_DO(
        may, tmp_path, monkeypatch):
    """Biến trỏ vào một trạm giọng dựng dở = năng lực chưa dùng được. Nó không chặn việc
    viết bài, nên nó không được phép làm cả bản cài đỏ."""
    _tram_giong(tmp_path, monkeypatch, station_json=False)
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    chu = _chu(kq)
    assert "station.json" in chu and "voice-studio init" in chu
    assert any("giọng" in x for x in kq["warn"]), kq["warn"]


def test_ten_bien_CU_van_chay_nhung_co_canh_bao(may, tmp_path, monkeypatch):
    """`OMNIVOICE_DIR` trỏ thư mục ENGINE. Máy đang chạy lịch thật dùng tên này, nên nó
    phải còn hiệu lực — nhưng im lặng chấp nhận thì không ai đổi sang tên mới bao giờ."""
    goc = _tram_giong(tmp_path, monkeypatch)
    monkeypatch.delenv("VOICE_STATION")
    monkeypatch.setenv("OMNIVOICE_DIR", str(goc / "omnivoice"))
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert any("OMNIVOICE_DIR" in x and "VOICE_STATION" in x for x in kq["warn"]), kq["warn"]


def test_khai_tram_video_ma_chua_co_station_json_thi_NHAC_chu_KHONG_DO(
        may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch)
    _tram_video(tmp_path, monkeypatch, station_json=False)
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert any("video-studio init" in x for x in kq["warn"]), kq["warn"]


def test_kenh_khai_voice_profile_KHONG_lam_ca_ban_cai_DO(may):
    """Một kênh khai `voice_profile` là lời hẹn cho về sau, không phải lỗi của hôm nay.

    Bản trước trả mã 3 ở đây. Hệ quả: ai chép `channel.yml` mẫu về cũng thấy bản cài của
    mình "CHƯA CÀI XONG" ngay phút đầu — và học được rằng `doctor` hay kêu oan."""
    _kenh(may, voice_profile="giong-mau")
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    chu = "\n".join(kq["warn"])
    assert "kenh-a" in chu and "agent-voice-studio" in chu, kq["warn"]
    # và phải nói TRƯỚC cho người dùng biết bước nào sẽ dừng, dừng bằng mã nào
    assert "mã 3" in chu, kq["warn"]


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


def test_CHI_co_loi_mau_txt_ma_THIEU_wav_thi_van_DO(may, tmp_path, monkeypatch):
    """Xanh giả nguy hiểm hơn không có cổng: engine giọng coi profile là tồn tại **khi và
    chỉ khi** có `<tên>.wav` (`voice_studio.profiles.list_profiles`). Doctor nới hơn engine
    nghĩa là nó báo ổn, rồi `speak` trả mã 2 giữa một lượt chạy lúc 18h."""
    goc = _tram_giong(tmp_path, monkeypatch, profiles=())
    _tram_video(tmp_path, monkeypatch)
    (goc / "omnivoice" / "voices" / "giong-mau.txt").write_text("x", encoding="utf-8")
    _kenh(may, voice_profile="giong-mau")
    kq = DR.kham()
    assert kq["code"] == SC.CONTRACT_ERROR
    assert any("giong-mau.wav" in x for x in kq["fail"]), kq["fail"]


def test_VOICES_DIR_doi_cho_kho_giong(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, profiles=())
    _tram_video(tmp_path, monkeypatch)
    kho = tmp_path / "kho-rieng"
    kho.mkdir()
    (kho / "giong-mau.wav").write_bytes(b"RIFF")
    monkeypatch.setenv("VOICES_DIR", str(kho))
    _kenh(may, voice_profile="giong-mau")
    assert DR.kham()["code"] == SC.OK


# ── phiên bản hợp đồng ───────────────────────────────────────────────────────────────

def test_phien_ban_hop_dong_THAP_HON_yeu_cau_thi_NHAC_kem_SO(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, voice_ver="0.9.0")
    _tram_video(tmp_path, monkeypatch)
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert any("0.9.0" in x and "voice_studio" in x for x in kq["warn"]), kq["warn"]


def test_chua_cai_package_vao_venv_thi_NHAC_kem_lenh_pip(may, tmp_path, monkeypatch):
    _tram_giong(tmp_path, monkeypatch, video_ver=None)
    _tram_video(tmp_path, monkeypatch)
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert any("pip install" in x and "video_studio" in x for x in kq["warn"]), kq["warn"]


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
    """Trạm nội dung — LÕI — chưa có: đó mới là "chưa cài xong", và nó vẫn là mã 3."""
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tmp_path / "khong-co-tram"))
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


# ══ CỔNG CỦA LUẬT PHÂN TẦNG ══════════════════════════════════════════════════════════
#
# Các test trên đo từng ca. Cái dưới đo chính LUẬT: không một nhánh nào của phần năng lực
# được phép đẩy mã thoát lên 3. Thiếu nó thì một nhánh mới thêm vào ngày mai lại lặng lẽ
# dựng lại đúng hành vi vừa bỏ, và không ca nào ở trên đi qua nhánh đó.

def test_KHONG_nhanh_nao_cua_phan_NANG_LUC_duoc_phep_bao_THIEU(may, tmp_path, monkeypatch):
    class Cam(DR.So):
        def thieu(self, msg):                       # noqa: D102
            raise AssertionError(
                "phần năng lực gọi so.thieu() ⇒ doctor trả mã 3 vì thiếu giọng/video: " + msg)

    canh = [
        lambda: None,                                                   # chưa khai gì
        lambda: _kenh(may, voice_profile="giong-mau"),                  # kênh khai, chưa có trạm
        lambda: _tram_giong(tmp_path, monkeypatch, station_json=False),
        lambda: monkeypatch.setenv("VOICE_STATION", str(tmp_path / "khong-ton-tai")),
        lambda: (_tram_giong(tmp_path, monkeypatch, voice_ver="0.9.0"),
                 _tram_video(tmp_path, monkeypatch)),
        lambda: (_tram_giong(tmp_path, monkeypatch, video_ver=None),
                 _tram_video(tmp_path, monkeypatch)),
        lambda: (_tram_giong(tmp_path, monkeypatch, profiles=()),
                 _kenh(may, voice_profile="giong-mau")),
    ]
    for i, dung in enumerate(canh):
        dung()
        so = Cam()
        DR.kham_nang_luc(so, may)
        assert so.code != SC.STATION_MISSING, f"cảnh {i}: {so.fail}"


# ══ REVIEW-P2 N4 + N12 — hai phép so khớp "đúng trên giấy, sai trên máy này" ══

def test_canh_bao_cloud_bat_duoc_ONEDRIVE_CO_HAU_TO_CONG_TY():
    """So khớp TUYỆT ĐỐI với "OneDrive" không bao giờ nổ ở nơi dùng tài khoản doanh
    nghiệp: thư mục thật tên `OneDrive - <tên công ty>`, và macOS đặt ở
    `Library/CloudStorage/OneDrive-…`. Cảnh báo không bao giờ nổ là cảnh báo không tồn
    tại — và nó nhắm đúng cái cây đang chứa trạm."""
    from pathlib import Path as _P
    for d in ("OneDrive - Mot Cong Ty", "OneDrive-MotCongTy", "CloudStorage",
              "My Drive (nguoi-dung)", "Dropbox", "SharePoint"):
        assert DR._trong_cloud(_P("/nha/toi") / d / "repo"), f"trượt {d!r}"


def test_canh_bao_cloud_KHONG_bat_ten_chi_TINH_CO_giong():
    """Khớp theo tiền tố mà không neo ranh giới thì `onedriver-notes` cũng thành cloud."""
    from pathlib import Path as _P
    for d in ("onedriver-notes", "dropboxes", "mydrives"):
        assert DR._trong_cloud(_P("/nha/toi") / d / "repo") is None, f"bắt oan {d!r}"


def test_so_phien_ban_hai_phan_KHONG_thua_ba_phan():
    """`_so("1.0") < _so("1.0.0")` là True nếu so tuple khác độ dài ⇒ trạm khai
    `API_VERSION = "1.0"` bị đỏ mã 3 OAN, và cả bộ cài đứng vì một dấu chấm."""
    assert DR._so("1.0") == DR._so("1.0.0")
    assert DR._so("1.1") > DR._so("1.0.0")
    assert DR._so("2.0") > DR._so("1.9.9")


def test_so_phien_ban_PRE_RELEASE_khong_duoc_coi_la_ban_chinh():
    """`1.0.0-rc1` == `1.0.0` thì một bản thử nghiệm lọt qua cổng hợp đồng."""
    assert DR._so("1.0.0-rc1") < DR._so("1.0.0")


def test_doctor_noi_ra_bien_env_KHONG_AI_DOC(tmp_path, monkeypatch):
    """REVIEW-P2 N11 (nửa còn lại). `.env` nhận mọi dòng người ta gõ vào; `doctor` phải
    nói thẳng dòng nào không có tác dụng, nhất là biến mà chỉ `.ps1` đọc."""
    repo = tmp_path / "repo"
    (repo / "scripts" / "lib").mkdir(parents=True)
    (repo / "install.ps1").write_text("$env:MARKETING_STUDIO_PY\n", encoding="utf-8")
    (repo / "scripts" / "lib" / "x.py").write_text(
        'secret_env("VOICE_STATION")\n', encoding="utf-8")
    so = DR.So()
    (repo / DR.SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "embedded"}), encoding="utf-8")
    (repo / ".env").write_text("VOICE_STATION=/a\nMARKETING_STUDIO_PY=/b\nLA_HOAC=/c\n",
                               encoding="utf-8")
    DR._kham_env_khong_ai_doc(so, repo)
    assert so.warn, "khong noi gi ve bien khong ai doc"
    t = " ".join(so.warn)
    assert "MARKETING_STUDIO_PY" in t and "LA_HOAC" in t
    assert "VOICE_STATION" not in t, "bien DOC DUOC ma van bi keu la bao oan"
    assert "PowerShell" in t


def _repo_embedded(tmp_path, noi_dung_env: str):
    """Repo giả ở chế độ `embedded`, có đúng một script đọc `VOICE_STATION` qua secret_env."""
    repo = tmp_path / "repo"
    (repo / "scripts" / "lib").mkdir(parents=True)
    (repo / "install.ps1").write_text("$env:MARKETING_STUDIO_PY\n", encoding="utf-8")
    (repo / "scripts" / "lib" / "x.py").write_text('secret_env("VOICE_STATION")\n',
                                                   encoding="utf-8")
    (repo / DR.SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "embedded"}), encoding="utf-8")
    (repo / ".env").write_text(noi_dung_env, encoding="utf-8")
    return repo


def test_dong_env_CHUA_DIEN_thi_KHONG_bi_keu(tmp_path):
    """"Clone là chạy": bộ cài `embedded` chép nguyên `.env.example` thành `.env`, nên
    người dùng chưa gõ một chữ nào đã có ~27 dòng `TÊN=` rỗng trong đó. Kêu về chúng ngay
    phút đầu là chào người mới bằng một cảnh báo về thứ họ chưa làm — và dạy họ rằng cảnh
    báo của `doctor` không đáng đọc.

    Cảnh báo này nói "bạn điền vào chỗ không ai nhìn". Chưa điền thì chưa có gì để nói."""
    repo = _repo_embedded(tmp_path, "MARKETING_STUDIO_PY=\nLA_HOAC=\nVOICE_STATION=\n")
    so = DR.So()
    DR._kham_env_khong_ai_doc(so, repo)
    assert not so.warn, so.warn


def test_dong_env_DA_DIEN_ma_khong_ai_doc_thi_VAN_keu(tmp_path):
    """Nới ở trên không được phép nuốt luôn ca thật: đã gõ giá trị vào thì phải được báo."""
    repo = _repo_embedded(tmp_path, "MARKETING_STUDIO_PY=\nLA_HOAC=D:/x\n")
    so = DR.So()
    DR._kham_env_khong_ai_doc(so, repo)
    assert so.warn and "LA_HOAC" in " ".join(so.warn), so.warn
    assert "MARKETING_STUDIO_PY" not in " ".join(so.warn), so.warn


def test_doctor_im_lang_khi_env_toan_bien_doc_duoc(tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts" / "lib").mkdir(parents=True)
    (repo / "install.ps1").write_text("x", encoding="utf-8")
    (repo / "scripts" / "lib" / "x.py").write_text('secret_env("VOICE_STATION")\n',
                                                    encoding="utf-8")
    (repo / DR.SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "embedded"}), encoding="utf-8")
    (repo / ".env").write_text("VOICE_STATION=/a\n", encoding="utf-8")
    so = DR.So()
    DR._kham_env_khong_ai_doc(so, repo)
    assert not so.warn
