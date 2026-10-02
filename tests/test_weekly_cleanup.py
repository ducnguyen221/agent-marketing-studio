# -*- coding: utf-8 -*-
"""Cổng job dọn dung lượng hằng tuần (SUBTASK-WIN-RUNTIME-2 §2).

Trạm giả đủ bốn thứ job đụng tới: media quá hạn ĐÃ ĐĂNG (phải dời), media quá hạn CHƯA có bằng
chứng (phải giữ), thùng rác cũ/mới, log cũ/mới/to. Hai chế độ:

* `--dry-run` — Mac nghiệm thu chạy cái này trước: **không một byte nào đổi** trên đĩa.
* chạy thật — dời (không xoá) vào `_trash/<hôm nay>` kèm kê khai, đổ thùng rác theo NGÀY DỜI,
  xoá log quá 60 ngày, cắt log quá 5 MB tại chỗ, và in dòng `CLEANUP_*` cho tin Telegram.
"""
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "runners"))
import weekly_cleanup as WC  # noqa: E402

NGAY = 86400


def _file(p: Path, tuoi_ngay: float, noi_dung: bytes = b"x" * 64) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(noi_dung)
    t = time.time() - tuoi_ngay * NGAY
    os.utime(p, (t, t))
    return p


@pytest.fixture
def may(tmp_path, monkeypatch):
    """Ba trạm giả + biến môi trường trỏ vào chúng (không rò ra máy thật)."""
    mkt, giong, video = tmp_path / "mkt", tmp_path / "giong", tmp_path / "video"
    ngay = mkt / "kenh" / "hang-ngay" / "out" / "2026-09-01"
    _file(ngay / "bai.json.published.json", 20,
          json.dumps({"uploaded_at": "2026-09-01T20:00", "video_id": "v1"}).encode("utf-8-sig"))
    _file(ngay / "bai.mp4", 20, b"v" * 4096)                       # đã đăng + quá 14 ngày ⇒ DỜI
    _file(mkt / "kenh" / "hang-ngay" / "out" / "2026-09-02" / "hong.mp4", 20)  # không bằng chứng
    _file(mkt / "kenh" / "hang-ngay" / "out" / "moi" / "moi.mp4", 2)          # còn hạn
    _file(mkt / "_trash" / "2026-01-01" / "kenh" / "cu.mp4", 200)             # rác cũ ⇒ ĐỔ
    hom_nay = dt.date.today().isoformat()
    _file(mkt / "_trash" / (dt.date.today() - dt.timedelta(days=3)).isoformat() / "x.mp4", 40)
    _file(mkt / "_trash" / "ghi-chu-tay" / "giu.mp4", 400)                    # tên không phải ngày
    lc = mkt / "logs" / "launchd"
    _file(lc / "studio.marketing.daily-story.out.log", 1,
          b"dong dau\n" + b"y" * (6 * 1024 * 1024) + b"\ndong cuoi\n")    # to ⇒ CẮT
    _file(lc / "studio.marketing.worker.out.log", 1, b"nho\n")
    dl = giong / "omnivoice" / "truyen-out" / "daily-logs"
    _file(dl / "pntt_1-10_20260101.log", 90)                                  # cũ ⇒ XOÁ
    _file(dl / "pntt_301-310_20261002.log", 1)
    (video / "projects").mkdir(parents=True)
    for n in ("MARKETING_STUDIO_DATA", "WEB_REPO_DIR", "OMNIVOICE_DIR", "VIDEO_ROOT"):
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("VOICE_STATION", str(giong))
    monkeypatch.setenv("VIDEO_STATION", str(video))
    return {"mkt": mkt, "giong": giong, "video": video, "hom_nay": hom_nay,
            "ngay": ngay, "log_to": lc / "studio.marketing.daily-story.out.log",
            "log_cu": dl / "pntt_1-10_20260101.log"}


def _anh(goc: Path) -> dict:
    """Ảnh chụp cây: đường tương đối -> (cỡ, mtime)."""
    return {str(p.relative_to(goc)): (p.stat().st_size, p.stat().st_mtime)
            for p in goc.rglob("*") if p.is_file()}


def _chay(may, *doi, capsys=None):
    ma = WC.main(["--station", str(may["mkt"]), "--json", *doi])
    out = capsys.readouterr().out if capsys else ""
    return ma, out


def test_DRY_RUN_khong_cham_mot_byte(may, tmp_path, capsys):
    truoc = _anh(tmp_path)
    ma, out = _chay(may, "--dry-run", capsys=capsys)
    assert ma == 0, out
    assert _anh(tmp_path) == truoc, "dry-run đã đổi đĩa"
    assert "CLEANUP_PRUNE mode=dry-run files=1 " in out, "phải BÁO được file sẽ dời"
    assert "CLEANUP_TRASH mode=dry-run dirs=1 " in out
    assert "CLEANUP_LOGS mode=dry-run deleted=1 truncated=1" in out


def test_chay_that_doi_vao_trash_hom_nay_kem_ke_khai(may, capsys):
    ma, out = _chay(may, capsys=capsys)
    assert ma == 0, out
    dich = may["mkt"] / "_trash" / may["hom_nay"]
    assert not (may["ngay"] / "bai.mp4").exists()
    assert (dich / "kenh" / "hang-ngay" / "out" / "2026-09-01" / "bai.mp4").is_file(), \
        "DỜI, không xoá — cấu trúc tương đối giữ nguyên để hoàn tác"
    ds = sorted(dich.glob("manifest-prune-media-*.json"))
    assert len(ds) == 1, "kê khai mang giờ của lượt — hai lượt trong ngày không ghi đè nhau"
    ke_khai = json.loads(ds[0].read_text(encoding="utf-8"))
    assert ke_khai["status"] == "done"
    assert (may["mkt"] / "kenh" / "hang-ngay" / "out" / "2026-09-02" / "hong.mp4").is_file(), \
        "không bằng chứng đã đăng ⇒ GIỮ"
    assert (may["mkt"] / "kenh" / "hang-ngay" / "out" / "moi" / "moi.mp4").is_file()
    assert "CLEANUP_PRUNE mode=move files=1 bytes=4096 " in out


def test_do_trash_theo_NGAY_DOI_khong_theo_mtime(may, capsys):
    _chay(may, capsys=capsys)
    rac = may["mkt"] / "_trash"
    assert not (rac / "2026-01-01").exists(), "rác dời quá 30 ngày phải bị đổ"
    ba_ngay = (dt.date.today() - dt.timedelta(days=3)).isoformat()
    assert (rac / ba_ngay / "x.mp4").is_file(), \
        "file mtime 40 ngày nhưng mới DỜI 3 ngày ⇒ còn hạn trong thùng rác"
    assert (rac / "ghi-chu-tay" / "giu.mp4").is_file(), "tên không phải ngày ⇒ không đụng"
    assert (rac / may["hom_nay"]).is_dir(), "thứ vừa dời hôm nay không bị đổ ngay"


def test_xoay_vong_log_xoa_cu_cat_to_giu_duoi(may, capsys):
    _chay(may, capsys=capsys)
    assert not may["log_cu"].exists()
    to = may["log_to"].read_bytes()
    assert len(to) <= WC.GIU_DUOI + 100 and to.endswith(b"dong cuoi\n")
    assert to.startswith(b"[weekly_cleanup:"), "cắt phải để lại dấu cho người đọc log"
    assert (may["mkt"] / "logs" / "launchd" / "studio.marketing.worker.out.log").read_bytes() == b"nho\n"
    assert (may["giong"] / "omnivoice" / "truyen-out" / "daily-logs" /
            "pntt_301-310_20261002.log").is_file()


def test_bao_dung_luong_tung_tram(may, capsys):
    _, out = _chay(may, capsys=capsys)
    for nhan in ("marketing", "giong", "video", "trash"):
        assert f"CLEANUP_SIZE label={nhan} " in out
    assert "CLEANUP_DONE ok=1" in out


def test_KHONG_quet_thung_rac_logs_va_thu_muc_noi_bo(may):
    (may["mkt"] / "_agent-call").mkdir()
    goc = WC.goc_quet(may["mkt"], may["giong"], may["video"])
    nhan = [g.split("=", 1)[0] for g in goc]
    assert nhan == ["kenh", "tram-giong", "tram-video"]


def test_tram_giong_trung_tram_marketing_thi_khong_quet_hai_lan(may):
    goc = WC.goc_quet(may["mkt"], may["mkt"], None)
    assert [g.split("=", 1)[0] for g in goc] == ["kenh"]


def test_cau_dao_prune_tu_choi_la_ma_2_va_KHONG_doi(may, capsys, monkeypatch):
    monkeypatch.setattr(WC, "doi_media", lambda *a, **k: (2, {}))
    ma, out = _chay(may, capsys=capsys)
    assert ma == 2
    assert (may["ngay"] / "bai.mp4").is_file()


def test_thieu_tram_la_ma_3(tmp_path):
    assert WC.main(["--station", str(tmp_path / "khong-co")]) == 3


@pytest.mark.parametrize("doi", [["--days", "0"], ["--log-max-mb", "1"], ["--trash-days", "0"]])
def test_tham_so_vo_ly_la_ma_2(may, doi):
    assert WC.main(["--station", str(may["mkt"]), *doi]) == 2


# ── tin Telegram: compose_report đọc dòng CLEANUP_* ────────────────────────────

def test_compose_report_ke_dung_luong_va_so_file_da_doi():
    import compose_report as CR
    log = "\n".join([
        "=== Weekly cleanup start ===",
        "CLEANUP_PRUNE mode=move files=7 bytes=3221225472 kept=12 code=0",
        "CLEANUP_TRASH mode=purge dirs=2 bytes=1073741824",
        "CLEANUP_LOGS mode=rotate deleted=5 truncated=1",
        "CLEANUP_SIZE label=marketing bytes=7340032 path=/m",
        "CLEANUP_SIZE label=giong bytes=4294967296 path=/g",
        "CLEANUP_SIZE label=video bytes=9017753 path=/v",
        "CLEANUP_SIZE label=trash bytes=3221225472 path=/m/_trash",
        "CLEANUP_DONE ok=1",
        "=== Weekly cleanup complete ==="])
    msg = CR.build("Dọn dung lượng tuần", 0, "00:01:10", log)
    assert "Đã dời 7 file" in msg and "3,00 GB" in msg
    assert "giữ 12" in msg
    assert "giọng 4,00 GB" in msg
    assert "Đổ 2 thư mục" in msg
    assert "xoá 5 log cũ" in msg and "cắt 1" in msg


def test_compose_report_dry_run_noi_ro_la_xem_truoc():
    import compose_report as CR
    msg = CR.build("Dọn", 0, "00:00:30", "CLEANUP_PRUNE mode=dry-run files=3 bytes=10 kept=1 code=0\n"
                                          "CLEANUP_DONE ok=1")
    assert "XEM TRƯỚC" in msg and "sẽ dời 3 file" in msg


# ── vỏ PowerShell ─────────────────────────────────────────────────────────────

def _ps1():
    return (REPO / "scripts" / "runners" / "run-weekly-cleanup.ps1").read_text(encoding="utf-8-sig")


def test_vo_ps1_goi_weekly_cleanup_va_co_DryRun():
    t = _ps1()
    assert "weekly_cleanup.py" in t and "'--dry-run'" in t
    assert "exit $code" in t


def test_register_windows_CN_qua_NOTIFY_RUN_va_IgnoreNew():
    t = _ps1()
    assert "-DaysOfWeek Sunday" in t and "[string]$Time = '04:00'" in t
    assert "NOTIFY_RUN" in t and "MultipleInstances IgnoreNew" in t


def test_log_TO_nhung_VUA_GHI_thi_KHONG_cat(may, capsys):
    """Review 02/10 NS2: lượt truyện còn chạy lúc CN 04:00, daily-logs mở `"w"` — cắt dưới chân
    nó để lại một khoảng byte 0. Vừa ghi trong 1 h ⇒ để tuần sau."""
    dang = may["giong"] / "omnivoice" / "truyen-out" / "daily-logs" / "dang_chay.log"
    _file(dang, 0.001, b"z" * (6 * 1024 * 1024))
    _chay(may, capsys=capsys)
    assert dang.stat().st_size == 6 * 1024 * 1024


def test_thieu_tram_giong_thi_NOI_RA_khong_im_lang(may, capsys, monkeypatch):
    monkeypatch.delenv("VOICE_STATION")
    monkeypatch.setattr(WC.SP, "voice_station", lambda *a, **k: None)
    _, out = _chay(may, capsys=capsys)
    assert "CLEANUP_SKIP label=giong reason=no-station var=VOICE_STATION" in out
    import compose_report as CR
    assert "Bỏ qua trạm giọng" in CR.build("Dọn", 0, "00:00:10", out)


def test_prune_hong_giua_chung_bao_KHONG_RO_va_chi_ke_khai(may, capsys, monkeypatch):
    monkeypatch.setattr(WC, "doi_media", lambda *a, **k: (1, {}))
    ma, out = _chay(may, capsys=capsys)
    assert ma == 1
    assert "CLEANUP_PRUNE mode=move files=? " in out and "manifest=" in out
    import compose_report as CR
    msg = CR.build("Dọn", 1, "00:00:10", out)
    assert "chưa rõ đã dời bao nhiêu file" in msg and "manifest-prune-media-" in msg


def test_ngoai_le_buoc_1_KHONG_chan_buoc_2_3(may, capsys, monkeypatch):
    def no(*a, **k):
        raise OSError("đĩa hỏng")
    monkeypatch.setattr(WC, "doi_media", no)
    ma, out = _chay(may, capsys=capsys)
    assert ma == 1
    assert not may["log_cu"].exists(), "bước 3 vẫn phải chạy"
    assert not (may["mkt"] / "_trash" / "2026-01-01").exists(), "bước 2 vẫn phải chạy"
