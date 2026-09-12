# -*- coding: utf-8 -*-
"""Bước `dung-trang` — B5 tiếng/hình · B6 dựng trang · B8 đăng web.

Đây là bước ĐẦU TIÊN đẩy chữ ra ngoài Internet. Hỏng ở đây thì hoặc trang lên sống mà ta
tưởng chưa, hoặc ngược lại — và cả hai đều tệ theo cách khó sửa.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import campaign_step as CS  # noqa: E402
import md_io                # noqa: E402

FM = """---
schema: campaign/1
id: CD-THU
channel: kenh-thu
id_prefix: T
name: Thử
status: active
content_pillar: ai-agent
runtime:
  label: Thử
---

# Thử

<!-- CONTENT:BEGIN -->
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | schedule | published | folder | web |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | Bài một | ai-agent | explainer | awareness | high | approved | 2026-09-01 | 2026-09-02 | 2026-09-15 |  | ./T-001_bai |  |
<!-- CONTENT:END -->
"""


def _cam(tmp_path, *, runtime_them=""):
    kenh = tmp_path / "tram" / "kenh-thu"
    cam = kenh / "CD-THU"
    (cam / "logs").mkdir(parents=True)
    (kenh / "channel.yml").write_text(
        "schema: channel/1\nid: kenh-thu\nlabel: \"K\"\nautonomy: suggest\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8", newline="\n")
    fm = FM.replace("  label: Thử\n", "  label: Thử\n" + runtime_them)
    (cam / "campaign.md").write_text(fm, encoding="utf-8", newline="\n")

    bai = cam / "T-001_bai"
    (bai / "atlas").mkdir(parents=True)
    (bai / "atlas" / "blog.md").write_text("# Tiêu đề\n\nThân bài.\n",
                                           encoding="utf-8", newline="\n")
    (bai / "meta.json").write_text(json.dumps({"post_id": "T-001", "title": "Bài một",
                                               "slug": "bai-mot", "category": "ai"}),
                                   encoding="utf-8", newline="\n")
    return cam


def _bang(cam):
    _, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in dong}


def _chay_gia(cam, *, url="https://x.vn/atlas/content/ai/bai-mot", dung_html=True):
    """Giả cả build lẫn publish. Ghi lại lệnh đã gọi."""
    goi = []

    def chay(lenh, **kw):
        goi.append(lenh)
        t = " ".join(str(x) for x in lenh)

        class R:
            returncode = 0
            stderr = ""
            stdout = ""
        if "build_blog_html" in t and dung_html:
            i = lenh.index("--out")
            Path(lenh[i + 1]).parent.mkdir(parents=True, exist_ok=True)
            Path(lenh[i + 1]).write_text("<html>bài</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t:
            R.stdout = json.dumps({"blog_url": url, "http": 200})
        return R()
    chay.goi = goi
    return chay


# ── đường chạy bình thường ──────────────────────────────────────────────────

def test_build_page_ghi_URL_that_vao_cot_web(tmp_path):
    """Cột `web` là thứ `pipeline_state` đọc để biết bài đã lên trang chưa.

    Không ghi vào đó thì bước sau tưởng chưa đăng và sẽ đăng lại — mỗi lượt một lần nữa.
    """
    cam = _cam(tmp_path)
    c = _chay_gia(cam)
    kq = CS.buoc_dung_trang(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 1, kq
    assert _bang(cam)["T-001"]["web"] == "https://x.vn/atlas/content/ai/bai-mot"


def test_goi_dung_thu_tu_dung_trang_roi_moi_dang(tmp_path):
    """Đăng trước khi dựng là đẩy lên một trang chưa tồn tại."""
    cam = _cam(tmp_path)
    c = _chay_gia(cam)
    CS.buoc_dung_trang(cam, bot=None, chay=c)
    thu_tu = [("build_blog_html" in " ".join(map(str, l))) for l in c.goi]
    assert thu_tu[0] is True, f"lệnh đầu không phải dựng trang: {c.goi[0]}"
    assert any("web_publish" in " ".join(map(str, l)) for l in c.goi)


# ── audio là TUỲ CHỌN ───────────────────────────────────────────────────────

def test_KHONG_khai_audio_cmd_thi_BO_QUA_chu_khong_hong(tmp_path):
    """Quy trình không giả định chiến dịch nào cũng có tiếng.

    Chiến dịch chỉ có web + ảnh + post phải chạy trót lọt mà không cần khai gì thêm.
    """
    cam = _cam(tmp_path)                       # KHÔNG khai audio_cmd
    c = _chay_gia(cam)
    kq = CS.buoc_dung_trang(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 1
    # Khẳng định đúng CỜ, đừng dò chuỗi "audio" trong cả dòng lệnh: `tmp_path` của pytest
    # mang tên hàm test, mà tên hàm này có chữ "audio" ⇒ dò chuỗi sẽ tự bắt nhầm chính nó.
    assert not any("--audio-src" in l for l in c.goi), c.goi


def test_CO_khai_audio_cmd_thi_chay_va_NHUNG_vao_trang(tmp_path):
    cam = _cam(tmp_path, runtime_them='  audio_cmd: \'lam-tieng --bai "{bai}"\'\n')
    bai = cam / "T-001_bai"

    def chay(lenh, **kw):
        t = " ".join(str(x) for x in lenh)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "lam-tieng" in t:
            (bai / "atlas" / "audio.mp3").write_bytes(b"ID3fake")
        if "build_blog_html" in t:
            i = lenh.index("--out")
            Path(lenh[i + 1]).write_text("<html>x</html>", encoding="utf-8", newline="\n")
            chay.co_audio_src = "--audio-src" in lenh
        if "web_publish" in t:
            R.stdout = json.dumps({"blog_url": "https://x.vn/a/b", "http": 200})
        return R()
    chay.co_audio_src = False

    kq = CS.buoc_dung_trang(cam, bot=None, chay=chay)
    assert kq["xu_ly"] == 1
    assert chay.co_audio_src, "dựng audio xong mà không nhúng vào trang"


# ── fail-closed ─────────────────────────────────────────────────────────────

def test_build_page_KHONG_ra_html_thi_la_HONG_du_ma_thoat_0(tmp_path):
    """Mã thoát 0 không đủ để tính là xong — luật đã có của repo, áp cả ở đây.

    Bộ dựng chạy êm mà không ra file thì đăng lên sẽ là một trang rỗng.
    """
    cam = _cam(tmp_path)
    c = _chay_gia(cam, dung_html=False)        # báo OK nhưng KHÔNG ghi file
    kq = CS.buoc_dung_trang(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 0 and kq["hong"], kq
    assert not any("web_publish" in " ".join(map(str, l)) for l in c.goi), \
        "đã đem đăng một trang chưa dựng được"


def test_dang_web_khong_tra_URL_thi_KHONG_ghi_cot_web(tmp_path):
    """Không có URL nghĩa là không biết bài nằm đâu — ghi bừa là nói dối cái bảng."""
    cam = _cam(tmp_path)

    def chay(lenh, **kw):
        t = " ".join(str(x) for x in lenh)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "build_blog_html" in t:
            i = lenh.index("--out")
            Path(lenh[i + 1]).write_text("<html>x</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t:
            R.stdout = json.dumps({"http": 200})        # THIẾU blog_url
        return R()

    kq = CS.buoc_dung_trang(cam, bot=None, chay=chay)
    assert kq["xu_ly"] == 0 and kq["hong"]
    assert _bang(cam)["T-001"]["web"] == ""


def test_bai_CHUA_qua_cong_2_thi_khong_dung(tmp_path):
    """Cổng 2 là chỗ người quyết bài có đáng dựng không. Vượt qua nó là vô hiệu hoá cổng."""
    cam = _cam(tmp_path)
    than_cu = (cam / "campaign.md").read_text(encoding="utf-8")
    (cam / "campaign.md").write_text(
        than_cu.replace("| 2026-09-01 | 2026-09-02 |", "| 2026-09-01 |  |"),
        encoding="utf-8", newline="\n")
    c = _chay_gia(cam)
    kq = CS.buoc_dung_trang(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 0 and c.goi == []


def test_bai_DA_len_web_thi_khong_dang_lai(tmp_path):
    """Idempotent: chạy lại không được đăng chồng."""
    cam = _cam(tmp_path)
    than_cu = (cam / "campaign.md").read_text(encoding="utf-8")
    (cam / "campaign.md").write_text(
        than_cu.replace("| ./T-001_bai |  |", "| ./T-001_bai | https://x.vn/da-co |"),
        encoding="utf-8", newline="\n")
    c = _chay_gia(cam)
    assert CS.buoc_dung_trang(cam, bot=None, chay=c)["xu_ly"] == 0
    assert c.goi == []


def test_chi_bai_gioi_han_dung_mot_bai(tmp_path):
    cam = _cam(tmp_path)
    c = _chay_gia(cam)
    kq = CS.buoc_dung_trang(cam, bot=None, chay=c, chi_bai="T-999")
    assert kq["xu_ly"] == 0 and c.goi == []
