# -*- coding: utf-8 -*-
"""Bài mẫu cố định (`samples/`): tồn tại, chỉ là chữ, chấm lại ra ĐÚNG kết quả kỳ vọng.

Bài mẫu là thứ người dùng chạy đầu tiên sau khi cài và là thứ `doctor` xác minh offline. Nó
chỉ có giá trị khi kết quả kỳ vọng là CỐ ĐỊNH và máy kiểm được — test này giữ điều đó, và
giữ luôn ba mức của dòng `samples` trong `doctor` (PASS · WARN · NOT_CHECKED).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "samples"
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import blog_gates as BG  # noqa: E402
import doctor as DR  # noqa: E402


@pytest.fixture(scope="module")
def ky_vong():
    return json.loads((S / DR.KY_VONG).read_text(encoding="utf-8"))


def test_file_mau_co_du_va_chi_la_chu():
    for rel in ("README.md", DR.KY_VONG, "bai-mau/atlas/blog.md", "bai-mau/research.md",
                "bai-mau/facebook/post.txt", "bai-mau/facebook/comment.txt"):
        assert (S / rel).is_file(), rel
    la = [p for p in S.rglob("*") if p.is_file() and p.suffix.lower() not in
          (".md", ".txt", ".json")]
    assert not la, f"samples/ chỉ chứa chữ: {la}"


def test_link_trong_bai_mau_chi_la_ten_mien_VI_DU():
    for p in S.rglob("*"):
        if p.is_file():
            for u in re.findall(r"https?://([^/\s)]+)", p.read_text(encoding="utf-8")):
                assert u in ("example.com", "example.org", "example.net"), f"{p}: {u}"


def test_cham_lai_ra_DUNG_tung_cong_da_ghi(ky_vong):
    kq = BG.run_cmd(S / ky_vong["post"], ky_vong["home_domain"], stage=ky_vong["stage"])
    thay = {r["id"]: DR._trang_thai_cong(r) for r in kq["gates"]}
    assert thay == ky_vong["gates"]
    assert kq["verdict"] == ky_vong["verdict"]
    assert {k: kq[k] for k in ky_vong["counts"]} == ky_vong["counts"]


def test_bai_mau_KHONG_ghi_file_khi_cham_trong_bo_nho(ky_vong):
    truoc = sorted(p.name for p in (S / ky_vong["post"]).rglob("*"))
    DR.kiem_bai_mau(ROOT)
    assert sorted(p.name for p in (S / ky_vong["post"]).rglob("*")) == truoc


def test_README_ghi_dung_con_so_ky_vong(ky_vong):
    """README là thứ người đọc; JSON là thứ máy đọc. Hai bên nói hai số là một bên nói dối."""
    t = (S / "README.md").read_text(encoding="utf-8")
    c = ky_vong["counts"]
    assert f"| Tổng số cổng | {c['total']} |" in t
    assert f"| Xanh | {c['pass']} |" in t
    assert f"| Đỏ chặn (`fail_block`) | {c['fail_block']} " in t
    assert f"| Đỏ cảnh báo (`fail_warn`) | {c['fail_warn']} " in t
    assert f"| Chưa đo được (`missing`) | {c['missing']} " in t
    for g, st in ky_vong["gates"].items():
        if st == "fail_block":
            assert f"`{g}`" in t, f"README không nêu cổng chặn {g}"


def test_doctor_PASS_tren_ban_clone():
    muc, chi_tiet = DR.kiem_bai_mau(ROOT)
    assert muc == "pass", chi_tiet


def test_doctor_NOT_CHECKED_khi_khong_co_samples(tmp_path):
    muc, _ = DR.kiem_bai_mau(tmp_path)
    assert muc == "not_checked"
    assert DR.kiem_bai_mau(None)[0] == "not_checked"


def test_doctor_WARN_khi_bai_mau_bi_sua_lech(tmp_path):
    shutil.copytree(S, tmp_path / "samples")
    blog = tmp_path / "samples" / "bai-mau" / "atlas" / "blog.md"
    blog.write_text(blog.read_text(encoding="utf-8") + "\nCòn nợ [KIỂM CHỨNG].\n",
                    encoding="utf-8")
    muc, chi_tiet = DR.kiem_bai_mau(tmp_path)
    assert muc == "warn" and "G08" in chi_tiet, chi_tiet


def test_doctor_WARN_khi_ky_vong_hong(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / DR.KY_VONG).write_text("{hỏng", encoding="utf-8")
    assert DR.kiem_bai_mau(tmp_path)[0] == "warn"


def test_dong_samples_co_mat_trong_doctor(monkeypatch, tmp_path):
    """Nối vào luồng thật: `kham()` phải in dòng `samples: PASS`, không đổi mã thoát."""
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tmp_path / "tram"))
    kq = DR.kham()
    assert any(x.startswith("samples: PASS") for x in kq["info"]), kq["info"]


@pytest.mark.skipif(not shutil.which("git") or not (ROOT / ".git").exists(),
                    reason="cần bản clone git")
def test_nhat_ky_cong_chay_tay_bi_gitignore():
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index",
                        "samples/bai-mau/gates.json"])
    assert r.returncode == 0
