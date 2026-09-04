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
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402

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
TRANG_THAI = {"proposed": "đề xuất", "approved": "đã duyệt", "in_progress": "đang làm",
              "review": "chờ duyệt", "published": "đã đăng", "paused": "tạm dừng",
              "done": "xong", "archived": "lưu trữ"}


def _e(s) -> str:
    return _html.escape("" if s is None else str(s), quote=True)


def _js(o) -> str:
    """Nhúng JSON vào <script> an toàn: `</script>` trong dữ liệu sẽ cắt đứt thẻ."""
    return (json.dumps(o, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


# ══════════════════════════════════════════════════════════════════ đọc dữ liệu

def doc_campaign(cam_dir: Path) -> dict:
    """Một chiến dịch → dict thuần, không dính Path (để nhúng JSON được)."""
    fm, body = md_io.read_fm(cam_dir / "campaign.md")
    cot, dong = md_io.read_table(body, "CONTENT")
    return {
        "id": fm.get("id", cam_dir.name), "name": fm.get("name", ""),
        "dir": cam_dir.name, "status": fm.get("status", ""),
        "brief": fm.get("brief", "") or fm.get("key_message", ""),
        "fm": {k: v for k, v in fm.items() if not isinstance(v, (dict, list)) or k == "channels"},
        "cot": cot, "dong": dong,
        "so_bai": len(dong),
        "da_dang": sum(1 for d in dong if d.get("status") == "published"),
    }


def doc_kenh(k: dict) -> dict:
    d = k["dir"]
    cams = []
    for c in sorted(d.iterdir()) if d.is_dir() else []:
        if (c / "campaign.md").is_file():
            cams.append(doc_campaign(c))
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


def _o(khoa: str, gia_tri: str) -> str:
    """Một ô. Cột link thành nút bấm được; trạng thái thành chip."""
    v = (gia_tri or "").strip()
    if not v:
        return '<td class="mo">—</td>'
    if khoa in COT_LINK and v.startswith("http"):
        return f'<td><a href="{_e(v)}" target="_blank" rel="noopener">mở ↗</a></td>'
    if khoa == "status":
        lop = "dang" if v == "published" else ("cho" if v in ("review", "approved") else "")
        return f'<td><span class="chip {lop}">{_e(TRANG_THAI.get(v, v))}</span></td>'
    if khoa == "folder":
        return f'<td class="nho"><a href="{_e(v)}">{_e(v)}</a></td>'
    if khoa == "content_name":
        return f'<td class="ten">{_e(v)}</td>'
    return f"<td>{_e(v)}</td>"


def _bang(cot: list, dong: list, id_bang: str) -> str:
    if not dong:
        return '<div class="cuon"><div class="trong">Chưa có dòng nào.</div></div>'
    th = "".join(f"<th>{_e(NHAN.get(c, c))}</th>" for c in cot)
    tr = "".join(
        f'<tr data-tt="{_e(d.get("status", ""))}">'
        + "".join(_o(c, d.get(c, "")) for c in cot) + "</tr>" for d in dong)
    return (f'<div class="cuon"><table id="{id_bang}"><thead><tr>{th}</tr></thead>'
            f"<tbody>{tr}</tbody></table></div>")


# ══════════════════════════════════════════════════════════════════ campaign.html

def html_campaign(c: dict) -> str:
    fm = c["fm"]
    bo_qua = {"schema", "id", "name", "status"}
    kv = "".join(f"<dt>{_e(NHAN.get(k, k))}</dt><dd>{_e(', '.join(v) if isinstance(v, list) else v)}</dd>"
                 for k, v in fm.items() if k not in bo_qua and v not in (None, "", []))
    chua_xong = c["so_bai"] - c["da_dang"]
    than = f"""
<div class="dau"><div>
  <h1>{_e(c['name'] or c['id'])}</h1>
  <div class="mo nho">{_e(c['id'])} · <span class="chip">{_e(TRANG_THAI.get(c['status'], c['status']))}</span>
  · <a href="./campaign.md">campaign.md</a></div>
</div></div>

<div class="luoi">
  <div class="the"><div class="so">{c['so_bai']}</div><div class="mo nho">bài trong chiến dịch</div></div>
  <div class="the"><div class="so">{c['da_dang']}</div><div class="mo nho">đã đăng</div></div>
  <div class="the"><div class="so">{chua_xong}</div><div class="mo nho">chưa xong</div></div>
</div>

<h2>Brief</h2>
<div class="the"><dl class="kv">{kv or '<dt class="mo">chưa điền</dt><dd></dd>'}</dl></div>

<h2>Danh sách bài</h2>
<div class="thanh">
  <input type="search" id="q" placeholder="Tìm trong bảng…">
  <select id="tt"><option value="">Mọi trạng thái</option>
    {''.join(f'<option value="{_e(k)}">{_e(v)}</option>' for k, v in TRANG_THAI.items())}</select>
  <span class="mo nho" id="dem"></span>
  <button id="csv">⤓ Xuất CSV</button>
</div>
{_bang(c['cot'], c['dong'], 'bang')}
"""
    js = f"""
var DL={_js({"cot": c["cot"], "dong": c["dong"], "id": c["id"]})};
var tb=document.getElementById('bang');
if(tb){{ gan(tb);
  function lam(){{ var n=locBang(tb,document.getElementById('q').value,
                                document.getElementById('tt').value);
    document.getElementById('dem').textContent=n+'/'+DL.dong.length+' dòng'; }}
  document.getElementById('q').oninput=lam; document.getElementById('tt').onchange=lam; lam();
}}
document.getElementById('csv').onclick=function(){{xuatCSV(DL.cot,DL.dong,DL.id+'_content.csv');}};
"""
    return _khung(f"{c['name'] or c['id']} — chiến dịch", than, js)


# ══════════════════════════════════════════════════════════════════ index.html

def _duong_toi(goc: Path, dich: Path) -> str:
    """Đường từ `index.html` tới một file, ưu tiên TƯƠNG ĐỐI.

    Kênh không bắt buộc nằm trong trạm (`studio_paths` nói rõ). Ghép cứng `<trạm>/<id>/`
    thì bấm vào là 404 — mà 404 trong một trang tổng quan thì không ai báo cho bạn.
    Khác ổ đĩa thì relpath không tính được, lúc đó dùng `file:///` tuyệt đối.
    """
    try:
        return os.path.relpath(dich, goc).replace("\\", "/")
    except ValueError:
        return dich.resolve().as_uri()


def html_index(kenhs: list, ten_station: str, goc: Path | None = None) -> str:
    hang, tong, dang = [], 0, 0
    for k in kenhs:
        for c in k["campaigns"]:
            for d in c["dong"]:
                tong += 1
                if d.get("status") == "published":
                    dang += 1
                hang.append({"kenh": k["label"], "campaign_id": c["id"],
                             "campaign_name": c["name"],
                             **{x: d.get(x, "") for x in
                                ("content_id", "content_name", "status", "schedule",
                                 "published", "web", "youtube", "facebook")}})
    cot = ["kenh", "campaign_id", "campaign_name", "content_id", "content_name",
           "status", "schedule", "published", "web", "youtube", "facebook"]
    NHAN["kenh"] = "Kênh"

    the_kenh = ""
    for k in kenhs:
        ds = "".join(
            f'<li><a href="{_e(_duong_toi(goc, Path(k["dir"]) / c["dir"] / "campaign.html"))}">'
            f'{_e(c["name"] or c["id"])}</a>'
            f' <span class="mo nho">· {c["da_dang"]}/{c["so_bai"]} đã đăng</span></li>'
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
    {''.join(f'<option value="{_e(k)}">{_e(v)}</option>' for k, v in TRANG_THAI.items())}</select>
  <span class="mo nho" id="dem"></span>
  <button id="csv">⤓ Xuất CSV</button>
</div>
{_bang(cot, hang, 'bang')}
"""
    js = f"""
var DL={_js({"cot": cot, "dong": hang})};
var tb=document.getElementById('bang');
if(tb){{ gan(tb);
  function lam(){{ var n=locBang(tb,document.getElementById('q').value,
                                document.getElementById('tt').value);
    document.getElementById('dem').textContent=n+'/'+DL.dong.length+' dòng'; }}
  document.getElementById('q').oninput=lam; document.getElementById('tt').onchange=lam; lam();
}}
document.getElementById('csv').onclick=function(){{xuatCSV(DL.cot,DL.dong,'toan_canh.csv');}};
"""
    return _khung(f"Toàn cảnh — {ten_station}", than, js)


# ══════════════════════════════════════════════════════════════════ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sinh campaign.html và index.html từ Markdown.")
    ap.add_argument("--station", default=None)
    ap.add_argument("--campaign", default=None, help="chỉ sinh cho MỘT chiến dịch")
    a = ap.parse_args(argv)

    if a.campaign:
        cam = Path(a.campaign).resolve()
        if not (cam / "campaign.md").is_file():
            sys.stderr.write(f"không thấy campaign.md trong {cam}\n")
            return 2
        md_io.ghi_nguyen_tu(cam / "campaign.html", html_campaign(doc_campaign(cam)))
        print(f"  {cam / 'campaign.html'}")
        return 0

    station = SP.root(a.station).resolve()
    kenhs = [doc_kenh(k) for k in SP.channels(station)]
    n = 0
    for k in kenhs:
        for c in k["campaigns"]:
            p = Path(k["dir"]) / c["dir"] / "campaign.html"
            md_io.ghi_nguyen_tu(p, html_campaign(c))
            n += 1
    md_io.ghi_nguyen_tu(station / "index.html",
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
