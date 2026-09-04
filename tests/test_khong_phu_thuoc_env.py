# -*- coding: utf-8 -*-
"""Script phải chạy đúng trên MÁY SẠCH — không có PYTHONUTF8, không PYTHONIOENCODING.

`conftest.py` đặt hai biến đó cho mọi tiến trình con, nên nếu chỉ có nó thì bộ test đang
tự tạo một thế giới dễ chịu mà người clone repo về không có. File này gỡ SẠCH hai biến,
đúng như máy vừa cài Python, và khẳng định script vẫn ghi được tiếng Việt ra stderr.

Đã trả giá: bộ test xanh suốt trong khi `pytest` trên máy sạch đỏ 6 test.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

ENTRY = sorted(p for p in (ROOT / "scripts" / "pipeline").glob("*.py")
               if "sys.stdout.reconfigure" in p.read_text(encoding="utf-8"))


def _may_sach():
    e = dict(os.environ)
    e.pop("PYTHONUTF8", None)
    e.pop("PYTHONIOENCODING", None)
    return e


def test_co_entrypoint_de_kiem():
    assert len(ENTRY) >= 10, "không tìm thấy entrypoint nào — regex hỏng?"


@pytest.mark.parametrize("script", ENTRY, ids=lambda p: p.name)
def test_moi_entrypoint_ep_ca_stdout_VA_stderr(script):
    """stdout thôi là chưa đủ: thông báo lỗi và câu hỏi cho người dùng đi qua STDERR."""
    t = script.read_text(encoding="utf-8")
    assert "sys.stderr.reconfigure(encoding=" in t, \
        f"{script.name} ép stdout nhưng bỏ quên stderr"


def test_thong_bao_tieng_Viet_ra_stderr_doc_duoc_tren_may_sach():
    """new_channel thiếu --path in ra câu hỏi bằng tiếng Việt — trên stderr."""
    r = subprocess.run([PY, str(ROOT / "scripts/pipeline/new_channel.py"),
                        "--id", "k", "--label", "K"],
                       capture_output=True, text=True, encoding="utf-8", env=_may_sach())
    assert r.returncode == 3
    assert r.stderr is not None, "stderr decode hỏng — script chưa ép utf-8"
    assert "HỎI NGƯỜI DÙNG" in r.stderr
    assert "→" in r.stderr, "ký tự ngoài cp1252 phải qua được"


def test_cong_campaign_bao_loi_doc_duoc_tren_may_sach(tmp_path):
    """Thông báo của cổng dài và nhiều dấu — chỗ dễ vỡ nhất."""
    import shutil
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import md_io as M
    S, K, C = tmp_path / "st", tmp_path / "st" / "k", tmp_path / "st" / "k" / "CMP-2609-t"
    C.mkdir(parents=True)
    M.write_fm(S / "CHANNELS.md", {"schema": "channels/1", "channels": [
        {"id": "k", "label": "K", "path": "./k", "status": "active"}]}, "# Sổ\n")
    (K / "channel.yml").write_text("schema: channel/1\nid: k\n", encoding="utf-8")
    shutil.copy2(ROOT / "templates" / "campaign.md", C / "campaign.md")

    r = subprocess.run([PY, str(ROOT / "scripts/pipeline/new_post.py"),
                        "--campaign", "CMP-2609-t", "--id", "THU-001", "--slug", "a",
                        "--title", "Bài A", "--station", str(S)],
                       capture_output=True, text=True, encoding="utf-8", env=_may_sach())
    assert r.returncode == 2
    assert r.stderr is not None and "CHƯA ĐỦ THÔNG TIN" in r.stderr
    assert "·" in r.stderr, "dấu chấm giữa (·) phải qua được cp1252"
