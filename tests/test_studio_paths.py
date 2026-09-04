# -*- coding: utf-8 -*-
"""Test cho studio_paths — phân giải 4 tầng.

Điều quan trọng nhất phải giữ: KÊNH NẰM NGOÀI STATION vẫn tìm được. Nếu script dò thư mục
thay vì đọc CHANNELS.md thì kênh ngoài trở nên vô hình, và nó vô hình một cách IM LẶNG —
lệnh chạy xong, chỉ là không thấy kênh đó đâu.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import md_io as M  # noqa: E402
import studio_paths as SP  # noqa: E402


def _dung_cay(tmp_path, path_kenh_ngoai=None):
    """STATION có 1 kênh trong, tuỳ chọn thêm 1 kênh NGOÀI STATION."""
    station = tmp_path / "station"
    (station / "trong-nha").mkdir(parents=True)
    (station / "trong-nha" / "channel.yml").write_text("id: trong-nha\n", encoding="utf-8")
    ds = [{"id": "trong-nha", "label": "Trong nhà", "path": "./trong-nha", "status": "active"}]
    if path_kenh_ngoai:
        path_kenh_ngoai.mkdir(parents=True)
        (path_kenh_ngoai / "channel.yml").write_text("id: ngoai-nha\n", encoding="utf-8")
        ds.append({"id": "ngoai-nha", "label": "Ngoài nhà",
                   "path": str(path_kenh_ngoai).replace("\\", "/"), "status": "active"})
    M.write_fm(station / "CHANNELS.md", {"schema": "channels/1", "channels": ds}, "# Sổ kênh\n")
    return station


def test_tim_duoc_kenh_NGOAI_station(tmp_path):
    """Ca quan trọng nhất: kênh để ở ổ/thư mục khác."""
    ngoai = tmp_path / "noi-khac" / "ngoai-nha"
    station = _dung_cay(tmp_path, ngoai)
    ids = [c["id"] for c in SP.channels(station)]
    assert ids == ["trong-nha", "ngoai-nha"]
    assert SP.channel_dir("ngoai-nha", station) == ngoai.resolve()
    assert ngoai.resolve() not in station.resolve().parents, "kênh này thật sự nằm ngoài STATION"


def test_duong_tuong_doi_tinh_theo_CHANNELS_md(tmp_path):
    station = _dung_cay(tmp_path)
    assert SP.channel_dir("trong-nha", station) == (station / "trong-nha").resolve()


def test_station_rong_khong_phai_loi(tmp_path):
    assert SP.channels(tmp_path / "chua-co-gi") == []


def test_kenh_khong_khai_thi_bao_loi_ro_rang(tmp_path):
    station = _dung_cay(tmp_path)
    with pytest.raises(KeyError, match="CHANNELS"):
        SP.channel_dir("khong-ton-tai", station)


def test_di_len_tim_theo_FILE_MOC_khong_dem_cap(tmp_path):
    """Lồng thêm một cấp thư mục vẫn phải tìm ra — đếm cấp là giả định sẽ sai."""
    d = tmp_path / "k" / "CMP-1" / "BAI-001" / "facebook" / "sau" / "nua"
    d.mkdir(parents=True)
    (tmp_path / "k" / "channel.yml").write_text("id: k\n", encoding="utf-8")
    (tmp_path / "k" / "CMP-1" / "campaign.md").write_text("---\nid: CMP-1\n---\n", encoding="utf-8")
    assert SP.channel_of(d) == (tmp_path / "k").resolve()
    assert SP.campaign_of(d) == (tmp_path / "k" / "CMP-1").resolve()


def test_liet_ke_campaign_va_bai(tmp_path):
    k = tmp_path / "k"
    (k / "CMP-1" / "AST-001_x").mkdir(parents=True)
    (k / "channel.yml").write_text("id: k\n", encoding="utf-8")
    (k / "CMP-1" / "campaign.md").write_text("---\nid: CMP-1\n---\n", encoding="utf-8")
    (k / "CMP-1" / "AST-001_x" / "meta.json").write_text("{}", encoding="utf-8")
    (k / "CMP-1" / "khong-phai-bai").mkdir()          # không có meta.json
    assert [p.name for p in SP.campaigns(k)] == ["CMP-1"]
    assert [p.name for p in SP.posts(k / "CMP-1")] == ["AST-001_x"]


def test_post_id_theo_nen_tang():
    assert SP.post_id("AST-001", "youtube", "youtube_video") == "AST-001-yt"
    assert SP.post_id("AST-001", "facebook", "facebook_post") == "AST-001-fb"
    assert SP.post_id("AST-001", "web_blog", "blog_article") == "AST-001-web"


def test_cap_chua_khai_thi_no_loi_chu_khong_doan():
    with pytest.raises(KeyError, match="HAU_TO"):
        SP.post_id("AST-001", "tiktok", "tiktok_video")
