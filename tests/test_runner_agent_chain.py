# -*- coding: utf-8 -*-
"""Runner tin đi qua `agent_call` theo `order` (P1-21) và job nặng chạy `Interactive` (P0-10).

Mac mini 01/10/2026:
    · P1-21 — Hot Data 19:00 gọi `claude -p` thô ⇒ hết hạn mức ×3, abort, không đăng; agy (đầu
      `order`) chạy được mà không được hỏi tới.
    · P0-10 — mẫu plist khai `ProcessType=Background` ⇒ macOS hãm CPU + I/O: dựng 10 chương
      mất 5 h 16 thay vì ~40 phút.

Phần PowerShell chạy THẬT `Invoke-AgentCall` (dot-source `brand-paths.ps1`) với engine giả, để
chứng minh đường nối runner → agent_call → chuỗi engine, chứ không chỉ quét chữ.
"""
from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNERS = ROOT / "scripts" / "runners"
BP = RUNNERS / "brand-paths.ps1"
TIN = ("run-toptoday-hot.ps1", "run-weekly-news.ps1", "run-weekly-repo.ps1")
PS = shutil.which("pwsh") or shutil.which("powershell")

# ── P0-10 ───────────────────────────────────────────────────────────────────────────

NANG = ("daily-news-a", "daily-news-b", "daily-story", "weekly-news-a", "weekly-news-b",
        "weekly-repo")
NHE = ("worker", "approve-poller")


def _plist(ten):
    t = (ROOT / "templates" / "launchd" / f"studio.marketing.{ten}.plist").read_text(encoding="utf-8")
    return plistlib.loads(re.sub(r"__[A-Z_]+__", "x", t).encode("utf-8"))


@pytest.mark.parametrize("ten", NANG)
def test_job_NANG_chay_Interactive(ten):
    assert _plist(ten).get("ProcessType") == "Interactive", (
        f"{ten}: Background làm macOS hãm CPU/I/O — dựng video chậm ×8 (P0-10)")


@pytest.mark.parametrize("ten", NHE)
def test_job_NHE_giu_Background(ten):
    assert _plist(ten).get("ProcessType") == "Background"


def test_moi_mau_deu_duoc_xep_loai():
    co = {p.stem.removeprefix("studio.marketing.")
          for p in (ROOT / "templates" / "launchd").glob("*.plist")}
    assert co == set(NANG) | set(NHE), "mẫu mới phải được xếp NANG hay NHE trong test này"


# ── P1-21: quét mã ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ten", TIN)
def test_runner_tin_KHONG_goi_claude_p_tho(ten):
    ma = "\n".join(d for d in (RUNNERS / ten).read_text(encoding="utf-8-sig").splitlines()
                   if not d.lstrip().startswith("#"))
    assert not re.search(r"\|\s*claude\s+-p\b|&\s*claude\b|\bclaude\s+-p\s+--", ma), (
        f"{ten} còn gọi `claude -p` thô — phải đi qua Invoke-AgentCall (P1-21)")
    assert "Invoke-AgentCall" in ma
    i = ma.find("$ac.code -eq 4")
    assert i >= 0 and "exit 4" in ma[i:i + 400], "hết hạn mức phải ra mã 4 (🟡)"


def test_helper_goi_agent_call_theo_order():
    t = BP.read_text(encoding="utf-8-sig")
    khoi = t[t.index("function Invoke-AgentCall"):t.index("function Format-NativeLine")]
    assert "'--engine', 'order'" in khoi and "'--prompt-file'" in khoi
    assert "agent_call.py" in khoi


# ── P1-21: chạy THẬT qua PowerShell ─────────────────────────────────────────────────

SHIM = textwrap.dedent('''
    import json, os, sys
    kb = json.loads(open(sys.argv[1], encoding="utf-8").read())
    data = sys.stdin.read()
    if kb.get("log_stdin"):
        open(kb["log_stdin"], "w", encoding="utf-8").write(data)
    for d in kb.get("stderr", []):
        print(d, file=sys.stderr, flush=True)
    for duong, nd in (kb.get("write") or {}).items():
        open(duong, "w", encoding="utf-8").write(nd)
    print(json.dumps({"result": "OK"}), flush=True)
    sys.exit(kb.get("rc", 0))
''')
QUOTA = {"rc": 1, "stderr": ["You've hit your session limit · resets 9:30pm"]}


def _tram_gia(tmp_path, **engines):
    shim = tmp_path / "shim.py"
    shim.write_text(SHIM, encoding="utf-8")
    cfg = {"version": 1, "order": [f"{e}:best" for e in engines], "engines": {},
           "skill_roots": [], "ledger": str(tmp_path / "so.jsonl")}
    for ten, kb in engines.items():
        f = tmp_path / f"{ten}.json"
        f.write_text(json.dumps(kb), encoding="utf-8")
        cfg["engines"][ten] = {"cmd": [sys.executable, str(shim), str(f)], "best": f"{ten}-m"}
    f_cfg = tmp_path / "engines.json"
    f_cfg.write_text(json.dumps(cfg), encoding="utf-8")
    return f_cfg


def _ps(tmp_path, f_cfg, prompt, expect):
    kich = tmp_path / "goi.ps1"
    kich.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        f". '{BP}'\n"
        f"$p = [System.IO.File]::ReadAllText('{tmp_path / 'prompt.txt'}', [System.Text.Encoding]::UTF8)\n"
        f"$r = Invoke-AgentCall -Python '{sys.executable}' -Prompt $p -Tools 'web,read,write' "
        f"-Cwd '{tmp_path}' -Expect @('{expect}:800') -OnLine {{ param($s) Write-Host ('agent: ' + $s) }}\n"
        "Write-Output ('RC=' + $r.code)\n"
        "if ($r.result) { Write-Output ('ENGINE=' + $r.result.engine) }\n",
        encoding="utf-8-sig")
    (tmp_path / "prompt.txt").write_text(prompt, encoding="utf-8")
    # `brand-paths.ps1` phân giải trạm NGAY khi được nạp và ném nếu không thấy. Checkout sạch
    # (CI) không có trạm nào — máy dev có `~/.marketing` nên không lộ. Trạm giả, tường minh:
    # test không được dựa vào trạm thật của máy đang chạy.
    tram = tmp_path / "tram"
    tram.mkdir(exist_ok=True)
    (tram / "CHANNELS.md").write_text("---\nchannels: []\n---\n", encoding="utf-8")
    env = {**os.environ, "AGENT_CALL_ENGINES": str(f_cfg), "PYTHONUTF8": "1",
           "PYTHONIOENCODING": "utf-8", "MARKETING_STUDIO_DATA": str(tram)}
    r = subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(kich)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    return r, r.stdout + r.stderr


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_Invoke_AgentCall_claude_HET_HAN_MUC_thi_lui_sang_engine_ke_va_giu_tieng_Viet(tmp_path):
    """Đúng cảnh Hot Data 19:00 nếu claude đứng đầu `order`: hết hạn mức ⇒ sang codex, JSON ra."""
    out = tmp_path / "2026-10-01-top.json"
    log = tmp_path / "stdin.txt"
    f_cfg = _tram_gia(tmp_path, claude=QUOTA,
                      codex={"write": {str(out): "x" * 900}, "log_stdin": str(log)})
    prompt = "Nghiên cứu tin nóng hôm nay — tiếng Việt có dấu: ắ ổ ữ đ"
    r, ra = _ps(tmp_path, f_cfg, prompt, out)
    assert "RC=0" in ra and "ENGINE=codex" in ra, ra[-3000:]
    assert out.is_file()
    assert prompt in log.read_text(encoding="utf-8"), "prompt tiếng Việt vỡ trên đường tới engine"
    so = [json.loads(d) for d in (tmp_path / "so.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["engine"] for x in so] == ["claude", "codex"]
    assert not list(tmp_path.glob("tmp*.tmp")), "tệp prompt tạm phải được dọn"


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_Invoke_AgentCall_MOI_engine_het_han_muc_la_ma_4(tmp_path):
    out = tmp_path / "top.json"
    f_cfg = _tram_gia(tmp_path, claude=QUOTA, codex=QUOTA)
    r, ra = _ps(tmp_path, f_cfg, "x", out)
    assert "RC=4" in ra, ra[-3000:]
