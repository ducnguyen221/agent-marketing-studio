# -*- coding: utf-8 -*-
"""check_fb_scopes.py — kiểm quyền của Page token, KHÔNG in token ra màn hình.

Dùng sau khi đổi token để biết chắc quyền mới đã vào:
    python check_fb_scopes.py                       # kiểm cả 3 config
    python check_fb_scopes.py --tool <thư mục>      # kiểm 1 config

Vì sao có file này: token là secret, không được dán ra chat/log để nhờ người khác xem.
Script đọc token tại chỗ, hỏi Graph API, rồi chỉ in TÊN QUYỀN — đủ để nghiệm thu mà
không lộ gì. Exit 1 nếu thiếu quyền bắt buộc, để dùng được trong kiểm tra tự động.
"""
import argparse
import json
import os
import sys

import requests

GRAPH = "https://graph.facebook.com/v21.0"

# Quyền BẮT BUỘC cho luồng hiện tại (v3: Reel native + comment mang link)
REQUIRED = [
    ("pages_show_list",           "thấy Page mình quản trị"),
    ("pages_manage_posts",        "đăng bài / Reel"),
    ("pages_read_engagement",     "đọc lại trạng thái bài đã đăng"),
    ("pages_manage_engagement",   "COMMENT dưới bài — cần cho link ở comment đầu"),
]
OPTIONAL = [
    ("read_insights",             "đọc reach/impressions thật (hiện chưa có → watchdog dùng proxy)"),
    ("business_management",       "Page thuộc portfolio doanh nghiệp"),
]

# Cấu hình Page đến từ con trỏ FB_CONFIG (đường dẫn tới file trong kho secret của máy) —
# không đường lùi viết trong mã: tên tài khoản là dữ liệu của máy, không phải của repo.
DEFAULT_TOOLS = [p for p in [os.environ.get("FB_CONFIG")] if p]


def check(tool):
    p = tool if tool.lower().endswith(".json") else os.path.join(tool, "facebook_config.json")
    label = os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(os.path.dirname(p))
    print(f"\n=== {p} ===")
    if not os.path.isfile(p):
        print("  ⚠️ KHÔNG CÓ FILE")
        return False
    try:
        with open(p, encoding="utf-8-sig") as f:
            c = json.load(f)
        tok = c["page_token"]
    except Exception as e:
        print(f"  ⚠️ đọc config lỗi: {type(e).__name__}")
        return False

    try:
        d = requests.get(f"{GRAPH}/debug_token",
                         params={"input_token": tok, "access_token": tok},
                         timeout=30).json().get("data", {})
    except Exception as e:
        print(f"  ⚠️ gọi Graph lỗi: {type(e).__name__}")
        return False

    if not d or d.get("is_valid") is False:
        print("  ❌ TOKEN KHÔNG HỢP LỆ — cần lấy lại")
        return False

    scopes = set(d.get("scopes", []))
    exp = d.get("expires_at", 0)
    print(f"  Page   : {c.get('page_name')} ({c.get('page_id')})")
    print(f"  App    : {d.get('application')} ({d.get('app_id')})")
    print(f"  Hết hạn: {'KHÔNG (long-lived)' if exp in (0, None) else exp}")

    ok = True
    print("  Quyền BẮT BUỘC:")
    for name, why in REQUIRED:
        has = name in scopes
        if not has:
            ok = False
        print(f"    {'✅' if has else '❌'} {name:<26} {why}")
    print("  Tuỳ chọn:")
    for name, why in OPTIONAL:
        print(f"    {'✅' if name in scopes else '➖'} {name:<26} {why}")
    return ok


def check_group(tool, group_id):
    """Kiểm tra quyền của Page token trên Group cụ thể qua Graph API, không lộ secret."""
    p = tool if tool.lower().endswith(".json") else os.path.join(tool, "facebook_config.json")
    print(f"\n=== Kiểm tra quyền trên Group ({group_id}) ===")
    if not os.path.isfile(p):
        print("  ⚠️ KHÔNG CÓ FILE CONFIG")
        return False
    try:
        with open(p, encoding="utf-8-sig") as f:
            c = json.load(f)
        tok = c["page_token"]
        pid = c.get("page_id", "")
    except Exception as e:
        print(f"  ⚠️ đọc config lỗi: {type(e).__name__}")
        return False

    try:
        r = requests.get(f"{GRAPH}/{group_id}",
                         params={"fields": "id,name,privacy,administrator",
                                 "access_token": tok}, timeout=30)
    except Exception as e:
        print(f"  ⚠️ gọi Graph API lỗi: {type(e).__name__}")
        return False

    if r.ok:
        d = r.json()
        print(f"  Tên Group  : {d.get('name')!r} (ID: {d.get('id')})")
        print(f"  Quyền riêng tư: {d.get('privacy', 'N/A')}")
        print(f"  Admin/Mod  : {'Có' if d.get('administrator') else 'Thành viên / Được cấp quyền'}")
        print(f"  Page Token : {c.get('page_name')} ({pid})")
        print("  ✅ ĐỦ QUYỀN TRUY CẬP VÀ ĐĂNG BÀI VÀO GROUP DƯỚI TƯ CÁCH PAGE.")
        return True

    try:
        err_data = r.json().get("error", {})
    except Exception:
        err_data = {}
    code = err_data.get("code")
    subcode = err_data.get("error_subcode")
    msg = err_data.get("message", r.text[:200])

    print(f"  ❌ KHÔNG THỂ TRUY CẬP GROUP ({group_id}): HTTP {r.status_code}")
    print(f"  Mã lỗi FB  : {code} (subcode: {subcode})")
    print(f"  Thông báo  : {msg}")
    print("  👉 Hướng dẫn xử lý:")
    if code == 190:
        print("     1. Token của Page đã hết hạn hoặc không hợp lệ. Cần tạo lại Page Access Token.")
    elif code == 200:
        print("     1. Đảm bảo Page của bạn đã THAM GIA vào Group với tư cách Page.")
        print("     2. Trong cài đặt Group, kiểm tra xem Page có được cấp quyền đăng bài không.")
        print("     3. Lưu ý Meta Graph API v19+: Page nên là Quản trị viên (Admin) của Group để đăng trực tiếp.")
    elif code == 10:
        print("     1. App chưa được thêm vào Group hoặc bị giới hạn quyền truy cập.")
    else:
        print("     1. Kiểm tra lại ID Group có chính xác không.")
        print("     2. Kiểm tra token có quyền `pages_manage_posts` và Page là thành viên Group.")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="", help="file config hoặc thư mục chứa facebook_config.json (bỏ trống = biến FB_CONFIG)")
    ap.add_argument("--group-id", default="", help="ID của Facebook Group cần kiểm tra quyền đăng")
    args = ap.parse_args()
    tools = [args.tool] if args.tool else DEFAULT_TOOLS
    if not tools:
        ap.error("chưa có cấu hình: truyền --tool hoặc đặt FB_CONFIG")
    results = [check(t) for t in tools]
    group_ok = True
    if args.group_id:
        group_results = [check_group(t, args.group_id) for t in tools]
        group_ok = all(group_results)
    print()
    if all(results) and group_ok:
        print("✅ TẤT CẢ QUYỀN ĐẠT — sẵn sàng đăng bài.")
        return 0
    print("❌ CÒN THIẾU QUYỀN — xem chi tiết lỗi ở trên.")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
