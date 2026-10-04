# -*- coding: utf-8 -*-
"""Cổng SUBTASK-WIN-RUNTIME-3 §4: log xoay vòng NGAY TRONG lượt chạy (job dọn tuần đã gỡ trên Mac).

Mac mini 03/10/2026: Đức gỡ `weekly-cleanup` — mỗi quy trình đã tự dọn media, chỉ còn log lớn
mãi (~0,5 MB/lượt truyện). Bốn thứ phải đúng:

* luật: `*.log` quá 60 ngày ⇒ xoá; > 5 MB ⇒ cắt giữ 1 MB cuối; file vừa ghi trong 1 h không cắt;
  `_heal_state.json` / `_heal_audit.log` và file không phải log KHÔNG bị đụng;
* gói chẩn đoán `render-stuck/<giờ>/` quá hạn ⇒ xoá;
* không bao giờ làm hỏng lượt chạy (thư mục không có, lỗi file ⇒ vẫn mã 0);
* đầu lượt tin (sau kiểm nhịp, trước rào render) và đầu lượt truyện (cạnh sweep_old) đều gọi nó.
"""
import importlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNERS = ROOT / "scripts" / "runners"
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import log_rotate as LR  # noqa: E402

PS = shutil.which("pwsh") or shutil.which("powershell")
NGAY = 86400


def _file(p: Path, noi_dung: bytes, tuoi_giay: float) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(noi_dung)
    t = time.time() - tuoi_giay
    os.utime(p, (t, t))
    return p


@pytest.fixture
def kho(tmp_path):
    d = tmp_path / "logs"
    to = b"x" * (6 * 1024 * 1024 - 10) + b"\ndong cuoi\n"
    return {
        "d": d,
        "cu": _file(d / "toptoday-AI-2026-07-01.log", b"cu\n", 61 * NGAY),
        "moi": _file(d / "toptoday-AI-2026-10-03.log", b"moi\n", NGAY),
        "to": _file(d / "pntt_301-310.log", to, 2 * 3600),
        "to_dang_ghi": _file(d / "dang-chay.log", to, 60),
        "heal_state": _file(d / "_heal_state.json", b"{}", 90 * NGAY),
        "heal_audit": _file(d / "_heal_audit.log", b"audit\n", 90 * NGAY),
        "anh": _file(d / "thumb-recap.jpg", b"jpg", 90 * NGAY),
        "goi_cu": _file(d / "render-stuck" / "20260701-170000" / "ps-top-cpu.txt", b"ps", 0),
        "goi_moi": _file(d / "render-stuck" / "20261003-170000" / "ps-top-cpu.txt", b"ps", 0),
    }


def _gia_tuoi_thu_muc(p: Path, tuoi_giay: float):
    t = time.time() - tuoi_giay
    os.utime(p, (t, t))


def test_luat_xoay_vong(kho):
    xoa, cat, loi = LR.xoay_log([kho["d"]], 60, 5, time.time(), False, mau="*.log",
                                log=lambda m: None)
    assert loi == []
    assert xoa == [kho["cu"]] and not kho["cu"].exists()
    assert kho["moi"].read_bytes() == b"moi\n"
    assert cat == [kho["to"]]
    b = kho["to"].read_bytes()
    assert len(b) <= LR.GIU_DUOI + 100 and b.endswith(b"dong cuoi\n") and b.startswith(b"[log_rotate:")
    assert kho["to_dang_ghi"].stat().st_size > 5 * 1024 * 1024, "vừa ghi trong 1 h ⇒ không cắt"
    for k in ("heal_state", "heal_audit", "anh"):
        assert kho[k].exists(), f"{k}: không phải log thường / state của heal_agent ⇒ không đụng"


def test_dry_run_khong_cham(kho):
    xoa, cat, _ = LR.xoay_log([kho["d"]], 60, 5, time.time(), True, mau="*.log", log=lambda m: None)
    assert xoa and cat and kho["cu"].exists()
    assert kho["to"].stat().st_size > 5 * 1024 * 1024


def test_goi_chan_doan_cu_bi_xoa(kho):
    rs = kho["d"] / "render-stuck"
    _gia_tuoi_thu_muc(rs / "20260701-170000", 61 * NGAY)
    xoa, loi = LR.xoa_thu_muc_cu([rs], 60, time.time(), False)
    assert loi == [] and [d.name for d in xoa] == ["20260701-170000"]
    assert (rs / "20261003-170000").is_dir()


def test_cli_thu_muc_khong_co_van_ma_0(tmp_path, capsys):
    assert LR.main(["--dir", str(tmp_path / "khong-co"), "--old-dirs", str(tmp_path / "x")]) == 0
    assert "LOG_ROTATE mode=rotate deleted=0 truncated=0 dirs=0 errors=0" in capsys.readouterr().out


@pytest.mark.parametrize("sai", [["--days", "0"], ["--max-mb", "1"], ["--la"]])
def test_cli_tham_so_sai_ma_2(sai):
    assert LR.main(sai) == 2


def test_cli_chay_that(kho, capsys):
    _gia_tuoi_thu_muc(kho["d"] / "render-stuck" / "20260701-170000", 61 * NGAY)
    assert LR.main(["--dir", str(kho["d"]), "--old-dirs", str(kho["d"] / "render-stuck")]) == 0
    out = capsys.readouterr().out
    assert "LOG_ROTATE mode=rotate deleted=1 truncated=1 dirs=1 errors=0" in out


# ── nối vào lượt chạy ───────────────────────────────────────────────────────────

def _doc(ten):
    return (RUNNERS / ten).read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("ten", ("run-toptoday-hot.ps1", "run-weekly-news.ps1", "run-weekly-repo.ps1"))
def test_runner_tin_xoay_log_truoc_rao_render(ten):
    t = _doc(ten)
    i = t.index("Invoke-LogRotate -Python $syspy -Dirs @($logdir)")
    assert i < t.index("$pf = Invoke-RenderPreflight")
    assert "-OldDirs @(Join-Path $logdir 'render-stuck')" in t
    if ten == "run-toptoday-hot.ps1":
        assert t.index("Test-Cadence -Date") < i, "ngày lệch nhịp thoát ngay — không xoay log"


def test_runner_truyen_xoay_log_launchd_truoc_luot():
    t = _doc("run-daily-truyen.ps1")
    assert t.index("Invoke-LogRotate -Python $py") < t.index("& $py -u $guard")


def test_daily_truyen_xoay_daily_logs_canh_sweep_old():
    t = (RUNNERS / "story" / "daily_truyen.py").read_text(encoding="utf-8")
    assert re.search(r"xoay_log_truyen\(log\)\n\s+sweep_old\(st, log", t)


def test_daily_truyen_xoay_that(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_DIR", str(tmp_path / "engine"))
    sys.path.insert(0, str(RUNNERS / "story"))
    dt = importlib.reload(importlib.import_module("daily_truyen"))
    logs = Path(dt.LOGDIR)
    cu = _file(logs / "pntt_1-10_20260701.log", b"cu\n", 61 * NGAY)
    state = _file(logs / "_heal_state.json", b"{}", 61 * NGAY)
    ghi = []
    dt.xoay_log_truyen(ghi.append)
    assert not cu.exists() and state.exists()
    assert any("LOG_ROTATE mode=rotate deleted=1" in g for g in ghi)


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_Invoke_LogRotate_kem_log_launchd_cua_tram(tmp_path):
    tram = tmp_path / "tram"
    (tram / "logs" / "launchd").mkdir(parents=True)
    (tram / "CHANNELS.md").write_text("---\nchannels: []\n---\n", encoding="utf-8")
    cu = _file(tram / "logs" / "launchd" / "studio.marketing.daily-news-a.out.log", b"cu\n", 61 * NGAY)
    kenh = _file(tmp_path / "kenh-logs" / "old.log", b"cu\n", 61 * NGAY)
    kich = tmp_path / "goi.ps1"
    kich.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        f". '{RUNNERS / 'brand-paths.ps1'}'\n"
        f"Invoke-LogRotate -Python '{sys.executable}' -Dirs @('{tmp_path / 'kenh-logs'}') "
        "-OnLine { param($l) Write-Output ('L: ' + $l) }\n", encoding="utf-8-sig")
    env = {**os.environ, "MARKETING_STUDIO_DATA": str(tram), "PYTHONUTF8": "1"}
    r = subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(kich)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=120)
    ra = r.stdout + r.stderr
    assert "LOG_ROTATE mode=rotate deleted=2" in ra, ra[-2000:]
    assert not cu.exists() and not kenh.exists()
