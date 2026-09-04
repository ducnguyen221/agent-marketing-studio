# -*- coding: utf-8 -*-
"""Test cho export_excel — Excel là BẢN XUẤT, đi một chiều từ Markdown.

Điều quan trọng nhất phải giữ: **bộ cột không đổi**. Người dùng có biểu mẫu, công thức và
pivot bám vào đúng thứ tự cột của `CAMPAIGN_TEMPLATE.xlsx` v3; đổi thứ tự là hỏng hết mà
không ai báo. Vì vậy test so cột với chính file template trong repo, không so với một danh
sách chép tay — chép tay thì cả hai cùng trôi mà vẫn xanh.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import md_io as M  # noqa: E402

openpyxl = pytest.importorskip("openpyxl")
import export_excel as EX  # noqa: E402

TPL = ROOT / "templates" / "CAMPAIGN_TEMPLATE.xlsx"
COT = ["content_id", "content_name", "pillar", "funnel", "angle", "priority",
       "status", "g1", "schedule", "published", "folder", "web", "youtube", "facebook"]


@pytest.fixture
def cam(tmp_path):
    C = tmp_path / "CMP-2609-x"
    B = C / "AST-001_slug"
    B.mkdir(parents=True)
    M.write_fm(C / "campaign.md",
               {"id": "CMP-2609-x", "name": "Chiến dịch thử", "channel": "tobi",
                "channels": ["web_blog", "youtube"],
                "kpi_target": {"blog": 300, "youtube": 150}},
               "\n<!-- CONTENT:BEGIN -->\n" + M.render_table(COT, [{
                   "content_id": "AST-001", "content_name": "Bài A", "pillar": "ai-agent",
                   "funnel": "awareness", "angle": "news", "priority": "high",
                   "status": "published", "g1": "2026-09-04", "schedule": "2026-09-04",
                   "published": "2026-09-04", "folder": "./AST-001_slug/",
                   "web": "https://vidu.vn/a.html", "youtube": "https://youtu.be/X",
                   "facebook": ""}]) + "\n<!-- CONTENT:END -->\n")
    M.write_fm(B / "research.md",
               {"content_id": "AST-001", "content_goal": "Mục tiêu bài",
                "target_keyword": "từ khoá", "audio": "yes", "video": "yes", "short": "no"}, "")
    (B / "publish.json").write_text(json.dumps({
        "schema": "publish/2", "post_id": "AST-001", "posts": [
            {"post_id": "AST-001-web", "channel": "web_blog", "post_format": "blog_article",
             "post_content": "post:blog_article",
             "review": {"status": "approved", "note": "ok"},
             "publish": {"status": "published", "link": "https://vidu.vn/a.html",
                         "at": "2026-09-04T10:00:00"},
             "metrics": {"view": 120, "reach": 900, "at": "2026-09-05"}}]},
        ensure_ascii=False), encoding="utf-8")
    return C


def _mo(p):
    return openpyxl.load_workbook(p)


def test_bo_cot_KHOP_template_cu(cam):
    """Cột lệch template = biểu mẫu, công thức và pivot của người dùng hỏng câm."""
    tpl = _mo(TPL)
    for sheet, cot_ta in (("Content", EX.COT_CONTENT), ("Post", EX.COT_POST)):
        assert [c.value for c in tpl[sheet][1]] == cot_ta, f"sheet {sheet} lệch template"


def test_xuat_du_ba_sheet_va_du_lieu_that(cam):
    w = _mo(EX.xuat(cam))
    assert w.sheetnames == ["Campaign", "Content", "Post"]

    h = [c.value for c in w["Content"][1]]
    d = dict(zip(h, [c.value for c in w["Content"][2]]))
    assert d["content_id"] == "AST-001" and d["status"] == "published"
    assert d["content_pillar"] == "ai-agent", "pillar (md) phải vào content_pillar (xlsx)"
    assert d["approved_date"] == "2026-09-04", "g1 (md) phải vào approved_date (xlsx)"
    assert d["content_goal"] == "Mục tiêu bài", "làm giàu từ research.md của chính bài"

    h = [c.value for c in w["Post"][1]]
    p = dict(zip(h, [c.value for c in w["Post"][2]]))
    assert p["post_id"] == "AST-001-web" and p["publish_link"] == "https://vidu.vn/a.html"
    assert p["actual_view"] == 120 and p["actual_reach"] == 900


def test_dict_long_TRAI_PHANG_chu_khong_vo(cam):
    """kpi_target là dict — nhét cả object vào một ô thì openpyxl từ chối thẳng."""
    ws = _mo(EX.xuat(cam))["Campaign"]
    kv = {r[0].value: r[1].value for r in ws.iter_rows(min_row=2)}
    assert kv["kpi_target.blog"] == 300 and kv["kpi_target.youtube"] == 150


def test_ghi_ro_day_la_BAN_XUAT(cam):
    """Không ghi rõ thì có người sẽ sửa Excel và tưởng đã sửa dữ liệu."""
    ws = _mo(EX.xuat(cam))["Campaign"]
    cuoi = [c.value for c in ws[ws.max_row]]
    assert "NGUỒN SỰ THẬT" in str(cuoi[0]) and "campaign.md" in str(cuoi[1])
    assert "KHÔNG quay ngược" in str(cuoi[2])


def test_truong_chua_co_thi_DE_TRONG_chu_khong_bia(cam):
    d = dict(zip([c.value for c in _mo(EX.xuat(cam))["Content"][1]],
                 [c.value for c in _mo(EX.xuat(cam))["Content"][2]]))
    assert d["notes"] in ("", None), "ô rỗng nói 'chưa biết' — đừng bịa cho đầy bảng"


def test_bai_chua_dang_thi_KHONG_co_dong_Post(cam):
    fm, body = M.read_fm(cam / "campaign.md")
    body = M.upsert_row(body, "CONTENT", "content_id",
                        {"content_id": "AST-002", "folder": "./AST-002_chua/"})
    M.write_fm(cam / "campaign.md", fm, body)
    w = _mo(EX.xuat(cam))
    assert w["Content"].max_row == 3, "Content có cả bài chưa đăng"
    assert w["Post"].max_row == 2, "Post chỉ có bài đã có publish.json"


def test_xuat_lai_KHONG_dung_vao_markdown(cam):
    truoc = (cam / "campaign.md").read_text(encoding="utf-8")
    EX.xuat(cam)
    EX.xuat(cam)
    assert (cam / "campaign.md").read_text(encoding="utf-8") == truoc
    assert not list(cam.glob("*.tmp")), "file tạm phải được đổi tên, không để lại"
