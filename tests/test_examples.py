# -*- coding: utf-8 -*-
"""Cổng chống `examples/` trôi khỏi code.

Ví dụ là tài liệu — mà tài liệu lệch code thì tệ hơn không có tài liệu, vì người ta tin nó.
Test này khẳng định thư mục ví dụ vẫn là thứ mà chính các script hiện tại sinh ra và chấp
nhận: `check_tree` xanh, bản HTML sinh lại không đổi, số liệu trong README khớp thực tế.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VD = ROOT / "examples"
KENH = VD / "vi-du-studio"
CAM = KENH / "CMP-2609-gioi-thieu"
BAI = CAM / "GTX-001_vi-sao-agent-can-cong-cua-nguoi"

sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import build_views as BV  # noqa: E402
import check_tree as CT  # noqa: E402
import md_io as M  # noqa: E402

PY = sys.executable
# Dòng chân trang mang giờ sinh — bỏ ra khi so, nếu không test đỏ mỗi phút.
GIO = re.compile(r"lúc \d{2}/\d{2}/\d{4} \d{2}:\d{2}")


def test_cay_vi_du_KHONG_do():
    s = CT.chay(VD)
    assert s.do == [], f"ví dụ mà cây gãy thì người đọc học sai: {s.do}"


def test_hai_nhac_dung_la_hai_bai_chua_dang():
    """README nói 'sẽ báo 2 nhắc'. Số đó phải đúng, không phải xấp xỉ."""
    nhac = CT.chay(VD).canh_bao
    assert len(nhac) == 2 and all("chưa có publish.json" in x for x in nhac)
    assert any("GTX-002" in x for x in nhac) and any("GTX-003" in x for x in nhac)


def test_ba_bai_dung_ba_trang_thai_nhu_README():
    _, dong = M.read_table(M.read_fm(CAM / "campaign.md")[1], "CONTENT")
    assert {d["content_id"]: d["status"] for d in dong} == {
        "GTX-001": "published", "GTX-002": "approved", "GTX-003": "proposed"}


def test_bai_da_dang_co_URL_that_trong_bang():
    d = [x for x in M.read_table(M.read_fm(CAM / "campaign.md")[1], "CONTENT")[1]
         if x["content_id"] == "GTX-001"][0]
    for cot in ("web", "youtube", "facebook"):
        assert d[cot].startswith("http"), f"cột {cot} phải có URL — đây là chỗ mở lại bài"


def test_moi_URL_trong_vi_du_deu_la_ten_mien_VI_DU():
    """Ví dụ không được trỏ vào địa chỉ thật của ai — kể cả của chính mình."""
    from urllib.parse import urlparse
    # So theo TÊN MIỀN. So chuỗi con thì `https://evil.com/?r=example.vn` lọt — một bộ lọc
    # an ninh dùng `in` là bộ lọc mở.
    mien_ok = {"example.vn", "www.example.vn", "youtu.be", "www.facebook.com",
               "fonts.googleapis.com", "fonts.gstatic.com"}
    for f in (list(VD.rglob("*.md")) + list(VD.rglob("*.json")) + list(VD.rglob("*.txt"))
              + list(VD.rglob("*.yml")) + list(VD.rglob("*.html"))):
        for m in re.finditer(r"https?://[^\s\"'()<>]+", f.read_text(encoding="utf-8")):
            mien = urlparse(m.group()).netloc
            assert mien in mien_ok,                 f"{f.relative_to(VD)}: URL ngoài danh sách ví dụ: {m.group()} (miền {mien})"


def test_HTML_sinh_lai_KHONG_doi():
    """Ví dụ đi kèm bản HTML dựng sẵn để xem ngay. Nó phải là thứ code HIỆN TẠI sinh ra."""
    cu = GIO.sub("", (CAM / "campaign.html").read_text(encoding="utf-8"))
    moi = GIO.sub("", BV.html_campaign(BV.doc_campaign(CAM)))
    assert cu == moi, "campaign.html đã trôi — chạy build_views.py --station ./examples"

    kenhs = [BV.doc_kenh(k) for k in __import__("studio_paths").channels(VD)]
    cu = GIO.sub("", (VD / "index.html").read_text(encoding="utf-8"))
    assert cu == GIO.sub("", BV.html_index(kenhs, VD.name, VD)), \
        "index.html đã trôi — chạy build_views.py --station ./examples"


def test_file_dem_dang_khop_content_md(tmp_path):
    """atlas/blog.md, youtube/, facebook/ là thứ sinh ra từ content.md — không sửa tay.

    So với ĐẦU RA THẬT của `write_outputs`, không so với `split_content`: chỗ bỏ dấu ngắt
    `---` nằm ở write_outputs, nên so với bán thành phẩm là test một hình dạng không tồn tại.
    """
    import gen_article as GA
    GA.write_outputs(GA.split_content((BAI / "content.md").read_text(encoding="utf-8")),
                     str(tmp_path))
    # Đường dẫn lấy từ chính LAYOUT — chép tay thì lệch, và cái `continue` cũ đã che đúng
    # lỗi đó suốt: file so sánh không tồn tại nên test bỏ qua rồi báo xanh.
    import post_paths as PP
    for khoa in ("blog", "yt_desc", "fb_post", "fb_comment"):
        ten = PP.LAYOUT[khoa]
        moi, cu = tmp_path / ten, BAI / ten
        assert moi.is_file(), f"gen_article không còn sinh ra {ten} — neo đã đổi?"
        assert cu.is_file(), f"ví dụ thiếu {ten}"
        a, b = moi.read_text(encoding="utf-8"), cu.read_text(encoding="utf-8")
        if "{{" in a:
            # File này có placeholder URL, và bản trong ví dụ đã được `register_publish set`
            # thay bằng link thật. So phần NGOÀI placeholder — bỏ qua cả file là tự miễn:
            # gen_article ngừng sinh file cũng vẫn xanh.
            kh = re.compile(r"\{\{[A-Z_]+\}\}|https?://\S+")
            assert kh.sub("§", a) == kh.sub("§", b),                 f"{ten} lệch content.md ở phần ngoài link"
            continue
        assert a == b, f"{ten} lệch content.md — chạy lại gen_article.py"
    blog = (BAI / "atlas" / "blog.md").read_text(encoding="utf-8")
    assert not blog.lstrip().startswith(">"), "hướng dẫn của mẫu lọt vào bản đăng"


def test_publish_json_va_bang_Content_noi_cung_mot_URL():
    pj = json.loads((BAI / "publish.json").read_text(encoding="utf-8"))
    tu_pj = {p["channel"]: p["publish"]["link"] for p in pj["posts"]}
    d = [x for x in M.read_table(M.read_fm(CAM / "campaign.md")[1], "CONTENT")[1]
         if x["content_id"] == "GTX-001"][0]
    assert d["web"] == tu_pj["web_blog"]
    assert d["youtube"] == tu_pj["youtube"]
    assert d["facebook"] == tu_pj["facebook"]


def test_campaign_vi_du_DU_thong_tin_de_tao_bai():
    """Ví dụ phải qua được chính cổng mà nó dạy người ta."""
    import new_post
    fm, _ = M.read_fm(CAM / "campaign.md")
    assert new_post._campaign_da_du(fm) == []


def test_khong_con_chu_mau_o_nhung_cho_DA_DIEN():
    """Bài CHƯA viết (GTX-002/003) giữ nguyên chữ mẫu — đó chính là thứ ví dụ muốn cho thấy.

    Chỉ những file đã điền mới bị soi: hồ sơ kênh, chiến dịch, và bài đã đăng.
    """
    da_dien = ([KENH / "channel.yml", KENH / "profile.md", CAM / "campaign.md",
                VD / "CHANNELS.md", KENH / "CAMPAIGNS.md", VD / "README.md"]
               + [p for p in BAI.rglob("*.md")])
    cho_phep = {"{{BLOG_URL}}", "{{YOUTUBE_URL}}"}
    for f in da_dien:
        la = [m.group() for m in re.finditer(r"\{\{[^}]*\}\}", f.read_text(encoding="utf-8"))
              if m.group() not in cho_phep]
        assert not la, f"{f.relative_to(VD)}: còn chữ mẫu {la}"


def test_bai_CHUA_viet_van_giu_nguyen_mau():
    """Mặt kia của cùng một luật: GTX-003 phải còn nguyên khung, nếu không ví dụ mất ý."""
    t = (CAM / "GTX-003_vi-sao-bo-excel-lam-nguon" / "content.md").read_text(encoding="utf-8")
    assert "{{" in t, "bài ở trạng thái proposed phải còn là khung mẫu"


def test_publish_json_vi_du_DU_KHOA_nhu_code_sinh():
    """Ví dụ là tài liệu — người ta chép hình dạng của nó. Trước 05/09 hai file JSON của ví dụ
    viết TAY nên lệch thứ `register_publish` sinh ra (`review.at` thay vì `approved_at`,
    thiếu 6 khoá), và người chép theo tạo ra dữ liệu mà `export_excel` đọc không ra.
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import register_publish as RP

    khung = RP._khung("X-001-web", "X-001", "web_blog", "blog_article", {})
    that = json.loads((BAI / "publish.json").read_text(encoding="utf-8"))["posts"][0]
    thieu = [k for k in khung if k not in that]
    assert not thieu, f"publish.json của ví dụ thiếu khoá {thieu} so với _khung()"
    assert "approved_at" in that["review"], "dấu vết Cổng 2 phải có approved_at"
    assert that["review"].get("approved_by"), "phải ghi ai duyệt"


def test_continuity_vi_du_dung_khoa_ma_B0_doc():
    cont = json.loads((KENH / "continuity.json").read_text(encoding="utf-8"))
    assert cont and isinstance(cont, list)
    for k in ("post_id", "slug", "title", "url", "published_at"):
        assert k in cont[0], f"continuity.json thiếu khoá {k} mà register_publish ghi"


def test_Excel_vi_du_KHONG_bo_trong_cot_trang_thai():
    """Excel là bản xuất chính thức. Ô trống ở đây nói 'chưa qua cổng kỹ thuật' — nói dối."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import export_excel as EX
    import md_io as _M

    _, dong = _M.read_table(_M.read_fm(CAM / "campaign.md")[1], "CONTENT")
    hang = EX._dong_post(CAM, dong)
    assert hang, "phải có dòng Post cho bài đã đăng"
    for o in hang:
        for c in ("quality_check", "agent_status", "post_status", "review_status",
                  "publish_status", "publish_link", "updated_at"):
            assert o[c], f"{o['post_id']}: cột {c} rỗng dù publish.json có dữ liệu"
