# -*- coding: utf-8 -*-
"""Cổng P1-24: rào render TRƯỚC các bước tốn kém của ba runner tin.

Mac mini 02/10/2026: Hot AI 18:00 hỏng sau 42 phút — `Navigation timeout` ở frame 0, môi
trường macOS kẹt, khởi động lại máy là hết. Runner chỉ biết sau agent + TTS. Ba thứ phải đúng:

* thứ tự: phép thử nằm SAU các kiểm rẻ (nhịp, nhạc nền) và TRƯỚC nghiên cứu + render;
* `Invoke-RenderPreflight` dịch mã của `video-studio probe` sang mã runner: kẹt/hỏng ⇒ 5,
  thiếu công cụ ⇒ 3, video-studio cũ chưa có `probe` ⇒ nhắc rồi đi tiếp;
* tin Telegram (cả `compose_report` lẫn định dạng dự phòng của `notify_run`) nói "khởi động
  lại máy rồi chạy lại".

Phần PowerShell chạy thật (pwsh hoặc Windows PowerShell 5.1) với một gói `video_studio` GIẢ
trên PYTHONPATH — không Node, không HyperFrames.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNERS = ROOT / "scripts" / "runners"
BP = RUNNERS / "brand-paths.ps1"
TIN = ("run-toptoday-hot.ps1", "run-weekly-news.ps1", "run-weekly-repo.ps1")
PS = shutil.which("pwsh") or shutil.which("powershell")
sys.path.insert(0, str(RUNNERS))


def _doc(ten):
    return (RUNNERS / ten).read_text(encoding="utf-8-sig")


def _vi_tri(t, mau):
    m = re.search(mau, t, re.M)
    assert m, f"không thấy {mau!r}"
    return m.start()


@pytest.mark.parametrize("ten", TIN)
def test_phep_thu_SAU_kiem_re_TRUOC_nghien_cuu_va_render(ten):
    t = _doc(ten)
    pf = _vi_tri(t, r"^\$pf = Invoke-RenderPreflight -Python \$ovpy")
    assert _vi_tri(t, r"Resolve-ForcedBgm -Cfg") < pf, "kiểm nhạc nền (rẻ hơn) đi trước"
    assert pf < _vi_tri(t, r"Invoke-AgentCall -Python"), "phép thử phải TRƯỚC bước nghiên cứu"
    # Render: hai runner deep-dive qua Invoke-TopstoryRender; bản tuần gọi module dựng media
    # của video-studio (`$ma = @($media + …)`).
    assert pf < _vi_tri(t, r"Invoke-TopstoryRender -Python|^\$ma = @\(\$media"), "và trước render"
    assert re.search(r"if \(\$pf -ne 0\) \{ Log '=== (run )?failed ==='; exit \$pf \}", t)


def test_hot_news_phep_thu_SAU_nhip_2_ngay():
    """Ngày lệch nhịp thoát 0 sau 0 s — không được tốn một lượt render thử."""
    t = _doc("run-toptoday-hot.ps1")
    assert _vi_tri(t, r"Test-Cadence -Date") < _vi_tri(t, r"^\$pf = Invoke-RenderPreflight")


# ── Invoke-RenderPreflight chạy thật với video_studio giả ─────────────────────

GIA = r'''
import json, os, sys
argv = sys.argv[1:]
open(os.environ["FAKE_ARGV"], "w", encoding="utf-8").write(json.dumps(argv))
mode = os.environ.get("FAKE_PROBE", "ok")
if argv[:1] != ["probe"]:
    sys.exit(9)
if mode == "old":
    print("lệnh lạ: 'probe'", file=sys.stderr); sys.exit(2)
if mode == "ok":
    print("[probe] render thử OK sau 7.2s", file=sys.stderr)
    print(json.dumps({"ok": True, "seconds": 7.2, "hyperframes": "0.8.54"})); sys.exit(0)
err = {"stuck": "RENDER_STUCK: môi trường render kẹt — khởi động lại máy rồi chạy lại",
       "fail": "render thử hỏng (mã 1) — chạy `video-studio doctor --hf`",
       "missing": "không thấy `npx` (Node ≥ 22)"}[mode]
code = 3 if mode == "missing" else 1
print(f"[probe] LỖI ({code}): {err}", file=sys.stderr)
print(json.dumps({"ok": False, "code": code, "error": err}, ensure_ascii=False)); sys.exit(code)
'''


def _preflight(tmp_path, mode, timeout_env=None):
    goi = tmp_path / "gia" / "video_studio"
    goi.mkdir(parents=True, exist_ok=True)
    (goi / "__init__.py").write_text("", encoding="utf-8")
    (goi / "__main__.py").write_text(GIA, encoding="utf-8")
    tram = tmp_path / "tram"
    tram.mkdir(exist_ok=True)
    (tram / "CHANNELS.md").write_text("---\nchannels: []\n---\n", encoding="utf-8")
    kich = tmp_path / "goi.ps1"
    kich.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        f". '{BP}'\n"
        f"$rc = Invoke-RenderPreflight -Python '{sys.executable}' "
        "-OnLine { param($l) Write-Host ('L: ' + $l) }\n"
        "Write-Output ('RC=' + $rc)\n", encoding="utf-8-sig")
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "gia"), "PYTHONUTF8": "1",
           "PYTHONIOENCODING": "utf-8", "MARKETING_STUDIO_DATA": str(tram),
           "FAKE_PROBE": mode, "FAKE_ARGV": str(tmp_path / "argv.json")}
    env.pop("RENDER_PROBE_TIMEOUT", None)
    if timeout_env:
        env["RENDER_PROBE_TIMEOUT"] = timeout_env
    r = subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(kich)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=180)
    ra = r.stdout + r.stderr
    rc = re.findall(r"RC=(\S+)", r.stdout)
    assert rc, ra[-3000:]
    return int(rc[-1]), ra, json.loads((tmp_path / "argv.json").read_text(encoding="utf-8"))


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_on_thi_di_tiep_va_goi_probe_tran_30s(tmp_path):
    rc, ra, argv = _preflight(tmp_path, "ok")
    assert rc == 0, ra[-2000:]
    assert argv == ["probe", "--timeout", "30", "--json"]
    assert "RENDER_PREFLIGHT=ok" in ra


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_ket_thi_ma_5_va_noi_khoi_dong_lai_may(tmp_path):
    rc, ra, _ = _preflight(tmp_path, "stuck")
    assert rc == 5, ra[-2000:]
    assert "RENDER_PREFLIGHT=stuck" in ra
    assert "khoi dong lai may roi chay lai" in ra


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_hong_kieu_khac_van_ma_5_nhung_KHONG_goi_la_ket(tmp_path):
    rc, ra, _ = _preflight(tmp_path, "fail")
    assert rc == 5 and "RENDER_PREFLIGHT=failed" in ra and "doctor --hf" in ra


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_thieu_npx_la_ma_3(tmp_path):
    rc, ra, _ = _preflight(tmp_path, "missing")
    assert rc == 3 and "RENDER_PREFLIGHT=missing" in ra


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_video_studio_cu_chua_co_probe_thi_nhac_roi_di_tiep(tmp_path):
    rc, ra, _ = _preflight(tmp_path, "old")
    assert rc == 0 and "can >= 0.2.5" in ra


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_RENDER_PROBE_TIMEOUT_doi_tran_de_GIA_LAP_may_ket(tmp_path):
    """Mac nghiệm thu: đặt RENDER_PROBE_TIMEOUT=1 ⇒ phép thử thật quá giờ ⇒ đúng nhánh ❌."""
    _rc, _ra, argv = _preflight(tmp_path, "ok", timeout_env="1")
    assert argv == ["probe", "--timeout", "1", "--json"]


# ── tin Telegram ───────────────────────────────────────────────────────────────

def test_compose_report_ma_5_ket_noi_khoi_dong_lai():
    import compose_report as CR
    log = ("=== Daily HOT AI start ===\nRender preflight: video-studio probe (tran 30s) ...\n"
           "probe: [probe] LỖI (1): RENDER_STUCK: môi trường render kẹt\n"
           "ERROR: moi truong render ket (HyperFrames khong mo duoc trang) - khoi dong lai may roi chay lai.\n"
           "RENDER_PREFLIGHT=stuck\n=== failed ===")
    msg = CR.build("Daily Hot AI", 5, "00:00:31", log)
    assert msg.startswith("❌")
    assert "MÔI TRƯỜNG RENDER KẸT (HyperFrames không mở được trang)" in msg
    assert "khởi động lại máy rồi chạy lại" in msg


def test_compose_report_navigation_timeout_khi_render_HONG():
    import compose_report as CR
    log = "  ! HyperFrames render hỏng: page.goto: Navigation timeout of 60000 ms exceeded\n"
    assert "RENDER KẸT" in CR.build("T", 1, "00:42:00", log)
    assert "RENDER KẸT" not in CR.build("T", 0, "00:42:00", log), \
        "lần thử sau qua thì lượt ✅ không được mang cảnh báo kẹt"


def test_compose_report_ke_luot_tu_chay_tiep():
    import compose_report as CR
    log = ("[resume] ⏳ quá trần 30600s — chạy tiếp MỘT lần từ chương 310\n"
           "RESUME_ONCE=start from=310 range=301-310\nRESUME_ONCE=done code=0\n"
           "PUBLISHED https://youtu.be/oIcyFy0zcVI\n")
    msg = CR.build("Truyện · p2", 0, "09:56:00", log)
    assert "tự chạy tiếp MỘT lần từ chương 310 (dải 301-310)" in msg


def test_notify_run_du_phong_ma_5_noi_khoi_dong_lai():
    import notify_run as NR
    msg = NR.soan_tin("Daily Hot AI", 5, "00:00:31", ["RENDER_PREFLIGHT=stuck"], [], None)
    assert "MÔI TRƯỜNG RENDER KẸT" in msg and "khởi động lại" in msg and "exit 5" in msg
