# -*- coding: utf-8 -*-
"""Test cho register_publish — sổ đăng bài, thay sheet Post.

Bốn điều phải giữ, mỗi điều là một cách bài có thể hỏng sau khi đã lên mạng:
1. Chưa qua Cổng 2 thì KHÔNG được ghi là đã đăng.
2. Cổng 2 phải có DẤU VẾT (ai, lúc nào, nói gì) — không phải cái cờ bật lên.
3. Facebook KHÔNG verify bằng HTTP (permalink trả 200 cả khi là trang đăng nhập);
   điều kiện là platform_id, và với bài thường thì cả comment_id.
4. Còn placeholder sau khi thay thì KHÔNG ghi sổ — bài dán lên mạng nguyên {{BLOG_URL}}.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import md_io as M  # noqa: E402
import post_paths as PP  # noqa: E402

PY = sys.executable
RP = ROOT / "scripts" / "pipeline" / "register_publish.py"


def _chay(bai, *a, mong_doi=0):
    r = subprocess.run([PY, str(RP), str(bai), *a], capture_output=True, text=True,
                       encoding="utf-8", cwd=ROOT)
    assert r.returncode == mong_doi, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    return r


@pytest.fixture
def bai(tmp_path):
    """Cây tối thiểu: kênh → chiến dịch → bài, đủ để register_publish chạy."""
    K = tmp_path / "st" / "tobi"
    C = K / "CMP-2609-x"
    B = C / "AST-001_slug"
    PP.tao_thu_muc(B)
    (K / "channel.yml").write_text(
        "schema: channel/1\nid: tobi\npillars: [ai-agent]\n"
        "platforms:\n"
        "  - channel: youtube\n    post_formats: [youtube_video]\n"
        "  - channel: web_blog\n    post_formats: [blog_article]\n"
        "  - channel: facebook\n    post_formats: [facebook_post]\n", encoding="utf-8")
    (K / "CAMPAIGNS.md").write_text(
        "---\nschema: campaigns/1\nchannel: tobi\n---\n\n<!-- CAMPAIGNS:BEGIN -->\n"
        "| campaign_id | bài | đã đăng |\n|---|---|---|\n| CMP-2609-x | 0 | 0 |\n"
        "<!-- CAMPAIGNS:END -->\n", encoding="utf-8")
    (C / "campaign.md").write_text(
        "---\nid: CMP-2609-x\nchannel: tobi\nid_prefix: AST\n"
        "channels: [web_blog, youtube, facebook]\nkpi: {}\n---\n\n<!-- CONTENT:BEGIN -->\n"
        "| content_id | status | g2 | published |\n|---|---|---|---|\n"
        "| AST-001 | in_production |  |  |\n<!-- CONTENT:END -->\n", encoding="utf-8")
    json.dump({"post_id": "AST-001", "slug": "slug", "title": "Bài A"},
              (B / "meta.json").open("w", encoding="utf-8"), ensure_ascii=False)
    PP.p(B, "content").write_text(
        "## post:blog_article\nA\n\n## post:facebook_post\nB\n\n## post:youtube_desc\nC\n",
        encoding="utf-8")
    PP.p(B, "fb_comment").write_text("Bản đầy đủ: {{BLOG_URL}}\n", encoding="utf-8")
    PP.p(B, "yt_desc").write_text("Bài viết: {{BLOG_URL}}\n", encoding="utf-8")
    return B


def _pj(bai):
    return json.loads(PP.p(bai, "publish").read_text(encoding="utf-8"))


def test_init_sinh_post_theo_neo_co_that(bai):
    _chay(bai, "init")
    ids = [p["post_id"] for p in _pj(bai)["posts"]]
    assert set(ids) == {"AST-001-yt", "AST-001-web", "AST-001-fb"}
    assert all(p["review"]["status"] == "pending" for p in _pj(bai)["posts"])


def test_chua_duyet_thi_KHONG_ghi_da_dang(bai):
    _chay(bai, "init")
    r = _chay(bai, "set", "--post", "fb", "--platform-id", "123", "--comment-id", "456",
              mong_doi=2)
    assert "Cổng 2" in r.stderr
    assert _pj(bai)["posts"][0]["publish"]["status"] == "not_published"


def test_approve_bat_buoc_co_dau_vet(bai):
    _chay(bai, "init")
    _chay(bai, "approve", "--by", "Đức", mong_doi=2)          # thiếu --note
    r = _chay(bai, "approve", "--by", "Đức", "--note", "ok đăng đi", "--post", "fb")
    p = [x for x in _pj(bai)["posts"] if x["channel"] == "facebook"][0]
    assert p["review"]["approved_by"] == "Đức"
    assert p["review"]["note"] == "ok đăng đi", "phải giữ NGUYÊN VĂN câu duyệt"
    assert p["review"]["approved_at"]


def test_facebook_thieu_comment_id_thi_TU_CHOI(bai):
    """Luật hiện hành: thân bài 0 URL. Không có comment là bài mồ côi."""
    _chay(bai, "init")
    _chay(bai, "approve", "--by", "Đ", "--note", "ok", "--post", "fb")
    r = _chay(bai, "set", "--post", "fb", "--platform-id", "123", mong_doi=1)
    assert "comment_id" in r.stderr and "mồ côi" in r.stderr


def test_facebook_KHONG_verify_bang_http(bai, monkeypatch):
    """Có platform_id + comment_id là đủ; không gọi mạng."""
    _chay(bai, "init")
    _chay(bai, "approve", "--by", "Đ", "--note", "ok", "--post", "fb")
    _chay(bai, "set", "--post", "fb", "--link", "https://facebook.com/x",
          "--platform-id", "123", "--comment-id", "456")
    p = [x for x in _pj(bai)["posts"] if x["channel"] == "facebook"][0]
    assert p["publish"]["status"] == "published" and p["publish"]["http"] is None


def test_thay_placeholder_va_cap_nhat_nguoc(bai):
    _chay(bai, "init")
    _chay(bai, "approve", "--by", "Đ", "--note", "ok")
    _chay(bai, "set", "--post", "web", "--link", "https://vidu.vn/a.html", "--no-verify")
    assert "{{BLOG_URL}}" not in PP.p(bai, "fb_comment").read_text(encoding="utf-8")
    assert "https://vidu.vn/a.html" in PP.p(bai, "yt_desc").read_text(encoding="utf-8")
    # ghi ngược: campaign.md, CAMPAIGNS.md, continuity.json
    cam = bai.parent / "campaign.md"
    dong = M.read_table(M.read_fm(cam)[1], "CONTENT")[1][0]
    assert dong["status"] == "published" and dong["published"]
    kenh = bai.parent.parent
    assert M.read_table(M.read_fm(kenh / "CAMPAIGNS.md")[1], "CAMPAIGNS")[1][0]["đã đăng"] == "1"
    cont = json.loads((kenh / "continuity.json").read_text(encoding="utf-8"))
    assert cont[0]["post_id"] == "AST-001"


def test_URL_that_vao_dung_cot_trong_bang_content(bai):
    """Đức 04/09: mở lại bài phải bấm được từ campaign.md, không phải đi lục publish.json."""
    _chay(bai, "init")
    _chay(bai, "approve", "--by", "Đ", "--note", "ok")
    _chay(bai, "set", "--post", "web", "--link", "https://vidu.vn/a.html", "--no-verify")
    _chay(bai, "set", "--post", "yt", "--link", "https://youtu.be/XYZ", "--no-verify")
    _chay(bai, "set", "--post", "fb", "--link", "https://facebook.com/1_2",
          "--platform-id", "1_2", "--comment-id", "2_3", "--no-verify")

    dong = M.read_table(M.read_fm(bai.parent / "campaign.md")[1], "CONTENT")[1][0]
    assert dong["web"] == "https://vidu.vn/a.html"
    assert dong["youtube"] == "https://youtu.be/XYZ"
    assert dong["facebook"] == "https://facebook.com/1_2",         "URL phải vào ĐÚNG cột của nền tảng — vào nhầm cột thì mở ra sai chỗ"


def test_migrate_tu_publish_v1(bai):
    PP.p(bai, "publish").write_text(json.dumps({
        "post_id": "AST-001", "title": "Bài A", "published_at": "2026-09-04T03:34:56+00:00",
        "blog_url": "https://vidu.vn/a.html", "youtube_url": "https://youtu.be/X",
        "fb_permalink": "https://fb.com/p", "fb_post_id": "1_2", "fb_comment_id": "2_3",
        "verified": {"blog_http": 200}}, ensure_ascii=False), encoding="utf-8")
    _chay(bai, "migrate")
    pj = _pj(bai)
    assert pj["schema"] == "publish/2" and pj["migrated_from"] == "publish/1"
    assert len(pj["posts"]) == 3
    web = [p for p in pj["posts"] if p["channel"] == "web_blog"][0]
    assert web["publish"]["http"] == 200 and web["review"]["status"] == "approved"
    _chay(bai, "migrate")   # idempotent
    assert len(_pj(bai)["posts"]) == 3


def test_qa_lay_ket_luan_tu_gates(bai):
    _chay(bai, "init")
    PP.p(bai, "gates").write_text(json.dumps({"ket_luan": "do", "do_chan": 2}), encoding="utf-8")
    _chay(bai, "qa")
    assert all(p["quality_check"] == "failed" for p in _pj(bai)["posts"])
    r = _chay(bai, "approve", "--by", "Đ", "--note", "ok", mong_doi=2)
    assert "override-qa" in r.stderr, "cổng kỹ thuật đỏ thì duyệt phải nêu lý do"
