# -*- coding: utf-8 -*-
"""test_fb_group_publish.py — kiểm thử tính năng đăng bài và kiểm tra quyền Facebook Group dưới tư cách Page.

Kiểm tra:
- Đăng bài text/link vào Group qua endpoint /{group_id}/feed với page_token.
- Đăng ảnh vào Group qua endpoint /{group_id}/photos với page_token.
- Bắt lỗi khi Page chưa tham gia Group hoặc thiếu quyền.
- Kiểm tra quyền Group qua check_fb_scopes.check_group.
- Cờ --group-id và --dry-run trong post_facebook.py.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "runners"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))

import check_fb_scopes as CS
import fb_publish as FB
import post_facebook as PF


@pytest.fixture
def dummy_cfg():
    return {
        "page_id": "PAGE_111",
        "page_name": "Test Page",
        "page_token": "TEST_PAGE_TOKEN_SECRET_XYZ",
    }


@pytest.fixture
def dummy_config_file(tmp_path, dummy_cfg):
    cfg_file = tmp_path / "facebook_config.json"
    cfg_file.write_text(json.dumps(dummy_cfg), encoding="utf-8")
    return str(cfg_file)


@pytest.fixture
def dummy_image(tmp_path):
    img = tmp_path / "test_image.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return str(img)


def test_post_to_group_success(dummy_cfg):
    """Đăng bài text lên Group thành công qua /{group_id}/feed bằng page_token."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"id": "GROUP_POST_12345"}
    mock_resp.status_code = 200

    with patch("requests.post", return_value=mock_resp) as mock_post:
        post_id = PF.post_to_group(dummy_cfg, "GROUP_999", "Nội dung bài viết", link="https://example.com/test")

    assert post_id == "GROUP_POST_12345"
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_data = mock_post.call_args[1]["data"]

    assert called_url == "https://graph.facebook.com/v21.0/GROUP_999/feed"
    assert called_data["message"] == "Nội dung bài viết"
    assert called_data["link"] == "https://example.com/test"
    assert called_data["access_token"] == "TEST_PAGE_TOKEN_SECRET_XYZ"


def test_post_to_group_permission_error(dummy_cfg):
    """Bắt lỗi khi Page chưa tham gia Group hoặc chưa có quyền."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "message": "(#200) Insufficient permissions to post to group",
            "type": "OAuthException",
            "code": 200,
        }
    }
    mock_resp.text = "Permission error"

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError) as exc_info:
            PF.post_to_group(dummy_cfg, "GROUP_999", "Nội dung test")

    err_msg = str(exc_info.value)
    assert "chưa tham gia Group" in err_msg or "chưa được cấp quyền" in err_msg


def test_post_group_photo_success(dummy_cfg, dummy_image):
    """Đăng ảnh lên Group thành công qua /{group_id}/photos bằng page_token."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "PHOTO_777", "post_id": "POST_888"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        photo_id, post_id = PF.post_group_photo(dummy_cfg, "GROUP_999", dummy_image, caption="Ảnh infographic")

    assert photo_id == "PHOTO_777"
    assert post_id == "POST_888"
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_data = mock_post.call_args[1]["data"]

    assert called_url == "https://graph.facebook.com/v21.0/GROUP_999/photos"
    assert called_data["message"] == "Ảnh infographic"
    assert called_data["access_token"] == "TEST_PAGE_TOKEN_SECRET_XYZ"


def test_check_fb_scopes_group_success(dummy_config_file):
    """Kiểm tra quyền của Page trên Group khi đã được cấp quyền."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "name": "Cộng đồng AI & Data",
        "id": "GROUP_999",
        "privacy": "CLOSED",
        "administrator": True,
    }

    with patch("requests.get", return_value=mock_resp):
        ok = CS.check_group(dummy_config_file, "GROUP_999")

    assert ok is True


def test_check_fb_scopes_group_denied(dummy_config_file):
    """Kiểm tra quyền của Page trên Group khi chưa được thêm vào Group."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "message": "Cannot access group",
            "code": 200,
            "error_subcode": 1373053,
        }
    }
    mock_resp.text = "Cannot access group"

    with patch("requests.get", return_value=mock_resp):
        ok = CS.check_group(dummy_config_file, "GROUP_999")

    assert ok is False


def test_fb_publish_dang_anh_group(dummy_cfg, dummy_image):
    """fb_publish.dang_anh đăng ảnh vào Group endpoint đúng và published=true."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "GRP_PHOTO_1", "post_id": "GRP_POST_1"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        photo_id, post_id = FB.dang_anh(dummy_cfg, "Caption bài blog", dummy_image, group_id="GROUP_555")

    assert photo_id == "GRP_PHOTO_1"
    assert post_id == "GRP_POST_1"
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_data = mock_post.call_args[1]["data"]

    assert called_url == "https://graph.facebook.com/v21.0/GROUP_555/photos"
    assert called_data["published"] == "true"
    assert called_data["access_token"] == "TEST_PAGE_TOKEN_SECRET_XYZ"


def test_post_facebook_cli_group_dry_run(tmp_path, capsys):
    """Kiểm tra CLI post_facebook.py với --dry-run và --group-id."""
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Tiêu đề bài viết\nNội dung chi tiết bài viết.", encoding="utf-8")

    test_args = [
        "post_facebook.py",
        "--dry-run",
        "--group-id", "99998888",
        "--message-file", str(msg_file),
    ]

    with patch.object(sys, "argv", test_args):
        rc = PF.main()

    assert rc == 0
    captured = capsys.readouterr()
    assert "DRY-RUN" in captured.out
    assert "99998888" in captured.out
    assert "Facebook GROUP" in captured.out


def test_post_facebook_cli_group_photo_execution(tmp_path, dummy_cfg, dummy_image, capsys):
    """Kiểm tra CLI post_facebook.py đăng ảnh vào Group lấy đúng post_id."""
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Bài viết kèm ảnh infographic.", encoding="utf-8")

    test_args = [
        "post_facebook.py",
        "--group-id", "777888",
        "--message-file", str(msg_file),
        "--image", dummy_image,
    ]

    with patch("post_facebook._cfg", return_value=dummy_cfg):
        with patch("post_facebook.post_group_photo", return_value=("PHOTO_ID_123", "POST_ID_456")):
            with patch.object(sys, "argv", test_args):
                rc = PF.main()

    assert rc == 0
    captured = capsys.readouterr()
    assert "FB_POST_ID=POST_ID_456" in captured.out
    assert "FB_TARGET=group:777888" in captured.out
    assert "FB_MODE=group-photo" in captured.out


def test_check_fb_scopes_non_json_error(dummy_config_file):
    """check_group xử lý an toàn khi Facebook trả về HTML error thay vì JSON."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 502
    mock_resp.json.side_effect = ValueError("No JSON object could be decoded")
    mock_resp.text = "<html>502 Bad Gateway</html>"

    with patch("requests.get", return_value=mock_resp):
        ok = CS.check_group(dummy_config_file, "GROUP_999")

    assert ok is False


def test_chia_se_vao_group_api_success(dummy_cfg):
    """chia_se_vao_group chia sẻ link thành công qua Graph API."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "GROUP_POST_SHARE_999"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = FB.chia_se_vao_group(dummy_cfg, "GROUP_777", "https://www.facebook.com/111/posts/222")

    assert res["status"] == "shared"
    assert res["share_id"] == "GROUP_POST_SHARE_999"
    mock_post.assert_called_once()
    called_data = mock_post.call_args[1]["data"]
    assert called_data["link"] == "https://www.facebook.com/111/posts/222"


def test_chia_se_vao_group_meta_deprecation_fallback(dummy_cfg):
    """chia_se_vao_group xử lý fallback khi Meta chặn Groups API (Error 100/33)."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": {"message": "Unsupported post request", "code": 100}}
    mock_resp.text = '{"error":{"message":"Unsupported post request","code":100}}'

    with patch("requests.post", return_value=mock_resp):
        res = FB.chia_se_vao_group(dummy_cfg, "GROUP_777", "https://www.facebook.com/111/posts/222")

    assert res["status"] == "manual_share_needed"
    assert "https://www.facebook.com/sharer/sharer.php" in res["share_url"]


def test_post_facebook_cli_share_to_group(tmp_path, dummy_cfg, capsys):
    """post_facebook.py gọi share_to_group khi đăng bài lên Page thành công."""
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("Nội dung bài viết trên Page.", encoding="utf-8")

    test_args = [
        "post_facebook.py",
        "--message-file", str(msg_file),
        "--share-to-group", "GROUP_TARGET_123",
    ]

    with patch("post_facebook._cfg", return_value=dummy_cfg):
        with patch("post_facebook.post_link", return_value="PAGE_POST_777"):
            with patch("post_facebook.post_to_group", return_value="GROUP_POST_888"):
                with patch.object(sys, "argv", test_args):
                    rc = PF.main()

    assert rc == 0
    captured = capsys.readouterr()
    assert "FB_POST_ID=PAGE_POST_777" in captured.out
    assert "FB_GROUP_SHARE_ID=GROUP_POST_888" in captured.out
