# -*- coding: utf-8 -*-
"""`campaign_cfg.py` — hợp nhất cấu hình chiến dịch thành JSON cho PowerShell đọc.

Mỗi test dưới đây tương ứng một cách hỏng ĐÃ ĐO ĐƯỢC trên máy thật, không phải giả định:

· PowerShell 5.1 không đọc nổi YAML → nếu script này im lặng trả JSON thiếu khoá thì
  runner chạy tiếp với giá trị rỗng: video không tiêu đề, bài đăng nhầm playlist, và
  KHÔNG có dòng lỗi nào. Vì vậy phải fail-closed, và có test cho đúng điều đó.
· Bốn runner đang đọc 25 tên khoá phẳng. Bản chụp mất tên cũ = 5 pipeline chết cùng lúc.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CFG = GOC / "scripts" / "pipeline" / "campaign_cfg.py"


def _tram(tmp_path: Path, *, campaign_fm: str, brand_json: dict | None = None,
          brand_md: str | None = None, channel_brand: str = "") -> Path:
    """Dựng một trạm tối thiểu: 1 kênh + 1 chiến dịch. Trả về thư mục chiến dịch."""
    channel = tmp_path / "kenh-thu"
    (channel / "cd-thu").mkdir(parents=True)
    (channel / "channel.yml").write_text(
        "schema: channel/1\nid: kenh-thu\nlabel: \"Kênh thử\"\n"
        "platforms:\n  - channel: youtube\n    post_formats: [youtube_video]\n"
        + channel_brand, encoding="utf-8")
    if brand_json is not None:
        (channel / "brand.json").write_text(json.dumps(brand_json, ensure_ascii=False),
                                        encoding="utf-8")
    if brand_md is not None:
        (channel / "brand.md").write_text(brand_md, encoding="utf-8")
    (channel / "cd-thu" / "campaign.md").write_text(campaign_fm, encoding="utf-8")
    return channel / "cd-thu"


def _chay(campaign: Path):
    return subprocess.run([sys.executable, str(CFG), "--campaign", str(campaign)],
                          capture_output=True, text=True, encoding="utf-8")


FM_TOI_THIEU = ("---\nschema: campaign/1\nid: cd-thu\nchannel: kenh-thu\n"
                "runtime:\n  label: \"Nhãn thử\"\n  runner: chay.ps1\n---\n\nThân bài.\n")


def test_gop_toi_thieu_va_co_meta(tmp_path):
    r = _chay(_tram(tmp_path, campaign_fm=FM_TOI_THIEU))
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["label"] == "Nhãn thử" and d["runner"] == "chay.ps1"
    assert d["_meta"]["schema"] == "campaign-config/1"
    assert d["_meta"]["campaign"] == "cd-thu" and d["_meta"]["channel"] == "kenh-thu"
    # Bản chụp phải TỰ NÓI nó là bản sinh — người mở ra sửa tay là mất lúc chạy sau.
    assert "đừng sửa tay" in d["_meta"]["warn"].lower()


def test_campaign_de_len_kenh(tmp_path):
    """Cùng một khoá ở hai tầng: campaign phải thắng. Sai chiều = mọi campaign giống nhau."""
    campaign = _tram(tmp_path, brand_json={"label": "của kênh", "repo": "r"},
                campaign_fm=FM_TOI_THIEU)
    d = json.loads(_chay(campaign).stdout)
    assert d["label"] == "Nhãn thử"      # campaign đè
    assert d["repo"] == "r"              # khoá kênh vẫn còn


def test_channel_yml_brand_lam_nen_brand_json_de_len(tmp_path):
    """`channel.yml:brand` là đích đến, `brand.json` là bản đang chạy — bản đang chạy thắng."""
    campaign = _tram(tmp_path, channel_brand="brand:\n  repo: moi\n  gh_repo: gh\n",
                brand_json={"repo": "dang-chay"}, campaign_fm=FM_TOI_THIEU)
    d = json.loads(_chay(campaign).stdout)
    assert d["repo"] == "dang-chay"
    assert d["gh_repo"] == "gh"          # khoá chỉ có ở channel.yml không bị mất


def test_khoi_long_duoc_trai_phang_sang_ten_cu(tmp_path):
    """Bản chụp phải mang CẢ hai tên. Mất tên cũ = 4 runner + 2 build-index chết cùng lúc."""
    fm = ("---\nschema: campaign/1\nid: cd-thu\nchannel: kenh-thu\n"
          "runtime:\n  label: L\n  runner: r.ps1\n"
          "identity:\n  brand_a: AAA\n  brand_b: BBB\n  kicker: KK\n  site: ss\n"
          "theme:\n  video_accents: \"#111,#222\"\n  email_accent: \"#333\"\n"
          "titles:\n  yt_prefix: TP\n  recap: RC\n  short: SH\n---\n\nx\n")
    d = json.loads(_chay(_tram(tmp_path, campaign_fm=fm)).stdout)
    assert d["topstory_brand_a"] == "AAA" and d["topstory_brand_b"] == "BBB"
    assert d["topstory_kicker"] == "KK" and d["topstory_site"] == "ss"
    assert d["topstory_accents"] == "#111,#222" and d["email_accent"] == "#333"
    assert d["weekly_recap_title"] == "RC" and d["weekly_short_title"] == "SH"
    assert d["yt_title_prefix"] == "TP" and d["yt_title_prefix_daily"] == "TP"
    # ...và giữ NGUYÊN hình dạng lồng cho code viết sau này.
    assert d["identity"]["brand_a"] == "AAA" and d["theme"]["email_accent"] == "#333"


def test_suy_ra_khoa_bo_di_nhung_khong_de_len_gia_tri_that(tmp_path):
    fm = FM_TOI_THIEU.replace("  runner: chay.ps1\n",
                              "  runner: chay.ps1\n  site_base: https://vi.du\n"
                              "  yt_playlist: PL\n  site_root: that\n")
    d = json.loads(_chay(_tram(tmp_path, campaign_fm=fm)).stdout)
    assert d["site"] == "https://vi.du"          # suy ra
    assert d["site_root"] == "that"              # ĐÃ CÓ -> không bị đè
    assert d["yt_playlist_daily"] == "PL" and d["yt_playlist_weekly"] == "PL"


# ── FAIL-CLOSED ────────────────────────────────────────────────────────────────
# Ba ca dưới đây quan trọng hơn mọi ca ở trên: chúng khẳng định script DỪNG chứ không
# trả về JSON thiếu. Một bản chụp thiếu khoá không làm gãy gì ngay — nó làm sản phẩm ra
# sai và chỉ lộ lúc xem video/bài đã đăng.

def test_thieu_campaign_md_thi_dung_han(tmp_path):
    (tmp_path / "kenh-thu" / "cd-rong").mkdir(parents=True)
    (tmp_path / "kenh-thu" / "channel.yml").write_text("id: kenh-thu\n", encoding="utf-8")
    r = _chay(tmp_path / "kenh-thu" / "cd-rong")
    assert r.returncode == 2
    assert "campaign.md" in r.stderr
    assert r.stdout.strip() == ""        # KHÔNG in JSON dở dang


@pytest.mark.parametrize("bo", ["label", "runner"])
def test_thieu_khoa_bat_buoc_thi_dung_han(tmp_path, bo):
    fm = FM_TOI_THIEU.replace(f"  {bo}: ", "  _bo_di: ")
    r = _chay(_tram(tmp_path, campaign_fm=fm))
    assert r.returncode == 2 and bo in r.stderr
    assert r.stdout.strip() == ""


def test_frontmatter_hong_thi_dung_han_khong_nuot(tmp_path):
    fm = "---\nrutime: [ chua dong ngoac\n---\nx\n"
    r = _chay(_tram(tmp_path, campaign_fm=fm))
    assert r.returncode == 2 and r.stdout.strip() == ""


def test_brand_md_gop_cau_chu_cap_kenh(tmp_path):
    """profile.md đã gộp vào brand.md — câu chữ cấp kênh phải ra được tới bản chụp."""
    campaign = _tram(tmp_path, brand_md="---\ntagline: \"Câu định vị\"\nwelcome: \"Chào\"\n---\n\nGiọng.\n",
                campaign_fm=FM_TOI_THIEU)
    d = json.loads(_chay(campaign).stdout)
    assert d["tagline"] == "Câu định vị" and d["welcome"] == "Chào"


# ── CHỐNG TÁI PHÁT: Excel phải nhận ĐỦ trường mà research.md khai ──────────────
def test_export_excel_doc_het_khoa_research_md_co_cot_tuong_ung():
    """`key_sources`, `content_relationship`, `notes` từng bị bỏ quên suốt nhiều bản.

    Template `research.md` khai chúng, sheet Content có đúng cột cho chúng, mà vòng lặp
    trong `export_excel.py` không đọc — ba cột ra file luôn trắng và người nhận tưởng
    chưa ai điền. Test này khoá lại: khoá nào có ở CẢ HAI nơi thì PHẢI được đọc.
    """
    sys.path.insert(0, str(GOC / "scripts" / "lib"))
    sys.path.insert(0, str(GOC / "scripts" / "pipeline"))
    import md_io
    import export_excel as EX

    fm, _ = md_io.read_fm(GOC / "templates" / "station" / "_channel" / "_campaign" / "_content" / "research.md")
    khai = set(fm) - {"schema", "campaign_id", "content_id"}
    co_cot = khai & set(EX.COT_CONTENT)
    source = (GOC / "scripts" / "pipeline" / "export_excel.py").read_text(encoding="utf-8")
    # Cắt đúng thân hàm dựng dòng Content để không khớp nhầm chỗ khác trong file.
    than = source.split("def _dong_content")[1].split("def _dong_post")[0]
    thieu = sorted(k for k in co_cot if f'"{k}"' not in than)
    assert not thieu, (
        f"research.md khai {sorted(thieu)} và sheet Content có cột tương ứng, "
        f"nhưng _dong_content không đọc — ba cột này sẽ trắng trong mọi file xuất ra.")


def test_autonomy_di_theo_ban_chup(tmp_path):
    """PowerShell 5.1 không đọc được YAML — không có khoá này trong bản chụp thì cổng tự
    trị ở tầng runner KHÔNG TỒN TẠI, nó chỉ còn là một lời dặn trong tài liệu."""
    campaign = _tram(tmp_path, campaign_fm=FM_TOI_THIEU)
    (campaign.parent / "channel.yml").write_text(
        (campaign.parent / "channel.yml").read_text(encoding="utf-8") + "autonomy: full\n",
        encoding="utf-8")
    r = _chay(campaign)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["autonomy"] == "full"


def test_khong_khai_autonomy_thi_mac_dinh_SUGGEST(tmp_path):
    """Thiếu khoá phải rơi về mức CHẶT nhất, không phải mức rộng nhất."""
    r = _chay(_tram(tmp_path, campaign_fm=FM_TOI_THIEU))
    assert json.loads(r.stdout)["autonomy"] == "suggest"


def test_campaign_md_KHONG_tu_nang_quyen_duoc(tmp_path):
    """Một file chiến dịch tự khai `autonomy: full` là tự cấp quyền đăng ra ngoài.

    ⚠️ Bản đầu của test này VÔ NGHĨA: nó đặt `autonomy: full` ở cấp cao nhất của
    campaign.md — mà `gop()` chỉ trộn khối `runtime:`, nên khoá đó không bao giờ tới bản
    chụp và test xanh dù cổng có thủng hay không. Kiểm bằng đột biến (dời dòng gán
    `autonomy` lên TRƯỚC chỗ trộn `runtime`) thấy test vẫn xanh — đúng dấu hiệu vô nghĩa.
    Nay đặt vào ĐÚNG khối `runtime:`, tức đường leo thang thật.
    """
    fm = FM_TOI_THIEU.replace("  runner: chay.ps1",
                              "  runner: chay.ps1\n  autonomy: full")
    campaign = _tram(tmp_path, campaign_fm=fm)
    r = _chay(campaign)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["autonomy"] == "suggest", \
        "campaign.md nâng được quyền cho chính nó — cổng tự trị thủng"
