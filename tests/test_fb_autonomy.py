# -*- coding: utf-8 -*-
"""Cổng tự trị của `fb_publish` — lời hứa an toàn phải là CỔNG MÁY, không phải câu văn.

Trang công khai và 4 tài liệu đều nói *"script từ chối chạy thật trừ khi kênh đặt
`autonomy: full`"*. Trước 05/09 **không script nào đọc `autonomy`** — lời bảo đảm đó chỉ
là luật cho agent đọc. Một lời hứa an toàn mà không có gì thi hành thì tệ hơn không hứa,
vì người ta dựa vào nó.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SCRIPT = ROOT / "scripts" / "pipeline" / "fb_publish.py"


@pytest.fixture
def bai(tmp_path):
    """Một bài HỢP LỆ hoàn toàn — mọi cổng nội dung đều qua, chỉ còn cổng tự trị."""
    K = tmp_path / "kenh"
    B = K / "CMP-2609-x" / "AST-001_a" / "facebook"
    B.mkdir(parents=True)
    (K / "channel.yml").write_text("schema: channel/1\nid: k\nautonomy: suggest\n",
                                   encoding="utf-8")
    (B / "post.txt").write_text("Thân bài không có URL nào cả.\n", encoding="utf-8")
    (B / "comment.txt").write_text("Bản đầy đủ: https://vidu.vn/a.html\n", encoding="utf-8")
    (B / "anh.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
    (B.parent / "publish.json").write_text(json.dumps({
        "schema": "publish/2", "post_id": "AST-001", "posts": [
            {"post_id": "AST-001-fb", "channel": "facebook", "post_format": "facebook_post",
             "quality_check": "passed",
             "review": {"status": "approved", "approved_by": "Người duyệt", "note": "ok"},
             "publish": {}}]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "cfg.json").write_text(json.dumps({"page_id": "1", "page_token": "x"}),
                                       encoding="utf-8")
    return tmp_path, K, B


def _chay(tmp, B, bai_dir, them=()):
    return subprocess.run(
        [PY, str(SCRIPT), "--config", str(tmp / "cfg.json"),
         "--message-file", str(B / "post.txt"), "--image", str(B / "anh.png"),
         "--comment-file", str(B / "comment.txt"), "--bai", str(bai_dir), *them],
        capture_output=True, text=True, encoding="utf-8")


def test_suggest_thi_TU_CHOI_dang_that(bai):
    tmp, K, B = bai
    r = _chay(tmp, B, B.parent)
    assert r.returncode == 4, "phải từ chối, và bằng một mã thoát riêng"
    assert "mức tự trị của kênh là 'suggest'" in r.stderr
    assert str(K / "channel.yml") in r.stderr, "phải nói rõ đọc từ FILE NÀO"


def test_KHONG_tim_thay_channel_yml_thi_coi_nhu_CHUA_CHO_PHEP(bai):
    """Fail-closed. Không biết mức tự trị mà vẫn đăng là đúng kiểu lỗi tệ nhất."""
    tmp, K, B = bai
    (K / "channel.yml").unlink()
    r = _chay(tmp, B, B.parent)
    assert r.returncode == 4 and "không thấy channel.yml" in r.stderr


def test_thieu_bai_cung_la_CHUA_CHO_PHEP(bai):
    tmp, K, B = bai
    r = subprocess.run(
        [PY, str(SCRIPT), "--config", str(tmp / "cfg.json"),
         "--message-file", str(B / "post.txt"), "--image", str(B / "anh.png"),
         "--comment-file", str(B / "comment.txt")],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 4
    assert "Thiếu --bai" in r.stderr and "Cổng 2" in r.stderr


def test_dry_run_van_chay_duoc_khi_suggest(bai):
    """Cổng chỉ chặn ĐĂNG THẬT. Kiểm thử phải luôn chạy được, nếu không người ta bỏ kiểm."""
    tmp, K, B = bai
    r = _chay(tmp, B, B.parent, ["--dry-run"])
    assert r.returncode == 0 and "dry-run" in r.stdout


def test_full_thi_KHONG_bi_cong_tu_tri_chan(bai):
    """Đặt `full` thì cổng này mở — bằng chứng: lỗi tiếp theo là lỗi MẠNG, không phải cổng."""
    tmp, K, B = bai
    (K / "channel.yml").write_text("schema: channel/1\nid: k\nautonomy: full\n",
                                   encoding="utf-8")
    r = _chay(tmp, B, B.parent)
    assert r.returncode != 4, f"autonomy=full mà vẫn bị cổng tự trị chặn:\n{r.stderr}"
    assert "mức tự trị" not in r.stderr


# ══════════════════════════════════════════════════════ Cổng 2 (Codex chỉ ra 05/09)

def test_CHUA_qua_Cong_2_thi_khong_dang_du_kenh_la_full(bai):
    """Cổng tự trị trả lời 'kênh này có được đăng tự động không'. Cổng 2 trả lời 'bài NÀY có
    được đăng không'. Thiếu câu thứ hai thì bài chưa ai duyệt vẫn lên."""
    tmp, K, B = bai
    (K / "channel.yml").write_text("schema: channel/1\nid: k\nautonomy: full\n",
                                   encoding="utf-8")
    pj = json.loads((B.parent / "publish.json").read_text(encoding="utf-8"))
    pj["posts"][0]["review"] = {"status": "pending"}
    (B.parent / "publish.json").write_text(json.dumps(pj, ensure_ascii=False), encoding="utf-8")

    r = _chay(tmp, B, B.parent)
    assert r.returncode == 4 and "chưa qua Cổng 2" in r.stderr
    assert "review.status='pending'" in r.stderr


def test_duyet_ma_KHONG_ghi_ai_duyet_thi_khong_tinh(bai):
    tmp, K, B = bai
    (K / "channel.yml").write_text("schema: channel/1\nid: k\nautonomy: full\n",
                                   encoding="utf-8")
    pj = json.loads((B.parent / "publish.json").read_text(encoding="utf-8"))
    pj["posts"][0]["review"] = {"status": "approved", "approved_by": "  "}
    (B.parent / "publish.json").write_text(json.dumps(pj, ensure_ascii=False), encoding="utf-8")
    r = _chay(tmp, B, B.parent)
    assert r.returncode == 4 and "approved_by" in r.stderr


def test_KHONG_MUON_duoc_kenh_full_cua_bai_khac(bai, tmp_path):
    """`--bai` trỏ sang một kênh `full` bất kỳ trong khi nội dung là của kênh khác — cổng
    tự trị khi đó đang gác một thứ không liên quan tới thứ sắp đăng."""
    tmp, K, B = bai
    K2 = tmp_path / "kenh_full"
    (K2 / "CMP-x" / "BAI-1").mkdir(parents=True)
    (K2 / "channel.yml").write_text("schema: channel/1\nid: k2\nautonomy: full\n",
                                    encoding="utf-8")
    r = _chay(tmp, B, K2 / "CMP-x" / "BAI-1")
    assert r.returncode == 4
    assert "không chứa" in r.stderr, "phải từ chối vì --bai không chứa nội dung đang đăng"


def test_qua_ca_hai_cong_thi_di_tiep(bai):
    tmp, K, B = bai
    (K / "channel.yml").write_text("schema: channel/1\nid: k\nautonomy: full\n",
                                   encoding="utf-8")
    r = _chay(tmp, B, B.parent)
    assert r.returncode != 4, f"đủ cả hai cổng mà vẫn bị chặn:\n{r.stderr}"
    assert "Cổng 2 OK" in r.stdout
