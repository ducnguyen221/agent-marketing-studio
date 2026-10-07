# -*- coding: utf-8 -*-
"""post_facebook.py — đăng bài lên Facebook PAGE qua Graph API (hẹn giờ 9h sáng).

Chạy bằng PYTHON HỆ THỐNG (có `requests`). Best-effort: lỗi KHÔNG làm hỏng run.
Chỉ đăng lên PAGE (Graph API không cho đăng trang cá nhân / nhóm).

Thiết lập 1 lần (xem knowledge/toolchains/PLATFORM_SETUP.md mục Facebook):
  FB_CONFIG=<duong/toi/facebook_config.json> python post_facebook.py --exchange <short_user_token> --app-id <id> --app-secret <secret>
  FB_CONFIG=<duong/toi/facebook_config.json> python post_facebook.py --verify

Đăng (hẹn 9h sáng kế tiếp): thẻ link trỏ TRANG NEWS; link YouTube nằm trong thân bài.
  python post_facebook.py --tool <dir> --message-file fb.txt \
      --link "https://<site>/news/ai/hot-today/?utm_source=facebook&..." \
      --video-url https://youtu.be/<id> \
      --reel <short.mp4> --reel-desc-file fbshort.txt --when-9am

In dòng cuối: FB_POST_ID=<id|-> FB_REEL_ID=<id|-> STATUS=<scheduled@iso|published|error:...>
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"
# Khối link trang tin chèn vào bài/caption (chỉ khi KHÔNG `--no-link`). Là CẤU HÌNH của kênh,
# không phải hằng số: `--site-link "🤖 Nhãn|https://..."` (lặp được). Rỗng = chỉ chèn link video.
SITE_LINKS: list = []


def _site_block():
    return [f"{nhan}: {url}" for nhan, url in SITE_LINKS]


def _parse_site_link(v):
    nhan, _, url = str(v).partition("|")
    nhan, url = nhan.strip(), url.strip()
    if not (nhan and url.startswith(("http://", "https://"))):
        raise argparse.ArgumentTypeError(f"--site-link phải là 'Nhãn|https://...', nhận {v!r}")
    return nhan, url


def compose(message, video_url, no_link=False):
    """Chèn khối link (video + trang tin của kênh) NGAY DƯỚI dòng tiêu đề (dòng đầu của bài AI viết),
    đúng bố cục bài mẫu. Bài AI KHÔNG tự viết link → script lo link đúng chuẩn.

    `no_link=True` (chiến lược v2, 18/08/2026): trả nguyên văn, KHÔNG chèn link nào.
    Facebook dìm phân phối bài dẫn ra ngoài; từ nay video được host native trên chính
    Facebook nên không còn lý do gì để đính link. Xem chú thích ở `post_video()`.
    """
    if not message or no_link:
        return message
    parts = message.split("\n", 1)
    title = parts[0].strip()
    body = parts[1].lstrip("\n") if len(parts) > 1 else ""
    hdr = []
    if video_url:
        hdr.append(f"▶️ Xem video: {video_url}")
    hdr.extend(_site_block())
    return title + "\n" + "\n".join(hdr) + ("\n\n" + body if body else "")


# Mồi mở đầu cho Reel. Chọn theo HASH của nội dung (không random) để cùng một bài
# luôn ra cùng một caption — chạy lại/resume không đổi kết quả, và vẫn đa dạng giữa các bài.
REEL_OPENERS = (
    "Chuyện này lạ nè 👇",
    "Nghe qua tưởng nhỏ, mà không nhỏ đâu 👇",
    "30 giây thôi, xem xong hiểu ngay 👇",
    "Cái này mình thấy đáng để ý 👇",
    "Tin hôm nay có một chi tiết ít ai nhắc 👇",
    "Mình tóm gọn lại cho nhanh 👇",
    "Đọc tiêu đề dễ hiểu nhầm — thực ra là thế này 👇",
    "Có một con số làm mình dừng lại 👇",
)


def with_links(caption, video_url, no_link=False):
    """Chèn khối link vào caption Reel DO AI VIẾT (đường `--reel-desc-file`).

    Prompt yêu cầu AI không tự chèn link (để link do script quản một chỗ, đổi domain
    không phải sửa 5 prompt). Nếu ở đây không chèn thì caption AI ra KHÔNG có đường dẫn
    nào — lỗi này lộ ra khi dry-run, không phải suy đoán.
    Đặt khối link TRƯỚC dòng hashtag để hashtag vẫn nằm cuối như quy ước Facebook.
    """
    if not caption or no_link:              # v2: Reel native cũng không đính link
        return caption
    if any(url in caption for _, url in SITE_LINKS):   # AI đã tự chèn -> tôn trọng, không nhân đôi
        return caption
    lines = caption.rstrip().split("\n")
    tags = ""
    if lines and (lines[-1].strip().startswith("#") or lines[-1].count("#") >= 3):
        tags = lines.pop().strip()
        while lines and not lines[-1].strip():
            lines.pop()
    block = []
    if video_url:
        block.append(f"▶️ Bản đầy đủ: {video_url}")
    block.extend(_site_block())
    out = lines + [""] + block
    if tags:
        out += ["", tags]
    return "\n".join(out)


def _hook_from_body(message):
    """Lấy câu ĐÁNG CHÚ Ý NHẤT trong thân bài để làm hook — KHÔNG lấy dòng tiêu đề.

    Ưu tiên câu có CON SỐ (số liệu thường là thứ giữ chân người xem), nếu không có
    thì lấy câu đủ dài đầu tiên. Bỏ qua dòng link, hashtag, và mục "Góc nhìn".
    """
    body = message.split("\n", 1)[1] if "\n" in message else ""
    cands = []
    for para in body.split("\n"):
        s = para.strip()
        if not s or s.startswith(("#", "▶", "🤖", "📊", "💭")):
            continue
        for snt in re.split(r"(?<=[.!?…])\s", s):
            snt = snt.strip()
            if 40 <= len(snt) <= 200:
                cands.append(snt)
    if not cands:
        return ""
    with_num = [s for s in cands if re.search(r"\d", s)]
    return (with_num or cands)[0]


def compose_reel(message, video_url, no_link=False):
    """Caption RIÊNG cho Reel — ĐƯỜNG LÙI khi AI không cấp sẵn `facebook_reel`.

    VÌ SAO VIẾT LẠI (17/08/2026): bản cũ mở đầu bằng ĐÚNG dòng tiêu đề của bài dài.
    Bài dài và Reel lại đăng cùng một phút, nên trên Page hiện hai mục có dòng đầu
    y hệt nhau — người lướt thấy trùng, thuật toán cũng đọc ra là trùng. Đã kiểm
    chứng qua Graph API: story trên feed CHÍNH LÀ Reel (attachment target = reel_id),
    không phải bài thứ ba, nên không thể tắt nó — chỉ có thể làm nó KHÁC ĐI.

    Bản mới: mồi mở đầu riêng + hook lấy từ THÂN bài (ưu tiên câu có số liệu),
    tuyệt đối không lặp dòng tiêu đề.
    """
    if not message:
        return message
    lines = message.split("\n")
    title = lines[0].strip()
    tags = ""
    for s in (l.strip() for l in reversed(lines)):
        if s:
            if s.startswith("#") or s.count("#") >= 3:
                tags = s
            break

    hook = _hook_from_body(message)
    opener = REEL_OPENERS[sum(map(ord, title)) % len(REEL_OPENERS)]

    out = [opener, ""]
    if hook and hook != title:
        out.append(hook)
    elif title:
        out.append(title)          # cùng lắm mới rơi về tiêu đề, và lúc đó nó KHÔNG ở dòng đầu
    if not no_link:
        out.append("")
        if video_url:
            out.append(f"▶️ Bản đầy đủ: {video_url}")
        out.extend(_site_block())
    if tags:
        out += ["", tags]
    return "\n".join(out)


def _cfg_path(args):
    return (os.environ.get("FB_CONFIG")
            or os.path.join(args.tool or os.path.dirname(os.path.abspath(__file__)),
                            "facebook_config.json"))


def _cfg(args):
    p = _cfg_path(args)
    if not os.path.isfile(p):
        sys.exit(f"Thiếu facebook_config.json: {p}\n  Chạy --exchange trước (xem knowledge/toolchains/PLATFORM_SETUP.md).")
    with open(p, encoding="utf-8") as f:
        c = json.load(f)
    if not c.get("page_id") or not c.get("page_token"):
        sys.exit(f"Config thiếu page_id/page_token: {p}")
    return c


def next_at(hhmm, now=None):
    """(unix_ts, iso) của mốc HH:MM kế tiếp — HÔM NAY nếu còn ≥ now+11 phút (Graph yêu cầu
    lịch ở tương lai), ngược lại HÔM SAU. hhmm = 'HH:MM' (vd '20:00')."""
    now = now or datetime.datetime.now()
    try:
        hh, mm = (int(x) for x in str(hhmm).split(":"))
    except Exception:
        hh, mm = 9, 0
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now + datetime.timedelta(minutes=11):
        target = target + datetime.timedelta(days=1)
    return int(target.timestamp()), target.isoformat(timespec="minutes")


def next_9am(now=None):
    """Tương thích ngược: mốc 09:00 kế tiếp."""
    return next_at("09:00", now)


def shift_when(when, minutes, now=None):
    """Mốc hẹn cho Reel = mốc bài dài + `minutes` phút. Trả (unix|None, iso).

    Giãn giờ để bài dài và Reel không hiện cùng một phút trên Page — trước đây cả hai
    dùng CHUNG một `scheduled_publish_time` nên trông như đăng đúp.
    `when=None` (đăng ngay) mà có offset thì tính từ BÂY GIỜ. Graph đòi lịch phải ở
    tương lai nên kẹp sàn now+11 phút, nếu không Reel sẽ bị từ chối.
    """
    if not minutes:
        return when, (datetime.datetime.fromtimestamp(when).isoformat(timespec="minutes")
                      if when else "now")
    now = now or datetime.datetime.now()
    base = datetime.datetime.fromtimestamp(when) if when else now
    t = base + datetime.timedelta(minutes=minutes)
    floor = now + datetime.timedelta(minutes=11)
    if t < floor:
        t = floor
    return int(t.timestamp()), t.isoformat(timespec="minutes")


def _read(path):
    if not path or not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8-sig") as f:
        return f.read().strip()


def verify(args):
    c = _cfg(args)
    r = requests.get(f"{GRAPH}/{c['page_id']}", params={"fields": "name,fan_count",
                     "access_token": c["page_token"]}, timeout=30)
    r.raise_for_status()
    d = r.json()
    print(f"FB_PAGE_OK name={d.get('name')!r} id={c['page_id']} fans={d.get('fan_count','?')}")
    return 0


def post_link(c, message, link, when):
    body = {"message": message, "access_token": c["page_token"]}
    if link:
        body["link"] = link
    if when:
        body["published"] = "false"
        body["scheduled_publish_time"] = str(when)
    r = requests.post(f"{GRAPH}/{c['page_id']}/feed", data=body, timeout=60)
    r.raise_for_status()
    return r.json().get("id", "")


def _handle_group_error(r, group_id):
    """Bắt và diễn giải mã lỗi chi tiết khi Page đăng bài vào Group."""
    try:
        err = r.json().get("error", {})
        code = err.get("code")
        subcode = err.get("error_subcode")
        msg = err.get("message", r.text[:200])
    except Exception:
        code, subcode, msg = None, None, r.text[:200]

    huong_dan = []
    if code in (200, 190):
        huong_dan.append(f"Page chưa tham gia Group ({group_id}) hoặc chưa được cấp quyền đăng bài.")
        huong_dan.append("Vào Cài đặt nhóm trên Facebook -> Thêm Page vào nhóm hoặc mời Page làm Quản trị viên/Thành viên.")
    elif code == 10:
        huong_dan.append(f"App chưa được thêm vào Group ({group_id}).")
        huong_dan.append("Vào Cài đặt nhóm -> Ứng dụng (Apps) -> Thêm App liên kết với Page.")
    else:
        huong_dan.append(f"Lỗi Graph API ({code}/{subcode}): {msg}")

    raise RuntimeError("Đăng bài vào Group thất bại: " + " | ".join(huong_dan))


def post_to_group(c, group_id, message, link=None):
    """Đăng bài (chữ hoặc link) lên Facebook GROUP dưới tư cách PAGE bằng page_token."""
    body = {"message": message, "access_token": c["page_token"]}
    if link:
        body["link"] = link
    r = requests.post(f"{GRAPH}/{group_id}/feed", data=body, timeout=60)
    if not r.ok:
        _handle_group_error(r, group_id)
    r.raise_for_status()
    return r.json().get("id", "")


def post_group_photo(c, group_id, image_path, caption=""):
    """Đăng ẢNH lên Facebook GROUP dưới tư cách PAGE bằng page_token."""
    data = {"message": caption or "", "access_token": c["page_token"]}
    with open(image_path, "rb") as f:
        r = requests.post(f"{GRAPH}/{group_id}/photos", data=data,
                          files={"source": f}, timeout=180)
    if not r.ok:
        _handle_group_error(r, group_id)
    r.raise_for_status()
    j = r.json()
    return j.get("id", ""), j.get("post_id", "") or j.get("id", "")


def post_video(c, video_path, description, when, title=""):
    """Upload VIDEO DÀI trực tiếp lên Page (native), resumable theo chunk.

    CHIẾN LƯỢC v2 (18/08/2026): bỏ hẳn bài text + thẻ link YouTube. Facebook dìm mạnh
    bài dẫn ra ngoài, mà Page này đang chết đói reach (1–11 view/bài). Nay video được
    HOST TRÊN CHÍNH FACEBOOK, phần chữ đi trong `description` của video — nên mỗi chủ
    đề chỉ còn 2 object native: video dài + Reel. Không còn link nào.

    Đã thăm dò trước khi viết: `/{page}/videos` mở được phiên resumable với đúng bộ quyền
    hiện có (`pages_manage_posts`), chunk 1 MB, và huỷ sạch được. Page trước nay chưa từng
    có video dài — định dạng này hoàn toàn chưa khai thác.

    Trả về video_id. Lỗi -> raise (caller xử lý best-effort).
    """
    pid, tok = c["page_id"], c["page_token"]
    size = os.path.getsize(video_path)

    s = requests.post(f"{GRAPH}/{pid}/videos",
                      data={"upload_phase": "start", "file_size": str(size),
                            "access_token": tok}, timeout=60)
    s.raise_for_status()
    sj = s.json()
    vid, sess = sj["video_id"], sj["upload_session_id"]
    start, end = int(sj["start_offset"]), int(sj["end_offset"])

    try:
        with open(video_path, "rb") as f:
            while start < end:
                f.seek(start)
                chunk = f.read(end - start)
                t = requests.post(f"{GRAPH}/{pid}/videos",
                                  data={"upload_phase": "transfer", "upload_session_id": sess,
                                        "start_offset": str(start), "access_token": tok},
                                  files={"video_file_chunk": chunk}, timeout=600)
                t.raise_for_status()
                tj = t.json()
                start, end = int(tj["start_offset"]), int(tj["end_offset"])
    except Exception:
        # Phiên dở dang mà bỏ mặc thì treo lại trên Page. Huỷ rồi mới ném lỗi lên.
        try:
            requests.post(f"{GRAPH}/{pid}/videos",
                          data={"upload_phase": "cancel", "upload_session_id": sess,
                                "access_token": tok}, timeout=60)
        except Exception:
            pass
        raise

    fin = {"upload_phase": "finish", "upload_session_id": sess,
           "description": description or "", "access_token": tok}
    if title:
        fin["title"] = title
    if when:
        fin["published"] = "false"
        fin["scheduled_publish_time"] = str(when)
    fr = requests.post(f"{GRAPH}/{pid}/videos", data=fin, timeout=180)
    fr.raise_for_status()
    return vid


def extract_cover(video_path, at, out_path):
    """Trích 1 frame tại giây `at` (lúc TIÊU ĐỀ đã hiện) làm ảnh bìa Reel.
    Mặc định 2.0s — sau khi headline fade-in xong, trước khi đổi sang section."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(at), "-i", video_path,
             "-frames:v", "1", "-q:v", "2", out_path],
            check=True, capture_output=True, timeout=120)
        return out_path if os.path.isfile(out_path) else ""
    except Exception:
        return ""


def set_video_cover(c, video_id, image_path, tries=6, wait=15):
    """Đặt ảnh bìa (preferred thumbnail) cho Reel/video qua /{id}/thumbnails.
    Reel mới upload có thể đang xử lý → thử lại vài lần. Lỗi → raise (best-effort ở caller)."""
    tok = c["page_token"]
    last = ""
    for i in range(tries):
        try:
            with open(image_path, "rb") as fh:
                r = requests.post(f"{GRAPH}/{video_id}/thumbnails",
                                  data={"is_preferred": "true", "access_token": tok},
                                  files={"source": fh}, timeout=120)
            r.raise_for_status()
            return True
        except Exception as e:
            last = _err(e)
            if i < tries - 1:
                time.sleep(wait)
    raise RuntimeError(last or "cover failed")


def post_reel(c, video_path, desc, when, cover_at=2.0, cover_path=""):
    """Reels resumable upload: start -> upload bytes -> finish (SCHEDULED).
    Sau finish: đặt ảnh bìa = frame lúc tiêu đề hiện (giây cover_at) hoặc ảnh cover_path.
    Trả về (video_id, cover_ok) — cover_ok = True/False/None (None = không đặt bìa)."""
    pid, tok = c["page_id"], c["page_token"]
    size = os.path.getsize(video_path)
    s = requests.post(f"{GRAPH}/{pid}/video_reels",
                      data={"upload_phase": "start", "access_token": tok}, timeout=60)
    s.raise_for_status()
    sj = s.json()
    vid, up_url = sj["video_id"], sj["upload_url"]
    with open(video_path, "rb") as f:
        u = requests.post(up_url, headers={"Authorization": f"OAuth {tok}",
                          "offset": "0", "file_size": str(size)}, data=f.read(), timeout=600)
    u.raise_for_status()
    fin = {"upload_phase": "finish", "video_id": vid, "access_token": tok,
           "description": desc or ""}
    if when:
        fin["video_state"] = "SCHEDULED"
        fin["scheduled_publish_time"] = str(when)
    else:
        fin["video_state"] = "PUBLISHED"
    fr = requests.post(f"{GRAPH}/{pid}/video_reels", data=fin, timeout=120)
    fr.raise_for_status()

    # --- Ảnh bìa: frame lúc tiêu đề hiện (best-effort, không làm hỏng việc đăng Reel) ---
    cover_ok = None
    tmp = ""
    img = cover_path
    if not img and cover_at and float(cover_at) > 0:
        tmp = img = extract_cover(video_path, cover_at, video_path + ".cover.jpg")
    if img and os.path.isfile(img):
        try:
            set_video_cover(c, vid, img)
            cover_ok = True
        except Exception:
            cover_ok = False
    elif cover_at and float(cover_at) > 0:
        cover_ok = False  # muốn đặt bìa nhưng trích frame thất bại
    if tmp:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return vid, cover_ok


def post_comment(c, object_id, message):
    """Bình luận DƯỚI TÊN PAGE vào một post/video đã publish.

    ⚠️ CHƯA DÙNG ĐƯỢC với token hiện tại (18/08/2026). Cần scope `pages_manage_engagement`
    — token đang có: pages_show_list · business_management · pages_read_engagement ·
    pages_read_user_content · pages_manage_posts. Thiếu đúng một cái.

    Công dụng dự kiến: đặt link (YouTube / trang của kênh) ở COMMENT ĐẦU thay vì trong bài,
    để giữ reach mà vẫn có đường dẫn về. Facebook dìm bài có link ngoài, nhưng link trong
    comment thì không bị tính vào bài.

    ⚠️ RÀNG BUỘC THỨ HAI, đừng quên: bài đang HẸN GIỜ thì CHƯA TỒN TẠI để comment. Muốn
    chạy được phải hoặc (a) đăng ngay thay vì hẹn, hoặc (b) có job chạy SAU thời điểm
    publish để đi gắn comment. Hiện luồng đang hẹn giờ nên phải theo (b).

    Trả về comment_id. Thiếu quyền -> Graph trả lỗi và hàm raise (đừng nuốt lỗi:
    comment hỏng mà im lặng thì lại đúng kiểu bug đã mất 2 tháng).
    """
    r = requests.post(f"{GRAPH}/{object_id}/comments",
                      data={"message": message, "access_token": c["page_token"]}, timeout=60)
    r.raise_for_status()
    return r.json().get("id", "")


def _ask_secret(label, current):
    """Hỏi bí mật qua stdin ẩn thay vì nhận từ dòng lệnh.

    Vì sao: tham số gõ trên terminal nằm lại trong LỊCH SỬ SHELL (PSReadLine lưu ra file
    `ConsoleHost_history.txt`, bash lưu `.bash_history`) và cả trong danh sách tiến trình.
    App secret + user token lộ ở đó là lộ thật. Nhập qua getpass thì không đi vào đâu cả.
    """
    if current:
        return current
    import getpass
    val = getpass.getpass(f"  {label} (gõ/dán, màn hình sẽ KHÔNG hiện): ").strip()
    if not val:
        sys.exit(f"Thiếu {label}.")
    return val


def exchange(args):
    """Đổi short-lived user token -> long-lived -> lấy Page token, ghi config."""
    # Cho phép bỏ trống trên dòng lệnh rồi nhập ẩn — an toàn hơn hẳn.
    args.app_id = _ask_secret("App ID", args.app_id)
    args.app_secret = _ask_secret("App Secret", args.app_secret)
    if args.exchange == "-":
        args.exchange = _ask_secret("Short-lived user token", "")
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": args.app_id,
        "client_secret": args.app_secret, "fb_exchange_token": args.exchange}, timeout=30)
    r.raise_for_status()
    long_user = r.json()["access_token"]
    a = requests.get(f"{GRAPH}/me/accounts", params={"access_token": long_user}, timeout=30)
    a.raise_for_status()
    pages = a.json().get("data", [])
    if not pages:
        sys.exit("Không thấy Page nào — tài khoản có quản trị Page chưa? Cấp đủ quyền chưa?")
    if args.page_id:
        pages = [p for p in pages if p["id"] == args.page_id] or pages
    if len(pages) > 1 and not args.page_id:
        print("Nhiều Page — chọn bằng --page-id <id>:")
        for p in pages:
            print(f"  {p['id']}  {p.get('name')}")
        sys.exit("Chạy lại với --page-id.")
    pg = pages[0]
    out = _cfg_path(args)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"page_id": pg["id"], "page_name": pg.get("name"),
                   "page_token": pg["access_token"]}, f, ensure_ascii=False, indent=2)
    print(f"FB_CONFIG_SAVED page={pg.get('name')!r} id={pg['id']} -> {out}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--message-file", default="")
    ap.add_argument("--link", default="", help="đích THẺ LINK dưới bài (nên là trang tin của kênh để Pixel đo được)")
    ap.add_argument("--site-link", action="append", default=[], type=_parse_site_link,
                    metavar="NHÃN|URL", help="link trang tin chèn vào bài khi không --no-link (lặp được)")
    ap.add_argument("--video-url", default="", help="link YouTube in trong THÂN bài; bỏ trống = dùng --link (như cũ)")
    # ── Chiến lược v2 (18/08/2026): video native, không link ──────────────────
    ap.add_argument("--video", default="",
                    help="VIDEO DÀI upload NATIVE lên Page (thay cho bài text + thẻ link YouTube)")
    ap.add_argument("--video-title", default="", help="tiêu đề video native trên Facebook")
    ap.add_argument("--no-link", action="store_true",
                    help="KHÔNG chèn link nào vào bài/caption (ưu tiên reach — FB dìm bài dẫn ra ngoài)")
    ap.add_argument("--reel", default="")
    ap.add_argument("--reel-desc-file", default="")
    ap.add_argument("--reel-cover-at", type=float, default=2.0,
                    help="giây trích frame làm ảnh bìa Reel (lúc tiêu đề hiện); 0 = tắt")
    ap.add_argument("--reel-cover", default="", help="ảnh bìa Reel chỉ định sẵn (ghi đè --reel-cover-at)")
    ap.add_argument("--reel-offset-min", type=int, default=0,
                    help="đăng Reel SAU bài dài bao nhiêu phút (vd 60) — tránh 2 mục cùng một phút")
    # ── v3 (18/08/2026): Reel là object DUY NHẤT trên Facebook ────────────────
    ap.add_argument("--reel-main", action="store_true",
                    help="Reel là bài chính: dùng TOÀN VĂN --message-file làm description của Reel")
    ap.add_argument("--no-text-post", action="store_true",
                    help="KHÔNG đăng bài chữ riêng lên /feed — chỉ còn Reel + caption.")
    ap.add_argument("--comment-file", default="",
                    help="đăng comment ngay dưới Reel sau khi publish (nơi đặt link, giữ reach cho bài)")
    ap.add_argument("--set-cover", default="",
                    help="CHẾ ĐỘ RIÊNG: đặt bìa cho 1 video_id có sẵn (dùng --reel-cover hoặc --reel + --reel-cover-at)")
    ap.add_argument("--when-9am", action="store_true", help="hẹn 9h sáng kế tiếp")
    ap.add_argument("--at", default="", help="hẹn HH:MM (hôm nay, hoặc hôm sau nếu đã qua) — vd 20:00")
    ap.add_argument("--when", default="", help="unix timestamp (ghi đè --at / --when-9am)")
    # setup
    ap.add_argument("--exchange", default="")
    ap.add_argument("--app-id", default="")
    ap.add_argument("--app-secret", default="")
    ap.add_argument("--page-id", default="")
    ap.add_argument("--group-id", default="", help="ID của Facebook Group để đăng bài dưới tư cách Page")
    ap.add_argument("--share-to-group", default="", help="ID của Facebook Group để chia sẻ bài viết từ Page vào Group (Cách 1)")
    ap.add_argument("--share-message-file", default="", help="file chứa teaser caption khi chia sẻ bài viết vào Group")
    ap.add_argument("--share-caption", default="", help="chuỗi teaser caption trực tiếp khi chia sẻ bài viết vào Group")
    ap.add_argument("--image", default="", help="đường dẫn file ảnh (PNG/JPG) để đăng bài kèm ảnh lên Page hoặc Group")
    args = ap.parse_args()

    if args.exchange:
        return exchange(args)
    if args.verify:
        return verify(args)
    if args.set_cover:
        c = _cfg(args)
        img = args.reel_cover
        tmp = ""
        if not img and args.reel and os.path.isfile(args.reel):
            tmp = img = extract_cover(args.reel, args.reel_cover_at, args.reel + ".cover.jpg")
        if not img or not os.path.isfile(img):
            print(f"COVER_SET video_id={args.set_cover} STATUS=error: thiếu ảnh bìa (--reel-cover hoặc --reel)")
            return 0
        try:
            set_video_cover(c, args.set_cover, img)
            print(f"COVER_SET video_id={args.set_cover} STATUS=ok")
        except Exception as e:
            print(f"COVER_SET video_id={args.set_cover} STATUS=error: {_err(e)}")
        finally:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        return 0

    when, when_iso = None, "now"
    if args.when:
        when, when_iso = int(args.when), datetime.datetime.fromtimestamp(int(args.when)).isoformat(timespec="minutes")
    elif args.at:
        when, when_iso = next_at(args.at)
    elif args.when_9am:
        when, when_iso = next_9am()

    SITE_LINKS[:] = list(args.site_link)
    raw = _read(args.message_file)
    # TÁCH ĐÔI có chủ đích (17/08/2026):
    #   --link      = đích của THẺ LINK (card) Facebook hiện dưới bài  -> trang tin của kênh
    #   --video-url = link YouTube in trong THÂN bài ("▶️ Xem video")  -> youtu.be/...
    # Trước đây hai thứ này dùng chung một giá trị nên thẻ luôn trỏ YouTube; người bấm rời
    # sang YouTube và Meta Pixel (chỉ chạy trên trang của kênh) không đo được gì. Không truyền
    # --video-url thì rơi về --link đúng như hành vi cũ (tương thích ngược).
    vid_url = args.video_url or args.link
    message = compose(raw, vid_url, args.no_link)   # v2 no_link -> giữ nguyên văn, không chèn gì
    # Reel: ưu tiên caption AI viết riêng (facebook_reel) -> script tự gắn khối link vào;
    # không có thì dựng caption dự phòng (compose_reel đã tự gắn link sẵn).
    ai_reel = _read(args.reel_desc_file)
    if args.reel_main:
        # v3: Reel là object DUY NHẤT trên Facebook -> nó mang TOÀN VĂN bài blog.
        # Video dài đã bỏ khỏi Facebook vì Meta gộp mọi video của Page thành Reel
        # (không có opt-out), làm video ngang 16:9 lọt vào thư viện Reel và hỏng bố cục.
        reel_desc = message
    elif ai_reel:
        reel_desc = with_links(ai_reel, vid_url, args.no_link)
    else:
        reel_desc = compose_reel(raw, vid_url, args.no_link)

    reel_when, reel_when_iso = shift_when(when, args.reel_offset_min)
    share_msg = _read(args.share_message_file) if args.share_message_file else (args.share_caption or "")
    if not share_msg and args.share_to_group:
        hk = _hook_from_body(message)
        if hk and hk != message:
            share_msg = f"{hk}\n\nXem chi tiết bài viết bên dưới 👇"

    if args.dry_run:
        print("=== DRY-RUN ===")
        if args.group_id:
            print(f"đích đăng  : Facebook GROUP ({args.group_id}) dưới tư cách PAGE")
            print(f"ảnh đính kèm: {args.image or '(không có)'}")
            print(f"card link  : {args.link or '(không có)'}")
            print(f"--- message bài GROUP ({len(message)} ký tự) ---\n{message}")
            return 0
        print(f"bài dài hẹn: {when_iso} (unix={when})")
        print(f"Reel hẹn   : {reel_when_iso} (lệch {args.reel_offset_min} phút)")
        che_do = ("v3 — REEL LÀ BÀI CHÍNH, không link" if args.reel_main
                  else ("v2 — video dài native, không link" if args.no_link
                        else "v1 — bài text + thẻ link"))
        print(f"chế độ     : {che_do}")
        if not args.reel_main:                 # v3 cố ý KHÔNG đăng video dài lên Facebook
            print(f"video dài  : {args.video or '(không có → sẽ đăng bài text)'}")
            print(f"card link  : {args.link or '(không có)'}")
            print(f"video url  : {vid_url or '(không có)'}")
        print(f"reel: {args.reel} (desc {len(reel_desc)} ký tự)")
        print(f"--- message bài dài ({len(message)} ký tự) ---\n{message}")
        print(f"--- caption REEL ({len(reel_desc)} ký tự) ---\n{reel_desc}")
        if args.share_to_group:
            print(f"share_to_group: {args.share_to_group}")
            if share_msg:
                print(f"--- caption SHARE GROUP ({len(share_msg)} ký tự) ---\n{share_msg}")
        # Comment cũng ra công khai -> phải xem trước được, đừng để nó là thứ duy nhất
        # chỉ thấy sau khi đã đăng.
        cmt_preview = _read(args.comment_file)
        if cmt_preview:
            khi = "BỎ QUA (bài đang hẹn giờ)" if when else "ngay sau khi Reel publish"
            print(f"--- COMMENT ({len(cmt_preview)} ký tự, {khi}) ---\n{cmt_preview}")
        else:
            print("--- COMMENT: (không có --comment-file)")
        return 0

    c = _cfg(args)
    post_id, reel_id, cover_ok, errs = "-", "-", None, []
    if args.group_id:
        # ── ĐĂNG VÀO FACEBOOK GROUP DƯỚI TƯ CÁCH PAGE ─────────────────────────
        if when:
            errs.append("group:Hẹn giờ đăng không được hỗ trợ qua Facebook Group API")
        if args.reel:
            errs.append("group:Đăng Reel không được hỗ trợ cho Facebook Group qua script này")
        if not errs:
            try:
                if args.image:
                    if not os.path.isfile(args.image):
                        raise FileNotFoundError(f"File ảnh không tồn tại: {args.image}")
                    photo_id, pid = post_group_photo(c, args.group_id, args.image, message)
                    post_id = pid or photo_id or "-"
                else:
                    post_id = post_to_group(c, args.group_id, message, args.link) or "-"
            except Exception as e:
                errs.append(f"group:{_err(e)}")
    elif args.no_text_post:
        # v3 ĐÚNG NGHĨA (05/09/2026): Reel là object DUY NHẤT.
        #
        # Từ 18/08 ba runner và chiến lược Facebook v2 đã tuyên bố "bài text riêng đã
        # bị bỏ", nhưng main() CHƯA BAO GIỜ bỏ post_link() — `--reel-main` chỉ đổi
        # caption của Reel chứ không tắt nhánh đăng. Kết quả: mỗi lượt chạy đẻ HAI
        # object trùng nguyên văn (đo 6 ngày liên tiếp 31/08–05/09, message khớp từng
        # ký tự: 5603=5603, 5127=5127, 3171=3171, 4010=4010, 3987=3987).
        # Reel còn tự sinh thêm một story `added_video` trên feed, nên người xem thấy
        # hai mục giống hệt nhau. Bài chữ thuần thì Facebook bóp: reel views=71 mà
        # post react=0 cmt=0 clicks=0 (03/09).
        #
        # Không xoá post_link(): nó vẫn là đường lùi. Tắt bằng CỜ để bật lại chỉ tốn
        # một giá trị trong brand.json ("fb_text_post": true).
        pass
    elif args.video and os.path.isfile(args.video):
        # v2 — VIDEO NATIVE: phần chữ đi trong description của chính video, không có
        # bài text riêng và không có thẻ link. Đây là object "bài dài" trên Facebook.
        try:
            post_id = post_video(c, args.video, message, when, args.video_title) or "-"
        except Exception as e:
            errs.append(f"video:{_err(e)}")
    else:
        # v1 — đường cũ: bài text + thẻ link. Giữ lại để còn lùi được và cho luồng nào
        # chưa có video dài. KHÔNG xoá: archive là bản sao, đây mới là đường chạy thật.
        try:
            post_id = post_link(c, message, args.link, when) or "-"
        except Exception as e:
            errs.append(f"feed:{_err(e)}")
    if not args.group_id and args.reel and os.path.isfile(args.reel):
        try:
            reel_id, cover_ok = post_reel(c, args.reel, reel_desc, reel_when,
                                          args.reel_cover_at, args.reel_cover)
            reel_id = reel_id or "-"
        except Exception as e:
            errs.append(f"reel:{_err(e)}")
    status = (f"scheduled@{when_iso}" if when else "published") if not errs else ("error:" + " | ".join(errs))
    cover_str = {True: "ok", False: "failed"}.get(cover_ok, "-")
    # ── Comment mang LINK, đăng ngay dưới Reel (hoặc bài Group) ───────────────
    cmt_id, cmt_txt = "-", _read(args.comment_file)
    if cmt_txt and args.group_id and post_id not in ("", "-"):
        try:
            cmt_id = post_comment(c, post_id, cmt_txt) or "-"
        except Exception as e:
            errs.append(f"comment:{_err(e)}")
    elif cmt_txt and reel_id not in ("", "-"):
        if when:
            errs.append("comment:bo qua (bai dang hen gio, chua ton tai de comment)")
        else:
            for attempt in range(6):          # Reel vừa upload còn đang xử lý -> thử lại
                try:
                    cmt_id = post_comment(c, reel_id, cmt_txt) or "-"
                    break
                except Exception as e:
                    if attempt == 5:
                        errs.append(f"comment:{_err(e)}")
                    else:
                        time.sleep(20)

    mode = ("group-photo" if (args.group_id and args.image)
            else ("group-post" if args.group_id
                  else ("reel-main" if args.reel_main
                        else ("native-video" if (args.video and os.path.isfile(args.video)) else "text-link"))))
    target = f"group:{args.group_id}" if args.group_id else f"page:{c.get('page_id')}"
    print(f"FB_POST_ID={post_id} FB_TARGET={target} FB_REEL_ID={reel_id} FB_REEL_COVER={cover_str} "
          f"FB_REEL_AT={reel_when_iso} FB_MODE={mode} FB_COMMENT_ID={cmt_id} STATUS={status}")
    if args.share_to_group and post_id not in ("", "-") and not args.group_id:
        page_post_url = f"https://www.facebook.com/{post_id}"
        web_share_url = f"https://www.facebook.com/sharer/sharer.php?u={page_post_url}"
        try:
            share_id = post_to_group(c, args.share_to_group, message=share_msg, link=page_post_url)
            print(f"FB_GROUP_SHARE_ID={share_id}")
            if share_msg:
                print(f"FB_GROUP_SHARE_CAPTION={share_msg}")
        except Exception as e:
            print(f"FB_GROUP_SHARE=manual_share_needed REASON={_err(e)}")
            print(f"FB_GROUP_SHARE_URL={web_share_url}")
            if share_msg:
                print(f"FB_GROUP_SHARE_CAPTION={share_msg}")
    return 0  # best-effort


def _err(e):
    if isinstance(e, requests.HTTPError) and e.response is not None:
        try:
            return str(e.response.json().get("error", {}).get("message", e))[:160]
        except Exception:
            return str(e)[:160]
    return f"{type(e).__name__}: {e}"[:160]


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
