# -*- coding: utf-8 -*-
"""UAT — chạy TRỌN đường ống 6 bước 3 cổng trên một chiến dịch dựng từ TEMPLATE.

## Vì sao cần file này khi đã có 400 test đơn vị

Bài học đắt nhất của đợt 10–12/09/2026, lặp lại ba lần:

> 264 test xanh, rồi chạy thật một lượt ra **ba lỗi** — trong đó có `main()` trả `exit=0`
> cho lượt thất bại hoàn toàn, và bước chấm trả mã 1 cho một *kết quả* hợp lệ khiến mọi bài
> cần sửa bị vứt vào `hong/`.

Vì sao test đơn vị không bắt được: chúng gọi HÀM chứ không đi qua `main()`; chúng dùng
fixture rỗng chứ không phải bảng đã lập lịch; và **bản giả trả về đúng theo ý người viết
test — chính là người đang hiểu sai**.

File này khác ở ba chỗ: dựng chiến dịch từ **template thật** (thứ người clone repo nhận
được), chạy **đủ sáu bước theo đúng thứ tự**, và mở **cả ba cổng** như người thật.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import approve_bus as AB     # noqa: E402
import campaign_step as CS   # noqa: E402
import md_io                 # noqa: E402
import tinh_trang as TT      # noqa: E402

MAU_CAMPAIGN = ROOT / "templates" / "station" / "_channel" / "_campaign" / "campaign.md"


class BotGia:
    def __init__(self):
        self.da_gui, self.da_file = [], []

    def duoc_phep(self, _):
        return True

    def gui(self, text, **kw):
        self.da_gui.append(text)
        return len(self.da_gui) + len(self.da_file)

    def gui_kem_nut(self, text, nut, **kw):
        self.da_gui.append(text)
        return len(self.da_gui) + len(self.da_file)

    def gui_tai_lieu(self, duong_dan, chu_thich="", **kw):
        self.da_file.append(str(duong_dan))
        return len(self.da_gui) + len(self.da_file)

    def sua_tin(self, *a, **k):
        pass

    def tra_loi_nut(self, *a, **k):
        pass

    def lay_cap_nhat(self, **kw):
        return []


@pytest.fixture
def tram(tmp_path):
    """Dựng trạm từ TEMPLATE THẬT — không chép tay bảng vào test.

    Chép tay nghĩa là test kiểm một cái bảng chỉ tồn tại trong test. Đọc template thật thì
    template hỏng là UAT đỏ, đúng thứ ta muốn.
    """
    kenh = tmp_path / "tram" / "kenh-uat"
    cam = kenh / "CD-UAT"
    (cam / "logs").mkdir(parents=True)
    (kenh / "channel.yml").write_text(
        "schema: channel/1\nid: kenh-uat\nlabel: \"UAT\"\nautonomy: suggest\n"
        "home_domain: uat.test\n"
        "platforms:\n  - channel: web_blog\n    post_formats: [blog_article]\n",
        encoding="utf-8", newline="\n")
    (kenh / "brand.md").write_text("# Giọng\n\nThẳng, không hoa mỹ.\n",
                                   encoding="utf-8", newline="\n")

    # Lấy bảng Content TỪ TEMPLATE, chỉ thêm một dòng dữ liệu.
    mau = MAU_CAMPAIGN.read_text(encoding="utf-8")
    fm, than = md_io.read_fm(MAU_CAMPAIGN)
    tieu_de, _ = md_io.read_table(than, "CONTENT")
    assert "g3" in tieu_de, "template mất cột g3 ⇒ Cổng 3 tắt cho mọi chiến dịch mới"

    dong = {c: "" for c in tieu_de}
    dong.update({"content_id": "U-001", "content_name": "Bài UAT", "pillar": "ai-agent",
                 "angle": "explainer", "funnel": "awareness", "priority": "high",
                 "status": "proposed", "schedule": "2026-09-15",
                 "folder": "./U-001_bai-uat"})
    than = md_io.upsert_row(than, "CONTENT", "content_id", dong)
    fm = dict(fm)
    fm.update({"id": "CD-UAT", "channel": "kenh-uat", "id_prefix": "U",
               "name": "UAT", "status": "active", "content_pillar": "ai-agent"})
    fm["runtime"] = {"label": "UAT"}
    md_io.write_fm(cam / "campaign.md", fm, than)

    bai = cam / "U-001_bai-uat"
    (bai / "atlas").mkdir(parents=True)
    (bai / "meta.json").write_text(json.dumps(
        {"post_id": "U-001", "title": "Bài UAT", "slug": "bai-uat", "category": "ai"}),
        encoding="utf-8", newline="\n")
    (bai / "content.md").write_text(
        "## post:blog_article\n\n> Khuôn.\n\n# {{tieu_de}}\n\n{{than}}\n",
        encoding="utf-8", newline="\n")
    return cam, bai


def _bang(cam):
    _, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    return {d["content_id"]: d for d in dong}


def _duyet(cam, cong, bot):
    """Mở một cổng đúng cách người thật làm: gửi tin, rồi bấm nút."""
    kq = AB.gui_cong(cam, cong, bot=bot)
    assert kq.get("gui"), f"cổng {cong} không gửi được tin: {kq}"
    tok = list(json.loads((cam / "logs" / "tg-approve.json")
                          .read_text(encoding="utf-8"))["cho"])[0]
    b = BotGia()
    b.lay_cap_nhat = lambda **kw: [{  # noqa: E731
        "update_id": 1,
        "callback_query": {"id": "cq", "data": f"ok:{tok}",
                           "message": {"message_id": 1, "chat": {"id": 1}},
                           "from": {"id": 1}}}]
    AB.nhan(cam, bot=b)


def test_UAT_tron_duong_ong_6_buoc_3_cong(tram, monkeypatch):
    """Đi hết `cho-G1` → `xong`, mở cả ba cổng, không bỏ sót nấc nào."""
    cam, bai = tram
    bot = BotGia()

    # ── nấc 1: chờ Cổng 1 ────────────────────────────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "cho-G1"
    _duyet(cam, "g1", bot)
    assert _bang(cam)["U-001"]["g1"] != "", "duyệt Cổng 1 mà cột g1 vẫn trống"

    # ── nấc 2: soạn (bộ viết giả điền bài) ───────────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "soan"
    than = "Câu chuyện đời thường mở bài. " * 60
    (bai / "content.md").write_text(f"## post:blog_article\n\n# Bài UAT\n\n{than}\n",
                                    encoding="utf-8", newline="\n")

    # ── nấc 3: chấm 23 cổng ──────────────────────────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "cham-cong"
    (bai / "gates.json").write_text(
        json.dumps({"tong": 23, "xanh": 23, "do_chan": 0, "ket_luan": "xanh", "cong": []}),
        encoding="utf-8", newline="\n")

    # ── nấc 4: chờ Cổng 2, và tin PHẢI kèm bài ───────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "cho-G2"
    b2 = BotGia()
    AB.gui_cong(cam, "g2", bot=b2)
    assert b2.da_file, "Cổng 2 không gửi bài ⇒ mời duyệt thứ không nhìn thấy được"
    tok = list(json.loads((cam / "logs" / "tg-approve.json")
                          .read_text(encoding="utf-8"))["cho"])[0]
    monkeypatch.setattr(AB, "_ghi_g2", lambda c, ids, boi, gc: list(ids))
    b2.lay_cap_nhat = lambda **kw: [{  # noqa: E731
        "update_id": 2,
        "callback_query": {"id": "cq2", "data": f"ok:{tok}",
                           "message": {"message_id": 2, "chat": {"id": 1}},
                           "from": {"id": 1}}}]
    AB.nhan(cam, bot=b2)
    # `_ghi_g2` thật ghi vào publish.json; UAT này đo ĐƯỜNG ỐNG nên ghi thẳng cột.
    fm, t = md_io.read_fm(cam / "campaign.md")
    t = md_io.upsert_row(t, "CONTENT", "content_id",
                         {"content_id": "U-001", "g2": "2026-09-12"}, chi_cap_nhat=True)
    md_io.write_fm(cam / "campaign.md", fm, t)

    # ── nấc 5: dựng trang + đăng web ─────────────────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "dung-trang"
    (bai / "atlas" / "blog.md").write_text("# Bài UAT\n\nThân bài.\n",
                                           encoding="utf-8", newline="\n")

    def chay_dung(lenh, **kw):
        t_ = " ".join(str(x) for x in lenh)

        class R:
            returncode, stdout, stderr = 0, "", ""
        if "build_blog_html" in t_:
            Path(lenh[lenh.index("--out") + 1]).write_text(
                "<html>UAT</html>", encoding="utf-8", newline="\n")
        if "web_publish" in t_:
            R.stdout = json.dumps({"blog_url": "https://uat.test/bai-uat", "http": 200})
        return R()

    kq = CS.buoc_dung_trang(cam, bot=bot, chay=chay_dung)
    assert kq["xu_ly"] == 1, kq
    assert _bang(cam)["U-001"]["web"] == "https://uat.test/bai-uat"

    # ── nấc 6: chờ Cổng 3, và tin PHẢI kèm LINK ──────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "cho-G3"
    b3 = BotGia()
    AB.gui_cong(cam, "g3", bot=b3)
    assert "https://uat.test/bai-uat" in b3.da_gui[0], \
        f"Cổng 3 không chở link bản thật: {b3.da_gui[0]}"
    _duyet(cam, "g3", BotGia())
    assert _bang(cam)["U-001"]["g3"] != ""

    # ── nấc 7: phát hành ─────────────────────────────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "phat-hanh"
    kq = CS.buoc_phat_hanh(cam, bot=bot, chay=lambda *a, **k: None)
    assert kq["xu_ly"] == 1, kq

    # ── đích ─────────────────────────────────────────────────────────────
    assert TT.buoc_ke(cam, _bang(cam)["U-001"]) == "xong"
    assert TT.tom_tat(cam) == {"xong": 1}


def test_UAT_template_bat_du_BA_CONG(tram):
    """Chiến dịch dựng từ template phải có đủ ba cổng — không thiếu cái nào.

    Cổng 3 bật bằng cách khai cột `g3`. Template mất cột đó thì mọi chiến dịch MỚI mất
    lặng lẽ một cổng, và không gì báo.
    """
    cam, _ = tram
    d = _bang(cam)["U-001"]
    assert "g1" in d and "g2" in d and "g3" in d, f"template thiếu cột cổng: {sorted(d)}"


def test_UAT_khong_buoc_nao_TU_NHAY_COC_qua_cong(tram):
    """Ba cổng phải nằm trong `CAN_NGUOI` — thợ không bao giờ tự mở."""
    assert TT.CAN_NGUOI == {"cho-G1", "cho-G2", "cho-G3"}
    for c in TT.CAN_NGUOI:
        assert c in TT.THU_TU, f"{c} không nằm trong đường ống"
