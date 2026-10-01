# -*- coding: utf-8 -*-
"""Ba lỗi lượt truyện đầu trên Mac mini (01/10/2026) — mỗi lỗi một cổng, ở `doctor` VÀ ở bộ
cài lịch, để máy mới bắt được TRƯỚC khi chạy chứ không phải sau hàng giờ TTS:

    P1-19  job launchd gọi `<chiến dịch>/run.ps1` không có → mã 64 sau 0 s
    P0-8   faster-whisper + PyAV 19: import được, `decode_audio` ném TypeError
    P0-9   ffmpeg Homebrew core thiếu drawtext/subtitles/ass → make_video chết ở pass 1

Không mạng, không ffmpeg thật, không venv giọng thật: mọi lệnh ngoài được giả ở tầng
`subprocess.run`. Phép thử CHẠY THẬT nằm ở `test_runtime_smoke.py` (cổng CI 2 OS).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "runners"))
sys.path.insert(0, str(ROOT / "scripts" / "runners" / "story"))
import doctor as DR  # noqa: E402
import install_launchd as IL  # noqa: E402
import runner_deps as RD  # noqa: E402
import studio_contract as SC  # noqa: E402
import truyen_paths as TP  # noqa: E402

TRUYEN = "studio.marketing.daily-story"

# Mẩu thật của `ffmpeg -hide_banner -filters` (Gyan 8.1 full) — đủ để parser không trôi.
FILTERS_DU = """Filters:
  T.. = Timeline support
  .S. = Slice threading
  ... = Command support
  A = Audio input/output
 ... abench            A->A       Benchmark part of a filtergraph.
 ... ass               V->V       Render ASS subtitles onto input video using the libass library.
 T.C drawtext          V->V       Draw text on top of video frames using libfreetype library.
 ... subtitles         V->V       Render text subtitles onto input video using the libass library.
 TSC scale             V->V       Scale the input video size and/or convert the image format.
 ... amix              N->A       Audio mixing.
"""
# Homebrew core 9.x: không libfreetype, không libass.
FILTERS_CORE = "\n".join(d for d in FILTERS_DU.splitlines()
                         if not any(x in d for x in ("drawtext", "subtitles", " ass ")))


def _gia_run(monkeypatch, stdout="", stderr="", rc=0, loi=None):
    goi = []

    def run(argv, **kw):
        goi.append(argv)
        if loi:
            raise loi
        return subprocess.CompletedProcess(argv, rc, stdout, stderr)
    monkeypatch.setattr(RD.subprocess, "run", run)
    return goi


# ── P0-9: bộ lọc ffmpeg ──────────────────────────────────────────────────────

def test_doc_ten_bo_loc_tu_dau_ra_ffmpeg():
    assert {"drawtext", "subtitles", "ass", "scale", "amix", "abench"} <= RD.ten_bo_loc(FILTERS_DU)
    assert "Timeline" not in RD.ten_bo_loc(FILTERS_DU)


def test_ffmpeg_DU_bo_loc(monkeypatch):
    goi = _gia_run(monkeypatch, stdout=FILTERS_DU)
    assert RD.ffmpeg_thieu_bo_loc("/x/ffmpeg") == []
    assert goi == [["/x/ffmpeg", "-hide_banner", "-filters"]]


def test_ffmpeg_core_THIEU_ca_ba_bo_loc_truyen(monkeypatch):
    _gia_run(monkeypatch, stdout=FILTERS_CORE)
    assert RD.ffmpeg_thieu_bo_loc("ffmpeg") == ["drawtext", "subtitles", "ass"]


@pytest.mark.parametrize("kw", [{"loi": FileNotFoundError("ffmpeg")}, {"rc": 1},
                                {"stdout": "rác không phải bảng bộ lọc"}])
def test_ffmpeg_KHONG_chay_duoc_la_None(monkeypatch, kw):
    _gia_run(monkeypatch, **kw)
    assert RD.ffmpeg_thieu_bo_loc("ffmpeg") is None


@pytest.mark.parametrize("he,can", [("darwin", "ffmpeg-full"), ("win32", "Gyan")])
def test_lenh_cai_ffmpeg_theo_he(he, can):
    assert can in RD.lenh_cai_ffmpeg(he)


def test_ff_exe_FFMPEG_DIR_thang_keg_va_PATH():
    p = TP.ff_exe("ffmpeg", env={"FFMPEG_DIR": "/khai"}, registry=False, platform="darwin",
                  is_file=lambda x: True, which=lambda n: "/opt/homebrew/bin/ffmpeg")
    assert Path(p).parent == Path("/khai").resolve() or p.startswith("/khai")


def test_ff_exe_keg_ffmpeg_full_THANG_ffmpeg_core_tren_PATH_macOS():
    """Máy có cả core (trên PATH) lẫn ffmpeg-full (keg-only): phải dùng bản đủ bộ lọc."""
    p = TP.ff_exe("ffmpeg", env={}, registry=False, platform="darwin",
                  is_file=lambda x: "ffmpeg-full" in x,
                  which=lambda n: "/opt/homebrew/bin/ffmpeg")
    assert "/opt/homebrew/opt/ffmpeg-full/bin" in p.replace("\\", "/")


def test_ff_exe_Windows_KHONG_do_keg():
    p = TP.ff_exe("ffmpeg", env={}, registry=False, platform="win32",
                  is_file=lambda x: True, which=lambda n: r"C:\ff\ffmpeg.exe")
    assert p == r"C:\ff\ffmpeg.exe"


def test_make_video_goi_ffmpeg_QUA_ff_exe():
    """make_video dùng đúng file doctor kiểm — không tự `shutil.which` riêng."""
    t = (ROOT / "scripts/runners/story/make_video.py").read_text(encoding="utf-8")
    assert "truyen_paths.ff_exe(name)" in t
    assert "shutil.which(name)" not in t


# ── P0-8: faster-whisper + PyAV, kiểm HÀNH VI ────────────────────────────────

def test_decode_audio_OK(monkeypatch):
    goi = _gia_run(monkeypatch, stdout="DECODE_OK 16000\n")
    assert RD.kiem_decode_audio("/v/python") == (True, "DECODE_OK 16000")
    assert goi[0][0] == "/v/python" and "decode_audio" in goi[0][2]


def test_decode_audio_PyAV19_TypeError_la_False_kem_dong_loi(monkeypatch):
    _gia_run(monkeypatch, rc=1, stderr=(
        "Traceback (most recent call last):\n  File \"faster_whisper/audio.py\", line 46\n"
        "TypeError: open() got an unexpected keyword argument 'metadata_errors'\n"))
    ok, chi_tiet = RD.kiem_decode_audio("/v/python")
    assert ok is False and "metadata_errors" in chi_tiet


def test_decode_audio_python_khong_chay_duoc_la_None(monkeypatch):
    _gia_run(monkeypatch, loi=FileNotFoundError("/v/python"))
    assert RD.kiem_decode_audio("/v/python")[0] is None


def test_requirements_runners_GHIM_cap_faster_whisper_av():
    dong = {d.split("#", 1)[0].strip().split(">")[0].split("=")[0].split("<")[0]:
            d.split("#", 1)[0].strip()
            for d in (ROOT / RD.REQ_FILE).read_text(encoding="utf-8").splitlines()
            if d.split("#", 1)[0].strip()}
    assert dong["av"] == "av>=15,<19", "PyAV 19 bỏ `metadata_errors` (P0-8) — trần phải <19"
    assert dong["faster-whisper"] == "faster-whisper>=1.2,<1.3"


# ── nhận diện truyện: runner RIÊNG của chiến dịch ────────────────────────────

def test_runner_rieng_goi_engine_truyen_LA_truyen(tmp_path):
    (tmp_path / "run-daily-truyen-p2.ps1").write_text(
        "& $py (Join-Path $eng 'daily_truyen.py') --state p2", encoding="utf-8")
    assert RD.la_truyen(tmp_path, "run-daily-truyen-p2.ps1")
    assert RD.la_truyen(tmp_path, "run-daily-truyen.ps1")
    (tmp_path / "run-blog.ps1").write_text("& python gen_article.py", encoding="utf-8")
    assert not RD.la_truyen(tmp_path, "run-blog.ps1")
    assert not RD.la_truyen(tmp_path, "khong-co.ps1")


def test_runner_dang_dung_cong_RUNNER_TRUYEN_khi_co_truyen_rieng(monkeypatch, tmp_path):
    monkeypatch.setattr(RD, "chien_dich_co_runner", lambda st: [
        {"dir": tmp_path, "runner": "run-daily-truyen-p2.ps1", "truyen": True}])
    assert RD.runner_dang_dung(tmp_path) == {"run-daily-truyen-p2.ps1", "run-daily-truyen.ps1"}


# ── P1-19: run.ps1 — bộ cài lịch ─────────────────────────────────────────────

def _tram_truyen(tmp_path, runner=None, tao=None):
    tram = tmp_path / "tram"
    tram.mkdir()
    k = {"channel": "nghe-tien-truyen", "campaign": "p2"}
    if runner:
        k["runner"] = runner
    (tram / IL.KHAI_FILE).write_text(json.dumps({TRUYEN: k}), encoding="utf-8")
    if tao:
        d = tram / "nghe-tien-truyen" / "p2"
        d.mkdir(parents=True)
        (d / tao).write_text("# gia", encoding="utf-8")
    return tram


def _args(tram):
    return IL._parser().parse_args(["--station", str(tram), "--dry-run", "--only", TRUYEN])


def test_install_launchd_DRY_RUN_thieu_run_ps1_la_ma_2_kem_lenh_scaffold(tmp_path):
    """Đúng cảnh P1-19: P2 chỉ có runner riêng, job gọi run.ps1."""
    tram = _tram_truyen(tmp_path, tao="run-daily-truyen-p2.ps1")
    with pytest.raises(SC.ContractError) as e:
        IL.lam(_args(tram))
    m = str(e.value)
    assert "run.ps1" in m and TRUYEN in m and "P1-19" in m
    assert str(RD.MAU_RUN_PS1).replace("\\", "/") in m.replace("\\", "/"), "thiếu lệnh scaffold"


def test_install_launchd_CO_run_ps1_thi_qua(tmp_path):
    job = IL.lam(_args(_tram_truyen(tmp_path, tao="run.ps1")))["jobs"][0]
    assert job["runner"] == "run.ps1"


def test_install_launchd_runner_khai_rieng_thi_kiem_DUNG_file_do(tmp_path):
    with pytest.raises(SC.ContractError):
        IL.lam(_args(_tram_truyen(tmp_path, runner="run-p2.ps1", tao="run.ps1")))
    tram2 = tmp_path / "b"
    tram2.mkdir()
    job = IL.lam(_args(_tram_truyen(tram2, runner="run-p2.ps1", tao="run-p2.ps1")))["jobs"][0]
    assert job["runner"] == "run-p2.ps1"


def test_runner_thieu_bo_qua_job_KHONG_goi_file_chien_dich(tmp_path):
    """worker/poller chạy runner của repo (mẫu không có `__RUNNER__`) — không kiểm."""
    assert IL.runner_thieu(tmp_path, {"studio.marketing.worker": {"channel": "k",
                                                                  "campaign": "c"}}) == []


# ── P1-19: run.ps1 — doctor ──────────────────────────────────────────────────

def test_doctor_job_launchd_thieu_run_ps1_la_DO_ma_2(tmp_path, monkeypatch):
    monkeypatch.setattr(RD, "chien_dich_co_runner", lambda st: [])
    tram = _tram_truyen(tmp_path, tao="run-daily-truyen-p2.ps1")
    so = DR.So()
    DR.kham_run_ps1(so, tram)
    assert so.code == SC.CONTRACT_ERROR, so.fail
    assert any("run.ps1" in x and TRUYEN in x for x in so.fail)


def test_doctor_job_launchd_CO_run_ps1_thi_khong_do(tmp_path, monkeypatch):
    monkeypatch.setattr(RD, "chien_dich_co_runner", lambda st: [])
    so = DR.So()
    DR.kham_run_ps1(so, _tram_truyen(tmp_path, tao="run.ps1"))
    assert so.fail == [] and so.code == SC.OK


def test_doctor_chien_dich_co_runner_thieu_run_ps1_la_NHAC(tmp_path, monkeypatch):
    """Không có launchd.json (máy Windows gọi thẳng runner): nhắc, không đỏ."""
    cd = tmp_path / "k" / "c"
    cd.mkdir(parents=True)
    monkeypatch.setattr(RD, "chien_dich_co_runner", lambda st: [
        {"dir": cd, "runner": "run-daily-truyen-p2.ps1", "truyen": True}])
    so = DR.So()
    DR.kham_run_ps1(so, tmp_path)
    assert so.fail == [] and so.code == SC.OK
    assert any("run.ps1" in x and str(cd) in x for x in so.warn)
    (cd / "run.ps1").write_text("# gia", encoding="utf-8")
    so = DR.So()
    DR.kham_run_ps1(so, tmp_path)
    assert so.warn == []


# ── P0-8 / P0-9 — doctor ─────────────────────────────────────────────────────

def _truyen_gia(monkeypatch, thieu_loc, decode):
    monkeypatch.setattr(TP, "ff_exe", lambda name: f"/gia/{name}")
    monkeypatch.setattr(RD, "ffmpeg_thieu_bo_loc", lambda ff, can=RD.BO_LOC_TRUYEN: thieu_loc)
    monkeypatch.setattr(RD, "kiem_decode_audio", lambda py: decode)


def test_doctor_truyen_ffmpeg_thieu_drawtext_la_DO(monkeypatch):
    _truyen_gia(monkeypatch, ["drawtext", "subtitles", "ass"], (True, "DECODE_OK 16000"))
    so = DR.So()
    DR._kham_truyen(so, "/v/python")
    assert so.code == SC.CONTRACT_ERROR
    assert any("drawtext" in x and "P0-9" in x and "/gia/ffmpeg" in x for x in so.fail)


def test_doctor_truyen_ffmpeg_khong_chay_duoc_la_DO(monkeypatch):
    _truyen_gia(monkeypatch, None, (True, "DECODE_OK 16000"))
    so = DR.So()
    DR._kham_truyen(so, None)
    assert so.code == SC.CONTRACT_ERROR


def test_doctor_truyen_decode_audio_hong_la_DO(monkeypatch):
    _truyen_gia(monkeypatch, [], (False, "TypeError: ... 'metadata_errors'"))
    so = DR.So()
    DR._kham_truyen(so, "/v/python")
    assert so.code == SC.CONTRACT_ERROR
    assert any("decode_audio" in x and "P0-8" in x and "pip install" in x for x in so.fail)


def test_doctor_truyen_DU_thi_xanh(monkeypatch):
    _truyen_gia(monkeypatch, [], (True, "DECODE_OK 16000"))
    so = DR.So()
    DR._kham_truyen(so, "/v/python")
    assert so.fail == [] and so.code == SC.OK
    assert any("đủ bộ lọc" in x for x in so.info)
    assert any("decode_audio chạy được" in x for x in so.info)


def test_doctor_kham_runner_CHI_kiem_truyen_khi_tram_co_truyen(monkeypatch, tmp_path):
    goi = []
    monkeypatch.setattr(DR, "_kham_truyen", lambda so, py: goi.append(py))
    monkeypatch.setattr(DR.SP, "voice_station", lambda *a, **k: None)
    monkeypatch.setattr(RD, "runner_dang_dung", lambda st: {"run-weekly-news.ps1"})
    monkeypatch.setattr(RD, "tim_last30days", lambda: Path("/l30.py"))
    monkeypatch.setattr(RD, "kiem_nhac_nen", lambda d: {"dir": None, "co_thu_vien": False,
                                                       "styles": [], "thieu_mp3": []})
    DR.kham_runner(DR.So(), tmp_path)
    assert goi == [], "trạm chỉ có tin mà vẫn kiểm truyện"
    monkeypatch.setattr(RD, "runner_dang_dung", lambda st: {"run-daily-truyen.ps1"})
    DR.kham_runner(DR.So(), tmp_path)
    assert goi == [None]


def test_kham_run_ps1_da_dang_ky_vao_doctor():
    assert DR.kham_run_ps1 in DR.KHAM_THEM


# ── station export nhắc run.ps1 (RUNBOOK-DOI-MAY §5) ─────────────────────────

def test_export_liet_ke_chien_dich_thieu_run_ps1(tmp_path, monkeypatch):
    import station as ST
    st = tmp_path / "tram"
    cd = st / "k" / "c"
    cd.mkdir(parents=True)
    (cd / "campaign.md").write_text("---\nid: c\n---\n", encoding="utf-8")
    monkeypatch.setattr(ST.RD, "chien_dich_co_runner", lambda s: [
        {"dir": cd, "runner": "run-p2.ps1", "truyen": True}])
    kq = ST.export_station(st, tmp_path / "goi.zip", dry_run=True)
    assert kq["missing_run_ps1"] == ["k/c"]
    (cd / "run.ps1").write_text("# gia", encoding="utf-8")
    assert ST.export_station(st, tmp_path / "goi.zip", dry_run=True)["missing_run_ps1"] == []
