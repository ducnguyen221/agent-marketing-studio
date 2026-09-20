# -*- coding: utf-8 -*-
"""Test cho `prune_media` — dọn media quá hạn ở các trạm.

Cách test: dựng cây GIẢ trong thư mục tạm rồi đặt `mtime` bằng `os.utime`. KHÔNG test
bằng trạm thật — trạm thật chứa thứ không dựng lại được, và một cổng dọn file mà chạy
lên dữ liệu thật để tự kiểm thì lần đầu nó sai là lần cuối người ta còn dữ liệu.

Nguyên tắc của bộ test này: mỗi luật giữ/dọn phải có CẢ HAI vế — một ca bị dọn và một ca
được giữ ĐÚNG LÝ DO. Chỉ khẳng định "có dọn" thì một script dọn sạch mọi thứ vẫn xanh.
"""
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "prune_media.py"
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import prune_media as PM  # noqa: E402

PY = sys.executable
NGAY = 86400


def _file(p: Path, tuoi_ngay: float, noi_dung=b"x" * 64) -> Path:
    """Tạo file với `mtime` lùi `tuoi_ngay` ngày."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(noi_dung)
    t = time.time() - tuoi_ngay * NGAY
    os.utime(p, (t, t))
    return p


def _chay(*args, cwd=None):
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([PY, str(SCRIPT), *[str(a) for a in args]],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, cwd=cwd)


@pytest.fixture
def tram(tmp_path):
    """Một trạm giả có đủ: media quá hạn, media còn hạn, và thứ CẤM ĐỤNG."""
    t = tmp_path / "tram"
    _file(t / "kenh-a" / "out" / "2026-01-01" / "bai.mp4", 30)
    _file(t / "kenh-a" / "out" / "2026-01-01" / "bai.mp3", 30)
    _file(t / "kenh-a" / "out" / "2026-01-01" / "bai.json", 30)
    _file(t / "kenh-a" / "out" / "2026-01-01" / "ghi-chu.md", 30)
    _file(t / "kenh-a" / "out" / "2026-01-01" / "anh.png", 30)
    _file(t / "kenh-a" / "out" / "moi" / "moi.mp4", 2)
    _file(t / "assets" / "nhac-nen" / "calm.mp3", 300)
    _file(t / "voices" / "giong-goc.wav", 300)
    _file(t / ".raw" / "mau-clone.wav", 300)
    _file(t / ".venv" / "Lib" / "site-packages" / "scipy" / "test.wav", 300)
    return t


# ── Luật tuổi ────────────────────────────────────────────────────────────────

def test_video_qua_han_bi_don(tram):
    kq = PM.quet([PM.Goc("tram", tram)], days=14)
    don = {e["rel"] for e in kq["entries"] if e["action"] == "prune"}
    assert "kenh-a/out/2026-01-01/bai.mp4" in don


def test_video_con_han_duoc_giu_dung_ly_do(tram):
    kq = PM.quet([PM.Goc("tram", tram)], days=14)
    giu = {e["rel"]: e["reason"] for e in kq["entries"] if e["action"] == "keep"}
    assert "kenh-a/out/moi/moi.mp4" in giu
    assert "hạn" in giu["kenh-a/out/moi/moi.mp4"]


def test_days_la_tham_so_that(tram):
    """`--days 60` thì video 30 ngày phải được GIỮ — nếu không, cờ chỉ là trang trí."""
    kq = PM.quet([PM.Goc("tram", tram)], days=60)
    assert not [e for e in kq["entries"] if e["action"] == "prune"]


# ── Luật audio: chỉ dọn khi đã có bản trên repo web ──────────────────────────

def test_audio_chua_co_ban_web_thi_GIU(tram):
    kq = PM.quet([PM.Goc("tram", tram)], days=14)
    giu = {e["rel"]: e["reason"] for e in kq["entries"] if e["action"] == "keep"}
    assert "kenh-a/out/2026-01-01/bai.mp3" in giu
    assert "web" in giu["kenh-a/out/2026-01-01/bai.mp3"].lower()


def test_audio_co_ban_web_thi_don(tram, tmp_path):
    web = tmp_path / "web"
    (web / "kenh-a" / "audio" / "2026-01-01").mkdir(parents=True)
    kq = PM.quet([PM.Goc("tram", tram)], days=14, web_repo=web)
    don = {e["rel"] for e in kq["entries"] if e["action"] == "prune"}
    assert "kenh-a/out/2026-01-01/bai.mp3" in don


def test_anh_xa_ten_kenh_web(tram, tmp_path):
    """Tên kênh ở trạm ≠ tên thư mục trên web (`ai-news` vs `ai`) — phải khai được."""
    web = tmp_path / "web"
    (web / "a" / "audio" / "2026-01-01").mkdir(parents=True)
    kq = PM.quet([PM.Goc("tram", tram)], days=14, web_repo=web)
    assert all(e["action"] == "keep" for e in kq["entries"]
               if e["rel"].endswith("bai.mp3")), "chưa khai ánh xạ mà đã dọn"
    kq = PM.quet([PM.Goc("tram", tram)], days=14, web_repo=web,
                 web_channel={"kenh-a": "a"})
    assert [e for e in kq["entries"] if e["rel"].endswith("bai.mp3")][0]["action"] == "prune"


def test_audio_policy_age_phai_khai_TUONG_MINH(tram):
    """Trạm mà audio chỉ là bản render trung gian (không có repo web nào) cần lối thoát —
    nhưng lối đó phải do người GÕ RA, không phải mặc định."""
    mac_dinh = PM.quet([PM.Goc("tram", tram)], days=14)
    assert [e for e in mac_dinh["entries"] if e["rel"].endswith("bai.mp3")][0]["action"] == "keep"
    theo_tuoi = PM.quet([PM.Goc("tram", tram)], days=14, audio_policy="age")
    assert [e for e in theo_tuoi["entries"] if e["rel"].endswith("bai.mp3")][0]["action"] == "prune"


# ── Thứ CẤM ĐỤNG ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cam", ["assets/nhac-nen/calm.mp3", "voices/giong-goc.wav",
                                 ".raw/mau-clone.wav",
                                 ".venv/Lib/site-packages/scipy/test.wav"])
def test_thu_muc_cam_khong_bao_gio_vao_ke_hoach(tram, cam):
    """Không phải "được giữ" — mà là KHÔNG XUẤT HIỆN. Một mục `keep` vẫn là một mục ai đó
    có thể lật thành `prune` bằng một cờ; thứ cấm phải nằm ngoài cả danh sách."""
    kq = PM.quet([PM.Goc("tram", tram)], days=14, audio_policy="age")
    assert cam not in {e["rel"] for e in kq["entries"]}


@pytest.mark.parametrize("duoi", [".json", ".md", ".png"])
def test_duoi_ngoai_danh_sach_khong_bao_gio_bi_dung(tram, duoi):
    kq = PM.quet([PM.Goc("tram", tram)], days=14, audio_policy="age")
    assert not [e for e in kq["entries"] if e["rel"].endswith(duoi)]


def test_goc_nam_trong_thu_muc_cam_bi_TU_CHOI(tram):
    """Trỏ thẳng `--root` vào `voices/` là cách dễ nhất để vượt rào — phải chặn."""
    r = _chay("--root", tram / "voices", "--dry-run")
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr


# ── Ba chế độ ───────────────────────────────────────────────────────────────

def test_dry_run_la_MAC_DINH_va_khong_ghi_gi(tram):
    truoc = sorted(p.relative_to(tram).as_posix() for p in tram.rglob("*") if p.is_file())
    r = _chay("--root", tram)
    assert r.returncode == PM.SC.OK, r.stderr
    sau = sorted(p.relative_to(tram).as_posix() for p in tram.rglob("*") if p.is_file())
    assert truoc == sau, "chạy không cờ nào mà cây đã đổi — mặc định KHÔNG phải dry-run"


def test_dry_run_khong_de_lai_manifest_khi_khong_duoc_xin(tram, tmp_path):
    ra = tmp_path / "ra"
    r = _chay("--root", tram, "--dry-run")
    assert r.returncode == PM.SC.OK, r.stderr
    assert not ra.exists()
    assert not list(tram.glob("manifest*"))


def test_move_to_giu_dung_cau_truc_tuong_doi(tram, tmp_path):
    kho = tmp_path / "kho"
    r = _chay("--root", f"tts-truyen-out={tram}", "--move-to", kho)
    assert r.returncode == PM.SC.OK, r.stderr
    assert (kho / "tts-truyen-out" / "kenh-a" / "out" / "2026-01-01" / "bai.mp4").is_file()
    assert not (tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp4").exists()
    # thứ được giữ vẫn nguyên chỗ cũ
    assert (tram / "kenh-a" / "out" / "moi" / "moi.mp4").is_file()
    assert (tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp3").is_file()
    assert (tram / "assets" / "nhac-nen" / "calm.mp3").is_file()


def test_move_to_tu_ghi_manifest(tram, tmp_path):
    kho = tmp_path / "kho"
    _chay("--root", tram, "--move-to", kho)
    m = kho / PM.TEN_MANIFEST
    assert m.is_file(), "dời mà không kê khai thì không lần ngược được"
    data = json.loads(m.read_text(encoding="utf-8"))
    mot = [e for e in data["entries"] if e["action"] == "prune"][0]
    assert {"rel", "bytes", "mtime", "reason", "action", "label"} <= set(mot)
    assert mot.get("moved_to"), "mục đã dời phải ghi chỗ mới"
    assert data["totals"]["prune"]["files"] >= 1


def test_move_to_KHONG_de_len_file_da_co(tram, tmp_path):
    kho = tmp_path / "kho"
    dich = kho / "tram" / "kenh-a" / "out" / "2026-01-01" / "bai.mp4"
    dich.parent.mkdir(parents=True)
    dich.write_bytes(b"ban cu")
    r = _chay("--root", tram, "--move-to", kho)
    assert dich.read_bytes() == b"ban cu", "đè lên bản đã có = mất dữ liệu im lặng"
    assert r.returncode != PM.SC.OK


def test_delete_chi_khi_goi_TUONG_MINH(tram, tmp_path):
    con = tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp4"
    _chay("--root", tram, "--move-to", tmp_path / "kho1")
    assert not con.exists()
    lai = _file(con, 30)
    r = _chay("--root", tram, "--delete")
    assert r.returncode == PM.SC.OK, r.stderr
    assert not lai.exists()


def test_move_to_va_delete_cung_luc_la_SAI_THAM_SO(tram, tmp_path):
    r = _chay("--root", tram, "--move-to", tmp_path / "k", "--delete")
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr


# ── Mã thoát theo hợp đồng ───────────────────────────────────────────────────

def test_khong_co_root_la_ma_2():
    assert _chay("--dry-run").returncode == PM.SC.CONTRACT_ERROR


def test_root_khong_ton_tai_la_ma_3(tmp_path):
    r = _chay("--root", tmp_path / "khong-co-dau", "--dry-run")
    assert r.returncode == PM.SC.STATION_MISSING, r.stderr


def test_nhan_root_sai_dinh_dang_la_ma_2(tram):
    r = _chay("--root", f"a/b={tram}", "--dry-run")
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr


def test_json_mot_dong_cuoi_stdout(tram):
    r = _chay("--root", tram, "--dry-run", "--json")
    assert r.returncode == PM.SC.OK, r.stderr
    data = PM.SC.last_json_line(r.stdout)
    assert data and data["ok"] is True
    assert data["totals"]["prune"]["files"] >= 1


# ── File đang bị khoá ────────────────────────────────────────────────────────

def test_file_khong_mo_duoc_de_ghi_thi_BO_QUA(tram):
    """Không đọc-ghi được = có thể đang có tiến trình giữ nó. Bỏ qua và ghi chú, không dọn.

    Dùng cờ chỉ-đọc vì đó là cách duy nhất tái lập được trên CẢ Windows lẫn POSIX: khoá
    bắt buộc của Windows không có bản tương đương trên POSIX, nên một test dựa vào nó sẽ
    xanh giả ở nửa số máy."""
    p = tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp4"
    os.chmod(p, stat.S_IREAD)
    try:
        kq = PM.quet([PM.Goc("tram", tram)], days=14)
        muc = [e for e in kq["entries"] if e["rel"].endswith("bai.mp4")][0]
        assert muc["action"] == "keep"
        assert "khoá" in muc["reason"] or "ghi" in muc["reason"]
    finally:
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)


# ── Chạy được trên cả hai hệ điều hành ───────────────────────────────────────

def test_duong_dan_kieu_macos(tram, monkeypatch):
    """`~/…`, `$BIEN` và dấu gạch chéo XUÔI — đó là cách người gõ trên macOS, và cả ba
    phải hiểu được trên Windows nữa — một repo hai hệ điều hành thì dòng lệnh trong tài
    liệu phải chạy được ở cả hai chỗ."""
    assert PM.no_duong("~/x") == (Path.home() / "x").resolve()
    monkeypatch.setenv("TRAM_THU", str(tram))
    assert PM.no_duong("$TRAM_THU") == tram.resolve()
    kq = PM.quet([PM.Goc("t", PM.no_duong(tram.as_posix()))], days=14)
    assert [e for e in kq["entries"] if e["rel"].endswith("bai.mp4")]


def test_rel_trong_manifest_luon_dau_gach_cheo_xuoi(tram):
    kq = PM.quet([PM.Goc("tram", tram)], days=14)
    assert all("\\" not in e["rel"] for e in kq["entries"])


def test_ma_nguon_khong_gia_dinh_windows():
    """Cổng chống 'chỉ chạy trên một máy': không `\\` trong đường dẫn, không biến của Windows."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "USERPROFILE" not in src
    assert "os.sep" not in src
    assert ":" + chr(92) not in src


def test_khong_chay_neu_move_to_nam_TRONG_goc(tram):
    """Dời vào chính cây đang quét = lượt sau quét lại chỗ vừa dời, lồng mãi."""
    r = _chay("--root", tram, "--move-to", tram / "kho")
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr
