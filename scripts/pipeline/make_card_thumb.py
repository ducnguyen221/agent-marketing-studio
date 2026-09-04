# -*- coding: utf-8 -*-
r"""make_card_thumb.py — thumbnail.png (cover 1280x720) → <slug>.jpg nhẹ cho card atlas.

Trang chủ atlas (dải "Mới nhất") hiển thị ảnh bìa cho mỗi bài. Ảnh gốc PNG ~400KB quá
nặng cho 10 card; script này hạ kích thước + xuất JPG (~40-60KB) đặt CẠNH file html
(`content/<cat>/<slug>.jpg`) để generate-manifest.js bắt được + card <img>.

CLI:
  python make_card_thumb.py --src thumbnail.png --out <atlas>/content/ai/<slug>.jpg [--width 640]
→ in `OK <abs_out>`.
"""
import argparse
import os
import sys

from PIL import Image


def main(argv=None):
    ap = argparse.ArgumentParser(description="thumbnail.png -> <slug>.jpg nhẹ cho card atlas")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=640)
    a = ap.parse_args(argv)

    if not os.path.isfile(a.src):
        sys.exit(f"thiếu ảnh nguồn: {a.src}")
    im = Image.open(a.src).convert("RGB")
    w, h = im.size
    if w > a.width:
        im = im.resize((a.width, round(h * a.width / w)), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    im.save(a.out, "JPEG", quality=82, optimize=True)
    print(f"OK {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
