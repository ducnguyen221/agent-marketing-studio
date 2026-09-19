# -*- coding: utf-8 -*-
"""Ép UTF-8 cho MỌI tiến trình con mà test sinh ra.

Vì sao cần: test chạy script bằng `subprocess.run(..., encoding="utf-8")` rồi đọc
`stderr`. Trên Windows máy sạch (không có `PYTHONUTF8`/`PYTHONIOENCODING` trong môi
trường), tiến trình con ghi stderr bằng cp1252 — `…` thành byte `0x85`, tiếng Việt vỡ —
và `r.stderr` về `None`, test nổ `TypeError` ở chỗ chẳng liên quan gì tới thứ nó đang kiểm.

Đây KHÔNG phải cách vá lỗi encoding của script: mỗi entrypoint đã tự
`sys.stderr.reconfigure(encoding="utf-8")`. File này chỉ khiến bộ test **giống máy sạch
hơn**, và có một test riêng (`test_no_env_dependency_utf8`) khẳng định script chạy đúng
NGAY CẢ KHI biến môi trường bị gỡ sạch.

Đã trả giá một lần: bộ test xanh suốt vì phiên làm việc export `PYTHONIOENCODING=utf-8`
ở mọi lệnh, trong khi người clone về chạy `pytest` thì 6 test đỏ.
"""
import os
import shutil

import pytest


@pytest.fixture(autouse=True)
def _utf8_cho_tien_trinh_con(monkeypatch):
    monkeypatch.setenv("PYTHONUTF8", "1")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")


def pytest_report_header(config):
    return (f"encoding máy: PYTHONUTF8={os.environ.get('PYTHONUTF8', '(không đặt)')} · "
            f"PYTHONIOENCODING={os.environ.get('PYTHONIOENCODING', '(không đặt)')}")


def pytest_configure(config):
    """CI đòi PowerShell THẬT: thiếu thì dừng cả lượt, không để test tự `skip`.

    Ba file test (`test_run_args`, `test_runner_stderr`, `test_ps1_portable`) tự bỏ qua khi
    máy không có PowerShell — hợp lý cho người clone về chạy thử, nhưng trên CI thì "bỏ qua"
    trông y hệt "xanh": runner macOS thiếu `pwsh` sẽ báo CI qua mà chưa chạy một dòng `.ps1`
    nào. Workflow đặt `MARKETING_STUDIO_REQUIRE_POWERSHELL=1` để biến im lặng đó thành lỗi.
    """
    if os.environ.get("MARKETING_STUDIO_REQUIRE_POWERSHELL") == "1" and not (
            shutil.which("powershell") or shutil.which("pwsh")):
        raise pytest.UsageError(
            # Khong dau co chu dich: pytest in loi nay qua console cp1252 cua runner Windows.
            "MARKETING_STUDIO_REQUIRE_POWERSHELL=1 nhung khong thay `powershell`/`pwsh` "
            "tren PATH - cai PowerShell 7 truoc khi chay test (cac test .ps1 se bi skip).")
