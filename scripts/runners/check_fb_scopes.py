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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="", help="file config hoặc thư mục chứa facebook_config.json (bỏ trống = biến FB_CONFIG)")
    args = ap.parse_args()
    tools = [args.tool] if args.tool else DEFAULT_TOOLS
    if not tools:
        ap.error("chưa có cấu hình: truyền --tool hoặc đặt FB_CONFIG")
    results = [check(t) for t in tools]
    print()
    if all(results):
        print("✅ ĐỦ QUYỀN — comment link sẽ chạy được ở lần đăng tới.")
        return 0
    print("❌ CÒN THIẾU QUYỀN — xem dấu ❌ ở trên. Làm lại bước cấp quyền trong knowledge/toolchains/PLATFORM_SETUP.md")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
