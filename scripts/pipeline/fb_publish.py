#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đăng bài Facebook theo mẫu của kênh blog: POST + ẢNH, rồi COMMENT ĐẦU chứa link.

Vì sao repo này cần bộ đăng riêng thay vì dùng lại engine tin tức: engine đó làm ba mẫu
khác (link post · video native · Reel) và KHÔNG có đường đăng ảnh, còn phần đính comment
thì nó chỉ gắn vào Reel. Mẫu ở đây là mẫu thứ tư và là mẫu của kênh blog:

    thân bài 0 URL  +  một ảnh infographic  →  comment đầu tiên chứa link

Hai ràng buộc đến từ chính Facebook, không phải từ ta:
· Bài HẸN GIỜ thì CHƯA TỒN TẠI để comment. Nên đăng hẹn giờ là HAI PHA: `--publish-at`
  hẹn bài và ghi `fb-state.json`, rồi `--attach-pending` chạy theo lịch gắn comment sau
  khi Facebook đã phát. Thiếu pha hai thì bài hẹn lên sóng mà không có link.
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


# Graph đòi mốc hẹn ở tương lai ít nhất 10 phút. Chừa thêm một phút cho trễ mạng: mốc sát
# hơn thế thì đăng NGAY, vì nó vốn đã gần như đúng giờ.
SAN_HEN_GIO = 11 * 60
# Quá giờ hẹn chừng này mà Facebook vẫn chưa phát thì không còn là "chờ" nữa.
QUA_HAN = 2 * 3600
# Một file trạng thái cho MỖI bài, nằm cạnh comment.txt. Nó là thứ duy nhất chống đăng
# trùng: có file = bài đã lên Facebook hoặc đã hẹn, chạy lại chỉ in lại link.
TRANG_THAI = "fb-state.json"


def dang_anh(cfg: dict, message: str, image_path: str,
             publish_ts: int | None = None) -> tuple[str, str]:
    """Đăng ảnh kèm caption. Trả về (photo_id, post_id). `post_id` rỗng nếu Graph không trả.

    Dùng /{page_id}/photos chứ không phải /feed: /feed chỉ nhận link hoặc chữ, muốn ảnh
    hiện to trên feed thì phải đi đường photos. Nó trả về CẢ photo_id lẫn post_id —
    comment phải gắn vào **post_id**, gắn vào photo_id thì comment nằm ở chỗ khác.

    `publish_ts` có giá trị = HẸN GIỜ: ảnh lên ở trạng thái chưa phát và Facebook tự phát
    đúng mốc. Bài hẹn chưa tồn tại trên feed nên chưa gắn comment được — đó là việc của
    `attach_pending` sau giờ phát.
    """
    data = {"message": message, "access_token": cfg["page_token"]}
    if publish_ts:
        data["published"] = "false"
        data["scheduled_publish_time"] = str(publish_ts)
    else:
        data["published"] = "true"
    with open(image_path, "rb") as f:
        r = requests.post(f"{GRAPH}/{cfg['page_id']}/photos",
                          data=data, files={"source": f}, timeout=180)
    if not r.ok:
        raise SystemExit(f"Đăng ảnh thất bại: {r.status_code} {str(r.json())[:400]}")
    j = r.json()
    return j.get("id", ""), j.get("post_id", "")


def da_len_song(cfg: dict, post_id: str) -> tuple[bool, str]:
    """(đã phát chưa, permalink). Hỏi thẳng Facebook, không suy từ đồng hồ máy mình."""
    r = requests.get(f"{GRAPH}/{post_id}",
                     params={"fields": "is_published,permalink_url",
                             "access_token": cfg["page_token"]}, timeout=60)
    if not r.ok:
        raise SystemExit(f"Không đọc được trạng thái bài {post_id}: "
                         f"{r.status_code} {str(r.json())[:300]}")
    j = r.json()
    return bool(j.get("is_published")), (j.get("permalink_url")
                                         or f"https://www.facebook.com/{post_id}")


def dien_cho_trong(text: str, gia_tri: dict) -> tuple[str, list[str]]:
    """Thay `{{KHOA}}` bằng giá trị. Khoá có giá trị RỖNG thì bỏ nguyên dòng chứa nó.

    Comment mẫu có cả dòng blog lẫn dòng YouTube. Chiến dịch chưa có video mà giữ dòng
    `{{YOUTUBE_URL}}` thì hoặc bị cổng chặn vì còn chỗ trống, hoặc người đọc gặp một dòng
    chết. Bỏ dòng là đúng, nhưng trả về dòng nào đã bỏ để in ra — không bỏ im lặng.
    """
    bo, ra = [], []
    for dong in text.splitlines(keepends=True):
        if any(not v and ("{{" + k + "}}") in dong for k, v in gia_tri.items()):
            bo.append(dong.strip())
            continue
        for k, v in gia_tri.items():
            dong = dong.replace("{{" + k + "}}", v)
        ra.append(dong)
    return "".join(ra), bo


def _ghi_json(path: Path, d: dict) -> None:
    tam = path.with_name(path.name + ".tmp")
    tam.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    os.replace(tam, path)


def _dong_ket_qua(d: dict) -> str:
    """Dòng JSON mà `campaign_step.step_release` đọc. Thiếu `url` là nó coi như hỏng."""
    return json.dumps({"url": d.get("permalink") or f"https://www.facebook.com/{d['post_id']}",
                       "post_id": d["post_id"], "scheduled": bool(d.get("scheduled")),
                       "publish_at": d.get("publish_at", ""),
                       "comment_id": d.get("comment_id", "")}, ensure_ascii=False)


def attach_pending(cfg: dict, goc: Path, *, now: float | None = None,
                   doc_song=None, gui_comment=None) -> list[dict]:
    """Pha hai của đăng hẹn giờ: gắn comment đầu cho bài đã tới giờ phát mà chưa có comment.

    Chạy lại bao nhiêu lần cũng được. Bài đã có `comment_id` thì bỏ qua, bài chưa tới giờ
    thì chờ. PHẢI có một lượt chạy theo lịch gọi hàm này: thiếu nó thì bài hẹn lên sóng mà
    không có đường về blog.

    Không kiểm lại Cổng 2 hay mức tự trị: bài đã NẰM TRÊN Facebook. Chặn comment lúc này
    không rút được bài, chỉ biến nó thành bài mồ côi. Chữ của comment đã chốt từ lúc hẹn và
    lưu trong file trạng thái, nên sửa `comment.txt` sau khi duyệt cũng không lọt ra ngoài.
    """
    now = time.time() if now is None else now
    doc_song = doc_song or (lambda pid: da_len_song(cfg, pid))
    gui_comment = gui_comment or (lambda pid, msg: dang_comment(cfg, pid, msg))
    ra = []
    for f in sorted(Path(goc).rglob(TRANG_THAI)):
        d = json.loads(f.read_text(encoding="utf-8"))
        kq = {"file": str(f), "post_id": d.get("post_id", "")}
        if d.get("comment_id"):
            kq["status"] = "done"
        elif now < float(d.get("publish_ts") or 0):
            kq["status"] = "waiting"
        else:
            tre = now - float(d.get("publish_ts") or 0)
            try:
                song, link = doc_song(d["post_id"])
                if not song:
                    kq["status"] = "overdue" if tre > QUA_HAN else "waiting"
                    kq["reason"] = f"quá giờ hẹn {int(tre // 60)} phút mà Facebook chưa phát"
                else:
                    d["comment_id"] = gui_comment(d["post_id"], d["comment"])
                    d["permalink"] = link
                    _ghi_json(f, d)
                    kq.update(status="attached", comment_id=d["comment_id"], url=link)
            except SystemExit as e:
                # Một bài hỏng không được giữ chân các bài sau: mỗi giờ trễ là thêm người
                # đọc thấy bài không có link.
                kq.update(status="failed", reason=str(e))
        ra.append(kq)
    return ra


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
        return "?", "không biết bài thuộc kênh nào (thiếu --post)"
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
            level = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("autonomy")
            return (level or "?"), str(f)
        except Exception as e:              # noqa: BLE001
            return "?", f"{f} đọc không được: {e}"
    return "?", (f"{d} không nằm trong kênh nào của CHANNELS.md "
                 f"({len(dang_ky)} kênh đã đăng ký)")


def _cong_2(post: Path, message_file: str, comment_file: str) -> tuple[bool, str]:
    """Kiểm bài ĐÃ QUA CỔNG 2 chưa, và `--post` có đúng là chỗ chứa nội dung đang đăng không.

    Hai điều, vì thiếu điều nào cũng đủ để đăng nhầm:

    1. **`--post` phải chứa chính file đang đăng.** Nếu không, trỏ `--post` vào một kênh đang
       `autonomy: full` là mở được cổng cho nội dung của kênh khác — cổng tự trị thành ra
       vô nghĩa vì nó gác một thứ không liên quan tới thứ sắp đăng.
    2. **`posts[]` của kênh facebook phải `review.status == approved`, có `approved_by`,**
       và `quality_check` không `failed`. Cổng tự trị trả lời "kênh này có được đăng tự động
       không"; Cổng 2 trả lời "bài NÀY có được đăng không". Hai câu khác nhau.
    """
    d = Path(post).resolve()
    for f in (message_file, comment_file):
        try:
            Path(f).resolve().relative_to(d)
        except ValueError:
            return False, (f"--post {d} không chứa {f} — cổng phải gác đúng nội dung sắp "
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
    ap.add_argument("--message-file", help="thân bài — KHÔNG được chứa URL")
    ap.add_argument("--image", help="ảnh infographic đính kèm")
    ap.add_argument("--comment-file", help="comment đầu — PHẢI có ít nhất 1 URL")
    ap.add_argument("--dry-run", action="store_true", help="kiểm hết nhưng không gọi Graph")
    ap.add_argument("--post", help="thư mục bài — nguồn của cổng tự trị VÀ cổng 2. Bắt buộc khi đăng thật.")
    ap.add_argument("--station", default=None,
                    help="trạm chứa CHANNELS.md (mặc định: như studio_paths)")
    ap.add_argument("--publish-at", default="",
                    help="mốc hẹn, unix giây. Rỗng hoặc sát hơn 11 phút = đăng ngay")
    ap.add_argument("--fill", action="append", default=[], metavar="KHOA=GIA_TRI",
                    help="thay {{KHOA}} trong thân bài và comment; giá trị rỗng = bỏ dòng đó")
    ap.add_argument("--attach-pending", metavar="THU_MUC",
                    help="PHA HAI: gắn comment cho mọi bài hẹn giờ đã phát trong thư mục này")
    a = ap.parse_args(argv)

    if a.attach_pending:
        ket = attach_pending(_cfg(a.config), Path(a.attach_pending))
        for kq in ket:
            print(json.dumps(kq, ensure_ascii=False))
        hong = [k for k in ket if k["status"] in ("failed", "overdue")]
        for k in hong:
            sys.stderr.write(f"BÀI {k['post_id']} ĐANG KHÔNG CÓ LINK: {k.get('reason')}\n")
        return 1 if hong else 0

    for ten, p in (("--config", a.config), ("--message-file", a.message_file),
                   ("--image", a.image), ("--comment-file", a.comment_file)):
        if not p:
            raise SystemExit(f"thiếu {ten}")
        if not os.path.isfile(p):
            raise SystemExit(f"không thấy file: {p}")

    gia_tri = {}
    for kv in a.fill:
        if "=" not in kv:
            raise SystemExit(f"--fill {kv!r} sai dạng, cần KHOA=GIA_TRI")
        k, v = kv.split("=", 1)
        gia_tri[k.strip()] = v.strip()
    msg, bo_than = dien_cho_trong(_doc(a.message_file), gia_tri)
    cmt, bo_cmt = dien_cho_trong(_doc(a.comment_file), gia_tri)
    for dong in bo_than + bo_cmt:
        print(f"  bỏ dòng  : {dong}  (chỗ trống không có giá trị)")

    hen = None
    if a.publish_at.strip():
        try:
            ts = int(a.publish_at.strip())
        except ValueError:
            raise SystemExit(f"--publish-at {a.publish_at!r} không phải unix giây")
        hen = ts if ts > time.time() + SAN_HEN_GIO else None

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
    print(f"  lịch     : {time.strftime('%Y-%m-%d %H:%M', time.localtime(hen)) if hen else 'đăng ngay'}")

    if a.dry_run:
        print("  [dry-run] mọi cổng đã qua, KHÔNG gọi Graph.")
        return 0

    # --- ĐÃ ĐĂNG RỒI thì không đăng lại ---------------------------------------------
    # Đặt TRƯỚC hai cổng người: bước này không gọi Graph, chỉ in lại link. Nếu để sau, một
    # kênh vừa bị hạ mức tự trị sẽ làm lượt chạy lại báo hỏng cho một bài ĐANG nằm trên
    # Facebook, và đường ống sẽ không bao giờ ghi nhận nó.
    state_file = Path(a.comment_file).resolve().parent / TRANG_THAI
    if state_file.is_file():
        d = json.loads(state_file.read_text(encoding="utf-8"))
        print(f"  đã có    : {state_file} — KHÔNG đăng lại")
        if not d.get("comment_id"):
            print("  [chú ý]  bài chưa có comment; --attach-pending sẽ gắn sau giờ phát")
        print(_dong_ket_qua(d))
        return 0

    # --- CỔNG 2: bài NÀY đã được người duyệt chưa -------------------------------
    if not a.post:
        sys.stderr.write(chr(10).join([
            "",
            "Thiếu --post. Đăng thật bắt buộc có nó, vì hai cổng đều đọc từ thư mục bài:",
            "  · Cổng 2   — publish.json: người đã duyệt chưa, ai duyệt",
            "  · tự trị   — channel.yml: kênh có được đăng tự động không",
            "",
            "Chạy lại với --post <thư mục bài>, hoặc --dry-run để chỉ kiểm.",
            ""]))
        return 4
    ok2, why = _cong_2(Path(a.post), a.message_file, a.comment_file)
    if not ok2:
        sys.stderr.write(chr(10).join([
            "", f"KHÔNG đăng thật — chưa qua Cổng 2: {why}", "",
            "Cổng 2 là dấu vết của NGƯỜI, không phải cái cờ:",
            '  register_publish.py <bài> approve --by "<tên>" --note "<câu duyệt nguyên văn>"',
            ""]))
        return 4
    print(f"  cổng 2   : {why}")

    # --- CỔNG TỰ TRỊ: chỉ `full` mới được đăng thật ------------------------------
    level, source = _muc_tu_tri(a.post, a.station)
    if level != "full":
        sys.stderr.write(chr(10).join([
            "",
            f"KHÔNG đăng thật — mức tự trị của kênh là {level!r}, cần 'full'.",
            f"  đọc từ: {source}",
            "",
            "Mọi cổng nội dung đã qua. Muốn đăng thì chọn một trong hai:",
            "  · người tự đăng bằng tay (mặc định, và là ý của chủ kênh);",
            "  · hoặc sửa `autonomy: full` trong channel.yml — do NGƯỜI sửa, không phải agent.",
            "",
            "Chạy lại với --dry-run để chỉ kiểm mà không đăng.",
            ""]))
        return 4

    photo_id, post_id = dang_anh(cfg, msg, a.image, hen)
    if not post_id:
        if hen:
            # Không có post_id thì pha hai không biết gắn comment vào đâu. Ảnh đã hẹn trên
            # Facebook rồi, nên phải nói to kèm photo_id để người vào xử lý tay.
            raise SystemExit(f"Facebook đã nhận ảnh hẹn giờ (photo_id={photo_id}) nhưng KHÔNG "
                             f"trả post_id — không gắn comment tự động được. Vào Meta Business "
                             f"Suite xử lý tay trước giờ phát.")
        post_id = photo_id
    print(f"  FB_PHOTO_ID={photo_id}")
    print(f"  FB_POST_ID={post_id}")

    # Ghi trạng thái NGAY sau khi Facebook nhận bài, TRƯỚC comment. Comment mà hỏng thì
    # lượt chạy lại vẫn thấy file này và không đăng trùng; pha hai gắn comment sau.
    d = {"post_id": post_id, "photo_id": photo_id, "scheduled": bool(hen),
         "publish_ts": hen or int(time.time()),
         "publish_at": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                     time.localtime(hen or time.time())),
         "comment": cmt, "comment_id": "", "permalink": ""}
    _ghi_json(state_file, d)

    if hen:
        print(f"  FB_SCHEDULED={d['publish_at']} — comment gắn sau giờ phát bằng --attach-pending")
    else:
        # Comment NGAY. Càng để lâu càng nhiều người thấy bài chưa có đường về.
        time.sleep(2)
        d["comment_id"] = dang_comment(cfg, post_id, cmt)
        d["permalink"] = f"https://www.facebook.com/{post_id}"
        _ghi_json(state_file, d)
        print(f"  FB_COMMENT_ID={d['comment_id']}")
        print(f"  FB_PERMALINK={d['permalink']}")
    print(_dong_ket_qua(d))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
