# -*- coding: utf-8 -*-
"""Hàng chờ việc — THƯ MỤC là trạng thái, `rename` là phép giành lượt.

## Vì sao cần hàng chờ

Poller đang giữ khoá đọc Telegram. Cho nó tự chạy agent viết bài (~10 phút) thì **cổng
duyệt điếc suốt 10 phút đó**: nhịp tim đứng lại, lượt sau tưởng nó chết rồi cướp khoá, và
ta quay lại đúng vòng lặp đã làm sập máy ngày 11/09/2026.

Nên poller chỉ **ghi một dòng việc** rồi đi tiếp, xong trong vài mili giây.

## Vì sao THƯ MỤC chứ không phải một file danh sách

```
logs/jobs/pending/      việc đang chờ
logs/jobs/running/ đã có thợ nhận
logs/jobs/done/     xong
logs/jobs/failed/     hỏng quá số lần cho phép
```

Giành lượt = `os.rename(cho/x → running/x)`. **`rename` trong cùng ổ đĩa là nguyên tử**:
hai thợ cùng giành thì đúng một con thắng, con thua nhận `FileNotFoundError`. Không cần
khoá, không cần đọc-sửa-ghi, nên không có cuộc đua nào để mà thua.

Một file danh sách thì ngược lại: mỗi lần nhận việc phải đọc cả file, sửa, ghi lại — đúng
hình dạng read-modify-write đã làm **MẤT CÚ BẤM của người** ngày 10/09/2026.

Thêm một lợi ích không nhỏ: mở File Explorer ra là **thấy hàng chờ bằng mắt**.

## Việc hỏng thì sao

Việc mang theo `attempts`. Thợ làm hỏng thì việc quay lại `pending/` với số lần +1; quá
`MAX_ATTEMPTS` thì sang `failed/` và **dừng hẳn** — không quay tít. Mỗi vòng viết lại đốt ~10
phút agent, nên vòng lặp vô hạn ở đây là đốt tiền thật.

## Thợ chết giữa chừng

Việc nằm lại `running/`. Quá `STALE_SECONDS` mà không ai đụng tới thì coi như mồ côi và
được trả về `pending/`. Không có tiến trình nào phải trông giữ điều đó — `nhat()` tự dọn.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

MAX_ATTEMPTS = 3                       # làm hỏng quá ngần này lần thì thôi, đừng quay tít
STALE_SECONDS = 30 * 60             # việc nằm `running` lâu hơn ngần này = thợ đã chết

BOXES = ("pending", "running", "done", "failed")


def _root(campaign: Path) -> Path:
    return Path(campaign) / "logs" / "jobs"


def _box(campaign: Path, name: str) -> Path:
    p = _root(campaign) / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def add(campaign: Path, job: str, *, post: str | None = None, **detail) -> str:
    """Xếp một việc vào cuối hàng. Trả mã việc.

    Tên file bắt đầu bằng thời gian nên **thứ tự chữ cái chính là thứ tự thời gian** —
    không cần đọc nội dung file để biết việc nào tới trước.
    """
    # Mốc tới MICRO GIÂY, không phải giây. Duyệt cả lô 5 bài thì 5 việc sinh ra trong
    # cùng một giây; mốc chỉ tới giây thì thứ tự rơi về chuỗi hex ngẫu nhiên và MẤT FIFO.
    # Test `vao_truoc_ra_truoc` bắt được đúng lỗi này 12/09/2026.
    job_id = f"{datetime.now().astimezone():%Y%m%dT%H%M%S%f}-{secrets.token_hex(4)}"
    d = {"job_id": job_id, "job": job, "post": post, "attempts": 0,
         "created_at": datetime.now().astimezone().isoformat(), **detail}
    (_box(campaign, "pending") / f"{job_id}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return job_id


def _reclaim_orphans(campaign: Path, *, now: float | None = None) -> int:
    """Việc nằm `running` quá lâu = thợ đã chết. Trả về `pending` để làm lại."""
    now = now if now is not None else time.time()
    n = 0
    for p in _box(campaign, "running").glob("*.json"):
        try:
            if now - p.stat().st_mtime <= STALE_SECONDS:
                continue
            os.replace(p, _box(campaign, "pending") / p.name)
            n += 1
        except OSError:
            continue                  # con khác vừa đụng vào; không phải lỗi của ta
    return n


def claim(campaign: Path, *, now: float | None = None) -> dict | None:
    """Giành MỘT việc cũ nhất. `None` nếu hàng rỗng.

    Giành bằng `os.replace` — nguyên tử. Hai thợ cùng nhắm một việc thì đúng một con thắng;
    con thua thấy `OSError` và **đi thử việc kế tiếp**, không phải lỗi.
    """
    _reclaim_orphans(campaign, now=now)
    for p in sorted(_box(campaign, "pending").glob("*.json")):
        dest = _box(campaign, "running") / p.name
        try:
            os.replace(p, dest)
        except OSError:
            continue
        try:
            return json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            os.replace(dest, _box(campaign, "failed") / p.name)   # việc rách, đừng chặn hàng
            continue
    return None


def done(campaign: Path, job_id: str, **result) -> None:
    _move(campaign, job_id, "done", result)


def failed(campaign: Path, job_id: str, reason: str, *, permanent: bool = False) -> str:
    """Thợ làm hỏng. Còn lượt thì trả về hàng chờ; hết lượt thì sang `failed/`.

    `permanent=True` bỏ qua hẳn phần đếm lượt: có những cái hỏng mà thử lại là vô nghĩa —
    bài không có trong bảng Content, chưa dựng bước đó. Thử lại một lỗi vĩnh viễn ba lần
    chỉ tổ làm nhiễu sổ và trì hoãn lúc người biết mà sửa.

    Trả về ô đích để chỗ gọi biết mà báo người: `"cho"` là sẽ thử lại, `"hong"` là bỏ cuộc.
    """
    p = _box(campaign, "running") / f"{job_id}.json"
    if not p.is_file():
        return "failed"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        os.replace(p, _box(campaign, "failed") / p.name)
        return "failed"
    d["attempts"] = int(d.get("attempts") or 0) + 1
    d["error"] = reason
    d["failed_at"] = datetime.now().astimezone().isoformat()
    dest = "pending" if (not permanent and d["attempts"] < MAX_ATTEMPTS) else "failed"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    os.replace(p, _box(campaign, dest) / p.name)
    return dest


def _move(campaign: Path, job_id: str, dest_box: str, extra: dict) -> None:
    p = _box(campaign, "running") / f"{job_id}.json"
    if not p.is_file():
        return
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        d = {"job_id": job_id}
    d.update(extra)
    d["finished_at"] = datetime.now().astimezone().isoformat()
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    os.replace(p, _box(campaign, dest_box) / p.name)


def count(campaign: Path) -> dict:
    """Số việc trong từng ô — để báo trạng thái mà không phải mở từng file."""
    return {box: len(list(_box(campaign, box).glob("*.json"))) for box in BOXES}
