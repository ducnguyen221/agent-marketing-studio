# -*- coding: utf-8 -*-
"""audio_truyen.py — MỘT lệnh: crawl chương truyện (tamhoan.com) -> đọc bằng OmniVoice giọng
'Giọng tiên hiệp' (ASR-verify tiêu đề) -> [tuỳ chọn] dựng video (nền + nhạc + overlay tên
chương + logo + phụ đề chạy + outro + fade). Dùng bởi slash command /audio-truyen.

Ví dụ:
  python audio_truyen.py --url https://tamhoan.com/pham-nhan-tu-tien/ --start 1141 --end 1150 --video
  python audio_truyen.py --start-id 107258 --chapters 2 --no-video
"""
import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# Script da doi sang apps/truyen/ (2026-08-26). DU LIEU (venv, assets, truyen-out,
# _vtitles, voices) VAN O GOC ENGINE - neo vao day, khong neo vao HERE.
# Phân giải (Windows + macOS): truyen_paths.py — OMNIVOICE_DIR → VOICE_STATION/omnivoice.
import truyen_paths  # noqa: E402
ENGINE = truyen_paths.engine_dir()
PY = truyen_paths.venv_python(ENGINE)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", HF_HUB_OFFLINE="0")


def default_out_dir():
    """Nơi xuất mặc định: LOCAL, cạnh script này.

    Trước đây hàm này dò Desktop (OneDrive\\Desktop rồi ~\\Desktop) và khi cả hai
    đều không có thì `return up` = thư mục home — tức ghi mp3/mp4 thẳng
    vào home root, vi phạm luật §C. Sau khi OneDrive đổi chủ (07/2026) cả hai ứng
    viên đều biến mất nên nhánh hỏng đó thành mặc định.
    Giờ sản phẩm nằm local cạnh script; muốn chỗ khác thì truyền --out-dir.
    """
    return os.path.join(ENGINE, "truyen-out", "out")


def run(cmd, retries=0):
    """Chạy 1 bước; thử lại `retries` lần nếu exit≠0 (encode đôi khi fail thoáng qua khi máy tải nặng)."""
    print(">>", " ".join(str(c) for c in cmd[2:]))
    rc = 1
    for attempt in range(retries + 1):
        rc = subprocess.run(cmd, env=ENV, cwd=HERE).returncode
        if rc == 0:
            return
        if attempt < retries:
            print(f"  ! exit {rc} — thử lại ({attempt + 1}/{retries}) sau 25s ...")
            time.sleep(25)
    sys.exit(f"BƯỚC LỖI (exit {rc}).")


def main():
    ap = argparse.ArgumentParser(description="Crawl + narrate (+video) một truyện tamhoan.com.")
    ap.add_argument("--url", default=None, help="URL truyện, vd https://tamhoan.com/pham-nhan-tu-tien/")
    ap.add_argument("--slug", default="pham-nhan-tu-tien")
    ap.add_argument("--site", default=None, choices=("tamhoan", "truyenfull", "pntt2"),
                    help="Nguồn (passthrough read_story; mặc định tự nhận từ --url).")
    ap.add_argument("--start-url", dest="start_url", default=None,
                    help="pntt2: URL trang chương bắt đầu (passthrough read_story).")
    ap.add_argument("--start", type=int, default=None, help="Số chương bắt đầu.")
    ap.add_argument("--end", type=int, default=None, help="Số chương kết thúc.")
    ap.add_argument("--start-id", dest="start_id", type=int, default=None, help="ID URL chương đầu.")
    ap.add_argument("--chapters", type=int, default=None, help="Số chương (khi dùng --start-id).")
    ap.add_argument("--video", dest="video", action="store_true", default=True)
    ap.add_argument("--no-video", dest="video", action="store_false")
    ap.add_argument("--out-dir", dest="out_dir", default=None,
                    help="Thư mục xuất (mặc định truyen-out/out cạnh script, KHÔNG phải Desktop).")
    ap.add_argument("--voice", default="Giọng tiên hiệp", help="Profile giọng đọc (read_story).")
    ap.add_argument("--bgm-file", dest="bgm_file", default=None,
                    help="Ghi đè nhạc nền video (mặc định 'Nhạc nền tiên hiệp 1.mp3').")
    # passthrough audio
    ap.add_argument("--speed", type=float, default=0.9)
    ap.add_argument("--gap-chapter", dest="gap_chapter", type=float, default=10.0)
    ap.add_argument("--lead-in", dest="lead_in", type=float, default=7.0,
                    help="Giây đầu video (hiện thẻ mở đầu 'từ chương…đến chương…' rồi vào chương 1).")
    ap.add_argument("--ending-text", dest="ending_text", default="",
                    help="Lời kết đọc sau chương cuối (nghỉ 5s rồi đọc).")
    ap.add_argument("--ending-gap", dest="ending_gap", type=float, default=5.0)
    ap.add_argument("--no-verify-title", dest="verify_title", action="store_false", default=True)
    # passthrough video
    ap.add_argument("--title-scale", dest="title_scale", type=float, default=2.0)
    ap.add_argument("--show", type=float, default=6.0)
    ap.add_argument("--bgm-vol", dest="bgm_vol", type=float, default=0.06)  # 1/2 mức cũ (0.12)
    ap.add_argument("--sub-size", dest="sub_size", type=int, default=18)
    ap.add_argument("--logo-w", dest="logo_w", type=int, default=150)
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--no-logo", dest="no_logo", action="store_true")
    ap.add_argument("--no-subs", dest="no_subs", action="store_true")
    # Outro PNTT.mp3 (audio chào mẫu user cung cấp) MẶC ĐỊNH BỎ từ 2026-07-06:
    # lời kết đã được đọc bằng giọng clone qua --ending-text, ghép thêm outro cũ = LẶP câu chào.
    ap.add_argument("--no-outro", dest="no_outro", action="store_true", default=True)
    ap.add_argument("--with-outro", dest="no_outro", action="store_false",
                    help="Ghép lại Outro PNTT.mp3 cũ sau lời kết (chỉ khi cố ý).")
    args = ap.parse_args()

    slug = args.slug
    if args.url:
        ms = re.search(r"tamhoan\.com/([^/?#]+)", args.url)
        if ms:
            slug = ms.group(1)

    # Tag giọng để TÁCH HOÀN TOÀN version a-tun khỏi version "Giọng tiên hiệp"
    # (tên file + thư mục cache wav riêng → không bao giờ dùng nhầm wav giọng khác).
    is_default_voice = args.voice.strip().lower() in ("giọng tiên hiệp", "giong tien hiep")
    vtag = "" if is_default_voice else "_" + re.sub(r"[^a-z0-9]+", "", args.voice.lower())

    if args.start is not None:
        label = f"{slug}{vtag}_{args.start}-{args.end if args.end else args.start}"
    elif args.start_id is not None:
        label = f"{slug}{vtag}_id{args.start_id}_n{args.chapters or 2}"
    else:
        sys.exit("Cần --start (số chương) hoặc --start-id.")

    out_dir = args.out_dir or default_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    voice = os.path.join(out_dir, label + ".mp3")
    video = os.path.join(out_dir, label + ".mp4")
    # cache wav riêng cho mỗi giọng (mặc định: truyen-out/<slug>; a-tun: truyen-out/<slug>__atun)
    read_out_dir = os.path.join(ENGINE, "truyen-out", slug + ("" if is_default_voice else vtag.replace("_", "__")))

    # ---- BƯỚC 1: đọc truyện -> mp3 + manifest + srt ----
    rs = [PY, "-u", os.path.join(HERE, "read_story.py"), "--slug", slug,
          "--voice", args.voice, "--out-dir", read_out_dir,
          "--speed", str(args.speed), "--gap-chapter", str(args.gap_chapter),
          "--lead-in", str(args.lead_in), "--out-file", voice]
    if not args.verify_title:
        rs += ["--no-verify-title"]
    if args.ending_text:
        rs += ["--ending-text", args.ending_text, "--ending-gap", str(args.ending_gap)]
    if args.start is not None:
        rs += ["--start-chapter", str(args.start)]
        if args.end is not None:
            rs += ["--end-chapter", str(args.end)]
    else:
        rs += ["--start-id", str(args.start_id), "--chapters", str(args.chapters or 2)]
    if args.url:
        rs += ["--url", args.url]
    if args.site:
        rs += ["--site", args.site]
    if args.start_url:
        rs += ["--start-url", args.start_url]
    print("===== BƯỚC 1/2: ĐỌC TRUYỆN =====")
    run(rs)

    if not args.video:
        print(f"\n✅ XONG (audio). -> {voice}")
        return

    # ---- BƯỚC 2: dựng video ----
    mv = [PY, "-u", os.path.join(HERE, "make_video.py"),
          "--manifest", voice + ".manifest.json", "--out", video,
          "--title-scale", str(args.title_scale), "--show", str(args.show),
          "--bgm-vol", str(args.bgm_vol), "--sub-size", str(args.sub_size),
          "--logo-w", str(args.logo_w), "--w", str(args.w), "--h", str(args.h)]
    if args.bgm_file:
        mv += ["--bgm-file", args.bgm_file]
    for flag, on in (("--no-logo", args.no_logo), ("--no-subs", args.no_subs),
                     ("--no-outro", args.no_outro)):
        if on:
            mv += [flag]
    print("\n===== BƯỚC 2/2: DỰNG VIDEO =====")
    run(mv, retries=2)  # encode đôi khi crash khi máy tải nặng → tự thử lại
    print(f"\n✅ XONG. audio -> {voice}\n        video -> {video}")


if __name__ == "__main__":
    main()
