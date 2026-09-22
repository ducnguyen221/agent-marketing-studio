# -*- coding: utf-8 -*-
r"""`Find-Python` không được loại một Python CHẠY ĐƯỢC chỉ vì nó in ra stderr.

Vì sao có file này — review độc lập P1 (N1), đo lại 20/09/2026:

Cả 5 `.ps1` có `Find-Python` đặt `$ErrorActionPreference = 'Stop'` ở đầu file, rồi thử ứng
viên bằng `& $exe -c '…' 2>$null`. Trên Windows PowerShell 5.1, **mọi** chuyển hướng luồng
lỗi của lệnh ngoài (`2>&1` hay `2>$null` đều vậy) bọc từng dòng stderr thành một
`ErrorRecord`; dưới `Stop` thì dòng ĐẦU TIÊN đã là lỗi kết thúc. Kết quả: một Python chạy
tốt nhưng in một dòng cảnh báo lúc khởi động (wrapper `.cmd`, shim pyenv/conda, một `.pth`
in ra, `PYTHONWARNINGS=default`) bị ném vào `catch` ⇒ `$false` ⇒ script in *"khong chay
duoc Python 3.10+ -> DUNG"* và **exit 2**. Trên pwsh 7 không nổ, nên cùng một file có hai
hành vi ở hai máy — đúng kiểu hỏng mà cả P1 sinh ra để chặn.

Đây là CÙNG MỘT cạm bẫy mà `tests/test_runner_stderr.py` đã vá cho thân runner; bản chép
trong `Find-Python` thì chưa. Test ở đây đo **chính khối `Find-Python` của từng file**
(trích ra rồi chạy bằng trình PowerShell của máy), nên vá lẻ một bản là thấy ngay.

Kèm theo: `[string](…)` nối MỌI dòng stdout bằng dấu cách, nên một ứng viên in thêm dòng
trước dòng phiên bản cũng trượt regex neo `^\(\d+, \d+\)$`. Lấy dòng CUỐI thay vì cả stdout.

Không đụng mạng, không chạy runner thật: ứng viên là một shim ủy nhiệm cho chính Python
đang chạy test.
"""
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
PS = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(PS is None, reason="khong co PowerShell tren may nay")

# 5 file mang bản chép `Find-Python`; `test_ps1_portable` giữ chúng giống hệt nhau, test này
# giữ cho bản-được-chép ấy đúng.
CO_FIND_PYTHON = [
    "install.ps1",
    "templates/station/_channel/_campaign/run.ps1",
    "scripts/runners/run-worker.ps1",
    "scripts/runners/run-approve-poller.ps1",
    "scripts/runners/run-blog-campaign.ps1",
]

# Shim: in nhiễu rồi ủy nhiệm cho Python thật. `--them-stdout` in thêm một dòng stdout TRƯỚC
# dòng phiên bản (bẫy `[string](…)` nối mọi dòng bằng dấu cách).
SHIM_PY = """import subprocess, sys
sys.stderr.write("canh bao khoi dong (gia)\\n")
sys.stderr.write("dong nhieu thu hai (gia)\\n")
sys.stderr.flush()
if {them_stdout}:
    print("loi chao cua shim (gia)")
    sys.stdout.flush()
sys.exit(subprocess.call([sys.executable] + sys.argv[1:]))
"""


def _shim(tmp_path: Path, them_stdout: bool = False) -> Path:
    """Một 'Python' chạy được nhưng ồn ào. Trả về đường dẫn gọi được như một exe."""
    loi = tmp_path / "shim_noisy.py"
    loi.write_text(SHIM_PY.format(them_stdout=them_stdout), encoding="utf-8")
    if os.name == "nt":
        vo = tmp_path / "python-on-ao.cmd"
        vo.write_text(f'@echo off\r\n"{sys.executable}" "{loi}" %*\r\n', encoding="ascii")
    else:
        vo = tmp_path / "python-on-ao.sh"
        vo.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{loi}" "$@"\n', encoding="ascii")
        vo.chmod(vo.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return vo


def _khoi_find_python(text: str) -> str:
    """Trích `function Find-Python { … }` (đóng bằng `}` ở cột 0) — y như cổng portable."""
    dong = text.replace("\r", "").splitlines()
    for i, d in enumerate(dong):
        if re.match(r"function\s+Find-Python\b", d):
            for j in range(i + 1, len(dong)):
                if dong[j].rstrip() == "}":
                    return "\n".join(dong[i:j + 1])
    raise AssertionError("khong thay khoi Find-Python")


def _hoi_find_python(tmp_path: Path, nguon: str, exe: Path | str, ten: str) -> subprocess.CompletedProcess:
    """Chạy ĐÚNG khối `Find-Python` của một file, với `MARKETING_STUDIO_PY = <exe>`.

    Dựng lại đúng bối cảnh của file thật: `$ErrorActionPreference = 'Stop'` ở đầu — thiếu
    dòng này thì test xanh trong khi file thật vẫn hỏng.
    """
    ps1 = tmp_path / f"hoi-{ten}.ps1"
    ps1.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        + _khoi_find_python(nguon)
        + "\n$ra = Find-Python -Repo ''\n"
        + "Write-Host ('KET QUA=[' + $ra + ']')\n",
        encoding="utf-8-sig")
    return subprocess.run(
        [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=dict(os.environ, MARKETING_STUDIO_PY=str(exe)))


@pytest.mark.parametrize("ten_file", CO_FIND_PYTHON)
def test_python_in_stderr_ma_exit_0_VAN_duoc_chon(tmp_path, ten_file):
    """Ứng viên in stderr rồi exit 0 là ứng viên HỢP LỆ — loại nó là loại oan."""
    exe = _shim(tmp_path)
    # Chốt tiền đề: shim này thật sự chạy được, nếu không test đang đo nhầm thứ.
    tra = subprocess.run([str(exe), "-c", "import sys;print(sys.version_info[:2])"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert tra.returncode == 0 and "(3," in tra.stdout, tra.stdout + tra.stderr

    r = _hoi_find_python(tmp_path, (GOC / ten_file).read_text(encoding="utf-8-sig"),
                         exe, Path(ten_file).stem)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"KET QUA=[{exe}]" in r.stdout, (
        f"{ten_file}: Python chay duoc bi loai vi in stderr:\n" + r.stdout + r.stderr)


@pytest.mark.parametrize("ten_file", CO_FIND_PYTHON)
def test_dong_stdout_thua_khong_lam_truot_phien_ban(tmp_path, ten_file):
    """`[string](…)` nối mọi dòng stdout bằng dấu cách ⇒ regex neo trượt. Lấy dòng CUỐI."""
    exe = _shim(tmp_path, them_stdout=True)
    r = _hoi_find_python(tmp_path, (GOC / ten_file).read_text(encoding="utf-8-sig"),
                         exe, Path(ten_file).stem + "-2dong")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"KET QUA=[{exe}]" in r.stdout, (
        f"{ten_file}: mot dong stdout thua lam Find-Python truot:\n" + r.stdout + r.stderr)


@pytest.mark.parametrize("ten_file", CO_FIND_PYTHON)
def test_ung_vien_KHONG_CHAY_DUOC_van_bi_loai(tmp_path, ten_file):
    """Vế ngược: nới lỏng quá tay (nuốt luôn mã thoát) còn tệ hơn — phải vẫn loại."""
    r = _hoi_find_python(tmp_path, (GOC / ten_file).read_text(encoding="utf-8-sig"),
                         tmp_path / "khong-he-ton-tai", Path(ten_file).stem + "-thieu")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "KET QUA=[]" in r.stdout, r.stdout + r.stderr
    assert "MARKETING_STUDIO_PY" in r.stdout, r.stdout


@pytest.mark.parametrize("ten_file", CO_FIND_PYTHON)
def test_ung_vien_exit_khac_0_van_bi_loai(tmp_path, ten_file):
    """Chạy được nhưng tự báo hỏng (mã ≠ 0) thì không phải Python dùng được."""
    loi = tmp_path / "shim_hong.py"
    loi.write_text("import sys\nsys.stderr.write('hong (gia)\\n')\nsys.exit(3)\n",
                   encoding="utf-8")
    if os.name == "nt":
        vo = tmp_path / "python-hong.cmd"
        vo.write_text(f'@echo off\r\n"{sys.executable}" "{loi}" %*\r\n', encoding="ascii")
    else:
        vo = tmp_path / "python-hong.sh"
        vo.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{loi}" "$@"\n', encoding="ascii")
        vo.chmod(vo.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    r = _hoi_find_python(tmp_path, (GOC / ten_file).read_text(encoding="utf-8-sig"),
                         vo, Path(ten_file).stem + "-ma3")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "KET QUA=[]" in r.stdout, r.stdout + r.stderr
