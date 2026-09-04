# -*- coding: utf-8 -*-
r"""gen_article.py — TÁCH content.md ra các file kênh, theo bố cục post_paths.LAYOUT.

`content.md` là nguồn DUY NHẤT của mọi text đem đăng. Script này tách nó thành các file
mà công cụ đăng thật sự ăn được (mọi tool đăng nhận ĐƯỜNG DẪN FILE, không nhận chuỗi):

  atlas/blog.md            <- ## post:blog_article
  facebook/post.txt        <- ## post:facebook_post      (thân bài, 0 URL)
  facebook/comment.txt     <- ### comment_1              (nơi DUY NHẤT chứa link)
  youtube/description.txt  <- ## post:youtube_desc
  facebook/reel.txt        <- ## post:reel   — CHỈ khi có cờ --with-reel

CLI:
  python gen_article.py --content-md F --meta meta.json --out-dir FOLDER [--with-reel]
→ in JSON các path + dòng cuối `OK <abs_path out-dir>`.

Tách theo NEO `## post:<tên>`, không theo số mục: số mục xê dịch theo từng bài, neo thì
không. Vẫn nhận dạng cũ (`## 3) Blog`) để bài cũ không vỡ.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "lib"))
import post_paths as PP  # noqa: E402

# Heading mục cấp section: "## 3) Blog", "### 4. FB post", "## 5 - YouTube desc"...
# Bắt: dấu #, số mục (1-9), dấu ngăn tùy ý, phần nhãn còn lại.
_SECTION_RE = re.compile(
    r"^\s{0,3}(#{2,3})\s*(\d{1,2})\s*[\).:\-–—]?\s*(.*)$"
)

# Nhãn (fallback khi heading không đánh số): map keyword -> khóa kênh.
# Thứ tự ưu tiên check: cụ thể trước (youtube/desc) rồi chung.
_LABEL_PATTERNS = [
    ("youtube_desc", re.compile(r"youtube", re.I)),
    ("fb_desc",      re.compile(r"\bfb\b.*\b(desc|caption|mô\s*tả)\b|facebook.*\b(desc|caption|mô\s*tả)\b", re.I)),
    ("fb_post",      re.compile(r"\bfb\b.*post|facebook.*post|\bpost\b.*facebook|bài.*facebook", re.I)),
    ("blog",         re.compile(r"\bblog\b|bài\s*viết", re.I)),
]

# Số mục chuẩn theo mẫu content -> khóa kênh.
_NUM_TO_KEY = {3: "blog", 4: "fb_post", 5: "youtube_desc", 6: "fb_desc"}

# NEO kiểu repo: "## post:facebook_post". Đây là dạng content.md hiện dùng.
# Trước bản vá này script CHỈ hiểu heading có ĐÁNH SỐ ("## 3) Blog"), nên khi cho ăn
# đúng template của chính repo thì tách ra 0 khối. Tách theo NEO chứ không theo SỐ MỤC
# là điều kiện bắt buộc: số mục xê dịch theo từng bài, neo thì không.
_ANCHOR_RE = re.compile(r"^\s{0,3}(#{2,4})\s*post:\s*([a-z0-9_]+)\s*$", re.I)
_ANCHOR_TO_KEY = {
    "blog_article": "blog", "blog": "blog",
    "facebook_post": "fb_post",
    "youtube_desc": "youtube_desc", "youtube_video": "youtube_desc",
    "reel": "fb_desc", "fb_desc": "fb_desc", "fb_caption": "fb_desc",
}
# Comment đầu tiên của bài Facebook — nơi DUY NHẤT được chứa link (luật 04/09/2026).
# Nằm lồng bên trong khối facebook_post nên phải bắt riêng, nếu không nó bị nuốt vào
# thân post và biến thành đúng cái lỗi "link trong thân bài" mà cổng G09 đang chặn.
_COMMENT_RE = re.compile(r"^\s{0,3}(#{2,4})\s*comment_1\s*$", re.I)

# Marker phân mục của mẫu content (vd "<!-- BEGIN BLOG -->", "<!-- END FB_POST -->")
# — KHÔNG được lọt vào file kênh (sẽ vào narration/HTML).
_MARKER_RE = re.compile(r"^\s*<!--\s*(BEGIN|END)\b.*?-->\s*$", re.I)


def _strip_markers(text):
    return "\n".join(ln for ln in text.split("\n") if not _MARKER_RE.match(ln)).strip("\n")


# Khóa kênh -> tên file output.
# Tên file lấy từ post_paths.LAYOUT — một nguồn sự thật. Đường dẫn có thư mục con
# (vd "facebook/post.txt") nên write_outputs phải tạo thư mục cha.
_OUT_FILES = {
    "blog": PP.LAYOUT["blog"],
    "fb_post": PP.LAYOUT["fb_post"],
    "fb_comment": PP.LAYOUT["fb_comment"],
    "youtube_desc": PP.LAYOUT["yt_desc"],
}
# reel CHỈ sinh khi bài có short.mp4 — bài thường không dùng tới, sinh ra là rác và còn
# chứa link blog (trái luật "thân bài Facebook 0 URL").
_OUT_REEL = {"fb_desc": PP.LAYOUT["fb_reel"]}


def _read(path):
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"Không thấy file: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _classify_heading(num, label):
    """Trả về khóa kênh ('blog'/'fb_post'/'youtube_desc'/'fb_desc') hoặc None."""
    # Ưu tiên nhãn cụ thể (để không nhầm '## 3 Core argument' của brief cũ).
    for key, pat in _LABEL_PATTERNS:
        if pat.search(label or ""):
            return key
    # Fallback: theo số mục chuẩn.
    return _NUM_TO_KEY.get(num)


def split_content(md_text):
    """Tách content.md -> dict {key: text} cho 4 kênh.

    Quét theo heading mục (## / ###). Mỗi heading mục mở 1 'section'; nội dung
    chạy tới heading mục CÙNG CẤP (hoặc cấp nông hơn) tiếp theo.
    """
    lines = md_text.replace("\r\n", "\n").split("\n")
    sections = []  # list of (key, level, [lines])
    cur = None     # (key, level, list)
    for raw in lines:
        # Thứ tự nhận dạng: neo "## post:x" -> "### comment_1" -> heading đánh số.
        ma = _ANCHOR_RE.match(raw)
        mc = _COMMENT_RE.match(raw) if ma is None else None
        m = _SECTION_RE.match(raw) if (ma is None and mc is None) else None
        if ma is not None:
            level = len(ma.group(1))
            key = _ANCHOR_TO_KEY.get(ma.group(2).lower())
        elif mc is not None:
            # comment_1 lồng bên trong facebook_post: đóng khối cha rồi mở khối riêng,
            # bất kể cấp heading, nên ép level về cấp của khối đang mở.
            level = cur[1] if cur else len(mc.group(1))
            key = "fb_comment"
        if m:
            level = len(m.group(1))
            num = int(m.group(2))
            label = m.group(3).strip()
            key = _classify_heading(num, label)
        if ma is not None or mc is not None or m:
            if key is not None:
                # Đóng section hiện tại nếu heading mới cùng cấp hoặc nông hơn.
                if cur and level <= cur[1]:
                    cur = None
                if cur is None:
                    cur = (key, level, [])
                    sections.append(cur)
                    continue  # bỏ dòng heading mục khỏi nội dung
                # heading mục lồng sâu hơn trong 1 section đang mở -> giữ nguyên dòng.
            else:
                # Heading đánh số nhưng KHÔNG phải mục kênh (vd '## 7) Ghi chú').
                # Nếu cùng cấp/nông hơn section đang mở -> đóng section.
                if cur and level <= cur[1]:
                    cur = None
                    continue
        if cur is not None:
            cur[2].append(raw)

    out = {}
    for key, _level, buf in sections:
        text = "\n".join(buf).strip("\n")
        # Giữ bản đầy đủ nhất nếu mục lặp (lấy bản dài hơn).
        if key not in out or len(text) > len(out[key]):
            if text.strip():
                out[key] = text
    return out


def write_outputs(parts, out_dir, with_reel=False):
    """Ghi 4 file (chỉ ghi file có nội dung). Trả về dict key->abs_path đã ghi."""
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    bang = dict(_OUT_FILES)
    if with_reel:
        bang.update(_OUT_REEL)
    for key, fname in bang.items():
        text = _strip_markers(parts.get(key, ""))
        # Bỏ dấu ngắt "---" mà content.md dùng để tách khối. Nó là ký hiệu CỦA FILE NGUỒN,
        # không thuộc về bản giao cho kênh — để sót thì nó lên thẳng phần mô tả YouTube và
        # vào comment Facebook nguyên văn ba dấu gạch.
        text = re.sub(r"(?:\n\s*(?:-{3,}|\*{3,}|_{3,})\s*)+$", "", text).strip()
        if not text or not text.strip():
            continue
        path = os.path.join(out_dir, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # blog.md: chuẩn hoá xuống dòng cuối; .txt: 1 newline cuối.
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.rstrip("\n") + "\n")
        written[key] = os.path.abspath(path)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Tách content.md (mẫu content) -> blog.md/fb_post.txt/youtube_desc.txt/fb_desc.txt")
    ap.add_argument("--content-md", required=True, help="instance content.md (mục 1-7)")
    ap.add_argument("--meta", required=True, help="meta.json của bài (giữ tương thích CLI)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--with-reel", action="store_true",
                    help="sinh thêm facebook/reel.txt — CHỈ dùng khi bài có short.mp4")
    args = ap.parse_args(argv)

    md_text = _read(args.content_md)
    # meta đọc để validate tồn tại + tương thích contract (chưa dùng trực tiếp khi tách).
    with open(args.meta, encoding="utf-8-sig") as f:
        json.load(f)

    parts = split_content(md_text)
    if "blog" not in parts:
        raise ValueError(
            "Không tách được khối blog từ content.md — cần neo '## post:blog_article' "
            "(hoặc heading đánh số '## 3) Blog' theo kiểu cũ).")
    written = write_outputs(parts, args.out_dir, args.with_reel)

    missing = [k for k in _OUT_FILES if k not in written]   # reel không tính là thiếu
    print(json.dumps({"out_dir": os.path.abspath(args.out_dir),
                      "written": written,
                      "missing_sections": missing},
                     ensure_ascii=False, indent=2))
    print(f"OK {os.path.abspath(args.out_dir)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
