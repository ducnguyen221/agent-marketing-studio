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
· **Có job "cài embedded rồi pytest trần"** trên cả hai OS (P1-8): bộ test phải xanh trên
  máy ĐÃ CÀI, không chỉ trên checkout sạch — 12 test từng đọc `workspace/` thật của repo.

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


JOB_CAI = "pytest-embedded"


def _job(wf):
    """Job pytest chính (checkout sạch, ma trận OS × Python)."""
    jobs = wf["jobs"]
    assert set(jobs) == {"pytest", JOB_CAI}, sorted(jobs)
    return jobs["pytest"]


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


# ── A11: mọi nhánh · ghim SHA · ma trận Python ───────────────────────────────

def test_chay_tren_MOI_nhanh(wf):
    """CI chỉ nhìn `main` thì tới lúc merge mới biết đỏ — quá muộn để còn là cổng."""
    on = wf.get("on", wf.get(True))
    assert (on["push"] or {}).get("branches") == ["**"]


def test_moi_action_GHIM_SHA_day_du():
    """Tag `@v4` có thể bị dời sang mã khác; SHA 40 ký tự thì không. Mỗi dòng giữ tag ở
    chú thích để người đọc biết bản nào."""
    import re
    t = WF.read_text(encoding="utf-8")
    dong = re.findall(r"uses:\s*(\S+)(.*)", t)
    assert dong
    for uses, sau in dong:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", uses), f"chưa ghim SHA: {uses}"
        assert re.search(r"#\s*v\d", sau), f"{uses}: thiếu chú thích phiên bản"


def test_ma_tran_python_phu_san_va_ban_moi(wf):
    """Sàn là `requires-python` của pyproject.toml — CI phải chạy đúng bản sàn đó."""
    import re
    s = _job(wf)["strategy"]["matrix"]
    ban = {str(v) for v in s["python-version"]}
    san = re.search(r'requires-python\s*=\s*">=(\d+\.\d+)"',
                    (ROOT / "pyproject.toml").read_text(encoding="utf-8")).group(1)
    assert {san, "3.12", "3.13"} <= ban, ban
    buoc = [st for st in _steps(wf) if "setup-python" in str(st.get("uses", ""))]
    assert buoc and buoc[0]["with"]["python-version"] == "${{ matrix.python-version }}"


# ── P1-8: cài embedded rồi pytest TRẦN, trên cả hai OS ─────────────────────────────────

def _job_cai(wf):
    return wf["jobs"][JOB_CAI]


def test_job_cai_roi_test_chay_hai_OS_khong_fail_fast(wf):
    j = _job_cai(wf)
    assert set(j["strategy"]["matrix"]["os"]) == {"windows-latest", "macos-latest"}
    assert j["strategy"]["fail-fast"] is False and j["runs-on"] == "${{ matrix.os }}"


def test_job_cai_dung_BO_CAI_THAT_che_do_embedded_TRUOC_pytest(wf):
    buoc = _job_cai(wf)["steps"]
    lenh = [str(st.get("run", "")) for st in buoc]
    i_sh = next(i for i, x in enumerate(lenh) if "install.sh" in x)
    i_ps = next(i for i, x in enumerate(lenh) if "install.ps1" in x)
    i_py = next(i for i, x in enumerate(lenh) if "pytest" in x)
    assert "--mode embedded" in lenh[i_sh] and "macOS" in str(buoc[i_sh].get("if"))
    assert "-Mode embedded" in lenh[i_ps] and "Windows" in str(buoc[i_ps].get("if"))
    assert buoc[i_ps].get("shell") == "powershell", "install.ps1 phải chạy bằng PS 5.1 như máy lịch"
    assert max(i_sh, i_ps) < i_py


def test_job_cai_chay_pytest_TRAN_doi_powershell_that(wf):
    """TRẦN = không chỉ đích `tests/`: chính việc gom nhầm `workspace/` là thứ phải bắt."""
    buoc = [st for st in _job_cai(wf)["steps"] if "pytest" in str(st.get("run", ""))]
    assert len(buoc) == 1
    assert "python -m pytest -q" in buoc[0]["run"] and "tests" not in buoc[0]["run"]
    assert str((buoc[0].get("env") or {}).get("MARKETING_STUDIO_REQUIRE_POWERSHELL")) == "1"
    macos = [st for st in _job_cai(wf)["steps"] if "macOS" in str(st.get("if", ""))]
    assert any("pwsh" in str(st.get("run", "")) for st in macos)
