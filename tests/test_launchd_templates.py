# -*- coding: utf-8 -*-
"""Cổng canh mẫu launchd và bộ cài lịch macOS.

Vì sao cần cổng riêng: plist là XML, và một plist sai cú pháp **không báo lúc ghi** — nó
báo lúc `launchctl bootstrap`, trên máy Mac, lúc nửa đêm, bằng một dòng lỗi cụt. Cây test
này chạy trên MỌI máy (kể cả Windows CI) và bắt gần hết lớp lỗi đó trước khi file rời repo:

· mẫu phải là XML plist hợp lệ ngay ở dạng CHƯA điền;
· điền xong không còn chỗ trống nào — không bao giờ ghi ra một plist dở;
· `--dry-run` **không** gọi `launchctl` và **không** ghi file;
· ba job nguy hiểm không nằm trong bộ mặc định;
· lịch khớp đúng bảng đã chốt (truyện Hour 0 — đây là quyết định của người, không phải
  của code, nên nó phải có một test giữ lại).
"""
import json
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAU = ROOT / "templates" / "launchd"

sys.path.insert(0, str(ROOT / "scripts" / "runners"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import install_launchd as IL  # noqa: E402
import studio_contract as SC  # noqa: E402

LABELS = sorted(p.stem for p in MAU.glob("*.plist"))

# Duong nha macOS GIA. Ghep tu manh, khong viet literal: `test_no_identity_leak` cam
# tuyet doi moi duong home trong cay git-tracked (Windows, Linux VA macOS) — mot du lieu
# thu viet literal la cong do vi chinh no, va roi ai do se go luat thay vi sua du lieu.
_NHA = "/" + "Users" + "/nguoi-dung"

GIA = {
    "__HOME__": _NHA,
    "__REPO__": _NHA + "/Code/agent-marketing-studio",
    "__STATION__": _NHA + "/noi-dung",
    "__PY__": _NHA + "/Code/agent-marketing-studio/.venv/bin/python",
    "__VOICE_STATION__": _NHA + "/tram-giong",
    "__VIDEO_STATION__": _NHA + "/tram-video",
    "__OMNIVOICE_PY__": _NHA + "/tram-giong/omnivoice/.venv/bin/python",
    "__CHANNEL__": "kenh-mau",
    "__CAMPAIGN__": "chien-dich-mau",
    "__RUNNER__": "run.ps1",
}

# Lịch đã chốt. Con số ở đây là QUYẾT ĐỊNH, không phải hệ quả của code — đổi giờ chạy mà
# không đổi bảng này thì test đỏ, và đó đúng là lúc phải có người nhìn.
LICH = {
    "studio.marketing.daily-news-a": {"Hour": 18, "Minute": 0},
    "studio.marketing.daily-news-b": {"Hour": 19, "Minute": 0},
    "studio.marketing.weekly-news-a": {"Weekday": 5, "Hour": 21, "Minute": 0},
    "studio.marketing.weekly-news-b": {"Weekday": 6, "Hour": 21, "Minute": 0},
    "studio.marketing.weekly-repo": {"Weekday": 0, "Hour": 20, "Minute": 0},
    "studio.marketing.daily-story": {"Hour": 0, "Minute": 0},
}

# ══ HAI PIPELINE, HAI CẤU HÌNH — bảng quyết định, không phải hệ quả của code ══
#
# Tin và truyện chạy cùng một engine giọng nhưng KHÔNG dùng chung cấu hình:
#
#   TIN        lượt 4–12 phút (bản tuần ~41 phút) trong cửa sổ 18:00–21:00 ⇒ thừa thời
#              gian, đổi tốc độ lấy độ chính xác: `float32`. Không đi nhánh fp16 nên
#              KHÔNG khai `HF_DEACTIVATE_ASYNC_LOAD` — vụ nổ mà biến đó vá chỉ xảy ra
#              lúc nạp trọng số fp16 trên MPS.
#   TRUYỆN     5 h 47 chỉ riêng TTS ⇒ thời gian mới là thứ khan hiếm: `float16`, và
#              fp16 trên MPS thì `HF_DEACTIVATE_ASYNC_LOAD=1` là BẮT BUỘC.
#   worker /   không chạy TTS ⇒ không khai cái nào. Một con số dtype thừa ở đây là mầm
#   poller     cho lần chép nhầm sang job có giọng.
#
# Vì sao phải có cổng: gộp lại thành MỘT cấu hình chung là hỏng đúng một bên mà không
# ai thấy — tin chạy fp16 thì đọc sai số, truyện chạy fp32 thì vượt trần giờ và bị giết
# sau khi đã chạy 6 tiếng. Cả hai đều báo ✅ cho tới khi có người nghe lại.

TIN = ["studio.marketing.daily-news-a", "studio.marketing.daily-news-b",
       "studio.marketing.weekly-news-a", "studio.marketing.weekly-news-b",
       "studio.marketing.weekly-repo"]
TRUYEN = ["studio.marketing.daily-story"]
KHONG_TTS = ["studio.marketing.worker", "studio.marketing.approve-poller"]

# label -> (giá trị OMNIVOICE_DTYPE hoặc None nếu KHÔNG được khai, có HF_DEACTIVATE_ASYNC_LOAD?)
GIONG = {**{l: ("float32", False) for l in TIN},
         **{l: ("float16", True) for l in TRUYEN},
         **{l: (None, False) for l in KHONG_TTS}}

# Trần giờ của wrapper. launchd không có `ExecutionTimeLimit`, nên con số này LÀ cái trần.
# Truyện 30600 s (8 h 30): lượt đo ~6 h 05 trên máy RẢNH, lượt thật còn crawl + dựng video
# chen vào. Trần cũ 21600 (6 h) giết lượt đúng lúc đọc xong mà chưa kịp dựng video.
TRAN_GIO = {
    "studio.marketing.daily-news-a": 7200,
    "studio.marketing.daily-news-b": 7200,
    "studio.marketing.weekly-news-a": 10800,
    "studio.marketing.weekly-news-b": 10800,
    "studio.marketing.weekly-repo": 10800,
    "studio.marketing.daily-story": 30600,
}


def test_co_du_8_mau():
    assert len(LABELS) == 8, f"đếm được {len(LABELS)} mẫu: {LABELS}"


@pytest.mark.parametrize("label", LABELS)
def test_mau_CHUA_dien_da_la_plist_hop_le(label):
    """Chỗ trống `__X__` nằm trong <string>, nên mẫu thô vẫn phải parse được.

    Nếu không, lỗi XML (ví dụ hai dấu gạch trong một chú thích) chỉ lộ ra sau khi điền —
    tức là trên máy người dùng.
    """
    d = plistlib.loads((MAU / f"{label}.plist").read_bytes())
    assert d["Label"] == label, "Label phải trùng tên file — launchctl định danh bằng Label"


@pytest.mark.parametrize("label", LABELS)
def test_dien_xong_khong_con_cho_trong(label):
    b = IL.render(label, GIA)
    t = b.decode("utf-8")
    assert not IL._CHO_TRONG.search(t), "còn chỗ trống sau khi điền"
    d = plistlib.loads(b)
    assert d["Label"] == label
    assert d["EnvironmentVariables"]["HOME"] == GIA["__HOME__"]
    assert d["WorkingDirectory"] == GIA["__STATION__"]


@pytest.mark.parametrize("label,lich", sorted(LICH.items()))
def test_lich_dung_bang_da_chot(label, lich):
    d = plistlib.loads(IL.render(label, GIA))
    assert d["StartCalendarInterval"] == lich


def test_truyen_chay_LUC_0_GIO():
    """Quyết định của người (dời 03:00 → 00:00 cho lượt Mac): giữ bằng một test riêng."""
    d = plistlib.loads(IL.render("studio.marketing.daily-story", GIA))
    assert d["StartCalendarInterval"]["Hour"] == 0


def _tran_gio(label) -> int:
    a = plistlib.loads(IL.render(label, GIA))["ProgramArguments"]
    assert "--timeout" in a, "job theo lịch phải có --timeout (launchd không tự giết)"
    assert a.index("--timeout") < a.index("--"), "--timeout là cờ của wrapper, không của lệnh con"
    return int(a[a.index("--timeout") + 1])


@pytest.mark.parametrize("label", [l for l in LABELS if l in LICH])
def test_job_theo_lich_CO_tran_gio(label):
    """launchd không có ExecutionTimeLimit — trần giờ phải nằm ở wrapper, không được quên."""
    giay = _tran_gio(label)
    assert 600 <= giay <= 24 * 3600, f"trần {giay}s vô lý"


@pytest.mark.parametrize("label,giay", sorted(TRAN_GIO.items()))
def test_tran_gio_dung_bang_da_chot(label, giay):
    assert _tran_gio(label) == giay


def test_truyen_KHONG_duoc_ha_tran_gio_sat_luot_that():
    """Trần của lượt truyện là quyết định của người, và nó có một đáy.

    Lượt thật bấm giờ ≈ 6 h 05 (TTS 5 h 47 + dựng video 15,5 phút + upload 30 phút) —
    nhưng đo trên máy RẢNH. Lượt hằng đêm còn crawl và dựng video chen vào. Hạ trần
    xuống sát 6 h là giết lượt đúng lúc nó vừa đọc xong và chưa kịp dựng video: mất
    trọn 6 tiếng đã chạy, mà wrapper vẫn chỉ báo "quá giờ".
    """
    assert _tran_gio("studio.marketing.daily-story") >= 30600


@pytest.mark.parametrize("label", ["studio.marketing.worker",
                                   "studio.marketing.approve-poller"])
def test_job_song_dai_KHONG_boc_wrapper_bao_Telegram(label):
    """Gọi mỗi phút mà báo mỗi lượt = hàng nghìn tin/ngày. Chủ đích, phải giữ."""
    d = plistlib.loads(IL.render(label, GIA))
    a = " ".join(d["ProgramArguments"])
    assert "notify_run.py" not in a
    assert d["KeepAlive"] is True
    assert d["ThrottleInterval"] == 60


@pytest.mark.parametrize("label", LABELS)
def test_moi_plist_khai_bien_MPS_cua_tram_giong(label):
    e = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]
    assert e["OMNIVOICE_DEVICE"] == "mps"
    # launchd không đọc ~/.zshrc: PATH phải khai ở đây, và phải có chỗ Homebrew.
    assert "/opt/homebrew/bin" in e["PATH"]


def test_bang_GIONG_phu_kin_moi_mau():
    """Thêm một mẫu plist mà quên xếp nó vào pipeline nào ⇒ đỏ ở đây.

    Không có cổng này thì mẫu mới lặng lẽ thừa hưởng cấu hình của mẫu người ta chép từ
    đó — đúng cách bộ plist cũ khai fp16 cho cả 8 job.
    """
    assert set(GIONG) == set(LABELS), (
        f"chưa xếp pipeline cho: {sorted(set(LABELS) - set(GIONG))}; "
        f"xếp cho label không có mẫu: {sorted(set(GIONG) - set(LABELS))}")


@pytest.mark.parametrize("label", LABELS)
def test_moi_pipeline_khai_dtype_cua_CHINH_no(label):
    dtype, co_hf = GIONG[label]
    e = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]
    assert e.get("OMNIVOICE_DTYPE") == dtype, (
        f"{label}: chờ OMNIVOICE_DTYPE={dtype!r}, thấy {e.get('OMNIVOICE_DTYPE')!r}")
    assert ("HF_DEACTIVATE_ASYNC_LOAD" in e) is co_hf, (
        f"{label}: HF_DEACTIVATE_ASYNC_LOAD {'phải có' if co_hf else 'KHÔNG được khai'}")
    if co_hf:
        assert e["HF_DEACTIVATE_ASYNC_LOAD"] == "1"


@pytest.mark.parametrize("label", TIN)
def test_plist_TIN_khong_duoc_mang_cau_hinh_cua_TRUYEN(label):
    """Cổng chốt của quyết định 20/09: KHÔNG gộp hai pipeline lại làm một.

    Đỏ nếu một plist tin mang `float16` hoặc mang `HF_DEACTIVATE_ASYNC_LOAD` — hai thứ
    thuộc về nhánh fp16 của lượt truyện. Đọc thẳng khối `EnvironmentVariables` đã điền
    (không quét chữ trong file) vì phần chú thích của plist tin có NHẮC tên hai thứ đó
    để giải thích vì sao chúng vắng mặt.
    """
    e = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]
    assert e["OMNIVOICE_DTYPE"] == "float32"
    assert e["OMNIVOICE_DTYPE"] != "float16", "pipeline tin chạy fp32 — xem bảng GIONG"
    assert "HF_DEACTIVATE_ASYNC_LOAD" not in e, (
        "biến này vá vụ nổ khi nạp trọng số fp16 trên MPS; lượt tin không đi nhánh đó")


@pytest.mark.parametrize("label", TRUYEN)
def test_plist_TRUYEN_giu_fp16_va_bien_chong_no(label):
    e = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]
    assert e["OMNIVOICE_DTYPE"] == "float16", "truyện 5 h 47 TTS — fp32 là vượt trần giờ"
    assert e["HF_DEACTIVATE_ASYNC_LOAD"] == "1", "thiếu là crash ngay lúc nạp model"


@pytest.mark.parametrize("label", KHONG_TTS)
def test_job_khong_chay_TTS_thi_khong_khai_dtype(label):
    e = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]
    assert "OMNIVOICE_DTYPE" not in e
    assert "HF_DEACTIVATE_ASYNC_LOAD" not in e


def test_ba_job_nguy_hiem_KHONG_nam_trong_bo_mac_dinh():
    """worker/poller chạy liên tục, truyện chạy hàng giờ giữa đêm. Bật phải là câu người gõ."""
    assert set(IL.KHONG_MAC_DINH) == {"studio.marketing.worker",
                                      "studio.marketing.approve-poller",
                                      "studio.marketing.daily-story"}
    assert set(IL.KHONG_MAC_DINH) <= set(LABELS), "tên trong danh sách chặn phải có mẫu thật"


def test_thieu_cho_trong_la_LOI_chu_khong_phai_plist_do_dang():
    with pytest.raises(SC.ContractError):
        IL.render(LABELS[0], {"__HOME__": "/x"})


# ── CLI ──────────────────────────────────────────────────────────────────────

def _chay(*doi, cwd=None):
    return subprocess.run([sys.executable, str(ROOT / "scripts/runners/install_launchd.py"),
                           *doi], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd or str(ROOT))


def test_list_in_du_8_label():
    r = _chay("--list")
    assert r.returncode == 0, r.stderr
    for l in LABELS:
        assert l in r.stderr


def test_thieu_khai_kenh_chien_dich_la_ma_2(tmp_path):
    r = _chay("--station", str(tmp_path), "--dry-run")
    assert r.returncode == 2, r.stderr
    assert "chưa khai kênh/chiến dịch" in r.stderr


def test_dry_run_KHONG_ghi_file_va_KHONG_goi_launchctl(tmp_path, monkeypatch):
    ra = tmp_path / "LaunchAgents"
    r = _chay("--station", str(tmp_path), "--out-dir", str(ra), "--dry-run",
              "--map", "studio.marketing.daily-news-a=kenh/chien-dich",
              "--only", "studio.marketing.daily-news-a")
    assert r.returncode == 0, r.stderr
    assert not ra.exists(), "dry-run vẫn tạo thư mục đích"
    assert "KHÔNG gọi launchctl" in r.stderr


def test_dry_run_khong_goi_launchctl_KE_CA_khi_launchctl_ton_tai(monkeypatch, tmp_path):
    """Vế mạnh hơn: chặn ở tầng gọi, không chỉ ở việc máy test không có launchctl."""
    goi = []
    monkeypatch.setattr(IL, "_launchctl", lambda *a: goi.append(a) or (0, ""))
    monkeypatch.setattr(IL, "_la_mac", lambda: True)
    ap = IL.argparse.Namespace(
        station=str(tmp_path), only=["studio.marketing.daily-news-a"], all=False,
        map=["studio.marketing.daily-news-a=kenh/chien-dich"], out_dir=str(tmp_path / "la"),
        uninstall=False, no_load=False, dry_run=True, list=False, json=False, prog="t")
    IL.lam(ap)
    assert goi == [], f"dry-run đã gọi launchctl: {goi}"


def test_khai_trong_launchd_json_cua_tram_duoc_doc(tmp_path):
    (tmp_path / "launchd.json").write_text(
        '{"studio.marketing.daily-news-a": "kenh/chien-dich"}', encoding="utf-8", newline="\n")
    r = _chay("--station", str(tmp_path), "--dry-run", "--json",
              "--only", "studio.marketing.daily-news-a")
    assert r.returncode == 0, r.stderr
    assert '"channel": "kenh"' in r.stdout and '"campaign": "chien-dich"' in r.stdout


def test_khai_sai_dang_la_ma_2(tmp_path):
    r = _chay("--station", str(tmp_path), "--dry-run",
              "--map", "studio.marketing.daily-news-a=chi-mot-muc",
              "--only", "studio.marketing.daily-news-a")
    assert r.returncode == 2, r.stderr


def test_label_khong_co_mau_la_ma_2(tmp_path):
    r = _chay("--station", str(tmp_path), "--dry-run", "--only", "studio.marketing.khong-co")
    assert r.returncode == 2, r.stderr


# ══ REVIEW-P2 N14 + Ghi nhận 18 — lỗi CẤU HÌNH không được mang mã 1 ═════════
# `SC.classify` xếp mọi lỗi lạ thành mã 1 = "thử lại có thể được", và bộ lập lịch THỬ LẠI
# mã 1. Một lỗi cấu hình mang mã 1 là một vòng lặp vô hạn trên thứ không bao giờ tự khỏi.

def test_duong_dan_co_ky_tu_XML_khong_lam_vo_plist():
    """`~/Code/AI & Data Studio` là tên thư mục hợp lệ trên macOS. Nhét thô vào XML thì
    `&` phá cả file, `plistlib.loads` ném `ExpatError` -> mã 1 -> cài lại vô hạn."""
    bang = {**GIA, "__HOME__": _NHA + "/Code/AI & Data <Studio>"}
    b = IL.render(LABELS[0], bang)
    import plistlib
    d = plistlib.loads(b)
    assert "AI & Data <Studio>" in json.dumps(d), "giá trị phải còn NGUYÊN sau khi thoát XML"


def test_gia_tri_pha_XML_bang_the_dong_la_ma_2_khong_phai_1():
    """Chuỗi cố tình đóng thẻ sớm: nếu vẫn lọt ra `ExpatError` thì mã thoát là 1."""
    bang = {**GIA, "__CHANNEL__": "</string></dict></plist><evil>"}
    b = IL.render(LABELS[0], bang)       # thoát đúng thì đây là một plist hợp lệ
    import plistlib
    assert "<evil>" in json.dumps(plistlib.loads(b))


def test_doc_khai_gia_tri_la_so_la_ma_2(tmp_path, monkeypatch):
    """`{"nhan": 7}` -> `7.get(...)` -> `AttributeError` -> `classify` -> mã 1."""
    tram = tmp_path / "tram"
    (tram).mkdir()
    (tram / IL.KHAI_FILE).write_text(json.dumps({"nhan": 7}), encoding="utf-8")
    monkeypatch.setenv("MARKETING_STUDIO_DATA", str(tram))
    with pytest.raises(SC.ContractError):
        IL.doc_khai(str(tram))


# ══ REVIEW-P2 Ghi nhận 15 — F13 phải được canh bằng HÀNH VI, không bằng hằng ═

def _khai_du(tmp_path):
    """Trạm giả có khai kênh/chiến dịch cho MỌI label, để `lam()` chạy tới bước chọn."""
    tram = tmp_path / "tram"
    tram.mkdir()
    (tram / IL.KHAI_FILE).write_text(
        json.dumps({l: "kenh-mau/chien-dich-mau" for l in LABELS}), encoding="utf-8")
    return tram


def _chon(tmp_path, **doi):
    a = IL._parser().parse_args([])
    a.station, a.dry_run, a.out_dir = str(_khai_du(tmp_path)), True, str(tmp_path / "ra")
    for k, v in doi.items():
        setattr(a, k, v)
    return [m["label"] for m in IL.lam(a)["jobs"]]


def test_mac_dinh_KHONG_nap_ba_job_chay_lien_tuc(tmp_path):
    """Assert trên hằng số `KHONG_MAC_DINH` không chứng minh `lam()` có dùng nó. Cổng này
    chạy `lam()` thật và đếm job nó chọn."""
    chon = _chon(tmp_path)
    assert set(chon) == set(LABELS) - set(IL.KHONG_MAC_DINH)
    for l in IL.KHONG_MAC_DINH:
        assert l not in chon, f"{l} không được nạp khi không ai gõ tên nó ra"


def test_all_thi_nap_du(tmp_path):
    assert set(_chon(tmp_path, all=True)) == set(LABELS)


def test_only_goi_dich_danh_thi_van_nap_duoc_job_bi_loai(tmp_path):
    l = IL.KHONG_MAC_DINH[0]
    assert _chon(tmp_path, only=[l]) == [l]


# ══ P4 (Mac mini chạy embedded) — PATH, con trỏ bí mật, runner, lịch, trạm ═══════════
#
# Kịch bản đích: một Mac mini chạy tự động ở chế độ `embedded` — KHÔNG có biến trạm nào,
# trạm là `<repo>/workspace/`, cấu hình ở `<repo>/.env`. launchd không đọc `.env` và không
# đọc `~/.zshrc`, nên mọi thứ job cần phải đi vào plist qua bộ cài — và chỉ TÊN của con trỏ
# bí mật được khai trong repo, GIÁ TRỊ đến từ máy.

import studio_paths as SP  # noqa: E402

CON_TRO_DAY_DU = ["TG_CONFIG", "TG_CHAT", "YT_CLIENT_SECRET", "YT_TOKEN_PATH", "FB_CONFIG",
                  "EMAIL_CONFIG", "CODEX_BRIDGE"]
# Quyền tối thiểu: job nào khai con trỏ nào là QUYẾT ĐỊNH. Poller chỉ nói chuyện Telegram.
BI_MAT = {**{l: CON_TRO_DAY_DU for l in TIN + TRUYEN + ["studio.marketing.worker"]},
          "studio.marketing.approve-poller": ["TG_CONFIG", "TG_CHAT"]}


@pytest.fixture
def khong_bien(monkeypatch):
    """Máy test có thể đặt sẵn biến thật (máy lịch Windows đặt ở cấp user). Gỡ hết."""
    for n in CON_TRO_DAY_DU + ["MARKETING_STUDIO_DATA", "MARKETING_STUDIO_HOME",
                               "YT_TOKEN_PATH__TRUYEN"]:
        monkeypatch.delenv(n, raising=False)


@pytest.mark.parametrize("label", LABELS)
def test_PATH_co_local_bin_DA_MO_RONG_va_homebrew_ca_hai_kien_truc(label):
    duong = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]["PATH"].split(":")
    assert duong[0] == GIA["__HOME__"] + "/.local/bin", "launchd không tự mở rộng ~"
    assert "/opt/homebrew/bin" in duong and "/usr/local/bin" in duong
    assert not any("~" in d or "$" in d for d in duong), duong


def test_bang_BI_MAT_phu_kin_moi_mau():
    assert set(BI_MAT) == set(LABELS)


@pytest.mark.parametrize("label", LABELS)
def test_mau_khai_DUNG_bo_con_tro_bi_mat_cua_job(label):
    assert IL.ten_bi_mat(label) == BI_MAT[label]


@pytest.mark.parametrize("ten", CON_TRO_DAY_DU)
def test_moi_con_tro_trong_mau_DEU_duoc_tai_lieu_hoa(ten):
    assert SP.la_con_tro_bi_mat(ten) or ten in IL.KHONG_PHAI_DUONG_DAN
    for noi in ("knowledge/toolchains/SECRETS.md", ".env.example", "docs/launchd.md"):
        assert ten in (ROOT / noi).read_text(encoding="utf-8"), f"{noi} thiếu {ten}"


@pytest.mark.parametrize("label", LABELS)
def test_mau_KHONG_chua_gia_tri_bi_mat_nao(label):
    """Chỉ TÊN nằm trong repo: mọi giá trị con trỏ trong mẫu là chỗ trống `__ENV_TÊN__`."""
    t = (MAU / f"{label}.plist").read_text(encoding="utf-8")
    for n in IL.ten_bi_mat(label):
        assert f"<key>{n}</key><string>__ENV_{n}__</string>" in t


@pytest.mark.parametrize("label", LABELS)
def test_con_tro_CHUA_khai_thi_BO_ca_dong_khong_ghi_chuoi_rong(label):
    e = plistlib.loads(IL.render(label, GIA))["EnvironmentVariables"]
    for n in BI_MAT[label]:
        assert n not in e, f"{n} chưa khai mà vẫn vào plist"
    assert all(v != "" for v in e.values())


def test_con_tro_DA_khai_thi_dien_dung_gia_tri():
    l = "studio.marketing.daily-story"
    bi_mat = {"YT_TOKEN_PATH": _NHA + "/khoa/yt & token.json", "TG_CHAT": "mac_dinh"}
    e = plistlib.loads(IL.render(l, GIA, bi_mat=bi_mat))["EnvironmentVariables"]
    assert e["YT_TOKEN_PATH"] == bi_mat["YT_TOKEN_PATH"]
    assert e["TG_CHAT"] == "mac_dinh"
    assert "FB_CONFIG" not in e


def test_gia_tri_chua_chuoi_giong_cho_trong_KHONG_bi_thay_lan_hai():
    l = "studio.marketing.daily-news-a"
    bi_mat = {"FB_CONFIG": _NHA + "/__HOME__/fb.json"}
    e = plistlib.loads(IL.render(l, GIA, bi_mat=bi_mat))["EnvironmentVariables"]
    assert e["FB_CONFIG"] == bi_mat["FB_CONFIG"]


def test_con_tro_THEM_theo_kenh_duoc_chen_dung_cho():
    l = "studio.marketing.daily-story"
    bi_mat = {"YT_TOKEN_PATH__TRUYEN": _NHA + "/khoa/truyen.json"}
    e = plistlib.loads(IL.render(l, GIA, bi_mat=bi_mat, them=["YT_TOKEN_PATH__TRUYEN"]))[
        "EnvironmentVariables"]
    assert e["YT_TOKEN_PATH__TRUYEN"] == bi_mat["YT_TOKEN_PATH__TRUYEN"]


def test_gia_bi_mat_BIEN_MOI_TRUONG_truoc_roi_toi_env_embedded(tmp_path, monkeypatch,
                                                              khong_bien):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / SP.LOCAL_CONFIG).write_text('{"mode": "embedded"}', encoding="utf-8")
    (repo / ".env").write_text("TG_CONFIG=~/khoa/tg.json\nYT_TOKEN_PATH=/khoa/yt.json\n",
                               encoding="utf-8")
    monkeypatch.setenv("YT_TOKEN_PATH", "/tu-bien/yt.json")
    co, thieu = IL.gia_bi_mat(["TG_CONFIG", "YT_TOKEN_PATH", "FB_CONFIG"], repo)
    assert co["YT_TOKEN_PATH"] == str(Path("/tu-bien/yt.json")), "biến thật phải thắng .env"
    assert co["TG_CONFIG"] == str(Path("~/khoa/tg.json").expanduser()), "~ phải được mở rộng"
    assert "~" not in co["TG_CONFIG"]
    assert thieu == ["FB_CONFIG"]


def test_gia_bi_mat_KHONG_doc_env_o_che_do_separate(tmp_path, khong_bien):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / SP.LOCAL_CONFIG).write_text('{"mode": "separate"}', encoding="utf-8")
    (repo / ".env").write_text("TG_CONFIG=/khoa/tg.json\n", encoding="utf-8")
    assert IL.gia_bi_mat(["TG_CONFIG"], repo) == ({}, ["TG_CONFIG"])


def test_TOKEN_TRAN_thay_cho_duong_dan_la_ma_2_va_KHONG_in_gia_tri(monkeypatch, khong_bien):
    tho = "123456:bi-mat-khong-duoc-lo"
    monkeypatch.setenv("TG_CONFIG", tho)
    with pytest.raises(SC.ContractError) as e:
        IL.gia_bi_mat(["TG_CONFIG"])
    assert tho not in str(e.value) and "TG_CONFIG" in str(e.value)


def test_log_va_JSON_chi_mang_TEN_bien_khong_mang_gia_tri(tmp_path):
    import os
    gia = _NHA + "/khoa/dau-vet-khong-duoc-lo.json"
    env = {**os.environ, "YT_TOKEN_PATH": gia, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(ROOT / "scripts/runners/install_launchd.py"),
                        "--station", str(tmp_path), "--dry-run", "--json",
                        "--map", "studio.marketing.daily-news-a=kenh/chien-dich",
                        "--only", "studio.marketing.daily-news-a"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env)
    assert r.returncode == 0, r.stderr
    assert "YT_TOKEN_PATH" in r.stderr and "YT_TOKEN_PATH" in r.stdout
    assert "dau-vet-khong-duoc-lo" not in r.stderr + r.stdout


# ── runner theo job ──────────────────────────────────────────────────────────

CO_RUNNER = [l for l in LABELS if l in LICH]


@pytest.mark.parametrize("label", CO_RUNNER)
def test_job_theo_lich_goi_RUNNER_khai_duoc(label):
    a = plistlib.loads(IL.render(label, {**GIA, "__RUNNER__": "run-daily-truyen-p2.ps1"}))[
        "ProgramArguments"]
    assert a[-1] == GIA["__STATION__"] + "/kenh-mau/chien-dich-mau/run-daily-truyen-p2.ps1"


def test_runner_mac_dinh_la_run_ps1(tmp_path):
    r = _chay("--station", str(tmp_path), "--dry-run", "--json",
              "--map", "studio.marketing.daily-story=kenh/chien-dich",
              "--only", "studio.marketing.daily-story")
    assert r.returncode == 0, r.stderr
    assert '"runner": "run.ps1"' in r.stdout


def test_runner_doc_tu_launchd_json(tmp_path):
    (tmp_path / "launchd.json").write_text(json.dumps({"studio.marketing.daily-story": {
        "channel": "truyen", "campaign": "hang-ngay", "runner": "run-daily-truyen-p2.ps1"}}),
        encoding="utf-8")
    r = _chay("--station", str(tmp_path), "--dry-run", "--json",
              "--only", "studio.marketing.daily-story")
    assert r.returncode == 0, r.stderr
    assert '"runner": "run-daily-truyen-p2.ps1"' in r.stdout


@pytest.mark.parametrize("runner", ["../ngoai.ps1", "con/run.ps1", "run.sh", "", 7,
                                    "..\\ngoai.ps1", "..ps1"])
def test_runner_KHONG_phai_ten_file_ps1_la_ma_2(runner):
    with pytest.raises(SC.ContractError):
        IL.muc_khai("studio.marketing.daily-story",
                    {"channel": "k", "campaign": "c", "runner": runner})


@pytest.mark.parametrize("khai", [{"channel": "k", "campaign": "c", "la": 1},
                                  {"channel": "k"}, {"channel": "..", "campaign": "c"},
                                  {"channel": "k", "campaign": "c", "env": "YT_TOKEN_PATH"},
                                  {"channel": "k", "campaign": "c", "env": ["PATH"]},
                                  {"channel": "k", "campaign": "c", "env": ["HOME"]}])
def test_khai_sai_hinh_dang_la_ma_2(khai):
    with pytest.raises(SC.ContractError):
        IL.muc_khai("studio.marketing.daily-story", khai)


def test_map_GIU_runner_cua_launchd_json(tmp_path):
    (tmp_path / "launchd.json").write_text(json.dumps({"studio.marketing.daily-story": {
        "channel": "truyen", "campaign": "cu", "runner": "run-p2.ps1"}}), encoding="utf-8")
    r = _chay("--station", str(tmp_path), "--dry-run", "--json",
              "--map", "studio.marketing.daily-story=truyen/moi",
              "--only", "studio.marketing.daily-story")
    assert r.returncode == 0, r.stderr
    assert '"campaign": "moi"' in r.stdout and '"runner": "run-p2.ps1"' in r.stdout


# ── env thêm theo kênh ───────────────────────────────────────────────────────

def _tram_co_env_them(tmp_path):
    tram = tmp_path / "tram"
    tram.mkdir()
    (tram / "launchd.json").write_text(json.dumps({"studio.marketing.daily-story": {
        "channel": "k", "campaign": "c", "env": ["YT_TOKEN_PATH__TRUYEN"]}}), encoding="utf-8")
    return IL._parser().parse_args(["--station", str(tram), "--dry-run",
                                    "--only", "studio.marketing.daily-story"])


def test_env_them_DA_KHAI_ma_THIEU_gia_tri_la_ma_2(tmp_path, khong_bien):
    with pytest.raises(SC.ContractError) as e:
        IL.lam(_tram_co_env_them(tmp_path))
    assert "YT_TOKEN_PATH__TRUYEN" in str(e.value)


def test_env_them_CO_gia_tri_thi_vao_ket_qua(tmp_path, monkeypatch, khong_bien):
    monkeypatch.setenv("YT_TOKEN_PATH__TRUYEN", "/khoa/truyen.json")
    job = IL.lam(_tram_co_env_them(tmp_path))["jobs"][0]
    assert job["secret_env"] == ["YT_TOKEN_PATH__TRUYEN"]
    assert "TG_CONFIG" in job["secret_env_missing"]


# ── lịch khai được ───────────────────────────────────────────────────────────

def test_schedule_thay_lich_cua_mau():
    d = plistlib.loads(IL.render("studio.marketing.daily-story", GIA,
                                 lich={"Hour": 0, "Minute": 30}))
    assert d["StartCalendarInterval"] == {"Hour": 0, "Minute": 30}
    assert d["EnvironmentVariables"]["OMNIVOICE_DTYPE"] == "float16", "đổi lịch không đổi giọng"


def test_schedule_tren_job_KHONG_co_lich_la_ma_2():
    with pytest.raises(SC.ContractError):
        IL.render("studio.marketing.worker", GIA, lich={"Hour": 1})


@pytest.mark.parametrize("lich", [{"Hour": 24}, {"Gio": 1}, {}, [], {"Minute": "5"},
                                  {"Hour": True}])
def test_schedule_sai_la_ma_2(lich):
    with pytest.raises(SC.ContractError):
        IL.muc_khai("studio.marketing.daily-story",
                    {"channel": "k", "campaign": "c", "schedule": lich})


# ── chế độ embedded: không biến trạm nào ⇒ trạm là <repo>/workspace ──────────

def test_embedded_KHONG_bien_tram_thi_tram_la_repo_workspace(monkeypatch, khong_bien):
    monkeypatch.setattr(SP, "local_config", lambda repo=None: {})
    bang, _ = IL.cho_trong(None)
    assert Path(bang["__STATION__"]) == (ROOT / "workspace").resolve()
    assert Path(bang["__REPO__"]) == ROOT


@pytest.mark.skipif(sys.platform == "win32", reason="quyền 600 chỉ có nghĩa trên POSIX")
def test_plist_ghi_ra_chi_chu_may_doc(tmp_path):
    import stat
    ra = tmp_path / "LaunchAgents"
    r = _chay("--station", str(tmp_path), "--out-dir", str(ra), "--no-load",
              "--map", "studio.marketing.daily-news-a=kenh/chien-dich",
              "--only", "studio.marketing.daily-news-a")
    assert r.returncode == 0, r.stderr
    f = ra / "studio.marketing.daily-news-a.plist"
    assert stat.S_IMODE(f.stat().st_mode) == 0o600


def test_tai_lieu_dinh_dang_launchd_json_co_vi_du_HOP_LE():
    """Ví dụ trong docs/launchd.md phải qua được chính bộ kiểm của bộ cài."""
    import re
    t = (ROOT / "docs" / "launchd.md").read_text(encoding="utf-8")
    khoi = re.findall(r"```json\n(.*?)```", t, re.S)
    assert khoi, "docs/launchd.md phải có ví dụ ```json"
    for k in khoi:
        for label, v in json.loads(k).items():
            assert label in LABELS, label
            IL.muc_khai(label, v)
