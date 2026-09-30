# -*- coding: utf-8 -*-
"""Cổng di động của BỘ CHẠY: `scripts/runners/**` (tin + truyện) và script khuôn trạm
`templates/station/**` phải chạy được trên MÁY KHÁC và HỆ ĐIỀU HÀNH KHÁC.

Bộ chạy từng sống ngoài git, trong `<trạm>/engine` của một máy Windows; mọi lỗi lộ ra trên
Mac (30/09/2026) đều nằm ở đó và không cổng nào thấy. Từ 1.1.0 chúng vào repo (P1-10), và
cổng này gom MỘT chỗ các luật đã trả giá (P3-11) — `tests/test_ps1_portable.py` giữ phần cú
pháp PowerShell chung cho mọi `.ps1`, file này giữ phần riêng của bộ chạy:

1. **Không đường của một máy** — ổ đĩa + thư mục người dùng, biến nhà kiểu Windows.
2. **Không tên thư mục engine dùng chung cũ**, không `cmd /c`, không bộ dựng cũ trong trạm giọng.
3. **Registry `'User'` chỉ đọc sau điều kiện Windows** (P0-1): macOS không có registry,
   đọc trần trả chuỗi rỗng và runner lặng lẽ bỏ qua upload mà vẫn báo ✅.
4. **Thư mục cũ trong thư mục nhà chỉ là đường lùi CUỐI, có tên trong danh sách** (P1-5):
   literal `.marketing`/`.voice`/`.tts`/`.video` chỉ được ở đúng chỗ phân giải có WARN.
5. **Bộ chạy tối thiểu của `engine_dir` có trong repo** — `run.ps1` tìm runner ở
   `<repo>/scripts/runners` trước `<trạm>/engine`.

Chuỗi cấm dựng từ mảnh: file này nằm trong vùng các cổng khác quét.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VUNG = [ROOT / "scripts" / "runners", ROOT / "templates" / "station"]


def _files(*duoi):
    ra = []
    for goc in VUNG:
        for p in sorted(goc.rglob("*")):
            if p.is_file() and p.suffix in duoi and "__pycache__" not in p.parts:
                ra.append(p)
    return ra


MA = _files(".ps1", ".py")
PS1 = _files(".ps1")


def _ten(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


# Miễn luật 2 và 4 (có LÝ DO): khuôn `run.ps1` của chiến dịch được CHÉP vào trạm của máy cũ và
# giữ đường lùi cho trạm chưa dọn — chính các đường lùi đó có kiểm thử riêng.
MIEN_DUONG_LUI = {
    "templates/station/_channel/_campaign/run.ps1":
        "đường lùi trạm/engine cũ cho trạm chưa dọn; kiểm bởi tests/test_run_args.py",
}


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig")


def _dong_ma(p: Path):
    """(số dòng, dòng) bỏ chú thích `#…` và khối `<# … #>` của PowerShell."""
    trong = False
    for i, d in enumerate(_doc(p).splitlines(), 1):
        s = d.strip()
        if p.suffix == ".ps1":
            if trong:
                if "#>" in s:
                    trong = False
                continue
            if s.startswith("<#"):
                trong = "#>" not in s[2:]
                continue
        if not s or s.startswith("#"):
            continue
        yield i, d


def test_co_file_de_quet():
    """Cổng quét 0 file là cổng luôn xanh."""
    ten = {p.name for p in MA}
    assert {"brand-paths.ps1", "run-toptoday-hot.ps1", "daily_truyen.py", "run.ps1"} <= ten, ten
    assert len(MA) >= 30, len(MA)


# ── Luật 1 — không đường của một máy ─────────────────────────────────────────
_BS = chr(92)
DUONG_MAY = [
    (re.compile(r"[A-Za-z]:" + re.escape(_BS) + r"{1,2}(?:Users|AppData|Program Files|Windows)"
                + re.escape(_BS), re.I),
     "đường Windows tuyệt đối — dùng $HOME (PS) / Path.home() (py) / biến"),
    (re.compile("/" + "Users" + r"/[A-Za-z0-9._-]+/"), "đường macOS tuyệt đối vào thư mục người dùng"),
    (re.compile("USER" + "PROFILE"), "biến nhà chỉ có trên Windows — dùng $HOME / expanduser"),
]


@pytest.mark.parametrize("p", MA, ids=_ten)
def test_khong_duong_cua_mot_may(p):
    xau = [f"  dòng {i}: {m.group(0)!r} -> {vs}" for i, d in enumerate(_doc(p).splitlines(), 1)
           for pat, vs in DUONG_MAY for m in [pat.search(d)] if m]
    assert not xau, f"{_ten(p)} có đường chỉ đúng trên MỘT máy:\n" + "\n".join(xau)


# ── Luật 2 — không engine dùng chung cũ, không cmd /c, không bộ dựng cũ ─────────
CAM = [
    (re.compile(r"[\\/'\"]" + re.escape("." + "news") + r"[\\/'\"]"),
     "thư mục engine dùng chung cũ — runner nay ở <repo>/scripts/runners"),
    (re.compile("cmd" + r"(?:\.exe)?\s+/c\b", re.I), "cmd /c chỉ có trên Windows"),
    (re.compile("apps" + r"[\\/'\", ]+news"), "bộ dựng cũ trong trạm giọng — dùng video-studio"),
]


@pytest.mark.parametrize("p", MA, ids=_ten)
def test_khong_engine_cu_khong_cmd_c(p):
    if _ten(p) in MIEN_DUONG_LUI:
        pytest.skip(MIEN_DUONG_LUI[_ten(p)])
    xau = [f"  dòng {i}: {d.strip()[:110]} -> {vs}" for i, d in _dong_ma(p)
           for pat, vs in CAM if pat.search(d)]
    assert not xau, f"{_ten(p)}:\n" + "\n".join(xau)


# ── Luật 3 — registry 'User' chỉ sau điều kiện Windows (P0-1) ──────────────────
_REG_USER = re.compile(r"GetEnvironmentVariable\([^)]*,\s*'User'\s*\)", re.I)
_DK_WIN = re.compile(r"Windows_NT|\$IsWin", re.I)


def _registry_tran(text: str) -> list[int]:
    dong = text.splitlines()
    ra = []
    for i, d in enumerate(dong):
        if d.lstrip().startswith("#") or not _REG_USER.search(d):
            continue
        # Điều kiện Windows trên CÙNG dòng, hoặc trong 3 dòng ngay trên (khối `if (...) {`).
        if not any(_DK_WIN.search(x) for x in dong[max(0, i - 3):i + 1]):
            ra.append(i + 1)
    return ra


@pytest.mark.parametrize("p", PS1, ids=_ten)
def test_registry_User_chi_sau_dieu_kien_Windows(p):
    xau = _registry_tran(_doc(p))
    assert not xau, (f"{_ten(p)}: đọc registry 'User' không điều kiện ở dòng {xau} — trên macOS "
                     f"trả chuỗi rỗng và runner lặng lẽ bỏ bước. Dùng Get-EnvVar (brand-paths.ps1).")


def test_tu_kiem_luat_registry():
    tran = "$v = [Environment]::GetEnvironmentVariable('YT_TOKEN_PATH','User')"
    co_dk = ("if (-not $v -and $env:OS -eq 'Windows_NT') { $v = "
             "[Environment]::GetEnvironmentVariable($n, 'User') }")
    khoi = ("if ($env:OS -eq 'Windows_NT') {\n  foreach ($t in $ten) {\n"
            "    $v = [Environment]::GetEnvironmentVariable($t, 'User')")
    assert _registry_tran(tran) == [1]
    assert _registry_tran(co_dk) == []
    assert _registry_tran(khoi) == []


# ── Luật 4 — thư mục cũ trong thư mục nhà: chỉ ở chỗ phân giải có WARN (P1-5) ────
_CU = re.compile(r"""['"]\.(marketing|voice|tts|video)['"]""")
# {file: số literal được phép} — mỗi chỗ là NẤC CUỐI của một hàm phân giải, có WARN, chỉ dùng
# khi thư mục có thật. Thêm một chỗ nữa là thêm một đường tạo trạm thứ hai trên máy mới.
CHO_PHEP_CU = {
    "scripts/runners/brand-paths.ps1": 4,   # Get-StationRoot · Get-VoiceStation (2) · Get-VideoStation
    "scripts/runners/paths.py": 1,          # station()
}


@pytest.mark.parametrize("p", MA, ids=_ten)
def test_thu_muc_cu_chi_o_cho_phan_giai(p):
    if _ten(p) in MIEN_DUONG_LUI:
        pytest.skip(MIEN_DUONG_LUI[_ten(p)])
    n = sum(len(_CU.findall(d)) for _, d in _dong_ma(p))
    cho = CHO_PHEP_CU.get(_ten(p), 0)
    assert n <= cho, (f"{_ten(p)}: {n} literal thư mục cũ trong thư mục nhà (được {cho}). Phân "
                      f"giải qua biến → <repo>/.env → repo anh em (studio_paths / brand-paths.ps1).")


def test_CHO_PHEP_CU_khong_han():
    for f, n in CHO_PHEP_CU.items():
        p = ROOT / f
        assert p.is_file(), f"{f} không còn — gỡ khỏi CHO_PHEP_CU"
        that = sum(len(_CU.findall(d)) for _, d in _dong_ma(p))
        assert that == n, f"{f}: có {that}, CHO_PHEP_CU ghi {n} — sửa con số cho khớp"


# ── Luật 5 — bộ chạy tối thiểu của engine_dir có trong repo ──────────────────────
def test_bo_chay_toi_thieu_nam_trong_repo():
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import engine_dir as ED
    thieu = [r for r in ED.RUNNER_BAT_BUOC if not (ROOT / "scripts" / "runners" / r).is_file()]
    assert not thieu, f"scripts/runners thiếu runner bắt buộc: {thieu}"
