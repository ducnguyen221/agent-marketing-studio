# -*- coding: utf-8 -*-
"""Bài đã có chữ THẬT chưa — luật dùng CHUNG cho cả bước soạn lẫn cổng duyệt.

## Vì sao luật này phải ở `lib/`, không ở một trong hai bên

Nó từng nằm trong `campaign_step._da_viet`. `campaign_step` **import** `approve_bus`, nên
`approve_bus` không import ngược lại được — và thế là cổng G2 không có cách nào hỏi "bài
này viết chưa". Ngày 11/09/2026 cổng G2 gửi đi một tin mời duyệt 5 bài, 3 bài còn nguyên
khuôn mẫu.

Chép luật sang bên kia thì có hai bản, và hai bản sẽ trôi khỏi nhau đúng lúc không ai nhìn.
Đặt ở `lib/` là chỗ **cả hai bên đều với tới được mà không tạo vòng import**.
"""
from __future__ import annotations

import re
from pathlib import Path

# Thân bài blog ngắn hơn ngần này thì coi như chưa viết. Con số không thiêng; nó chỉ cần
# lớn hơn phần chữ CÒN LẠI của khuôn sau khi lọc, và nhỏ hơn một bài thật ngắn nhất.
MIN_BLOG_WORDS = 800


def has_content(post: Path) -> bool:
    """`content.md` đã có chữ THẬT chưa, hay còn là khung mẫu?

    ĐÃ TRẢ GIÁ 10/09/2026 — cổng này từng FAIL-OPEN. Bản đầu đếm ký tự (ngưỡng 400) và coi
    KHUÔN MẪU là "đã viết": khuôn tự nó dài **3.701 ký tự** sau khi lọc, gấp 9 lần ngưỡng.
    Bước `soan` báo 3 bài SẴN SÀNG ĐĂNG trong khi chưa có một chữ nào, và còn gửi tin xin
    duyệt đăng chúng.

    **Đếm ký tự là đo SAI ĐẠI LƯỢNG** — nó đo "có nhiều chữ không", trong khi câu hỏi là
    "đã ai viết chưa". Khuôn mẫu có rất nhiều chữ, toàn chữ của khuôn.

    Dấu hiệu đúng, cả ba phải thoả:
      1. có neo `## post:blog_article` — thiếu là chưa dựng đúng khuôn
      2. thân dưới neo đó không còn `{{...}}` — khuôn đầy chỗ trống, bài xong thì hết
      3. thân đủ dài (`MIN_BLOG_WORDS`) — chặn trường hợp xoá sạch chỗ trống rồi bỏ đó

    Thư mục bài chưa tồn tại cũng là **chưa viết** — fail-closed, không đoán.
    """
    p = Path(post) / "content.md"
    if not p.is_file():
        return False
    raw = p.read_text(encoding="utf-8")

    m = re.search(r"(?m)^##\s+post:blog_article\s*$", raw)
    if not m:
        return False
    than = raw[m.end():]
    # cắt ở neo kênh kế tiếp
    ke = re.search(r"(?m)^##\s+post:", than)
    if ke:
        than = than[:ke.start()]

    if "{{" in than:
        return False                       # còn chỗ trống của khuôn
    than = re.sub(r"<!--.*?-->", "", than, flags=re.S)
    than = re.sub(r"(?m)^\s*>.*$", "", than)      # khối chỉ dẫn của khuôn
    than = re.sub(r"(?m)^\s*#{1,6}\s.*$", "", than)
    return len(than.strip()) >= MIN_BLOG_WORDS
