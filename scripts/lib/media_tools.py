# -*- coding: utf-8 -*-
"""Tìm công cụ dựng hình — Chrome, ffmpeg/ffprobe, font — trên Windows, macOS, Linux.

MỘT nguồn dò cho mọi script dựng hình. Trước đây mỗi script tự giữ danh sách đường Windows
của riêng nó; có máy mới là phải nhớ sửa từng chỗ, và quên một chỗ thì script đó hỏng
theo kiểu không báo (ảnh bìa rơi về Pillow vẫn ra PNG, chỉ xấu hơn).

Biến môi trường (khai thì THẮNG mọi đường dò):

    CHROME_BIN   đường tới Chrome/Edge/Chromium, hoặc tên lệnh trên PATH.
                 Khai mà không tìm thấy ⇒ trả None và nói rõ — KHÔNG lặng lẽ dùng bản khác.
    FFMPEG_DIR   thư mục chứa ffmpeg + ffprobe (đuôi `.exe` chỉ thêm trên Windows).
    FFPROBE      đường ffprobe riêng (giữ cho tương thích với `blog_gates.py`).
    VIDEO_FONT   file font .ttf/.otf dùng khi Pillow phải tự vẽ chữ.

Font KHÔNG đóng gói vào repo: Segoe UI và Arial là font thương mại của Microsoft/Monotype,
không được phân phối lại. Trên Mac, Arial có sẵn ở `/System/Library/Fonts/Supplemental/`
và đủ dấu tiếng Việt; muốn font khác (vd Inter, giấy phép OFL) thì khai `VIDEO_FONT`.

launchd trên Mac chạy với PATH tối giản (không có `/opt/homebrew/bin`), nên ffmpeg cài qua
Homebrew phải được dò thêm ở thư mục của Homebrew — nếu không, chạy tay thì được, chạy
theo lịch thì hỏng.
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

# Hai chỗ chạm hệ thống — tách ra để test giả được máy khác mà không cần máy đó.
_la_file = os.path.isfile
_which = shutil.which

# WinGet ghim SỐ HIỆU BẢN ffmpeg vào tên thư mục -> nâng cấp ffmpeg là đứt đường này.
# Giữ làm đường lùi cho máy Windows đang chạy; máy mới nên khai FFMPEG_DIR hoặc PATH.
_WINGET_FF = ("Microsoft", "WinGet", "Packages",
              "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
              "ffmpeg-8.1.1-full_build", "bin")
_HOMEBREW = ("/opt/homebrew/bin", "/usr/local/bin")


def _he() -> str:
    return platform.system()


def chrome_candidates() -> list[str]:
    """Đường Chrome/Edge quen thuộc của hệ điều hành đang chạy (chưa kiểm tồn tại)."""
    he = _he()
    if he == "Windows":
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        lad = os.environ.get("LOCALAPPDATA", "")
        ra = [os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
              os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe")]
        if lad:
            ra.append(os.path.join(lad, "Google", "Chrome", "Application", "chrome.exe"))
        ra += [os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
               os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe")]
        return ra
    if he == "Darwin":
        goi = [("Google Chrome", "Google Chrome"), ("Chromium", "Chromium"),
               ("Microsoft Edge", "Microsoft Edge")]
        nha = os.path.expanduser("~")
        ra = []
        for app, exe in goi:
            ra.append(f"/Applications/{app}.app/Contents/MacOS/{exe}")
            ra.append(f"{nha}/Applications/{app}.app/Contents/MacOS/{exe}")
        return ra
    return []


def find_chrome() -> str | None:
    """CHROME_BIN → đường quen thuộc của hệ điều hành → PATH. Không thấy ⇒ None."""
    khai = os.environ.get("CHROME_BIN", "").strip()
    if khai:
        if _la_file(khai):
            return khai
        tren_path = _which(khai)
        if tren_path:
            return tren_path
        print(f"[media_tools] CHROME_BIN={khai!r} không tồn tại và không có trên PATH "
              f"→ coi như KHÔNG có Chrome (không tự đổi sang bản khác).", file=sys.stderr)
        return None
    for c in chrome_candidates():
        if c and _la_file(c):
            return c
    for ten in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                "chrome", "msedge", "microsoft-edge"):
        p = _which(ten)
        if p:
            return p
    return None


def ff_tool(name: str) -> str:
    """Đường tới `ffmpeg`/`ffprobe`: FFPROBE (chỉ ffprobe) → FFMPEG_DIR → WinGet (Windows)
    → PATH → Homebrew (macOS). Không thấy ⇒ trả tên trần, để lỗi nổ ở chỗ gọi."""
    if name == "ffprobe" and os.environ.get("FFPROBE", "").strip():
        return os.environ["FFPROBE"].strip()
    he = _he()
    duoi = ".exe" if he == "Windows" else ""
    thu_muc = []
    if os.environ.get("FFMPEG_DIR", "").strip():
        thu_muc.append(os.environ["FFMPEG_DIR"].strip())
    if he == "Windows" and os.environ.get("LOCALAPPDATA"):
        thu_muc.append(os.path.join(os.environ["LOCALAPPDATA"], *_WINGET_FF))
    for d in thu_muc:
        p = str(Path(d) / (name + duoi))
        if _la_file(p):
            return p
    p = _which(name)
    if p:
        return p
    if he == "Darwin":
        for d in _HOMEBREW:
            p = f"{d}/{name}"
            if _la_file(p):
                return p
    return name


def font_candidates(bold: bool = True) -> list[str]:
    """Font cho Pillow, theo thứ tự thử. Tên trần chỉ dùng trên Windows (Pillow tự tìm
    trong thư mục Fonts); hệ khác phải là đường tuyệt đối."""
    ra = []
    if os.environ.get("VIDEO_FONT", "").strip():
        ra.append(os.environ["VIDEO_FONT"].strip())
    he = _he()
    if he == "Windows":
        ra += ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    elif he == "Darwin":
        ten = "Arial Bold.ttf" if bold else "Arial.ttf"
        ra += [f"/System/Library/Fonts/Supplemental/{ten}", f"/Library/Fonts/{ten}",
               "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]
    else:
        ten = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        ra += [f"/usr/share/fonts/truetype/dejavu/{ten}", f"/usr/share/fonts/dejavu/{ten}"]
    return ra


def file_url(path: str) -> str:
    """`file://` URL đúng chuẩn trên mọi hệ: `file:///C:/…` và `file:///var/…`, có mã hoá
    dấu cách. Nối tay `"file:///" + đường` cho ra `file:////var/…` trên Mac."""
    return Path(os.path.abspath(path)).as_uri()
