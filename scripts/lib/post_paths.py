# -*- coding: utf-8 -*-
"""Bố cục thư mục của MỘT bài — khai ở đúng một chỗ.

Vì sao cần: trước file này, tên file bài nằm rải trong 6 script và 8 tài liệu. Đổi tên một
file là đi sửa 14 chỗ, và chỗ nào quên thì hỏng IM LẶNG — script vẫn chạy, chỉ là không
tìm thấy file rồi bỏ qua.

NGUYÊN TẮC BỐ CỤC:
· Gốc thư mục = phần NGHIÊN CỨU và VIẾT (research, content, kịch bản, sổ). Đây là thứ
  người làm bài đọc và sửa.
· Thư mục con = phần ĐEM ĐI ĐĂNG, chia theo KÊNH. Kênh nào upload file nào thì file nằm
  ở kênh đó. Không có thư mục "handoff" riêng: bàn giao chính là ba thư mục kênh này.
· Kênh khác cần cùng một file thì script DẪN XUẤT sang đích (vd infographic.png -> atlas
  <slug>-1.jpg), KHÔNG chép sang thư mục kênh khác. Có hai bản là sớm muộn hai bản lệch
  nhau, và không ai biết bản nào đã đăng.

Thứ tự thư mục kênh đọc theo thứ tự đăng: youtube -> atlas -> facebook (ATLAS_CHANNEL §3).
"""
from __future__ import annotations

from pathlib import Path

LAYOUT = {
    # --- gốc: nghiên cứu / viết / sổ ---
    "meta":       "meta.json",        # định danh bài. KHÔNG chứa URL sau đăng — xem "publish".
    "research":   "research.md",      # B1. ĐÓNG BĂNG sau B1, chỉ được append mục "Kiểm sau".
    "content":    "content.md",       # B2. Nguồn DUY NHẤT của text mọi kênh.
    "podcast":    "podcast.txt",      # B5, sinh sau Cổng 2 từ blog.md
    "scenes":     "scenes.json",      # B5
    "gates":      "gates.json",       # B4, nhật ký 23 cổng
    "publish":    "publish.json",     # B10, gộp result.json + continuity.json cũ

    # --- youtube ---
    "yt_video":   "youtube/video.mp4",
    "yt_thumb":   "youtube/thumbnail.png",     # cũng là nguồn cho atlas <slug>.jpg và cover scene 1
    "yt_desc":    "youtube/description.txt",

    # --- atlas ---
    "blog":       "atlas/blog.md",
    "atlas_html": "atlas/atlas.html",
    "audio":      "atlas/audio.mp3",

    # --- facebook ---
    "fb_post":    "facebook/post.txt",         # thân bài, 0 URL
    "fb_comment": "facebook/comment.txt",      # nơi DUY NHẤT chứa link
    "fb_image":   "facebook/infographic.png",  # đính post FB; dẫn xuất sang atlas <slug>-1.jpg
    "fb_prompt":  "facebook/infographic.prompt.txt",
    "fb_reel":    "facebook/reel.txt",         # CHỈ khi bài có short.mp4
}

# Thư mục con phải tạo khi dựng bài mới.
THU_MUC_KENH = ("youtube", "atlas", "facebook")

# File bản công khai — thứ thật sự đến tay người đọc (cổng lộ lọt quét đúng nhóm này).
FILE_CONG_KHAI = ("blog", "fb_post", "fb_comment", "yt_desc", "fb_reel", "atlas_html")


def p(thu_muc_bai, khoa: str) -> Path:
    """Đường dẫn tuyệt đối của một file trong bài. KeyError nếu khoá sai — cố ý.

    Trả về đường dẫn kể cả khi file chưa tồn tại: người gọi tự quyết định "chưa có" nghĩa
    là lỗi hay là đúng trạng thái (bài chưa dựng tới bước đó).
    """
    return Path(thu_muc_bai) / LAYOUT[khoa]


def tao_thu_muc(thu_muc_bai) -> None:
    d = Path(thu_muc_bai)
    for t in THU_MUC_KENH:
        (d / t).mkdir(parents=True, exist_ok=True)


# ── Giá trị hợp lệ của các trường trạng thái trong publish.json ────────────────────────
#
# Đây là NGUỒN SỰ THẬT, và nó cố tình HẸP: chỉ liệt kê giá trị mà code THẬT SỰ sinh ra.
#
# Trước 05/09 tài liệu khai 6 giá trị cho `agent_status`, 12 cho `post_status`, 5 cho
# `quality_check` — trong khi không lệnh nào đặt được những giá trị đó, và không cổng nào
# kiểm. Agent làm đúng theo tài liệu sẽ ghi một giá trị không ai định nghĩa vào sổ, rồi nó
# nằm im ở đó và in ra Excel. Tài liệu tả thứ không tồn tại tệ hơn không tả.
#
# Thêm trạng thái mới thì thêm ở ĐÂY trước, rồi mới viết lệnh đặt nó — không phải ngược lại.
GIA_TRI_HOP_LE = {
    "agent_status":   {"", "draft", "completed", "blocked"},
    "post_status":    {"", "not_created", "approved", "published"},
    "quality_check":  {"", "passed", "failed"},
    "review_status":  {"", "pending", "approved", "changes_requested"},
    "publish_status": {"", "not_published", "scheduled", "published", "failed"},
}
