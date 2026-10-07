# -*- coding: utf-8 -*-
"""test_group_share_teaser.py — kiểm thử tính năng teaser caption khi chia sẻ bài vào Facebook Group."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "runners"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))

import fb_publish as FB
import gen_article as GA
import post_facebook as PF


@pytest.fixture
def dummy_cfg():
    return {
        "page_id": "PAGE_TEST_123",
        "page_token": "TOKEN_SECRET_XYZ",
    }


def test_gen_article_extracts_group_share(tmp_path):
    """gen_article trích xuất khối ## post:group_share ra facebook/group_share.txt nguyên tử."""
    post_dir = tmp_path / "post_01"
    post_dir.mkdir()
    content_md = post_dir / "content.md"
    content_md.write_text("""# Tiêu đề bài viết

## post:facebook
Nội dung bài viết Facebook dài ở đây.

## post:group_share
💡 3 bài học đắt giá khi triển khai AI Agent:
- Bài học 1: Fail-closed an toàn
- Bài học 2: Không lưu secret trong prompt
- Bài học 3: Tối ưu token theo ngữ cảnh

Mời mọi người cùng thảo luận bên dưới! 👇
""", encoding="utf-8")

    meta_json = post_dir / "meta.json"
    meta_json.write_text(json.dumps({"content_id": "P01", "post_type": "article"}), encoding="utf-8")

    parts = GA.split_content(content_md.read_text(encoding="utf-8"))
    assert "fb_group_share" in parts
    da_ghi = GA.write_outputs(parts, str(post_dir))

    share_file = post_dir / "facebook" / "group_share.txt"
    assert share_file.is_file()
    assert str(share_file) == da_ghi.get("fb_group_share")
    text = share_file.read_text(encoding="utf-8").strip()
    assert "3 bài học đắt giá" in text
    assert "Mời mọi người cùng thảo luận" in text


def test_gen_article_cleans_group_share_when_removed(tmp_path):
    """gen_article tự động xóa facebook/group_share.txt khi section ## post:group_share bị gỡ."""
    post_dir = tmp_path / "post_02"
    fb_dir = post_dir / "facebook"
    fb_dir.mkdir(parents=True)
    old_file = fb_dir / "group_share.txt"
    old_file.write_text("Teaser cũ", encoding="utf-8")

    content_md = post_dir / "content.md"
    content_md.write_text("""# Tiêu đề bài viết

## post:facebook
Chỉ còn bài Facebook, không còn group_share.
""", encoding="utf-8")

    parts = GA.split_content(content_md.read_text(encoding="utf-8"))
    assert "fb_group_share" not in parts
    GA.write_outputs(parts, str(post_dir))
    assert not old_file.exists()


def test_chia_se_vao_group_with_teaser_message(dummy_cfg, capsys):
    """chia_se_vao_group truyền message khi chia sẻ link và in FB_GROUP_SHARE_CAPTION."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "GROUP_SHARE_123456"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = FB.chia_se_vao_group(
            dummy_cfg,
            "GROUP_888",
            "https://www.facebook.com/123/posts/456",
            share_message="🔥 Hook teaser cực đỉnh cho Group",
        )

    assert res["status"] == "shared"
    assert res["share_id"] == "GROUP_SHARE_123456"
    assert res["share_caption"] == "🔥 Hook teaser cực đỉnh cho Group"

    mock_post.assert_called_once()
    called_data = mock_post.call_args[1]["data"]
    assert called_data["link"] == "https://www.facebook.com/123/posts/456"
    assert called_data["message"] == "🔥 Hook teaser cực đỉnh cho Group"

    captured = capsys.readouterr()
    assert "FB_GROUP_SHARE_ID=GROUP_SHARE_123456" in captured.out
    assert "FB_GROUP_SHARE_CAPTION=🔥 Hook teaser cực đỉnh cho Group" in captured.out


def test_chia_se_vao_group_fallback_with_caption(dummy_cfg, capsys):
    """Khi Meta chặn Groups API, chia_se_vao_group in FB_GROUP_SHARE_CAPTION và link Web Share."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": {"message": "Unsupported post request", "code": 100}}
    mock_resp.text = '{"error":{"message":"Unsupported post request","code":100}}'

    with patch("requests.post", return_value=mock_resp):
        res = FB.chia_se_vao_group(
            dummy_cfg,
            "GROUP_888",
            "https://www.facebook.com/123/posts/456",
            share_message="🔥 Hook teaser khi fallback",
        )

    assert res["status"] == "manual_share_needed"
    assert res["share_caption"] == "🔥 Hook teaser khi fallback"
    assert "https://www.facebook.com/sharer/sharer.php" in res["share_url"]

    captured = capsys.readouterr()
    assert "Graph API từ chối (100)" in captured.out
    assert "Web Share URL: https://www.facebook.com/sharer/sharer.php" in captured.out
    assert "FB_GROUP_SHARE_CAPTION=🔥 Hook teaser khi fallback" in captured.out


def test_post_facebook_cli_with_share_message_file(tmp_path, dummy_cfg, capsys):
    """post_facebook.py đọc --share-message-file và truyền caption khi gọi share_to_group."""
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Nội dung bài dài trên Fanpage.", encoding="utf-8")
    teaser_file = tmp_path / "group_share.txt"
    teaser_file.write_text("Tóm tắt 3 ý chính cho nhóm thảo luận.", encoding="utf-8")

    test_args = [
        "post_facebook.py",
        "--message-file", str(msg_file),
        "--share-to-group", "GROUP_TARGET_777",
        "--share-message-file", str(teaser_file),
    ]

    with patch("post_facebook._cfg", return_value=dummy_cfg):
        with patch("post_facebook.post_link", return_value="PAGE_POST_111"):
            with patch("post_facebook.post_to_group", return_value="GROUP_POST_SHARE_222") as mock_share:
                with patch.object(sys, "argv", test_args):
                    rc = PF.main()

    assert rc == 0
    mock_share.assert_called_once()
    assert mock_share.call_args[1]["message"] == "Tóm tắt 3 ý chính cho nhóm thảo luận."
    captured = capsys.readouterr()
    assert "FB_POST_ID=PAGE_POST_111" in captured.out
    assert "FB_GROUP_SHARE_ID=GROUP_POST_SHARE_222" in captured.out
    assert "FB_GROUP_SHARE_CAPTION=Tóm tắt 3 ý chính cho nhóm thảo luận." in captured.out
