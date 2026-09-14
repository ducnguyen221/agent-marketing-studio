#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_views.py — sinh HAI bản HTML để NGƯỜI đọc, từ chính các file Markdown.

  · `campaign.html` cạnh mỗi `campaign.md`  — một chiến dịch: brief + danh sách bài
  · `index.html` ở gốc STATION              — toàn cảnh: mọi kênh, mọi chiến dịch, mọi bài

Ba luật của hai file này, mỗi luật đến từ một chỗ đã trả giá:

1. **MỞ ĐƯỢC BẰNG CÁCH BẤM ĐÚP.** Không `fetch`, không CDN, không server. `file://` chặn
   `fetch` ngay cả với file cạnh nó, nên dữ liệu phải NHÚNG THẲNG vào HTML dạng JSON.
   Trang cần server để xem là trang không ai xem.

2. **HTML LÀ BẢN ĐỌC, KHÔNG PHẢI NGUỒN.** Markdown là nguồn duy nhất. Sinh lại HTML bất
   cứ lúc nào cũng ra đúng cái đang có trong `.md`. Không bao giờ sửa HTML rồi mong nó
   quay ngược về Markdown.

3. **XUẤT CSV BẰNG JS THUẦN.** Người dùng bấm nút là có file — không cần Python, không cần
   cài gì. Bản Python (`export_excel.py`) là để chạy trong pipeline, không phải để người
   ngồi chờ.

CLI:
  python build_views.py --station ~/.marketing            # cả STATION: index + mọi campaign
  python build_views.py --campaign <đường/dẫn/chiến-dịch> # một chiến dịch
"""
from __future__ import annotations

import argparse
import html as _html
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402
import pipeline_state as PS  # noqa: E402
import approval_gate as AG  # noqa: E402

# Nhãn tiếng Việt cho cột. Cột nào không có ở đây thì in nguyên tên khoá — thêm cột mới
# vào bảng không được làm vỡ trang.
NHAN = {
    "content_id": "Mã", "content_name": "Tên bài", "pillar": "Trụ", "angle": "Góc",
    "funnel": "Phễu", "priority": "Ưu tiên", "status": "Trạng thái",
    "g1": "Cổng 1", "g2": "Cổng 2", "schedule": "Lịch", "published": "Đã đăng",
    "folder": "Thư mục", "web": "Web", "youtube": "YouTube", "facebook": "Facebook",
    "campaign_id": "Mã chiến dịch", "campaign_name": "Chiến dịch",
    "bài": "Bài", "đã đăng": "Đã đăng",
}
COT_LINK = ("web", "youtube", "facebook")
STATUSES = {"proposed": "đề xuất", "approved": "đã duyệt", "in_progress": "đang làm",
              "review": "chờ duyệt", "published": "đã đăng", "paused": "tạm dừng",
              "done": "done", "archived": "lưu trữ"}


def _e(s) -> str:
    return _html.escape("" if s is None else str(s), quote=True)


def _js(o) -> str:
    """Nhúng JSON vào <script> an toàn: `</script>` trong dữ liệu sẽ cắt đứt thẻ."""
    return (json.dumps(o, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


# ══════════════════════════════════════════════════════════════════ đọc dữ liệu

def _progress(campaign_dir: Path, row: list) -> dict:
    """Bài nào đang ở bước nào, và bài đang chờ cổng thì MỞ FILE NÀO để duyệt.

    Trang này là chỗ người xem tiến độ mà không phải gõ lệnh. Nếu nó chỉ nói "T-001 chờ
    Cổng 2" mà không kèm đường dẫn bài thì người vẫn phải đi lục thư mục — và cổng lại
    thành con dấu cao su, đúng chỗ đã dính 11/09/2026.

    Đường dẫn để TƯƠNG ĐỐI so với thư mục chiến dịch: trang mở bằng `file://` cạnh
    `campaign.md`, nên tương đối là bấm được, còn tuyệt đối thì gãy khi ai đó chép cây
    thư mục đi nơi khác.
    """
    by_step: dict[str, list[str]] = {}
    waiting_at: dict[str, list[dict]] = {}
    for d in row:
        try:
            b = PS.next_step(campaign_dir, d)
        except Exception:                      # noqa: BLE001 — trang đọc KHÔNG được sập
            b = "?"                            # vì một dòng lỗi; báo "?" rồi đi tiếp
        by_step.setdefault(b, []).append(d.get("content_id", ""))
        if b in PS.NEEDS_HUMAN:
            h = AG.post_files(campaign_dir, d)
            waiting_at.setdefault(b.replace("cho-G", "g"), []).append({
                "content_id": h["content_id"], "content_name": h["content_name"],
                "web": h["web"],
                "file": {k: os.path.relpath(v, campaign_dir).replace(os.sep, "/")
                         for k, v in h["file"].items()}})
    return {"by_step": {b: by_step[b] for b in PS.ORDER if b in by_step},
            "khac": {b: v for b, v in by_step.items() if b not in PS.ORDER},
            "waiting_at": waiting_at}


def read_campaign(campaign_dir: Path) -> dict:
    """Một chiến dịch → dict thuần, không dính Path (để nhúng JSON được)."""
    fm, body = md_io.read_fm(campaign_dir / "campaign.md")
    col, row = md_io.read_table(body, "CONTENT")
    return {
        "tien_do": _progress(campaign_dir, row),
        "id": fm.get("id", campaign_dir.name), "name": fm.get("name", ""),
        "dir": campaign_dir.name, "status": fm.get("status", ""),
        "brief": fm.get("brief", "") or fm.get("key_message", ""),
        "fm": {k: v for k, v in fm.items() if not isinstance(v, (dict, list)) or k == "channels"},
        "col": col, "row": row,
        "count": len(row),
        "da_dang": sum(1 for d in row if d.get("status") == "published"),
    }


def read_channel(k: dict) -> dict:
    d = k["dir"]
    cams = []
    for c in sorted(d.iterdir()) if d.is_dir() else []:
        if (c / "campaign.md").is_file():
            cams.append(read_campaign(c))
    return {"id": k["id"], "label": k.get("label", k["id"]), "dir": str(d),
            "status": k.get("status", ""), "campaigns": cams}


# ══════════════════════════════════════════════════════════════════ khung HTML

CSS = """
:root{--nen:#0f1115;--the:#171a21;--vien:#252a35;--chu:#e6e9ef;--mo:#98a2b3;
      --nhan:#7dd3fc;--ok:#4ade80;--cho:#fbbf24;--tat:#64748b}
@media (prefers-color-scheme:light){:root{--nen:#f7f8fa;--the:#fff;--vien:#e3e6ec;
      --chu:#1a1d24;--mo:#5b6472;--nhan:#0369a1}}
*{box-sizing:border-box}
body{margin:0;background:var(--nen);color:var(--chu);font:15px/1.55 -apple-system,
     "Segoe UI",Roboto,"Be Vietnam Pro",sans-serif}
.bao{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:30px 0 10px}
.mo{color:var(--mo)}.nho{font-size:13px}
.dau{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;justify-content:space-between}
.the{background:var(--the);border:1px solid var(--vien);border-radius:10px;padding:14px 16px}
.luoi{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:14px 0}
.so{font-size:26px;font-weight:600}
.cuon{overflow-x:auto;border:1px solid var(--vien);border-radius:10px;background:var(--the)}
tr.cho td{background:color-mix(in srgb,var(--cho) 14%,transparent)}
.so-nho{font-weight:600;text-align:right;width:5em}
ul.ds{margin:8px 0 0;padding-left:18px}ul.ds li{margin:6px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:8px 11px;text-align:left;border-bottom:1px solid var(--vien);white-space:nowrap}
th{position:sticky;top:0;background:var(--the);font-weight:600;font-size:12.5px;
   color:var(--mo);text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none}
th:hover{color:var(--chu)}
tbody tr:hover{background:rgba(125,211,252,.06)}
td.ten{white-space:normal;min-width:230px}
a{color:var(--nhan);text-decoration:none}a:hover{text-decoration:underline}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;
      border:1px solid var(--vien);color:var(--mo)}
.chip.dang{color:var(--ok);border-color:var(--ok)}
.chip.cho{color:var(--cho);border-color:var(--cho)}
.thanh{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:14px 0}
input[type=search],select{background:var(--the);border:1px solid var(--vien);color:var(--chu);
      border-radius:8px;padding:7px 11px;font:inherit;font-size:14px}
input[type=search]{min-width:230px}
button{background:var(--the);border:1px solid var(--vien);color:var(--chu);border-radius:8px;
      padding:7px 13px;font:inherit;font-size:14px;cursor:pointer}
button:hover{border-color:var(--nhan);color:var(--nhan)}
.kv{display:grid;grid-template-columns:190px 1fr;gap:5px 16px;font-size:14px}
.kv dt{color:var(--mo)}.kv dd{margin:0}
footer{margin-top:44px;color:var(--mo);font-size:12.5px;border-top:1px solid var(--vien);
      padding-top:14px}
.trong{padding:22px;color:var(--mo);text-align:center}
"""

# JS chung: lọc, sắp xếp, xuất CSV. Không thư viện ngoài — trang phải chạy ở file://.
JS = r"""
function csvO(v){v=(v==null?'':String(v));
  return /[",\n;]/.test(v) ? '"'+v.replace(/"/g,'""')+'"' : v;}
function xuatCSV(cot,dong,ten){
  // BOM: thiếu nó thì Excel bản Việt mở ra "Trá»‹" thay vì "Trị". Đã dính một lần.
  var s='﻿'+cot.map(csvO).join(',')+'\n'
      +dong.map(function(d){return cot.map(function(c){return csvO(d[c]);}).join(',');}).join('\n');
  var a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([s],{type:'text/csv;charset=utf-8'}));
  a.download=ten; document.body.appendChild(a); a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href); a.remove();},0);
}
function sapXep(tb,i){
  var t=tb.tBodies[0], ds=Array.prototype.slice.call(t.rows);
  var nguoc = tb.__cot===i ? !tb.__nguoc : false;
  ds.sort(function(a,b){
    var x=a.cells[i].innerText.trim(), y=b.cells[i].innerText.trim();
    var r = (x===''&&y!=='') ? 1 : (y===''&&x!=='') ? -1
          : x.localeCompare(y,'vi',{numeric:true});
    return nguoc ? -r : r;});
  ds.forEach(function(r){t.appendChild(r);});
  tb.__cot=i; tb.__nguoc=nguoc;
}
function locBang(tb,q,tt){
  q=(q||'').toLowerCase(); var n=0;
  Array.prototype.forEach.call(tb.tBodies[0].rows,function(r){
    var hop = (!q || r.innerText.toLowerCase().indexOf(q)>=0)
           && (!tt || (r.dataset.tt||'')===tt);
    r.style.display = hop ? '' : 'none'; if(hop) n++;});
  return n;
}
function gan(tb){
  Array.prototype.forEach.call(tb.tHead.rows[0].cells,function(th,i){
    th.title='Bấm để sắp xếp'; th.onclick=function(){sapXep(tb,i);};});
}
"""


def _khung(tieu_de: str, than: str, du_lieu_js: str = "") -> str:
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(tieu_de)}</title>
<style>{CSS}</style></head><body><div class="bao">
{than}
<footer>Sinh bởi <code>build_views.py</code> lúc {datetime.now():%d/%m/%Y %H:%M} —
bản ĐỌC. Nguồn duy nhất là các file <code>.md</code>; sửa ở đó rồi sinh lại.</footer>
</div>
<script>{JS}{du_lieu_js}</script></body></html>
"""


def _box(khoa: str, gia_tri: str) -> str:
    """Một ô. Cột link thành nút bấm được; trạng thái thành chip."""
    v = (gia_tri or "").strip()
    if not v:
        return '<td class="mo">—</td>'
    if khoa in COT_LINK and v.startswith("http"):
        return f'<td><a href="{_e(v)}" target="_blank" rel="noopener">mở ↗</a></td>'
    if khoa == "status":
        lop = "dang" if v == "published" else ("pending" if v in ("review", "approved") else "")
        return f'<td><span class="chip {lop}">{_e(STATUSES.get(v, v))}</span></td>'
    if khoa == "folder":
        return f'<td class="nho"><a href="{_e(v)}">{_e(v)}</a></td>'
    if khoa == "content_name":
        return f'<td class="ten">{_e(v)}</td>'
    return f"<td>{_e(v)}</td>"


def _bang(col: list, row: list, id_bang: str) -> str:
    if not row:
        return '<div class="cuon"><div class="trong">Chưa có dòng nào.</div></div>'
    th = "".join(f"<th>{_e(NHAN.get(c, c))}</th>" for c in col)
    tr = "".join(
        f'<tr data-tt="{_e(d.get("status", ""))}">'
        + "".join(_box(c, d.get(c, "")) for c in col) + "</tr>" for d in row)
    return (f'<div class="cuon"><table id="{id_bang}"><thead><tr>{th}</tr></thead>'
            f"<tbody>{tr}</tbody></table></div>")


# ══════════════════════════════════════════════════════════════════ campaign.html

# Nhãn cho mười trạng thái của đường ống. Nguồn thứ tự là `pipeline_state.ORDER`, ở đây chỉ
# dịch sang tiếng người — thiếu nhãn thì in nguyên mã bước, không được làm vỡ trang.
STEP_LABELS = {
    "await-G1": "Chờ Cổng 1 · duyệt đề tài",
    "create-post": "Dựng thư mục bài",
    "write": "Đang chờ soạn",
    "check-gates": "Chờ chấm 24 cổng",
    "fix-gates": "Cổng đỏ · chờ viết lại",
    "await-G2": "Chờ Cổng 2 · duyệt trước khi đăng",
    "build-page": "Chờ dựng trang + đăng web",
    "await-G3": "Chờ Cổng 3 · duyệt bản thật",
    "release": "Chờ phát hành kênh ngoài",
    "done": "Xong hẳn",
}
GATE_LABELS = {"g1": "Cổng 1 — duyệt đề tài",
             "g2": "Cổng 2 — duyệt trước khi đăng",
             "g3": "Cổng 3 — duyệt BẢN THẬT trên web"}


def _html_progress(td: dict) -> str:
    """Khối 'bài đang ở đâu' + 'ai đang chờ mình quyết', kèm link mở file."""
    queue = []
    for b, ds in list(td["by_step"].items()) + list(td.get("khac", {}).items()):
        label = STEP_LABELS.get(b, b)
        pending = ' class="cho"' if b in ("await-G1", "await-G2", "await-G3") else ""
        queue.append(f'<tr{pending}><td>{_e(label)}</td><td class="so-nho">{len(ds)}</td>'
                    f'<td class="mo nho">{_e(", ".join(ds[:14]))}'
                    f'{" …" if len(ds) > 14 else ""}</td></tr>')
    bang = ('<div class="cuon"><table><thead><tr><th>Bước</th><th>Số bài</th>'
            '<th>Bài</th></tr></thead><tbody>' + "".join(queue) + "</tbody></table></div>")

    khoi = []
    for gate, ds in td.get("waiting_at", {}).items():
        level = []
        for h in ds:
            lk = " · ".join(f'<a href="./{_e(p)}">{_e(label)}</a>'
                            for label, p in h["file"].items())
            if h.get("web"):
                lk += (" · " if lk else "") + f'<a href="{_e(h["web"])}">bản thật</a>'
            level.append(f'<li><b>{_e(h["content_id"])}</b> — {_e(h["content_name"])}'
                       + (f'<div class="nho">{lk}</div>' if lk
                          else '<div class="nho mo">chưa có file nào để mở</div>')
                       + "</li>")
        khoi.append(f'<div class="the"><b>{_e(GATE_LABELS.get(gate, gate))}</b>'
                    f'<ul class="ds">{"".join(level)}</ul></div>')
    if not khoi:
        khoi = ['<div class="the mo">Không bài nào đang chờ người quyết.</div>']
    return bang + '<h2>Đang chờ mình quyết</h2>' + "".join(khoi)


def html_campaign(c: dict) -> str:
    fm = c["fm"]
    bo_qua = {"schema", "id", "name", "status"}
    kv = "".join(f"<dt>{_e(NHAN.get(k, k))}</dt><dd>{_e(', '.join(v) if isinstance(v, list) else v)}</dd>"
                 for k, v in fm.items() if k not in bo_qua and v not in (None, "", []))
    chua_xong = c["count"] - c["da_dang"]
    than = f"""
<div class="dau"><div>
  <h1>{_e(c['name'] or c['id'])}</h1>
  <div class="mo nho">{_e(c['id'])} · <span class="chip">{_e(STATUSES.get(c['status'], c['status']))}</span>
  · <a href="./campaign.md">campaign.md</a></div>
</div></div>

<div class="luoi">
  <div class="the"><div class="so">{c['count']}</div><div class="mo nho">bài trong chiến dịch</div></div>
  <div class="the"><div class="so">{c['da_dang']}</div><div class="mo nho">đã đăng</div></div>
  <div class="the"><div class="so">{chua_xong}</div><div class="mo nho">chưa xong</div></div>
</div>

<h2>Brief</h2>
<div class="the"><dl class="kv">{kv or '<dt class="mo">chưa điền</dt><dd></dd>'}</dl></div>

<h2>Tiến độ đường ống</h2>
{_html_progress(c['tien_do'])}

<h2>Danh sách bài</h2>
<div class="thanh">
  <input type="search" id="q" placeholder="Tìm trong bảng…">
  <select id="tt"><option value="">Mọi trạng thái</option>
    {''.join(f'<option value="{_e(k)}">{_e(v)}</option>' for k, v in STATUSES.items())}</select>
  <span class="mo nho" id="dem"></span>
  <button id="csv">⤓ Xuất CSV</button>
</div>
{_bang(c['col'], c['row'], 'bang')}
"""
    js = f"""
var DL={_js({"col": c["col"], "row": c["row"], "id": c["id"]})};
var tb=document.getElementById('bang');
if(tb){{ gan(tb);
  function lam(){{ var n=locBang(tb,document.getElementById('q').value,
                                document.getElementById('tt').value);
    document.getElementById('dem').textContent=n+'/'+DL.row.length+' dòng'; }}
  document.getElementById('q').oninput=lam; document.getElementById('tt').onchange=lam; lam();
}}
document.getElementById('csv').onclick=function(){{xuatCSV(DL.col,DL.row,DL.id+'_content.csv');}};
"""
    return _khung(f"{c['name'] or c['id']} — chiến dịch", than, js)


# ══════════════════════════════════════════════════════════════════ index.html

def _path_to(src: Path, dest: Path) -> str:
    """Đường từ `index.html` tới một file, ưu tiên TƯƠNG ĐỐI.

    Kênh không bắt buộc nằm trong trạm (`studio_paths` nói rõ). Ghép cứng `<trạm>/<id>/`
    thì bấm vào là 404 — mà 404 trong một trang tổng quan thì không ai báo cho bạn.
    Khác ổ đĩa thì relpath không tính được, lúc đó dùng `file:///` tuyệt đối.
    """
    try:
        return os.path.relpath(dest, src).replace("\\", "/")
    except ValueError:
        return dest.resolve().as_uri()


def html_index(kenhs: list, ten_station: str, src: Path | None = None) -> str:
    queue, tong, dang = [], 0, 0
    for k in kenhs:
        for c in k["campaigns"]:
            for d in c["row"]:
                tong += 1
                if d.get("status") == "published":
                    dang += 1
                queue.append({"kenh": k["label"], "campaign_id": c["id"],
                             "campaign_name": c["name"],
                             **{x: d.get(x, "") for x in
                                ("content_id", "content_name", "status", "schedule",
                                 "published", "web", "youtube", "facebook")}})
    col = ["kenh", "campaign_id", "campaign_name", "content_id", "content_name",
           "status", "schedule", "published", "web", "youtube", "facebook"]
    NHAN["kenh"] = "Kênh"

    the_kenh = ""
    for k in kenhs:
        ds = "".join(
            f'<li><a href="{_e(_path_to(src, Path(k["dir"]) / c["dir"] / "campaign.html"))}">'
            f'{_e(c["name"] or c["id"])}</a>'
            f' <span class="mo nho">· {c["da_dang"]}/{c["count"]} đã đăng</span></li>'
            for c in k["campaigns"]) or '<li class="mo">chưa có chiến dịch nào</li>'
        the_kenh += (f'<div class="the"><b>{_e(k["label"])}</b>'
                     f'<div class="mo nho">{_e(k["id"])} · {len(k["campaigns"])} chiến dịch</div>'
                     f'<ul style="margin:9px 0 0;padding-left:18px">{ds}</ul></div>')

    than = f"""
<div class="dau"><div>
  <h1>Toàn cảnh nội dung</h1>
  <div class="mo nho">{_e(ten_station)} · {len(kenhs)} kênh</div>
</div></div>

<div class="luoi">
  <div class="the"><div class="so">{len(kenhs)}</div><div class="mo nho">kênh</div></div>
  <div class="the"><div class="so">{sum(len(k['campaigns']) for k in kenhs)}</div>
       <div class="mo nho">chiến dịch</div></div>
  <div class="the"><div class="so">{tong}</div><div class="mo nho">bài</div></div>
  <div class="the"><div class="so">{dang}</div><div class="mo nho">đã đăng</div></div>
</div>

<h2>Kênh &amp; chiến dịch</h2>
<div class="luoi">{the_kenh or '<div class="the mo">chưa có kênh nào trong CHANNELS.md</div>'}</div>

<h2>Mọi bài</h2>
<div class="thanh">
  <input type="search" id="q" placeholder="Tìm bài, kênh, chiến dịch…">
  <select id="tt"><option value="">Mọi trạng thái</option>
    {''.join(f'<option value="{_e(k)}">{_e(v)}</option>' for k, v in STATUSES.items())}</select>
  <span class="mo nho" id="dem"></span>
  <button id="csv">⤓ Xuất CSV</button>
</div>
{_bang(col, queue, 'bang')}
"""
    js = f"""
var DL={_js({"col": col, "row": queue})};
var tb=document.getElementById('bang');
if(tb){{ gan(tb);
  function lam(){{ var n=locBang(tb,document.getElementById('q').value,
                                document.getElementById('tt').value);
    document.getElementById('dem').textContent=n+'/'+DL.row.length+' dòng'; }}
  document.getElementById('q').oninput=lam; document.getElementById('tt').onchange=lam; lam();
}}
document.getElementById('csv').onclick=function(){{xuatCSV(DL.col,DL.row,'toan_canh.csv');}};
"""
    return _khung(f"Toàn cảnh — {ten_station}", than, js)


# ══════════════════════════════════════════════════════════════════ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sinh campaign.html và index.html từ Markdown.")
    ap.add_argument("--station", default=None)
    ap.add_argument("--campaign", default=None, help="chỉ sinh cho MỘT chiến dịch")
    a = ap.parse_args(argv)

    if a.campaign:
        campaign = Path(a.campaign).resolve()
        if not (campaign / "campaign.md").is_file():
            sys.stderr.write(f"không thấy campaign.md trong {campaign}\n")
            return 2
        md_io.write_atomic(campaign / "campaign.html", html_campaign(read_campaign(campaign)))
        print(f"  {campaign / 'campaign.html'}")
        return 0

    station = SP.root(a.station).resolve()
    kenhs = [read_channel(k) for k in SP.channels(station)]
    n = 0
    for k in kenhs:
        for c in k["campaigns"]:
            p = Path(k["dir"]) / c["dir"] / "campaign.html"
            md_io.write_atomic(p, html_campaign(c))
            n += 1
    md_io.write_atomic(station / "index.html",
                        html_index(kenhs, station.name, station))
    print(f"  {n} campaign.html")
    print(f"  {station / 'index.html'}  ← mở bằng cách bấm đúp")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
