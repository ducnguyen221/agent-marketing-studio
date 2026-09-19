# -*- coding: utf-8 -*-
"""Bước `release` — B7 YouTube · B9 Facebook · B10 ghi sổ.

Bước CUỐI của đường ống, và là bước duy nhất đẩy bài ra các nền tảng ngoài. Sai ở đây thì
hoặc đăng trùng, hoặc báo đã đăng trong khi chưa, và cả hai đều chỉ lộ ra khi đã muộn.
"""
import json
import sys
from datetime import date
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


# Bài mẫu hẹn 15/09. Hai mốc dưới đây kẹp hai phía của nó, và mọi lượt gọi đều truyền
# mốc TƯỜNG MINH: một bài test đọc `date.today()` là bài test tự đổi kết quả theo ngày chạy.
SAU_LICH = date(2026, 9, 20)
TRUOC_LICH = date(2026, 9, 10)


def _cam(tmp_path, *, runtime_them=""):
    channel = tmp_path / "tram" / "kenh-thu"
    campaign = channel / "CD-THU"
    (campaign / "logs").mkdir(parents=True)
    (channel / "channel.yml").write_text(
        "schema: channel/1\nid: kenh-thu\nlabel: \"K\"\nautonomy: suggest\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8", newline="\n")
    (campaign / "campaign.md").write_text(
        FM.replace("  label: Thử\n", "  label: Thử\n" + runtime_them),
        encoding="utf-8", newline="\n")
    (campaign / "T-001_bai" / "atlas").mkdir(parents=True)
    return campaign


def _bang(campaign):
    _, than = md_io.read_fm(campaign / "campaign.md")
    _, row = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in row}


def _chay_gia(**ra):
    """`ra` map: chuỗi-nhận-dạng-lệnh -> stdout JSON."""
    goi = []

    def run_cmd(cmd, **kw):
        goi.append(cmd)
        t = " ".join(str(x) for x in cmd)

        class R:
            returncode, stdout, stderr = 0, "", ""
        for khoa, gt in ra.items():
            if khoa in t:
                R.stdout = json.dumps(gt)
        return R()
    run_cmd.goi = goi
    return run_cmd


# ── chiến dịch CHỈ CÓ WEB ───────────────────────────────────────────────────

def test_khong_khai_kenh_nao_thi_ghi_published_va_XONG(tmp_path):
    """Chiến dịch chỉ có web: bài lên trang RỒI là đã phát hành.

    Bắt khai YouTube/Facebook mới cho đánh dấu xong là ép mọi chiến dịch phải có video.
    """
    campaign = _cam(tmp_path)
    c = _chay_gia()
    result = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)
    assert result["xu_ly"] == 1, result
    assert _bang(campaign)["T-001"]["published"] != ""
    assert c.goi == [], f"không khai kênh nào mà vẫn gọi lệnh: {c.goi}"


# ── có kênh ngoài ───────────────────────────────────────────────────────────

def test_khai_youtube_thi_chay_va_ghi_link(tmp_path):
    campaign = _cam(tmp_path, runtime_them='  youtube_cmd: \'len-yt --post "{post}"\'\n')
    c = _chay_gia(**{"len-yt": {"url": "https://youtu.be/abc"}})
    result = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)
    assert result["xu_ly"] == 1
    assert _bang(campaign)["T-001"]["youtube"] == "https://youtu.be/abc"


def test_khai_facebook_thi_chay_va_ghi_link(tmp_path):
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --post "{post}"\'\n')
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/1"}})
    CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)
    assert _bang(campaign)["T-001"]["facebook"] == "https://fb.com/1"


def test_kenh_HONG_thi_KHONG_danh_dau_da_dang(tmp_path):
    """Báo đã phát hành trong khi chưa là cách hỏng tệ nhất: không ai đi kiểm lại.

    Bài sẽ nằm im mãi mãi ở trạng thái "xong" mà thật ra chưa lên kênh nào.
    """
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --post "{post}"\'\n')

    def run_cmd(cmd, **kw):
        class R:
            returncode, stdout, stderr = 1, "", "token hết hạn"
        return R()

    result = CS.step_release(campaign, bot=None, run_cmd=run_cmd, hom_nay=SAU_LICH)
    assert result["xu_ly"] == 0 and result["failed"], result
    assert _bang(campaign)["T-001"]["published"] == "", "đánh dấu đã đăng trong khi kênh hỏng"


def test_kenh_chay_EM_nhung_khong_tra_link_van_la_HONG(tmp_path):
    """Mã thoát 0 không đủ để tính là xong — luật cũ của repo, áp cả ở đây."""
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --post "{post}"\'\n')
    c = _chay_gia(**{"len-fb": {"ok": True}})          # THIẾU url
    result = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)
    assert result["xu_ly"] == 0 and result["failed"]
    assert _bang(campaign)["T-001"]["published"] == ""


# ── điều kiện vào bước ──────────────────────────────────────────────────────

def test_CHUA_len_web_thi_khong_phat_hanh(tmp_path):
    """Facebook và YouTube đều trỏ về bài web. Chưa có trang thì trỏ vào đâu?"""
    campaign = _cam(tmp_path)
    s = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(s.replace("| https://x.vn/bai-mot |", "|  |"),
                                     encoding="utf-8", newline="\n")
    c = _chay_gia()
    assert CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)["xu_ly"] == 0


def test_DA_dang_roi_thi_khong_dang_lai(tmp_path):
    """Idempotent: chạy lại không được đăng chồng lên Facebook."""
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --post "{post}"\'\n')
    s = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(
        s.replace("| 2026-09-15 |  | ./T-001_bai |", "| 2026-09-15 | 2026-09-16 | ./T-001_bai |"),
        encoding="utf-8", newline="\n")
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/2"}})
    assert CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)["xu_ly"] == 0
    assert c.goi == [], "đã đăng lại một bài đã phát hành"


def test_CHUA_qua_cong_3_thi_khong_phat_hanh(tmp_path):
    """Bảng có khai cột `g3` mà để trống = chưa ai mở link xem. Không được phát tiếp."""
    campaign = _cam(tmp_path)
    s = (campaign / "campaign.md").read_text(encoding="utf-8")
    s = s.replace("| g2 | schedule |", "| g2 | g3 | schedule |")
    s = s.replace("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    s = s.replace("| 2026-09-02 | 2026-09-15 |", "| 2026-09-02 |  | 2026-09-15 |")
    (campaign / "campaign.md").write_text(s, encoding="utf-8", newline="\n")
    c = _chay_gia()
    assert CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)["xu_ly"] == 0, "vượt Cổng 3"


def test_chi_bai_gioi_han_dung_mot_bai(tmp_path):
    campaign = _cam(tmp_path)
    c = _chay_gia()
    assert CS.step_release(campaign, bot=None, run_cmd=c, only_post="T-999", hom_nay=SAU_LICH)["xu_ly"] == 0


def test_ten_cu_dang_van_chay_duoc_va_GHI_URL(tmp_path):
    """`dang` là tên cũ. Lệnh cũ không được gãy, và phải được luôn phần ghi URL.

    Bản cũ chỉ bọc `web_publish` và KHÔNG ghi URL ngược vào bảng — thiếu đúng chỗ đó nên
    `pipeline_state` không bao giờ biết bài đã lên trang, và lượt sau lại đăng lần nữa.
    """
    campaign = _cam(tmp_path)
    s = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(s.replace("| https://x.vn/bai-mot |", "|  |"),
                                     encoding="utf-8", newline="\n")
    (campaign / "T-001_bai" / "atlas" / "blog.md").write_text("# T\n\nThân.\n",
                                                         encoding="utf-8", newline="\n")
    (campaign / "T-001_bai" / "meta.json").write_text(
        json.dumps({"post_id": "T-001", "title": "Bài một", "slug": "bai-mot",
                    "category": "ai"}), encoding="utf-8", newline="\n")

    def run_cmd(cmd, **kw):
        t = " ".join(str(x) for x in cmd)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "build_blog_html" in t:
            i = cmd.index("--out")
            Path(cmd[i + 1]).write_text("<html>x</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t:
            R.stdout = json.dumps({"blog_url": "https://x.vn/moi", "http": 200})
        return R()

    result = CS.step_publish(campaign, bot=None, run_cmd=run_cmd)
    assert result["step"] == "build-page", f"`dang` không uỷ quyền: {result}"
    assert _bang(campaign)["T-001"]["web"] == "https://x.vn/moi", "tên cũ vẫn không ghi URL"


# ── hẹn giờ trên nền tảng ───────────────────────────────────────────────────

def test_om_ngay_thi_hook_nhan_du_ba_dinh_dang(tmp_path):
    """YouTube ăn RFC3339 UTC, Graph ăn số giây. Hook không phải tự đổi ngày ra giờ."""
    campaign = _cam(tmp_path, runtime_them=(
        '  publish_time: "09:00"\n'
        '  youtube_cmd: \'len-yt --at "{publish_at}" --ts "{publish_ts}" --ngay "{schedule}"\'\n'))
    c = _chay_gia(**{"len-yt": {"url": "https://youtu.be/abc"}})
    result = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=TRUOC_LICH)
    assert result["xu_ly"] == 1, result
    cmd = c.goi[0]
    assert cmd[cmd.index("--ngay") + 1] == "2026-09-15", cmd
    at = cmd[cmd.index("--at") + 1]
    ts = cmd[cmd.index("--ts") + 1]
    assert at == CS.publish_moment("2026-09-15", "09:00")[0] and at.endswith("Z"), cmd
    assert ts == CS.publish_moment("2026-09-15", "09:00")[1] and ts.isdigit(), cmd


def test_lenh_KHONG_nhan_ngay_thi_bai_hen_tuong_lai_BI_CHAN(tmp_path):
    """Lệnh không có ô ngày chỉ biết đăng ngay. Gọi nó cho bài tuần sau là đăng sớm.

    Không có nút thu hồi trên Facebook hay YouTube, nên chặn trước còn hơn phát rồi mới biết.
    """
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --post "{post}"\'\n')
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/1"}})
    result = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=TRUOC_LICH)
    assert result["xu_ly"] == 0 and result["failed"], result
    assert c.goi == [], f"đã gọi nền tảng cho bài chưa tới ngày: {c.goi}"
    assert _bang(campaign)["T-001"]["published"] == ""
    assert "đăng sớm" in result["failed"][0]["reason"]


def test_den_ngay_roi_thi_lenh_khong_nhan_ngay_van_chay(tmp_path):
    """Đúng ngày thì đăng ngay CHÍNH LÀ đúng. Luật chặn chỉ áp cho bài còn ở tương lai."""
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --post "{post}"\'\n')
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/1"}})
    r = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=date(2026, 9, 15))
    assert r["xu_ly"] == 1, r
    assert _bang(campaign)["T-001"]["facebook"] == "https://fb.com/1"


def test_lich_RAC_thi_dung_chu_khong_doan_ngay(tmp_path):
    """Ngày hỏng không được âm thầm thành 'đăng ngay'."""
    campaign = _cam(tmp_path, runtime_them='  facebook_cmd: \'len-fb --at "{publish_at}"\'\n')
    s = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(s.replace("| 2026-09-15 |", "| thu-hai |"),
                                          encoding="utf-8", newline="\n")
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/1"}})
    r = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=TRUOC_LICH)
    assert r["xu_ly"] == 0 and c.goi == [], r
    assert _bang(campaign)["T-001"]["published"] == ""


def test_gio_dang_hong_thi_KHONG_dang_bai_nao(tmp_path):
    """Một khoá gõ sai trong cấu hình không được biến thành giờ đăng đoán bừa."""
    campaign = _cam(tmp_path, runtime_them=(
        '  publish_time: "chin gio"\n'
        '  youtube_cmd: \'len-yt --at "{publish_at}"\'\n'))
    c = _chay_gia(**{"len-yt": {"url": "https://youtu.be/abc"}})
    r = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=TRUOC_LICH)
    assert r["xu_ly"] == 0 and c.goi == [], r
    assert "publish_time" in r["failed"][0]["reason"]


def test_publish_moment_doi_gio_dia_phuong_sang_UTC():
    from datetime import datetime, timezone
    at, ts = CS.publish_moment("2026-09-15", "09:00")
    lai = datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert int(lai.timestamp()) == int(ts), "hai định dạng phải chỉ cùng một mốc"
    assert lai.astimezone().hour == 9, "giờ địa phương phải đúng 09:00"
    assert lai.astimezone().date() == date(2026, 9, 15)


def test_khong_co_lich_thi_khong_hen_gio():
    assert CS.publish_moment("", "09:00") == ("", "")


def test_ham_chan_tu_no_cung_khong_doan_ngay_rac():
    """`step_release` đã chặn lịch rác ở bước tính giờ, nên nhánh này không chạy qua đường đó.

    Nhưng hàm chặn phải tự đứng được: ai gọi nó ở chỗ khác thì lịch rác vẫn không được
    biến thành 'không có lý do chặn', tức đăng ngay.
    """
    assert CS._khong_the_hen_gio('len-fb --post "{post}"', "thu-hai", TRUOC_LICH) != ""
    assert CS._khong_the_hen_gio('len-fb --post "{post}"', "", TRUOC_LICH) == ""
    assert CS._khong_the_hen_gio('len-fb --at "{publish_ts}"', "2026-09-15", TRUOC_LICH) == ""
    assert CS._khong_the_hen_gio('len-fb --post "{post}"', "2026-09-15", TRUOC_LICH) != ""


# ── nhiều kênh: không đăng trùng ────────────────────────────────────────────

HAI_KENH = ("  youtube_cmd: 'len-yt --at \"{publish_at}\"'\n"
            "  facebook_cmd: 'len-fb --ts \"{publish_ts}\" --yt \"{youtube_url}\"'\n")


def test_youtube_LEN_ma_facebook_HONG_thi_lan_sau_KHONG_tai_lai_video(tmp_path):
    """Trước bản vá, link YouTube chỉ nằm trong bộ nhớ tới khi MỌI kênh xong.

    Facebook hỏng thì không gì được ghi, và mỗi lượt chạy lại là thêm một video trùng.
    """
    campaign = _cam(tmp_path, runtime_them=HAI_KENH)
    goi = []

    def fb_hong(cmd, **kw):
        goi.append(cmd[0])

        class R:
            returncode, stdout, stderr = 0, "", ""
        if cmd[0] == "len-yt":
            R.stdout = json.dumps({"url": "https://youtu.be/abc"})
        else:
            R.returncode, R.stderr = 1, "token hết hạn"
        return R()

    r1 = CS.step_release(campaign, bot=None, run_cmd=fb_hong, hom_nay=TRUOC_LICH)
    assert r1["xu_ly"] == 0 and r1["failed"], r1
    assert _bang(campaign)["T-001"]["youtube"] == "https://youtu.be/abc", "link YouTube bị mất"
    assert _bang(campaign)["T-001"]["published"] == ""

    goi.clear()
    c = _chay_gia(**{"len-fb": {"url": "https://fb.com/1"}})
    r2 = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=TRUOC_LICH)
    assert r2["xu_ly"] == 1, r2
    assert [x[0] for x in c.goi] == ["len-fb"], f"đã gọi lại YouTube: {c.goi}"
    fb = c.goi[0]
    assert fb[fb.index("--yt") + 1] == "https://youtu.be/abc", "Facebook không nhận link YouTube"


def test_bai_HEN_GIO_ghi_ngay_hen_chu_khong_ghi_hom_nay(tmp_path):
    """Cột `published` trả lời 'bài ra mắt ngày nào'. Hẹn 15/09 thì là 15/09."""
    campaign = _cam(tmp_path, runtime_them=HAI_KENH)
    c = _chay_gia(**{"len-yt": {"url": "https://youtu.be/abc"},
                     "len-fb": {"url": "https://fb.com/1"}})
    r = CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=TRUOC_LICH)
    assert r["xu_ly"] == 1, r
    assert _bang(campaign)["T-001"]["published"] == "2026-09-15"


def test_youtube_cmd_thay_channel_va_station(tmp_path):
    campaign = _cam(tmp_path, runtime_them='  youtube_cmd: \'len-yt "{channel}" "{station}"\'\n')
    (tmp_path / "tram" / "CHANNELS.md").write_text("# Kênh\n", encoding="utf-8")
    c = _chay_gia(**{"len-yt": {"url": "https://youtu.be/abc"}})
    CS.step_release(campaign, bot=None, run_cmd=c, hom_nay=SAU_LICH)
    assert c.goi, "không gọi youtube_cmd"
    assert Path(c.goi[0][1]).resolve() == campaign.parent.resolve()
    assert Path(c.goi[0][2]).resolve() == (tmp_path / "tram").resolve()
