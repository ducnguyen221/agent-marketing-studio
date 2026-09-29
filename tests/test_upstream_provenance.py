# -*- coding: utf-8 -*-
"""Phần CHƯNG CẤT từ repo ngoài: ghi công đủ (NOTICE), sổ nguồn khớp đĩa (upstream.json).

Ba thứ hỏng IM LẶNG nếu không có cổng:

1. **Thêm một file chưng cất mà quên ghi nguồn.** Mọi file mang dòng "Chưng cất từ `owner/repo`"
   phải có mặt trong `upstream.json` dưới đúng repo đó — và ngược lại.
2. **Sửa file chưng cất mà không rà lại nguồn.** `upstream.json` giữ sha256 của bản trong repo;
   sửa file mà không cập nhật hash là đỏ, tức lần sửa đó buộc phải có người nhìn lại nguồn.
3. **Nghĩa vụ MIT.** NOTICE phải mang đúng dòng Copyright của từng nguồn và văn bản giấy phép.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SO = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
NOTICE = (ROOT / "NOTICE").read_text(encoding="utf-8")
NGUON = SO["sources"]

# Dòng ghi nguồn đầu thân bài. `owner/repo` trong dấu nháy ngược, đứng ngay sau "từ", "+",
# "·" hoặc "của" — đường con trong upstream (`skills/marketing-psychology`) đứng sau dấu `)`
# của ghi chú giấy phép nên không bị đếm nhầm thành một repo.
_DONG = re.compile(r"^>?\s*Chưng cất từ[^\n]*", re.M | re.I)
_REPO = re.compile(r"(?:từ:?|\+|·|của)\s+`([\w.-]+/[\w.-]+)`", re.I)


def _hash(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _tracked_md() -> list[str]:
    ra = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True)
    if ra.returncode != 0:
        pytest.skip("cần bản clone git")
    return [p for p in ra.stdout.decode("utf-8").split("\0") if p]


def _khai_trong_file() -> dict:
    """{owner/repo: {file}} đọc từ chính các dòng "Chưng cất từ" trong cây git."""
    ra: dict = {}
    for rel in _tracked_md():
        if rel.startswith("tests/"):
            continue
        for dong in _DONG.findall((ROOT / rel).read_text(encoding="utf-8", errors="replace")):
            for repo in _REPO.findall(dong):
                if not (ROOT / repo).exists():          # đường trong repo, không phải nguồn ngoài
                    ra.setdefault(repo, set()).add(rel)
    return ra


def test_moi_file_khai_chung_cat_DEU_co_trong_so_nguon():
    khai = _khai_trong_file()
    assert khai, "không thấy dòng 'Chưng cất từ' nào — cổng đang quét hụt"
    for repo, files in khai.items():
        assert repo in NGUON, f"{sorted(files)} khai chưng cất từ {repo} mà upstream.json không có"
        thieu = files - set(NGUON[repo]["files"])
        assert not thieu, f"{repo}: file khai nguồn mà sổ thiếu: {sorted(thieu)}"


def test_so_nguon_KHONG_ghi_file_khong_khai_nguon():
    khai = _khai_trong_file()
    for repo, src in NGUON.items():
        thua = set(src["files"]) - khai.get(repo, set())
        assert not thua, f"{repo}: sổ ghi {sorted(thua)} nhưng file không nêu nguồn đó ở đầu bài"


@pytest.mark.parametrize("repo,rel", [(r, f) for r, s in NGUON.items() for f in s["files"]])
def test_hash_ban_chung_cat_KHOP_so(repo, rel):
    assert (ROOT / rel).is_file(), rel
    assert _hash(rel) == NGUON[repo]["files"][rel], (
        f"{rel} đã đổi so với bản đã rà nguồn ({repo}). Rà lại phần chưng cất, rồi cập nhật "
        f"sha256 trong upstream.json trong cùng commit.")


@pytest.mark.parametrize("repo", sorted(NGUON))
def test_NOTICE_ghi_cong_du_theo_MIT(repo):
    src = NGUON[repo]
    assert src["license"] == "MIT"
    assert src["url"] == f"https://github.com/{repo}"
    assert repo in NOTICE and src["copyright"] in NOTICE, f"NOTICE thiếu ghi công {repo}"
    for rel in src["files"]:
        assert rel in NOTICE, f"NOTICE không liệt kê {rel} dưới nguồn nào"


def test_NOTICE_mang_van_ban_giay_phep_MIT():
    for cau in ("Permission is hereby granted, free of charge",
                "The above copyright notice and this permission notice shall be included",
                'THE SOFTWARE IS PROVIDED "AS IS"'):
        assert cau in NOTICE, cau


def test_tham_khao_thiet_ke_noi_ro_KHONG_chep_van_ban():
    for repo, ref in SO.get("design_references", {}).items():
        assert ref["copied_text"] is False
        assert repo in NOTICE
        for rel in ref["used_in"]:
            assert (ROOT / rel).is_file(), rel
