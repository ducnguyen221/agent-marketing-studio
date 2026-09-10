# -*- coding: utf-8 -*-
"""`scripts/pipeline/campaign_step.py` — một BƯỚC của chiến dịch, không phải cả chuỗi.

Ba bước rời: `dung-bai` → [Cổng 1] → `soan` → [Cổng 2] → `dang`.

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
    dau = ("---\nschema: campaign/1\nid: CD-THU\nchannel: kenh-thu\nid_prefix: T\n"
           "name: Thử\nstatus: active\ncontent_pillar: ai-agent\n"
           "runtime:\n  label: Thử\n  runner: run-blog-campaign.ps1\n  lookahead_days: 3\n"
           "---\n\n# Thử\n\n<!-- CONTENT:BEGIN -->\n"
           "| content_id | content_name | pillar | angle | funnel | priority | status | g1 | g2 "
           "| schedule | published | folder | web | youtube | facebook |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    return dau + "".join(rows) + "<!-- CONTENT:END -->\n"


def _row(cid, ten, lich, g1="", g2="", folder="", published=""):
    return (f"| {cid} | {ten} | ai-agent | explainer | awareness | high | proposed "
            f"| {g1} | {g2} | {lich} | {published} | {folder} |  |  |  |\n")


def _cam(tmp_path, rows, autonomy="suggest"):
    kenh = tmp_path / "tram" / "kenh-thu"
    cam = kenh / "CD-THU"
    (cam / "logs").mkdir(parents=True)
    (kenh / "channel.yml").write_text(
        f"schema: channel/1\nid: kenh-thu\nlabel: \"K\"\nautonomy: {autonomy}\n"
        "pillars: [ai-agent]\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8")
    (cam / "campaign.md").write_text(_fm(rows), encoding="utf-8")
    return cam


class BotGia:
    def __init__(self):
        self.da_gui = []

    def duoc_phep(self, c):
        return True

    def gui(self, text, chat=None, **kw):
        self.da_gui.append(text)
        return 1

    def gui_kem_nut(self, text, nut, chat=None, **kw):
        self.da_gui.append(text)
        return 1

    def lay_cap_nhat(self, offset=None, timeout=0):
        return []


def _bang(cam):
    _, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in dong}


# ── Slug ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tieu_de, mong_doi", [
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
    assert CS.slug_hoa(tieu_de) == mong_doi


def test_slug_khong_bao_gio_rong_hay_co_gach_thua():
    for t in ("...", "  ", "— — —", "A"):
        s = CS.slug_hoa(t)
        assert s, f"slug rỗng cho {t!r}"
        assert not s.startswith("-") and not s.endswith("-"), s
        assert "--" not in s, s


# ── dung-bai: chọn đúng bài tới hạn ─────────────────────────────────────────

def test_chi_lay_bai_TRONG_CUA_SO_lich(tmp_path):
    cam = _cam(tmp_path, [
        _row("T-001", "Bài một", "2026-09-15"),
        _row("T-002", "Bài hai", "2026-09-17"),
        _row("T-003", "Bài xa", "2026-10-30"),
    ])
    ds = CS.bai_toi_han(cam, truoc=3, hom_nay=HOM_NAY)
    assert [d["content_id"] for d in ds] == ["T-001", "T-002"], \
        "lấy quá tay thì cổng duyệt vô nghĩa và đốt tiền nghiên cứu một lượt"


def test_bai_DA_CO_thu_muc_thi_khong_lam_lai(tmp_path):
    cam = _cam(tmp_path, [
        _row("T-001", "Bài một", "2026-09-15", folder="./T-001_bai-mot"),
        _row("T-002", "Bài hai", "2026-09-15"),
    ])
    ds = CS.bai_toi_han(cam, truoc=3, hom_nay=HOM_NAY)
    assert [d["content_id"] for d in ds] == ["T-002"]


def test_bai_thieu_lich_thi_bo_qua_khong_no(tmp_path):
    cam = _cam(tmp_path, [_row("T-001", "Bài một", ""),
                          _row("T-002", "Bài hai", "2026-09-15")])
    ds = CS.bai_toi_han(cam, truoc=3, hom_nay=HOM_NAY)
    assert [d["content_id"] for d in ds] == ["T-002"]


# ── Cổng tự trị ─────────────────────────────────────────────────────────────

def test_suggest_thi_GUI_cong_va_KHONG_tu_duyet(tmp_path):
    cam = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               folder="./T-001_bai-mot")], autonomy="suggest")
    b = BotGia()
    CS.mo_cong(cam, "g1", ["T-001"], bot=b, hom_nay=HOM_NAY)
    assert b.da_gui, "suggest mà không gửi tin xin duyệt"
    assert _bang(cam)["T-001"]["g1"] == "", "suggest mà agent TỰ duyệt — cổng thủng"


def test_full_thi_TU_DUYET_va_khong_gui_tin(tmp_path):
    cam = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               folder="./T-001_bai-mot")], autonomy="full")
    b = BotGia()
    CS.mo_cong(cam, "g1", ["T-001"], bot=b, hom_nay=HOM_NAY)
    assert _bang(cam)["T-001"]["g1"] == HOM_NAY.isoformat()
    assert not b.da_gui, "full mà vẫn xin duyệt — làm phiền vô ích"


def test_autonomy_LA_thi_coi_nhu_SUGGEST(tmp_path):
    """Giá trị lạ phải rơi về mức CHẶT nhất, không phải mức rộng nhất."""
    cam = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               folder="./T-001_bai-mot")], autonomy="khong-biet-la-gi")
    CS.mo_cong(cam, "g1", ["T-001"], bot=BotGia(), hom_nay=HOM_NAY)
    assert _bang(cam)["T-001"]["g1"] == "", "giá trị lạ mà mở cổng — fail-open"


# ── dang: không qua cổng thì không đăng ─────────────────────────────────────

def test_chua_qua_g2_thi_KHONG_dang(tmp_path):
    cam = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               g1="2026-09-14", folder="./T-001_bai-mot")])
    ds = CS.bai_san_sang_dang(cam)
    assert ds == [], "bài chưa qua Cổng 2 mà đã vào danh sách đăng"


def test_da_dang_roi_thi_khong_dang_lai(tmp_path):
    cam = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15", g1="2026-09-14",
                               g2="2026-09-15", folder="./T-001_bai-mot",
                               published="2026-09-15")])
    assert CS.bai_san_sang_dang(cam) == []


# ── Mã thoát: bước hỏng thì PHẢI khác 0 ─────────────────────────────────────
#
# ĐÃ TRẢ GIÁ 10/09/2026 trong chính đợt UAT này: `main()` trả 0 vô điều kiện, nên một lượt
# `dung-bai` thất bại hoàn toàn vẫn cho `exit=0`. Chạy theo lịch thì `notify-run.ps1` đọc
# mã thoát đó và báo ✅ cho một lượt KHÔNG LÀM ĐƯỢC GÌ. Đây là cổng canh chỗ đó.

def test_buoc_hong_thi_ma_thoat_KHAC_0():
    assert CS.ma_thoat({"buoc": "dung-bai", "loi": "new_post that bai", "exit": 2}) != 0
    assert CS.ma_thoat({"buoc": "soan", "hong": [{"id": "T-001", "vi_sao": "gen_article"}]}) != 0
    assert CS.ma_thoat({"buoc": "dang", "chi_tiet": [{"id": "T-001", "exit": 4}]}) != 0


def test_KHONG_CO_VIEC_thi_van_la_0():
    """Không có bài nào tới hạn ≠ thất bại. Báo đỏ mỗi ngày rồi thì không ai đọc báo nữa."""
    assert CS.ma_thoat({"buoc": "dung-bai", "tao": 0, "ly_do": "không có bài nào tới hạn"}) == 0
    assert CS.ma_thoat({"buoc": "soan", "xu_ly": 0, "hong": [], "cho_nguoi_viet": []}) == 0
    assert CS.ma_thoat({"buoc": "dang", "dang": 1,
                        "chi_tiet": [{"id": "T-001", "exit": 0}]}) == 0


def test_cho_nguoi_viet_KHONG_phai_loi():
    """Bài chưa ai viết là trạng thái BÌNH THƯỜNG của quy trình có cổng người."""
    assert CS.ma_thoat({"buoc": "soan", "xu_ly": 0,
                        "cho_nguoi_viet": ["T-001", "T-002"], "hong": []}) == 0


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
    bai = tmp_path / "bai"
    bai.mkdir()
    (bai / "content.md").write_text(KHUON.read_text(encoding="utf-8"), encoding="utf-8")
    assert CS._da_viet(bai) is False, "khuôn mẫu bị tính là đã viết — cổng fail-open"


def test_con_cho_trong_thi_CHUA_XONG(tmp_path):
    bai = tmp_path / "bai"
    bai.mkdir()
    (bai / "content.md").write_text(
        "## post:blog_article\n\n" + "Câu văn thật. " * 60 + "\n\n{{còn chỗ này}}\n",
        encoding="utf-8")
    assert CS._da_viet(bai) is False, "còn `{{}}` mà đã tính là viết xong"


def test_bai_VIET_THAT_thi_tinh_la_xong(tmp_path):
    bai = tmp_path / "bai"
    bai.mkdir()
    (bai / "content.md").write_text(
        "---\nschema: content/1\n---\n\n## post:blog_article\n\n"
        + "Người thợ khoá cầm bản vẽ sai thì làm ra cái chìa không mở được cửa nào. " * 12,
        encoding="utf-8")
    assert CS._da_viet(bai) is True


def test_thieu_neo_blog_article_thi_CHUA_XONG(tmp_path):
    bai = tmp_path / "bai"
    bai.mkdir()
    (bai / "content.md").write_text("Chữ nghĩa đầy đủ nhưng không có neo. " * 40,
                                    encoding="utf-8")
    assert CS._da_viet(bai) is False


def test_khong_co_content_md_thi_CHUA_XONG(tmp_path):
    bai = tmp_path / "bai"
    bai.mkdir()
    assert CS._da_viet(bai) is False


# ── `--dry-run` KHÔNG được có tác dụng phụ ──────────────────────────────────

def test_dry_run_KHONG_duoc_gui_telegram(tmp_path):
    """ĐÃ TRẢ GIÁ: `soan --dry-run` vừa gửi tin THẬT xin duyệt đăng 3 bài rỗng.

    Một lệnh có chữ "dry-run" mà gây tác dụng ra ngoài thì người ta sẽ không bao giờ dám
    dùng nó để thử — tức là mất luôn công cụ an toàn duy nhất."""
    cam = _cam(tmp_path, [_row("T-001", "Bài một", "2026-09-15",
                               g1="2026-09-14", folder="./T-001_bai")])
    (cam / "T-001_bai").mkdir()
    (cam / "T-001_bai" / "content.md").write_text(
        "## post:blog_article\n\n" + "Chữ thật đủ dài để qua ngưỡng. " * 60,
        encoding="utf-8")
    b = BotGia()
    # Khẳng định bài THẬT SỰ được coi là đã viết. Không có dòng này thì `xong` rỗng và test
    # không bao giờ chạm tới chỗ cần kiểm — bản đầu dài 799 ký tự, hụt ngưỡng 800 đúng MỘT
    # ký tự, nên nó xanh cả khi dry-run vẫn gửi tin. Đột biến không giết được nó.
    assert CS._da_viet(cam / "T-001_bai"), "fixture chưa đủ dài — test sẽ vô nghĩa"
    CS.buoc_soan(cam, bot=b, hom_nay=HOM_NAY, dry_run=True)
    assert b.da_gui == [], f"dry-run mà vẫn gửi Telegram: {b.da_gui}"


# ── writer_cmd · chỗ nối agent viết bài ─────────────────────────────────────
#
# Repo là PUBLIC nên KHÔNG được phụ thuộc cứng vào `claude` CLI hay bất kỳ agent nào.
# `runtime.writer_cmd` để người dùng tự khai lệnh của họ. Không khai thì bước `soan` báo
# "chờ người viết" — fail-closed, không đoán.

def _cam_writer(tmp_path, writer_cmd=None, rows=None, autonomy="suggest"):
    cam = _cam(tmp_path, rows or [_row("T-001", "Bài một", "2026-09-15",
                                       g1="2026-09-14", folder="./T-001_bai")],
               autonomy=autonomy)
    if writer_cmd:
        fm, than = md_io.read_fm(cam / "campaign.md")
        fm.setdefault("runtime", {})["writer_cmd"] = writer_cmd
        md_io.write_fm(cam / "campaign.md", fm, than)
    (cam / "T-001_bai").mkdir(exist_ok=True)
    (cam / "T-001_bai" / "content.md").write_text(
        "## post:blog_article\n\n{{chưa viết}}\n", encoding="utf-8")
    return cam


def test_KHONG_khai_writer_cmd_thi_bao_cho_nguoi_viet(tmp_path):
    """Fail-closed: không có bộ viết thì nói thẳng, đừng dựng bài rỗng rồi đẩy tiếp."""
    cam = _cam_writer(tmp_path)
    kq = CS.buoc_soan(cam, bot=BotGia(), hom_nay=HOM_NAY)
    assert kq["cho_nguoi_viet"] == ["T-001"], kq
    assert kq["xu_ly"] == 0


def test_writer_cmd_duoc_goi_voi_duong_dan_bai(tmp_path):
    cam = _cam_writer(tmp_path, writer_cmd="python -c \"import sys;print(sys.argv[1])\" {bai}")
    goi = []
    kq = CS.buoc_soan(cam, bot=BotGia(), hom_nay=HOM_NAY,
                      chay=lambda cmd, **kw: goi.append(cmd) or _ok())
    assert goi, "khai writer_cmd mà không gọi"
    assert str(cam / "T-001_bai") in " ".join(goi[0]), goi[0]


def test_writer_cmd_KHONG_chay_qua_shell(tmp_path):
    """Lệnh tách bằng shlex, chạy không shell — `;` trong cấu hình không thành lệnh thứ hai."""
    nguon = (ROOT / "scripts" / "pipeline" / "campaign_step.py").read_text(encoding="utf-8")
    import ast
    for n in ast.walk(ast.parse(nguon)):
        if isinstance(n, ast.Call):
            for kw in n.keywords:
                assert not (kw.arg == "shell" and getattr(kw.value, "value", False) is True), \
                    f"campaign_step dùng shell=True dòng {n.lineno}"


def test_PHAN_HOI_duoc_ghi_ra_file_cho_bo_viet_doc(tmp_path, monkeypatch):
    """Phản hồi là DỮ LIỆU của người: đưa qua FILE, không nối vào dòng lệnh."""
    cam = _cam_writer(tmp_path, writer_cmd="echo {bai}")
    monkeypatch.setattr(CS.AB, "doc_phan_hoi",
                        lambda c, cid: [{"luc": "2026-09-10T10:00:00+07:00",
                                         "noi_dung": "Mở bài dài quá, cắt còn 2 câu."}])
    CS.buoc_soan(cam, bot=BotGia(), hom_nay=HOM_NAY, chay=lambda cmd, **kw: _ok())
    ph = cam / "T-001_bai" / "phan-hoi.md"
    assert ph.is_file(), "không ghi phản hồi ra file cho bộ viết đọc"
    t = ph.read_text(encoding="utf-8")
    assert "cắt còn 2 câu" in t
    assert "```" in t, "phản hồi phải nằm trong khối có rào — nó là dữ liệu, không phải chỉ thị"


def test_writer_HONG_thi_bao_hong_khong_bao_xong(tmp_path):
    cam = _cam_writer(tmp_path, writer_cmd="echo {bai}")
    kq = CS.buoc_soan(cam, bot=BotGia(), hom_nay=HOM_NAY,
                      chay=lambda cmd, **kw: _hong("bộ viết chết"))
    assert kq["hong"] and kq["hong"][0]["id"] == "T-001", kq
    assert kq["xu_ly"] == 0


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
    cam = _cam_writer(tmp_path, writer_cmd="echo {bai}")
    kq = CS.buoc_soan(cam, bot=BotGia(), hom_nay=HOM_NAY, chay=lambda cmd, **kw: _ok())
    assert kq["xu_ly"] == 0, f"bài rỗng mà báo xong: {kq}"
    assert kq["hong"] and "chưa có bài" in kq["hong"][0]["vi_sao"], kq


def test_writer_ma_KHAC_0_thi_HONG_du_bai_co_chu(tmp_path):
    """Mặt kia: writer báo lỗi thì phải là hỏng, kể cả khi file tình cờ có chữ."""
    cam = _cam_writer(tmp_path, writer_cmd="echo {bai}")

    def viet_roi_bao_loi(cmd, **kw):
        (cam / "T-001_bai" / "content.md").write_text(
            "## post:blog_article\n\n" + "Chữ đầy đủ để qua ngưỡng. " * 50, encoding="utf-8")
        return _hong("nhưng tôi vẫn lỗi")

    kq = CS.buoc_soan(cam, bot=BotGia(), hom_nay=HOM_NAY, chay=viet_roi_bao_loi)
    assert kq["xu_ly"] == 0, f"writer báo lỗi mà vẫn tính là xong: {kq}"
    assert kq["hong"] and kq["hong"][0]["vi_sao"] == "writer_cmd", kq


def test_tach_lenh_KHONG_nuot_dau_gach_cheo_windows():
    r"""`shlex.split` mặc định POSIX coi `\` là ký tự thoát ⇒ đường dẫn Windows bị ăn sạch:
    `D:\tram\kenh\x.ps1` -> `D:tramkenhx.ps1`. Lệnh không bao giờ chạy, và lỗi báo ra là
    "không tìm thấy file" — chẳng trỏ vào đâu."""
    cmd = CS.tach_lenh(r'powershell -File D:\tram\kenh\viet-bai.ps1 -Bai {bai}')
    assert r"D:\tram\kenh\viet-bai.ps1" in cmd, cmd
    assert cmd[-1] == "{bai}"


def test_tach_lenh_giu_duong_dan_co_khoang_trang():
    cmd = CS.tach_lenh(r'python "D:\Chuong Trinh\x\y.py" {bai}')
    assert cmd[1] == r"D:\Chuong Trinh\x\y.py", cmd
