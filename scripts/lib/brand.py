# -*- coding: utf-8 -*-
"""brand.py — DANH TÍNH của một kênh, đọc từ cấu hình trạm chứ không từ mã nguồn.

## Vì sao tồn tại

Bốn script dựng sản phẩm công khai (`build_blog_html`, `gen_infographic`,
`make_podcast_video`, `blog_gates`) từng mang sẵn tên miền, tên người, tên tổ chức và
link mạng xã hội của **một** chủ repo ngay trong mã. Hai hậu quả khác nhau, đều nặng:

· Rò rỉ — repo là MIT công khai, mọi thứ trong mã ra Internet vĩnh viễn.
· Khuôn hỏng — ai clone về cũng xuất bản dưới danh nghĩa người khác, và **không hề biết**:
  trang họ dựng ra có chân trang, ảnh đại diện và bốn nút mạng xã hội của người lạ.

Cái thứ hai tệ hơn, vì nó im lặng. Cổng `tests/test_no_identity_leak.py` chặn tái phạm;
module này là chỗ để câu trả lời đúng đi vào.

## Nguồn sự thật: `channel.yml` khối `brand:`

Danh tính thuộc về **trạm** (nơi chứa nội dung thật), không thuộc về repo engine. Thứ tự
phân giải, dừng ở chỗ đầu tiên có:

    1. `--brand <file>`   — file `.json`/`.yml` khai thẳng khối brand (dùng khi chạy tay)
    2. đi NGƯỢC LÊN từ một đường dẫn đang xử lý tới `channel.yml`, lấy khối `brand:`

Cố ý **không có tầng ba**. Trước bản này, ba khoá đi qua biến môi trường `ATLAS_*` mà
biến nào cũng có **giá trị mặc định là danh tính thật** — tức không ai phải khai gì cả,
và vì thế không ai từng khai. Một mặc định "chạy được ngay" là cách chắc chắn nhất để
khuôn không bao giờ được điền.

## FAIL-CLOSED

Thiếu `brand:` hoặc thiếu một khoá bắt buộc → `BrandThieu`, và script gọi phải **dừng
với mã 2**, không dựng ra file nào. Không có đường lùi về tên thật, cũng không có đường
lùi về chuỗi rỗng: một trang có chân trang trống trông như trang hỏng, còn một trang
mang tên người khác thì trông như thật — và sai im lặng là loại sai đắt nhất.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

import studio_paths as SP

# Khoá BẮT BUỘC: thiếu một trong ba thì sản phẩm công khai ra sai mà không có dòng lỗi
# nào — trang không biết mình tên gì, của ai, ở đâu. Khoá chỉ làm đẹp không nằm ở đây.
KHOA_BAT_BUOC = ("site_name", "author", "site_base")

# Khoá TÙY CHỌN mà bốn script dựng sản phẩm biết đọc. Liệt kê ra đây để `channel.yml`
# mẫu và tài liệu có một danh sách duy nhất để đối chiếu.
# Bảy khoá cuối thêm 20/09 (REVIEW-P2 Ghi nhận 12): mã ĐANG ĐỌC chúng nhưng danh sách
# này không có, trong khi chính nó tự xưng là "một danh sách duy nhất để đối chiếu". Một
# danh sách thiếu thì tệ hơn không có: người dùng tin nó và không biết mình đang bỏ trống
# một khoá có tác dụng. `home_domain` khai được ở CẤP KÊNH (ngoài khối `brand:`) — xem
# `doc()`; liệt kê ở đây để khuôn `channel.yml` luôn có một dòng cho nó.
KHOA_TUY_CHON = ("home_url", "author_title", "author_avatar", "og_image", "footer",
                 "org_names", "socials", "badge_default",
                 "a", "b", "author_display", "footer_image", "footer_video",
                 "home_domain", "site_home")


class BrandThieu(RuntimeError):
    """Không có khối `brand:` dùng được. Người gọi phải dừng, không được đoán."""


def _doc_file(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    d = json.loads(t) if p.suffix.lower() == ".json" else (yaml.safe_load(t) or {})
    if not isinstance(d, dict):
        raise BrandThieu(f"{p}: phải là ánh xạ khoá-giá trị, đang là {type(d).__name__}")
    # Cho phép khai cả hai dạng: nguyên khối brand, hoặc cả channel.yml có khối `brand:`.
    b = d.get("brand", d)
    if not isinstance(b, dict):
        raise BrandThieu(f"{p}: `brand:` phải là ánh xạ khoá-giá trị")
    if "home_domain" in d and "home_domain" not in b:
        b = {**b, "home_domain": d["home_domain"]}
    return b


def tim_kenh(tu) -> Path | None:
    """`channel.yml` gần nhất tính từ `tu` đi ngược lên. Không thấy → None."""
    try:
        return SP.channel_of(tu) / SP.MOC_KENH
    except (FileNotFoundError, OSError):
        return None


def doc(brand_file=None, *, tu=None, bat_buoc=KHOA_BAT_BUOC) -> dict:
    """Trả khối brand đã kiểm. Thiếu → `BrandThieu` với câu chỉ rõ phải sửa file nào.

    `brand_file` — đường dẫn khai thẳng (cờ `--brand`). `tu` — một đường dẫn bất kỳ trong
    cây trạm (file meta, thư mục bài…) để đi ngược lên tìm `channel.yml`.
    """
    nguon: Path | None = None
    if brand_file:
        nguon = Path(brand_file).expanduser()
        if not nguon.is_file():
            raise BrandThieu(f"--brand trỏ tới file không có thật: {nguon}")
    elif tu is not None:
        nguon = tim_kenh(tu)

    if nguon is None:
        raise BrandThieu(
            "không tìm thấy `channel.yml` để lấy danh tính kênh.\n"
            "Chạy lệnh này từ trong cây trạm, hoặc khai `--brand <file>`.\n"
            "Repo engine KHÔNG mang sẵn tên miền/tên người của ai — xem scripts/lib/brand.py.")

    b = _doc_file(nguon)
    thieu = [k for k in bat_buoc if not str(b.get(k) or "").strip()]
    if thieu:
        raise BrandThieu(
            f"{nguon}: khối `brand:` thiếu khoá {thieu}.\n"
            f"Điền vào `brand:` của channel.yml. Thiếu mà vẫn dựng thì trang ra đời không "
            f"biết mình tên gì, của ai — và không có dòng lỗi nào.")
    return {k: v for k, v in b.items() if v not in (None, "")}


def site_base(b: dict) -> str:
    """URL gốc, KHÔNG có dấu `/` cuối — mọi chỗ ghép URL đều giả định vậy."""
    return str(b["site_base"]).rstrip("/")


def home_domain(b: dict) -> str:
    """Tên miền trần, để phân biệt link 'về nhà' với nguồn ngoài."""
    d = str(b.get("home_domain") or "").strip()
    if d:
        return d
    s = site_base(b)
    return s.split("//", 1)[-1].split("/", 1)[0]


def org_names(b: dict) -> list[str]:
    """Tên tổ chức không được lộ ra bản công khai của kênh KHÁC (cổng G22).

    Danh sách này là CẤU HÌNH chứ không phải hằng số trong mã: mỗi chủ repo có bộ tên
    riêng, và bộ tên của người này vô nghĩa với người kia.
    """
    v = b.get("org_names") or []
    if isinstance(v, str):
        v = [x.strip() for x in v.split(",")]
    return [str(x).strip() for x in v if str(x).strip()]


# ── Kho BIỂU TƯỢNG dùng chung ────────────────────────────────────────────────
#
# Đây là HÌNH, không phải danh tính: một quyển sách mở, một quả địa cầu, logo nền
# tảng. Chúng ở trong mã có chủ đích — cấu hình chỉ chọn TÊN biểu tượng
# (`socials: [{icon: youtube, url: …}]`), không dán SVG thô vào `channel.yml`.
#
# Vì sao không để cấu hình dán SVG: nội dung `channel.yml` đi thẳng vào HTML xuất
# bản. Cho phép dán thẻ tuỳ ý là biến một file cấu hình thành mã chạy trên trang
# của người đọc. Chọn theo tên thì tập giá trị hợp lệ là hữu hạn và đọc được.
ICON = {
    "brand": '<svg viewBox="0 0 576 512" fill="#fff"><path d="M249.6 471.5c10.8 3.8 22.4-4.1 22.4-15.5V78.6c0-4.2-1.6-8.4-5-11C247.4 52 202.4 32 144 32C93.5 32 46.3 45.3 18.1 56.1C6.8 60.5 0 71.7 0 83.8V454.1c0 11.9 12.8 20.2 24.1 16.5C55.6 460.1 105.5 448 144 448c33.9 0 79 14 105.6 23.5zm76.8 0C353 462 398.1 448 432 448c38.5 0 88.4 12.1 119.9 22.6c11.3 3.8 24.1-4.6 24.1-16.5V83.8c0-12.1-6.8-23.3-18.1-27.6C529.7 45.3 482.5 32 432 32c-58.4 0-103.4 20-123 35.6c-3.3 2.6-5 6.8-5 11V456c0 11.4 11.7 19.3 22.4 15.5z"/></svg>',
    "website": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
    "profile": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
}


class IconLa(BrandThieu):
    """Cấu hình chọn một biểu tượng không có trong kho — dừng, đừng vẽ ô trống."""


def icon(ten: str) -> str:
    try:
        return ICON[str(ten).strip().lower()]
    except KeyError:
        raise IconLa(
            f"biểu tượng {ten!r} không có trong kho. Có: {', '.join(sorted(ICON))}.\n"
            f"Thêm biểu tượng mới vào scripts/lib/brand.py:ICON, đừng dán SVG vào channel.yml."
        ) from None


def socials(b: dict) -> list[dict]:
    """Danh sách nút mạng xã hội đã kiểm: mỗi mục cần `icon` và `url`."""
    ra = []
    for i, m in enumerate(b.get("socials") or []):
        if not isinstance(m, dict) or not str(m.get("url") or "").strip():
            raise BrandThieu(f"brand.socials[{i}] thiếu `url` (hoặc không phải ánh xạ)")
        nhan = str(m.get("label") or m.get("icon") or "").strip()
        ra.append({"icon": icon(m.get("icon") or "website"),
                   "url": str(m["url"]).strip(),
                   "label": nhan,
                   "title": str(m.get("title") or nhan).strip()})
    return ra
