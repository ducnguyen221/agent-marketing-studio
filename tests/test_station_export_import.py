# -*- coding: utf-8 -*-
"""`station.py export|import` — gói bàn giao một trạm sang máy khác.

Khác `studio.py backup` có chủ đích, và hai lệnh KHÔNG được gộp:

    backup  ảnh chụp cho chính mình — zip cả trạm, không hỏi cái gì đáng mang.
    export  gói bàn giao — **danh sách khai rõ** (kế hoạch §4), manifest + sha256, và
            một bên nhận (`import`) đếm lại xem thiếu gì.

Vì sao phải khai rõ thay vì "zip tất, trừ vài thứ": trạm thật nặng ~930 MB mà 906 MB là
mp4/ảnh trong `out/` — thứ dựng lại được. Cái **không** dựng lại được là mấy chục KB
JSON trạng thái: mất `covered-repos.json` là làm lại repo đã làm, mất `fb-state.json` là
đăng trùng Facebook, mất `*.published.json` là upload YouTube trùng. Một danh sách loại-trừ
sẽ im lặng bỏ sót đúng những file đó khi cây thư mục mọc thêm nhánh mới; danh sách khai rõ
thì bỏ sót là **đỏ ở đây**.

Ba nhóm test:
  1. `chon()` — ma trận giữ/loại từng đường dẫn (phần dễ trôi nhất khi ai đó thêm luật).
  2. `export` — manifest, sha256, từ chối secret, `--with-git`, `--dry-run`.
  3. `import` — sha khớp, đổi đường máy cũ, KHÔNG đè, báo thiếu file §4.
"""
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import station as STN  # noqa: E402
import station_manifest as SM  # noqa: E402
import studio_contract as SC  # noqa: E402

BIEN_HOP_DONG = ("MARKETING_STUDIO_DATA", "MARKETING_STUDIO_HOME", "VOICE_STATION",
                 "OMNIVOICE_DIR", "VIDEO_STATION", "VIDEO_ROOT")


@pytest.fixture(autouse=True)
def _moi_truong_sach(monkeypatch):
    """Mọi test tự dựng trạm trong thư mục tạm và truyền `--station` tường minh.

    Gỡ sạch biến hợp đồng: máy đang chạy lịch thật CÓ đặt chúng, và một `doctor` trong
    test mà đi hỏi trạm giọng thật là test đo máy chứ không đo code.
    """
    for b in BIEN_HOP_DONG:
        monkeypatch.delenv(b, raising=False)


def _ghi(p: Path, noi_dung="x\n", nhi_phan=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if nhi_phan:
        p.write_bytes(noi_dung if isinstance(noi_dung, bytes) else noi_dung.encode("utf-8"))
    else:
        p.write_text(noi_dung, encoding="utf-8", newline="\n")
    return p


CHANNELS_MD = """---
schema: channels/1
updated: '2026-09-01'
channels:
- id: kenh-a
  label: Kenh A
  path: ./kenh-a
  status: active
  note: ''
---

# So kenh
"""

# `voice_profile` là cách một kênh nói "tôi cần trạm giọng" ⇒ `doctor` trên máy vừa import
# sẽ ĐỎ mã 3. Đúng thực tế của một máy mới, và là thứ một test dưới đây cần đo.
CHANNEL_YML = """schema: channel/1
id: kenh-a
label: Kenh A
voice_profile: giong-a
brand:
  site_name: Vi Du
  author: Nguoi Viet
  site_base: https://vidu.vn
"""

# Ma trận giữ/loại. Mỗi dòng là một đường thật đã thấy trong một trạm đang chạy.
CAY = [
    # (đường tương đối, có trong gói MẶC ĐỊNH?)
    ("CHANNELS.md", True),
    ("AUTHOR.md", True),
    ("Auto Task.xlsx", True),
    ("index.html", False),
    ("_backup/cu.json", False),
    ("_migrated-20260907/cu.md", False),
    ("_task-backup/cu.md", False),
    (".tmp.driveupload/rac.bin", False),
    ("kenh-a/channel.yml", True),
    ("kenh-a/CAMPAIGNS.md", True),
    ("kenh-a/brand.md", True),
    ("kenh-a/continuity.json", True),
    ("kenh-a/build-index.ps1", True),
    ("kenh-a/assets/logo.png", True),
    ("kenh-a/assets/nen.mp4", True),
    ("kenh-a/__pycache__/x.pyc", False),
    ("kenh-a/_vtitles/tieu-de.png", False),
    ("kenh-a/cd-1/campaign.md", True),
    ("kenh-a/cd-1/prompt.txt", True),
    ("kenh-a/cd-1/run.ps1", True),
    ("kenh-a/cd-1/covered-repos.json", True),
    ("kenh-a/cd-1/campaign.html", False),
    ("kenh-a/cd-1/cd-1.xlsx", False),
    ("kenh-a/cd-1/out/2026-09-01/2026-09-01-top.json", True),
    ("kenh-a/cd-1/out/2026-09-01/2026-09-01-top.json.published.json", True),
    ("kenh-a/cd-1/out/2026-09-01/2026-09-01-top.mp4", False),
    ("kenh-a/cd-1/out/2026-09-01/thumb.jpg", False),
    ("kenh-a/cd-1/out/2026-09-01/xlsx-row.json", False),
    ("kenh-a/cd-1/out/2026-09-01/desc-top.txt", False),
    ("kenh-a/cd-1/logs/tg-approve.json", False),        # chỉ với --include-logs-state
    ("kenh-a/cd-1/logs/feedback.json", False),
    ("kenh-a/cd-1/logs/events.jsonl", False),
    ("kenh-a/cd-1/logs/jobs/pending/j1.json", False),
    ("kenh-a/cd-1/logs/jobs/running/j2.json", False),
    ("kenh-a/cd-1/logs/jobs/running/feedback.json", False),
    ("kenh-a/cd-1/logs/config-2026-09-01.json", False),
    ("kenh-a/cd-1/logs/tg-poller.lock", False),
    ("kenh-a/cd-1/logs/tg-poll-alive.json", False),
    ("kenh-a/cd-1/logs/chay.log", False),
    ("kenh-a/cd-1/BAI-001/meta.json", True),
    ("kenh-a/cd-1/BAI-001/publish.json", True),
    ("kenh-a/cd-1/BAI-001/gates.json", True),
    ("kenh-a/cd-1/BAI-001/.write-count.json", True),
    ("kenh-a/cd-1/BAI-001/content.md", True),
    ("kenh-a/cd-1/BAI-001/research.md", True),
    ("kenh-a/cd-1/BAI-001/gates.json.bak-20260912", False),
    ("kenh-a/cd-1/BAI-001/facebook/fb-state.json", True),
    ("kenh-a/cd-1/BAI-001/facebook/infographic.meta.json", True),
    ("kenh-a/cd-1/BAI-001/facebook/infographic.png", True),
    ("kenh-a/truyen/truyen-state.json", True),
    ("kenh-a/truyen/playlist-youtube.json", True),
    ("kenh-a/truyen/truyen-out/daily-logs/_heal_state.json", True),
    ("kenh-a/truyen/truyen-out/slug__giong/cache/a.wav", False),
    ("kenh-a/truyen/truyen-out/slug__giong/chuong-1.mp4", False),
]

CHI_KHI_LOGS_STATE = {
    "kenh-a/cd-1/logs/tg-approve.json",
    "kenh-a/cd-1/logs/feedback.json",
    "kenh-a/cd-1/logs/events.jsonl",
    "kenh-a/cd-1/logs/jobs/pending/j1.json",
}


@pytest.fixture
def tram(tmp_path):
    st = tmp_path / "tram"
    st.mkdir()
    _ghi(st / "CHANNELS.md", CHANNELS_MD)
    for rel, _ in CAY:
        if rel == "CHANNELS.md":
            continue
        _ghi(st / rel, f"noi dung cua {rel}\n")
    _ghi(st / "kenh-a" / "channel.yml", CHANNEL_YML)
    return st


def _rel(files):
    return {rel for _, rel in files}


@pytest.mark.parametrize("duong,trong_goi", CAY, ids=[c[0] for c in CAY])
def test_chon_dung_giu_dung_loai(tram, duong, trong_goi):
    co = _rel(SM.chon(tram))
    assert (duong in co) is trong_goi, (
        f"{duong}: {'phải có' if trong_goi else 'KHÔNG được có'} trong gói mặc định")


@pytest.mark.parametrize("duong", sorted(CHI_KHI_LOGS_STATE))
def test_logs_trang_thai_chi_vao_goi_khi_xin_ro(tram, duong):
    assert duong not in _rel(SM.chon(tram))
    assert duong in _rel(SM.chon(tram, logs_state=True))


@pytest.mark.parametrize("duong", ["kenh-a/cd-1/logs/jobs/running/j2.json",
                                   "kenh-a/cd-1/logs/jobs/running/feedback.json"])
def test_logs_jobs_running_KHONG_vao_goi_ke_ca_khi_xin_logs(tram, duong):
    """`jobs/running/` là việc của máy CŨ đang làm dở. Mang sang máy mới là hồi sinh một
    lượt chạy không có tiến trình nào đứng sau nó.

    Ca thứ hai là ca thật sự khó: `feedback.json` NẰM TRONG bộ tên được phép mang. Luật
    chọn phải neo theo đường tính từ `logs/`, không theo tên file — nếu không, một cái tên
    trùng ở nhầm chỗ là lọt.
    """
    assert duong not in _rel(SM.chon(tram, logs_state=True))


def test_git_chi_vao_goi_khi_xin_with_git(tram):
    _ghi(tram / ".git" / "HEAD", "ref: refs/heads/main\n")
    _ghi(tram / ".git" / "objects" / "ab" / "cdef", "x")
    _ghi(tram / ".git" / "index.lock", "x")
    assert not [r for r in _rel(SM.chon(tram)) if r.startswith(".git/")]
    co = _rel(SM.chon(tram, with_git=True))
    assert ".git/HEAD" in co and ".git/objects/ab/cdef" in co
    assert ".git/index.lock" not in co, "index.lock là khoá của máy cũ, không mang đi"


# ── từ chối secret ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ten", ["yt_token.json", "client_secret_123.json",
                                 "credentials.json", ".env", "khoa.pem", "khoa.key"])
def test_export_TU_CHOI_khi_trong_goi_co_file_giong_secret(tram, tmp_path, ten):
    _ghi(tram / "kenh-a" / ten, "{}")
    out = tmp_path / "goi.zip"
    with pytest.raises(SC.ContractError) as e:
        STN.export_station(tram, out)
    assert ten in str(e.value)
    assert not out.exists(), "từ chối mà vẫn ghi zip = đã rò trước khi kịp từ chối"


def test_tu_choi_chi_xet_thu_nhung_gi_THUC_SU_vao_goi(tram, tmp_path):
    """Một token nằm trong `_backup/` không được phép chặn export vĩnh viễn: nó đã bị loại
    khỏi gói rồi. Từ chối theo cả cây là biến một thư mục rác thành cái khoá cửa."""
    _ghi(tram / "_backup" / "yt_token.json", "{}")
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    assert out.exists()


def test_env_example_KHONG_bi_coi_la_secret():
    assert not SM.giong_secret(".env.example")
    assert SM.giong_secret(".env")


# ── export: manifest + sha256 ─────────────────────────────────────────────────────────

def _doc_manifest(z: Path) -> dict:
    with zipfile.ZipFile(z) as f:
        return json.loads(f.read(SM.MANIFEST).decode("utf-8"))


def test_export_ra_zip_co_manifest_va_sha256_khop(tram, tmp_path):
    out = tmp_path / "goi.zip"
    kq = STN.export_station(tram, out, logs_state=True)
    mf = _doc_manifest(out)
    assert mf["kind"] == SM.KIND and mf["format"] == SM.FORMAT
    assert mf["source_home"] == str(Path.home())
    assert len(mf["files"]) == kq["count"] > 20
    with zipfile.ZipFile(out) as z:
        ten_trong_zip = set(z.namelist()) - {SM.MANIFEST}
        assert ten_trong_zip == {m["path"] for m in mf["files"]}
        for m in mf["files"]:
            assert SM.sha256_bytes(z.read(m["path"])) == m["sha256"], m["path"]
            assert z.getinfo(m["path"]).file_size == m["size"]


def test_thu_muc_ngay_RONG_trong_out_van_di_theo_goi(tram, tmp_path):
    """Một lượt chạy hỏng để lại `out/<ngày>/` chỉ có media. Lọc theo tên thì thư mục ngày
    biến mất, và `check_tree.py` ở máy mới báo ĐỎ "bảng Content có out/<ngày> nhưng thư
    mục không tồn tại" — một lỗi GIẢ, ngay ở lần chạy đầu trên máy mới. Gặp thật ở gói
    bàn giao đầu tiên (hai ngày, hai kênh)."""
    ngay = "kenh-a/cd-1/out/2026-09-04"
    _ghi(tram / ngay / "clips" / "a.mp4", "x")
    out = tmp_path / "goi.zip"
    kq = STN.export_station(tram, out)
    assert ngay in kq["dirs"]
    assert not any(m["path"].startswith(ngay + "/") for m in kq["files"])
    dich = tmp_path / "moi"
    STN.import_station(out, dich)
    assert (dich / ngay).is_dir(), "thư mục ngày rỗng không được dựng lại ở máy mới"


def test_export_dry_run_KHONG_ghi_gi(tram, tmp_path):
    out = tmp_path / "goi.zip"
    kq = STN.export_station(tram, out, dry_run=True)
    assert not out.exists()
    assert kq["dry_run"] is True and kq["count"] > 0 and kq["bytes"] > 0
    assert any(m["path"] == "kenh-a/cd-1/covered-repos.json" for m in kq["files"])


def test_export_tram_khong_co_thi_MA_3(tmp_path):
    with pytest.raises(SC.StationMissing):
        STN.export_station(tmp_path / "khong-co", tmp_path / "a.zip")


def test_export_TU_CHOI_ghi_zip_vao_trong_chinh_tram(tram):
    """Zip nằm trong trạm thì lần export sau sẽ gói chính nó — và kích thước nhân đôi mỗi
    lượt cho tới khi hết đĩa."""
    with pytest.raises(SC.ContractError):
        STN.export_station(tram, tram / "goi.zip")


def test_manifest_dem_du_file_trang_thai_theo_ke_hoach(tram, tmp_path):
    kq = STN.export_station(tram, tmp_path / "goi.zip")
    ke = _doc_manifest(tmp_path / "goi.zip")["state_files"]
    assert ke["covered-repos.json"] == 1
    assert ke["truyen-state.json"] == 1
    assert ke["continuity.json"] == 1
    assert ke["fb-state.json"] == 1
    assert ke["*.published.json"] == 1
    assert kq["state_files"] == ke


# ── import ────────────────────────────────────────────────────────────────────────────

def test_import_vao_thu_muc_trong_giu_nguyen_sha(tram, tmp_path):
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out, logs_state=True)
    dich = tmp_path / "moi"
    kq = STN.import_station(out, dich)
    assert kq["count"] == len(_doc_manifest(out)["files"])
    for rel in ("kenh-a/cd-1/covered-repos.json", "kenh-a/truyen/truyen-state.json",
                "kenh-a/cd-1/BAI-001/facebook/fb-state.json"):
        assert SM.sha256(dich / rel) == SM.sha256(tram / rel), rel


def test_import_KHONG_DE_file_da_co(tram, tmp_path):
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    dich = tmp_path / "moi"
    cu = _ghi(dich / "kenh-a" / "continuity.json", "TRANG THAI CUA MAY DICH\n")
    with pytest.raises(SC.ContractError) as e:
        STN.import_station(out, dich)
    assert "continuity.json" in str(e.value)
    assert cu.read_text(encoding="utf-8") == "TRANG THAI CUA MAY DICH\n", "đã đè mất"
    assert not (dich / "CHANNELS.md").exists(), "từ chối mà vẫn giải nén một phần"


def test_import_bao_thieu_file_trang_thai(tram, tmp_path):
    (tram / "kenh-a" / "cd-1" / "covered-repos.json").unlink()
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    kq = STN.import_station(out, tmp_path / "moi")
    assert any("covered-repos.json" in m for m in kq["missing"]), kq["missing"]


def test_import_chay_check_tree_va_doctor(tram, tmp_path):
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    kq = STN.import_station(out, tmp_path / "moi")
    assert "check_tree" in kq and "doctor" in kq
    assert kq["doctor"]["station"] == str((tmp_path / "moi").resolve())


def test_import_KHONG_lay_ma_thoat_cua_doctor_lam_ma_cua_minh(tram, tmp_path):
    """Máy mới gần như chắc chắn chưa cài xong trạm giọng — đó là lý do người ta đang
    import. Để `doctor` quyết mã thoát của `import` là biến bước-đầu-tiên thành thất bại."""
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    kq = STN.import_station(out, tmp_path / "moi")
    assert kq["doctor"]["code"] != 0
    assert STN.main(["import", str(out), "--station", str(tmp_path / "moi2")]) == 0


# ── đổi đường của máy cũ ──────────────────────────────────────────────────────────────

NHA_CU = str(Path.home())


@pytest.mark.parametrize("rel,truoc,sau", [
    ("kenh-a/channel.yml", "root: " + NHA_CU + "/.marketing\n", "root: ~/.marketing\n"),
    ("kenh-a/cd-1/BAI-001/meta.json",
     '{"p": "' + NHA_CU.replace("\\", "\\\\") + '\\\\x"}',
     '{"p": "~\\\\x"}'),
    ("kenh-a/cd-1/campaign.md", "xem " + NHA_CU + " nhe\n", "xem ~ nhe\n"),
])
def test_import_doi_duong_may_cu_thanh_dau_nga(tram, tmp_path, rel, truoc, sau):
    _ghi(tram / rel, truoc)
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    dich = tmp_path / "moi"
    kq = STN.import_station(out, dich)
    assert (dich / rel).read_text(encoding="utf-8") == sau
    assert rel in kq["rewritten"]


def test_import_KHONG_doi_duong_trong_out(tram, tmp_path):
    """`out/` là **nhật ký của cái đã đăng**. Sửa đường trong đó là sửa lịch sử, và
    `*.published.json` là chốt chống đăng trùng — nó phải giống hệt bản máy cũ."""
    rel = "kenh-a/cd-1/out/2026-09-01/2026-09-01-top.json.published.json"
    _ghi(tram / rel, '{"p": "' + NHA_CU.replace("\\", "/") + '/x"}')
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    dich = tmp_path / "moi"
    STN.import_station(out, dich)
    assert SM.sha256(dich / rel) == SM.sha256(tram / rel)


def test_import_KHONG_doi_duong_trong_file_khong_phai_van_ban(tram, tmp_path):
    rel = "kenh-a/assets/logo.png"
    _ghi(tram / rel, (NHA_CU + "/x").encode("utf-8"), nhi_phan=True)
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    dich = tmp_path / "moi"
    STN.import_station(out, dich)
    assert SM.sha256(dich / rel) == SM.sha256(tram / rel)


def test_import_giu_BOM_va_CRLF_khi_doi_duong(tram, tmp_path):
    """`.ps1` mất BOM là PowerShell 5.1 parse hỏng và task chạy lịch **im lặng** không
    đăng gì (bài học đã trả giá). Nên việc đổi đường phải làm trên BYTE, không đi qua
    một vòng decode/encode nào."""
    rel = "kenh-a/cd-1/run.ps1"
    goc = "\ufeff$station = '" + NHA_CU + "\\.marketing'\r\nWrite-Host ok\r\n"
    _ghi(tram / rel, goc)
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    dich = tmp_path / "moi"
    STN.import_station(out, dich)
    b = (dich / rel).read_bytes()
    assert b[:3] == b"\xef\xbb\xbf", "mất BOM"
    assert b.count(b"\r\n") == 2, "đổi CRLF"
    assert b"~\\.marketing" in b


def test_import_vao_duong_qua_dai_thi_DUNG_TRUOC_khi_ghi(tram, tmp_path):
    """Đích quá sâu -> vượt MAX_PATH của Windows.

    Gặp thật khi chạy gói bàn giao đầu tiên: `export` xong gọn, `import` chết GIỮA CHỪNG
    ở một thư mục bài có slug dài. Điều tệ nhất là nó chỉ nổ ở BÊN NHẬN — đúng lúc người
    ta đang đổi máy. Nay nó dừng TRƯỚC khi ghi byte nào và nói phải làm gì.

    Trên POSIX giới hạn này không tồn tại, nên ở đó ca thử phải CHẠY ĐƯỢC — cùng một
    test đo hai hành vi đúng của hai hệ điều hành.
    """
    out = tmp_path / "goi.zip"
    rel_dai = "kenh-a/cd-1/" + "B" * 90 + "/meta.json"
    _ghi(tram / rel_dai, "{}")
    STN.export_station(tram, out)
    dich = tmp_path / ("s" * 80) / ("u" * 80)
    assert len(str(dich / rel_dai)) > STN.GIOI_HAN_DUONG, "ca thử chưa đủ dài để đo được gì"
    if os.name == "nt":
        with pytest.raises(SC.ContractError) as e:
            STN.import_station(out, dich)
        assert str(STN.GIOI_HAN_DUONG) in str(e.value)
        assert not dich.exists(), "từ chối mà vẫn tạo thư mục đích"
    else:
        STN.import_station(out, dich)
        assert SM.sha256(dich / rel_dai) == SM.sha256(tram / rel_dai)


def test_thu_muc_dung_tam_KHONG_dai_hon_ten_dich(tram, tmp_path):
    """Thư mục dựng tạm cộng thêm vào MỌI đường bên trong. Một cái tên dựng tạm dài hơn
    tên đích là tự làm hỏng gói lẽ ra vừa đủ chỗ — bug đã gặp, tên cũ là
    `.<tên đích>.import-<pid>`."""
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    dich = tmp_path / "m"
    ten = []
    that = STN._dat_vao_cho

    def rinh(tam, st):
        ten.append(Path(str(tam)).name)
        return that(tam, st)

    STN._dat_vao_cho = rinh
    try:
        STN.import_station(out, dich)
    finally:
        STN._dat_vao_cho = that
    assert ten and len(ten[0]) <= len(dich.name) + 12, f"tên dựng tạm quá dài: {ten[0]}"


def test_import_TU_CHOI_zip_co_duong_thoat_ra_ngoai(tmp_path):
    """Zip-slip: một entry `../` ghi đè file ngoài thư mục đích. Gói này đi qua USB và
    email giữa hai máy — coi nó là dữ liệu tin cậy là sai."""
    z = tmp_path / "doc.zip"
    # sha256 phải ĐÚNG: nếu để sai, lệnh dừng vì "gói hỏng" và test xanh mà chưa hề chạm
    # tới luật zip-slip — đúng kiểu test xanh không đo gì.
    noi_dung = b"x"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr(SM.MANIFEST, json.dumps({
            "kind": SM.KIND, "format": SM.FORMAT, "source_home": "/nha",
            "files": [{"path": "../thoat.txt", "size": len(noi_dung),
                       "sha256": SM.sha256_bytes(noi_dung)}], "state_files": {}}))
        f.writestr("../thoat.txt", noi_dung)
    with pytest.raises(SC.ContractError):
        STN.import_station(z, tmp_path / "moi")
    assert not (tmp_path / "thoat.txt").exists()


def test_import_TU_CHOI_zip_khong_phai_goi_cua_lenh_nay(tmp_path):
    z = tmp_path / "la.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("a.txt", "x")
    with pytest.raises(SC.ContractError) as e:
        STN.import_station(z, tmp_path / "moi")
    assert SM.MANIFEST in str(e.value)


def test_import_TU_CHOI_khi_sha256_khong_khop(tram, tmp_path):
    """Gói hỏng dọc đường (USB, mạng) mà vẫn giải nén là máy mới chạy bằng dữ liệu sai —
    tệ hơn hẳn việc dừng lại và chép gói lần nữa."""
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out)
    xau = tmp_path / "xau.zip"
    with zipfile.ZipFile(out) as a, zipfile.ZipFile(xau, "w") as b:
        for i in a.infolist():
            data = a.read(i.filename)
            if i.filename == "kenh-a/continuity.json":
                data = b"DA BI SUA\n"
            b.writestr(i.filename, data)
    with pytest.raises(SC.ContractError) as e:
        STN.import_station(xau, tmp_path / "moi")
    assert "continuity.json" in str(e.value)


# ── vòng tròn export → import ─────────────────────────────────────────────────────────

def test_vong_tron_export_import_giu_du_moi_file(tram, tmp_path):
    out = tmp_path / "goi.zip"
    kq_e = STN.export_station(tram, out, logs_state=True)
    dich = tmp_path / "moi"
    kq_i = STN.import_station(out, dich)
    assert kq_i["count"] == kq_e["count"]
    assert kq_i["state_files"] == kq_e["state_files"]
    co = {str(p.relative_to(dich)).replace(os.sep, "/") for p in dich.rglob("*") if p.is_file()}
    assert co == {m["path"] for m in kq_e["files"]}


def test_vong_tron_voi_git_chay_update_index(tram, tmp_path):
    """`.git` của máy cũ mang stat cache của HĐH cũ: mọi file trông như "đã sửa" cho tới
    khi `git update-index --refresh` chạy. Không chạy thì việc đầu tiên người dùng thấy
    trên máy mới là một `git status` đỏ rực và họ sẽ `checkout -- .` đè mất trạng thái."""
    subprocess.run(["git", "init", "-q", str(tram)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tram), "add", "CHANNELS.md"], check=True, capture_output=True)
    out = tmp_path / "goi.zip"
    STN.export_station(tram, out, with_git=True)
    dich = tmp_path / "moi"
    kq = STN.import_station(out, dich)
    assert (dich / ".git").is_dir()
    assert kq["git_refreshed"] is True


# ── CLI ───────────────────────────────────────────────────────────────────────────────

def test_CLI_export_import_tra_mot_dong_JSON_cuoi_va_ma_0(tram, tmp_path, capsys):
    out = tmp_path / "goi.zip"
    assert STN.main(["export", "--station", str(tram), "--out", str(out), "--json"]) == 0
    d = SC.last_json_line(capsys.readouterr().out)
    assert d["ok"] is True and d["out"] == str(out)
    assert STN.main(["import", str(out), "--station", str(tmp_path / "moi"), "--json"]) == 0
    d = SC.last_json_line(capsys.readouterr().out)
    assert d["ok"] is True and d["count"] > 0


def test_CLI_tram_thieu_tra_ma_3_va_JSON_loi(tmp_path, capsys):
    ma = STN.main(["export", "--station", str(tmp_path / "khong-co"),
                   "--out", str(tmp_path / "a.zip"), "--json"])
    assert ma == SC.STATION_MISSING
    d = SC.last_json_line(capsys.readouterr().out)
    assert d["ok"] is False and d["code"] == SC.STATION_MISSING


def test_CLI_chay_that_bang_tien_trinh_con(tram, tmp_path):
    """Gọi qua `python station.py` chứ không import: đó là cách người dùng và runbook gọi,
    và nó là chỗ duy nhất đo được `sys.path`, encoding stdout, mã thoát thật."""
    out = tmp_path / "goi.zip"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "station.py"),
                        "export", "--station", str(tram), "--out", str(out),
                        "--with-git", "--include-logs-state", "--json"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert SC.last_json_line(r.stdout)["ok"] is True
    assert out.exists()


# ── cổng-của-cổng ─────────────────────────────────────────────────────────────────────

def test_ma_tran_CAY_dung_dung_cay_that(tram):
    """Mỗi đường trong `CAY` phải tồn tại thật trong trạm mẫu — nếu không, một dòng gõ sai
    sẽ mãi mãi "đạt" ở vế `KHÔNG được có` mà chẳng đo gì."""
    thieu = [rel for rel, _ in CAY if not (tram / rel).is_file()]
    assert not thieu, thieu


def test_moi_file_trang_thai_cua_ke_hoach_deu_co_luat(tram):
    """Danh sách §4 "CÓ" là hợp đồng với kế hoạch. Thêm một loại file trạng thái mới mà
    quên viết luật chọn cho nó thì đây là chỗ đỏ."""
    co = _rel(SM.chon(tram, logs_state=True))
    for rel in ("kenh-a/cd-1/covered-repos.json", "kenh-a/truyen/truyen-state.json",
                "kenh-a/truyen/playlist-youtube.json", "kenh-a/continuity.json",
                "kenh-a/cd-1/campaign.md", "kenh-a/CAMPAIGNS.md",
                "kenh-a/cd-1/BAI-001/publish.json", "kenh-a/cd-1/BAI-001/meta.json",
                "kenh-a/cd-1/BAI-001/gates.json", "kenh-a/cd-1/BAI-001/.write-count.json",
                "kenh-a/cd-1/BAI-001/facebook/infographic.meta.json",
                "kenh-a/cd-1/BAI-001/facebook/fb-state.json",
                "kenh-a/cd-1/out/2026-09-01/2026-09-01-top.json.published.json",
                "kenh-a/cd-1/logs/tg-approve.json", "kenh-a/cd-1/logs/feedback.json",
                "kenh-a/cd-1/logs/events.jsonl", "kenh-a/cd-1/logs/jobs/pending/j1.json",
                "kenh-a/truyen/truyen-out/daily-logs/_heal_state.json",
                "Auto Task.xlsx"):
        assert rel in co, f"file trạng thái §4 bị bỏ khỏi gói: {rel}"
