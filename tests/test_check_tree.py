# -*- coding: utf-8 -*-
"""Test cho check_tree — cổng bắt liên kết gãy.

Cách test: dựng một cây ĐÚNG, khẳng định xanh; rồi bẻ TỪNG cạnh một và khẳng định đỏ
ĐÚNG LÝ DO. Chỉ khẳng định "có đỏ" là vô dụng — cổng bắt nhầm cạnh vẫn qua được.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import check_tree as CT  # noqa: E402
import md_io as M  # noqa: E402
import post_paths as PP  # noqa: E402

PY = sys.executable


@pytest.fixture
def cay(tmp_path):
    """Cây ĐÚNG: 1 kênh · 1 chiến dịch · 1 bài."""
    S = tmp_path / "st"
    K = S / "tobi"
    C = K / "CMP-2609-x"
    B = C / "AST-001_slug"
    PP.tao_thu_muc(B)
    M.write_fm(S / "CHANNELS.md", {"schema": "channels/1", "channels": [
        {"id": "tobi", "label": "Tobi", "path": "./tobi", "status": "active"}]}, "# Sổ\n")
    (K / "channel.yml").write_text(
        "schema: channel/1\nid: tobi\npillars: [ai-agent]\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8")
    M.write_fm(K / "CAMPAIGNS.md", {"schema": "campaigns/1", "channel": "tobi"},
               "\n<!-- CAMPAIGNS:BEGIN -->\n| campaign_id | bài | đã đăng |\n|---|---|---|\n"
               "| CMP-2609-x | 1 | 0 |\n<!-- CAMPAIGNS:END -->\n")
    M.write_fm(C / "campaign.md",
               {"id": "CMP-2609-x", "channel": "tobi", "id_prefix": "AST",
                "content_pillar": "ai-agent", "channels": ["web_blog"], "status": "proposed"},
               "\n<!-- CONTENT:BEGIN -->\n| content_id | status | g1 | published | folder |\n"
               "|---|---|---|---|---|\n| AST-001 | proposed |  |  | ./AST-001_slug/ |\n"
               "<!-- CONTENT:END -->\n")
    json.dump({"post_id": "AST-001", "campaign_id": "CMP-2609-x", "slug": "slug"},
              (B / "meta.json").open("w", encoding="utf-8"), ensure_ascii=False)
    M.write_fm(B / "research.md", {"content_id": "AST-001", "campaign_id": "CMP-2609-x"}, "")
    (B / "content.md").write_text("## post:blog_article\nA\n", encoding="utf-8")
    json.dump({"schema": "publish/2", "post_id": "AST-001", "campaign_id": "CMP-2609-x",
               "channel_id": "tobi", "posts": []},
              (B / "publish.json").open("w", encoding="utf-8"), ensure_ascii=False)
    return S, K, C, B


def test_cay_dung_thi_XANH(cay):
    s = CT.chay(cay[0])
    assert s.do == [], f"cây đúng mà báo đỏ: {s.do}"


def test_path_trong_CHANNELS_chet(cay):
    S = cay[0]
    fm, body = M.read_fm(S / "CHANNELS.md")
    fm["channels"][0]["path"] = "./khong-ton-tai"
    M.write_fm(S / "CHANNELS.md", fm, body)
    assert any("không tồn tại" in x for x in CT.chay(S).do)


def test_thu_muc_chien_dich_mo_coi(cay):
    S, K, _, _ = cay
    (K / "CMP-2609-y").mkdir()
    M.write_fm(K / "CMP-2609-y" / "campaign.md", {"id": "CMP-2609-y", "channel": "tobi"}, "")
    assert any("mồ côi" in x and "CMP-2609-y" in x for x in CT.chay(S).do)


def test_bai_co_thu_muc_ma_khong_co_dong_trong_bang(cay):
    S, _, C, _ = cay
    B2 = C / "AST-002_khac"
    B2.mkdir()
    json.dump({"post_id": "AST-002"}, (B2 / "meta.json").open("w", encoding="utf-8"))
    assert any("mồ côi" in x and "AST-002" in x for x in CT.chay(S).do)


def test_dong_trong_bang_ma_khong_co_thu_muc(cay):
    S, _, C, _ = cay
    fm, body = M.read_fm(C / "campaign.md")
    body = M.upsert_row(body, "CONTENT", "content_id",
                        {"content_id": "AST-009", "folder": "./AST-009_ao/"})
    M.write_fm(C / "campaign.md", fm, body)
    assert any("AST-009_ao" in x and "không tồn tại" in x for x in CT.chay(S).do)


def test_id_campaign_lech_ten_thu_muc(cay):
    S, _, C, _ = cay
    fm, body = M.read_fm(C / "campaign.md")
    fm["id"] = "CMP-2609-KHAC"
    M.write_fm(C / "campaign.md", fm, body)
    assert any("≠ tên thư mục" in x for x in CT.chay(S).do)


def test_pillar_ngoai_bo_cua_kenh(cay):
    S, _, C, _ = cay
    fm, body = M.read_fm(C / "campaign.md")
    fm["content_pillar"] = "khong-co-trong-kenh"
    M.write_fm(C / "campaign.md", fm, body)
    assert any("pillars" in x for x in CT.chay(S).do)


def test_neo_post_content_khong_co_trong_content_md(cay):
    S, _, _, B = cay
    pj = json.loads((B / "publish.json").read_text(encoding="utf-8"))
    pj["posts"] = [{"post_id": "AST-001-web", "channel": "web_blog",
                    "post_format": "blog_article", "post_content": "post:khong_co",
                    "review": {}, "publish": {}}]
    (B / "publish.json").write_text(json.dumps(pj, ensure_ascii=False), encoding="utf-8")
    assert any("không có khối đó" in x for x in CT.chay(S).do)


def test_approved_ma_khong_ghi_ai_duyet(cay):
    S, _, _, B = cay
    pj = json.loads((B / "publish.json").read_text(encoding="utf-8"))
    pj["posts"] = [{"post_id": "AST-001-web", "channel": "web_blog",
                    "post_format": "blog_article", "post_content": "post:blog_article",
                    "review": {"status": "approved", "approved_by": ""}, "publish": {}}]
    (B / "publish.json").write_text(json.dumps(pj, ensure_ascii=False), encoding="utf-8")
    assert any("Cổng 2 phải có dấu vết" in x for x in CT.chay(S).do)


def test_fb_da_dang_ma_thieu_comment_id(cay):
    S, _, _, B = cay
    pj = json.loads((B / "publish.json").read_text(encoding="utf-8"))
    pj["posts"] = [{"post_id": "AST-001-fb", "channel": "facebook",
                    "post_format": "facebook_post", "post_content": "",
                    "review": {"status": "approved", "approved_by": "Đ"},
                    "publish": {"status": "published", "link": "x", "comment_id": ""}}]
    (B / "publish.json").write_text(json.dumps(pj, ensure_ascii=False), encoding="utf-8")
    assert any("mồ côi" in x for x in CT.chay(S).do)


def test_cli_exit_khac_0_khi_do(cay):
    S = cay[0]
    fm, body = M.read_fm(S / "CHANNELS.md")
    fm["channels"][0]["path"] = "./chet"
    M.write_fm(S / "CHANNELS.md", fm, body)
    r = subprocess.run([PY, str(ROOT / "scripts/pipeline/check_tree.py"), "--station", str(S)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "ĐỎ" in r.stdout
