# -*- coding: utf-8 -*-
"""Bước `phat-hanh` — B7 YouTube · B9 Facebook · B10 ghi sổ.

Bước CUỐI của đường ống, và là bước duy nhất đẩy bài ra các nền tảng ngoài. Sai ở đây thì
hoặc đăng trùng, hoặc báo đã đăng trong khi chưa, và cả hai đều chỉ lộ ra khi đã muộn.
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
| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 | schedule | published | folder | web | youtube | facebook |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | Bài một | ai-agent | explainer | awareness | high | approved | 2026-09-01 | 2026-09-02 | 2026-09-15 |  | ./T-001_bai | https://x.vn/bai-mot |  |  |
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
    (cam / "campaign.md").write_text(
        FM.replace("  label: Thử\n", "  label: Thử\n" + runtime_them),
        encoding="utf-8", newline="\n")
    (cam / "T-001_bai" / "atlas").mkdir(parents=True)
    return cam


def _bang(cam):
    _, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in dong}


def _chay_gia(**ra):
    """`ra` map: chuỗi-nhận-dạng-lệnh -> stdout JSON."""
    goi = []

    def chay(lenh, **kw):
        goi.append(lenh)
        t = " ".join(str(x) for x in lenh)

        class R:
            returncode, stdout, stderr = 0, "", ""
        for khoa, gt in ra.items():
            if khoa in t:
                R.stdout = json.dumps(gt)
        return R()
    chay.goi = goi
    return chay


# ── chiến dịch CHỈ CÓ WEB ───────────────────────────────────────────────────

def test_khong_khai_kenh_nao_thi_ghi_published_va_XONG(tmp_path):
    """Chiến dịch chỉ có web: bài lên trang RỒI là đã phát hành.

    Bắt khai YouTube/Facebook mới cho đánh dấu xong là ép mọi chiến dịch phải có video.
    """
    cam = _cam(tmp_path)
    c = _chay_gia()
    kq = CS.buoc_phat_hanh(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 1, kq
    assert _bang(cam)["T-001"]["published"] != ""
    assert c.goi == [], f"không khai kênh nào mà vẫn gọi lệnh: {c.goi}"


# ── có kênh ngoài ───────────────────────────────────────────────────────────

def test_khai_youtube_thi_chay_va_ghi_link(tmp_path):
    cam = _cam(tmp_path, runtime_them='  youtube_cmd: \'len-yt --bai "{bai}"\'\n')
    c = _chay_gia(**{"len-yt": {"url": "https://youtu.be/abc"}})
    kq = CS.buoc_phat_hanh(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 1
    assert _bang(cam)["T-001"]["youtube"] == "https://youtu.be/abc"


def test_khai_facebook_thi_chay_va_ghi_link(tmp_path):
    cam = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --bai "{bai}"\'\n')
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/1"}})
    CS.buoc_phat_hanh(cam, bot=None, chay=c)
    assert _bang(cam)["T-001"]["facebook"] == "https://fb.com/1"


def test_kenh_HONG_thi_KHONG_danh_dau_da_dang(tmp_path):
    """Báo đã phát hành trong khi chưa là cách hỏng tệ nhất: không ai đi kiểm lại.

    Bài sẽ nằm im mãi mãi ở trạng thái "xong" mà thật ra chưa lên kênh nào.
    """
    cam = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --bai "{bai}"\'\n')

    def chay(lenh, **kw):
        class R:
            returncode, stdout, stderr = 1, "", "token hết hạn"
        return R()

    kq = CS.buoc_phat_hanh(cam, bot=None, chay=chay)
    assert kq["xu_ly"] == 0 and kq["hong"], kq
    assert _bang(cam)["T-001"]["published"] == "", "đánh dấu đã đăng trong khi kênh hỏng"


def test_kenh_chay_EM_nhung_khong_tra_link_van_la_HONG(tmp_path):
    """Mã thoát 0 không đủ để tính là xong — luật cũ của repo, áp cả ở đây."""
    cam = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --bai "{bai}"\'\n')
    c = _chay_gia(**{"len-fb": {"ok": True}})          # THIẾU url
    kq = CS.buoc_phat_hanh(cam, bot=None, chay=c)
    assert kq["xu_ly"] == 0 and kq["hong"]
    assert _bang(cam)["T-001"]["published"] == ""


# ── điều kiện vào bước ──────────────────────────────────────────────────────

def test_CHUA_len_web_thi_khong_phat_hanh(tmp_path):
    """Facebook và YouTube đều trỏ về bài web. Chưa có trang thì trỏ vào đâu?"""
    cam = _cam(tmp_path)
    s = (cam / "campaign.md").read_text(encoding="utf-8")
    (cam / "campaign.md").write_text(s.replace("| https://x.vn/bai-mot |", "|  |"),
                                     encoding="utf-8", newline="\n")
    c = _chay_gia()
    assert CS.buoc_phat_hanh(cam, bot=None, chay=c)["xu_ly"] == 0


def test_DA_dang_roi_thi_khong_dang_lai(tmp_path):
    """Idempotent: chạy lại không được đăng chồng lên Facebook."""
    cam = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --bai "{bai}"\'\n')
    s = (cam / "campaign.md").read_text(encoding="utf-8")
    (cam / "campaign.md").write_text(
        s.replace("| 2026-09-15 |  | ./T-001_bai |", "| 2026-09-15 | 2026-09-16 | ./T-001_bai |"),
        encoding="utf-8", newline="\n")
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/2"}})
    assert CS.buoc_phat_hanh(cam, bot=None, chay=c)["xu_ly"] == 0
    assert c.goi == [], "đã đăng lại một bài đã phát hành"


def test_CHUA_qua_cong_3_thi_khong_phat_hanh(tmp_path):
    """Bảng có khai cột `g3` mà để trống = chưa ai mở link xem. Không được phát tiếp."""
    cam = _cam(tmp_path)
    s = (cam / "campaign.md").read_text(encoding="utf-8")
    s = s.replace("| g2 | schedule |", "| g2 | g3 | schedule |")
    s = s.replace("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    s = s.replace("| 2026-09-02 | 2026-09-15 |", "| 2026-09-02 |  | 2026-09-15 |")
    (cam / "campaign.md").write_text(s, encoding="utf-8", newline="\n")
    c = _chay_gia()
    assert CS.buoc_phat_hanh(cam, bot=None, chay=c)["xu_ly"] == 0, "vượt Cổng 3"


def test_chi_bai_gioi_han_dung_mot_bai(tmp_path):
    cam = _cam(tmp_path)
    c = _chay_gia()
    assert CS.buoc_phat_hanh(cam, bot=None, chay=c, chi_bai="T-999")["xu_ly"] == 0


def test_ten_cu_dang_van_chay_duoc_va_GHI_URL(tmp_path):
    """`dang` là tên cũ. Lệnh cũ không được gãy, và phải được luôn phần ghi URL.

    Bản cũ chỉ bọc `web_publish` và KHÔNG ghi URL ngược vào bảng — thiếu đúng chỗ đó nên
    `pipeline_state` không bao giờ biết bài đã lên trang, và lượt sau lại đăng lần nữa.
    """
    cam = _cam(tmp_path)
    s = (cam / "campaign.md").read_text(encoding="utf-8")
    (cam / "campaign.md").write_text(s.replace("| https://x.vn/bai-mot |", "|  |"),
                                     encoding="utf-8", newline="\n")
    (cam / "T-001_bai" / "atlas" / "blog.md").write_text("# T\n\nThân.\n",
                                                         encoding="utf-8", newline="\n")
    (cam / "T-001_bai" / "meta.json").write_text(
        json.dumps({"post_id": "T-001", "title": "Bài một", "slug": "bai-mot",
                    "category": "ai"}), encoding="utf-8", newline="\n")

    def chay(lenh, **kw):
        t = " ".join(str(x) for x in lenh)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "build_blog_html" in t:
            i = lenh.index("--out")
            Path(lenh[i + 1]).write_text("<html>x</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t:
            R.stdout = json.dumps({"blog_url": "https://x.vn/moi", "http": 200})
        return R()

    kq = CS.buoc_dang(cam, bot=None, chay=chay)
    assert kq["buoc"] == "dung-trang", f"`dang` không uỷ quyền: {kq}"
    assert _bang(cam)["T-001"]["web"] == "https://x.vn/moi", "tên cũ vẫn không ghi URL"
