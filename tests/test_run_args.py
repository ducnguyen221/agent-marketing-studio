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
import shutil
import subprocess
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


def _tram(tmp_path: Path, runner_args: str, probe: str = PROBE) -> Path:
    """Dựng trạm tối thiểu 1 kênh + 1 chiến dịch, trả về thư mục chiến dịch."""
    cam = tmp_path / "kenh-thu" / "cd-thu"
    cam.mkdir(parents=True)
    (cam.parent / "channel.yml").write_text(
        'schema: channel/1\nid: kenh-thu\nlabel: "Kênh thử"\n'
        "platforms:\n  - channel: youtube\n    post_formats: [youtube_video]\n",
        encoding="utf-8")
    (cam / "campaign.md").write_text(
        "---\nschema: campaign/1\nid: cd-thu\nchannel: kenh-thu\n"
        'runtime:\n  label: "Nhãn thử"\n  runner: probe.ps1\n'
        f'  runner_args: "{runner_args}"\n---\n\nThân bài.\n', encoding="utf-8")
    (cam / "probe.ps1").write_text(probe, encoding="utf-8-sig")

    # `run.ps1` trỏ cứng tới `campaign_cfg.py` qua $env:USERPROFILE. Test phải chạy được
    # trên BẢN CLONE ở đường dẫn bất kỳ, nên trỏ lại vào repo đang kiểm. Chỉ đổi đúng
    # dòng đó — phần đang được kiểm (ghép đối số) giữ nguyên từng byte.
    goc = MAU.read_text(encoding="utf-8-sig")
    cfgpy = (GOC / "scripts" / "pipeline" / "campaign_cfg.py").as_posix()
    dau, _, duoi = goc.partition("$cfgpy  = ")
    assert duoi, "run.ps1 doi cach dat $cfgpy — sua lai test cho khop"
    goc = dau + "$cfgpy  = '" + cfgpy + "'\n" + duoi.split("\n", 1)[1]
    (cam / "run.ps1").write_text(goc, encoding="utf-8-sig")
    return cam


def _chay(cam: Path, *them: str):
    moi = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return subprocess.run(
        [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cam / "run.ps1"), *them],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cam), env=moi)


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
