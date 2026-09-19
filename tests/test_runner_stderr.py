# -*- coding: utf-8 -*-
"""Runner chạy nền KHÔNG được chết vì Python in một dòng ra stderr.

Vì sao có file này — đo thật 20/09/2026 (gói P1-G1):

`run-worker.ps1` và `run-approve-poller.ps1` gọi `& <python> … 2>&1` dưới
`$ErrorActionPreference = 'Stop'`. Trên Windows PowerShell 5.1, `2>&1` bọc mỗi dòng stderr
của lệnh ngoài thành một `ErrorRecord` (NativeCommandError); gặp `Stop` thì dòng ĐẦU TIÊN
đã là lỗi kết thúc. Worker in một cảnh báo vô hại ra stderr ⇒ runner exit 1, và vì chết
trước dòng `Ghi`, **file log không có một chữ nào**. Hai runner này chạy ẩn theo lịch, không
qua notify-run — log là đường quan sát DUY NHẤT, nên đây là kiểu chết câm hoàn toàn.

Test chép runner NGUYÊN BYTE vào một cây repo giả, thay `worker.py` / `approve_bus.py` bằng
script in stderr rồi thoát với mã cho trước. Không đụng mạng, không đụng Telegram, không
chạy worker/poller thật (hai task đó đang Disabled).

Khẳng định hai vế, vì vá sai theo hướng ngược lại cũng là hỏng:
· stderr không giết runner, và dòng stderr VÀO LOG;
· mã thoát thật của Python vẫn đi ra nguyên vẹn (0 là 0, 3 là 3) — nuốt lỗi là tệ hơn chết.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
PS = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(PS is None, reason="khong co PowerShell tren may nay")

GIA = """import sys
sys.stderr.write("canh bao: khong dung duoc bot (gia)\\n")
sys.stderr.flush()
print("dong stdout (gia)")
sys.exit({ma})
"""

RUNNER = {
    "worker": ("run-worker.ps1", "worker.py", "tho-viec-*.log", [], "=== tho thoat, ma {ma} ==="),
    "poller": ("run-approve-poller.ps1", "approve_bus.py", "tg-poller-*.log",
               ["-AliveSeconds", "1"], "=== thoat, ma {ma} ==="),
}


def _chay(tmp_path: Path, loai: str, ma: int):
    ten_ps1, ten_py, mau_log, them, dong_cuoi = RUNNER[loai]
    repo = tmp_path / "repo"
    (repo / "scripts" / "runners").mkdir(parents=True)
    (repo / "scripts" / "pipeline").mkdir(parents=True)
    ps1 = repo / "scripts" / "runners" / ten_ps1
    ps1.write_bytes((GOC / "scripts" / "runners" / ten_ps1).read_bytes())
    (repo / "scripts" / "pipeline" / ten_py).write_text(GIA.format(ma=ma), encoding="utf-8")

    cd = tmp_path / "cd"
    cd.mkdir()
    (cd / "campaign.md").write_text("---\nid: cd\n---\n", encoding="utf-8")

    env = dict(os.environ, MARKETING_STUDIO_PY=sys.executable)
    r = subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-Campaign", str(cd), *them],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=120)
    logs = sorted((cd / "logs").glob(mau_log))
    log = logs[0].read_text(encoding="utf-8") if logs else ""
    return r, log, dong_cuoi.format(ma=ma)


@pytest.mark.parametrize("loai", ["worker", "poller"])
def test_stderr_KHONG_giet_runner_va_vao_log(tmp_path, loai):
    r, log, dong_cuoi = _chay(tmp_path, loai, 0)
    assert r.returncode == 0, (
        f"{loai}: Python thoát 0 mà runner thoát {r.returncode} — stderr bị coi là lỗi "
        f"kết thúc.\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}\nLOG:\n{log}")
    assert "canh bao: khong dung duoc bot" in log, f"dòng stderr không vào log:\n{log}"
    assert "dong stdout (gia)" in log, log
    assert dong_cuoi in log, log
    assert "NativeCommandError" not in log + r.stdout + r.stderr


@pytest.mark.parametrize("loai", ["worker", "poller"])
def test_ma_thoat_that_cua_python_di_ra_nguyen_ven(tmp_path, loai):
    r, log, dong_cuoi = _chay(tmp_path, loai, 3)
    assert r.returncode == 3, f"{loai}: mã 3 thành {r.returncode}\n{r.stdout}\n{r.stderr}"
    assert dong_cuoi in log and "canh bao" in log, log


def test_worker_luot_RONG_van_im_lang(tmp_path, monkeypatch):
    """Vá stderr không được làm hỏng luật cũ: hàng rỗng thì KHÔNG ghi log (1.440 dòng/ngày)."""
    monkeypatch.setattr(sys.modules[__name__], "GIA", 'print("hang rong")\nraise SystemExit({ma})\n')
    r, log, _ = _chay(tmp_path, "worker", 0)
    assert r.returncode == 0, r.stderr
    assert log == "", log
