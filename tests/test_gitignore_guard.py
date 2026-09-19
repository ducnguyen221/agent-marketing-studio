# -*- coding: utf-8 -*-
"""Rào của chế độ `embedded` (F17.4): `.gitignore` · hook pre-commit · `doctor` · `migrate`.

Chế độ `embedded` đặt nội dung riêng và `<repo>/.env` NGAY TRONG một repo có remote công
khai. Ba lớp rào, mỗi lớp bắt cái lớp trước để lọt:

  1. `.gitignore` — thói quen. Một dòng bị xoá là im lặng mở cửa ⇒ test dưới đây đòi từng
     dòng có mặt **theo tên**, không chấp nhận "một mẫu rộng hơn vẫn chặn": mẫu rộng hơn có
     thể biến mất ở lần dọn sau.
  2. hook pre-commit — cổng. Chặn `git add -f` và mọi thứ lách được `.gitignore`.
  3. `doctor` — người kiểm. Đo lại rằng hai lớp trên còn sống, và bắt "hai nguồn sự thật".

`migrate --to separate` là đường ra: người dùng lớn lên thì dời trạm khỏi repo mà không
phải chép tay.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import doctor as DR  # noqa: E402
import init_station as IS  # noqa: E402
import pre_commit_guard as PCG  # noqa: E402
import studio as ST  # noqa: E402
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

GITIGNORE = ROOT / ".gitignore"

# Xoá BẤT KỲ dòng nào dưới đây là test đỏ — kể cả khi một mẫu rộng hơn tình cờ vẫn chặn.
BAT_BUOC = ["/workspace/", ".env", ".env.*", "!.env.example", "studio.local.json"]


def _dong():
    return {d.strip() for d in GITIGNORE.read_text(encoding="utf-8").splitlines()}


@pytest.mark.parametrize("dong", BAT_BUOC)
def test_gitignore_giu_dung_dong_bat_buoc(dong):
    assert dong in _dong(), f".gitignore thiếu dòng bắt buộc của chế độ embedded: {dong}"


@pytest.mark.skipif(not (shutil.which("git") and (ROOT / ".git").exists()),
                    reason="cần bản clone git")
@pytest.mark.parametrize("duong,bi_chan", [
    ("workspace/ai-news/channel.yml", True),
    ("workspace/a.md", True),
    (".env", True),
    (".env.local", True),
    (".env.example", False),
    ("studio.local.json", True),
    ("templates/workspace/CHANNELS.md", False),
    ("scripts/pipeline/init_station.py", False),
])
def test_git_that_su_bo_qua(duong, bi_chan):
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", duong])
    assert (r.returncode == 0) is bi_chan, duong


# ── hook pre-commit ───────────────────────────────────────────────────────────────────

@pytest.fixture
def repo_git(tmp_path, monkeypatch):
    """Một repo git THẬT trong thư mục tạm — hook được đo bằng `git diff --cached` thật."""
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
    subprocess.run(["git", "init", "-q", str(r)], check=True, capture_output=True)
    for c in (["user.email", "x@y.z"], ["user.name", "x"]):
        subprocess.run(["git", "-C", str(r), "config", *c], check=True, capture_output=True)
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))
    for b in ("MARKETING_STUDIO_DATA", "VOICE_STATION", "OMNIVOICE_DIR",
              "VIDEO_STATION", "VIDEO_ROOT"):
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(r))
    return r


def _stage(repo, rel, noi_dung="x\n"):
    f = repo / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(noi_dung, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-f", rel], check=True, capture_output=True)


@pytest.mark.parametrize("rel", ["workspace/a.md", ".env", ".env.local", "studio.local.json"])
def test_hook_chan_noi_dung_tram_va_secret(repo_git, rel):
    _stage(repo_git, rel)
    van_de = PCG.soi(str(repo_git))
    assert van_de and rel in van_de[0]


def test_hook_cho_qua_file_binh_thuong(repo_git):
    _stage(repo_git, "scripts/pipeline/x.py", "print(1)\n")
    assert PCG.soi(str(repo_git)) == []


def test_hook_chan_dong_them_moi_giong_token(repo_git):
    _stage(repo_git, "docs/ghi-chu.md", "cau hinh: " + "gh" + "p_" + "A" * 36 + "\n")
    van_de = PCG.soi(str(repo_git))
    assert van_de and "token" in van_de[0]


def test_hook_KHONG_chan_chinh_khuon_trong_repo():
    """`.env.example` và `templates/` phải commit được — rào mà chặn cả khuôn là rào hỏng."""
    for d in (".env.example", "templates/workspace/CHANNELS.md", "templates/hooks/pre-commit"):
        assert not PCG.duong_bi_chan(d), d


# ── doctor ────────────────────────────────────────────────────────────────────────────

def test_doctor_bat_HAI_NGUON_SU_THAT(repo_git, tmp_path, monkeypatch):
    """Vừa có `<repo>/workspace/` vừa có trạm ngoài ⇒ không ai biết bài mới nằm ở đâu."""
    IS.do_init(yes=True)                                   # dựng embedded: có workspace/
    ngoai = tmp_path / "tram-ngoai"
    ngoai.mkdir()
    (ngoai / SP.SO_KENH).write_text("---\nchannels: []\n---\n", encoding="utf-8")
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(ngoai))
    kq = DR.kham()
    assert kq["code"] == SC.CONTRACT_ERROR
    assert any("hai nguồn sự thật" in x for x in kq["fail"]), kq


def test_doctor_XANH_sau_khi_init_embedded(repo_git):
    shutil.copyfile(ROOT / ".gitignore", repo_git / ".gitignore")
    IS.do_init(yes=True)
    kq = DR.kham()
    assert kq["code"] == SC.OK, kq["fail"]
    assert kq["mode"] == "embedded"


def test_doctor_bao_MA_3_khi_chua_cai(repo_git):
    kq = DR.kham()
    assert kq["code"] == SC.STATION_MISSING
    assert any("chưa" in x for x in kq["fail"]), kq


def test_doctor_bat_gitignore_bi_thung(repo_git):
    """Đây là cổng của cổng: `.gitignore` của bản clone mất một dòng thì doctor phải đỏ."""
    shutil.copyfile(ROOT / ".gitignore", repo_git / ".gitignore")
    IS.do_init(yes=True)
    thu = [d for d in (repo_git / ".gitignore").read_text(encoding="utf-8").splitlines()
           if d.strip() != "/workspace/"]
    (repo_git / ".gitignore").write_text("\n".join(thu) + "\n", encoding="utf-8")
    kq = DR.kham()
    assert kq["code"] == SC.CONTRACT_ERROR
    assert any(SP.WORKSPACE in x and "git" in x for x in kq["fail"]), kq


def test_doctor_canh_bao_repo_nam_trong_thu_muc_dong_bo_may(repo_git, tmp_path, monkeypatch):
    cloud = tmp_path / "OneDrive" / "repo"
    shutil.copytree(repo_git, cloud)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(cloud))
    IS.do_init(yes=True)
    kq = DR.kham()
    assert any("OneDrive" in x for x in kq["warn"]), kq


def test_doctor_CLI_json_tra_ma_thoat_that(repo_git, capsys):
    ma = DR.main(["--json"])
    out, _ = capsys.readouterr()
    assert ma == SC.STATION_MISSING
    kq = json.loads(out.strip().splitlines()[-1])
    assert kq["ok"] is False and kq["code"] == SC.STATION_MISSING


# ── migrate --to separate ─────────────────────────────────────────────────────────────

def test_migrate_doi_workspace_ra_ngoai_va_dời_env(repo_git, tmp_path):
    IS.do_init(yes=True)
    ws = repo_git / SP.WORKSPACE
    (ws / "kenh-cua-toi").mkdir()
    (ws / "kenh-cua-toi" / "channel.yml").write_text("id: kenh-cua-toi\n", encoding="utf-8")
    (repo_git / ".env").write_text("TG_CONFIG=D:/kho/tg.json\n", encoding="utf-8")
    kho = tmp_path / "kho-secret"
    dich = tmp_path / "tram-moi"

    kq = ST.migrate_sang_separate(station=str(dich), kho_secret=str(kho))

    assert Path(kq["station"]) == dich.resolve()
    assert (dich / "kenh-cua-toi" / "channel.yml").is_file()
    assert not ws.exists(), "workspace/ phải được DỜI, không phải chép"
    assert (kho / ".env").read_text(encoding="utf-8").startswith("TG_CONFIG=")
    assert not (repo_git / ".env").exists()
    lc = json.loads((repo_git / SP.LOCAL_CONFIG).read_text(encoding="utf-8"))
    assert lc["mode"] == "separate" and Path(lc["station_path"]) == dich.resolve()
    assert SP.resolve_station()[0] == dich.resolve()


def test_migrate_tu_choi_khi_dich_KHONG_RONG(repo_git, tmp_path):
    IS.do_init(yes=True)
    dich = tmp_path / "co-nguoi-o"
    dich.mkdir()
    (dich / "co-san.md").write_text("x", encoding="utf-8")
    with pytest.raises(SC.ContractError, match="không rỗng"):
        ST.migrate_sang_separate(station=str(dich), kho_secret=str(tmp_path / "kho"))
    assert (repo_git / SP.WORKSPACE).is_dir(), "từ chối thì phải chưa đụng gì"


def test_migrate_tu_choi_khi_kho_secret_da_co_env(repo_git, tmp_path):
    """Đè `.env` của kho secret là ghi đè cấu hình của cả máy — kiểm TRƯỚC khi dời gì."""
    IS.do_init(yes=True)
    (repo_git / ".env").write_text("A=1\n", encoding="utf-8")
    kho = tmp_path / "kho"
    kho.mkdir()
    (kho / ".env").write_text("B=2\n", encoding="utf-8")
    with pytest.raises(SC.ContractError, match="đã có"):
        ST.migrate_sang_separate(station=str(tmp_path / "moi"), kho_secret=str(kho))
    assert (repo_git / SP.WORKSPACE).is_dir() and (repo_git / ".env").is_file()


def test_migrate_khi_khong_o_che_do_embedded_la_loi(repo_git, tmp_path):
    IS.do_init(station=str(tmp_path / "ngoai"))
    with pytest.raises(SC.ContractError, match="embedded"):
        ST.migrate_sang_separate(station=str(tmp_path / "moi"), kho_secret=str(tmp_path / "kho"))


# ── update / backup ───────────────────────────────────────────────────────────────────

def test_update_KHONG_BAO_GIO_xoa_gi():
    """`update` = `git pull --ff-only`. Đo ĐÚNG những chuỗi sẽ đi vào `subprocess.run` —
    không grep cả file, vì chính docstring giải thích "không `git clean`" sẽ làm grep đỏ oan."""
    import ast
    cay = ast.parse((ROOT / "scripts" / "pipeline" / "studio.py").read_text(encoding="utf-8"))
    argv = []
    for nut in ast.walk(cay):
        if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)
                and nut.func.attr == "run" and nut.args):
            argv += [x.value for x in ast.walk(nut.args[0])
                     if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    assert argv, "không tìm thấy lời gọi subprocess.run nào — cổng này đang đo suông"
    for cam in ("clean", "reset", "checkout", "rm", "restore", "--force", "-f"):
        assert cam not in argv, f"studio.py truyền lệnh có thể xoá cho git: {cam!r} ({argv})"
    assert "--ff-only" in argv and "pull" in argv


def test_backup_zip_workspace_va_KHONG_kem_env(repo_git, tmp_path):
    IS.do_init(yes=True)
    (repo_git / SP.WORKSPACE / "bai.md").write_text("nội dung", encoding="utf-8")
    (repo_git / ".env").write_text("TG_CONFIG=x\n", encoding="utf-8")
    out = tmp_path / "goi.zip"
    kq = ST.backup(str(out))
    import zipfile
    with zipfile.ZipFile(out) as z:
        ten = set(z.namelist())
    assert "bai.md" in ten and "CHANNELS.md" in ten
    assert ".env" not in ten, "backup mặc định KHÔNG được kèm secret"
    assert kq["with_env"] is False


def test_backup_kem_env_chi_khi_xin_ro(repo_git, tmp_path):
    IS.do_init(yes=True)
    (repo_git / ".env").write_text("TG_CONFIG=x\n", encoding="utf-8")
    out = tmp_path / "goi2.zip"
    ST.backup(str(out), with_env=True)
    import zipfile
    with zipfile.ZipFile(out) as z:
        assert ".env" in set(z.namelist())


def test_backup_tu_choi_file_trong_giong_secret(repo_git, tmp_path):
    IS.do_init(yes=True)
    (repo_git / SP.WORKSPACE / "youtube_token.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SC.ContractError, match="giống secret"):
        ST.backup(str(tmp_path / "goi3.zip"))


# ── khuôn trong repo phải khớp cái mã trông đợi ───────────────────────────────────────

def test_cay_mau_workspace_du_file():
    t = ROOT / "templates" / SP.WORKSPACE
    for rel in ("README.md", "CHANNELS.md", "AUTHOR.md"):
        assert (t / rel).is_file(), rel


def test_CHANNELS_md_mau_KHONG_khai_san_kenh_khong_co_that(tmp_path):
    """Khai sẵn `ten-kenh` là để `check_tree.py` đỏ ngay phút đầu vì một đường không có thật."""
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import md_io  # noqa: E402
    fm, _ = md_io.read_fm(ROOT / "templates" / SP.WORKSPACE / "CHANNELS.md")
    assert fm.get("channels") == []
