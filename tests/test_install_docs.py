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
