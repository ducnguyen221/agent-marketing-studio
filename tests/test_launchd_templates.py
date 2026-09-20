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

GIA = {
    "__HOME__": "/Users/nguoi-dung",
    "__REPO__": "/Users/nguoi-dung/Code/agent-marketing-studio",
    "__STATION__": "/Users/nguoi-dung/noi-dung",
    "__PY__": "/Users/nguoi-dung/Code/agent-marketing-studio/.venv/bin/python",
    "__VOICE_STATION__": "/Users/nguoi-dung/tram-giong",
    "__VIDEO_STATION__": "/Users/nguoi-dung/tram-video",
    "__OMNIVOICE_PY__": "/Users/nguoi-dung/tram-giong/omnivoice/.venv/bin/python",
    "__CHANNEL__": "kenh-mau",
    "__CAMPAIGN__": "chien-dich-mau",
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


@pytest.mark.parametrize("label", [l for l in LABELS if l in LICH])
def test_job_theo_lich_CO_tran_gio(label):
    """launchd không có ExecutionTimeLimit — trần giờ phải nằm ở wrapper, không được quên."""
    d = plistlib.loads(IL.render(label, GIA))
    a = d["ProgramArguments"]
    assert "--timeout" in a, "job theo lịch phải có --timeout (launchd không tự giết)"
    giay = int(a[a.index("--timeout") + 1])
    assert 600 <= giay <= 24 * 3600, f"trần {giay}s vô lý"
    assert a.index("--timeout") < a.index("--"), "--timeout là cờ của wrapper, không của lệnh con"


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
    assert e["OMNIVOICE_DTYPE"] == "float16"
    assert e["HF_DEACTIVATE_ASYNC_LOAD"] == "1"
    # launchd không đọc ~/.zshrc: PATH phải khai ở đây, và phải có chỗ Homebrew.
    assert "/opt/homebrew/bin" in e["PATH"]


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
