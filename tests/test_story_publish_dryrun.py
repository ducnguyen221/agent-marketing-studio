# -*- coding: utf-8 -*-
"""P2-21 — `truyen_publish.py --dry-run` không được gọi agent.

Trước 1.1.3, `build()` gọi `gen_hook()` (agent_call → agy/codex/claude, lùi `claude -p`) TRƯỚC
khi xét `--dry-run` ⇒ một lượt "xem trước" vẫn tốn hạn mức và ghi ledger, trái docstring.
Không mạng, không token: `gen_hook` bị thay bằng hàm ghi nhận lần gọi.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "runners" / "story"))


@pytest.fixture
def TPUB(tmp_path, monkeypatch):
    """`truyen_publish` phân giải trạm giọng NGAY lúc import (`truyen_paths.engine_dir()`) và
    thoát khi máy không có trạm (CI). Cấp một trạm giả rồi mới import — không đụng trạm thật."""
    monkeypatch.setenv("OMNIVOICE_DIR", str(tmp_path / "omnivoice"))
    sys.modules.pop("truyen_publish", None)
    mod = importlib.import_module("truyen_publish")
    yield mod
    sys.modules.pop("truyen_publish", None)


@pytest.fixture
def manifest(tmp_path):
    m = tmp_path / "tap.mp3.manifest.json"
    m.write_text(json.dumps({"chapters": [
        {"num": 1, "name": "Mot", "start": 5.0},
        {"num": 2, "name": "Hai", "start": 65.0},
    ]}), encoding="utf-8")
    return m


@pytest.fixture
def goi(TPUB, monkeypatch):
    lan = []

    def gia(chs, cache_dir=None):
        lan.append(len(chs))
        return {"title_hook": "Hook gia", "summary": "Tom tat", "closing": ""}
    monkeypatch.setattr(TPUB, "gen_hook", gia)
    return lan


def test_dry_run_KHONG_goi_agent(TPUB, manifest, goi, capsys):
    assert TPUB.main(["--manifest", str(manifest), "--video", "khong-can.mp4", "--dry-run"]) == 0
    assert goi == [], "dry-run đã gọi agent viết hook"
    ra = capsys.readouterr().out
    assert "bỏ qua (dry-run" in ra and "Chương 1-2" in ra


def test_dry_run_with_hook_thi_goi_agent(TPUB, manifest, goi, capsys):
    assert TPUB.main(["--manifest", str(manifest), "--video", "khong-can.mp4",
                      "--dry-run", "--with-hook"]) == 0
    assert goi == [2]
    assert "Hook gia" in capsys.readouterr().out


def test_build_mac_dinh_van_goi_hook(TPUB, manifest, goi):
    """Lượt đăng thật (`daily_truyen.py` không truyền --dry-run) giữ nguyên hành vi."""
    title, _desc, first, last = TPUB.build(str(manifest))
    assert goi == [2] and "Hook gia" in title and (first, last) == (1, 2)
