# -*- coding: utf-8 -*-
"""`scripts/pipeline/campaign_step.py` — một BƯỚC của chiến dịch, không phải cả chuỗi.

Ba bước rời: `create-post` → [Cổng 1] → `soan` → [Cổng 2] → `dang`.

Vì sao rời chứ không gộp: script điều phối gộp đã bị gỡ 04/09 vì nó *"nuốt cổng duyệt của
người vào giữa chuỗi"*. Gộp lại dưới một cái tên khác là dựng lại đúng cái đã bỏ.

Mỗi test dưới đây chặn một cách hỏng cụ thể:

· **Lấy quá tay** — dựng sẵn 90 bài ngay ngày đầu thì cổng duyệt vô nghĩa và tiền nghiên
  cứu đốt hết một lượt.
· **Slug vỡ** — tiêu đề tiếng Việt có dấu và dấu câu; `new_post.py` chỉ nhận `a-z0-9-`.
  `Đ/đ` là ngoại lệ cứng: NFD KHÔNG tách được nó, phải thay tay.
· **Tự nâng quyền** — `autonomy` quyết có dừng ở cổng hay không. Sai chiều là 90 bài tự
  đăng, hoặc ngược lại là không bài nào chạy mà không rõ vì sao.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import md_io  # noqa: E402
import campaign_step as CS  # noqa: E402

HOM_NAY = date(2026, 9, 15)


def _fm(rows):
    start = ("---\nschema: campaign/1\nid: CD-THU\nchannel: kenh-thu\nid_prefix: T\n"
           "name: Thử\nstatus: active\ncontent_pillar: ai-agent\n"
           "runtime:\n  label: Thử\n  runner: run-blog-campaign.ps1\n  lookahead_days: 3\n"
           "---\n\n# Thử\n\n<!-- CONTENT:BEGIN -->\n"
           "| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 "
           "| schedule | published | folder | web | youtube | facebook |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    return start + "".join(rows) + "<!-- CONTENT:END -->\n"


def _row(cid, name, lich, g1="", g2="", folder="", published=""):
    return (f"| {cid} | {name} | ai-agent | explainer | awareness | high | proposed "
            f"| {g1} | {g2} | {lich} | {published} | {folder} |  |  |  |\n")


def _cam(tmp_path, rows, autonomy="suggest"):
    channel = tmp_path / "tram" / "kenh-thu"
    campaign = channel / "CD-THU"
    (campaign / "logs").mkdir(parents=True)
    (channel / "channel.yml").write_text(
        f"schema: channel/1\nid: kenh-thu\nlabel: \"K\"\nautonomy: {autonomy}\n"
        "pillars: [ai-agent]\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8")
    (campaign / "campaign.md").write_text(_fm(rows), encoding="utf-8")
    return campaign


class BotGia:
    def __init__(self):
        self.sent = []

    def duoc_phep(self, c):
        return True

    def gui(self, text, chat=None, **kw):
        self.sent.append(text)
        return 1

    def gui_kem_nut(self, text, nut, chat=None, **kw):
        self.sent.append(text)
        return 1

    def lay_cap_nhat(self, offset=None, timeout=0):
        return []


def _bang(campaign):
    _, than = md_io.read_fm(campaign / "campaign.md")
    _, row = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in row}


# ── Slug ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tieu_de,mong_doi", [
    ("Người thợ khoá và bản vẽ sai: prompt không phải câu thần chú",
     "nguoi-tho-khoa-va-ban-ve-sai-prompt-khong-phai-cau-than-chu"),
    ("Đường lùi im lặng: vì sao silent fallback nguy hiểm hơn báo lỗi",
     "duong-lui-im-lang-vi-sao-silent-fallback-nguy-hiem-hon-bao-loi"),
    ("[Chốt chặng 1] Prompt giỏi không cứu nổi agent tồi",
     "chot-chang-1-prompt-gioi-khong-cuu-noi-agent-toi"),
    ("Đi chợ có cầm tiền: đặt trần chi phí — token budget",
     "di-cho-co-cam-tien-dat-tran-chi-phi-token-budget"),
])
def test_slug_hop_le_va_giu_nghia(tieu_de, mong_doi):
    """`new_post.py` chỉ nhận a-z0-9-. `Đ/đ` là ngoại lệ cứng: NFD không tách được nó."""
    assert CS.slugify(tieu_de) == mong_doi


def test_slug_khong_bao_gio_rong_hay_co_gach_thua():
    for t in ("...", "  ", "— — —", "A"):
        s = CS.slugify(t)
        assert s, f"slug rỗng cho {t!r}"
        assert not s.startswith("-") and not s.endswith("-"), s
        assert "--" not in s, s


# ── create-post: chọn đúng bài tới hạn ─────────────────────────────────────────

def test_chi_lay_bai_TRONG_CUA_SO_lich(tmp_path):
    campaign = _cam(tmp_path, [
        _row("T-001", "Bài một", "2026-09-15"),
        _row("T-002", "Bài hai", "2026-09-17"),
        _row("T-003", "Bài xa", "2026-10-30"),
    ])
    ds = CS.posts_due(campaign, lookahead=3, hom_nay=HOM_NAY)
    assert [d["content_id"] for d in ds] == ["T-001", "T-002"], \
        "lấy quá tay thì cổng duyệt vô nghĩa và đốt tiền nghiên cứu một lượt"


def test_bai_DA_CO_thu_muc_thi_khong_lam_lai(tmp_path):
    campaign = _cam(tmp_path, [
        _row("T-001", "Bài một", "2026-09-15", folder="./T-001_bai-mot"),
        _row("T-002", "Bài hai", "2026-09-15"),
    ])
    ds = CS.posts_due(campaign, lookahead=3, hom_nay=HOM_NAY)
    assert [d["content_id"] for d in ds] == ["T-002"]


def test_bai_thieu_lich_thi_bo_qua_khong_no(tmp_path):
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", ""),
                          _row("T-002", "Bài hai", "2026-09-15")])
    ds = CS.posts_due(campaign, lookahead=3, hom_nay=HOM_NAY)
    assert [d["content_id"] for d in ds] == ["T-002"]


# ── Cổng tự trị ─────────────────────────────────────────────────────────────

def test_suggest_thi_GUI_cong_va_KHONG_self_approved(tmp_path):
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               folder="./T-001_bai-mot")], autonomy="suggest")
    b = BotGia()
    CS.open_gate(campaign, "g1", ["T-001"], bot=b, hom_nay=HOM_NAY)
    assert b.sent, "suggest mà không gửi tin xin duyệt"
    assert _bang(campaign)["T-001"]["g1"] == "", "suggest mà agent TỰ duyệt — cổng thủng"


def test_full_thi_TU_DUYET_va_khong_gui_tin(tmp_path):
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               folder="./T-001_bai-mot")], autonomy="full")
    b = BotGia()
    CS.open_gate(campaign, "g1", ["T-001"], bot=b, hom_nay=HOM_NAY)
    assert _bang(campaign)["T-001"]["g1"] == HOM_NAY.isoformat()
    assert not b.sent, "full mà vẫn xin duyệt — làm phiền vô ích"


def test_autonomy_LA_thi_coi_nhu_SUGGEST(tmp_path):
    """Giá trị lạ phải rơi về mức CHẶT nhất, không phải mức rộng nhất."""
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               folder="./T-001_bai-mot")], autonomy="khong-biet-la-gi")
    CS.open_gate(campaign, "g1", ["T-001"], bot=BotGia(), hom_nay=HOM_NAY)
    assert _bang(campaign)["T-001"]["g1"] == "", "giá trị lạ mà mở cổng — fail-open"


# ── dang: không qua cổng thì không đăng ─────────────────────────────────────

def test_chua_qua_g2_thi_KHONG_dang(tmp_path):
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               g1="2026-09-14", folder="./T-001_bai-mot")])
    ds = CS.posts_ready_to_publish(campaign)
    assert ds == [], "bài chưa qua Cổng 2 mà đã vào danh sách đăng"


def test_da_dang_roi_thi_khong_dang_lai(tmp_path):
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15", g1="2026-09-14",
                               g2="2026-09-15", folder="./T-001_bai-mot",
                               published="2026-09-15")])
    assert CS.posts_ready_to_publish(campaign) == []


# ── Mã thoát: bước hỏng thì PHẢI khác 0 ─────────────────────────────────────
#
# ĐÃ TRẢ GIÁ 10/09/2026 trong chính đợt UAT này: `main()` trả 0 vô điều kiện, nên một lượt
# `create-post` thất bại hoàn toàn vẫn cho `exit=0`. Chạy theo lịch thì `notify-run.ps1` đọc
# mã thoát đó và báo ✅ cho một lượt KHÔNG LÀM ĐƯỢC GÌ. Đây là cổng canh chỗ đó.

def test_buoc_hong_thi_ma_thoat_KHAC_0():
    assert CS.exit_code({"step": "create-post", "loi": "new_post that bai", "exit": 2}) != 0
    assert CS.exit_code({"step": "write", "failed": [{"id": "T-001", "why": "gen_article"}]}) != 0
    assert CS.exit_code({"step": "publish", "detail": [{"id": "T-001", "exit": 4}]}) != 0


def test_KHONG_CO_VIEC_thi_van_la_0():
    """Không có bài nào tới hạn ≠ thất bại. Báo đỏ mỗi ngày rồi thì không ai đọc báo nữa."""
    assert CS.exit_code({"step": "create-post", "tao": 0, "reason": "không có bài nào tới hạn"}) == 0
    assert CS.exit_code({"step": "write", "xu_ly": 0, "failed": [], "cho_nguoi_viet": []}) == 0
    assert CS.exit_code({"step": "publish", "publish": 1,
                        "detail": [{"id": "T-001", "exit": 0}]}) == 0


def test_cho_nguoi_viet_KHONG_phai_loi():
    """Bài chưa ai viết là trạng thái BÌNH THƯỜNG của quy trình có cổng người."""
    assert CS.exit_code({"step": "write", "xu_ly": 0,
                        "cho_nguoi_viet": ["T-001", "T-002"], "failed": []}) == 0


# ── `_da_viet` phải FAIL-CLOSED ─────────────────────────────────────────────
#
# ĐÃ TRẢ GIÁ 10/09/2026: bản đầu đếm ký tự (ngưỡng 400) và coi KHUÔN MẪU là "đã viết" —
# khuôn tự nó dài 3.701 ký tự sau khi lọc, gấp 9 lần ngưỡng. Cổng lẽ ra chặn "chưa ai viết"
# lại mở toang, và bước `soan` báo 3 bài SẴN SÀNG ĐĂNG trong khi chưa có một chữ nào.
#
# Đếm ký tự là phép đo SAI ĐẠI LƯỢNG. Dấu hiệu đúng: khuôn đầy `{{...}}`; bài viết xong thì
# không còn chỗ trống nào.

KHUON = (ROOT / "templates" / "station" / "_channel" / "_campaign" / "_content" / "content.md")


def test_KHUON_MAU_khong_duoc_tinh_la_da_viet(tmp_path):
    """Cổng quan trọng nhất của bước `soan`. Sai chiều là đăng bài rỗng."""
    post = tmp_path / "post"
    post.mkdir()
    (post / "content.md").write_text(KHUON.read_text(encoding="utf-8"), encoding="utf-8")
    assert CS._da_viet(post) is False, "khuôn mẫu bị tính là đã viết — cổng fail-open"


def test_con_cho_trong_thi_CHUA_XONG(tmp_path):
    post = tmp_path / "post"
    post.mkdir()
    (post / "content.md").write_text(
        "## post:blog_article\n\n" + "Câu văn thật. " * 60 + "\n\n{{còn chỗ này}}\n",
        encoding="utf-8")
    assert CS._da_viet(post) is False, "còn `{{}}` mà đã tính là viết xong"


def test_bai_VIET_THAT_thi_tinh_la_xong(tmp_path):
    post = tmp_path / "post"
    post.mkdir()
    (post / "content.md").write_text(
        "---\nschema: content/1\n---\n\n## post:blog_article\n\n"
        + "Người thợ khoá cầm bản vẽ sai thì làm ra cái chìa không mở được cửa nào. " * 12,
        encoding="utf-8")
    assert CS._da_viet(post) is True


def test_thieu_neo_blog_article_thi_CHUA_XONG(tmp_path):
    post = tmp_path / "post"
    post.mkdir()
    (post / "content.md").write_text("Chữ nghĩa đầy đủ nhưng không có neo. " * 40,
                                    encoding="utf-8")
    assert CS._da_viet(post) is False


def test_khong_co_content_md_thi_CHUA_XONG(tmp_path):
    post = tmp_path / "post"
    post.mkdir()
    assert CS._da_viet(post) is False


# ── `--dry-run` KHÔNG được có tác dụng phụ ──────────────────────────────────

def test_dry_run_KHONG_duoc_gui_telegram(tmp_path):
    """ĐÃ TRẢ GIÁ: `soan --dry-run` vừa gửi tin THẬT xin duyệt đăng 3 bài rỗng.

    Một lệnh có chữ "dry-run" mà gây tác dụng ra ngoài thì người ta sẽ không bao giờ dám
    dùng nó để thử — tức là mất luôn công cụ an toàn duy nhất."""
    campaign = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               g1="2026-09-14", folder="./T-001_bai")])
    (campaign / "T-001_bai").mkdir()
    (campaign / "T-001_bai" / "content.md").write_text(
        "## post:blog_article\n\n" + "Chữ thật đủ dài để qua ngưỡng. " * 60,
        encoding="utf-8")
    b = BotGia()
    # Khẳng định bài THẬT SỰ được coi là đã viết. Không có dòng này thì `xong` rỗng và test
    # không bao giờ chạm tới chỗ cần kiểm — bản đầu dài 799 ký tự, hụt ngưỡng 800 đúng MỘT
    # ký tự, nên nó xanh cả khi dry-run vẫn gửi tin. Đột biến không giết được nó.
    assert CS._da_viet(campaign / "T-001_bai"), "fixture chưa đủ dài — test sẽ vô nghĩa"
    CS.step_write(campaign, bot=b, hom_nay=HOM_NAY, dry_run=True)
    assert b.sent == [], f"dry-run mà vẫn gửi Telegram: {b.sent}"


# ── writer_cmd · chỗ nối agent viết bài ─────────────────────────────────────
#
# Repo là PUBLIC nên KHÔNG được phụ thuộc cứng vào `claude` CLI hay bất kỳ agent nào.
# `runtime.writer_cmd` để người dùng tự khai lệnh của họ. Không khai thì bước `soan` báo
# "chờ người viết" — fail-closed, không đoán.

def _cam_writer(tmp_path, writer_cmd=None, rows=None, autonomy="suggest",
                writer_skills=None):
    campaign = _cam(tmp_path, rows or [_row("T-001", "Bài một", "2026-09-15",
                                       g1="2026-09-14", folder="./T-001_bai")],
               autonomy=autonomy)
    if writer_cmd or writer_skills:
        fm, than = md_io.read_fm(campaign / "campaign.md")
        rt = fm.setdefault("runtime", {})
        if writer_cmd:
            rt["writer_cmd"] = writer_cmd
        if writer_skills:
            rt["writer_skills"] = writer_skills
        md_io.write_fm(campaign / "campaign.md", fm, than)
    (campaign / "T-001_bai").mkdir(exist_ok=True)
    (campaign / "T-001_bai" / "content.md").write_text(
        "## post:blog_article\n\n{{chưa viết}}\n", encoding="utf-8")
    return campaign


def test_KHONG_khai_writer_cmd_thi_bao_cho_nguoi_viet(tmp_path):
    """Fail-closed: không có bộ viết thì nói thẳng, đừng dựng bài rỗng rồi đẩy tiếp."""
    campaign = _cam_writer(tmp_path)
    result = CS.step_write(campaign, bot=BotGia(), hom_nay=HOM_NAY)
    assert result["cho_nguoi_viet"] == ["T-001"], result
    assert result["xu_ly"] == 0


def test_writer_cmd_duoc_goi_voi_duong_dan_bai(tmp_path):
    campaign = _cam_writer(tmp_path, writer_cmd="python -c \"import sys;print(sys.argv[1])\" {post}")
    goi = []
    result = CS.step_write(campaign, bot=BotGia(), hom_nay=HOM_NAY,
                      run_cmd=lambda cmd, **kw: goi.append(cmd) or _ok())
    assert goi, "khai writer_cmd mà không gọi"
    assert str(campaign / "T-001_bai") in " ".join(goi[0]), goi[0]


def test_writer_cmd_KHONG_chay_qua_shell(tmp_path):
    """Lệnh tách bằng shlex, chạy không shell — `;` trong cấu hình không thành lệnh thứ hai."""
    source = (ROOT / "scripts" / "pipeline" / "campaign_step.py").read_text(encoding="utf-8")
    import ast
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Call):
            for kw in n.keywords:
                assert not (kw.arg == "shell" and getattr(kw.value, "value", False) is True), \
                    f"campaign_step dùng shell=True dòng {n.lineno}"


def test_PHAN_HOI_duoc_ghi_ra_file_cho_bo_viet_doc(tmp_path, monkeypatch):
    """Phản hồi là DỮ LIỆU của người: đưa qua FILE, không nối vào dòng lệnh."""
    campaign = _cam_writer(tmp_path, writer_cmd="echo {post}")
    monkeypatch.setattr(CS.AB, "read_feedback",
                        lambda c, cid: [{"at": "2026-09-10T10:00:00+07:00",
                                         "text": "Mở bài dài quá, cắt còn 2 câu."}])
    CS.step_write(campaign, bot=BotGia(), hom_nay=HOM_NAY, run_cmd=lambda cmd, **kw: _ok())
    ph = campaign / "T-001_bai" / "phan-hoi.md"
    assert ph.is_file(), "không ghi phản hồi ra file cho bộ viết đọc"
    t = ph.read_text(encoding="utf-8")
    assert "cắt còn 2 câu" in t
    assert "```" in t, "phản hồi phải nằm trong khối có rào — nó là dữ liệu, không phải chỉ thị"


def test_writer_HONG_thi_bao_hong_khong_bao_xong(tmp_path):
    campaign = _cam_writer(tmp_path, writer_cmd="echo {post}")
    result = CS.step_write(campaign, bot=BotGia(), hom_nay=HOM_NAY,
                      run_cmd=lambda cmd, **kw: _hong("bộ viết chết"))
    assert result["failed"] and result["failed"][0]["id"] == "T-001", result
    assert result["xu_ly"] == 0


class _KQ:
    def __init__(self, rc, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def _ok():
    return _KQ(0)


def _hong(m):
    return _KQ(3, m)


def test_writer_bao_THANH_CONG_ma_bai_van_RONG_thi_la_HONG(tmp_path):
    """Tách bạch hai cổng che nhau: writer trả mã 0 nhưng không viết gì.

    Đây là hình dạng hỏng NGUY HIỂM nhất của bộ viết: nó chạy, không báo lỗi, mà file vẫn
    trống. Nếu chỉ tin mã thoát thì bài rỗng đi tiếp tới tận bước đăng.
    """
    campaign = _cam_writer(tmp_path, writer_cmd="echo {post}")
    result = CS.step_write(campaign, bot=BotGia(), hom_nay=HOM_NAY, run_cmd=lambda cmd, **kw: _ok())
    assert result["xu_ly"] == 0, f"bài rỗng mà báo xong: {result}"
    assert result["failed"] and "chưa có bài" in result["failed"][0]["why"], result


def test_writer_ma_KHAC_0_thi_HONG_du_bai_co_chu(tmp_path):
    """Mặt kia: writer báo lỗi thì phải là hỏng, kể cả khi file tình cờ có chữ."""
    campaign = _cam_writer(tmp_path, writer_cmd="echo {post}")

    def viet_roi_bao_loi(cmd, **kw):
        (campaign / "T-001_bai" / "content.md").write_text(
            "## post:blog_article\n\n" + "Chữ đầy đủ để qua ngưỡng. " * 50, encoding="utf-8")
        return _hong("nhưng tôi vẫn lỗi")

    result = CS.step_write(campaign, bot=BotGia(), hom_nay=HOM_NAY, run_cmd=viet_roi_bao_loi)
    assert result["xu_ly"] == 0, f"writer báo lỗi mà vẫn tính là xong: {result}"
    assert result["failed"] and result["failed"][0]["why"] == "writer_cmd", result


def test_tach_lenh_KHONG_nuot_dau_gach_cheo_windows():
    r"""`shlex.split` mặc định POSIX coi `\` là ký tự thoát ⇒ đường dẫn Windows bị ăn sạch:
    `D:\tram\kenh\x.ps1` -> `D:tramkenhx.ps1`. Lệnh không bao giờ chạy, và lỗi báo ra là
    "không tìm thấy file" — chẳng trỏ vào đâu."""
    cmd = CS.split_command(r'powershell -File D:\tram\kenh\viet-bai.ps1 -Bai {post}')
    assert r"D:\tram\kenh\viet-bai.ps1" in cmd, cmd
    assert cmd[-1] == "{post}"


def test_tach_lenh_giu_duong_dan_co_khoang_trang():
    cmd = CS.split_command(r'python "D:\Chuong Trinh\x\y.py" {post}')
    assert cmd[1] == r"D:\Chuong Trinh\x\y.py", cmd


# ── Skill nạp cho bộ viết: KHAI Ở TRẠM, hiện ra được ────────────────────────

def test_writer_skills_duoc_thay_vao_cho_dien(tmp_path):
    """`{skills}` phải được thay bằng danh sách khai ở `campaign.md`.

    Khai skill ở campaign.md thay vì chôn trong script của trạm là để NGƯỜI DUYỆT nhìn ra
    bài này viết dưới ảnh hưởng của skill nào. Chỗ điền không hoạt động thì cả cơ chế đó
    chỉ là một dòng tài liệu không ai thi hành.
    """
    ra = tmp_path / "goi.txt"
    campaign = _cam_writer(
        tmp_path,
        writer_cmd=f'python -c "import sys,pathlib;pathlib.Path(sys.argv[1]).write_text('
                   f'sys.argv[2],encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56))" '
                   f'"{ra}" "{{skills}}"',
        writer_skills=["kpim-skills:blog-writing", "x:y"])
    CS.step_write(campaign, bot=BotGia())
    assert ra.read_text(encoding="utf-8") == "kpim-skills:blog-writing,x:y"


def test_khong_khai_skills_thi_cho_dien_thanh_RONG(tmp_path):
    """Không khai thì chỗ điền thành rỗng, bộ viết chạy như cũ — cùng luật với mọi hook."""
    ra = tmp_path / "goi2.txt"
    campaign = _cam_writer(
        tmp_path,
        writer_cmd=f'python -c "import sys,pathlib;pathlib.Path(sys.argv[1]).write_text('
                   f'chr(91)+sys.argv[2]+chr(93),encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56))" '
                   f'"{ra}" "{{skills}}"')
    CS.step_write(campaign, bot=BotGia())
    assert ra.read_text(encoding="utf-8") == "[]"


# ── Cổng đỏ phải kích hoạt viết lại (đổi 12/09/2026) ────────────────────────

def _gates_do(post, *, chan=("G05",), verdict="fail"):
    import json as _j
    (post / "gates.json").write_text(_j.dumps({
        "stage": "write", "verdict": verdict,
        "gates": [{"id": m, "name": f"Cổng {m}", "measured": 0, "rule": ">=3",
                   "status": "fail", "level": "block", "note": ""} for m in chan]},
        ensure_ascii=False), encoding="utf-8", newline="\n")


def _bai_da_viet(post):
    post.mkdir(exist_ok=True)
    (post / "content.md").write_text(
        "## post:blog_article\n\n# T\n\n" + ("Một đoạn nội dung thật. " * 300),
        encoding="utf-8", newline="\n")


def test_CONG_DO_kich_hoat_viet_lai(tmp_path):
    """Đo thật 11–12/09: bản đầu chỉ viết lại khi có nhận xét MỚI của người.

    Bước `fix-gates` gọi bộ viết, bộ viết thấy "bài đã viết, không có nhận xét mới" rồi
    trả về thành công mà không sửa gì. Ba bài kẹt đúng chỗ đó hai ngày, và đường ống
    không có cách nào tự chữa một bài cổng chấm đỏ.
    """
    ra = tmp_path / "goi.txt"
    campaign = _cam_writer(
        tmp_path,
        writer_cmd=f'python -c "import pathlib;pathlib.Path(r\'{ra}\').write_text(chr(120))"')
    post = campaign / "T-001_bai"
    _bai_da_viet(post)
    _gates_do(post)

    CS.step_write(campaign, bot=BotGia())
    assert ra.exists(), "cổng đỏ mà bộ viết không được gọi — bài kẹt vĩnh viễn"


def test_cong_do_ghi_ra_FILE_cho_bo_viet_doc(tmp_path):
    """Bộ viết phải biết SỬA GÌ. Bảo nó viết lại mà không nói đỏ ở đâu là bảo nó đoán."""
    campaign = _cam_writer(tmp_path, writer_cmd='python -c "pass"')
    post = campaign / "T-001_bai"
    _bai_da_viet(post)
    _gates_do(post, chan=("G05", "G06"))

    CS.step_write(campaign, bot=BotGia())
    t = (post / "cong-do.md").read_text(encoding="utf-8")
    assert "G05" in t and "G06" in t and "luật" in t


def test_cham_TRAN_thi_DUNG_viet_lai_va_noi_ro(tmp_path):
    """Vòng viết lại phải có trần. Mỗi vòng đốt một lượt agent thật."""
    campaign = _cam_writer(tmp_path, writer_cmd='python -c "pass"')
    post = campaign / "T-001_bai"
    _bai_da_viet(post)
    for i in range(CS.MAX_REWRITES):
        _gates_do(post, chan=(f"G0{i+1}",))       # mỗi vòng một chữ ký khác
        can, vi_sao = CS._needs_rewrite(post, 0, CS._dump_gate_report(post))
        assert can, f"vòng {i+1} phải được viết lại: {vi_sao}"
        CS._mark_written(post, 0, CS._dump_gate_report(post), vi_cong=True)

    _gates_do(post, chan=("G09",))
    can, vi_sao = CS._needs_rewrite(post, 0, CS._dump_gate_report(post))
    assert not can and "dung" in vi_sao, vi_sao


def test_cham_LAI_ra_KET_QUA_CU_thi_KHONG_viet_lai(tmp_path):
    """Chấm lại mà không đổi gì thì không phải cớ để đốt thêm một lượt agent."""
    campaign = _cam_writer(tmp_path, writer_cmd='python -c "pass"')
    post = campaign / "T-001_bai"
    _bai_da_viet(post)
    _gates_do(post)
    chu_ky = CS._dump_gate_report(post)
    CS._mark_written(post, 0, chu_ky, vi_cong=True)
    can, _ = CS._needs_rewrite(post, 0, CS._dump_gate_report(post))
    assert not can, "cùng một kết quả chấm mà vẫn viết lại — quay tít"
