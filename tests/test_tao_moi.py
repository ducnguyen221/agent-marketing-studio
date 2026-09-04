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
    "content_pillar": "tru-cot-1",   # phải nằm trong pillars của channel.yml — cổng kiểm thật
    "channels": ["web_blog"],
    "primary_cta": "traffic",   # enum, không phải câu văn xuôi
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


def test_content_id_trung_thi_TU_CHOI_chu_khong_xoa_Cong_1(station):
    """Lỗi thật (Fable 05/09): chỉ kiểm THƯ MỤC nên `--id THU-001 --slug b` ghi đè dòng đã
    `approved` về `proposed` với g1 rỗng — máy xoá quyết định của người, không báo."""
    cam = _cd_san_sang(station)
    _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
          "THU-001", "--slug", "a", "--title", "Bài A", "--station", station)

    # người duyệt Cổng 1
    fm, body = M.read_fm(cam / "campaign.md")
    body = M.upsert_row(body, "CONTENT", "content_id",
                        {"content_id": "THU-001", "status": "approved", "g1": "2026-09-05"})
    M.write_fm(cam / "campaign.md", fm, body)

    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
              "THU-001", "--slug", "b", "--title", "Bài A lần 2", "--station", station,
              mong_doi=2)
    assert "đã có trong bảng Content" in r.stderr

    d = M.read_table(M.read_fm(cam / "campaign.md")[1], "CONTENT")[1][0]
    assert d["status"] == "approved" and d["g1"] == "2026-09-05", \
        "quyết định của NGƯỜI ở Cổng 1 không được phép bị máy ghi đè"
    assert not (cam / "THU-001_b").exists()


def test_bulk_cung_TU_CHOI_id_da_co_trong_bang(station, tmp_path):
    cam = _cd_san_sang(station)
    _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
          "THU-001", "--slug", "a", "--title", "Bài A", "--station", station)
    tsv = tmp_path / "loat.tsv"
    tsv.write_text(chr(9).join(["THU-001", "khac", "Trùng id"]) + chr(10), encoding="utf-8")
    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t",
              "--bulk", tsv, "--station", station, mong_doi=2)
    assert "đã có trong bảng Content" in r.stderr


def test_cong_bat_MOI_truong_van_xuoi_con_nguyen_mau(station):
    """Cổng cũ so với chuỗi chép tay nên chỉ bắt 3: `campaign_goal: "Kết quả mong muốn, đo
    được"` lọt qua và bài vẫn đẻ ra từ chiến dịch rỗng. Nay so với CHÍNH template.

    Sáu trường văn xuôi phải bị bắt. `channels`/`primary_cta` thì KHÔNG — mẫu chọn sẵn một
    giá trị hợp lệ, nên trùng mẫu là câu trả lời thật (test dưới kiểm chiều còn lại).
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import new_post

    fm, _ = M.read_fm(ROOT / "templates" / "campaign.md")
    bat = {x.split()[0].split("=")[0] for x in new_post._campaign_da_du(fm)}
    van_xuoi = [k for k in new_post.BAT_BUOC if k not in new_post.CHON_TU_DANH_SACH]
    assert set(van_xuoi) <= bat, f"lọt trường văn xuôi: {set(van_xuoi) - bat}"
    assert "content_pillar" in bat, "pillar mẫu ('tru-cot') không phải trụ thật"

    du = dict(fm, **DU_THONG_TIN)
    assert new_post._campaign_da_du(du, ["tru-cot-1", "tru-cot-2"]) == [], \
        "điền đủ rồi mà vẫn chặn = cổng kêu oan, và cổng kêu oan thì người ta tắt cổng"


def test_channels_va_cta_RONG_thi_van_bi_bat(station):
    """Chiều còn lại: chúng được miễn so-với-mẫu, KHÔNG được miễn kiểm rỗng."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import new_post

    fm, _ = M.read_fm(ROOT / "templates" / "campaign.md")
    du = dict(fm, **DU_THONG_TIN)
    for k in ("channels", "primary_cta"):
        thieu = new_post._campaign_da_du(dict(du, **{k: [] if k == "channels" else ""}),
                                         ["tru-cot-1", "tru-cot-2"])
        assert thieu == [k], f"{k} rỗng phải bị bắt, đang: {thieu}"


def test_pillar_ngoai_danh_sach_cua_kenh_thi_CHAN(station):
    cam = _cd_san_sang(station)
    fm, body = M.read_fm(cam / "campaign.md")
    fm["content_pillar"] = "khong-co-trong-kenh"
    M.write_fm(cam / "campaign.md", fm, body)
    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
              "THU-001", "--slug", "a", "--title", "X", "--station", station, mong_doi=2)
    assert "không có trong pillars của kênh" in r.stderr


def test_platforms_thuc_su_LOC_chu_khong_bi_bo_qua(station):
    """Codex chỉ ra 05/09: `--platforms` khai ra nhưng KHÔNG được đọc — người dùng gõ
    `--platforms web_blog` rồi nhận về channel.yml đủ ba nền tảng, không ai báo.
    Cờ khai ra mà không làm gì tệ hơn không có cờ: nó nói dối về việc mình đã làm."""
    _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
          "--path", "./k", "--station", station, "--platforms", "web_blog,facebook")
    t = (station / "k" / "channel.yml").read_text(encoding="utf-8")
    assert "- channel: web_blog" in t and "- channel: facebook" in t
    assert "- channel: youtube" not in t, "nền tảng không chọn phải bị bỏ"
    assert "kpi_default:" in t and "# ⚠️ Số ở đây phải đến từ" in t, \
        "lọc không được ăn mất phần còn lại của file, và phải giữ chú thích"


def test_platforms_gia_tri_la_thi_TU_CHOI(station):
    r = _chay(ROOT / "scripts/pipeline/new_channel.py", "--id", "k", "--label", "K",
              "--path", "./k", "--station", station, "--platforms", "tiktok", mong_doi=2)
    assert "giá trị lạ" in r.stderr and "tiktok" in r.stderr
    assert not (station / "k").exists() or not (station / "k" / "channel.yml").exists()


def test_primary_cta_phai_la_ENUM_khong_phai_cau_van(station):
    """Codex 05/09: không kiểm enum thì "Đọc bài dài trên atlas" cũng lọt, và cột này mất
    tác dụng phân loại ngay từ bài đầu tiên."""
    cam = _cd_san_sang(station)
    fm, body = M.read_fm(cam / "campaign.md")
    fm["primary_cta"] = "Đọc bài dài trên atlas"
    M.write_fm(cam / "campaign.md", fm, body)
    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
              "THU-001", "--slug", "a", "--title", "X", "--station", station, mong_doi=2)
    assert "primary_cta" in r.stderr and "không hợp lệ" in r.stderr


def test_channels_phai_la_TAP_CON_cua_platforms_kenh(station):
    """Chiến dịch khai đăng YouTube trong khi kênh chưa khai nền tảng đó = post mồ côi
    ngay từ `register_publish init`."""
    cam = _cd_san_sang(station)
    fm, body = M.read_fm(cam / "campaign.md")
    fm["channels"] = ["web_blog", "youtube"]
    M.write_fm(cam / "campaign.md", fm, body)
    # kênh chỉ khai web_blog
    yml = (station / "k" / "channel.yml").read_text(encoding="utf-8")
    i = yml.index("  - channel: youtube")
    j = yml.index("  - channel: facebook")
    (station / "k" / "channel.yml").write_text(yml[:i] + yml[j:], encoding="utf-8")

    r = _chay(ROOT / "scripts/pipeline/new_post.py", "--campaign", "CMP-2609-t", "--id",
              "THU-001", "--slug", "a", "--title", "X", "--station", station, mong_doi=2)
    assert "youtube" in r.stderr and "platforms của kênh" in r.stderr
