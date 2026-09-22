# -*- coding: utf-8 -*-
"""Cổng `<trạm>/engine`: **hoặc không tồn tại, hoặc đủ bộ chạy** — không có trạng thái giữa.

## Sự cố đã trả giá (đêm 20→21/09/2026)

`run.ps1` của MỌI chiến dịch coi **sự tồn tại** của `<trạm>/engine` là tín hiệu "engine đã
dọn về trạm": thấy thư mục là **bỏ đường lùi** sang engine dùng chung trong thư mục nhà của
máy nguồn, rồi đi tìm runner **trong đó**. Một gói khác ghi một file cấu hình JSON vào
`<trạm>/engine/` ⇒ thư mục ra đời như **tác dụng phụ của một lệnh ghi file** ⇒ 5 task tin
theo lịch sẽ `exit 2` ("khong thay runner"), lượt đầu dính là 21/09 19:00.

Ba tính chất khiến nó đắt, và cả ba đều là lý do cổng này tồn tại:

· **im lặng** — không lệnh nào báo lỗi lúc thư mục ra đời; nó chỉ là một `mkdir` ngầm;
· **hoãn** — hậu quả rơi vào lượt LỊCH kế tiếp, cách đó nhiều giờ, ở một tiến trình khác;
· **lan** — một thư mục tắt đường lùi của **tất cả** chiến dịch cùng lúc, không riêng cái
  nào, vì `run.ps1` giống hệt nhau ở mọi chiến dịch.

## Vì sao đo `engine/` chứ không đo "ai đã tạo nó"

Cổng chỉ được nói **cái nó đo được**. Nó không biết, và không được đoán, thư mục kia ra đời
vì ai: nó đo **trạng thái** — thư mục có mặt mà không có bộ chạy — và nói ra **hai đường
sửa**, để người đọc chọn theo thứ họ biết mà cổng không biết.

Mã thoát 2 (`CONTRACT_ERROR`, "cấu hình SAI — phải sửa") chứ không phải 3 ("cài tiếp"): đây
đúng là mã mà `run.ps1` sẽ trả lúc 19:00, và một cổng trả mã khác cái mà thực tế sẽ trả thì
người đọc không nối được hai chuyện với nhau.
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
import engine_dir as ED  # noqa: E402
import studio_contract as SC  # noqa: E402

CLI = ROOT / "scripts" / "pipeline" / "check_engine.py"

BIEN = ("MARKETING_STUDIO_DATA", "MARKETING_STUDIO_HOME", "VOICE_STATION", "OMNIVOICE_DIR",
        "OMNIVOICE_PY", "VOICES_DIR", "VIDEO_STATION", "VIDEO_ROOT", "AGENT_CALL_ENGINES")


@pytest.fixture
def tram(tmp_path, monkeypatch):
    """Trạm GIẢ trong `%TEMP%`.

    Cổng này đo một thư mục trên đĩa, nên một fixture quên chặn đường phân giải mặc định sẽ
    lặng lẽ đi khám **trạm thật** của máy đang chạy test: kết quả đổi theo máy, và một lượt
    `pytest` trở thành phép đo môi trường thay vì phép đo mã.
    """
    for b in BIEN:
        monkeypatch.delenv(b, raising=False)
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))
    st = tmp_path / "tram"
    st.mkdir()
    (st / "CHANNELS.md").write_text("---\nschema: channels/1\nchannels: []\n---\n",
                                    encoding="utf-8")
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(st))
    return st


def _engine(tram: Path, *ten: str) -> Path:
    d = tram / ED.TEN_ENGINE
    d.mkdir(exist_ok=True)
    for t in ten:
        (d / t).write_text("x", encoding="utf-8")
    return d


def _chu(kq) -> str:
    return "\n".join(kq["fail"] + kq.get("warn", []))


# ── cổng của cổng ────────────────────────────────────────────────────────────────────

def test_bo_runner_bat_buoc_khong_rong_va_co_runner_cua_pipeline_tin():
    """Danh sách rỗng thì mọi test dưới đây xanh mà không đo gì."""
    assert ED.RUNNER_BAT_BUOC, "bộ runner bắt buộc rỗng — cổng không đo gì"
    assert "run-toptoday-hot.ps1" in ED.RUNNER_BAT_BUOC


def test_cong_duoc_noi_that_vao_doctor():
    """`doctor` trên máy thật phải chạy luật này, không chỉ bộ test chạy nó."""
    assert any(getattr(f, "__name__", "") == "kham_engine" for f in DR.KHAM_THEM), \
        "chưa nối kham_engine vào doctor.KHAM_THEM"


# ── ĐỎ ĐÚNG LÝ DO: thư mục ra đời vì một file JSON lạc vào ───────────────────────────

def test_engine_chi_co_mot_file_json_thi_DO_ma_2_va_NEU_DUNG_LY_DO(tram):
    """Tái dựng ĐÚNG sự cố: `engine/` chỉ chứa `engines.json`, không một runner nào."""
    _engine(tram, "engines.json")
    kq = ED.kiem(tram)
    assert kq["code"] == SC.CONTRACT_ERROR, kq
    assert kq["ok"] is False
    chu = _chu(kq)
    # đo được cái gì: thiếu runner nào, và đang có gì trong đó
    assert "run-toptoday-hot.ps1" in chu, chu
    assert "engines.json" in chu, chu
    # vì sao nguy hiểm: đường lùi bị tắt
    assert "đường lùi" in chu, chu
    # sửa thế nào: hai đường, nêu rõ cả hai
    assert ED.THU_MUC_CAU_HINH in chu, chu
    assert "xoá" in chu.lower(), chu


def test_engine_RONG_cung_DO(tram):
    """Thư mục rỗng nguy hiểm y hệt: `run.ps1` chỉ hỏi `Test-Path`, không hỏi bên trong."""
    _engine(tram)
    assert ED.kiem(tram)["code"] == SC.CONTRACT_ERROR


def test_engine_la_MOT_FILE_chu_khong_phai_thu_muc_thi_DO(tram):
    (tram / ED.TEN_ENGINE).write_text("khong phai thu muc", encoding="utf-8")
    kq = ED.kiem(tram)
    assert kq["code"] == SC.CONTRACT_ERROR
    assert "thư mục" in _chu(kq)


def test_thieu_mot_runner_trong_BO_van_DO(tram, monkeypatch):
    """Luật là "đủ bộ", không phải "có ít nhất một file". Thêm runner vào bộ bắt buộc là
    sửa MỘT dòng dữ liệu, và cổng phải đỏ ngay với thư mục chỉ có nửa bộ."""
    monkeypatch.setattr(ED, "RUNNER_BAT_BUOC", ("run-toptoday-hot.ps1", "notify-run.ps1"))
    _engine(tram, "run-toptoday-hot.ps1")
    kq = ED.kiem(tram)
    assert kq["code"] == SC.CONTRACT_ERROR
    assert "notify-run.ps1" in _chu(kq)
    assert kq["missing"] == ["notify-run.ps1"]


# ── XANH: hai trạng thái hợp lệ ──────────────────────────────────────────────────────

def test_KHONG_co_thu_muc_engine_thi_XANH(tram):
    """Trạng thái hợp lệ thứ nhất — và là trạng thái của máy thật sau khi dọn."""
    kq = ED.kiem(tram)
    assert kq["code"] == SC.OK and kq["ok"] is True
    assert kq["state"] == "vang"
    assert not kq["fail"]


def test_engine_DU_bo_chay_thi_XANH(tram):
    """Trạng thái hợp lệ thứ hai — sau khi engine thật sự dọn về trạm."""
    _engine(tram, *ED.RUNNER_BAT_BUOC, "notify-run.ps1", "paths.py")
    kq = ED.kiem(tram)
    assert kq["code"] == SC.OK and kq["state"] == "du"


def test_runner_nam_trong_THU_MUC_CON_khong_duoc_tinh_la_co(tram):
    """`run.ps1` gọi `Join-Path $engine $cfg.runner` — runner phải nằm NGAY trong `engine/`.
    Nhận một file cùng tên ở tầng sâu hơn là tự tạo XANH GIẢ."""
    d = _engine(tram)
    (d / "cu").mkdir()
    (d / "cu" / "run-toptoday-hot.ps1").write_text("x", encoding="utf-8")
    assert ED.kiem(tram)["code"] == SC.CONTRACT_ERROR


# ── doctor: cùng luật, trên trạm đang phân giải ──────────────────────────────────────

def test_doctor_DO_khi_trạm_roi_vao_trang_thai_nay(tram):
    _engine(tram, "engines.json")
    kq = DR.kham()
    assert kq["code"] == SC.CONTRACT_ERROR, kq["fail"]
    assert any("run-toptoday-hot.ps1" in x for x in kq["fail"]), kq["fail"]


def test_doctor_KHONG_keu_khi_khong_co_thu_muc_engine(tram):
    kq = DR.kham()
    assert not any(ED.TEN_ENGINE + "/" in x or "bộ chạy" in x for x in kq["fail"]), kq["fail"]


# ── CLI chạy độc lập ─────────────────────────────────────────────────────────────────

def _cli(*argv):
    return subprocess.run([sys.executable, str(CLI), *argv],
                          capture_output=True, text=True, encoding="utf-8")


def test_CLI_chay_doc_lap_tra_ma_2_va_MOT_dong_JSON_cuoi(tram):
    _engine(tram, "engines.json")
    r = _cli("--check-station", str(tram), "--json")
    assert r.returncode == SC.CONTRACT_ERROR, r.stderr
    kq = json.loads(r.stdout.strip().splitlines()[-1])
    assert kq["ok"] is False and kq["code"] == SC.CONTRACT_ERROR
    assert "run-toptoday-hot.ps1" in " ".join(kq["fail"])


def test_CLI_xanh_khi_tram_khong_co_engine(tram):
    r = _cli("--station", str(tram), "--json")
    assert r.returncode == SC.OK, r.stderr
    assert json.loads(r.stdout.strip().splitlines()[-1])["ok"] is True


def test_CLI_nhan_ca_hai_ten_co(tram):
    """`--station` (đồng bộ với `doctor`) và `--check-station` (gõ tay cho rõ nghĩa) phải
    trỏ cùng một chỗ — hai tên mà lệch nhau thì một trong hai là bẫy."""
    _engine(tram, "engines.json")
    assert _cli("--station", str(tram)).returncode == \
        _cli("--check-station", str(tram)).returncode == SC.CONTRACT_ERROR
