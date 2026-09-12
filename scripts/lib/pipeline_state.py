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

import post_content
import md_io

# Thứ tự đường ống. Dùng để sắp xếp báo cáo, và để thợ biết bước nào đi trước bước nào.
ORDER = ["await-G1", "create-post", "write", "check-gates", "fix-gates",
          "await-G2", "build-page", "await-G3", "release", "done"]

# Bước nào CẦN NGƯỜI, bước nào máy tự làm được. Thợ chỉ được nhặt việc máy làm được.
NEEDS_HUMAN = {"await-G1", "await-G2", "await-G3"}


def next_step(campaign: Path, d: dict) -> str:
    """Bước KẾ TIẾP của một dòng trong bảng Content.

    Đọc theo đúng thứ tự đường ống và trả về bước ĐẦU TIÊN chưa xong. Fail-closed: thiếu
    dữ kiện thì lùi về bước sớm hơn, không bao giờ nhảy cóc lên trước.
    """
    campaign = Path(campaign)
    if not (d.get("g1") or "").strip():
        return "await-G1"

    f = (d.get("folder") or "").strip()
    post = campaign / f.lstrip("./") if f else None
    if not post or not post.is_dir():
        return "create-post"

    if not post_content.has_content(post):
        return "write"

    g = post / "gates.json"
    if not g.is_file():
        return "check-gates"
    try:
        if (json.loads(g.read_text(encoding="utf-8")).get("verdict") or "").lower() == "fail":
            return "fix-gates"
    except json.JSONDecodeError:
        return "check-gates"             # sổ cổng hỏng = coi như chưa chấm

    if not (d.get("g2") or "").strip():
        return "await-G2"
    if not (d.get("web") or "").strip():
        return "build-page"

    # CỔNG 3 — duyệt BẢN THẬT trên web. Bật bằng cách KHAI CỘT `g3` trong bảng Content.
    #
    # Vì sao "khai cột = bật cổng" chứ không bật mặc định: thêm một cổng mà làm đứng hết
    # các chiến dịch đang chạy là cái giá không đáng trả. Bảng cũ không có cột `g3` thì
    # `d` không có khoá đó, và ta đi thẳng tới phát hành y như trước.
    #
    # Phân biệt bằng `in d`, KHÔNG bằng giá trị rỗng: cột có mà để trống nghĩa là *chưa
    # duyệt* (phải dừng), còn không có cột nghĩa là *không dùng cổng này* (đi tiếp).
    if "g3" in d and not (d.get("g3") or "").strip():
        return "await-G3"

    if not (d.get("published") or "").strip():
        return "release"
    return "done"


def compute(campaign: Path) -> list[dict]:
    """Mỗi bài một mục: `{content_id, buoc, can_nguoi, folder}`."""
    campaign = Path(campaign)
    _, than = md_io.read_fm(campaign / "campaign.md")
    _, row = md_io.read_table(than, "CONTENT")
    ra = []
    for d in row:
        b = next_step(campaign, d)
        ra.append({"content_id": d.get("content_id", ""), "step": b,
                   "can_nguoi": b in NEEDS_HUMAN,
                   "folder": (d.get("folder") or "").strip()})
    return ra


def summary(campaign: Path) -> dict:
    """Đếm theo bước, sắp theo thứ tự đường ống."""
    ds = compute(campaign)
    count = {}
    for x in ds:
        count[x["step"]] = count.get(x["step"], 0) + 1
    return {b: count[b] for b in ORDER if b in count}


def as_text(campaign: Path, *, detail: bool = False) -> str:
    """Bản in cho người và cho agent đọc. Ngắn có chủ đích."""
    ds = compute(campaign)
    tt = summary(campaign)
    d = [f"{b:<14} {n}" for b, n in tt.items()]
    if detail:
        d.append("")
        for x in sorted(ds, key=lambda y: (ORDER.index(y["step"]), y["content_id"])):
            d.append(f"{x['content_id']:<10} {x['step']}")
    return "\n".join(d)
