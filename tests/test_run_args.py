# -*- coding: utf-8 -*-
"""`run.ps1` phải truyền đối số xuống runner THEO TÊN, không theo vị trí.

Vì sao có file này — một sự cố thật, 07–08/09/2026:

`run.ps1` gom `runtime.runner_args` thành MẢNG rồi `& $runner @rargs`. PowerShell splat
mảng thì buộc tham số **theo vị trí**, nên `-Brand ai -Publish` vào runner thành
`$Brand = '-Brand'`, `$Profile = 'ai'`, và switch `-Publish` **biến mất không một dòng
báo**. Hai kiểu hỏng khác hẳn nhau:

· Runner CÓ `-Brand` (`run-toptoday-hot.ps1`, `run-weekly-news.ps1`) → `Get-BrandDir`
  ném lỗi ngay: Daily Hot Data 7PM (07/09) và Daily Hot AI 6PM (08/09) exit 1. Thấy được.
· Runner KHÔNG có `-Brand` (`run-weekly-repo.ps1`) → `-Publish` rơi vào `$Date`, switch
  `$Publish` = `$false`, pipeline chạy hết rồi `if (-not $Publish) { exit 0 }`:
  **không đăng gì mà exit 0, Telegram báo ✅**. Đây mới là kiểu đắt tiền, và nó chưa kịp
  tới lịch nên không ai biết.

Cả 5 chiến dịch có scheduled task dùng CHUNG một `run.ps1` (byte giống hệt nhau), nên
một dòng sai ở đây là 5 pipeline chết cùng lúc. Test này giữ đúng chỗ đó.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
MAU = GOC / "templates" / "station" / "_channel" / "_campaign" / "run.ps1"

PS = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(PS is None, reason="khong co PowerShell tren may nay")

# Runner giả: chỉ in ra ĐÚNG những gì nó nhận được. Không đụng mạng, không đụng đĩa.
PROBE = """param(
  [string]$Brand = 'ai',
  [string]$Date = 'MAC-DINH',
  [string]$Profile = '',
  [switch]$SkipResearch,
  [switch]$Publish,
  [string]$Config = ''
)
"PROBE Brand=[$Brand] Date=[$Date] Profile=[$Profile] Publish=[$Publish] SkipResearch=[$SkipResearch] CoConfig=[$([bool]$Config)]"
"""

# Runner giả kiểu `run-weekly-repo.ps1`: KHÔNG có -Brand, tham số vị trí đầu là -Date.
PROBE_KHONG_BRAND = """param(
  [string]$Date = 'MAC-DINH',
  [switch]$Publish,
  [string]$Config = ''
)
"PROBE Date=[$Date] Publish=[$Publish] CoConfig=[$([bool]$Config)]"
"""


def _tram(tmp_path: Path, runner_args: str, probe: str = PROBE,
          channels: bool = True) -> Path:
    """Dựng trạm tối thiểu 1 kênh + 1 chiến dịch, trả về thư mục chiến dịch.

    `run.ps1` được chép NGUYÊN TỪNG BYTE từ template — không vá dòng nào. Trạm tìm bằng
    cách đi lên tới `CHANNELS.md` (có ở `tmp_path`), repo và Python đi qua biến môi
    trường (`_chay`), nên test chạy được ở bản clone bất kỳ, trên Windows lẫn macOS.
    """
    campaign = tmp_path / "kenh-thu" / "cd-thu"
    campaign.mkdir(parents=True)
    if channels:
        (tmp_path / "CHANNELS.md").write_text("# Kênh\n", encoding="utf-8")
    (campaign.parent / "channel.yml").write_text(
        'schema: channel/1\nid: kenh-thu\nlabel: "Kênh thử"\n'
        "platforms:\n  - channel: youtube\n    post_formats: [youtube_video]\n",
        encoding="utf-8")
    (campaign / "campaign.md").write_text(
        "---\nschema: campaign/1\nid: cd-thu\nchannel: kenh-thu\n"
        'runtime:\n  label: "Nhãn thử"\n  runner: probe.ps1\n'
        f'  runner_args: "{runner_args}"\n---\n\nThân bài.\n', encoding="utf-8")
    (campaign / "probe.ps1").write_text(probe, encoding="utf-8-sig")

    (campaign / "run.ps1").write_bytes(MAU.read_bytes())
    return campaign


def _chay(campaign: Path, *add: str, **env):
    moi = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               MARKETING_STUDIO_HOME=str(GOC), MARKETING_STUDIO_PY=sys.executable)
    moi.update(env)
    return subprocess.run(
        [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(campaign / "run.ps1"), *add],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(campaign), env=moi)


def test_doi_so_buoc_theo_ten_khong_theo_vi_tri(tmp_path):
    """`-Brand ai` phải vào $Brand, KHÔNG được để $Brand = '-Brand'."""
    r = _chay(_tram(tmp_path, "-Brand ai -Publish"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Brand=[ai]" in r.stdout, r.stdout
    assert "Brand=[-Brand]" not in r.stdout, "splat theo vi tri da quay lai: " + r.stdout


def test_switch_publish_khong_bi_nuot(tmp_path):
    """Kiểu hỏng ĐẮT NHẤT: mất `-Publish` thì pipeline exit 0 mà không đăng gì."""
    r = _chay(_tram(tmp_path, "-Brand ai -Publish"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Publish=[True]" in r.stdout, "switch -Publish bi nuot: " + r.stdout


def test_runner_khong_co_brand_van_nhan_dung_publish(tmp_path):
    """Hình dạng `hot-repo`: chỉ `-Publish`, runner không có -Brand.

    Bản hỏng cho `$Date = '-Publish'` và `$Publish = $false` — im lặng tuyệt đối.
    """
    r = _chay(_tram(tmp_path, "-Publish", probe=PROBE_KHONG_BRAND))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Publish=[True]" in r.stdout, r.stdout
    assert "Date=[MAC-DINH]" in r.stdout, "'-Publish' roi vao $Date: " + r.stdout


def test_doi_so_dong_lenh_ghep_them_va_van_theo_ten(tmp_path):
    """`.\run.ps1 -Date ... -SkipResearch` phải cộng vào, không phá phần của campaign.md."""
    r = _chay(_tram(tmp_path, "-Brand ai -Publish"), "-Date", "2026-09-01", "-SkipResearch")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Brand=[ai]" in r.stdout and "Publish=[True]" in r.stdout, r.stdout
    assert "Date=[2026-09-01]" in r.stdout and "SkipResearch=[True]" in r.stdout, r.stdout


def test_config_luon_duoc_truyen(tmp_path):
    """Bản chụp cấu hình phải tới runner, nếu không runner lặng lẽ đọc brand.json cũ."""
    r = _chay(_tram(tmp_path, "-Brand ai"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CoConfig=[True]" in r.stdout, r.stdout


def test_runner_args_khong_phai_doi_so_thi_dung_han(tmp_path):
    """`runner_args` là ô cho MÁY đọc. Có người từng viết văn xuôi vào đó.

    (`nghe-tien-truyen/pham_nhan_tu_tien_phan_1`: "(chạy tay — KHÔNG có scheduled task)".)
    Đoán bừa nghĩa là truyền rác xuống runner; phải dừng và nói rõ.
    """
    r = _chay(_tram(tmp_path, "chay tay KHONG co scheduled task"))
    assert r.returncode == 2, f"phai dung han, ma exit={r.returncode}: {r.stdout}"
    assert "khong phai ten tham so" in r.stdout, r.stdout
    assert "PROBE" not in r.stdout, "van goi runner voi doi so rac: " + r.stdout


# ── Tìm runner ở `scripts/runners/` của REPO ────────────────────────────────

def _tram_runner_repo(tmp_path: Path, runner_ten: str) -> tuple[Path, Path]:
    """Trạm + một BẢN SAO cây `scripts/` để probe nằm đúng chỗ repo sẽ tìm.

    Chép cả cây thay vì trỏ vào repo thật: đặt file probe vào repo thật là để lại rác,
    và test sẽ phụ thuộc vào thứ nó tự bày ra ở nơi khác.
    """
    import shutil
    ban_sao = tmp_path / "repo" / "scripts"
    shutil.copytree(GOC / "scripts", ban_sao,
                    ignore=shutil.ignore_patterns("__pycache__"))
    (ban_sao / "runners").mkdir(exist_ok=True)
    (ban_sao / "runners" / runner_ten).write_text(PROBE, encoding="utf-8-sig")

    campaign = tmp_path / "kenh-thu" / "cd-thu"
    campaign.mkdir(parents=True)
    (campaign.parent / "channel.yml").write_text(
        'schema: channel/1\nid: kenh-thu\nlabel: "Kênh thử"\n'
        "platforms:\n  - channel: youtube\n    post_formats: [youtube_video]\n",
        encoding="utf-8")
    (campaign / "campaign.md").write_text(
        "---\nschema: campaign/1\nid: cd-thu\nchannel: kenh-thu\n"
        f'runtime:\n  label: "Nhãn thử"\n  runner: {runner_ten}\n'
        '  runner_args: "-Brand ai -Publish"\n---\n\nThân bài.\n', encoding="utf-8")

    # Repo = bản sao ở tmp (qua MARKETING_STUDIO_HOME khi chạy), run.ps1 = template nguyên byte.
    (tmp_path / "CHANNELS.md").write_text("# Kênh\n", encoding="utf-8")
    (campaign / "run.ps1").write_bytes(MAU.read_bytes())
    return campaign, ban_sao


def test_runner_dung_chung_tim_thay_o_scripts_runners_cua_repo(tmp_path):
    """Runner đi kèm repo phải chạy được ngay sau khi clone, không cần chép vào từng
    chiến dịch — nếu không thì mỗi chiến dịch giữ một bản sao và chúng trôi khỏi nhau."""
    campaign, ban_sao = _tram_runner_repo(tmp_path, "probe-chung.ps1")
    r = _chay(campaign, MARKETING_STUDIO_HOME=str(ban_sao.parent))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PROBE" in r.stdout, r.stdout
    assert "Brand=[ai]" in r.stdout and "Publish=[True]" in r.stdout, r.stdout


def test_runner_trong_thu_muc_chien_dich_VAN_thang_ban_cua_repo(tmp_path):
    """Thứ tự ưu tiên: chiến dịch > repo > engine. Một chiến dịch phải ghi đè được."""
    campaign, ban_sao = _tram_runner_repo(tmp_path, "probe-chung.ps1")
    (ban_sao / "runners" / "probe-chung.ps1").write_text(
        'param([string]$Config="")\n"PROBE SAI — ban cua REPO da chay"\n',
        encoding="utf-8-sig")
    (campaign / "probe-chung.ps1").write_text(PROBE, encoding="utf-8-sig")
    r = _chay(campaign, MARKETING_STUDIO_HOME=str(ban_sao.parent))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PROBE SAI" not in r.stdout, "bản của repo thắng bản của chiến dịch — sai thứ tự"
    assert "Brand=[ai]" in r.stdout, r.stdout


# ── Phân giải trạm / repo / Python: cùng một file cho Windows lẫn macOS ──────
# Bản cũ trỏ trạm và repo qua biến thư mục nhà CHỈ Windows có; trên macOS biến đó rỗng,
# Join-Path ra đường tương đối và mọi lượt lịch chết ngay dòng đầu (audit 19/09/2026).

_DONG = re.compile(r"run\.ps1: station=(.*?) engine=(.*?) repo=(.*)$", re.M)


def _cung(a: str, b: Path) -> bool:
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(b.resolve()))


def test_tram_tim_bang_cach_DI_LEN_toi_CHANNELS_md(tmp_path):
    """`CHANNELS.md` gần nhất phía trên THẮNG biến MARKETING_STUDIO_DATA: chạy một chiến
    dịch ở trạm nào thì dùng trạm đó, kể cả khi máy khai biến trỏ trạm khác."""
    khac = tmp_path / "tram-khac"
    khac.mkdir()
    r = _chay(_tram(tmp_path, "-Brand ai"), MARKETING_STUDIO_DATA=str(khac))
    assert r.returncode == 0, r.stdout + r.stderr
    m = _DONG.search(r.stdout)
    assert m, "thieu dong 'run.ps1: station=… engine=… repo=…': " + r.stdout
    assert _cung(m.group(1), tmp_path), m.group(0)
    assert _cung(m.group(3), GOC), m.group(0)


def test_khong_co_CHANNELS_thi_lui_ve_MARKETING_STUDIO_DATA(tmp_path):
    tram = tmp_path / "tram-bien"
    tram.mkdir()
    r = _chay(_tram(tmp_path, "-Brand ai", channels=False), MARKETING_STUDIO_DATA=str(tram))
    assert r.returncode == 0, r.stdout + r.stderr
    m = _DONG.search(r.stdout)
    assert m and _cung(m.group(1), tram), r.stdout


def test_engine_la_thu_muc_engine_CO_DINH_trong_tram(tmp_path):
    """Trạm có sẵn `engine/` thì dùng nó — không đường lùi nào được thắng."""
    (tmp_path / "engine").mkdir()
    r = _chay(_tram(tmp_path, "-Brand ai"))
    assert r.returncode == 0, r.stdout + r.stderr
    m = _DONG.search(r.stdout)
    assert m and _cung(m.group(2), tmp_path / "engine"), r.stdout


def test_repo_sai_thi_DUNG_va_noi_ro_bien_nao(tmp_path):
    r = _chay(_tram(tmp_path, "-Brand ai"), MARKETING_STUDIO_HOME=str(tmp_path / "khong-co"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "MARKETING_STUDIO_HOME" in r.stdout, r.stdout
    assert "PROBE" not in r.stdout, r.stdout


def test_MARKETING_STUDIO_PY_hong_thi_DUNG_khong_lang_le_doi_Python(tmp_path):
    """Người đã khai Python nào thì dùng đúng Python đó. Khai sai mà lặng lẽ lấy Python
    khác trong PATH là chạy với bộ thư viện khác — hỏng kiểu rất khó lần ra."""
    r = _chay(_tram(tmp_path, "-Brand ai"),
              MARKETING_STUDIO_PY=str(tmp_path / "khong-co-python"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "MARKETING_STUDIO_PY" in r.stdout, r.stdout
    assert "PROBE" not in r.stdout, r.stdout


def test_khong_khai_MARKETING_STUDIO_PY_van_tim_duoc_Python(tmp_path):
    """Đường thường của lịch chạy: không biến nào, Find-Python tự dò (.venv -> python ->
    python3 -> py). Máy chạy test chắc chắn có một Python — chính nó đang chạy test."""
    moi = {k: v for k, v in os.environ.items() if k != "MARKETING_STUDIO_PY"}
    campaign = _tram(tmp_path, "-Brand ai")
    r = subprocess.run(
        [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(campaign / "run.ps1")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(campaign),
        env=dict(moi, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", MARKETING_STUDIO_HOME=str(GOC)))
    if r.returncode != 0 and "Find-Python" in r.stdout:
        pytest.skip("PATH cua may test khong co python/python3/py: " + r.stdout)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Brand=[ai]" in r.stdout, r.stdout
