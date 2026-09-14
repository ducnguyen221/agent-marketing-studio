# -*- coding: utf-8 -*-
"""Đăng Facebook HẸN GIỜ — hai pha, không đăng trùng, không bài mồ côi.

Facebook không cho comment vào bài chưa phát, mà comment là chỗ DUY NHẤT chứa link về blog.
Nên hẹn giờ phải tách: pha một hẹn bài, pha hai gắn comment sau giờ phát. Mỗi test ở đây
gác một cách hai pha đó có thể hỏng mà không ai thấy.
"""
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import fb_publish as FB  # noqa: E402


@pytest.fixture
def post(tmp_path, monkeypatch):
    """Bài qua đủ Cổng 2 và kênh `autonomy: full`, Graph bị thay bằng bản giả ghi lại lượt gọi."""
    K = tmp_path / "kenh"
    B = K / "CMP-2609-x" / "AST-001_a" / "facebook"
    B.mkdir(parents=True)
    import md_io as _M
    _M.write_fm(tmp_path / "CHANNELS.md", {"schema": "channels/1", "channels": [
        {"id": "k", "label": "K", "path": str(K), "status": "active"}]}, "# Sổ\n")
    (K / "channel.yml").write_text("schema: channel/1\nid: k\nautonomy: full\n", encoding="utf-8")
    (B / "post.txt").write_text("Thân bài không có URL nào cả.\n", encoding="utf-8")
    (B / "comment.txt").write_text("Đọc bản đầy đủ: {{BLOG_URL}}\nXem video: {{YOUTUBE_URL}}\n",
                                   encoding="utf-8")
    (B / "anh.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
    (B.parent / "publish.json").write_text(json.dumps({
        "schema": "publish/2", "post_id": "AST-001", "posts": [
            {"post_id": "AST-001-fb", "channel": "facebook", "post_format": "facebook_post",
             "quality_check": "passed",
             "review": {"status": "approved", "approved_by": "Người duyệt", "note": "ok"},
             "publish": {}}]}, ensure_ascii=False), encoding="utf-8")
    # Ảnh mẫu ĐÃ SOÁT CHỮ, gắn với đúng byte của nó — cổng soát chữ so sha256.
    import hashlib as _h
    (B / "anh.meta.json").write_text(json.dumps({"schema": "fb-image/1", "text_check": {
        "status": "passed", "by": "Người soát", "quote": "chữ đúng dấu", "at": "2026-09-14T09:00:00",
        "image_sha256": _h.sha256((B / "anh.png").read_bytes()).hexdigest()}}), encoding="utf-8")
    (tmp_path / "cfg.json").write_text(json.dumps({"page_id": "1", "page_token": "x"}),
                                       encoding="utf-8")

    goi = {"anh": [], "comment": []}

    def dang_anh(cfg, msg, img, publish_ts=None):
        goi["anh"].append(publish_ts)
        return "PHOTO1", "PAGE_POST1"

    def dang_comment(cfg, pid, msg):
        goi["comment"].append((pid, msg))
        return "CMT1"

    monkeypatch.setattr(FB, "dang_anh", dang_anh)
    monkeypatch.setattr(FB, "dang_comment", dang_comment)
    monkeypatch.setattr(FB.time, "sleep", lambda s: None)
    return tmp_path, B, goi


def _argv(tmp, B, *them, blog="https://x.vn/bai"):
    """Giống hook thật: chiến dịch chưa có video nên link YouTube truyền xuống là RỖNG."""
    fill = ["--fill", "YOUTUBE_URL="]
    if blog is not None:
        fill += ["--fill", f"BLOG_URL={blog}"]
    return ["--config", str(tmp / "cfg.json"), "--message-file", str(B / "post.txt"),
            "--image", str(B / "anh.png"), "--comment-file", str(B / "comment.txt"),
            "--post", str(B.parent), "--station", str(tmp), *fill, *them]


def _json_cuoi(out: str) -> dict:
    return json.loads([d for d in out.splitlines() if d.startswith("{")][-1])


# ── pha một ─────────────────────────────────────────────────────────────────

def test_hen_gio_thi_KHONG_comment_va_ghi_trang_thai(post, capsys):
    tmp, B, goi = post
    ts = int(time.time()) + 3 * 86400
    assert FB.main(_argv(tmp, B, "--publish-at", str(ts))) == 0
    assert goi["anh"] == [ts], "không truyền mốc hẹn cho Graph"
    assert goi["comment"] == [], "comment vào bài chưa phát — Graph sẽ từ chối"
    st = json.loads((B / FB.TRANG_THAI).read_text(encoding="utf-8"))
    assert st["scheduled"] and st["publish_ts"] == ts and st["comment_id"] == ""
    assert "https://x.vn/bai" in st["comment"], "chữ comment phải chốt từ lúc hẹn"
    assert "Xem video" not in st["comment"], "dòng YouTube rỗng phải bị bỏ"
    ra = _json_cuoi(capsys.readouterr().out)
    assert ra["url"] and ra["scheduled"] is True, "step_release cần dòng JSON có url"


def test_dang_ngay_thi_comment_luon_va_in_url(post, capsys):
    tmp, B, goi = post
    assert FB.main(_argv(tmp, B)) == 0
    assert goi["anh"] == [None] and len(goi["comment"]) == 1
    ra = _json_cuoi(capsys.readouterr().out)
    assert ra["url"].endswith("PAGE_POST1") and ra["comment_id"] == "CMT1"


def test_moc_hen_SAT_hon_11_phut_thi_dang_ngay(post):
    """Graph từ chối lịch dưới 10 phút. Mốc sát như vậy vốn đã là 'bây giờ'."""
    tmp, B, goi = post
    assert FB.main(_argv(tmp, B, "--publish-at", str(int(time.time()) + 120))) == 0
    assert goi["anh"] == [None] and len(goi["comment"]) == 1


def test_chay_lai_KHONG_dang_trung(post, capsys):
    """Tiến trình chết sau khi Facebook nhận bài mà trước khi ghi bảng: lượt sau không đăng lại."""
    tmp, B, goi = post
    ts = int(time.time()) + 86400
    FB.main(_argv(tmp, B, "--publish-at", str(ts)))
    capsys.readouterr()
    assert FB.main(_argv(tmp, B, "--publish-at", str(ts))) == 0
    assert goi["anh"] == [ts], f"đã đăng lần hai: {goi['anh']}"
    assert _json_cuoi(capsys.readouterr().out)["url"], "lượt chạy lại phải in lại link"


def test_comment_HONG_luc_dang_ngay_thi_van_con_trang_thai_de_gan_sau(post, monkeypatch):
    tmp, B, goi = post

    def hong(cfg, pid, msg):
        raise SystemExit("thiếu pages_manage_engagement")
    monkeypatch.setattr(FB, "dang_comment", hong)
    with pytest.raises(SystemExit):
        FB.main(_argv(tmp, B))
    st = json.loads((B / FB.TRANG_THAI).read_text(encoding="utf-8"))
    assert st["post_id"] == "PAGE_POST1" and st["comment_id"] == "", \
        "bài đã lên mà không để lại dấu — lượt sau sẽ đăng trùng"


def test_hen_gio_ma_Graph_KHONG_tra_post_id_thi_noi_to(post, monkeypatch):
    tmp, B, goi = post
    monkeypatch.setattr(FB, "dang_anh", lambda *a, **k: ("PHOTO1", ""))
    with pytest.raises(SystemExit) as e:
        FB.main(_argv(tmp, B, "--publish-at", str(int(time.time()) + 86400)))
    assert "PHOTO1" in str(e.value)


# ── chỗ trống trong comment ─────────────────────────────────────────────────

def test_cho_trong_KHONG_co_gia_tri_thi_bo_dong_va_bao():
    ra, bo = FB.dien_cho_trong("Blog: {{BLOG_URL}}\nVideo: {{YOUTUBE_URL}}\nHết.\n",
                               {"BLOG_URL": "https://x.vn/a", "YOUTUBE_URL": ""})
    assert ra == "Blog: https://x.vn/a\nHết.\n"
    assert bo == ["Video: {{YOUTUBE_URL}}"]


def test_quen_fill_link_blog_thi_cong_van_chan(post):
    """Không truyền --fill cho BLOG_URL thì chỗ trống còn nguyên, và cổng cũ phải chặn."""
    tmp, B, goi = post
    with pytest.raises(SystemExit) as e:
        FB.main(_argv(tmp, B, blog=None))
    # Hai cổng cũ đều bắt được: comment không còn URL nào, hoặc còn chỗ trống chưa điền.
    assert "placeholder" in str(e.value) or "không có URL" in str(e.value), \
        f"đỏ sai lý do: {e.value}"
    assert goi["anh"] == []


# ── pha hai ─────────────────────────────────────────────────────────────────

def _trang_thai(B, **d):
    base = {"post_id": "P1", "photo_id": "F1", "scheduled": True, "publish_ts": 1000,
            "publish_at": "", "comment": "Đọc: https://x.vn/a", "comment_id": "", "permalink": ""}
    base.update(d)
    (B / FB.TRANG_THAI).write_text(json.dumps(base), encoding="utf-8")


def test_pha_hai_CHUA_toi_gio_thi_cho(post):
    tmp, B, _ = post
    _trang_thai(B)
    gui = []
    kq = FB.attach_pending({}, tmp, now=500, doc_song=lambda p: (True, ""),
                           gui_comment=lambda p, m: gui.append(p))
    assert kq[0]["status"] == "waiting" and gui == []


def test_pha_hai_toi_gio_va_DA_phat_thi_gan_comment_da_chot(post):
    tmp, B, _ = post
    _trang_thai(B)
    gui = []
    kq = FB.attach_pending({}, tmp, now=2000, doc_song=lambda p: (True, "https://fb.com/P1"),
                           gui_comment=lambda p, m: gui.append((p, m)) or "C9")
    assert kq[0]["status"] == "attached", kq
    assert gui == [("P1", "Đọc: https://x.vn/a")]
    st = json.loads((B / FB.TRANG_THAI).read_text(encoding="utf-8"))
    assert st["comment_id"] == "C9" and st["permalink"] == "https://fb.com/P1"


def test_pha_hai_chay_lai_KHONG_comment_hai_lan(post):
    tmp, B, _ = post
    _trang_thai(B, comment_id="C9")
    gui = []
    kq = FB.attach_pending({}, tmp, now=2000, doc_song=lambda p: (True, ""),
                           gui_comment=lambda p, m: gui.append(p))
    assert kq[0]["status"] == "done" and gui == []


def test_pha_hai_qua_gio_lau_ma_Facebook_chua_phat_thi_BAO_DONG(post):
    """Đồng hồ máy mình nói đã tới giờ không có nghĩa là bài đã lên. Hỏi Facebook."""
    tmp, B, _ = post
    _trang_thai(B)
    kq = FB.attach_pending({}, tmp, now=1000 + FB.QUA_HAN + 60,
                           doc_song=lambda p: (False, ""), gui_comment=lambda p, m: "X")
    assert kq[0]["status"] == "overdue", kq


def test_pha_hai_mot_bai_hong_KHONG_chan_bai_sau(post):
    tmp, B, _ = post
    _trang_thai(B, post_id="HONG")
    B2 = tmp / "kenh" / "CMP-2609-x" / "AST-002_b" / "facebook"
    B2.mkdir(parents=True)
    _trang_thai(B2, post_id="TOT")

    def gui(p, m):
        if p == "HONG":
            raise SystemExit("token hết hạn")
        return "C1"
    kq = {k["post_id"]: k["status"] for k in
          FB.attach_pending({}, tmp, now=2000, doc_song=lambda p: (True, ""), gui_comment=gui)}
    assert kq == {"HONG": "failed", "TOT": "attached"}, kq


# ── soát chữ trên ảnh ───────────────────────────────────────────────────────

def test_anh_CHUA_soat_chu_thi_KHONG_dang(post, capsys):
    tmp, B, goi = post
    (B / "anh.meta.json").unlink()
    assert FB.main(_argv(tmp, B)) == 4
    assert goi["anh"] == [], "đã đăng ảnh chưa ai soát chữ"
    assert "soát chữ" in capsys.readouterr().err


def test_anh_bi_sua_SAU_khi_soat_thi_KHONG_dang(post):
    tmp, B, goi = post
    (B / "anh.png").write_bytes((B / "anh.png").read_bytes() + b"sua")
    assert FB.main(_argv(tmp, B)) == 4
    assert goi["anh"] == []
