# -*- coding: utf-8 -*-
"""Sổ sự kiện của chiến dịch — CHỈ NỐI THÊM, không bao giờ ghi đè.

## Vì sao tách khỏi trạng thái

Trạng thái và lịch sử là hai thứ đối nghịch, nhốt chung một file là hỏng cả hai:

| | Trạng thái | Lịch sử |
|---|---|---|
| Bản chất | ghi đè, luôn nhỏ | chỉ nối thêm, lớn mãi |
| Đọc khi nào | mỗi lần dò | chỉ khi cần truy *vì sao* |

Đo ngày 11/09/2026 với 90 bài × ~14 sự kiện: gộp vào một YAML thì muốn biết *"bài nào đang
ở đâu"* phải nạp **36.787 token** vì lịch sử nằm xen giữa; tách ra thì chỉ **2.137**. Gộp
lại là đắt gấp 17 lần cho đúng câu hỏi hay hỏi nhất.

Nên: **trạng thái** sống ở bảng Content trong `campaign.md` (nguồn sự thật, đã có sẵn), còn
file này giữ **chuyện đã xảy ra**.

## Vì sao JSONL chứ không YAML

1. **Chỉ nối thêm nên không có cuộc đua.** Mở chế độ append, ghi một dòng, xong. Không đọc,
   không sửa, không ghi đè. Poller và thợ ghi cùng lúc cũng không đạp nhau — khác hẳn
   read-modify-write vốn đã làm MẤT CÚ BẤM của người ngày 10/09/2026.
2. **Đọc được phần ĐUÔI.** Muốn biết một bài gần đây ra sao thì đọc ngược vài chục dòng
   cuối. YAML lồng không có khái niệm "đuôi": phải parse cả file mới lấy được phần tử cuối.
3. **Hỏng một dòng không mất cả sổ.** Một dòng JSON lỗi thì bỏ đúng dòng đó. Một file YAML
   sai cú pháp là mất sạch.

## Sổ này KHÔNG phải nguồn sự thật

Nó ghi lại chuyện đã xảy ra, nó **không quyết định** điều gì. Xoá nó đi thì mất khả năng
truy vì sao, nhưng không bài nào đổi trạng thái. Đừng bao giờ đọc sổ này để quyết một bài
có được đăng hay không — cái đó hỏi bảng Content và `publish.json`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

LOG_NAME = "events.jsonl"

# Đọc đuôi: nhảy về cuối file rồi lùi dần, thay vì nạp cả file. Sổ chạy cả năm vẫn không
# làm chậm lượt dò. 64 KB đủ chứa vài trăm dòng — quá đủ cho câu hỏi "gần đây thế nào".
TAIL_BYTES = 64 * 1024


def log_path(campaign: Path) -> Path:
    return Path(campaign) / "logs" / LOG_NAME


def write(campaign: Path, job: str, *, post: str | None = None, by: str = "",
        at: datetime | None = None, **detail) -> None:
    """Nối MỘT dòng vào sổ. Không bao giờ đọc file trước khi ghi.

    `viec` là danh từ ngắn, ổn định, dùng để lọc: `g1_approved`, `g2_rejected`, `feedback`,
    `soan_xong`, `soan_hong`. Đặt tên theo VIỆC ĐÃ XẢY RA, không theo ý định.

    Ghi sổ hỏng **KHÔNG được làm hỏng việc chính**. Sổ là thứ để đọc lại sau; đánh đổ cả
    lượt duyệt vì không ghi được một dòng nhật ký là sai thứ tự ưu tiên.
    """
    d = {"at": (at or datetime.now().astimezone()).isoformat(), "job": job}
    if post:
        d["post"] = post
    if by:
        d["by"] = by
    d.update(detail)
    p = log_path(campaign)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        # "a" + một lệnh write cho MỘT dòng: hệ điều hành nối vào cuối, không cần khoá.
        with p.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    except OSError as e:
        # In ra stderr chứ không ném: xem docstring.
        import sys
        sys.stderr.write(f"event_log: không ghi được sổ ({e}) — việc chính vẫn tiếp tục.\n")


def read(campaign: Path, *, post: str | None = None, n: int = 20) -> list[dict]:
    """`n` sự kiện GẦN NHẤT, cũ trước mới sau. `bai` để lọc đúng một bài.

    Chỉ đọc phần đuôi file (`TAIL_BYTES`), nên sổ to bao nhiêu cũng không đổi chi phí.

    Dòng hỏng bị BỎ QUA LẶNG LẼ ở đây là có chủ đích: hàm này phục vụ việc *đọc lại cho
    hiểu*, và một dòng rách không đáng làm hỏng cả lượt đọc. Chỗ cần chặt chẽ là lúc GHI.
    """
    p = log_path(campaign)
    if not p.is_file():
        return []
    with p.open("rb") as f:
        f.seek(0, os.SEEK_END)
        kt = f.tell()
        f.seek(max(0, kt - TAIL_BYTES))
        tho = f.read().decode("utf-8", errors="replace")
    row = tho.splitlines()
    if kt > TAIL_BYTES and row:
        row = row[1:]                    # dòng đầu gần như chắc chắn bị cắt giữa chừng
    ra = []
    for d in row:
        d = d.strip()
        if not d:
            continue
        try:
            o = json.loads(d)
        except json.JSONDecodeError:
            continue
        if post and o.get("post") != post:
            continue
        ra.append(o)
    return ra[-n:]
