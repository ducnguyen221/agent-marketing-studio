#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kho CỔNG DUYỆT — nơi DUY NHẤT ghi ba cổng, và mặt tiền TRONG PHIÊN.

## Vì sao có file này

Trước 12/09/2026, người ghi `g1` và `g3` duy nhất là `approve_bus.py` — mặt tiền Telegram.
Nghĩa là **Telegram không phải tuỳ chọn, nó là con đường duy nhất**: không có điện thoại
thì cả chiến dịch đứng. Mà cách làm việc mặc định lại là người ngồi cùng agent trong một
phiên, đọc file trên máy rồi gật ngay tại chỗ.

Nên tách làm hai tầng:

```
        mặt tiền                       kho cổng                  chỗ ở thật
  approve_bus.py  (Telegram) ─┐
                              ├─► cong_duyet.mo_cong() ─► campaign.md · publish.json
  cong_duyet.py   (trong phiên)┘
```

Hai mặt tiền NGANG HÀNG. Cái nào cũng ghi vào đúng một chỗ, đúng một cách, cùng để lại
dấu vết trong `logs/su-kien.jsonl`. Thêm mặt tiền thứ ba (web, CLI khác) chỉ cần gọi vào
đây, không được đẻ kho cổng riêng.

## Cổng ở đâu

| Cổng | Chỗ ở thật | Hàm ghi |
|---|---|---|
| **g1** — duyệt đề tài | cột `g1` + `status=approved` trong bảng Content của `campaign.md` | `ghi_g1` |
| **g2** — duyệt trước khi đăng | `publish.json → posts[].review` (+ ô `g2` mirror) | `ghi_g2` → gọi `register_publish approve` |
| **g3** — duyệt BẢN THẬT trên web | cột `g3` trong bảng Content | `ghi_cot` |

Không đẻ kho phê duyệt thứ hai. Hai nguồn sự thật thì sớm muộn chúng nói khác nhau.

## Hai điều bắt buộc khi mở cổng

1. **`boi`** — AI duyệt. Cổng không có tên người là cổng vô chủ.
2. **`nguyen_van`** — NGUYÊN VĂN câu người nói. Không phải để đẹp hồ sơ: đây là thứ ngăn
   agent tự đóng dấu thay người. Agent chép được câu của người thì câu đó phải đã tồn tại.
   Cùng luật với `register_publish approve --note`, đặt ra từ 04/09/2026.

⚠️ **KHÔNG xếp việc.** Mở cổng xong có chạy tiếp hay không là quyết định của MẶT TIỀN:
Telegram xếp việc cho thợ chạy nền, còn agent trong phiên thường chạy bước kế tiếp ngay.
Gộp hai thứ vào đây thì một trong hai đường sẽ làm việc hai lần.

## Lệnh (dùng trong phiên, không cần Telegram)

```
cong_duyet.py <chiến dịch> cho     --cong g1|g2|g3 [--json]
cong_duyet.py <chiến dịch> mo      --cong g1|g2|g3 --bai A,B --boi "Đức" --nguyen-van "..."
cong_duyet.py <chiến dịch> tu-choi --cong g1|g2|g3 --bai A   --boi "Đức" --nguyen-van "..."
```

`cho` in kèm **đường dẫn file để mở** — đó là thứ người cần để duyệt thật thay vì gật bừa.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
import bai_noi_dung  # noqa: E402
import md_io  # noqa: E402
import so_su_kien as SO  # noqa: E402

CONG = ("g1", "g2", "g3")

# Tên file giữ tiền tố `tg-` vì LÝ DO DỮ LIỆU: chiến dịch đang chạy có sẵn file này, đổi
# tên là bỏ lại toàn bộ phản hồi cũ. Nội dung thì không riêng của Telegram nữa — phản hồi
# gõ trong phiên cũng vào đây, và vòng viết lại đọc chung một chỗ.
TEN_PHAN_HOI = "tg-phan-hoi.json"


def loi(m: str) -> None:
    sys.stderr.write(f"cong_duyet: {m}\n")


# ── Bảng Content ────────────────────────────────────────────────────────────

def doc_bang(cam: Path):
    fm, than = md_io.read_fm(Path(cam) / "campaign.md")
    cot, dong = md_io.read_table(than, "CONTENT")
    return fm, than, cot, dong


def da_viet_bai(cam: Path, dong: dict) -> bool:
    """Bài của DÒNG này đã có chữ thật chưa. Không khai `folder` = chưa viết (fail-closed)."""
    f = (dong.get("folder") or "").strip()
    if not f:
        return False
    return bai_noi_dung.da_viet(Path(cam) / f.lstrip("./"))


def vi_sao_chua_duoc_hoi(cam: Path, dong: dict) -> str:
    """Lý do bài này CHƯA được phép đem ra hỏi ở Cổng 2. Chuỗi rỗng = được hỏi.

    FAIL-CLOSED ba nhánh (Đức chốt 11/09/2026):
      · chưa viết          — không có gì để đọc
      · chưa chấm cổng nào — KHÔNG ĐO ĐƯỢC nghĩa là *chưa biết*, không phải *đã qua*
      · máy chấm ĐỎ        — máy đã nói không thì đừng đem hỏi người

    Vì sao nhánh giữa quan trọng ngang nhánh cuối: `content.md` đầy đủ **không** chứng minh
    bài đã qua kiểm. Ca thật NEN-002 — gọi thẳng bộ viết, nhảy cóc bước chấm B4, file bài
    trông hoàn hảo mà chưa một cổng nào chạy.

    Trả LÝ DO chứ không trả bool: bỏ qua im lặng thì người vận hành không biết vì sao bài
    của mình không bao giờ tới cổng.
    """
    if not da_viet_bai(cam, dong):
        return "CHƯA VIẾT"

    f = (dong.get("folder") or "").strip()
    p = Path(cam) / f.lstrip("./") / "gates.json"
    if not p.is_file():
        return "CHƯA CHẤM cổng nào (thiếu gates.json) — chạy blog_gates.py trước"
    try:
        g = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "gates.json HỎNG — coi như chưa chấm"

    if (g.get("ket_luan") or "").lower() == "do":
        do = [c.get("ma", "?") for c in (g.get("cong") or [])
              if c.get("trang_thai") == "do" and c.get("muc") != "canh_bao"]
        return (f"máy chấm ĐỎ ({g.get('do_chan', '?')} cổng chặn"
                + (f": {', '.join(do[:8])}" if do else "") + ")")
    return ""


def cho_cong(cam: Path, cong: str) -> list[dict]:
    """Bài đang chờ đúng cổng đó. g1: chưa có g1. g2: có g1, chưa có g2."""
    _, _, _, dong = doc_bang(cam)
    if cong == "g1":
        return [d for d in dong if not (d.get("g1") or "").strip()]
    if cong == "g3":
        # Cổng 3 duyệt BẢN THẬT: phải đã lên web mới có gì để xem. Và chỉ hỏi khi bảng
        # CÓ KHAI cột `g3` — bảng cũ không khai thì không có cổng này.
        return [d for d in dong
                if "g3" in d and (d.get("web") or "").strip()
                and not (d.get("g3") or "").strip()]
    return [d for d in dong
            if (d.get("g1") or "").strip() and not (d.get("g2") or "").strip()]


def ho_so_bai(cam: Path, dong: dict) -> dict:
    """Bài này có những file NÀO ĐANG CÓ THẬT để người mở ra kiểm.

    Đây là phần hay bị bỏ quên nhất của một cổng duyệt: hỏi "duyệt không?" mà không nói
    đọc ở đâu thì người chỉ còn cách gật bừa, và cổng thành con dấu cao su — đúng chỗ
    Cổng 2 đã dính ngày 11/09/2026.

    Chỉ liệt kê file **tồn tại**. Kê một đường dẫn không có thật còn tệ hơn không kê:
    người mở không được sẽ tưởng máy hỏng chứ không hiểu là bước đó chưa chạy.
    """
    cam = Path(cam)
    f = (dong.get("folder") or "").strip().lstrip("./")
    ho_so: dict = {"content_id": dong.get("content_id", ""),
                   "content_name": dong.get("content_name", ""),
                   "thu_muc": f, "file": {}, "web": (dong.get("web") or "").strip()}
    if not f:
        return ho_so
    bai = cam / f
    for nhan, tuong_doi in (("bài", "content.md"),
                            ("nghiên cứu", "research.md"),
                            ("chấm cổng", "gates.json"),
                            ("blog tách kênh", "atlas/blog.md"),
                            ("trang dựng sẵn", "atlas/atlas.html"),
                            ("facebook", "facebook/post.txt"),
                            ("youtube", "youtube/description.txt")):
        p = bai / tuong_doi
        if p.is_file():
            ho_so["file"][nhan] = str(p)
    return ho_so


# ── Phản hồi của người ──────────────────────────────────────────────────────

def doc_phan_hoi(cam: Path, cid: str) -> list[dict]:
    """Mọi phản hồi của người cho một bài, theo thứ tự thời gian.

    GIỮ ĐỦ, không ghi đè: vòng viết lại có thể lặp, và ghi đè lần trước là mất dấu vết vì
    sao bài thành ra như thế. Sáu tháng sau đọc lại còn hiểu được.
    """
    p = Path(cam) / "logs" / TEN_PHAN_HOI
    if not p.is_file():
        return []
    try:
        return (json.loads(p.read_text(encoding="utf-8")) or {}).get(cid, [])
    except json.JSONDecodeError:
        loi(f"{p} hỏng — coi như chưa có phản hồi nào.")
        return []


def ghi_phan_hoi(cam: Path, cid: str, noi_dung: str) -> None:
    p = Path(cam) / "logs" / TEN_PHAN_HOI
    d = {}
    if p.is_file():
        try:
            d = json.loads(p.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError:
            pass
    d.setdefault(cid, []).append(
        {"luc": datetime.now().astimezone().isoformat(), "noi_dung": noi_dung})
    p.parent.mkdir(parents=True, exist_ok=True)
    md_io.ghi_nguyen_tu(p, json.dumps(d, ensure_ascii=False, indent=2) + "\n")


# ── Ghi cổng ────────────────────────────────────────────────────────────────

def ghi_g1(cam: Path, cids: list[str], ngay: str) -> list[str]:
    """Ghi cột g1 + status. IDEMPOTENT: bài đã có g1 thì bỏ qua, không ghi đè."""
    cam = Path(cam)
    fm, than, _, dong = doc_bang(cam)
    hien = {d["content_id"]: d for d in dong}
    xong = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        if (d.get("g1") or "").strip():
            continue                       # đã duyệt rồi, không ghi lại
        than = md_io.upsert_row(than, "CONTENT", "content_id",
                                {"content_id": cid, "g1": ngay, "status": "approved"},
                                chi_cap_nhat=True)
        xong.append(cid)
    if xong:
        md_io.write_fm(cam / "campaign.md", fm, than)
    return xong


def ghi_cot(cam: Path, cids: list[str], cot: str, gia_tri: str) -> list[str]:
    """Ghi một cột ngày duyệt. IDEMPOTENT: đã có thì bỏ qua, không ghi đè."""
    cam = Path(cam)
    fm, than, _, dong = doc_bang(cam)
    hien = {d["content_id"]: d for d in dong}
    xong = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        if (d.get(cot) or "").strip():
            continue
        than = md_io.upsert_row(than, "CONTENT", "content_id",
                                {"content_id": cid, cot: gia_tri}, chi_cap_nhat=True)
        xong.append(cid)
    if xong:
        md_io.write_fm(cam / "campaign.md", fm, than)
    return xong


def ghi_g2(cam: Path, cids: list[str], boi: str, ghi_chu: str) -> list[str]:
    """Gọi ĐÚNG `register_publish approve` — giữ nguyên dấu vết duyệt đang có."""
    cam = Path(cam)
    _, _, _, dong = doc_bang(cam)
    hien = {d["content_id"]: d for d in dong}
    rp = _HERE / "register_publish.py"
    xong = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        thu_muc = (d.get("folder") or "").strip().lstrip("./")
        bai = cam / thu_muc
        if not bai.is_dir():
            loi(f"{cid}: không thấy thư mục bài {bai} — bỏ qua.")
            continue
        r = subprocess.run(
            [sys.executable, str(rp), str(bai), "approve", "--by", boi, "--note", ghi_chu],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            loi(f"{cid}: register_publish approve thất bại — {r.stdout}{r.stderr}")
            continue
        xong.append(cid)
    return xong


# ── Mở / từ chối cổng — lối vào DUY NHẤT của mọi mặt tiền ───────────────────

def _kiem_chung_nhan(boi: str, nguyen_van: str) -> None:
    """Cổng phải biết AI duyệt và người đó nói GÌ. Thiếu một trong hai là ném lỗi.

    Fail-closed chứ không cảnh báo rồi ghi: một cổng ghi được mà không có chứng nhân thì
    hồ sơ nói "đã duyệt" trong khi không ai duyệt, và không gì phát hiện ra sau đó.
    """
    if not (boi or "").strip():
        raise ValueError("thiếu `boi`: cổng phải biết AI duyệt.")
    if not (nguyen_van or "").strip():
        raise ValueError(
            "thiếu `nguyen_van`: chép NGUYÊN VĂN câu duyệt của người. "
            "Đây là thứ ngăn agent tự đóng dấu thay người.")


def mo_cong(cam: Path, cong: str, cids: list[str], *, boi: str, nguyen_van: str,
            qua: str, bay_gio: datetime | None = None) -> list[str]:
    """Mở một cổng cho các bài đã nêu. Trả về danh sách bài THỰC SỰ được ghi.

    Idempotent: bài đã qua cổng thì không nằm trong kết quả và không sinh sự kiện mới.
    KHÔNG xếp việc — xem cảnh báo ở đầu file.
    """
    cam = Path(cam)
    if cong not in CONG:
        raise ValueError(f"cổng lạ: {cong!r} — chỉ có {', '.join(CONG)}")
    _kiem_chung_nhan(boi, nguyen_van)
    bay_gio = bay_gio or datetime.now().astimezone()

    if cong == "g1":
        xong = ghi_g1(cam, cids, bay_gio.date().isoformat())
    elif cong == "g3":
        xong = ghi_cot(cam, cids, "g3", bay_gio.date().isoformat())
    else:
        xong = ghi_g2(cam, cids, boi, nguyen_van)

    for cid in xong:
        SO.ghi(cam, f"{cong}_duyet", bai=cid, boi=boi, qua=qua, ghi_chu=nguyen_van[:300])
    return xong


def tu_choi(cam: Path, cong: str, cids: list[str], *, boi: str, nguyen_van: str,
            qua: str) -> list[str]:
    """Ghi từ chối + phản hồi. KHÔNG đụng vào cổng: từ chối là *chưa duyệt*, không phải xoá.

    Phản hồi vào kho chung để vòng viết lại đọc được. Từ chối mà không nói vì sao thì lần
    viết lại sau cũng ra đúng bài cũ.
    """
    cam = Path(cam)
    if cong not in CONG:
        raise ValueError(f"cổng lạ: {cong!r} — chỉ có {', '.join(CONG)}")
    _kiem_chung_nhan(boi, nguyen_van)
    for cid in cids:
        SO.ghi(cam, f"{cong}_tu_choi", bai=cid, boi=boi, qua=qua, ly_do=nguyen_van[:300])
        ghi_phan_hoi(cam, cid, nguyen_van)
    return list(cids)


# ── CLI trong phiên ─────────────────────────────────────────────────────────

def _in_cho(cam: Path, cong: str, *, ra_json: bool) -> int:
    ds = cho_cong(cam, cong)
    ho_so = []
    for d in ds:
        h = ho_so_bai(cam, d)
        if cong == "g2":
            h["chua_duoc_hoi"] = vi_sao_chua_duoc_hoi(cam, d)
        ho_so.append(h)

    if ra_json:
        print(json.dumps({"cong": cong, "so_bai": len(ho_so), "bai": ho_so},
                         ensure_ascii=False, indent=2))
        return 0

    if not ho_so:
        print(f"{cong}: không bài nào đang chờ.")
        return 0
    print(f"{cong}: {len(ho_so)} bài đang chờ\n")
    for h in ho_so:
        print(f"· {h['content_id']} — {h['content_name']}")
        if h.get("chua_duoc_hoi"):
            print(f"    ⛔ chưa được đem ra hỏi: {h['chua_duoc_hoi']}")
        for nhan, p in h["file"].items():
            print(f"    {nhan:<16} {p}")
        if h["web"]:
            print(f"    {'bản thật':<16} {h['web']}")
        print()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cổng duyệt — mặt tiền TRONG PHIÊN, không cần Telegram.")
    ap.add_argument("campaign", help="thư mục chiến dịch")
    sub = ap.add_subparsers(dest="lenh", required=True)

    pc = sub.add_parser("cho", help="bài nào đang chờ cổng, kèm file để mở kiểm")
    pc.add_argument("--cong", choices=list(CONG), required=True)
    pc.add_argument("--json", action="store_true")

    for ten, tro in (("mo", "mở cổng"), ("tu-choi", "ghi từ chối + phản hồi")):
        p = sub.add_parser(ten, help=tro)
        p.add_argument("--cong", choices=list(CONG), required=True)
        p.add_argument("--bai", required=True, help="mã bài, phân tách bằng dấu phẩy")
        p.add_argument("--boi", required=True, help="ai duyệt")
        p.add_argument("--nguyen-van", required=True,
                       help="NGUYÊN VĂN câu người nói — agent KHÔNG được tự bịa")
        p.add_argument("--qua", default="phiên", help="mặt tiền nào (mặc định: phiên)")

    a = ap.parse_args(argv)
    cam = Path(a.campaign)
    if not (cam / "campaign.md").is_file():
        loi(f"không thấy {cam / 'campaign.md'}")
        return 2

    if a.lenh == "cho":
        return _in_cho(cam, a.cong, ra_json=a.json)

    cids = [x.strip() for x in a.bai.split(",") if x.strip()]
    if not cids:
        loi("--bai rỗng")
        return 2
    try:
        if a.lenh == "mo":
            xong = mo_cong(cam, a.cong, cids, boi=a.boi,
                           nguyen_van=a.nguyen_van, qua=a.qua)
            print(f"{a.cong}: đã mở cho {len(xong)}/{len(cids)} bài"
                  + (f" — {', '.join(xong)}" if xong else " (không bài nào đổi)"))
        else:
            xong = tu_choi(cam, a.cong, cids, boi=a.boi,
                           nguyen_van=a.nguyen_van, qua=a.qua)
            print(f"{a.cong}: đã ghi từ chối {len(xong)} bài — {', '.join(xong)}")
    except ValueError as e:
        loi(str(e))
        return 2
    # Không bài nào đổi ≠ hỏng: idempotent nghĩa là chạy lại vẫn 0.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
