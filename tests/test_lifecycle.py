# -*- coding: utf-8 -*-
"""Vòng đời cài → gỡ → cài lại trên một repo git THẬT trong thư mục tạm, nhà giả.

Luật được đo (khuôn chung của các studio):
  · `uninstall` gỡ ĐÚNG phần bộ cài tạo ra (`studio.local.json`, hook pre-commit của nó)
  · nội dung trạm, `.env` người dùng đã điền, và mọi thứ không phải của bộ cài: GIỮ nguyên
    từng byte (đo bằng file canary)
  · `update` dừng TRƯỚC khi kéo nếu checkout có sửa đổi chưa commit, và không đụng chúng
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import init_station as IS  # noqa: E402
import studio as ST  # noqa: E402
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

CANARY = "nội dung thật của người dùng — không được mất\n"


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True,
                          text=True, encoding="utf-8")


@pytest.fixture
def repo_git(tmp_path, monkeypatch):
    if not shutil.which("git"):
        pytest.skip("cần git")
    r = tmp_path / "repo"
    (r / "scripts" / "lib").mkdir(parents=True)
    (r / "install.ps1").write_text("", encoding="utf-8")
    shutil.copytree(ROOT / "templates" / "workspace", r / "templates" / "workspace")
    (r / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "templates" / "hooks" / "pre-commit",
                    r / "templates" / "hooks" / "pre-commit")
    shutil.copyfile(ROOT / ".env.example", r / ".env.example")
    shutil.copyfile(ROOT / ".gitignore", r / ".gitignore")
    _git(tmp_path, "init", "-q", str(r))
    for c in (["user.email", "x@y.z"], ["user.name", "x"]):
        _git(r, "config", *c)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "khoi tao")
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))
    for b in ("MARKETING_STUDIO_DATA", "VOICE_STATION", "OMNIVOICE_DIR",
              "VIDEO_STATION", "VIDEO_ROOT"):
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(r))
    return r


def _hook(repo) -> Path:
    return ST._hook_pre_commit(repo)


# ── uninstall ─────────────────────────────────────────────────────────────────────────

def test_embedded_go_dung_phan_bo_cai_va_GIU_tram_env(repo_git):
    IS.do_init(yes=True)
    ws = repo_git / SP.WORKSPACE
    (ws / "canary.md").write_text(CANARY, encoding="utf-8")
    (repo_git / ".env").write_text("TG_CHAT=kenh-rieng\n", encoding="utf-8")
    assert (repo_git / SP.LOCAL_CONFIG).is_file() and _hook(repo_git).is_file()

    kq = ST.uninstall()
    assert not (repo_git / SP.LOCAL_CONFIG).exists()
    assert not _hook(repo_git).exists()
    assert (ws / "canary.md").read_text(encoding="utf-8") == CANARY
    assert (repo_git / ".env").read_text(encoding="utf-8") == "TG_CHAT=kenh-rieng\n"
    assert kq["mode"] == "embedded" and len(kq["removed"]) == 2
    assert any(".env" in x for x in kq["kept"]) and any("trạm" in x for x in kq["kept"])


def test_separate_go_cau_hinh_GIU_tram_ngoai(repo_git, tmp_path):
    ngoai = tmp_path / "tram-ngoai"
    IS.do_init(station=str(ngoai))
    (ngoai / "canary.md").write_text(CANARY, encoding="utf-8")
    kq = ST.uninstall()
    assert not (repo_git / SP.LOCAL_CONFIG).exists()
    assert (ngoai / "canary.md").read_text(encoding="utf-8") == CANARY
    assert kq["station"] == str(ngoai.resolve())


def test_dry_run_khong_go_gi(repo_git):
    IS.do_init(yes=True)
    kq = ST.uninstall(dry_run=True)
    assert kq["dry_run"] and kq["removed"]
    assert (repo_git / SP.LOCAL_CONFIG).is_file() and _hook(repo_git).is_file()


def test_hook_KHONG_phai_cua_bo_cai_thi_giu(repo_git):
    IS.do_init(yes=True)
    hook = _hook(repo_git)
    hook.write_text("#!/bin/sh\n# hook riêng của người dùng\nexit 0\n", encoding="utf-8")
    kq = ST.uninstall()
    assert hook.is_file(), "gỡ mất hook không phải của mình"
    assert any("không phải hook của bộ cài" in x for x in kq["kept"])


def test_go_xong_cai_lai_duoc_va_du_lieu_con_nguyen(repo_git):
    IS.do_init(yes=True)
    (repo_git / SP.WORKSPACE / "canary.md").write_text(CANARY, encoding="utf-8")
    ST.uninstall()
    kq = IS.do_init(yes=True)
    assert kq["mode"] == "embedded" and (repo_git / SP.LOCAL_CONFIG).is_file()
    assert (repo_git / SP.WORKSPACE / "canary.md").read_text(encoding="utf-8") == CANARY


def test_go_hai_lan_khong_loi(repo_git):
    IS.do_init(yes=True)
    ST.uninstall()
    kq = ST.uninstall()
    assert kq["removed"] == []


def test_file_cau_hinh_hong_van_go_duoc(repo_git):
    (repo_git / SP.LOCAL_CONFIG).write_text("{hong", encoding="utf-8")
    kq = ST.uninstall()
    assert not (repo_git / SP.LOCAL_CONFIG).exists() and kq["mode"] is None


def test_CLI_uninstall_json(repo_git, capsys):
    IS.do_init(yes=True)
    assert ST.main(["uninstall", "--json"]) == 0
    dong = [d for d in capsys.readouterr().out.splitlines() if d.strip().startswith("{")]
    ra = json.loads(dong[-1])
    assert ra["ok"] is True and ra["removed"]


# ── update ────────────────────────────────────────────────────────────────────────────

def test_update_DUNG_truoc_khi_keo_neu_co_sua_doi_va_KHONG_dung_toi_no(repo_git):
    f = repo_git / ".env.example"
    f.write_text(f.read_text(encoding="utf-8") + "# sửa tay\n", encoding="utf-8")
    truoc = f.read_bytes()
    with pytest.raises(SC.ContractError, match="chưa commit"):
        ST.update()
    assert f.read_bytes() == truoc


def test_update_bo_qua_file_bi_ignore_cua_nguoi_dung(repo_git):
    """`workspace/`, `.env`, `studio.local.json` là dữ liệu, không phải "sửa đổi mã"."""
    IS.do_init(yes=True)
    (repo_git / SP.WORKSPACE / "bai.md").write_text("x", encoding="utf-8")
    assert ST._sua_doi_cuc_bo(repo_git) == []
    with pytest.raises(SC.EngineError):       # sạch → tới bước kéo; repo tạm không có remote
        ST.update()
