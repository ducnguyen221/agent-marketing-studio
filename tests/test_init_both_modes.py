# -*- coding: utf-8 -*-
"""`init_station.py` — bộ cài hai chế độ (F17): `embedded` và `separate`.

Vì sao mỗi nhóm test dưới đây tồn tại:

· **Bộ cài phải HỎI, không được tự chọn im lặng.** Chế độ quyết định nội dung của người
  dùng nằm trong hay ngoài repo — chọn hộ là quyết hộ họ một thứ khó đảo.
· **Không có người trả lời thì DỪNG, đừng đoán.** Chạy trong CI, trong một tác vụ theo
  lịch, hay qua pipe: `input()` ném `EOF` và một bộ cài ẩu sẽ hiểu thành "Enter". Ở đây
  nó phải in bảng lựa chọn ra rồi thoát mã 2 mà **chưa ghi gì**.
· **Máy đã có trạm ngoài thì không bao giờ mọc thêm `workspace/`.** Đó là bảo vệ máy đang
  chạy lịch thật: hai nguồn sự thật cho cùng một repo là cách mất dữ liệu êm nhất.

Mọi test chạy trong thư mục tạm: repo giả (`MARKETING_STUDIO_HOME`) + nhà giả
(`HOME`/`USERPROFILE`). Không đụng trạm thật, không đụng `~`.
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
import init_station as IS  # noqa: E402
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

BIEN_HOP_DONG = ("MARKETING_STUDIO_DATA", "MARKETING_STUDIO_HOME", "VOICE_STATION",
                 "OMNIVOICE_DIR", "VIDEO_STATION", "VIDEO_ROOT")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Bản sao TỐI THIỂU của repo: đủ mốc để `repo_root()` nhận ra + cây mẫu thật."""
    r = tmp_path / "repo"
    (r / "scripts" / "lib").mkdir(parents=True)
    (r / "install.ps1").write_text("", encoding="utf-8")
    shutil.copytree(ROOT / "templates" / "workspace", r / "templates" / "workspace")
    (r / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "templates" / "hooks" / "pre-commit",
                    r / "templates" / "hooks" / "pre-commit")
    shutil.copyfile(ROOT / ".env.example", r / ".env.example")
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))
    for b in BIEN_HOP_DONG:
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(r))
    return r


@pytest.fixture
def nha(tmp_path):
    return tmp_path / "nha"


def khong_duoc_hoi(_bang):
    raise AssertionError("bộ cài không được hỏi trong trường hợp này")


def chup(*goc):
    ra = set()
    for g in goc:
        for dp, dn, fn in os.walk(g):
            for n in dn + fn:
                ra.add(os.path.join(dp, n))
    return ra


def cay_tram_ok(st: Path):
    assert (st / "CHANNELS.md").is_file()
    assert (st / "README.md").is_file()
    return st


def doc_local(repo: Path) -> dict:
    return json.loads((repo / SP.LOCAL_CONFIG).read_text(encoding="utf-8"))


# ── embedded ──────────────────────────────────────────────────────────────────────────

def test_Enter_nghia_la_embedded(repo, nha):
    bang = []
    kq = IS.do_init(ask=lambda b: bang.append(b) or "")
    ws = repo / SP.WORKSPACE
    cay_tram_ok(ws)
    assert kq["mode"] == "embedded"
    assert Path(kq["station"]) == ws.resolve()
    t = bang[0]
    for phai_co in ("embedded", "separate", "KHUYẾN NGHỊ", "Là gì", "Lợi", "Hại", "Chọn khi"):
        assert phai_co in t, f"bảng lựa chọn thiếu mục {phai_co!r}"
    lc = doc_local(repo)
    assert lc["mode"] == "embedded" and lc["station_path"] == SP.WORKSPACE
    assert lc["secrets"] == ".env"
    # mọi script từ giờ phân giải ra đúng trạm này
    st, nguon = SP.resolve_station()
    assert st == ws.resolve() and nguon == SP.LOCAL_CONFIG
    assert not (nha / ".marketing").exists(), "embedded không được đụng tới ~/.marketing"


# ── bảng lựa chọn PHÂN TÍCH theo trình độ người dùng (chỉ đạo 21/09) ──────────────────
#
# "Hỏi trống" — `Chọn [1/2]?` không kèm gì — là đẩy một quyết định khó đảo sang người
# chưa có dữ kiện để quyết. Bảng này phải TỰ PHÂN TÍCH: nói thẳng người kiểu nào nên chọn
# nhánh nào, và khuyến nghị một nhánh.

def test_bang_lua_chon_DAN_nguoi_dung_theo_TRINH_DO(repo):
    """Người không rành kỹ thuật phải đọc được câu dành cho mình ở nhánh `embedded`, và
    người nhiều máy/repo public đọc được câu của mình ở nhánh `separate`."""
    t = IS.BANG_LUA_CHON
    d1 = t[t.index("[1]"):t.index("[2]")]
    d2 = t[t.index("[2]"):]
    assert "không rành kỹ thuật" in d1, d1
    assert "KHUYẾN NGHỊ" in d1 and "Enter" in d1, d1
    for cum in ("rành kỹ thuật", "nhiều máy", "public"):
        assert cum in d2, f"nhánh separate thiếu {cum!r}:\n{d2}"


def test_bang_lua_chon_noi_ro_KHONG_BAT_BUOC_tram_giong_video(repo):
    """Lúc cài KHÔNG hỏi vu vơ "bạn có muốn cài trạm giọng/video không" — nhưng phải nói
    rằng cài xong là dùng được ngay, nếu không người mới tưởng mình còn thiếu hai repo nữa
    và bỏ dở giữa chừng. Lời đề nghị cài đến sau, đúng lúc chạm bước cần (voice.py)."""
    t = IS.BANG_LUA_CHON
    assert "không bắt buộc trạm giọng/video" in t, t
    assert "viết bài và đăng" in t.lower(), t


def test_co_yes_thi_nhan_khuyen_nghi_khong_hoi(repo):
    kq = IS.do_init(yes=True, ask=khong_duoc_hoi)
    assert kq["mode"] == "embedded" and (repo / SP.WORKSPACE / "CHANNELS.md").is_file()


def test_embedded_tao_env_tu_env_example_va_khoa_quyen(repo):
    IS.do_init(yes=True)
    f = repo / ".env"
    assert f.is_file(), "embedded phải dọn sẵn <repo>/.env để người dùng điền"
    assert "MARKETING_STUDIO_DATA" in f.read_text(encoding="utf-8")
    if os.name != "nt":
        assert oct(f.stat().st_mode & 0o777) == "0o600"


def test_embedded_cai_hook_pre_commit_va_KHONG_de_ban_co_san(repo):
    (repo / ".git" / "hooks").mkdir(parents=True)
    kq = IS.do_init(yes=True)
    hook = repo / ".git" / "hooks" / "pre-commit"
    assert hook.is_file() and "pre_commit_guard" in hook.read_text(encoding="utf-8")
    assert kq["hook"] == "đã cài"
    hook.write_text("#!/bin/sh\necho cua toi\n", encoding="utf-8")
    kq2 = IS.do_init(yes=True)
    assert "cua toi" in hook.read_text(encoding="utf-8") and kq2["hook"] == "giữ bản có sẵn"


def test_chay_lai_KHONG_de_file_da_co(repo):
    IS.do_init(yes=True)
    f = repo / SP.WORKSPACE / "CHANNELS.md"
    f.write_text("---\nschema: channels/1\nchannels: []\n---\n# của tôi\n", encoding="utf-8")
    IS.do_init(yes=True)
    assert "của tôi" in f.read_text(encoding="utf-8")


# ── separate: tường minh và tự nhận diện ──────────────────────────────────────────────

def test_tra_loi_2_nghia_la_separate_o_nha_marketing(repo, nha):
    kq = IS.do_init(ask=lambda b: "2")
    assert kq["mode"] == "separate"
    cay_tram_ok(nha / ".marketing")
    assert not (repo / SP.WORKSPACE).exists()
    assert doc_local(repo)["mode"] == "separate"


def test_co_station_thi_separate_khong_hoi(repo, tmp_path):
    st = tmp_path / "noi-khac"
    kq = IS.do_init(station=str(st), ask=khong_duoc_hoi)
    assert kq["mode"] == "separate" and kq["reason"] == "--station"
    cay_tram_ok(st)
    assert not (repo / SP.WORKSPACE).exists()
    assert Path(doc_local(repo)["station_path"]) == st.resolve()


@pytest.mark.parametrize("bien", ["MARKETING_STUDIO_DATA", "VOICE_STATION", "VIDEO_STATION",
                                  "OMNIVOICE_DIR", "VIDEO_ROOT"])
def test_bien_hop_dong_da_dat_thi_TU_CHON_separate(bien, repo, tmp_path, nha, monkeypatch):
    """Máy Đức: biến đã có từ trước ⇒ không hỏi, và KHÔNG BAO GIỜ tạo workspace/."""
    ngoai = tmp_path / "tram-cu"
    ngoai.mkdir()
    monkeypatch.setenv(bien, str(ngoai))
    kq = IS.do_init(yes=True, ask=khong_duoc_hoi)       # kể cả khi được bảo "nhận khuyến nghị"
    assert kq["mode"] == "separate" and bien in kq["reason"]
    assert not (repo / SP.WORKSPACE).exists()
    dich = ngoai if bien == "MARKETING_STUDIO_DATA" else nha / ".marketing"
    assert Path(kq["station"]) == dich.resolve()


def test_nha_marketing_co_marker_thi_TU_CHON_separate(repo, nha):
    (nha / ".marketing").mkdir(parents=True)
    (nha / ".marketing" / "CHANNELS.md").write_text("---\nchannels: []\n---\n", encoding="utf-8")
    kq = IS.do_init(ask=khong_duoc_hoi)
    assert kq["mode"] == "separate" and "CHANNELS.md" in kq["reason"]
    assert not (repo / SP.WORKSPACE).exists()


def test_doi_embedded_khi_may_da_co_tram_ngoai_la_LOI_khong_phai_cam_ket(repo, tmp_path,
                                                                         monkeypatch):
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tmp_path / "tram-cu"))
    with pytest.raises(SC.ContractError, match="hai nguồn sự thật"):
        IS.do_init(mode="embedded")
    assert not (repo / SP.WORKSPACE).exists()


# ── không có người trả lời ────────────────────────────────────────────────────────────

def test_khong_co_nguoi_tra_loi_thi_ma_2_va_KHONG_ghi_gi(repo, nha, capsys):
    truoc = chup(repo)
    ma = IS.main(["--json"])                 # stdin của pytest không phải terminal
    out, err = capsys.readouterr()
    assert ma == SC.CONTRACT_ERROR
    assert "embedded" in err and "separate" in err and "--mode" in err
    assert json.loads(out.strip().splitlines()[-1])["ok"] is False
    assert chup(repo) == truoc and not (nha / ".marketing").exists()


def test_tra_loi_bay_la_ma_2_va_KHONG_ghi_gi(repo):
    truoc = chup(repo)
    with pytest.raises(SC.ContractError):
        IS.do_init(ask=lambda b: "ba")
    assert chup(repo) == truoc


def test_existing_ma_khong_co_thu_muc_la_ma_3(repo, tmp_path):
    with pytest.raises(SC.StationMissing):
        IS.do_init(station=str(tmp_path / "khong-co"), existing=True)


def test_dry_run_khong_ghi_gi(repo, nha):
    truoc = chup(repo)
    kq = IS.do_init(yes=True, dry_run=True)
    assert kq["mode"] == "embedded" and kq["dry_run"] is True
    assert chup(repo) == truoc and not (nha / ".marketing").exists()


# ── cross-repo (F17.3): bộ cài ghi lại trạm giọng/video đã có ──────────────────────────

def test_ghi_lai_tram_giong_video_neu_may_da_co(repo, tmp_path, monkeypatch):
    giong, video = tmp_path / "giong", tmp_path / "video"
    for d in (giong, video):
        d.mkdir()
        (d / "station.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VOICE_STATION", str(giong))
    monkeypatch.setenv("VIDEO_STATION", str(video))
    IS.do_init(yes=True)
    lc = doc_local(repo)
    assert Path(lc["voice_station"]) == giong.resolve()
    assert Path(lc["video_station"]) == video.resolve()


# ── cây trạm dựng ra phải qua được cổng thật ──────────────────────────────────────────

@pytest.mark.parametrize("che_do", ["embedded", "separate"])
def test_check_tree_XANH_tren_cay_vua_dung(che_do, repo, tmp_path, nha):
    kq = IS.do_init(station=str(tmp_path / "ngoai") if che_do == "separate" else None,
                    yes=(che_do == "embedded"))
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "check_tree.py"),
                        "--station", kq["station"]],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 đỏ" in r.stdout


def test_CLI_json_in_dung_mot_dong_ket_qua(repo, capsys):
    ma = IS.main(["--yes", "--json"])
    out, _ = capsys.readouterr()
    assert ma == SC.OK
    kq = json.loads(out.strip().splitlines()[-1])
    assert kq["ok"] is True and kq["mode"] == "embedded"


# ── hai vỏ phải đi cùng nhau ──────────────────────────────────────────────────────────
#
# `install.ps1` và `install.sh` là hai cửa vào của CÙNG một bộ cài. Chúng trôi khỏi nhau
# một cách im lặng: sửa bên Windows rồi quên bên macOS thì không test nào đỏ, và người
# dùng macOS nhận một bộ cài khác — chỉ phát hiện khi họ đã cài xong.

INSTALL_PS1 = ROOT / "install.ps1"
INSTALL_SH = ROOT / "install.sh"


def test_ca_hai_vo_deu_giao_viec_cho_init_station():
    for f in (INSTALL_PS1, INSTALL_SH):
        t = f.read_text(encoding="utf-8-sig")
        assert "init_station.py" in t, f"{f.name} không gọi lõi chung"


def test_install_sh_khong_BOM_va_dung_LF():
    tho = INSTALL_SH.read_bytes()
    assert not tho.startswith(b"\xef\xbb\xbf"), "BOM làm `#!` hỏng: sh sẽ không chạy được file"
    assert b"\r\n" not in tho, "CRLF trong script sh = 'bad interpreter' trên macOS"
    assert tho.startswith(b"#!/bin/sh")


@pytest.mark.skipif(not shutil.which("sh"), reason="máy không có sh")
def test_install_sh_dung_cu_phap():
    r = subprocess.run([shutil.which("sh"), "-n", str(INSTALL_SH)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def test_install_ps1_giu_BOM():
    """PS 5.1 đọc file không BOM bằng ANSI — tiếng Việt trong file vỡ ngay dòng đầu."""
    assert INSTALL_PS1.read_bytes()[:3] == b"\xef\xbb\xbf"


# ── Bộ cài phải CHỈ ĐƯỜNG sang tài liệu ──────────────────────────────────────
# `install.sh`/`install.ps1` chỉ là vỏ dò interpreter; phần in ra cho người dùng nằm ở
# đây. Người vừa cài xong là người duy nhất chưa biết đọc tiếp cái gì — và cũng là người
# sắp mắc lỗi đắt nhất của cả hệ (bật lịch trên máy thứ hai).

@pytest.mark.parametrize("duong", ["docs/ONBOARDING.md", "docs/WORKSPACE.md",
                                   "docs/RUNBOOK-DOI-MAY.md"])
def test_bo_cai_in_duong_tai_lieu(capsys, duong):
    IS._in({"dry_run": False, "mode": "embedded", "station": "/x", "reason": "test",
            "created": [], "hook": None})
    ra = capsys.readouterr()
    assert duong in (ra.out + ra.err), f"bộ cài không chỉ sang {duong}"
    assert (ROOT / duong).is_file(), f"{duong} được in ra nhưng không tồn tại"


# ══ REVIEW-P2 N6 + N7 — lỗi CẤU HÌNH của `--station` phải là mã 2, và không ═
# ══ bao giờ để lại một cây nửa vời ══════════════════════════════════════════

def test_station_tro_vao_mot_FILE_la_ma_2(tmp_path):
    """`FileExistsError` lọt ra thành mã 1 = "thử lại được", và lịch chạy/CI sẽ thử lại
    vô hạn một lỗi gõ nhầm đường dẫn."""
    f = tmp_path / "toi-la-file"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(IS.SC.ContractError):
        IS.do_init(station=str(f), yes=True)


@pytest.mark.skipif(os.name != "nt", reason="MAX_PATH la luat cua Windows")
def test_duong_qua_MAX_PATH_la_ma_2_va_KHONG_tao_gi(tmp_path):
    """`station import` đã học bài này (`station.py:267`), `init_station` thì chưa: mkdir
    tạo được vài cấp rồi nổ, để lại cây nửa vời mà người dùng không biết dọn gì."""
    sau = tmp_path / ("x" * 90) / ("y" * 90) / ("z" * 90) / ("w" * 90)
    with pytest.raises(IS.SC.ContractError) as e:
        IS.do_init(station=str(sau), yes=True)
    assert "260" in str(e.value) or "dài" in str(e.value).lower()
    assert not (tmp_path / ("x" * 90)).exists(), "đã nổ mà vẫn để lại cây nửa vời"


def test_hai_VO_cai_xu_su_GIONG_NHAU_khi_khong_co_ai_tra_loi():
    """REVIEW-P2 N8. `install.sh --noninteractive` cho mã 2 (lõi không hiểu cờ, và kể cả
    hiểu thì luật "không có người ⇒ không đoán" cũng cho mã 2), trong khi `install.ps1
    -NonInteractive` lặng lẽ đổi thành `--yes` ⇒ cài embedded không hỏi ai.

    Đó là hai bộ cài khác nhau cho hai hệ điều hành — đúng thứ P2-T02 gộp lõi để tránh.
    Cổng này canh bằng văn bản vì không chạy được `install.ps1` thật trên máy CI macOS."""
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8-sig")
    dong = [d.strip() for d in ps1.splitlines()
            if "--yes" in d and not d.strip().startswith("#")]
    assert dong, "khong thay dong ghep --yes trong install.ps1"
    for d in dong:
        assert "NonInteractive" not in d, (
            "`-NonInteractive` KHONG duoc tu bien thanh `--yes`: khong co ai tra loi thi "
            "dung va bao ma 2, giong het install.sh")


def test_hai_VO_deu_chuyen_co_KHONG_TUONG_TAC_vao_LOI():
    """Parity phải là parity THẬT: cả hai vỏ cùng đổ vào một cờ của lõi, chứ không phải
    mỗi vỏ tự diễn giải "không có ai ngồi đây" theo cách riêng."""
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8-sig")
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "'--non-interactive'" in ps1
    assert "--non-interactive" in sh, "install.sh phai NHAC toi co nay (no forward $@)"
    # Va no phai la mot co THAT cua loi, khong phai mot chuoi trang tri:
    assert "--non-interactive" in IS._parser_help()


def test_non_interactive_KHONG_doan_che_do(tmp_path, monkeypatch):
    """`--non-interactive` nghĩa là "đừng hỏi", KHÔNG phải "đoán hộ tôi"."""
    for b in IS.BIEN_NHAN_DIEN:
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setattr(IS, "nha_marketing", lambda: tmp_path / "khong-co")
    with pytest.raises(IS.SC.ContractError) as e:
        IS.chon_che_do(non_interactive=True)
    assert "chọn chế độ" in str(e.value)
    # nhưng khai rõ thì vẫn chạy, không hỏi ai
    assert IS.chon_che_do(station=str(tmp_path / "t"), non_interactive=True)[0] == "separate"
