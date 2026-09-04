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


# Trường campaign.md phải điền xong trước khi đẻ bài. Fixture dưới điền đúng bộ này.
DU_THONG_TIN = {
    "business_problem": "Người làm dữ liệu chưa biết dùng agent vào việc thật",
    "campaign_goal": "300 người đọc hết bài đầu tiên",
    "target_audience": "Analyst 2-5 năm kinh nghiệm, đã dùng Power BI hằng ngày",
    "audience_pain_points": "Đọc tin AI thấy hay nhưng không biết áp vào việc của mình",
    "key_message": "Agent không thay bạn, nó bỏ phần bạn ghét",
    "content_pillar": "ai-agent",
    "channels": ["web_blog"],
    "primary_cta": "Đọc bài dài trên atlas",
}


def _dien_du_campaign(cam_md):
    fm, body = M.read_fm(cam_md)
    fm.update(DU_THONG_TIN)
    M.write_fm(cam_md, fm, body)


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

    # Cổng: campaign.md còn nguyên chữ mẫu thì KHÔNG đẻ bài được.
    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
              "THU-001", "--slug", "a", "--title", "Bài A", "--station", station, mong_doi=2)
    assert "CHƯA ĐỦ THÔNG TIN" in r.stderr and "target_audience" in r.stderr
    assert not (station / "k" / "CMP-2609-t" / "THU-001_a").exists(),         "cổng chặn mà vẫn tạo thư mục là chặn giả"

    _dien_du_campaign(station / "k" / "CMP-2609-t" / "campaign.md")
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


def test_bo_qua_cong_van_tao_duoc_khi_biet_minh_lam_gi(station):
    """Cổng phải có đường vòng CÓ Ý THỨC — nếu không, người ta sẽ sửa script để lách."""
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station)
    _chay(ROOT / "scripts/pipeline/new_campaign.py", "--channel", "k", "--id", "CMP-2609-t",
          "--name", "CD", "--prefix", "THU", "--station", station)
    _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id", "THU-001",
          "--slug", "a", "--title", "Bài A", "--station", station, "--bo-qua-cong")
    assert (station / "k" / "CMP-2609-t" / "THU-001_a" / "meta.json").is_file()


def _cd_san_sang(station):
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station)
    _chay(ROOT / "scripts/pipeline/new_campaign.py", "--channel", "k", "--id", "CMP-2609-t",
          "--name", "CD", "--prefix", "THU", "--station", station)
    _dien_du_campaign(station / "k" / "CMP-2609-t" / "campaign.md")
    return station / "k" / "CMP-2609-t"


def test_bulk_tao_ca_loat(station, tmp_path):
    cam = _cd_san_sang(station)
    tsv = tmp_path / "loat.tsv"
    tsv.write_text(chr(10).join([
        "# id<TAB>slug<TAB>title<TAB>angle".replace("<TAB>", chr(9)),
        chr(9).join(["THU-001", "a", "Bài A", "góc 1"]),
        chr(9).join(["THU-002", "b", "Bài B"]),
    ]) + chr(10), encoding="utf-8")
    _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t",
          "--bulk", tsv, "--station", station)

    assert (cam / "THU-001_a" / "meta.json").is_file()
    assert (cam / "THU-002_b" / "meta.json").is_file()
    dong = M.read_table(M.read_fm(cam / "campaign.md")[1], "CONTENT")[1]
    assert [d["content_id"] for d in dong] == ["THU-001", "THU-002"]
    assert dong[0]["angle"] == "góc 1"
    assert all(d["status"] == "proposed" and d["g1"] == "" for d in dong),         "bulk vẫn phải để Cổng 1 cho người"


def test_bulk_loi_MOT_dong_thi_khong_tao_bai_nao(station, tmp_path):
    """Nửa loạt thành công nửa loạt lỗi là trạng thái khó dọn nhất — kiểm hết rồi mới tạo."""
    cam = _cd_san_sang(station)
    tsv = tmp_path / "loat.tsv"
    tsv.write_text(("THU-001	a	Bài A" + chr(10) +
                    "SAI-002	b	Bài B" + chr(10)), encoding="utf-8")
    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t",
              "--bulk", tsv, "--station", station, mong_doi=2)
    assert "KHÔNG tạo bài nào" in r.stderr and "SAI-002" in r.stderr
    assert not (cam / "THU-001_a").exists(), "dòng hợp lệ đứng trước cũng không được tạo"
