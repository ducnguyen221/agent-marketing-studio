# -*- coding: utf-8 -*-
"""Con trỏ bí mật (`YT_TOKEN_PATH`, `FB_CONFIG`…): cùng MỘT thứ tự ở mọi nơi, thiếu thì nêu tên.

Luật của repo (giống `telegram_io.py`): biến môi trường → `<repo>/.env` (chỉ embedded). Hai
đường mới dùng luật đó — `studio_paths.hook_env()` cho hook đăng bài và `install_launchd.py`
cho plist — nên cổng này giữ ba điều:

· biến thật luôn THẮNG `.env`;
· chỉ tên thuộc bộ con trỏ (kèm hậu tố kênh) đi từ `.env` sang tiến trình con;
· thiếu biến / giá trị không phải đường dẫn thì LỖI nêu đúng tên biến, không in giá trị.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import studio_paths as SP  # noqa: E402

TEN = ["YT_TOKEN_PATH", "YT_CLIENT_SECRET", "FB_CONFIG", "EMAIL_CONFIG", "TG_CONFIG",
       "CODEX_BRIDGE", "YT_TOKEN_PATH__TRUYEN", "FB_CONFIG_A"]


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for n in TEN + ["LA_HOAC", "PATH_GIA"]:
        monkeypatch.delenv(n, raising=False)
    r = tmp_path / "repo"
    r.mkdir()
    (r / SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "embedded"}), encoding="utf-8")
    (r / ".env").write_text(
        "YT_TOKEN_PATH=~/khoa/yt.json\n"
        "YT_TOKEN_PATH__TRUYEN=/khoa/truyen.json\n"
        "FB_CONFIG=123:token-tran\n"
        "LA_HOAC=/khong/duoc/di/theo\n"
        "PATH_GIA=/x\n", encoding="utf-8")
    return r


@pytest.mark.parametrize("ten,la", [("YT_TOKEN_PATH", True), ("YT_TOKEN_PATH__TRUYEN", True),
                                    ("FB_CONFIG_A", True), ("CODEX_BRIDGE", True),
                                    ("TG_CHAT", False), ("PATH", False), ("HOME", False),
                                    ("YT_TOKEN_PATHX", False), ("yt_token_path", False)])
def test_bo_ten_con_tro(ten, la):
    assert SP.la_con_tro_bi_mat(ten) is la


def test_hook_env_mang_DUNG_con_tro_tu_env(repo):
    e = SP.hook_env(repo)
    assert e["YT_TOKEN_PATH"] == str(Path("~/khoa/yt.json").expanduser())
    assert e["YT_TOKEN_PATH__TRUYEN"] == str(Path("/khoa/truyen.json"))
    assert "LA_HOAC" not in e, "tên ngoài bộ con trỏ không được đi theo"
    assert e.get("PATH_GIA") is None
    assert "FB_CONFIG" not in e, "giá trị không phải đường dẫn không được đi vào môi trường"


def test_hook_env_bien_THAT_thang_env(repo, monkeypatch):
    monkeypatch.setenv("YT_TOKEN_PATH", "/that/yt.json")
    assert SP.hook_env(repo)["YT_TOKEN_PATH"] == "/that/yt.json"


def test_hook_env_KHONG_doc_env_o_che_do_separate(repo):
    (repo / SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "separate"}), encoding="utf-8")
    assert "YT_TOKEN_PATH" not in SP.hook_env(repo)


def test_secret_path_thieu_thi_NEU_TEN_bien(repo):
    with pytest.raises(SP.StudioPathsError) as e:
        SP.secret_path("YT_CLIENT_SECRET", repo)
    assert "YT_CLIENT_SECRET" in str(e.value) and ".env" in str(e.value)


def test_secret_path_gia_tri_khong_phai_duong_dan_la_loi_KHONG_in_gia_tri(repo):
    with pytest.raises(SP.StudioPathsError) as e:
        SP.secret_path("FB_CONFIG", repo)
    assert "FB_CONFIG" in str(e.value) and "token-tran" not in str(e.value)


def test_secret_path_mo_rong_nga(repo):
    assert SP.secret_path("YT_TOKEN_PATH", repo) == str(Path("~/khoa/yt.json").expanduser())


def test_buoc_release_goi_hook_bang_hook_env():
    """Đường mặc định của bước `release` phải truyền `env=SP.hook_env()` cho hook."""
    src = (ROOT / "scripts" / "pipeline" / "campaign_step.py").read_text(encoding="utf-8")
    than = src.split("def step_release", 1)[1].split("\ndef ", 1)[0]
    assert "env=SP.hook_env()" in than
