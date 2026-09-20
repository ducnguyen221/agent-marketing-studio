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


def _so_dang(p: Path, tuoi_ngay=30, **khoa) -> Path:
    """Một cuốn `*.published.json` như đường ống tin ghi ra — CÓ BOM, đúng như trên đĩa."""
    d = {"uploaded_at": "2026-01-01T02:20:18", "video_id": "vid-da-dang", **khoa}
    return _file(p, tuoi_ngay, json.dumps(d, ensure_ascii=False).encode("utf-8-sig"))


@pytest.fixture
def tram(tmp_path):
    """Một trạm giả có đủ: media quá hạn ĐÃ ĐĂNG, media còn hạn, và thứ CẤM ĐỤNG.

    Có `*.published.json` vì luật hiện hành (Đức chốt 20/09) chỉ dọn khi CÓ bằng chứng;
    một trạm giả không có sổ đăng nào thì mọi test dọn/dời bên dưới xanh vì lý do sai."""
    t = tmp_path / "tram"
    _so_dang(t / "kenh-a" / "out" / "2026-01-01" / "bai.json.published.json")
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
    _file(web / "kenh-a" / "audio" / "2026-01-01" / "bai.mp3", 30)
    kq = PM.quet([PM.Goc("tram", tram)], days=14, web_repo=web)
    don = {e["rel"] for e in kq["entries"] if e["action"] == "prune"}
    assert "kenh-a/out/2026-01-01/bai.mp3" in don


def test_ban_web_doi_chieu_theo_FILE_khong_phai_theo_THU_MUC(tram, tmp_path):
    """REVIEW-P2 N2. Thư mục web của ngày đó tồn tại **không** chứng minh gì cho từng file.

    Ca thật: `podcast.mp3` đã đăng nên `<web>/…/2026-01-01/` có mặt; `raw.wav` cùng ngày
    chưa từng đăng. So theo thư mục thì `raw.wav` bị dọn vì một file anh em — với
    `--delete` là mất hẳn bản audio duy nhất, đúng thứ docstring của script thề tránh."""
    web = tmp_path / "web"
    _file(web / "kenh-a" / "audio" / "2026-01-01" / "podcast.mp3", 30)
    _file(tram / "kenh-a" / "out" / "2026-01-01" / "podcast.mp3", 30)
    _file(tram / "kenh-a" / "out" / "2026-01-01" / "raw.wav", 30)
    kq = PM.quet([PM.Goc("tram", tram)], days=14, web_repo=web)
    theo = {e["rel"]: e for e in kq["entries"]}
    assert theo["kenh-a/out/2026-01-01/podcast.mp3"]["action"] == "prune"
    con = theo["kenh-a/out/2026-01-01/raw.wav"]
    assert con["action"] == "keep", "bản web của FILE KHÁC không phải bằng chứng cho file này"
    assert "raw" in con["reason"]


def test_ban_web_khac_duoi_van_tinh_la_da_dang(tram, tmp_path):
    """Web phát `.mp3`, trạm giữ `.wav` của CÙNG bản dựng — cùng `stem` là cùng một bản."""
    web = tmp_path / "web"
    _file(web / "kenh-a" / "audio" / "2026-01-01" / "bai.mp3", 30)
    _file(tram / "kenh-a" / "out" / "2026-01-01" / "bai.wav", 30)
    kq = PM.quet([PM.Goc("tram", tram)], days=14, web_repo=web)
    theo = {e["rel"]: e["action"] for e in kq["entries"]}
    assert theo["kenh-a/out/2026-01-01/bai.wav"] == "prune"


def test_anh_xa_ten_kenh_web(tram, tmp_path):
    """Tên kênh ở trạm ≠ tên thư mục trên web (`ai-news` vs `ai`) — phải khai được."""
    web = tmp_path / "web"
    _file(web / "a" / "audio" / "2026-01-01" / "bai.mp3", 30)
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


# ══ LUẬT MỚI: BẰNG CHỨNG ĐÃ ĐĂNG, không chỉ tuổi file ═══════════════════════
# Đức chốt 2026-09-20: video chỉ dọn khi đã lên YouTube, audio chỉ dọn khi đã có bản
# trong repo web. 14 ngày hạ xuống thành SÀN AN TOÀN — phải thoả CẢ HAI vế.

def test_video_KHONG_co_bang_chung_thi_GIU(tmp_path):
    """Vế mới quan trọng nhất. Một `.mp4` 30 ngày tuổi mà không sổ nào nhận là đã đăng có
    thể là lượt render hỏng chưa ai đăng lại — xoá nó là mất hẳn."""
    t = tmp_path / "tram"
    _file(t / "kenh-a" / "out" / "2026-01-01" / "bai.mp4", 30)
    kq = PM.quet([PM.Goc("tram", t)], days=14)
    muc = [e for e in kq["entries"] if e["rel"].endswith("bai.mp4")][0]
    assert muc["action"] == "keep"
    assert "bằng chứng" in muc["reason"]


def test_video_co_bang_chung_va_qua_han_thi_don(tram):
    kq = PM.quet([PM.Goc("tram", tram)], days=14)
    muc = [e for e in kq["entries"] if e["rel"].endswith("bai.mp4")][0]
    assert muc["action"] == "prune"
    assert muc["evidence"]["key"] == "video_id"


def test_bang_chung_KHONG_bo_qua_san_14_ngay(tmp_path):
    """Đã đăng nhưng mới render hôm qua ⇒ vẫn GIỮ. YouTube xử lý chậm và có lúc phải đăng
    lại — chính comment của `sweep_old()` trong `daily_truyen.py` nói vậy."""
    t = tmp_path / "tram"
    _so_dang(t / "kenh-a" / "out" / "moi" / "x.json.published.json", 1)
    _file(t / "kenh-a" / "out" / "moi" / "x.mp4", 1)
    kq = PM.quet([PM.Goc("tram", t)], days=14)
    muc = [e for e in kq["entries"] if e["rel"].endswith("x.mp4")][0]
    assert muc["action"] == "keep" and "hạn" in muc["reason"]


def test_video_policy_age_la_NGOAI_LE_phai_khai_tuong_minh(tmp_path):
    """Lối thoát cho trạm không có sổ nào — nhưng phải GÕ RA, như `--audio-policy age`."""
    t = tmp_path / "tram"
    _file(t / "kenh-a" / "out" / "2026-01-01" / "bai.mp4", 30)
    assert PM.quet([PM.Goc("t", t)], days=14)["entries"][0]["action"] == "keep"
    theo_tuoi = PM.quet([PM.Goc("t", t)], days=14, video_policy="age")
    assert theo_tuoi["entries"][0]["action"] == "prune"


def test_video_policy_keep_khong_bao_gio_don(tram):
    kq = PM.quet([PM.Goc("t", tram)], days=14, video_policy="keep")
    assert not [e for e in kq["entries"] if e["action"] == "prune"]


def test_bang_chung_truyen_khai_bang_co(tmp_path):
    """Sổ của truyện nằm ở trạm nội dung, video nằm ở trạm giọng — hai cây khác nhau, nên
    sổ phải khai bằng `--evidence`, không đoán."""
    t = tmp_path / "truyen-out"
    _file(t / "out" / "PNTT 2441-2446.mp4", 30)
    so = tmp_path / "truyen-state.json"
    so.write_text(json.dumps({"last_publish_ok": True, "history": ["2441-2446@20260813_0500"],
                              "last_video": "x/PNTT 2441-2446.mp4"}), encoding="utf-8")
    chua = PM.quet([PM.Goc("t", t)], days=14)
    assert chua["entries"][0]["action"] == "keep"
    co = PM.quet([PM.Goc("t", t)], days=14, evidence=[so])
    assert co["entries"][0]["action"] == "prune"
    assert co["evidence_sources"][0]["kind"] == "truyen-state"


def test_evidence_khai_sai_la_ma_2(tram, tmp_path):
    la = tmp_path / "la.json"
    la.write_text('{"khong": "phai so"}', encoding="utf-8")
    r = _chay("--root", tram, "--evidence", la, "--dry-run")
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr


# ══ C1 — `--delete` PHẢI để lại kê khai, ghi TRƯỚC khi xoá ══════════════════

def test_delete_luon_ghi_ke_khai(tram, tmp_path):
    """REVIEW-P2 C1 (Chặn). `--move-to` tự ghi manifest, `--delete` thì không ghi gì —
    mà `--delete` mới là chế độ sắp chạy tự động, không người nhìn."""
    ke = tmp_path / "so" / "da-xoa.json"
    r = _chay("--root", tram, "--delete", "--manifest", ke)
    assert r.returncode == PM.SC.OK, r.stderr
    assert ke.is_file(), "xoá mà không để lại dấu vết = không điều tra được"
    d = json.loads(ke.read_text(encoding="utf-8"))
    mot = [e for e in d["entries"] if e["action"] == "prune"][0]
    assert {"path", "bytes", "mtime", "reason", "evidence"} <= set(mot)
    assert mot.get("deleted") is True


def test_delete_khong_khai_manifest_van_co_ke_khai_MAC_DINH(tram, tmp_path):
    """Quên `--manifest` là ca dễ xảy ra nhất khi gắn vào lịch. Không được im lặng bỏ sổ."""
    r = _chay("--root", tram, "--delete")
    assert r.returncode == PM.SC.OK, r.stderr
    ds = list((tram.parent / PM.THU_MUC_SO).glob("*.json"))
    assert len(ds) == 1, f"không thấy kê khai mặc định: {ds}"
    assert json.loads(ds[0].read_text(encoding="utf-8"))["totals"]["prune"]["files"] >= 1


def test_ke_khai_ghi_TRUOC_khi_xoa_byte_dau_tien(tram, tmp_path, monkeypatch):
    """Ghi sổ sau khi xoá thì một lần bị giết giữa chừng là mất CẢ HAI: file lẫn danh sách.
    Mô phỏng bằng cách cho bước thi hành nổ — kê khai vẫn phải nằm trên đĩa."""
    ke = tmp_path / "so.json"

    def no(*a, **k):
        raise RuntimeError("giả vờ bị giết giữa chừng")

    monkeypatch.setattr(PM, "thuc_thi", no)
    with pytest.raises(RuntimeError):
        PM._lam(PM._args_thu(root=[str(tram)], delete=True, manifest=str(ke)))
    assert ke.is_file(), "kê khai phải có mặt TRƯỚC khi đụng byte đầu tiên"
    assert json.loads(ke.read_text(encoding="utf-8"))["status"] == "planned"


def test_ke_khai_khong_ghi_duoc_thi_KHONG_xoa_gi(tram, tmp_path):
    """Không có chỗ ghi sổ ⇒ mã 2 và không đụng file nào — chứ không phải 'cứ xoá đi'."""
    chan = tmp_path / "chan"
    chan.write_text("toi la FILE, khong phai thu muc", encoding="utf-8")
    con = tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp4"
    r = _chay("--root", tram, "--delete", "--manifest", chan / "so.json")
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr
    assert con.is_file(), "không ghi được sổ mà vẫn xoá = đúng thứ C1 cấm"


# ══ N3 — cầu dao: một lượt tự động không được xoá cả kho ════════════════════

def test_cau_dao_so_file(tram, tmp_path):
    con = tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp4"
    r = _chay("--root", tram, "--delete", "--max-files", 0)
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr
    assert con.is_file(), "vượt cầu dao mà vẫn xoá thì cầu dao chỉ là trang trí"
    assert "cầu dao" in (r.stderr or "").lower() or "max-files" in (r.stderr or "")


def test_cau_dao_dung_luong(tram):
    con = tram / "kenh-a" / "out" / "2026-01-01" / "bai.mp4"
    r = _chay("--root", tram, "--delete", "--max-bytes", 1)
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr
    assert con.is_file()


def test_cau_dao_KHONG_chan_dry_run(tram):
    """Chỉ in thì không có gì để chặn — chặn luôn cả bản kế hoạch là bịt mắt người dùng."""
    assert _chay("--root", tram, "--dry-run", "--max-files", 0).returncode == PM.SC.OK


def test_days_0_khi_XOA_phai_go_them_co_rieng(tram):
    """`--days 0` xoá cả file vừa render xong. Vẫn cho phép (Đức muốn 'dọn ngay' được),
    nhưng không được là một ký tự gõ nhầm trong dòng lệnh của bộ lập lịch."""
    con = tram / "kenh-a" / "out" / "moi" / "moi.mp4"
    r = _chay("--root", tram, "--delete", "--days", 0)
    assert r.returncode == PM.SC.CONTRACT_ERROR, r.stderr
    assert con.is_file()
    assert _chay("--root", tram, "--dry-run", "--days", 0).returncode == PM.SC.OK


# ══ N1 — junction/symlink thư mục: không đi xuyên qua ═══════════════════════

def _lien_ket_thu_muc(lien: Path, dich: Path) -> bool:
    """Junction trên Windows (`is_symlink()` trả False cho nó), symlink trên POSIX."""
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(lien), str(dich)],
                           capture_output=True, text=True)
        return r.returncode == 0
    try:
        os.symlink(dich, lien, target_is_directory=True)
        return True
    except OSError:
        return False


def test_khong_di_xuyen_junction_ra_ngoai_tram(tram, tmp_path):
    """REVIEW-P2 N1, tái lập được: `mklink /J <trạm>\\lien-ket <ngoài>` rồi quét.

    `Path.is_symlink()` trả **False** cho junction Windows và `rglob` đi xuyên qua, nên
    file NGOÀI trạm lọt vào kế hoạch — với `--delete` là xoá ở vị trí thật ngoài trạm."""
    ngoai = tmp_path / "ngoai-tram"
    _so_dang(ngoai / "a.json.published.json")
    _file(ngoai / "quy.mp4", 30)
    if not _lien_ket_thu_muc(tram / "lien-ket", ngoai):
        pytest.skip("máy này không tạo được junction/symlink thư mục")
    kq = PM.quet([PM.Goc("tram", tram)], days=14)
    assert not [e for e in kq["entries"] if "quy.mp4" in e["rel"]], \
        "đi xuyên liên kết = lập kế hoạch xoá file ngoài trạm"
    assert (ngoai / "quy.mp4").is_file()
