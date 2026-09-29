# -*- coding: utf-8 -*-
"""INSTALL.md là hợp đồng giữa người dùng và agent cài hộ — nó phải đúng, gọn và an toàn.

Đo:
  · prompt copy-dán có bản VI + EN, mỗi bản ≤ 12 dòng; README chép ĐÚNG bản VI (một nguồn)
  · luật an toàn có mặt: không đổi ExecutionPolicy, không tải-rồi-chạy, không đụng bí mật,
    không đăng bài, hỏi trước khi cài
  · mọi script INSTALL.md bảo chạy có thật trong repo; mọi host được nhắc có trang hướng dẫn
  · lệnh bộ cài trong INSTALL.md dùng đúng cờ mà `install.ps1`/`install.sh`/`uninstall.ps1` nhận
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "INSTALL.md").read_text(encoding="utf-8")


def _prompt() -> list[str]:
    phan = INSTALL.split("## Prompt copy-dán", 1)
    assert len(phan) == 2, "INSTALL.md thiếu mục '## Prompt copy-dán'"
    return re.findall(r"```text\n(.*?)```", phan[1], re.S)


def test_prompt_co_VI_va_EN_moi_ban_toi_da_12_dong():
    ds = _prompt()
    assert len(ds) == 2, f"cần đúng 2 khối prompt (VI, EN), thấy {len(ds)}"
    vi, en = ds
    assert "Hãy cài" in vi and "Install" in en
    for ten, k in (("VI", vi), ("EN", en)):
        dong = k.strip("\n").splitlines()
        assert len(dong) <= 12, f"prompt {ten} dài {len(dong)} dòng (tối đa 12)"
        assert "INSTALL.md" in k and "github.com/" in k and "/agent-marketing-studio" in k


def test_README_chep_dung_prompt_VI():
    vi = _prompt()[0]
    assert vi in (ROOT / "README.md").read_text(encoding="utf-8"), (
        "README phải chép NGUYÊN VĂN prompt VI từ INSTALL.md — hai bản sửa tay sẽ trôi")


@pytest.mark.parametrize("luat", [
    "ExecutionPolicy", "iex", "Invoke-Expression", "Không đụng bí mật", "Không đăng gì",
    "Hỏi trước khi chạm máy", "OneDrive", "NOT_CHECKED",
])
def test_luat_an_toan_co_mat(luat):
    assert luat in INSTALL, f"INSTALL.md thiếu luật/ý: {luat}"


def test_script_duoc_bao_chay_deu_co_that():
    ten = set(re.findall(r"\b((?:un)?install\.(?:ps1|sh))\b", INSTALL))
    ten |= set(re.findall(r"(scripts[\\/][\w/\\]+\.py)", INSTALL))
    assert {"install.ps1", "install.sh", "uninstall.ps1", "uninstall.sh"} <= ten
    thieu = [t for t in ten if not (ROOT / t.replace("\\", "/")).is_file()]
    assert not thieu, f"INSTALL.md bảo chạy file không có: {thieu}"


def test_co_trang_huong_dan_cho_moi_host():
    for h in ("claude", "codex", "antigravity", "claude-desktop"):
        f = ROOT / "hosts" / h / "README.md"
        assert f.is_file(), f"thiếu {f.relative_to(ROOT)}"
        assert "INSTALL.md" in f.read_text(encoding="utf-8") or h == "claude-desktop"
    assert (ROOT / "hosts" / "README.md").is_file()


def _co_ps1(file: str) -> set[str]:
    src = (ROOT / file).read_text(encoding="utf-8-sig")
    khoi = re.search(r"param\((.*?)\n\)", src, re.S).group(1)
    return {m.lower() for m in re.findall(r"\$(\w+)", khoi)}


def test_co_cua_lenh_cai_go_KHOP_script_that():
    """Tài liệu gọi `-Mode`/`-Station`/`-DryRun` — script đổi tên cờ là tài liệu chết im lặng."""
    for m in re.finditer(r"\b(install|uninstall)\.ps1((?:\s+-\w+)+)", INSTALL):
        co = {c.lstrip("-").lower() for c in m.group(2).split()}
        co.discard("file")
        thieu = co - _co_ps1(f"{m.group(1)}.ps1")
        assert not thieu, f"{m.group(0)!r}: {m.group(1)}.ps1 không có cờ {thieu}"
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")
    for co in set(re.findall(r"\./install\.sh\s+(--[\w-]+)", INSTALL)):
        assert co in sh or co.lstrip("-") in (ROOT / "scripts/pipeline/init_station.py").read_text(
            encoding="utf-8"), f"install.sh/init_station không hiểu {co}"


# ── A10: START-HERE · trang /install/ · gỡ vướng — cùng MỘT prompt, cùng một nguồn ──────

def _doc(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def _pre(page: str, ident: str) -> str:
    import html
    m = re.search(rf'<pre id="{ident}">(.*?)</pre>', page, re.S)
    assert m, f'thiếu <pre id="{ident}">'
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip("\n")


def test_START_HERE_ngan_va_chep_DUNG_prompt_VI():
    t = _doc("START-HERE.md")
    assert len(t.splitlines()) <= 60, "START-HERE.md phải ngắn (≤ 60 dòng)"
    assert _prompt()[0] in t, "START-HERE phải chép NGUYÊN VĂN prompt VI từ INSTALL.md"
    for can in ("INSTALL.md", "docs/troubleshooting.md", "samples/README.md", "docs/launchd.md",
                "python3.12"):
        assert can in t, f"START-HERE.md thiếu {can}"


def test_trang_install_chep_DUNG_hai_prompt_va_duoc_trang_chu_tro_toi():
    page = _doc("docs/install/index.html")
    vi, en = (p.strip("\n") for p in _prompt())
    assert _pre(page, "prompt-vi") == vi
    assert _pre(page, "prompt-en") == en
    for host in ("Claude Code", "Codex", "Antigravity", "Claude Desktop"):
        assert host in page, host
    assert 'href="install/"' in _doc("docs/index.html"), "trang chủ chưa trỏ tới /install/"


def test_trang_go_vuong_ton_tai_va_duoc_tro_toi():
    t = _doc("docs/troubleshooting.md")
    for muc in ("## Khi cài", "## Dòng `doctor`", "## Lịch chạy trên macOS (launchd)"):
        assert muc in t, muc
    for rel in ("INSTALL.md", "START-HERE.md"):
        assert "docs/troubleshooting.md" in _doc(rel), f"{rel} chưa trỏ tới docs/troubleshooting.md"


@pytest.mark.parametrize("y", [
    "python3.12 -m venv .venv",        # python3 của Mac mới là 3.9
    "xcode-select --install",          # Command Line Tools — người dùng bấm Install
    "brew.sh",                         # Homebrew do NGƯỜI DÙNG cài (lệnh tải-rồi-chạy bị cấm)
    "/opt/homebrew/bin",               # PATH của Apple Silicon
    "brew install --cask powershell",  # pwsh cho runner .ps1
    "zsh -lic",                        # kiểm biến bằng shell đăng nhập
    "install_launchd.py --dry-run --no-load",
])
def test_INSTALL_du_cho_Mac_moi_tinh(y):
    assert y in INSTALL, f"INSTALL.md thiếu hướng dẫn macOS: {y}"


def test_INSTALL_KHONG_bao_agent_tu_cai_Homebrew():
    """Lệnh cài Homebrew là tải-rồi-chạy — đúng thứ mục 0 cấm. Chỉ trỏ người dùng tới brew.sh."""
    assert "install.sh)" not in INSTALL and "curl -fsSL" not in INSTALL
