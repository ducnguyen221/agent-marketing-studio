#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đăng bài Facebook theo mẫu của kênh blog: POST + ẢNH, rồi COMMENT ĐẦU chứa link.

Vì sao repo này cần bộ đăng riêng thay vì dùng lại engine tin tức: engine đó làm ba mẫu
khác (link post · video native · Reel) và KHÔNG có đường đăng ảnh, còn phần đính comment
thì nó chỉ gắn vào Reel. Mẫu ở đây là mẫu thứ tư và là mẫu của kênh blog:

    thân bài 0 URL  +  một ảnh infographic  →  comment đầu tiên chứa link

Hai ràng buộc đến từ chính Facebook, không phải từ ta:
· Bài HẸN GIỜ thì CHƯA TỒN TẠI để comment. Muốn có comment thì phải đăng NGAY, hoặc
  phải có một lượt chạy thứ hai sau giờ publish. Script này chỉ làm nhánh đăng ngay.
· Comment cần scope `pages_manage_engagement`. Thiếu là Graph trả lỗi — và script này
  DỪNG LỚN TIẾNG chứ không nuốt, vì một bài không link trong thân mà cũng không link ở
  comment là bài mồ côi: người đọc không có đường nào về bài viết.

FAIL-CLOSED có chủ đích: kiểm mọi thứ kiểm được TRƯỚC khi gọi Graph. Sau khi ảnh đã lên
Facebook thì không rút lại được nữa.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"
_URL = re.compile(r"https?://\S+", re.I)


def _doc(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def _cfg(path: str) -> dict:
    c = json.load(open(path, encoding="utf-8"))
    for k in ("page_id", "page_token"):
        if not c.get(k):
            raise SystemExit(f"config thiếu khoá {k}: {path}")
    return c


def dang_anh(cfg: dict, message: str, image_path: str) -> tuple[str, str]:
    """Đăng ảnh kèm caption. Trả về (photo_id, post_id).

    Dùng /{page_id}/photos chứ không phải /feed: /feed chỉ nhận link hoặc chữ, muốn ảnh
    hiện to trên feed thì phải đi đường photos. Nó trả về CẢ photo_id lẫn post_id —
    comment phải gắn vào **post_id**, gắn vào photo_id thì comment nằm ở chỗ khác.
    """
    with open(image_path, "rb") as f:
        r = requests.post(f"{GRAPH}/{cfg['page_id']}/photos",
                          data={"message": message, "published": "true",
                                "access_token": cfg["page_token"]},
                          files={"source": f}, timeout=180)
    if not r.ok:
        raise SystemExit(f"Đăng ảnh thất bại: {r.status_code} {str(r.json())[:400]}")
    j = r.json()
    return j.get("id", ""), j.get("post_id", "") or j.get("id", "")


def dang_comment(cfg: dict, object_id: str, message: str) -> str:
    r = requests.post(f"{GRAPH}/{object_id}/comments",
                      data={"message": message, "access_token": cfg["page_token"]},
                      timeout=60)
    if not r.ok:
        raise SystemExit(
            f"BÀI ĐÃ LÊN ({object_id}) NHƯNG COMMENT THẤT BẠI: {r.status_code} "
            f"{str(r.json())[:300]}\n"
            f"Bài đang không có link ở đâu cả. Vào Facebook dán comment bằng tay NGAY.")
    return r.json().get("id", "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Đăng post + ảnh, rồi comment đầu chứa link.")
    ap.add_argument("--config", required=True, help="facebook_config.json (page_id + page_token)")
    ap.add_argument("--message-file", required=True, help="thân bài — KHÔNG được chứa URL")
    ap.add_argument("--image", required=True, help="ảnh infographic đính kèm")
    ap.add_argument("--comment-file", required=True, help="comment đầu — PHẢI có ít nhất 1 URL")
    ap.add_argument("--dry-run", action="store_true", help="kiểm hết nhưng không gọi Graph")
    a = ap.parse_args(argv)

    for p in (a.config, a.message_file, a.image, a.comment_file):
        if not os.path.isfile(p):
            raise SystemExit(f"không thấy file: {p}")

    msg, cmt = _doc(a.message_file), _doc(a.comment_file)

    # --- cổng TRƯỚC khi gọi Graph -------------------------------------------------
    trong_than = _URL.findall(msg)
    if trong_than:
        raise SystemExit(f"Thân bài có {len(trong_than)} URL: {trong_than[:3]} — luật hiện "
                         f"hành là 0. Link đi vào comment đầu.")
    if not _URL.findall(cmt):
        raise SystemExit("Comment không có URL nào — đăng lên sẽ thành bài mồ côi.")
    if "{{" in msg or "{{" in cmt:
        raise SystemExit("Còn placeholder {{...}} chưa thay bằng link thật.")
    if os.path.getsize(a.image) > 8 * 1024 * 1024:
        raise SystemExit("Ảnh > 8 MB, Facebook hay từ chối. Nén lại trước.")

    cfg = _cfg(a.config)
    print(f"  thân bài : {len(msg)} ký tự, 0 URL")
    print(f"  ảnh      : {os.path.basename(a.image)} ({os.path.getsize(a.image) / 1024:.0f} KB)")
    print(f"  comment  : {len(_URL.findall(cmt))} URL")

    if a.dry_run:
        print("  [dry-run] mọi cổng đã qua, KHÔNG gọi Graph.")
        return 0

    photo_id, post_id = dang_anh(cfg, msg, a.image)
    print(f"  FB_PHOTO_ID={photo_id}")
    print(f"  FB_POST_ID={post_id}")

    # Comment NGAY. Càng để lâu càng nhiều người thấy bài chưa có đường về.
    time.sleep(2)
    cmt_id = dang_comment(cfg, post_id, cmt)
    print(f"  FB_COMMENT_ID={cmt_id}")
    print(f"  FB_PERMALINK=https://www.facebook.com/{post_id}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
