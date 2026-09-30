# -*- coding: utf-8 -*-
"""`pytest` TRẦN ở gốc repo không được gom test của TRẠM (`workspace/`) hay của `.venv`.

Máy đã `install.sh --mode embedded` có `workspace/` ngay trong repo, và trạm mang script +
test riêng của người dùng (Mac 30/09/2026: `workspace/nghe-tien-truyen/**/test_*.py` cần
`numpy` → 3 lỗi collect). Chặn bằng `collect_ignore` trong `conftest.py` ở GỐC repo. Test
này dựng một cây tạm mang đúng file đó, rồi chạy `pytest` trần ở gốc cây — đo hành vi thật
của pytest, không chỉ đọc chuỗi trong file.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HONG = "def test_cua_tram():\n    assert False, 'test cua TRAM bi gom vao bo test repo'\n"


def test_conftest_goc_bo_qua_workspace_va_venv():
    import importlib.util
    spec = importlib.util.spec_from_file_location("conftest_goc", ROOT / "conftest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert {"workspace", ".venv"} <= set(m.collect_ignore)


def test_pytest_TRAN_khong_gom_test_cua_tram(tmp_path):
    goc = tmp_path / "repo"
    (goc / "tests").mkdir(parents=True)
    shutil.copyfile(ROOT / "conftest.py", goc / "conftest.py")
    (goc / "tests" / "test_repo.py").write_text("def test_repo():\n    assert True\n",
                                                encoding="utf-8")
    for d in ("workspace/kenh", ".venv/lib"):
        (goc / d).mkdir(parents=True)
        (goc / d / "test_tram.py").write_text(HONG, encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                       cwd=str(goc), capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 passed" in r.stdout and "test_tram" not in r.stdout, r.stdout
