# -*- coding: utf-8 -*-
"""Cổng của `Test-Cadence` (brand-paths.ps1) — lịch "2 ngày/lần" nằm TRONG runner.

Trên Windows, nhịp chẵn/lẻ do Task Scheduler giữ (`-EveryDays 2`). launchd trên macOS không
có nhịp đó: nó gọi runner MỖI NGÀY, nên nếu runner không tự biết hôm nay có phải ngày của
mình không thì mỗi kênh ra bài gấp đôi — và hai kênh AI/Data (lệch nhau một ngày) chạy
chồng lên nhau. Mốc lấy từ `campaign.md: runtime.cadence_anchor` (AI 2026-06-26, Data
2026-06-27 — ngày chạy thật đầu tiên của hai task).

Test gọi thẳng PowerShell (Windows: powershell 5.1; macOS: pwsh 7) với NGÀY GIẢ — không
chạy runner, không chạm mạng. Không có PowerShell thì skip.

Chạy:  python -m pytest tests/test_runner_cadence.py -q
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import pytest

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "runners")
PS = shutil.which("powershell") or shutil.which("pwsh")

pytestmark = pytest.mark.skipif(not PS, reason="khong co PowerShell")


def _cadence(ngay, days=None, anchor=None):
    """-> 'RUN' | 'SKIP' | 'NONE' (không khai lịch)."""
    cfg = []
    if days is not None:
        cfg.append("cadence_days=%s" % days)
    if anchor is not None:
        cfg.append("cadence_anchor='%s'" % anchor)
    script = (
        "$ErrorActionPreference='Stop'; . '%s'; "
        "$c = [pscustomobject]@{%s}; "
        "$r = Test-Cadence -Date '%s' -Cfg $c; "
        "if ($null -eq $r) { 'NONE' } elseif ($r.run) { 'RUN' } else { 'SKIP' }"
        % (os.path.join(ENGINE, "brand-paths.ps1"), "; ".join(cfg), ngay))
    # brand-paths.ps1 phân giải trạm NGAY lúc dot-source (fail-closed): trỏ nó vào thư mục
    # tạm để test không phụ thuộc — và không chạm — trạm thật của máy.
    env = dict(os.environ, MARKETING_STUDIO_DATA=tempfile.gettempdir())
    p = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True, timeout=60, env=env)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip().splitlines()[-1]


@pytest.mark.parametrize("ngay,mong", [
    ("2026-06-26", "RUN"),     # chính mốc
    ("2026-09-28", "RUN"),     # lượt thật Daily Hot AI 28/09 (rc 0)
    ("2026-09-30", "RUN"),
    ("2026-09-29", "SKIP"),    # ngày của Data
    ("2026-06-25", "SKIP"),    # TRƯỚC mốc vẫn đúng nhịp (modulo âm)
    ("2026-06-24", "RUN"),
])
def test_ai_moc_26_06(ngay, mong):
    assert _cadence(ngay, 2, "2026-06-26") == mong


@pytest.mark.parametrize("ngay,mong", [
    ("2026-09-27", "RUN"),     # lượt thật Daily Hot Data 27/09 (rc 0)
    ("2026-09-29", "RUN"),     # lượt kế tiếp theo lịch Windows
    ("2026-09-28", "SKIP"),
])
def test_data_moc_27_06(ngay, mong):
    assert _cadence(ngay, 2, "2026-06-27") == mong


def test_khong_khai_lich_la_khong_chan():
    # Chiến dịch không khai cadence (weekly, repo) -> runner chạy mỗi lần được gọi.
    assert _cadence("2026-09-29") == "NONE"
    assert _cadence("2026-09-29", 1, "2026-06-26") == "NONE"
    assert _cadence("2026-09-29", 2, None) == "NONE"
