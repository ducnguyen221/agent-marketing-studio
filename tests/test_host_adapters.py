# -*- coding: utf-8 -*-
"""Adapter skill của Claude (`.claude/skills/`) phải khớp skill gốc (`.agents/skills/`).

Skill gốc sửa mà quên sinh lại adapter thì Claude định tuyến theo mô tả cũ; skill gốc xoá mà
adapter còn thì Claude thấy một skill trỏ vào file không có. Cả hai đều im lặng — cổng này
chạy `--check` trên chính bản checkout.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "build_host_adapters.py"


def test_adapter_khop_skill_goc():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(GEN), "--check"], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, ("adapter lệch nguồn — chạy `python scripts/build_host_adapters.py` "
                               "rồi xem diff:\n" + r.stdout + r.stderr)


def test_moi_skill_goc_co_dung_mot_adapter_tro_ve_no():
    goc = sorted(p.parent.name for p in (ROOT / ".agents" / "skills").glob("*/SKILL.md"))
    ad = sorted(p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    assert goc and goc == ad, (goc, ad)
    for ten in ad:
        t = (ROOT / ".claude" / "skills" / ten / "SKILL.md").read_text(encoding="utf-8")
        assert f"../../../.agents/skills/{ten}/SKILL.md" in t


def test_check_bat_duoc_adapter_lech(tmp_path):
    """Cổng-của-cổng: `--check` phải đỏ khi adapter bị sửa tay."""
    import shutil
    goc = tmp_path / "repo"
    (goc / "scripts").mkdir(parents=True)
    shutil.copy2(GEN, goc / "scripts" / GEN.name)
    shutil.copytree(ROOT / ".agents" / "skills", goc / ".agents" / "skills")
    chay = lambda *a: subprocess.run([sys.executable, str(goc / "scripts" / GEN.name), *a],  # noqa: E731
                                     capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert chay("--check").returncode == 1, "chưa sinh adapter mà --check vẫn xanh"
    assert chay().returncode == 0 and chay("--check").returncode == 0
    f = next((goc / ".claude" / "skills").glob("*/SKILL.md"))
    f.write_text(f.read_text(encoding="utf-8") + "\nsửa tay\n", encoding="utf-8", newline="\n")
    assert chay("--check").returncode == 1


def test_doctor_bao_adapter_khop_va_NOT_CHECKED_cho_tung_host(monkeypatch):
    """Doctor đo được adapter; việc host nạp skill thì KHÔNG — phải nói NOT_CHECKED, không xanh."""
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import doctor as DR
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(ROOT))
    so = DR.So()
    DR.kham_host(so, ROOT / "workspace")
    assert so.code == 0 and not so.fail
    assert any("adapter Claude: .claude/skills khớp" in x for x in so.info), so.info
    assert [h for h in DR.HOSTS if any(f"host {h}:" in x for x in so.not_checked)] == list(DR.HOSTS)
