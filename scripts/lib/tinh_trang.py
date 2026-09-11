# -*- coding: utf-8 -*-
"""Bài nào đang ở bước nào — SUY RA, không phải sổ trạng thái.

## Vì sao SUY RA chứ không ghi

Trạng thái đã có nơi ở chính thức: cột `g1`/`g2`/`web`/`published` trong bảng Content, và
sự tồn tại của `content.md` / `gates.json`. Đẻ thêm một file "trạng thái" nghĩa là hai chỗ
cùng nói về một việc, và sớm muộn chúng nói khác nhau — đúng thứ cả hệ đang tránh
(*"Không đẻ kho phê duyệt thứ hai"*).

Nên module này **không ghi gì cả**. Nó đọc sự thật rồi tính lại mỗi lần. Xoá đi lúc nào
cũng được; gọi lại thì ra y hệt.

## Vì sao đáng có

Agent nối lại việc sau khi đứt phải biết *"đang ở đâu"*. Cách duy nhất trước đây là nạp cả
`campaign.md` — **38.220 ký tự ≈ 9.555 token**, mà 21.726 ký tự trong đó là bối cảnh, đối
tượng, playbook phân phối: những thứ một agent chạy bước máy móc không cần.

Bản suy ra cho cả 90 bài tốn **~350 token**. Rẻ hơn **27 lần** cho đúng câu hỏi hay hỏi nhất.

## Cạm bẫy: `xong` KHÔNG có nghĩa là hoàn hảo

`xong` chỉ nói *"không còn bước nào trong đường ống này"*. Nó không nói bài hay hay dở.
"""
from __future__ import annotations

import json
from pathlib import Path

import bai_noi_dung
import md_io

# Thứ tự đường ống. Dùng để sắp xếp báo cáo, và để thợ biết bước nào đi trước bước nào.
THU_TU = ["cho-G1", "dung-bai", "soan", "cham-cong", "sua-loi-cong",
          "cho-G2", "dung-trang", "phat-hanh", "xong"]

# Bước nào CẦN NGƯỜI, bước nào máy tự làm được. Thợ chỉ được nhặt việc máy làm được.
CAN_NGUOI = {"cho-G1", "cho-G2"}


def buoc_ke(cam: Path, d: dict) -> str:
    """Bước KẾ TIẾP của một dòng trong bảng Content.

    Đọc theo đúng thứ tự đường ống và trả về bước ĐẦU TIÊN chưa xong. Fail-closed: thiếu
    dữ kiện thì lùi về bước sớm hơn, không bao giờ nhảy cóc lên trước.
    """
    cam = Path(cam)
    if not (d.get("g1") or "").strip():
        return "cho-G1"

    f = (d.get("folder") or "").strip()
    bai = cam / f.lstrip("./") if f else None
    if not bai or not bai.is_dir():
        return "dung-bai"

    if not bai_noi_dung.da_viet(bai):
        return "soan"

    g = bai / "gates.json"
    if not g.is_file():
        return "cham-cong"
    try:
        if (json.loads(g.read_text(encoding="utf-8")).get("ket_luan") or "").lower() == "do":
            return "sua-loi-cong"
    except json.JSONDecodeError:
        return "cham-cong"             # sổ cổng hỏng = coi như chưa chấm

    if not (d.get("g2") or "").strip():
        return "cho-G2"
    if not (d.get("web") or "").strip():
        return "dung-trang"
    if not (d.get("published") or "").strip():
        return "phat-hanh"
    return "xong"


def tinh(cam: Path) -> list[dict]:
    """Mỗi bài một mục: `{content_id, buoc, can_nguoi, folder}`."""
    cam = Path(cam)
    _, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    ra = []
    for d in dong:
        b = buoc_ke(cam, d)
        ra.append({"content_id": d.get("content_id", ""), "buoc": b,
                   "can_nguoi": b in CAN_NGUOI,
                   "folder": (d.get("folder") or "").strip()})
    return ra


def tom_tat(cam: Path) -> dict:
    """Đếm theo bước, sắp theo thứ tự đường ống."""
    ds = tinh(cam)
    dem = {}
    for x in ds:
        dem[x["buoc"]] = dem.get(x["buoc"], 0) + 1
    return {b: dem[b] for b in THU_TU if b in dem}


def dang_chu(cam: Path, *, chi_tiet: bool = False) -> str:
    """Bản in cho người và cho agent đọc. Ngắn có chủ đích."""
    ds = tinh(cam)
    tt = tom_tat(cam)
    d = [f"{b:<14} {n}" for b, n in tt.items()]
    if chi_tiet:
        d.append("")
        for x in sorted(ds, key=lambda y: (THU_TU.index(y["buoc"]), y["content_id"])):
            d.append(f"{x['content_id']:<10} {x['buoc']}")
    return "\n".join(d)
