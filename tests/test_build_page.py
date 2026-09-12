# -*- coding: utf-8 -*-
"""Bước `build-page` — B5 tiếng/hình · B6 dựng trang · B8 đăng web.

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
    channel = tmp_path / "tram" / "kenh-thu"
    campaign = channel / "CD-THU"
    (campaign / "logs").mkdir(parents=True)
    (channel / "channel.yml").write_text(
        "schema: channel/1\nid: kenh-thu\nlabel: \"K\"\nautonomy: suggest\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8", newline="\n")
    fm = FM.replace("  label: Thử\n", "  label: Thử\n" + runtime_them)
    (campaign / "campaign.md").write_text(fm, encoding="utf-8", newline="\n")

    post = campaign / "T-001_bai"
    (post / "atlas").mkdir(parents=True)
    (post / "atlas" / "blog.md").write_text("# Tiêu đề\n\nThân bài.\n",
                                           encoding="utf-8", newline="\n")
    (post / "meta.json").write_text(json.dumps({"post_id": "T-001", "title": "Bài một",
                                               "slug": "bai-mot", "category": "ai"}),
                                   encoding="utf-8", newline="\n")
    return campaign


def _bang(campaign):
    _, than = md_io.read_fm(campaign / "campaign.md")
    _, row = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in row}


def _chay_gia(campaign, *, url="https://x.vn/atlas/content/ai/bai-mot", dung_html=True):
    """Giả cả build lẫn publish. Ghi lại lệnh đã gọi."""
    goi = []

    def run_cmd(cmd, **kw):
        goi.append(cmd)
        t = " ".join(str(x) for x in cmd)

        class R:
            returncode = 0
            stderr = ""
            stdout = ""
        if "build_blog_html" in t and dung_html:
            i = cmd.index("--out")
            Path(cmd[i + 1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[i + 1]).write_text("<html>bài</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t:
            R.stdout = json.dumps({"blog_url": url, "http": 200})
        return R()
    run_cmd.goi = goi
    return run_cmd


# ── đường chạy bình thường ──────────────────────────────────────────────────

def test_build_page_ghi_URL_that_vao_cot_web(tmp_path):
    """Cột `web` là thứ `pipeline_state` đọc để biết bài đã lên trang chưa.

    Không ghi vào đó thì bước sau tưởng chưa đăng và sẽ đăng lại — mỗi lượt một lần nữa.
    """
    campaign = _cam(tmp_path)
    c = _chay_gia(campaign)
    result = CS.step_build_page(campaign, bot=None, run_cmd=c)
    assert result["xu_ly"] == 1, result
    assert _bang(campaign)["T-001"]["web"] == "https://x.vn/atlas/content/ai/bai-mot"


def test_goi_dung_thu_tu_dung_trang_roi_moi_dang(tmp_path):
    """Đăng trước khi dựng là đẩy lên một trang chưa tồn tại."""
    campaign = _cam(tmp_path)
    c = _chay_gia(campaign)
    CS.step_build_page(campaign, bot=None, run_cmd=c)
    thu_tu = [("build_blog_html" in " ".join(map(str, l))) for l in c.goi]
    assert thu_tu[0] is True, f"lệnh đầu không phải dựng trang: {c.goi[0]}"
    assert any("web_publish" in " ".join(map(str, l)) for l in c.goi)


# ── audio là TUỲ CHỌN ───────────────────────────────────────────────────────

def test_KHONG_khai_audio_cmd_thi_BO_QUA_chu_khong_hong(tmp_path):
    """Quy trình không giả định chiến dịch nào cũng có tiếng.

    Chiến dịch chỉ có web + ảnh + post phải chạy trót lọt mà không cần khai gì thêm.
    """
    campaign = _cam(tmp_path)                       # KHÔNG khai audio_cmd
    c = _chay_gia(campaign)
    result = CS.step_build_page(campaign, bot=None, run_cmd=c)
    assert result["xu_ly"] == 1
    # Khẳng định đúng CỜ, đừng dò chuỗi "audio" trong cả dòng lệnh: `tmp_path` của pytest
    # mang tên hàm test, mà tên hàm này có chữ "audio" ⇒ dò chuỗi sẽ tự bắt nhầm chính nó.
    assert not any("--audio-src" in l for l in c.goi), c.goi


def test_CO_khai_audio_cmd_thi_chay_va_NHUNG_vao_trang(tmp_path):
    campaign = _cam(tmp_path, runtime_them='  audio_cmd: \'lam-tieng --post "{post}"\'\n')
    post = campaign / "T-001_bai"

    def run_cmd(cmd, **kw):
        t = " ".join(str(x) for x in cmd)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "lam-tieng" in t:
            (post / "atlas" / "audio.mp3").write_bytes(b"ID3fake")
        if "build_blog_html" in t:
            i = cmd.index("--out")
            Path(cmd[i + 1]).write_text("<html>x</html>", encoding="utf-8", newline="\n")
            run_cmd.co_audio_src = "--audio-src" in cmd
        if "web_publish" in t:
            R.stdout = json.dumps({"blog_url": "https://x.vn/a/b", "http": 200})
        return R()
    run_cmd.co_audio_src = False

    result = CS.step_build_page(campaign, bot=None, run_cmd=run_cmd)
    assert result["xu_ly"] == 1
    assert run_cmd.co_audio_src, "dựng audio xong mà không nhúng vào trang"


# ── fail-closed ─────────────────────────────────────────────────────────────

def test_build_page_KHONG_ra_html_thi_la_HONG_du_ma_thoat_0(tmp_path):
    """Mã thoát 0 không đủ để tính là xong — luật đã có của repo, áp cả ở đây.

    Bộ dựng chạy êm mà không ra file thì đăng lên sẽ là một trang rỗng.
    """
    campaign = _cam(tmp_path)
    c = _chay_gia(campaign, dung_html=False)        # báo OK nhưng KHÔNG ghi file
    result = CS.step_build_page(campaign, bot=None, run_cmd=c)
    assert result["xu_ly"] == 0 and result["failed"], result
    assert not any("web_publish" in " ".join(map(str, l)) for l in c.goi), \
        "đã đem đăng một trang chưa dựng được"


def test_dang_web_khong_tra_URL_thi_KHONG_ghi_cot_web(tmp_path):
    """Không có URL nghĩa là không biết bài nằm đâu — ghi bừa là nói dối cái bảng."""
    campaign = _cam(tmp_path)

    def run_cmd(cmd, **kw):
        t = " ".join(str(x) for x in cmd)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "build_blog_html" in t:
            i = cmd.index("--out")
            Path(cmd[i + 1]).write_text("<html>x</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t:
            R.stdout = json.dumps({"http": 200})        # THIẾU blog_url
        return R()

    result = CS.step_build_page(campaign, bot=None, run_cmd=run_cmd)
    assert result["xu_ly"] == 0 and result["failed"]
    assert _bang(campaign)["T-001"]["web"] == ""


def test_bai_CHUA_qua_cong_2_thi_khong_dung(tmp_path):
    """Cổng 2 là chỗ người quyết bài có đáng dựng không. Vượt qua nó là vô hiệu hoá cổng."""
    campaign = _cam(tmp_path)
    than_cu = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(
        than_cu.replace("| 2026-09-01 | 2026-09-02 |", "| 2026-09-01 |  |"),
        encoding="utf-8", newline="\n")
    c = _chay_gia(campaign)
    result = CS.step_build_page(campaign, bot=None, run_cmd=c)
    assert result["xu_ly"] == 0 and c.goi == []


def test_bai_DA_len_web_thi_khong_dang_lai(tmp_path):
    """Idempotent: chạy lại không được đăng chồng."""
    campaign = _cam(tmp_path)
    than_cu = (campaign / "campaign.md").read_text(encoding="utf-8")
    (campaign / "campaign.md").write_text(
        than_cu.replace("| ./T-001_bai |  |", "| ./T-001_bai | https://x.vn/da-co |"),
        encoding="utf-8", newline="\n")
    c = _chay_gia(campaign)
    assert CS.step_build_page(campaign, bot=None, run_cmd=c)["xu_ly"] == 0
    assert c.goi == []


def test_chi_bai_gioi_han_dung_mot_bai(tmp_path):
    campaign = _cam(tmp_path)
    c = _chay_gia(campaign)
    result = CS.step_build_page(campaign, bot=None, run_cmd=c, only_post="T-999")
    assert result["xu_ly"] == 0 and c.goi == []
