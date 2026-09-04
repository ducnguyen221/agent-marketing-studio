# -*- coding: utf-8 -*-
"""Test cho ba script tạo: new_channel · new_campaign · new_post.

Ba điều quan trọng nhất phải giữ:
1. `new_channel.py` KHÔNG tự đoán chỗ lưu kênh — thiếu --path là exit 3 kèm câu hỏi.
   Chỗ lưu là quyết định của người; agent đoán hộ rồi tạo cây thư mục ở chỗ người dùng
   không ngờ tới là bắt họ đi dọn.
2. Script KHÔNG tự đặt `approved`. Cổng 1 là của người — ô `g1` phải rỗng khi mới tạo.
3. Kênh nằm trong STATION thì `path` ghi TƯƠNG ĐỐI, để chép STATION sang máy khác vẫn chạy.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import md_io as M  # noqa: E402

PY = sys.executable


def _chay(*a, mong_doi=0):
    r = subprocess.run([PY, *[str(x) for x in a]], capture_output=True, text=True,
                       encoding="utf-8", cwd=ROOT)
    assert r.returncode == mong_doi, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    return r


@pytest.fixture
def station(tmp_path):
    return tmp_path / "station"


def test_thieu_path_thi_HOI_chu_khong_doan(station):
    r = _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
              "--station", station, mong_doi=3)
    assert "HỎI NGƯỜI DÙNG" in r.stderr
    assert not station.exists(), "chưa hỏi xong mà đã tạo thư mục là sai"


def test_kenh_trong_station_ghi_duong_TUONG_DOI(station):
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station)
    fm, _ = M.read_fm(station / "CHANNELS.md")
    assert fm["channels"][0]["path"] == "./k", \
        "kênh trong STATION phải ghi đường tương đối, nếu không chép STATION sang máy khác là chết"


def test_kenh_NGOAI_station_ghi_duong_tuyet_doi(tmp_path):
    station, ngoai = tmp_path / "station", tmp_path / "cho-khac" / "k2"
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k2", "--label", "K2",
          "--path", ngoai, "--station", station)
    fm, _ = M.read_fm(station / "CHANNELS.md")
    p = fm["channels"][0]["path"]
    assert Path(p).is_absolute() and (Path(p) / "channel.yml").is_file()


def test_chuoi_day_du_va_KHONG_tu_dat_approved(station):
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station)
    _chay(ROOT / "scripts/pipeline/new_campaign.py", "--channel", "k", "--id", "CMP-2609-t",
          "--name", "CD", "--prefix", "THU", "--station", station)
    _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id", "THU-001",
          "--slug", "a", "--title", "Bài A", "--station", station)

    bai = station / "k" / "CMP-2609-t" / "THU-001_a"
    assert sorted(x.name for x in bai.iterdir() if x.is_dir()) == ["atlas", "facebook", "youtube"]
    for f in ("meta.json", "research.md", "content.md"):
        assert (bai / f).is_file()

    _, body = M.read_fm(station / "k" / "CMP-2609-t" / "campaign.md")
    dong = M.read_table(body, "CONTENT")[1][0]
    assert dong["status"] == "proposed"
    assert dong["g1"] == "" and dong["g2"] == "", \
        "Cổng 1 và 2 là của NGƯỜI — script không được tự đặt"
    assert dong["folder"] == "./THU-001_a/"


def test_khong_ghi_de_thu_muc_da_co(station):
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station)
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station, mong_doi=2)


def test_id_sai_dinh_dang_thi_tu_choi(station):
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station)
    # id chiến dịch không đúng CMP-YYMM-slug
    _chay(ROOT / "scripts/pipeline/new_campaign.py", "--channel", "k", "--id", "linh-tinh",
          "--name", "X", "--prefix", "THU", "--station", station, mong_doi=2)
    # prefix không phải chữ HOA
    _chay(ROOT / "scripts/pipeline/new_campaign.py", "--channel", "k", "--id", "CMP-2609-t",
          "--name", "X", "--prefix", "thu", "--station", station, mong_doi=2)


def test_kenh_chua_khai_thi_tu_choi(station):
    _chay(ROOT / "scripts/pipeline/new_campaign.py", "--channel", "khong-co", "--id",
          "CMP-2609-t", "--name", "X", "--prefix", "THU", "--station", station, mong_doi=2)
