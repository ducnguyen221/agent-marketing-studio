# -*- coding: utf-8 -*-
"""`.github/workflows/tests.yml` — CI hai hệ điều hành phải giữ được bốn điều.

Repo này chạy lịch thật trên Windows (PowerShell 5.1, Task Scheduler) và sẽ chạy trên macOS
(pwsh 7, launchd). Bộ test là thứ duy nhất nói "cả hai vẫn chạy"; CI chỉ có giá trị khi:

· **Chạy cả hai OS**, và `fail-fast: false` — một bên đỏ không được huỷ bên kia, nếu không
  ta không biết lỗi là của một OS hay của cả hai.
· **Có PowerShell thật trên macOS.** Ba file test `.ps1` tự `skip` khi thiếu PowerShell;
  trên CI "skip" trông y hệt "xanh". Nên workflow phải cài/kiểm `pwsh` VÀ đặt
  `MARKETING_STUDIO_REQUIRE_POWERSHELL=1` (conftest biến thiếu PowerShell thành lỗi).
· **Chạy đúng `python -m pytest -q`** trên các phụ thuộc khai trong `requirements.txt`.
· **Quyền tối thiểu** (`contents: read`) — workflow chỉ đọc mã, không cần gì hơn.

File này không chứng minh CI xanh — nó chỉ giữ cho cấu hình CI không trôi khỏi bốn điều đó.
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "tests.yml"


@pytest.fixture(scope="module")
def wf():
    assert WF.is_file(), f"thiếu {WF.relative_to(ROOT)}"
    return yaml.safe_load(WF.read_text(encoding="utf-8"))


def _job(wf):
    jobs = wf["jobs"]
    assert len(jobs) == 1, "một job pytest duy nhất, ma trận theo OS"
    return next(iter(jobs.values()))


def _steps(wf):
    return _job(wf)["steps"]


def test_kich_hoat_khi_push_va_pull_request(wf):
    on = wf.get("on", wf.get(True))          # YAML 1.1 đọc khoá `on` thành True
    assert "push" in on and "pull_request" in on


def test_quyen_chi_doc(wf):
    assert wf.get("permissions") == {"contents": "read"}


def test_ma_tran_hai_os_khong_fail_fast(wf):
    s = _job(wf)["strategy"]
    assert set(s["matrix"]["os"]) == {"windows-latest", "macos-latest"}
    assert s["fail-fast"] is False
    assert _job(wf)["runs-on"] == "${{ matrix.os }}"


def test_macos_cai_va_kiem_pwsh(wf):
    mac = [st for st in _steps(wf) if "macOS" in str(st.get("if", ""))]
    lenh = "\n".join(str(st.get("run", "")) for st in mac)
    assert "pwsh" in lenh, "bước macOS phải cài/kiểm pwsh"
    assert "brew install" in lenh


def test_pytest_doi_powershell_that(wf):
    buoc = [st for st in _steps(wf) if "pytest" in str(st.get("run", ""))]
    assert len(buoc) == 1
    assert "python -m pytest -q" in buoc[0]["run"]
    env = {**(_job(wf).get("env") or {}), **(buoc[0].get("env") or {})}
    assert str(env.get("MARKETING_STUDIO_REQUIRE_POWERSHELL")) == "1"


def test_cai_phu_thuoc_tu_requirements(wf):
    lenh = "\n".join(str(st.get("run", "")) for st in _steps(wf))
    assert "pip install -r requirements.txt" in lenh


def test_bien_moi_truong_conftest_khop_ten(wf):
    """Tên biến ở workflow và ở conftest phải là MỘT — lệch tên là cổng tắt câm."""
    assert "MARKETING_STUDIO_REQUIRE_POWERSHELL" in (ROOT / "tests" / "conftest.py").read_text(
        encoding="utf-8")
