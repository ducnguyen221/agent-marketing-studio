# -*- coding: utf-8 -*-
"""Cổng của `topstory_spec.py` — file ghép spec cho `video-studio render --project topstory`.

Spec sai kiểu nào cũng vẫn là JSON hợp lệ, nên nó không hỏng ở chỗ ghép mà hỏng ở VIDEO:
thương hiệu của kênh khác, không có nhạc nền, ảnh tương đối trỏ vào hư không. Các test dưới
đây canh đúng những kiểu đó, không cần GPU hay engine giọng.

Chạy:  python -m pytest tests/test_runner_topstory_spec.py -q
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "runners")
sys.path.insert(0, ENGINE)
import topstory_spec as ts  # noqa: E402

CFG_AI = {
    "topstory_brand_a": "Daily Demo", "topstory_brand_b": "News",
    "topstory_site": "example.com", "topstory_kicker": "HOT",
    "pronounce": {r"example\.com": "ví dụ chấm com"},
}
TOP = {
    "date": "sai-ngay", "display_date": "Thứ Hai · 28/09/2026", "bgm": "lofi",
    "top_story": {"headline": "H", "sections": [{"title": "s1", "media": [{"src": "a.png"}]}]},
    "verdict": "v", "voice": {"profile": "khong-duoc-lot-vao"},
}


def test_ghep_du_bon_khoi_hop_dong():
    s = ts.dung_spec(TOP, CFG_AI, "2026-09-28", "p1", "news-corporate", "0.10")
    assert s["schema_version"] == 1
    assert s["brand"] == {"a": "Daily Demo", "b": "News", "site": "example.com",
                          "kicker": "HOT", "pronounce": {r"example\.com": "ví dụ chấm com"}}
    assert s["voice"] == {"profile": "p1"}
    assert s["bgm"] == {"style": "news-corporate", "volume": 0.10}
    assert s["outputs"] == {"long": True, "short": True}


def test_noi_dung_giu_nguyen_khoa_hop_dong_do_runner_quyet():
    s = ts.dung_spec(TOP, CFG_AI, "2026-09-28", "p1", "none", None)
    # Nội dung đi nguyên vẹn …
    assert s["top_story"] == TOP["top_story"] and s["verdict"] == "v"
    assert s["display_date"] == TOP["display_date"]
    # … nhưng `date` là của runner, còn `bgm`/`voice` trong -top.json chỉ là gợi ý.
    assert s["date"] == "2026-09-28"
    assert s["bgm"] == "none"
    assert s["voice"] == {"profile": "p1"}


def test_accent_tu_chuoi_phay():
    cfg = dict(CFG_AI, topstory_accents="#111, #222,#333")
    assert ts.dung_spec(TOP, cfg, "2026-09-28")["brand"]["accent"] == ["#111", "#222", "#333"]


@pytest.mark.parametrize("thieu", ["topstory_brand_a", "topstory_brand_b", "topstory_site"])
def test_thieu_thuong_hieu_la_loi_khong_lui_ve_ten_ai(thieu):
    cfg = {k: v for k, v in CFG_AI.items() if k != thieu}
    with pytest.raises(ts.Loi) as e:
        ts.dung_spec(TOP, cfg, "2026-09-28")
    assert "identity" in str(e.value)


def test_pronounce_sai_kieu_bi_chan():
    with pytest.raises(ts.Loi):
        ts.dung_spec(TOP, dict(CFG_AI, pronounce=["x"]), "2026-09-28")


def test_cli_ghi_file_va_ma_thoat(tmp_path):
    top = tmp_path / "2026-09-28-top.json"
    cfg = tmp_path / "config.json"
    out = tmp_path / "2026-09-28-spec.json"
    top.write_text(json.dumps(TOP, ensure_ascii=False), encoding="utf-8")
    cfg.write_text(json.dumps(CFG_AI, ensure_ascii=False), encoding="utf-8")
    assert ts.main(["--top", str(top), "--config", str(cfg), "--date", "2026-09-28",
                    "--profile", "p1", "--bgm", "lofi", "--bgm-volume", "0.1",
                    "--out", str(out)]) == 0
    s = json.loads(out.read_text(encoding="utf-8"))
    assert s["brand"]["a"] == "Daily Demo" and s["bgm"]["style"] == "lofi"
    # Thiếu thương hiệu -> mã 2, KHÔNG ghi file.
    cfg.write_text("{}", encoding="utf-8")
    out2 = tmp_path / "x.json"
    assert ts.main(["--top", str(top), "--config", str(cfg), "--date", "2026-09-28",
                    "--out", str(out2)]) == 2
    assert not out2.exists()
