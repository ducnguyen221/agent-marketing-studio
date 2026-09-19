# -*- coding: utf-8 -*-
r"""Cổng di động HAI HỆ ĐIỀU HÀNH cho mọi `.ps1` của repo.

Mọi điểm vào tự động của repo là `.ps1`, và cùng một file phải chạy được ở hai nơi:
Windows PowerShell 5.1 (máy hôm nay, Task Scheduler) và pwsh 7 trên macOS (máy lịch
chính sau đợt chuyển máy). Audit 19/09/2026 chấm 4/10 vì các lỗi dưới đây — mỗi luật
trong `LUAT` là một kiểu hỏng đã tìm thấy thật, không phải phòng xa:

· biến thư mục nhà kiểu Windows      -> trên macOS là RỖNG, Join-Path ra đường tương đối
· gọi `python` trần                  -> macOS chỉ có `python3`; Windows có stub Store
· literal đuôi exe / trình PS cũ      -> không tồn tại trên macOS
· nối đường bằng gạch ngược           -> macOS coi gạch ngược là một ký tự trong TÊN file
· regex tách đường chỉ theo gạch ngược -> macOS khớp 0 dòng, và KHÔNG báo gì (sai im lặng)

Cách chữa chung: `$HOME`, `Join-Path` lồng với từng đoạn tên, hàm `Find-Python` chép
NGUYÊN vào từng file (PS 5.1 không có module chung), regex `[\\/]`.

Chuỗi cấm dựng từ mảnh (`chr(92)`, nối chuỗi) như `test_no_identity_leak.py`: lệnh
`grep` của người review quét cây repo, và file cổng không được là thứ làm nó đỏ.

Quét cả `.ps1` CHƯA commit (không bị ignore): thêm một file mới phạm luật là đỏ ngay
trong lượt test đầu tiên, không phải đợi tới lúc commit.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_BS = chr(92)
_E = re.escape

# ── Luật: (mã, giải thích, hàm khớp một DÒNG) ────────────────────────────────
_NHA_WIN = "$env:" + "USER" + "PROFILE"
_DUOI_EXE = "." + "ex" + "e"
_PS_CU = "power" + "shell" + _DUOI_EXE

_RE_NHA_WIN = re.compile(_E(_NHA_WIN), re.I)
_RE_PY_TRAN = re.compile(r"&\s*(?:python3?|py)(?=\s|$)", re.I)
_RE_EXE = re.compile(_E(_DUOI_EXE) + r"['\"]", re.I)
_RE_JOIN_BS = re.compile(r"Join-Path\b.*?(['\"])[^'\"\n]*" + _E(_BS) + r"[^'\"\n]*\1", re.I)
_RE_PS_CU = re.compile(_E(_PS_CU), re.I)
_RE_CMD_C = re.compile(r"\bcmd(?:" + _E(_DUOI_EXE) + r")?\s+/c\b", re.I)
# `$bien\ten` / `${bien}\ten` / `{0}\ten` trong chuỗi: nối đường bằng gạch ngược.
_RE_BIEN_BS = re.compile(
    r"(?:\$\{?[A-Za-z_][\w:]*\}?|\{\d+\})" + _E(_BS) + r"(?=[\w.<{])")
# Đường TƯƠNG ĐỐI viết bằng gạch ngược: `scripts\pipeline\x.py`, `.\examples`.
_RE_TUONG_DOI_BS = re.compile(
    r"(?<![\w$" + _E(_BS) + r"])(?:\.{1,2}|[A-Za-z_][\w.-]*)" + _E(_BS)
    + r"(?:(?:[\w.-]+" + _E(_BS) + r")*[\w-]+\.(?:py|ps1|md|json|html|ya?ml|txt|csv)\b"
    + r"|[A-Za-z_][\w-]*(?=[\s\"'`]|$))")
_RE_DO_PY = re.compile(
    r"(['\"])(?:python3?|py)\1|\bGet-Command\s+['\"]?(?:python3?|py)\b", re.I)
_RE_MATCH_SQ = re.compile(r"-i?match\s+'([^']*)'", re.I)
_LOP_GACH = "[" + _BS * 2 + "/]"


def _regex_tach_duong(dong: str) -> bool:
    r"""`$_.FullName -match '\\(\d{4})\\...'` — chỉ khớp gạch ngược => macOS khớp 0."""
    if "FullName" not in dong:
        return False
    for m in _RE_MATCH_SQ.finditer(dong):
        if _BS * 2 in m.group(1).replace(_LOP_GACH, ""):
            return True
    return False


LUAT = [
    ("nha-windows", "biến thư mục nhà chỉ Windows có -> dùng $HOME",
     lambda d: bool(_RE_NHA_WIN.search(d))),
    ("python-tran", "gọi python trần -> dùng Find-Python (macOS chỉ có python3)",
     lambda d: bool(_RE_PY_TRAN.search(d))),
    ("duoi-exe", "literal đuôi exe -> macOS không có",
     lambda d: bool(_RE_EXE.search(d))),
    ("join-path-gach-nguoc", "Join-Path với chuỗi có gạch ngược -> Join-Path lồng từng đoạn",
     lambda d: bool(_RE_JOIN_BS.search(d))),
    ("ps-cu", "gọi thẳng Windows PowerShell -> không có trên macOS",
     lambda d: bool(_RE_PS_CU.search(d))),
    ("cmd-c", "cmd /c -> không có trên macOS",
     lambda d: bool(_RE_CMD_C.search(d))),
    ("bien-gach-nguoc", "nối đường bằng gạch ngược sau biến -> Join-Path",
     lambda d: bool(_RE_BIEN_BS.search(d))),
    ("tuong-doi-gach-nguoc", "đường tương đối viết bằng gạch ngược -> dùng /",
     # Dòng đã bị luật Join-Path bắt thì không báo đúp: một chỗ sai, một lý do.
     lambda d: bool(_RE_TUONG_DOI_BS.search(d)) and not _RE_JOIN_BS.search(d)),
    ("regex-tach-duong", "regex tách đường chỉ theo gạch ngược -> [\\\\/]",
     _regex_tach_duong),
]
_LUAT_DO_PY = ("do-python-ngoai-find-python",
               "dò python bằng tên ngoài hàm Find-Python -> gọi Find-Python")


def _khoi_find_python(dong: list[str]) -> tuple[int, int] | None:
    """(đầu, cuối) — chỉ số dòng của `function Find-Python { ... }` (đóng bằng `}` cột 0)."""
    for i, d in enumerate(dong):
        if re.match(r"function\s+Find-Python\b", d):
            for j in range(i + 1, len(dong)):
                if dong[j].rstrip() == "}":
                    return i, j
            return i, len(dong) - 1
    return None


def quet(text: str) -> list[tuple[int, str]]:
    """Trả về [(số dòng, mã luật)]. Bỏ qua dòng chú thích `#…` và khối `<# … #>`.

    Nội dung here-string (`@" … "@`) KHÔNG phải chú thích — nó là chữ sẽ chạy/ghi ra, nên
    vẫn bị quét (đúng chỗ `write-post.SAMPLE.ps1` từng nối đường bằng gạch ngược).
    """
    dong = text.splitlines()
    khoi = _khoi_find_python(dong)
    ra: list[tuple[int, str]] = []
    trong_cmt = False
    for i, d in enumerate(dong):
        s = d.strip().lstrip("\ufeff")
        if trong_cmt:
            if "#>" in s:
                trong_cmt = False
            continue
        if s.startswith("<#"):
            trong_cmt = "#>" not in s[2:]
            continue
        if not s or s.startswith("#"):
            continue
        for ma, _, khop in LUAT:
            if khop(d):
                ra.append((i + 1, ma))
        trong_khoi = khoi is not None and khoi[0] <= i <= khoi[1]
        if not trong_khoi and _RE_DO_PY.search(d):
            ra.append((i + 1, _LUAT_DO_PY[0]))
    return ra


def _ds_ps1(goc: Path = ROOT) -> list[Path]:
    """`.ps1` đã commit + chưa commit mà không bị ignore."""
    ra = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.ps1"],
        cwd=goc, capture_output=True, check=True)
    ds = {goc / p for p in ra.stdout.decode("utf-8").split("\0") if p}
    return sorted(p for p in ds if p.is_file())


def _ds_ps1_tracked() -> list[Path]:
    ra = subprocess.run(["git", "ls-files", "-z", "--", "*.ps1"],
                        cwd=ROOT, capture_output=True, check=True)
    return sorted(ROOT / p for p in ra.stdout.decode("utf-8").split("\0") if p)


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig")


# ── Cổng chính ───────────────────────────────────────────────────────────────

def test_co_file_de_quet():
    """Cổng quét 0 file là cổng luôn xanh."""
    ds = _ds_ps1()
    assert len(ds) >= 7, f"chỉ thấy {len(ds)} file .ps1 — nghi lỗi môi trường"


def test_moi_ps1_di_dong_hai_os():
    dinh = []
    for p in _ds_ps1():
        dong = _doc(p).splitlines()
        for so, ma in quet(_doc(p)):
            dinh.append(f"{p.relative_to(ROOT).as_posix()}:{so} [{ma}] {dong[so - 1].strip()[:90]}")
    giai = "\n".join(f"  {ma}: {gt}" for ma, gt, _ in LUAT + [(*_LUAT_DO_PY, None)])
    # pytest.fail thay vì assert: thông báo in NGUYÊN chữ Việt, không qua repr() thành \uXXXX.
    if dinh:
        pytest.fail("`.ps1` không chạy được trên macOS/pwsh:\n  " + "\n  ".join(dinh)
                    + "\n\nLuật:\n" + giai, pytrace=False)


def test_find_python_CHEP_NGUYEN_giua_cac_file():
    """PS 5.1 không có module chung nên hàm được chép. Chép thì phải GIỐNG HỆT.

    Một bản bị sửa lẻ là hai file dò Python theo hai thứ tự khác nhau — cùng máy mà
    run.ps1 chạy một Python, runner chạy một Python khác, và không ai thấy vì cả hai
    đều "chạy được".
    """
    ban = {}
    for p in _ds_ps1():
        dong = _doc(p).replace("\r", "").splitlines()
        khoi = _khoi_find_python(dong)
        goi = any(re.search(r"\bFind-Python\b", d) and not d.lstrip().startswith("#")
                  for d in dong)
        if khoi is None:
            assert not goi, f"{p.name} gọi Find-Python mà không định nghĩa (PS 5.1 không import chung)"
            continue
        ban[p.relative_to(ROOT).as_posix()] = "\n".join(dong[khoi[0]:khoi[1] + 1])
    can = {"install.ps1", "templates/station/_channel/_campaign/run.ps1",
           "scripts/runners/run-worker.ps1", "scripts/runners/run-approve-poller.ps1",
           "scripts/runners/run-blog-campaign.ps1"}
    assert can <= set(ban), f"thiếu Find-Python ở: {sorted(can - set(ban))}"
    mau = ban["install.ps1"]
    lech = [f for f, b in ban.items() if b != mau]
    assert not lech, f"Find-Python bị sửa lẻ (khác install.ps1) ở: {lech}"


def test_moi_ps1_giu_BOM():
    """Mất BOM = PS 5.1 đọc tiếng Việt thành rác, và có khi parse hỏng => lịch chết câm."""
    thieu = [p.relative_to(ROOT).as_posix() for p in _ds_ps1_tracked()
             if p.read_bytes()[:3] != b"\xef\xbb\xbf"]
    assert not thieu, f"mất BOM UTF-8: {thieu}"


# ── Kiểm cú pháp bằng MỌI trình PowerShell có trên máy ───────────────────────
# Bản cũ là `which("pwsh") or which("powershell")`: máy nào có pwsh 7 thì 5.1 không bao giờ
# được hỏi. Trên `windows-latest` của CI pwsh 7 có sẵn ⇒ cú pháp chỉ 7 hiểu (`??`, `?:`,
# `&&`, `-f` mới…) đi qua CI xanh rồi CHẾT CÂM ở Task Scheduler 5.1 — đúng loại hỏng cả pha
# P1 sinh ra để chặn. Trình nào có mặt thì trình đó phải được hỏi, và mỗi trình là một test
# riêng để đọc kết quả biết ngay bản nào từ chối.
TRINH_PS = {ten: duong for ten, duong in
            ((t, shutil.which(t)) for t in ("powershell", "pwsh")) if duong}
PS = TRINH_PS.get("powershell") or TRINH_PS.get("pwsh")


def test_Windows_phai_co_PowerShell_5_1_de_kiem():
    """Windows nào cũng có `powershell` 5.1. Vắng nó = cổng 5.1 biến mất trong im lặng.

    Lịch thật trên máy Windows chạy bằng ĐÚNG 5.1; kiểm bằng pwsh 7 thôi là kiểm một trình
    khác với trình sẽ chạy.
    """
    if os.name != "nt":
        pytest.skip("may khong phai Windows — 5.1 khong ton tai o day")
    assert "powershell" in TRINH_PS, (
        "khong thay `powershell` (5.1) tren PATH: cong kiem cu phap 5.1 dang khong chay")


@pytest.mark.parametrize("ten", sorted(TRINH_PS) or [None])
def test_moi_ps1_parse_duoc(ten):
    """Parser của CHÍNH từng trình PowerShell có trên máy (5.1 Windows, pwsh 7 macOS/CI)."""
    if ten is None:
        # Không có trình nào: nói thành lời. Trên CI `conftest.pytest_configure` đã dừng cả
        # lượt (MARKETING_STUDIO_REQUIRE_POWERSHELL=1), nên im lặng ở đây không thành xanh giả.
        pytest.skip("khong co PowerShell tren may nay")
    ds = [str(p) for p in _ds_ps1_tracked()]
    lenh = ("$loi = @(); foreach ($f in $args) { $e = $null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$null, [ref]$e); "
            "foreach ($x in $e) { $loi += ($f + ':' + $x.Extent.StartLineNumber + ' ' + $x.Message) } }; "
            "$loi; exit $loi.Count")
    r = subprocess.run([TRINH_PS[ten], "-NoProfile", "-Command", "& {" + lenh + "}", *ds],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"{ten} không parse được:\n" + r.stdout + r.stderr


# ── Tự kiểm: cổng phải ĐỎ ĐÚNG LÝ DO ─────────────────────────────────────────
# Mỗi mẫu phạm ĐÚNG MỘT luật. Cổng bắt nhầm luật (hay bắt thêm luật khác) cũng là hỏng:
# người đọc thông báo sẽ đi sửa sai chỗ.

_Q = '"'
MAU_PHAM = [
    ("nha-windows", "$d = Join-Path " + _NHA_WIN + " '.marketing'"),
    ("python-tran", "& python $x --campaign $cam"),
    ("python-tran", "$ra = & python3 $py 2>&1"),
    ("duoi-exe", "$p = " + _Q + "C:/Tools/ffmpeg" + _DUOI_EXE + _Q),
    ("join-path-gach-nguoc", "Copy-Item (Join-Path $RepoRoot " + _Q + "templates" + _BS + "station" + _Q + ") $d"),
    ("ps-cu", "& " + _PS_CU + " -NoProfile -File $f"),
    ("cmd-c", "cmd /c dir"),
    ("bien-gach-nguoc", "Say " + _Q + "1. $cam" + _BS + "campaign.md" + _Q),
    ("bien-gach-nguoc", "Say (" + _Q + "--path {0}" + _BS + "ten-kenh" + _Q + " -f $s)"),
    ("tuong-doi-gach-nguoc", "Say " + _Q + "python scripts" + _BS + "pipeline" + _BS + "new_post.py" + _Q),
    ("tuong-doi-gach-nguoc", "Say " + _Q + "check --station ." + _BS + "examples" + _Q),
    ("regex-tach-duong", "$x | ? { $_.FullName -match '" + _BS * 2 + r"(\d{4})" + _BS * 2 + r"(\d{2})\.html$' }"),
    ("do-python-ngoai-find-python", "foreach ($t in @('python', 'py')) { }"),
    ("do-python-ngoai-find-python", "$c = Get-Command python -ErrorAction SilentlyContinue"),
]

MAU_SACH = [
    "$d = Join-Path $HOME '.marketing'",
    "$e = Join-Path $station (Join-Path 'engine' 'run.ps1')",
    "$py = Find-Python -Repo $repo",
    "$ra = & $python $py $Campaign 2>&1",
    "$x | ? { $_.FullName -match '[" + _BS * 2 + r"/](\d{4})[" + _BS * 2 + r"/](\d{2})\.html$' }",
    "Say " + _Q + "python scripts/pipeline/new_post.py --station ./examples" + _Q,
    "# " + _NHA_WIN + " trong CHÚ THÍCH không chạy, không tính",
    r"$s = $t -replace '^(\.\./)+', ''",
    "Write-Host ('run.ps1: ' + $cfg.runner + ' <- ' + $x)",
]


@pytest.mark.parametrize("ma,dong", MAU_PHAM, ids=[f"{m}-{i}" for i, (m, _) in enumerate(MAU_PHAM)])
def test_tu_kiem_mau_pham_do_DUNG_LUAT(ma, dong):
    hits = {m for _, m in quet(dong)}
    assert hits == {ma}, f"mẫu {dong!r}: mong đúng [{ma}], cổng bắt {sorted(hits)}"


@pytest.mark.parametrize("dong", MAU_SACH)
def test_tu_kiem_mau_sach_khong_bi_bat(dong):
    assert quet(dong) == [], f"báo đỏ oan: {dong!r} -> {quet(dong)}"


def test_tu_kiem_chu_thich_khoi_va_find_python(tmp_path):
    """Khối `<# … #>` bỏ qua; dò python TRONG Find-Python hợp lệ, NGOÀI nó thì đỏ."""
    src = "\n".join([
        "<#",
        ".EXAMPLE",
        "    " + _NHA_WIN,
        "#>",
        "function Find-Python {",
        "  param([string]$Repo)",
        "  foreach ($t in @('python', 'python3', 'py')) { }",
        "}",
        "foreach ($t in @('python')) { }",
    ])
    assert quet(src) == [(9, "do-python-ngoai-find-python")], quet(src)


def test_tu_kiem_file_moi_chua_commit_DO_DUNG_LY_DO(tmp_path):
    """Đầu-cuối trên một repo git TẠM: `.ps1` mới CHƯA `git add` mà phạm luật thì phải
    vào danh sách quét và đỏ đúng luật. Cổng không đợi tới lúc commit mới thấy."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "x.ps1").write_text("$d = Join-Path " + _NHA_WIN + " 'a'\n", encoding="utf-8-sig")
    (tmp_path / "sach.ps1").write_text("$d = Join-Path $HOME 'a'\n", encoding="utf-8-sig")
    ds = _ds_ps1(tmp_path)
    assert {p.name for p in ds} == {"x.ps1", "sach.ps1"}, ds
    ket = {p.name: quet(_doc(p)) for p in ds}
    assert ket == {"x.ps1": [(1, "nha-windows")], "sach.ps1": []}, ket
