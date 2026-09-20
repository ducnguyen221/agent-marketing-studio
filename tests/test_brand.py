# -*- coding: utf-8 -*-
"""Danh tính đến từ CẤU HÌNH KÊNH, không từ mã nguồn — và thiếu thì DỪNG.

Ba loại khẳng định, thiếu loại nào cũng để lọt một kiểu hỏng:

  1. Phân giải đúng thứ tự (`--brand` → đi ngược lên `channel.yml`).
  2. Thiếu khoá bắt buộc → dừng với mã 2, KHÔNG dựng ra file nào. Đây là phần quan
     trọng nhất: bản cũ có giá trị mặc định là danh tính thật, nên "thiếu cấu hình"
     và "cấu hình đúng" cho ra hai trang trông y hệt nhau — sai mà không ai thấy.
  3. HTML dựng ra thật sự mang giá trị của cấu hình, không mang gì khác.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import brand as BR  # noqa: E402
import build_blog_html as BH  # noqa: E402

DU = {"site_name": "Site Thử", "author": "Tác Giả Thử", "site_base": "https://thu.example/blog"}


def _kenh(d: Path, brand=None, them=""):
    """Dựng một cây kênh tối thiểu: <d>/channel.yml + <d>/cd/bai/meta.json."""
    import yaml
    d.mkdir(parents=True, exist_ok=True)
    cfg = {"schema": "channel/1", "id": d.name}
    if brand is not None:
        cfg["brand"] = brand
    (d / "channel.yml").write_text(yaml.safe_dump(cfg, allow_unicode=True) + them,
                                   encoding="utf-8")
    bai = d / "cd" / "bai"
    bai.mkdir(parents=True)
    (bai / "meta.json").write_text(json.dumps({"slug": "x", "pillar": "ai-agent"}),
                                   encoding="utf-8")
    return bai


# ───────────────────────────────────────────────── 1. phân giải

def test_di_nguoc_len_tim_channel_yml(tmp_path):
    bai = _kenh(tmp_path / "k", DU)
    assert BR.doc(tu=bai / "meta.json")["site_name"] == "Site Thử"


def test_co_brand_thang_channel_yml(tmp_path):
    bai = _kenh(tmp_path / "k", DU)
    rieng = tmp_path / "rieng.json"
    rieng.write_text(json.dumps({**DU, "site_name": "Khai Thẳng"}), encoding="utf-8")
    assert BR.doc(rieng, tu=bai / "meta.json")["site_name"] == "Khai Thẳng"


def test_brand_tro_file_khong_co_that_thi_DUNG(tmp_path):
    with pytest.raises(BR.BrandThieu, match="không có thật"):
        BR.doc(tmp_path / "khong-ton-tai.json")


def test_home_domain_suy_tu_site_base_khi_khong_khai(tmp_path):
    assert BR.home_domain(DU) == "thu.example"
    assert BR.home_domain({**DU, "home_domain": "khac.example"}) == "khac.example"


def test_org_names_nhan_ca_chuoi_va_danh_sach():
    assert BR.org_names({"org_names": "A, B"}) == ["A", "B"]
    assert BR.org_names({"org_names": ["A", " B "]}) == ["A", "B"]
    assert BR.org_names({}) == []


# ───────────────────────────────────────────────── 2. fail-closed

def test_khong_co_channel_yml_thi_DUNG(tmp_path):
    (tmp_path / "le.json").write_text("{}", encoding="utf-8")
    with pytest.raises(BR.BrandThieu, match="channel.yml"):
        BR.doc(tu=tmp_path / "le.json")


@pytest.mark.parametrize("bo", BR.KHOA_BAT_BUOC)
def test_thieu_tung_khoa_bat_buoc_thi_DUNG(tmp_path, bo):
    thieu = {k: v for k, v in DU.items() if k != bo}
    bai = _kenh(tmp_path / "k", thieu)
    with pytest.raises(BR.BrandThieu, match=bo):
        BR.doc(tu=bai / "meta.json")


def test_khong_co_khoi_brand_thi_DUNG(tmp_path):
    bai = _kenh(tmp_path / "k", None)
    with pytest.raises(BR.BrandThieu):
        BR.doc(tu=bai / "meta.json")


def test_CLI_build_blog_html_thieu_brand_tra_MA_2_va_khong_ghi_file(tmp_path):
    """Mã thoát nói lên điều gì đó chỉ khi nó khác 0 — và file đích phải KHÔNG ra đời."""
    bai = _kenh(tmp_path / "k", None)
    (bai / "blog.md").write_text("# Tiêu đề\n\nnội dung.\n", encoding="utf-8")
    ra = bai / "atlas.html"
    ma = BH.main(["--blog-md", str(bai / "blog.md"), "--meta", str(bai / "meta.json"),
                  "--out", str(ra)])
    assert ma == 2
    assert not ra.exists(), "dựng hỏng mà vẫn để lại file = lần chạy sau tưởng đã xong"


def test_CLI_chay_that_ngoai_cay_tram_tra_MA_2(tmp_path):
    """Chạy `python build_blog_html.py` ở một thư mục lẻ: không có kênh nào để hỏi."""
    (tmp_path / "blog.md").write_text("# T\n\nx\n", encoding="utf-8")
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "build_blog_html.py"),
                        "--blog-md", str(tmp_path / "blog.md"),
                        "--meta", str(tmp_path / "meta.json"),
                        "--out", str(tmp_path / "a.html")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "channel.yml" in (r.stderr or "")


# ───────────────────────────────────────────────── 3. HTML mang đúng cấu hình

def _dung(brand):
    return BH.build_html_full("# Tiêu đề\n\nMột đoạn.\n",
                              {"slug": "bai", "pillar": "ai-agent", "angle": "góc nhìn"},
                              "", brand=brand)


def test_html_mang_dung_gia_tri_cau_hinh():
    h = _dung({**DU, "a": "Nửa", "b": "Sau", "footer": "Chân trang",
               "author_title": "Một dòng", "home_url": "https://nha.example",
               "author_avatar": "https://nha.example/a.png",
               "socials": [{"icon": "youtube", "url": "https://yt.example/@x",
                            "label": "YouTube"}]})
    assert "<title>Tiêu đề · Site Thử</title>" in h
    assert '<meta property="og:site_name" content="Site Thử">' in h
    assert '<meta name="author" content="Tác Giả Thử">' in h
    assert 'href="https://thu.example/blog/"' in h          # topbar về trang gốc
    assert "<h1>Nửa <span>Sau</span></h1><p>Chân trang</p>" in h
    assert '<h3 id="author-name">Tác Giả Thử</h3>' in h
    assert "Một dòng. Trang cá nhân tại" in h
    assert 'href="https://nha.example" target="_blank" rel="noopener">nha.example</a>' in h
    assert 'src="https://nha.example/a.png"' in h
    assert h.count('class="social-btn"') == 1
    assert "https://thu.example/blog/content/ai/bai.html" in h   # canonical + og:url


def test_html_khong_khai_them_gi_thi_khong_de_lai_o_trong():
    """Khai tối thiểu: không có ảnh đại diện, không có nút mạng xã hội, và trang vẫn
    không chứa khối rỗng — ô trống trông như trang hỏng."""
    h = _dung(DU)
    assert '<div class="author-avatar">' not in h   # tên lớp vẫn còn trong CSS, khối thì không
    assert '<nav class="social-grid"' not in h
    assert "<h1>Site Thử</h1>" in h


def test_build_html_full_thieu_brand_NEM_LOI():
    with pytest.raises(BR.BrandThieu):
        _dung({"site_name": "chỉ có tên"})


def test_icon_la_thi_DUNG():
    """Cấu hình chọn biểu tượng không có trong kho → dừng, không vẽ nút rỗng."""
    with pytest.raises(BR.BrandThieu, match="không có trong kho"):
        _dung({**DU, "socials": [{"icon": "tiktok-chua-co", "url": "https://x.example"}]})


def test_social_thieu_url_thi_DUNG():
    with pytest.raises(BR.BrandThieu, match="socials"):
        _dung({**DU, "socials": [{"icon": "website"}]})


# ───────────────────────────────────────────────── 4. cây ví dụ trong repo

def test_kenh_vi_du_khai_du_khoa_bat_buoc():
    """`examples/` là bộ ví dụ chạy được — nếu nó thiếu brand thì tài liệu nói một đằng,
    repo làm một nẻo."""
    b = BR.doc(ROOT / "examples" / "example-studio" / "channel.yml")
    assert all(b.get(k) for k in BR.KHOA_BAT_BUOC)
    assert BR.socials(b), "ví dụ phải cho thấy `socials` khai thế nào"


def test_khuon_channel_yml_co_DU_khoa_de_dien():
    """Khuôn phải LIỆT KÊ đủ khoá — thiếu dòng nào thì người dùng không biết là có nó."""
    import yaml
    d = yaml.safe_load((ROOT / "templates" / "station" / "_channel" / "channel.yml")
                       .read_text(encoding="utf-8"))
    co = set(d["brand"])
    thieu = [k for k in BR.KHOA_BAT_BUOC + BR.KHOA_TUY_CHON if k not in co]
    assert thieu == [], f"khuôn channel.yml chưa có dòng cho: {thieu}"
