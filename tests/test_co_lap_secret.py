# -*- coding: utf-8 -*-
"""P1-18 — bộ test không bao giờ chạm con trỏ secret của máy đang chạy.

Mac mini 30/09: `.env` của bản clone chạy lịch điền con trỏ thật → `pytest` trần đỏ 5 ca, một
assert in ra mẩu cấu hình Telegram thật, và `notify_run.py` chạy như tiến trình con đọc được
`TG_CONFIG` thật. Chốt nằm ở `tests/conftest.py::_khong_cham_secret_that` + biến
`studio_paths.BIEN_CHAN_ENV_FILE`. File này giữ cho chốt không bị gỡ im lặng.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import studio_paths as SP  # noqa: E402


def _repo_embedded(goc: Path, env_text: str) -> Path:
    goc.mkdir(parents=True)
    (goc / SP.LOCAL_CONFIG).write_text(json.dumps({"mode": "embedded"}), encoding="utf-8")
    (goc / ".env").write_text(env_text, encoding="utf-8")
    return goc


def test_fixture_go_sach_con_tro_va_chan_env_cua_repo_that():
    assert not [t for t in os.environ if SP.la_con_tro_bi_mat(t) or t.startswith("TG_")]
    assert Path(os.environ[SP.BIEN_CHAN_ENV_FILE]).resolve() == ROOT.resolve()


def test_env_cua_repo_BI_CHAN_thi_khong_doc(tmp_path, monkeypatch):
    r = _repo_embedded(tmp_path / "r", "TG_CONFIG=/that/config.json\n")
    monkeypatch.setenv(SP.BIEN_CHAN_ENV_FILE, str(r))
    assert SP.env_file(r) is None
    assert SP.secret_env("TG_CONFIG", r) is None


def test_env_cua_repo_KHAC_van_doc_binh_thuong(tmp_path):
    """Chốt chỉ nhắm bản clone đang test — repo giả trong thư mục tạm vẫn là đối tượng test."""
    r = _repo_embedded(tmp_path / "r", "TG_CONFIG=/gia/config.json\n")
    assert SP.secret_env("TG_CONFIG", r) == "/gia/config.json"


def test_tien_trinh_con_KE_THUA_chot(tmp_path):
    """Tiến trình con nhận môi trường của test ⇒ chốt đi theo; nó cũng không thấy `.env`."""
    r = _repo_embedded(tmp_path / "r", "TG_CONFIG=/that/config.json\n")
    env = dict(os.environ, **{SP.BIEN_CHAN_ENV_FILE: str(r)})
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import studio_paths as SP; "
            "print(SP.secret_env('TG_CONFIG', sys.argv[2]))")
    ra = subprocess.run([sys.executable, "-c", code, str(ROOT / "scripts" / "lib"), str(r)],
                        capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
    assert ra.returncode == 0, ra.stderr
    assert ra.stdout.strip() == "None"
