# -*- coding: utf-8 -*-
"""P1-9: `engines.json` là cấu hình THEO MÁY — sổ `ledger` và thứ tự engine không được mang
nguyên sang máy khác.

Mac mini 30/09: gói nhập từ Windows có `ledger: ~/<trạm của máy cũ>/_bench/agent-call.jsonl`
→ lượt truyện đầu tiên sẽ lặng lẽ TẠO một trạm thứ hai trong thư mục nhà của máy mới, và
`order` Claude-trước trái ý người vận hành cho máy đó.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# `lib/` PHẢI đứng trước `pipeline/`: `pipeline/agent_call.py` là CLI mỏng trùng tên.
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import agent_call as AC  # noqa: E402
import station as STATION  # noqa: E402


def test_ledger_TUONG_DOI_tinh_tu_goc_tram(tmp_path):
    p = AC.ledger_path({"ledger": "_bench/x.jsonl"}, station=tmp_path)
    assert p == tmp_path.resolve() / "_bench" / "x.jsonl"


def test_ledger_mac_dinh_nam_trong_tram(tmp_path):
    assert AC.ledger_path({}, station=tmp_path) == tmp_path.resolve() / "_bench" / "agent-call.jsonl"


def test_ledger_TUYET_DOI_ngoai_tram_van_dung_nhung_CANH_BAO(tmp_path, capsys):
    ngoai = tmp_path / "noi-khac" / "so.jsonl"
    tram = tmp_path / "tram"
    tram.mkdir()
    assert AC.ledger_path({"ledger": str(ngoai)}, station=tram) == ngoai
    assert "NGOÀI trạm" in capsys.readouterr().err


def test_ledger_TUYET_DOI_trong_tram_khong_canh_bao(tmp_path, capsys):
    trong = tmp_path / "_bench" / "so.jsonl"
    assert AC.ledger_path({"ledger": str(trong)}, station=tmp_path) == trong
    assert "NGOÀI trạm" not in capsys.readouterr().err


def test_override_thang_cau_hinh(tmp_path):
    assert AC.ledger_path({"ledger": "_bench/a"}, override=str(tmp_path / "o"),
                          station=tmp_path) == tmp_path / "o"


def _eng(d: dict) -> bytes:
    return json.dumps(d).encode("utf-8")


def test_export_doi_ledger_tuyet_doi_trong_tram_thanh_tuong_doi(tmp_path):
    st = tmp_path.resolve()
    ra = json.loads(STATION._engines_cho_may(
        _eng({"ledger": str(st / "_bench" / "a.jsonl"), "order": ["claude"]}), st, None))
    assert ra["ledger"] == "_bench/a.jsonl" and ra["order"] == ["claude"]


def test_export_BO_ledger_ngoai_tram(tmp_path):
    st = (tmp_path / "tram").resolve()
    ra = json.loads(STATION._engines_cho_may(_eng({"ledger": str(tmp_path / "x.jsonl")}), st, None))
    assert "ledger" not in ra


def test_export_for_machine_lay_order_cua_may_dich(tmp_path):
    d = {"order": ["claude", "agy"], "_may_khac": {"mac-mini": {"order": ["agy", "claude"]}}}
    ra = json.loads(STATION._engines_cho_may(_eng(d), tmp_path.resolve(), "mac-mini"))
    assert ra["order"] == ["agy", "claude"]
    ra = json.loads(STATION._engines_cho_may(_eng(d), tmp_path.resolve(), "may-la"))
    assert ra["order"] == ["claude", "agy"], "máy không khai thì giữ nguyên order"


def test_export_json_hong_giu_nguyen_byte(tmp_path):
    assert STATION._engines_cho_may(b"{hong", tmp_path, "x") == b"{hong"
