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


def _eng_hai_may() -> dict:
    return {
        "_may": {"ten": "may-nguon", "nen_tang": "win32", "_doc": ["rieng may nay"]},
        "order": ["claude:opus", "agy:x"],
        "_order_ly_do": ["ly do cua Windows"],
        "_may_khac": {"_doc": ["ghi chu"],
                      "mac-mini": {"order": ["agy:x", "claude:opus"], "nen_tang": "darwin",
                                   "_ly_do": ["ly do cua Mac"]}},
        "ledger": "_bench/agent-call.jsonl",
    }


def test_export_for_machine_lam_du_BA_viec_runbook(tmp_path):
    """P1-17: gói cho máy X phải dùng được ngay — không còn tên/lý do/thứ tự máy nguồn ở
    chỗ của máy X, và thứ tự mỗi máy xuất hiện đúng một lần (RUNBOOK-DOI-MAY §5)."""
    ra = json.loads(STATION._engines_cho_may(_eng(_eng_hai_may()), tmp_path.resolve(), "mac-mini"))
    assert ra["_may"] == {"ten": "mac-mini", "nen_tang": "darwin", "_doc": ["rieng may nay"]}
    assert ra["order"] == ["agy:x", "claude:opus"]
    assert ra["_order_ly_do"] == ["ly do cua Mac"]
    assert "mac-mini" not in ra["_may_khac"]
    assert ra["_may_khac"]["may-nguon"] == {
        "order": ["claude:opus", "agy:x"], "nen_tang": "win32", "_ly_do": ["ly do cua Windows"]}
    assert ra["_may_khac"]["_doc"] == ["ghi chu"]
    assert list(ra)[:3] == ["_may", "order", "_order_ly_do"], "giữ thứ tự khoá cho người đọc"


def test_export_for_machine_khong_khai_nen_tang_thi_BO(tmp_path):
    d = _eng_hai_may()
    del d["_may_khac"]["mac-mini"]["nen_tang"]
    ra = json.loads(STATION._engines_cho_may(_eng(d), tmp_path.resolve(), "mac-mini"))
    assert "nen_tang" not in ra["_may"], "export không đoán hệ điều hành máy đích"


def test_export_for_machine_KHONG_khai_order_thi_giu_nguyen_order(tmp_path):
    ra = json.loads(STATION._engines_cho_may(_eng(_eng_hai_may()), tmp_path.resolve(), "may-la"))
    assert ra["order"] == ["claude:opus", "agy:x"]
    assert ra["_order_ly_do"] == ["ly do cua Windows"]
    assert set(ra["_may_khac"]) == {"_doc", "mac-mini"}, "không thêm mục máy nguồn trùng order"
    assert ra["_may"]["ten"] == "may-la" and "nen_tang" not in ra["_may"]


def test_export_khong_for_machine_khong_dung_vao_may(tmp_path):
    ra = json.loads(STATION._engines_cho_may(_eng(_eng_hai_may()), tmp_path.resolve(), None))
    assert ra["_may"]["ten"] == "may-nguon" and "mac-mini" in ra["_may_khac"]


def test_export_json_hong_giu_nguyen_byte(tmp_path):
    assert STATION._engines_cho_may(b"{hong", tmp_path, "x") == b"{hong"
