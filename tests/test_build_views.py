# -*- coding: utf-8 -*-
"""Test cho build_views — hai bản HTML để người đọc.

Ba thứ phải giữ, mỗi thứ một lý do cụ thể:

1. **Không phụ thuộc mạng.** `file://` chặn `fetch`, và máy có thể đang không có mạng.
   Trang cần server để xem là trang không ai xem.
2. **Dữ liệu nhúng khớp Markdown.** HTML là bản ĐỌC; lệch một ô là người đọc sai số.
3. **JS thật sự chạy.** Test chạy chính đoạn JS trong file đã sinh (trích ra, cấp một DOM
   tối thiểu), không chạy một bản chép — bản chép xanh trong khi bản thật hỏng là vô dụng.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import build_views as BV  # noqa: E402
import md_io as M  # noqa: E402

NODE = shutil.which("node")

COT = ["content_id", "content_name", "status", "published", "web", "youtube", "facebook"]
DONG = [
    {"content_id": "AST-001", "content_name": "Bài một, có dấu phẩy", "status": "published",
     "published": "2026-09-04", "web": "https://vidu.vn/a.html",
     "youtube": "https://youtu.be/X", "facebook": "https://facebook.com/1_2"},
    {"content_id": "AST-002", "content_name": 'Bài "hai"', "status": "proposed",
     "published": "", "web": "", "youtube": "", "facebook": ""},
]


@pytest.fixture
def station(tmp_path):
    S = tmp_path / "st"
    K = S / "tobi"
    C = K / "CMP-2609-x"
    C.mkdir(parents=True)
    M.write_fm(S / "CHANNELS.md", {"schema": "channels/1", "channels": [
        {"id": "tobi", "label": "Tobi AI", "path": "./tobi", "status": "active"}]}, "# Sổ\n")
    (K / "channel.yml").write_text("schema: channel/1\nid: tobi\n", encoding="utf-8")
    M.write_fm(C / "campaign.md",
               {"id": "CMP-2609-x", "name": "Chiến dịch thử", "channel": "tobi",
                "status": "active", "key_message": "Thông điệp chính",
                "channels": ["web_blog", "youtube"]},
               "\n<!-- CONTENT:BEGIN -->\n" + M.render_table(COT, DONG) + "\n<!-- CONTENT:END -->\n")
    BV.main(["--station", str(S)])
    return S, C


def test_khong_phu_thuoc_mang(station):
    S, C = station
    for f in (S / "index.html", C / "campaign.html"):
        t = f.read_text(encoding="utf-8")
        assert "fetch(" not in t and "XMLHttpRequest" not in t
        assert "<script src" not in t, "script ngoài = mở ở file:// hoặc lúc mất mạng là vỡ"
        assert not re.search(r'<link[^>]+href="https?:', t), "CSS ngoài cũng vậy"
        # Ngoài <script> (nơi dữ liệu bài nằm), URL http DUY NHẤT được phép là link bài
        # đã đăng trong thẻ <a> — mọi cái khác là một thứ trang đi tải về từ mạng.
        than = re.sub(r"<script>.*?</script>", "", t, flags=re.S)
        for m in re.finditer(r'https?://[^\s"\']+', than):
            assert than[max(0, m.start() - 9):m.start()] == '<a href="', \
                f"URL ngoài thẻ <a>: {m.group()}"


def test_du_lieu_nhung_khop_markdown(station):
    S, C = station
    dl = json.loads(re.search(r"var DL=(\{.*?\});",
                              (C / "campaign.html").read_text(encoding="utf-8"), re.S).group(1)
                    .replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&"))
    assert dl["cot"] == COT
    assert [d["content_id"] for d in dl["dong"]] == ["AST-001", "AST-002"]
    assert dl["dong"][0]["content_name"] == "Bài một, có dấu phẩy"


def test_URL_thanh_nut_bam_duoc(station):
    t = station[1].joinpath("campaign.html").read_text(encoding="utf-8")
    assert '<a href="https://youtu.be/X" target="_blank"' in t
    assert t.count('rel="noopener"') >= 3, "3 cột link của bài đã đăng phải bấm được"


def test_index_gom_moi_kenh_va_tro_dung_campaign(station):
    t = station[0].joinpath("index.html").read_text(encoding="utf-8")
    assert "Tobi AI" in t
    assert 'href="tobi/CMP-2609-x/campaign.html"' in t, \
        "đường dẫn tương đối, nếu không thì chép STATION đi chỗ khác là gãy"
    assert "AST-001" in t and "AST-002" in t


def test_sinh_lai_khong_doi_gi_khac(station):
    """HTML là bản ĐỌC: sinh lại phải ra đúng thứ đang có trong .md, không đụng .md."""
    S, C = station
    truoc_md = (C / "campaign.md").read_text(encoding="utf-8")
    BV.main(["--station", str(S)])
    assert (C / "campaign.md").read_text(encoding="utf-8") == truoc_md


@pytest.mark.skipif(not NODE, reason="không có node")
def test_JS_THAT_chay_duoc_loc_va_xuat_csv(station, tmp_path):
    """Chạy chính đoạn JS trong file đã sinh, với một DOM tối thiểu."""
    html = station[1].joinpath("campaign.html").read_text(encoding="utf-8")
    js = re.search(r"<script>(.*?)</script>", html, re.S).group(1)

    harness = r"""
// ── DOM tối thiểu: đủ để đoạn JS thật chạy, không hơn.
let CSV = null;
class El {
  constructor(){ this.style={}; this.dataset={}; this.cells=[]; this._t=""; }
  get innerText(){ return this._t || this.cells.map(c=>c.innerText).join(" "); }
  set innerText(v){ this._t = v; }
  set textContent(v){ this._t = v; }
  appendChild(){} remove(){}
  click(){ }
}
const rows = DONG_JS.map(d => {
  const r = new El();
  r.dataset.tt = d.status;
  r.cells = Object.values(d).map(v => { const c = new El(); c.innerText = String(v); return c; });
  return r;
});
const bang = new El();
bang.tBodies = [{ rows, appendChild(){} }];
bang.tHead   = { rows: [{ cells: [new El(), new El(), new El(), new El(),
                                  new El(), new El(), new El()] }] };
const els = { bang, q: new El(), tt: new El(), dem: new El(), csv: new El() };
global.document = {
  getElementById: id => els[id] || null,
  createElement: () => { const a = new El(); a.click = () => {}; return a; },
  body: new El(),
};
global.URL = { createObjectURL: b => { CSV = b; return "blob:x"; }, revokeObjectURL(){} };
global.Blob = class { constructor(p){ this.parts = p; } };
global.setTimeout = f => f();
"""
    day_du = (f"const DONG_JS = {json.dumps(DONG, ensure_ascii=False)};\n"
              + harness + js + r"""
// ── kiểm 1: lọc theo chữ
els.q.value = "AST-002"; els.tt.value = "";
els.q.oninput();
const hien = () => rows.filter(r => r.style.display !== "none").length;
if (hien() !== 1) throw new Error("lọc theo chữ sai: còn " + hien());

// ── kiểm 2: lọc theo trạng thái
els.q.value = ""; els.tt.value = "published"; els.tt.onchange();
if (hien() !== 1) throw new Error("lọc theo trạng thái sai: còn " + hien());

// ── kiểm 3: xuất CSV — dấu phẩy và dấu nháy trong dữ liệu phải được bọc đúng
els.q.value = ""; els.tt.value = ""; els.q.oninput();
els.csv.onclick();
const s = CSV.parts[0];
if (s.charCodeAt(0) !== 0xFEFF) throw new Error("thiếu BOM — Excel bản Việt sẽ hỏng dấu");
const Q = String.fromCharCode(34);   // dựng bằng mã, đừng viết thẳng: ba nháy liền nhau
if (!s.includes(Q + "Bài một, có dấu phẩy" + Q)) throw new Error("dấu phẩy không được bọc");
if (!s.includes(Q + "Bài " + Q + Q + "hai" + Q + Q + Q))
  throw new Error("dấu nháy không được nhân đôi");
if (s.trim().split("\n").length !== 3) throw new Error("phải 1 dòng tiêu đề + 2 dòng");
console.log("JS OK");
""")
    f = tmp_path / "chay.js"
    f.write_text(day_du, encoding="utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"JS thật lỗi:\n{r.stdout}\n{r.stderr}"
    assert "JS OK" in r.stdout


def test_kenh_NGOAI_tram_van_bam_duoc(tmp_path):
    """`studio_paths` nói rõ kênh có thể nằm ngoài trạm. Link cứng `<trạm>/<id>/` thì bấm
    vào là 404 — mà 404 trong một trang tổng quan thì không ai báo cho bạn."""
    S, K = tmp_path / "st", tmp_path / "ngoai" / "kenhx"
    C = K / "CMP-2609-y"
    C.mkdir(parents=True)
    S.mkdir()
    M.write_fm(S / "CHANNELS.md", {"schema": "channels/1", "channels": [
        {"id": "kenhx", "label": "Kênh ngoài", "path": str(K), "status": "active"}]}, "# Sổ\n")
    (K / "channel.yml").write_text("schema: channel/1\nid: kenhx\n", encoding="utf-8")
    M.write_fm(C / "campaign.md", {"id": "CMP-2609-y", "name": "CD ngoài", "channel": "kenhx"},
               "\n<!-- CONTENT:BEGIN -->\n" + M.render_table(COT, DONG[:1]) + "\n<!-- CONTENT:END -->\n")
    BV.main(["--station", str(S)])

    t = (S / "index.html").read_text(encoding="utf-8")
    m = re.search(r'href="([^"]*campaign\.html)"', t)
    assert m, "không có link tới campaign.html"
    dich = (S / m.group(1)).resolve() if not Path(m.group(1)).is_absolute() \
        else Path(m.group(1))
    assert dich.is_file() or (C / "campaign.html").samefile(dich), \
        f"link {m.group(1)!r} không trỏ tới file có thật — bấm vào là 404"
