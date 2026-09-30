# -*- coding: utf-8 -*-
"""check_fb_reach.py — hậu kiểm ĐỘ PHỦ của bài Facebook đã đăng.

VÌ SAO CÓ FILE NÀY (đọc trước khi sửa):
Từ 20/06 đến 17/08/2026, 61 bài của 4 luồng tin được đăng "thành công" mà KHÔNG AI
NGOÀI THẤY — app Meta còn ở Development mode. Graph API vẫn trả `is_published=true`,
`privacy=EVERYONE`, nên `post_facebook.py` in `STATUS=scheduled@...` xanh mượt suốt 2
tháng. Không một tín hiệu nào báo động. Bài học: **"API nhận bài" KHÔNG PHẢI bằng chứng
bài tới được người xem.** Bằng chứng duy nhất là có người thật xem/tương tác.

Script này đọc lại các bài ĐÃ publish và kêu to khi chúng chết lặng.

GIỚI HẠN TRUNG THỰC — số liệu ở đây là PROXY, không phải reach thật:
Token ĐÃ có scope `read_insights` từ 19/08/2026, nhưng **reach vẫn không đọc được** —
`post_impressions*`, `page_impressions*`, `page_fans` đều trả `(#100) invalid insights
metric` vì **Meta khai tử chúng ở Graph v21**. Đây là giới hạn của API, KHÔNG phải
thiếu quyền — đừng đi xin thêm quyền nữa, vô ích.

Cái đo được thật:
  - Reel  : `post_views` (số lượt phát) qua /{page}/video_reels
  - Feed  : reactions / comments / shares qua summary
  - Insights còn sống: `post_clicks`, `post_video_views` (post) ·
    `page_video_views`, `page_follows`, `page_post_engagements`, `page_views_total` (page)

Script vẫn thử insights trước và tự dùng nếu có. Không im lặng đánh tráo proxy thành reach.

VÁ 30/08/2026 — CHÍNH SCRIPT NÀY ĐÃ BÁO ĐỘNG SAI, tốn một vòng chẩn đoán:
Nó thấy `react=0 cmt=0 share=0` rồi in "Bài lên được nhưng Facebook chưa đẩy tới ai. Kiểm
tra: app còn Live không, quyền có tụt về Standard Access không". Kiểm lại bằng Graph API +
mở bài bằng trình duyệt CHƯA đăng nhập: bài hiển thị công khai bình thường
(`privacy=EVERYONE`, `is_hidden=false`, Page `is_published=true`), và bài "chết lặng" đó
thật ra có `post_clicks=2`. **Có người xem, chỉ là không ai bấm thích.**

Bốn lỗi đã sửa — đọc trước khi đụng lại:
  1. `is_silent()` chỉ nhìn react/cmt/share, KHÔNG nhìn `post_clicks` ⇒ click bị coi như
     không tồn tại. Nay bài chỉ "chết lặng" khi tương tác = 0 VÀ click = 0.
  2. `try_insights()` chạy trên ĐÚNG MỘT bài rồi `break` ⇒ các bài còn lại vĩnh viễn không
     có số click để mà xét. Nay lấy theo TỪNG bài.
  3. Câu cảnh báo quy thẳng nguyên nhân cho app/quyền. Đó là MỘT giả thuyết, không phải kết
     luận — và lần này nó sai. Nay chỉ nói "ít người xem"; chỉ khi CẢ post LẪN reel đều câm
     mới gợi ý đi kiểm quyền (đó mới là chữ ký của "vô hình" thật, như sự cố 20/06-17/08).
  4. In "token thiếu scope read_insights" trong khi token CÓ scope từ 19/08 — mâu thuẫn với
     chính docstring ở trên. Nguyên nhân thật là Meta khai tử metric. Nay nói đúng.

BÀI HỌC: cổng hậu kiểm mà chẩn đoán sai còn tệ hơn không có cổng — nó khiến người ta đi sửa
thứ không hỏng. Cổng chỉ được phép nói CÁI NÓ ĐO ĐƯỢC, không được suy ra nguyên nhân.

DÙNG:
  python check_fb_reach.py --tool <brandDir> [--hours 48] [--min-age-hours 6]
                           [--min-views 25] [--label "Daily AI"]

IN RA (notify-run.ps1 bắt khối giữa 2 mốc và đẩy vào Telegram):
  FB_REACH_BEGIN
  ...báo cáo người đọc được...
  FB_REACH_END
  FB_REACH_STATUS=ok|low|nodata|error n=<tổng> low=<số bài chết lặng>

Exit LUÔN 0 — hậu kiểm hỏng thì không được phép làm hỏng pipeline. Nhưng nó phải nói
ra là mình hỏng (STATUS=error), chứ không lặng lẽ trả ok.
"""
import argparse
import datetime as dt
import json
import os
import sys

import requests

GRAPH = "https://graph.facebook.com/v21.0"
TZ = dt.timezone(dt.timedelta(hours=7))          # giờ VN, để in cho người đọc


def cfg_path(tool):
    return (os.environ.get("FB_CONFIG")
            or os.path.join(tool or os.path.dirname(os.path.abspath(__file__)),
                            "facebook_config.json"))


def load_cfg(tool):
    p = cfg_path(tool)
    if not os.path.isfile(p):
        return None, f"không có facebook_config.json ({p})"
    try:
        with open(p, encoding="utf-8-sig") as f:
            c = json.load(f)
    except Exception as e:
        return None, f"đọc config lỗi: {type(e).__name__}"
    if not c.get("page_id") or not c.get("page_token"):
        return None, "config thiếu page_id/page_token"
    return c, ""


def get(c, path, **params):
    params["access_token"] = c["page_token"]
    try:
        r = requests.get(f"{GRAPH}/{path}", params=params, timeout=40)
        return r.json()
    except Exception as e:
        return {"error": {"message": f"{type(e).__name__}: {e}"}}


def parse_time(s):
    """'2026-08-17T02:00:17+0000' -> datetime aware."""
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return None


# ĐO 19/08 + xác nhận lại 30/08/2026: `post_impressions*`, `page_impressions*`, `page_fans`
# đều trả "(#100) invalid insights metric" trên CẢ v21 lẫn v23 — Meta ĐÃ KHAI TỬ, KHÔNG phải
# thiếu quyền. Đừng đi xin thêm scope, vô ích. Thứ còn sống: post_clicks, post_video_views.
LIVE_POST_METRICS = ("post_clicks", "post_video_views")
LEGACY_POST_METRICS = ("post_impressions_unique", "post_impressions")


def try_insights(c, post_id, try_legacy=False):
    """Trả (dict metric, True) nếu đọc được insights; ({}, False) nếu không.

    KHÔNG coi 'không đọc được' là 'reach = 0' — hai chuyện đó khác nhau hoàn toàn,
    và nhầm lẫn đúng kiểu đó là thứ đã giấu lỗi suốt 2 tháng (20/06-17/08/2026).

    `try_legacy` chỉ bật cho bài ĐẦU TIÊN mỗi lượt: hai metric kia gần như chắc chắn chết,
    nhưng vẫn thử một lần để nếu Meta hồi sinh thì script tự dùng lại, khỏi phải nhớ sửa.
    Thử trên mọi bài thì chỉ tốn 2 round-trip/bài cho một câu trả lời đã biết.
    """
    out = {}
    metrics = (LEGACY_POST_METRICS + LIVE_POST_METRICS) if try_legacy else LIVE_POST_METRICS
    for m in metrics:
        r = get(c, f"{post_id}/insights", metric=m)
        data = r.get("data")
        if isinstance(data, list) and data:
            vals = data[0].get("values") or [{}]
            v = vals[0].get("value")
            if isinstance(v, int):
                out[m] = v
    return out, bool(out)


def collect(c, hours, now_utc):
    """Gom bài feed + reel đã PUBLISH trong `hours` giờ qua."""
    cutoff = now_utc - dt.timedelta(hours=hours)
    items, errs = [], []

    feed = get(c, f"{c['page_id']}/feed",
               fields="id,created_time,status_type,permalink_url,"
                      "reactions.summary(true).limit(0),"
                      "comments.summary(true).limit(0),shares",
               limit=25)
    if "error" in feed:
        errs.append("feed: " + str(feed["error"].get("message"))[:90])
    for p in feed.get("data", []):
        t = parse_time(p.get("created_time", ""))
        if not t or t < cutoff or t > now_utc:
            continue          # bỏ bài quá cũ, và bài còn HẸN GIỜ ở tương lai
        if p.get("status_type") == "added_video":
            continue          # Reel đếm riêng ở dưới, tránh đếm đúp
        items.append({
            "kind": "post",
            "id": p["id"],
            "t": t,
            "url": p.get("permalink_url", ""),
            "react": (p.get("reactions") or {}).get("summary", {}).get("total_count", 0),
            "cmt": (p.get("comments") or {}).get("summary", {}).get("total_count", 0),
            "share": (p.get("shares") or {}).get("count", 0),
            "views": None,
        })

    reels = get(c, f"{c['page_id']}/video_reels",
                fields="id,created_time,post_views,permalink_url", limit=25)
    if "error" in reels:
        errs.append("reels: " + str(reels["error"].get("message"))[:90])
    for r in reels.get("data", []):
        t = parse_time(r.get("created_time", ""))
        if not t or t < cutoff or t > now_utc:
            continue
        items.append({
            "kind": "reel",
            "id": r["id"],
            "t": t,
            "url": "https://www.facebook.com" + (r.get("permalink_url") or ""),
            "react": None, "cmt": None, "share": None,
            "views": r.get("post_views"),
        })

    items.sort(key=lambda x: x["t"], reverse=True)
    return items, errs


def is_silent(it, min_views):
    """Bài 'chết lặng' = không ai xem VÀ không ai tương tác.

    Với post: tương tác = 0 mà `post_clicks` > 0 thì KHÔNG phải chết lặng — có người mở bài,
    chỉ là không bấm thích. Đây đúng là ca đã làm script báo động sai ngày 30/08 (bài 29/08:
    react=0 cmt=0 share=0 nhưng clicks=2). `clicks=None` = không đọc được, KHÔNG phải = 0.
    """
    if it["kind"] == "reel":
        v = it["views"]
        return v is not None and v < min_views
    if (it["react"] or 0) + (it["cmt"] or 0) + (it["share"] or 0) > 0:
        return False
    clicks = it.get("clicks")
    if clicks is None:
        return True                       # không đo được click -> giữ nguyên hành vi cũ
    return clicks == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="", help="thư mục chứa facebook_config.json")
    ap.add_argument("--label", default="", help="tên luồng, chỉ để in cho dễ đọc")
    ap.add_argument("--hours", type=int, default=48, help="soi bài publish trong N giờ qua")
    ap.add_argument("--min-age-hours", type=float, default=6.0,
                    help="bài mới hơn ngần này thì CHƯA kết luận (FB cần thời gian phân phối)")
    ap.add_argument("--min-views", type=int, default=25,
                    help="Reel dưới ngưỡng này coi là chết lặng")
    args = ap.parse_args()

    print("FB_REACH_BEGIN")
    head = f"Hậu kiểm độ phủ Facebook{' — ' + args.label if args.label else ''} ({args.hours}h qua)"
    print(head)

    c, err = load_cfg(args.tool)
    if not c:
        print(f"  ⚠️ Không kiểm được: {err}")
        print("FB_REACH_END")
        print(f"FB_REACH_STATUS=error n=0 low=0 reason={err[:60]}")
        return 0

    now_utc = dt.datetime.now(dt.timezone.utc)
    items, errs = collect(c, args.hours, now_utc)
    for e in errs:
        print(f"  ⚠️ {e}")

    if not items:
        print("  (chưa có bài nào publish trong khoảng này)")
        print("FB_REACH_END")
        print(f"FB_REACH_STATUS=nodata n=0 low=0")
        return 0

    # Lấy insights cho TỪNG bài feed. Bản cũ chỉ lấy cho bài đầu rồi `break`, nên mọi bài
    # sau đó không bao giờ có `clicks` để `is_silent` xét -> tương tác=0 là bị kết tội ngay.
    real_ok = False
    first_post = True
    for it in items:
        if it["kind"] != "post":
            continue
        m, ok = try_insights(c, it["id"], try_legacy=first_post)
        first_post = False
        real_ok = real_ok or ok
        it["clicks"] = m.get("post_clicks")
        it["vviews"] = m.get("post_video_views")
        reach = m.get("post_impressions_unique") or m.get("post_impressions")
        if reach is not None:
            it["reach"] = reach

    mature, low = [], []
    for it in items:
        age_h = (now_utc - it["t"]).total_seconds() / 3600.0
        it["age_h"] = age_h
        if age_h < args.min_age_hours:
            continue
        mature.append(it)
        if is_silent(it, args.min_views):
            low.append(it)

    for it in items:
        loc = it["t"].astimezone(TZ).strftime("%d/%m %H:%M")
        if it["kind"] == "reel":
            num = f"views={it['views']}"
        else:
            num = f"react={it['react']} cmt={it['cmt']} share={it['share']}"
            # In click ra MÀN HÌNH, không chỉ dùng ngầm: người đọc Telegram phải thấy được
            # vì sao một bài tương tác=0 lại KHÔNG bị gắn cờ đỏ.
            num += f" clicks={it['clicks']}" if it.get("clicks") is not None else " clicks=?"
        if it.get("reach") is not None:
            num += f" reach={it['reach']}"
        young = "" if it["age_h"] >= args.min_age_hours else "  (còn mới, chưa tính)"
        mark = "🔴" if it in low else ("🟢" if it in mature else "⏳")
        print(f"  {mark} {loc}  {it['kind']:<4} {num}{young}")
        if it in low and it["url"]:
            print(f"      {it['url']}")

    if not real_ok:
        print("  ℹ️ Số trên là PROXY (views/tương tác/click), KHÔNG phải reach thật —")
        print("     Meta đã khai tử metric post_impressions* (không phải thiếu quyền).")
        print("     Reach thật chỉ xem được ở Meta Business Suite.")

    if not mature:
        print("  (bài đều còn quá mới để kết luận)")
        status = "nodata"
    elif low:
        # CHỈ NÓI CÁI ĐO ĐƯỢC. Bản cũ quy thẳng nguyên nhân cho app/quyền và đã sai một lần
        # (30/08): bài công khai bình thường, chỉ là text dài không được phân phối.
        # Chữ ký của "vô hình" THẬT (sự cố 20/06-17/08) là MỌI thứ đều câm, kể cả reel.
        # Còn reel có views mà post câm thì đó là chuyện ĐỊNH DẠNG/PHÂN PHỐI, không phải quyền.
        reels_mature = [x for x in mature if x["kind"] == "reel"]
        reels_alive = [x for x in reels_mature if (x["views"] or 0) >= args.min_views]
        print(f"  🔴 {len(low)}/{len(mature)} bài đã đủ tuổi mà rất ít người xem/tương tác.")
        if reels_mature and not reels_alive:
            print("     CẢ post LẪN reel đều câm — đây mới là dấu hiệu bài không tới được ai.")
            print("     Kiểm: app còn Live không, quyền có tụt về Standard Access không,")
            print("     Page có bị hạn chế không. (Xác nhận bằng cách mở bài ở tab ẩn danh.)")
        elif reels_alive:
            print("     Reel VẪN có người xem -> bài hiển thị bình thường, đây là chuyện")
            print("     PHÂN PHỐI/ĐỊNH DẠNG, không phải quyền. Post text thuần rất dài bị")
            print("     Facebook bóp; cân nhắc gắn ảnh/infographic hoặc rút ngắn.")
        else:
            print("     Chưa đủ căn cứ quy nguyên nhân — mở bài ở tab ẩn danh để xác nhận")
            print("     nó có công khai không trước khi đi sửa quyền.")
        status = "low"
    else:
        print(f"  🟢 {len(mature)}/{len(mature)} bài có người xem/tương tác — phân phối đang chạy.")
        status = "ok"

    print("FB_REACH_END")
    print(f"FB_REACH_STATUS={status} n={len(mature)} low={len(low)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:                     # hậu kiểm hỏng ≠ pipeline hỏng, nhưng phải KÊU
        print("FB_REACH_END")
        print(f"FB_REACH_STATUS=error n=0 low=0 reason={type(e).__name__}")
        raise SystemExit(0)
