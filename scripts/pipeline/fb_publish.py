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
from pathlib import Path
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


def _muc_tu_tri(duong_bai: str | None, station: str | None = None) -> tuple[str, str]:
    """Đọc `autonomy` từ `channel.yml` của kênh chứa bài. Trả (mức, nguồn).

    Tài liệu và trang công khai đều hứa: *"script từ chối chạy thật trừ khi kênh đặt
    `autonomy: full`"*. Trước bản vá này KHÔNG script nào đọc `autonomy` — lời hứa an toàn
    đó chỉ là luật cho agent đọc, không phải cổng máy. Một lời bảo đảm mà không có gì thi
    hành thì tệ hơn không hứa: người ta dựa vào nó.

    Không tìm được kênh → trả `("?", …)`, và người gọi coi đó là CHƯA CHO PHÉP.
    """
    if not duong_bai:
        return "?", "không biết bài thuộc kênh nào (thiếu --bai)"
    d = Path(duong_bai).resolve()

    # Kênh phải CÓ TRONG SỔ. Trước bản vá này hàm lấy `channel.yml` đầu tiên gặp khi đi ngược
    # cây — nghĩa là một file `channel.yml` với `autonomy: full` đặt lạc vào thư mục bài là
    # mở được cổng. Cổng này tồn tại để chặn agent, nên nó không được tin một file mà agent
    # tạo ra được: sổ kênh mới là thứ người giữ.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
        import studio_paths as SP
        dang_ky = [c["dir"].resolve() for c in SP.channels(station) if c.get("dir")]
    except Exception as e:                  # noqa: BLE001
        return "?", f"không đọc được CHANNELS.md: {e}"
    if not dang_ky:
        return "?", "CHANNELS.md rỗng hoặc không có — chưa kênh nào được đăng ký"

    for cha in [d] + list(d.parents):
        if cha not in dang_ky:
            continue
        f = cha / "channel.yml"
        if not f.is_file():
            return "?", f"{cha} có trong CHANNELS.md nhưng thiếu channel.yml"
        try:
            import yaml
            muc = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("autonomy")
            return (muc or "?"), str(f)
        except Exception as e:              # noqa: BLE001
            return "?", f"{f} đọc không được: {e}"
    return "?", (f"{d} không nằm trong kênh nào của CHANNELS.md "
                 f"({len(dang_ky)} kênh đã đăng ký)")


def _cong_2(bai: Path, message_file: str, comment_file: str) -> tuple[bool, str]:
    """Kiểm bài ĐÃ QUA CỔNG 2 chưa, và `--bai` có đúng là chỗ chứa nội dung đang đăng không.

    Hai điều, vì thiếu điều nào cũng đủ để đăng nhầm:

    1. **`--bai` phải chứa chính file đang đăng.** Nếu không, trỏ `--bai` vào một kênh đang
       `autonomy: full` là mở được cổng cho nội dung của kênh khác — cổng tự trị thành ra
       vô nghĩa vì nó gác một thứ không liên quan tới thứ sắp đăng.
    2. **`posts[]` của kênh facebook phải `review.status == approved`, có `approved_by`,**
       và `quality_check` không `failed`. Cổng tự trị trả lời "kênh này có được đăng tự động
       không"; Cổng 2 trả lời "bài NÀY có được đăng không". Hai câu khác nhau.
    """
    d = Path(bai).resolve()
    for f in (message_file, comment_file):
        try:
            Path(f).resolve().relative_to(d)
        except ValueError:
            return False, (f"--bai {d} không chứa {f} — cổng phải gác đúng nội dung sắp "
                           f"đăng, không phải một thư mục bất kỳ")

    pj_p = d / "publish.json"
    if not pj_p.is_file():
        return False, f"không có {pj_p} — chưa qua Cổng 2 (chạy register_publish init/approve)"
    try:
        pj = json.loads(pj_p.read_text(encoding="utf-8"))
    except Exception as e:            # noqa: BLE001
        return False, f"{pj_p} đọc không được: {e}"

    fb = [p for p in pj.get("posts", []) if p.get("channel") == "facebook"]
    if not fb:
        return False, "publish.json không có post nào kênh facebook"
    for p in fb:
        rv = p.get("review") or {}
        if rv.get("status") != "approved":
            return False, (f"{p.get('post_id')}: review.status={rv.get('status')!r}, "
                           f"cần 'approved' — Cổng 2 là của NGƯỜI")
        if not (rv.get("approved_by") or "").strip():
            return False, f"{p.get('post_id')}: duyệt mà không ghi approved_by"
        if p.get("quality_check") == "failed" and "[override-qa:" not in (rv.get("note") or ""):
            # Cổng kỹ thuật đỏ vẫn đăng được, nhưng CHỈ qua đường miễn trừ có ghi lý do:
            # `approve --override-qa "…"` chép lý do vào review.note. Chặn cứng ở đây sẽ
            # khiến người ta sửa gates.json cho xanh — tệ hơn nhiều so với một lý do được ghi.
            return False, (f"{p.get('post_id')}: quality_check=failed và không có miễn trừ. "
                           f"Muốn đăng vẫn được: approve --override-qa \"<lý do>\"")
    ai = (fb[0].get("review") or {}).get("approved_by")
    return True, f"Cổng 2 OK — {len(fb)} post facebook, duyệt bởi {ai}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Đăng post + ảnh, rồi comment đầu chứa link.")
    ap.add_argument("--config", required=True, help="facebook_config.json (page_id + page_token)")
    ap.add_argument("--message-file", required=True, help="thân bài — KHÔNG được chứa URL")
    ap.add_argument("--image", required=True, help="ảnh infographic đính kèm")
    ap.add_argument("--comment-file", required=True, help="comment đầu — PHẢI có ít nhất 1 URL")
    ap.add_argument("--dry-run", action="store_true", help="kiểm hết nhưng không gọi Graph")
    ap.add_argument("--bai", help="thư mục bài — nguồn của cổng tự trị VÀ cổng 2. Bắt buộc khi đăng thật.")
    ap.add_argument("--station", default=None,
                    help="trạm chứa CHANNELS.md (mặc định: như studio_paths)")
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

    # --- CỔNG 2: bài NÀY đã được người duyệt chưa -------------------------------
    if not a.bai:
        sys.stderr.write(chr(10).join([
            "",
            "Thiếu --bai. Đăng thật bắt buộc có nó, vì hai cổng đều đọc từ thư mục bài:",
            "  · Cổng 2   — publish.json: người đã duyệt chưa, ai duyệt",
            "  · tự trị   — channel.yml: kênh có được đăng tự động không",
            "",
            "Chạy lại với --bai <thư mục bài>, hoặc --dry-run để chỉ kiểm.",
            ""]))
        return 4
    ok2, vi_sao = _cong_2(Path(a.bai), a.message_file, a.comment_file)
    if not ok2:
        sys.stderr.write(chr(10).join([
            "", f"KHÔNG đăng thật — chưa qua Cổng 2: {vi_sao}", "",
            "Cổng 2 là dấu vết của NGƯỜI, không phải cái cờ:",
            '  register_publish.py <bài> approve --by "<tên>" --note "<câu duyệt nguyên văn>"',
            ""]))
        return 4
    print(f"  cổng 2   : {vi_sao}")

    # --- CỔNG TỰ TRỊ: chỉ `full` mới được đăng thật ------------------------------
    muc, nguon = _muc_tu_tri(a.bai, a.station)
    if muc != "full":
        sys.stderr.write(chr(10).join([
            "",
            f"KHÔNG đăng thật — mức tự trị của kênh là {muc!r}, cần 'full'.",
            f"  đọc từ: {nguon}",
            "",
            "Mọi cổng nội dung đã qua. Muốn đăng thì chọn một trong hai:",
            "  · người tự đăng bằng tay (mặc định, và là ý của chủ kênh);",
            "  · hoặc sửa `autonomy: full` trong channel.yml — do NGƯỜI sửa, không phải agent.",
            "",
            "Chạy lại với --dry-run để chỉ kiểm mà không đăng.",
            ""]))
        return 4

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
