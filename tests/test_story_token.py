# -*- coding: utf-8 -*-
"""P3-12 — token kênh truyện: biến RIÊNG kênh thắng biến chung.

Env plist/tác vụ truyện có thể mang `YT_TOKEN_PATH` của kênh tin. `truyen_publish.py` cũ lấy
`YT_TOKEN_PATH` TRƯỚC `YT_TOKEN_PATH__NGHE_TIEN_TRUYEN` ⇒ chạy tay trong env đó là đăng nhầm
kênh. Lượt thật (`daily_truyen.py`) an toàn vì nó ép `YT_TOKEN_PATH=<token truyện>` cho tiến
trình con — cổng cuối giữ hai bên nói cùng một token.
Không mạng, không token thật: chỉ so ĐƯỜNG (chuỗi), không mở file nào.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "runners" / "story"))
import truyen_paths as TP  # noqa: E402

RIENG, CHUNG = "/tram/token-truyen.json", "/tram/token-tin.json"


def test_bien_rieng_kenh_THANG_bien_chung():
    env = {"YT_TOKEN_PATH__NGHE_TIEN_TRUYEN": RIENG, "YT_TOKEN_PATH": CHUNG}
    assert TP.token_truyen(env, registry=False) == os.path.expanduser(RIENG)


def test_khong_co_bien_rieng_thi_lui_ve_bien_chung_roi_rong():
    assert TP.token_truyen({"YT_TOKEN_PATH": CHUNG}, registry=False) == os.path.expanduser(CHUNG)
    assert TP.token_truyen({"YT_TOKEN_PATH__NGHE_TIEN_TRUYEN": "  "}, registry=False) == ""
    assert TP.token_truyen({}, registry=False) == ""


def test_truyen_publish_mac_dinh_token_qua_ham_chung():
    """`--token` mặc định phải đi qua `token_truyen` — không tự đọc `YT_TOKEN_PATH` trước."""
    src = (ROOT / "scripts" / "runners" / "story" / "truyen_publish.py").read_text(encoding="utf-8")
    assert "DEFAULT_TOKEN = truyen_paths.token_truyen()" in src
    assert 'ap.add_argument("--token", default=DEFAULT_TOKEN' in src
    assert 'os.environ.get("YT_TOKEN_PATH") or' not in src


def test_daily_truyen_ep_dung_token_rieng_cho_buoc_dang():
    """Lượt thật: `daily_truyen` đọc biến RIÊNG kênh và ép nó vào `YT_TOKEN_PATH` của tiến
    trình đăng — cùng token mà `token_truyen` chọn, nên hai đường không lệch nhau."""
    src = (ROOT / "scripts" / "runners" / "story" / "daily_truyen.py").read_text(encoding="utf-8")
    assert 'truyen_paths.getenv("YT_TOKEN_PATH__NGHE_TIEN_TRUYEN")' in src
    assert "env=dict(ENV, YT_TOKEN_PATH=TOKEN_TRUYEN)" in src
