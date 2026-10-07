# -*- coding: utf-8 -*-
"""test_calendar_pipeline.py — Bộ kiểm thử nghiêm ngặt cho Auto Pipeline by Calendar (2 Pha).

Bao phủ toàn bộ Ma trận kiểm thử (TC1 -> TC7) theo PLAN.md:
- TC1: Chống đăng đúp Page khi Group share bị lỗi
- TC2: Đối soát bài hẹn giờ đã phát sóng (attach_pending comment + group share teaser)
- TC3: Chặn bão Overdue quá hạn lâu (> 7 ngày)
- TC4: Bài đến hạn hôm nay đã duyệt trước (Batch Mode)
- TC5: Bài đến hạn hôm nay chưa có nội dung (Just-in-Time Mode - Suggest)
- TC6: Fallback Group Share khi Meta chặn (100/33)
- TC7: Kiểm thử chế độ --dry-run
"""
from datetime import date
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

import calendar_pipeline as CP
import fb_publish as FB
import md_io


@pytest.fixture(autouse=True)
def mock_post_content():
    with patch("pipeline_state.post_content.has_content", return_value=True):
        yield


@pytest.fixture
def dummy_cfg():
    return {
        "page_id": "PAGE_TEST_123",
        "page_token": "TOKEN_SECRET_XYZ",
    }


@pytest.fixture
def sample_campaign(tmp_path):
    """Tạo fixture thư mục chiến dịch chuẩn có campaign.md và bảng CONTENT."""
    cam_dir = tmp_path / "CMP-2610-test"
    cam_dir.mkdir()

    fm = {
        "id": "CMP-2610-test",
        "channel": "fb",
        "channels": ["facebook", "web"],
        "runtime": {"publish_time": "09:00"},
    }
    body = """# Kế hoạch Chiến dịch Test

<!-- CONTENT:BEGIN -->
| content_id | content_name | schedule | g1 | g2 | web | facebook | published | folder |
|---|---|---|---|---|---|---|---|---|
| P01 | Bài hôm nay duyệt sẵn | 2026-10-07 | 2026-10-01 | 2026-10-05 | https://blog.com/p01 | | | ./p01 |
| P02 | Bài quá hạn trong ngưỡng | 2026-10-05 | 2026-10-01 | 2026-10-04 | https://blog.com/p02 | | | ./p02 |
| P03 | Bài quá hạn lâu bị chặn | 2026-09-15 | 2026-09-01 | | | | | ./p03 |
| P04 | Bài chưa có chữ suggest | 2026-10-07 | 2026-10-01 | | | | | ./p04 |
<!-- CONTENT:END -->
"""
    md_io.write_fm(cam_dir / "campaign.md", fm, body)

    # Dựng folder bài P01 (đã duyệt g2, sẵn sàng release)
    p01_dir = cam_dir / "p01"
    p01_dir.mkdir()
    (p01_dir / "content.md").write_text("# P01\n\n## post:facebook\nBài P01\n\n## post:group_share\nTeaser P01\n", encoding="utf-8")
    (p01_dir / "gates.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
    (p01_dir / "publish.json").write_text(json.dumps({
        "posts": [{"post_id": "p01_fb", "channel": "facebook", "review": {"status": "approved", "approved_by": "Tobi"}}]
    }), encoding="utf-8")

    # Dựng folder bài P02
    p02_dir = cam_dir / "p02"
    p02_dir.mkdir()
    (p02_dir / "content.md").write_text("# P02\n\n## post:facebook\nBài P02\n", encoding="utf-8")
    (p02_dir / "gates.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
    (p02_dir / "publish.json").write_text(json.dumps({
        "posts": [{"post_id": "p02_fb", "channel": "facebook", "review": {"status": "approved", "approved_by": "Tobi"}}]
    }), encoding="utf-8")

    # Dựng folder bài P04 (đã kiểm cổng kỹ thuật, đang chờ duyệt Cổng 2)
    p04_dir = cam_dir / "p04"
    p04_dir.mkdir()
    (p04_dir / "content.md").write_text("# P04\n\n## post:facebook\nBài P04\n", encoding="utf-8")
    (p04_dir / "gates.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")

    return cam_dir


def test_tc1_idempotency_chong_dang_dup_page_khi_group_share_loi(tmp_path, dummy_cfg):
    """TC1: Nếu fb-state.json đã có post_id, lần chạy lại KHÔNG đăng lại Page, chỉ thử lại group share."""
    post_dir = tmp_path / "post_dup"
    post_dir.mkdir()
    msg_file = post_dir / "msg.txt"
    msg_file.write_text("Thân bài Facebook không URL", encoding="utf-8")
    cmt_file = post_dir / "comment.txt"
    cmt_file.write_text("Comment có URL https://example.com/test", encoding="utf-8")
    img_file = post_dir / "img.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    # Đã có state từ lần trước (Page thành công, comment thành công, nhưng group_share lỗi)
    state_file = post_dir / FB.TRANG_THAI
    state_data = {
        "post_id": "EXISTING_PAGE_POST_777",
        "comment_id": "EXISTING_CMT_888",
        "permalink": "https://www.facebook.com/EXISTING_PAGE_POST_777",
        "group_share": {"status": "error", "group_id": "GROUP_TARGET_999", "share_caption": "Teaser test"},
        "share_to_group_id": "GROUP_TARGET_999",
        "share_caption": "Teaser test",
    }
    state_file.write_text(json.dumps(state_data), encoding="utf-8")

    cfg_file = tmp_path / "facebook_config.json"
    cfg_file.write_text(json.dumps(dummy_cfg), encoding="utf-8")

    call_args = [
        "--config", str(cfg_file),
        "--message-file", str(msg_file),
        "--comment-file", str(cmt_file),
        "--image", str(img_file),
        "--share-to-group", "GROUP_TARGET_999",
    ]

    with patch("fb_publish.dang_anh") as mock_dang_anh:
        with patch("fb_publish.chia_se_vao_group", return_value={"status": "shared", "group_id": "GROUP_TARGET_999", "share_id": "NEW_SHARE_111"}) as mock_share:
            rc = FB.main(call_args)

    assert rc == 0
    # Tuyệt đối không gọi dang_anh (không đăng đúp lên Page)
    mock_dang_anh.assert_not_called()
    # Nhưng có gọi chia_se_vao_group để bù phần thiếu
    mock_share.assert_called_once()

    # Kiểm tra state đã được cập nhật
    updated = json.loads(state_file.read_text(encoding="utf-8"))
    assert updated["group_share"]["status"] == "shared"
    assert updated["group_share"]["share_id"] == "NEW_SHARE_111"


def test_tc2_doi_soat_bai_hen_gio_da_phat(tmp_path, dummy_cfg):
    """TC2: Bài hẹn giờ lên sóng thì attach_pending thực hiện cả gắn comment VÀ group share teaser."""
    post_dir = tmp_path / "post_scheduled"
    post_dir.mkdir()
    state_file = post_dir / FB.TRANG_THAI
    state_file.write_text(json.dumps({
        "post_id": "PAGE_SCHED_POST_123",
        "publish_ts": 1000,
        "scheduled": True,
        "comment": "Link bài blog: https://example.com/blog",
        "comment_id": "",
        "share_to_group_id": "GROUP_ABC",
        "share_caption": "Teaser bài hẹn giờ",
        "group_share": {"status": "waiting", "group_id": "GROUP_ABC"},
    }), encoding="utf-8")

    def mock_doc_song(pid):
        return True, f"https://www.facebook.com/{pid}"

    def mock_gui_cmt(pid, msg):
        return "CMT_ID_555"

    def mock_gui_share(gid, link, msg):
        return {"status": "shared", "group_id": gid, "share_id": "SHARE_ID_666", "share_caption": msg}

    results = FB.attach_pending(
        dummy_cfg,
        tmp_path,
        now=2000,
        doc_song=mock_doc_song,
        gui_comment=mock_gui_cmt,
        gui_share_group=mock_gui_share,
    )

    assert len(results) == 1
    assert results[0]["status"] == "attached"
    assert results[0]["comment_id"] == "CMT_ID_555"
    assert results[0]["group_share"]["status"] == "shared"

    updated = json.loads(state_file.read_text(encoding="utf-8"))
    assert updated["comment_id"] == "CMT_ID_555"
    assert updated["group_share"]["share_id"] == "SHARE_ID_666"


def test_tc3_chan_bao_overdue_qua_han_lau(sample_campaign):
    """TC3: Bài quá hạn > 7 ngày (P03) bị chặn vào stale_overdue, không đưa vào danh sách chạy."""
    res = CP.run_calendar_pipeline(
        sample_campaign,
        target_date="2026-10-07",
        lookback_days=3,
        dry_run=True,
    )
    p2 = res["phase2_calendar"]
    assert "P03" in p2["stale_overdue"]
    assert "P03" not in [ex["post"] for ex in p2["executed"]]


def test_tc4_bai_den_han_hom_nay_da_duyet_truoc_batch_mode(sample_campaign):
    """TC4: Bài đến hạn hôm nay đã duyệt trước (P01) được xuất bản ngay đúng lịch."""
    mock_release = MagicMock(return_value={"status": "published", "url": "https://fb.com/p01"})

    res = CP.run_calendar_pipeline(
        sample_campaign,
        target_date="2026-10-07",
        lookback_days=3,
        dry_run=False,
        release_fn=mock_release,
    )
    p2 = res["phase2_calendar"]
    assert "P01" in p2["due_today"]
    ex_p01 = next(ex for ex in p2["executed"] if ex["post"] == "P01")
    assert ex_p01["action"] == "released"
    mock_release.assert_called()


def test_tc4b_step_release_default_path_with_group_share(sample_campaign):
    """TC4b: Gọi step_release qua đường mặc định có truyền bot=None và inject --share-to-group."""
    fm, body = md_io.read_fm(sample_campaign / "campaign.md")
    fm["runtime"]["facebook_cmd"] = "python scripts/pipeline/fb_publish.py --post {post}"
    md_io.write_fm(sample_campaign / "campaign.md", fm, body)

    captured_cmds = []
    def fake_subprocess_run(cmd, **kw):
        captured_cmds.append(list(cmd))
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = json.dumps({"url": "https://facebook.com/123456789"})
        return mock_r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        res = CP.run_calendar_pipeline(
            sample_campaign,
            target_date="2026-10-07",
            lookback_days=3,
            share_to_group="GROUP_INJECT_999",
            dry_run=False,
        )

    p2 = res["phase2_calendar"]
    ex_p01 = next(ex for ex in p2["executed"] if ex["post"] == "P01")
    assert ex_p01["action"] == "released"
    fb_called = next(cmd for cmd in captured_cmds if any("fb_publish" in c for c in cmd))
    assert "--share-to-group" in fb_called
    assert "GROUP_INJECT_999" in fb_called


def test_tc5_bai_chua_co_chu_just_in_time_suggest_mode(sample_campaign):
    """TC5: Bài đến hạn hôm nay chưa có nội dung (P04) dừng ở Cổng 2, ghi nhận waiting_approval."""
    res = CP.run_calendar_pipeline(
        sample_campaign,
        target_date="2026-10-07",
        dry_run=True,
    )
    p2 = res["phase2_calendar"]
    assert "P04" in p2["due_today"]
    # P04 chưa qua Cổng 2, ghi nhận chờ duyệt
    assert any(w["post"] == "P04" for w in p2["waiting_approval"])


def test_tc6_fallback_group_share_khi_meta_chan(dummy_cfg, capsys):
    """TC6: Khi Graph API trả lỗi 100/33, ghi nhận manual_share_needed và in FB_GROUP_SHARE_CAPTION."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": {"code": 100, "message": "Graph API groups deprecated"}}
    mock_resp.text = '{"error":{"code":100}}'

    with patch("requests.post", return_value=mock_resp):
        res = FB.chia_se_vao_group(
            dummy_cfg,
            "GROUP_ERR_123",
            "https://www.facebook.com/123",
            share_message="Hook đặc biệt khi Meta lỗi",
        )

    assert res["status"] == "manual_share_needed"
    assert "https://www.facebook.com/sharer/sharer.php" in res["share_url"]
    assert res["share_caption"] == "Hook đặc biệt khi Meta lỗi"

    captured = capsys.readouterr()
    assert "Graph API từ chối (100)" in captured.out
    assert "FB_GROUP_SHARE_CAPTION=Hook đặc biệt khi Meta lỗi" in captured.out


def test_tc7_kiem_thu_dry_run(sample_campaign):
    """TC7: Chế độ --dry-run không gọi API hay thay đổi file state."""
    res = CP.run_calendar_pipeline(
        sample_campaign,
        target_date="2026-10-07",
        dry_run=True,
    )
    assert res["dry_run"] is True
    p2 = res["phase2_calendar"]
    assert "P01" in p2["due_today"]
    assert "P02" in p2["overdue_recoverable"]
    assert "P03" in p2["stale_overdue"]
    for ex in p2["executed"]:
        assert "dry_run" in ex["action"]


def test_tc8_nested_failure_visibility_in_report(sample_campaign):
    """TC8: Khi step_release trả về failed posts, action đổi thành release_failed và báo cáo in ❌."""
    mock_failed_release = MagicMock(return_value={
        "step": "release",
        "xu_ly": 0,
        "post": [],
        "failed": [{"post": "P01", "reason": "Facebook API token expired"}],
    })

    res = CP.run_calendar_pipeline(
        sample_campaign,
        target_date="2026-10-07",
        dry_run=False,
        release_fn=mock_failed_release,
    )
    p2 = res["phase2_calendar"]
    ex_p01 = next(ex for ex in p2["executed"] if ex["post"] == "P01")
    assert ex_p01["action"] == "release_failed"
    assert "Facebook API token expired" in ex_p01["error"]

    report = CP.format_report(res)
    assert "❌ **P01**: `release_failed`" in report
    assert "Facebook API token expired" in report


def test_tc9_custom_hook_warning_when_unrecognized(sample_campaign, capsys):
    """TC9: Cảnh báo ra stderr nếu hook Facebook không nhận diện được để inject --share-to-group."""
    fm, body = md_io.read_fm(sample_campaign / "campaign.md")
    fm["runtime"]["facebook_cmd"] = "custom_tool_facebook --post {post}"
    md_io.write_fm(sample_campaign / "campaign.md", fm, body)

    def fake_subprocess_run(cmd, **kw):
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = json.dumps({"url": "https://facebook.com/custom_hook"})
        return mock_r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        CP.run_calendar_pipeline(
            sample_campaign,
            target_date="2026-10-07",
            share_to_group="GROUP_XYZ",
            dry_run=False,
        )

    err = capsys.readouterr().err
    assert "facebook hook không nhận diện được để inject --share-to-group" in err

