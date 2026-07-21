#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_kpim_bank.py — sinh 8 bảng còn thiếu của bộ dữ liệu học liệu MKA-101 (KPIM Bank).

Nguồn (CHỈ ĐỌC, không bao giờ ghi đè):
    <KPIM Academy>/.../KPIM Bank Marketing Data/
        KPIM_Bank_Marketing_Plan.xlsx   (sheet Campaign 4 dòng, sheet Post 60 dòng)
        Facebook Post Summary.csv       (60 dòng × 95 cột)
        Facebook Post Daily.csv         (630 dòng)

Sinh ra (deterministic — seed 20260721, chạy lại ra y hệt):
    content/KPIM/instance.yml
    content/KPIM/01_brand/pillars.csv
    content/KPIM/02_campaigns/<campaign_id>/brief.yml + calendar.csv
    content/KPIM/03_approvals/content_review.csv
    content/KPIM/04_published/execution_log.csv
    content/KPIM/DATA_DICTIONARY.md
    data/KPIM/raw/youtube_export.csv
    data/KPIM/raw/leads/lead_*.csv          (7 file schema LỆCH NHAU — bài luyện S05)
    data/KPIM/raw/Facebook Post *.csv       (copy nguyên si từ nguồn)
    data/KPIM/star/kpi_target.csv
    data/KPIM/star/cost_by_post.csv
    data/KPIM/star/cta_lead_bridge.csv

Nguyên tắc: KHÔNG PII thật · KHÔNG token · KHÔNG gọi API · CSV ghi UTF-8-BOM.

Chạy:
    python scripts/courseware/generate_kpim_bank.py
    python scripts/courseware/generate_kpim_bank.py --validate
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import shutil
import statistics
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SEED = 20260721

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SRC = Path(
    r"<ORG-DOCS-PATH>\General"
    r"\01_COURSE_MATERIAL\MKA-101_Marketing_Analytics\04_PRACTICE_LAB\Data"
    r"\KPIM Bank Marketing Data"
)

FB_SUMMARY = "Facebook Post Summary.csv"
FB_DAILY = "Facebook Post Daily.csv"
XLSX = "KPIM_Bank_Marketing_Plan.xlsx"

# ── ánh xạ theo templates/schema/crosswalk.yml ──────────────────────────────
FORMAT_MAP = {
    "Ảnh": "fb_post",
    "Video": "long_video",
    "Thước phim": "fb_reel",
    "Liên kết": "fb_post",
}
APPROVAL_TO_STATUS = {
    "Draft": "drafted",
    "Need Review": "need_review",
    "Approved": "approved",
    "Need Revision": "drafted",
    "Rejected": "rejected",
}
PILLARS = ["Product", "Education", "Promo", "HowTo", "Testimonial", "Brand"]
PILLAR_META = {
    # pillar_code: (pillar_name, goal, target_share, crosswalk_personal, funnel_stage, cta_type)
    "Product": ("Sản phẩm", "Giới thiệu tính năng & quyền lợi sản phẩm", 0.22, "A", "conversion", "register"),
    "Education": ("Kiến thức tài chính", "Nâng hiểu biết tài chính, xây niềm tin", 0.22, "B", "consumption", "link_click"),
    "Promo": ("Ưu đãi", "Thúc đẩy hành động ngắn hạn bằng ưu đãi", 0.25, "C", "business", "register"),
    "HowTo": ("Hướng dẫn", "Gỡ rào cản thao tác, giảm ma sát mở sản phẩm", 0.15, "D", "consumption", "link_click"),
    "Testimonial": ("Khách hàng nói gì", "Bằng chứng xã hội từ khách hàng thật", 0.10, "E", "engagement", "comment"),
    "Brand": ("Thương hiệu", "Giữ độ nhận biết và cảm tình thương hiệu", 0.06, "F", "discovery", "none"),
}

# ── TÍN HIỆU cố ý cài vào dữ liệu ───────────────────────────────────────────
# Signal #2: Promo click nhiều nhưng lead/click thấp nhất (bẫy kinh điển)
PILLAR_LEAD_PER_CLICK = {
    "Promo": 0.18,
    "Brand": 0.30,
    "Product": 0.62,
    "Testimonial": 0.66,
    "Education": 0.78,
    "HowTo": 0.85,
}
# Signal #3: Education + HowTo cho lead chất lượng cao nhất
PILLAR_HOT_RATE = {
    "HowTo": 0.46,
    "Education": 0.42,
    "Product": 0.28,
    "Testimonial": 0.26,
    "Brand": 0.11,
    "Promo": 0.10,
}
# Signal #4: Q3 hụt target_leads rõ rệt
CAMPAIGN_LEAD_ACHIEVEMENT = {
    "CMP-2026-Q1": 1.020,
    "CMP-2026-Q2": 0.965,
    "CMP-2026-Q3": 0.676,   # ← hụt hẳn, trang "KPI vs Actual" có chuyện để kể
    "CMP-2026-Q4": 0.990,
}
# Signal #5: YouTube reach thấp hơn Facebook nhưng subs/1000 view tốt hơn
YT_VIEW_RATIO = {"long_video": (0.30, 0.46), "fb_reel": (0.18, 0.30), "fb_post": (0.20, 0.32)}
YT_SUBS_PER_1000 = (4.0, 9.0)

REGIONS = {
    "Miền Bắc": ["CN Hà Nội - Ba Đình", "CN Hà Nội - Cầu Giấy", "CN Hải Phòng", "CN Bắc Ninh"],
    "Miền Trung": ["CN Đà Nẵng", "CN Huế", "CN Nha Trang"],
    "Miền Nam": ["CN TP.HCM - Quận 1", "CN TP.HCM - Thủ Đức", "CN Bình Dương", "CN Cần Thơ"],
}
REGION_WEIGHTS = [0.38, 0.17, 0.45]

NEED_TYPES = ["Mở mới", "Tư vấn sản phẩm", "So sánh sản phẩm", "Hỗ trợ hồ sơ", "Hỏi ưu đãi"]
NEED_WEIGHTS = [0.34, 0.26, 0.14, 0.16, 0.10]
LEAD_STATUS_VI = ["Mới", "Đang liên hệ", "Đã tư vấn", "Chuyển hồ sơ", "Thành công", "Không liên hệ được"]
LEAD_STATUS_W = [0.28, 0.22, 0.18, 0.12, 0.12, 0.08]
LEAD_STATUS_EN = {
    "Mới": "new", "Đang liên hệ": "contacting", "Đã tư vấn": "consulted",
    "Chuyển hồ sơ": "submitted", "Thành công": "won", "Không liên hệ được": "unreachable",
}
SEGMENT_VI = {"hot": "Nóng", "warm": "Ấm", "nurture": "Cần nuôi", "low_priority": "Ưu tiên thấp"}

CAMPAIGN_PRODUCT = {
    "CMP-2026-Q1": "Thẻ tín dụng hoàn tiền",
    "CMP-2026-Q2": "Vay mua nhà",
    "CMP-2026-Q3": "App số & Tiết kiệm online",
    "CMP-2026-Q4": "Tài khoản lương",
}
CAMPAIGN_PERSONA = {
    "CMP-2026-Q1": ("Nhân viên văn phòng 25-35 tuổi, chi tiêu thẻ đều",
                    "Người mới mở thẻ tín dụng lần đầu"),
    "CMP-2026-Q2": ("Gia đình trẻ 30-40 tuổi mua căn nhà đầu tiên",
                    "Khách chuyển khoản vay từ ngân hàng khác"),
    "CMP-2026-Q3": ("Người trẻ 22-30 tuổi quen dùng app, ngại ra quầy",
                    "Khách gửi tiết kiệm nhỏ lẻ định kỳ"),
    "CMP-2026-Q4": ("Người đi làm nhận lương qua tài khoản",
                    "Doanh nghiệp SME cần dịch vụ trả lương"),
}
CAMPAIGN_KEY_MESSAGE = {
    "CMP-2026-Q1": "Hoàn tiền đến 8% cho chi tiêu hằng ngày — không cần đổi thói quen.",
    "CMP-2026-Q2": "Lãi suất ưu đãi cố định 24 tháng, hồ sơ duyệt trong 5 ngày làm việc.",
    "CMP-2026-Q3": "Mở sổ tiết kiệm online trong 3 phút, lãi suất cao hơn quầy 0,3%/năm.",
    "CMP-2026-Q4": "Tài khoản lương miễn phí trọn gói + ưu đãi chi tiêu Tết.",
}
CAMPAIGN_TONE = {
    "CMP-2026-Q1": "Gần gũi, thực dụng, tránh thuật ngữ tài chính khó",
    "CMP-2026-Q2": "Tin cậy, điềm đạm, nhấn vào an tâm dài hạn",
    "CMP-2026-Q3": "Trẻ, nhanh, ưu tiên demo thao tác",
    "CMP-2026-Q4": "Ấm áp dịp Tết, nhấn vào tiện lợi và quà tặng",
}
COMPLIANCE_BASE = [
    "Mọi con số lãi suất/hoàn tiền phải kèm điều kiện áp dụng và thời hạn hiệu lực.",
    "Không dùng từ tuyệt đối: 'cao nhất thị trường', 'duy nhất', 'cam kết sinh lời'.",
    "Không hiển thị thông tin định danh khách hàng (số thẻ, CCCD, số tài khoản) trong ảnh/video.",
    "Nội dung testimonial phải có văn bản đồng ý của khách hàng lưu tại phòng Pháp chế.",
    "Bài Promo bắt buộc gắn dòng 'Điều kiện & điều khoản áp dụng' và link Biểu phí.",
]

CAPTION_TPL = {
    "Product": "{title}. KPIM Bank thiết kế sản phẩm này cho nhu cầu thật của bạn — xem đầy đủ quyền lợi, biểu phí và điều kiện áp dụng trước khi đăng ký. {cta}.",
    "Education": "{title}? Cùng KPIM Bank hiểu đúng trong 2 phút để không mất tiền oan vì hiểu nhầm. {cta}.",
    "Promo": "{title}! Ưu đãi có giới hạn theo ngân sách chương trình, điều kiện & điều khoản áp dụng. {cta}.",
    "HowTo": "{title} — làm theo từng bước dưới đây, chỉ mất vài phút và không cần ra quầy. {cta}.",
    "Testimonial": "{title}. Câu chuyện có thật từ khách hàng KPIM Bank, chia sẻ với sự đồng ý của chủ tài khoản. {cta}.",
    "Brand": "{title}. Cảm ơn bạn đã đồng hành cùng KPIM Bank. {cta}.",
}
HASHTAGS = {
    "Product": "#KPIMBank #SanPhamKPIM",
    "Education": "#KPIMBank #HieuVeTien",
    "Promo": "#KPIMBank #UuDaiKPIM",
    "HowTo": "#KPIMBank #HuongDanNhanh",
    "Testimonial": "#KPIMBank #KhachHangKPIM",
    "Brand": "#KPIMBank",
}
# tiêu đề cho các bài KẾ HOẠCH bổ sung (chưa đăng) — mỗi quý 10 bài
PLANNED_TITLES = {
    "CMP-2026-Q1": [
        ("Product", "Ảnh", "Hạn mức thẻ Cashback: ai được cấp bao nhiêu?"),
        ("Education", "Video", "Sao kê thẻ tín dụng: đọc thế nào cho đúng"),
        ("Promo", "Thước phim", "Tuần lễ hoàn tiền siêu thị – tối đa 500.000đ"),
        ("HowTo", "Video", "Kích hoạt thẻ Cashback ngay trên app trong 2 phút"),
        ("Testimonial", "Ảnh", "Chị Lan tiết kiệm 3,2 triệu/năm nhờ hoàn tiền"),
        ("Brand", "Ảnh", "KPIM Bank và cam kết minh bạch phí"),
        ("Promo", "Ảnh", "Mở thẻ trước 31/03 – miễn phí thường niên năm đầu"),
        ("Education", "Ảnh", "Trả góp 0% và những chi phí ẩn cần biết"),
        ("HowTo", "Thước phim", "Cách khoá thẻ khẩn cấp khi nghi ngờ gian lận"),
        ("Product", "Liên kết", "So sánh 3 dòng thẻ Cashback trên một trang"),
    ],
    "CMP-2026-Q2": [
        ("Education", "Video", "Lãi suất thả nổi sau ưu đãi: tính thử cho dễ hình dung"),
        ("Product", "Ảnh", "Gói vay mua nhà 25 năm – điều kiện tối thiểu"),
        ("HowTo", "Video", "Chuẩn bị hồ sơ vay mua nhà: checklist 8 giấy tờ"),
        ("Promo", "Thước phim", "Ưu đãi lãi suất cố định 24 tháng – đến hết quý"),
        ("Testimonial", "Ảnh", "Vợ chồng anh Minh nhận nhà sau 5 tháng"),
        ("Brand", "Ảnh", "10 năm KPIM Bank đồng hành cùng gia đình Việt"),
        ("Education", "Ảnh", "Nên vay bao nhiêu phần trăm giá trị căn nhà?"),
        ("HowTo", "Thước phim", "Tra cứu tiến độ hồ sơ vay trên app"),
        ("Promo", "Ảnh", "Miễn phí định giá tài sản trong tháng 6"),
        ("Product", "Liên kết", "Công cụ tính khoản trả hằng tháng"),
    ],
    "CMP-2026-Q3": [
        ("HowTo", "Video", "Mở sổ tiết kiệm online trong 3 phút"),
        ("Product", "Ảnh", "KPIM Digital: 5 việc làm được ngay trên app"),
        ("Education", "Video", "Tiết kiệm online và tiết kiệm tại quầy khác nhau ra sao"),
        ("Promo", "Thước phim", "Nạp app lần đầu – tặng 50.000đ vào ví"),
        ("Testimonial", "Ảnh", "Bạn Trang gửi tiết kiệm mỗi tháng bằng app"),
        ("Brand", "Ảnh", "Bảo mật app KPIM: 3 lớp xác thực"),
        ("Education", "Ảnh", "Lãi kép: vì sao gửi sớm hơn quan trọng hơn gửi nhiều"),
        ("HowTo", "Thước phim", "Đặt lệnh tiết kiệm tự động hằng tháng"),
        ("Promo", "Ảnh", "Ưu đãi lãi suất kỳ hạn 6 tháng cho khách mới"),
        ("Product", "Liên kết", "Bảng lãi suất tiết kiệm online cập nhật"),
    ],
    "CMP-2026-Q4": [
        ("Product", "Ảnh", "Tài khoản lương KPIM: miễn phí trọn gói"),
        ("Education", "Video", "Lập ngân sách chi tiêu Tết trong 15 phút"),
        ("Promo", "Thước phim", "Chi tiêu Tết không tiền mặt – hoàn tiền mỗi tuần"),
        ("HowTo", "Video", "Chuyển tài khoản nhận lương sang KPIM Bank"),
        ("Testimonial", "Ảnh", "Công ty ABC chuyển 240 nhân sự sang trả lương KPIM"),
        ("Brand", "Ảnh", "Lời chúc năm mới từ KPIM Bank"),
        ("Education", "Ảnh", "Thưởng Tết nên chia thế nào cho hợp lý"),
        ("HowTo", "Thước phim", "Rút tiền không cần thẻ tại ATM KPIM"),
        ("Promo", "Ảnh", "Ưu đãi lì xì điện tử cho khách tài khoản lương"),
        ("Product", "Liên kết", "Đăng ký dịch vụ trả lương cho doanh nghiệp"),
    ],
}
PLANNED_CTA = {
    "Product": "Tìm hiểu thêm", "Education": "Xem thêm", "Promo": "Đăng ký ngay",
    "HowTo": "Xem hướng dẫn", "Testimonial": "Xem thêm", "Brand": "Theo dõi KPIM Bank",
}

REVIEWERS = ["Nguyễn Thu Hà (Marketing Lead)", "Trần Quốc Anh (Compliance)",
             "Lê Minh Châu (Content Lead)", "Phạm Hải Yến (Brand)"]

# ── nhiễu cố ý (số lượng khai báo — validate đếm lại đúng bằng số này) ──────
NOISE_MISSING_MEDIA = 5      # dòng thiếu media_link
NOISE_BAD_DATE = 3           # dòng schedule_date sai định dạng (dd/MM/yyyy)
NOISE_DUP_ROWS = 2           # dòng lặp asset_id
LEAD_DUP_RATE = 0.04         # ~4% lead trùng người, khác nguồn


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════
def w(path: Path, rows: list[dict], fieldnames: list[str]) -> int:
    """Ghi CSV UTF-8 có BOM (Excel tiếng Việt mở không lỗi font)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    return len(rows)


def wtext(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def to_int(v) -> int:
    if v is None:
        return 0
    s = str(v).strip().replace(",", "")
    if not s:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def largest_remainder(weights: list[float], total: int) -> list[int]:
    """Chia `total` theo `weights` sao cho tổng phần chia == total (không lệch do làm tròn)."""
    s = sum(weights)
    if s <= 0:
        base = [total // len(weights)] * len(weights)
        for i in range(total - sum(base)):
            base[i % len(base)] += 1
        return base
    raw = [total * x / s for x in weights]
    out = [int(x) for x in raw]
    rem = total - sum(out)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)
    for i in range(rem):
        out[order[i % len(order)]] += 1
    return out


def pick(rng: random.Random, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


# ════════════════════════════════════════════════════════════════════════════
# 1. Đọc nguồn
# ════════════════════════════════════════════════════════════════════════════
def load_sources(src_dir: Path) -> dict:
    """Copy xlsx/csv ra %TEMP% rồi mới đọc (nguồn nằm trên OneDrive → tránh treo/khoá file)."""
    import openpyxl

    tmp = Path(tempfile.mkdtemp(prefix="kpim_src_"))
    for name in (XLSX, FB_SUMMARY, FB_DAILY):
        s = src_dir / name
        if not s.exists():
            raise SystemExit(f"[FATAL] Không thấy file nguồn: {s}")
        shutil.copy2(s, tmp / name)

    wb = openpyxl.load_workbook(tmp / XLSX, data_only=True)

    def sheet_dicts(name):
        ws = wb[name]
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(c) for c in rows[0]]
        return [dict(zip(hdr, r)) for r in rows[1:] if r[0] is not None]

    campaigns = sheet_dicts("Campaign")
    posts = sheet_dicts("Post")
    wb.close()

    with (tmp / FB_SUMMARY).open(encoding="utf-8-sig") as fh:
        fb_summary = list(csv.DictReader(fh))
    with (tmp / FB_DAILY).open(encoding="utf-8-sig") as fh:
        fb_daily = list(csv.DictReader(fh))

    return {"tmp": tmp, "campaigns": campaigns, "posts": posts,
            "fb_summary": fb_summary, "fb_daily": fb_daily}


# ════════════════════════════════════════════════════════════════════════════
# 2. Calendar (★a)
# ════════════════════════════════════════════════════════════════════════════
CALENDAR_FIELDS = [
    "asset_id", "post_code", "campaign_id", "quarter",
    "planned_publish_date", "schedule_date",
    "pillar_code", "format_source", "format", "funnel_stage",
    "platform_primary", "on_facebook", "on_youtube",
    "title", "caption", "media_link",
    "cta_label", "cta_type",
    "approval_status", "status", "is_published",
    "platform_native_id_fb", "platform_native_id_yt",
    "owner",
]


def make_caption(pillar: str, title: str, cta: str) -> str:
    t = title.rstrip(".!?").strip()
    body = CAPTION_TPL[pillar].format(title=t, cta=cta)
    return f"{body} {HASHTAGS[pillar]}"


def build_calendar(rng: random.Random, src: dict) -> tuple[list[dict], list[dict]]:
    """Trả về (logical_rows, physical_rows). physical = logical + 2 dòng lặp asset_id."""
    campaigns = {c["campaign_id"]: c for c in src["campaigns"]}
    rows: list[dict] = []

    # --- 60 bài ĐÃ ĐĂNG (từ sheet Post) ---
    for p in src["posts"]:
        pillar = p["content_pillar"]
        fmt_src = p["format"]
        rows.append({
            "asset_id": p["post_code"],
            "post_code": p["post_code"],
            "campaign_id": p["campaign_id"],
            "quarter": p["quarter"],
            "planned_publish_date": str(p["planned_date"])[:10],
            "schedule_date": "",
            "pillar_code": pillar,
            "format_source": fmt_src,
            "format": FORMAT_MAP[fmt_src],
            "funnel_stage": PILLAR_META[pillar][4],
            "platform_primary": "youtube" if p.get("yt_video_id") else "facebook",
            "on_facebook": "Y" if p.get("on_facebook") else "N",
            "on_youtube": "Y" if p.get("yt_video_id") else "N",
            "title": p["title"],
            "caption": make_caption(pillar, p["title"], p["cta"]),
            "media_link": "",
            "cta_label": p["cta"],
            "cta_type": PILLAR_META[pillar][5],
            "approval_status": "Approved",      # đã đăng thật ⇒ chắc chắn đã duyệt
            "status": "published",
            "is_published": "Y",
            "platform_native_id_fb": str(p["fb_post_id"] or ""),
            "platform_native_id_yt": str(p.get("yt_video_id") or ""),
            "owner": p["owner"],
        })

    # --- 40 bài KẾ HOẠCH (10/quý) — nơi chứa các trạng thái duyệt khác ---
    # 100 dòng logic ⇒ 70 Approved / 12 Need Review / 10 Draft / 5 Need Revision / 3 Rejected.
    # 60 Approved đã dùng cho bài đã đăng ⇒ 40 bài kế hoạch nhận:
    plan_statuses = (["Approved"] * 10 + ["Need Review"] * 12 + ["Draft"] * 10
                     + ["Need Revision"] * 5 + ["Rejected"] * 3)
    assert len(plan_statuses) == 40
    rng.shuffle(plan_statuses)

    si = 0
    for cid in sorted(campaigns):
        c = campaigns[cid]
        q = c["quarter"]
        end = datetime.strptime(str(c["end_date"])[:10], "%Y-%m-%d").date()
        for i, (pillar, fmt_src, title) in enumerate(PLANNED_TITLES[cid], start=16):
            # rải trong 3 tuần cuối quý + 2 tuần sau khi quý kết thúc (đợt bổ sung)
            d = end - timedelta(days=18) + timedelta(days=i - 16) * 3
            appr = plan_statuses[si]
            si += 1
            aid = f"P-{q}-{i}"
            rows.append({
                "asset_id": aid,
                "post_code": aid,
                "campaign_id": cid,
                "quarter": q,
                "planned_publish_date": d.isoformat(),
                "schedule_date": "",
                "pillar_code": pillar,
                "format_source": fmt_src,
                "format": FORMAT_MAP[fmt_src],
                "funnel_stage": PILLAR_META[pillar][4],
                "platform_primary": "youtube" if fmt_src == "Video" else "facebook",
                "on_facebook": "Y",
                "on_youtube": "Y" if fmt_src == "Video" else "N",
                "title": title,
                "caption": make_caption(pillar, title, PLANNED_CTA[pillar]),
                "media_link": "",
                "cta_label": PLANNED_CTA[pillar],
                "cta_type": PILLAR_META[pillar][5],
                "approval_status": appr,
                "status": APPROVAL_TO_STATUS[appr],
                "is_published": "N",
                "platform_native_id_fb": "",
                "platform_native_id_yt": "",
                "owner": c["owner"],
            })

    # --- media_link + schedule_date ---
    for r in rows:
        ext = "mp4" if r["format_source"] in ("Video", "Thước phim") else "jpg"
        r["media_link"] = f"media/{r['quarter']}/{r['asset_id']}.{ext}"
        d = datetime.strptime(r["planned_publish_date"], "%Y-%m-%d").date()
        sd = d + timedelta(days=rng.choice([0, 0, 0, 1, 2]))
        r["schedule_date"] = sd.isoformat()

    # --- NHIỄU 1: 5 dòng thiếu media_link (rải đều 4 quý, ưu tiên bài kế hoạch) ---
    cand = [r for r in rows if r["is_published"] == "N"]
    for r in rng.sample(cand, NOISE_MISSING_MEDIA):
        r["media_link"] = ""

    # --- NHIỄU 2: 3 dòng schedule_date sai định dạng dd/MM/yyyy ---
    for r in rng.sample(rows, NOISE_BAD_DATE):
        d = datetime.strptime(r["schedule_date"], "%Y-%m-%d").date()
        r["schedule_date"] = d.strftime("%d/%m/%Y")

    logical = rows
    # --- NHIỄU 3: 2 dòng lặp asset_id (bản sao gần-giống, lệch schedule_date) ---
    # Chỉ nhân bản dòng có schedule_date ISO + media_link đầy đủ, để 2 nhiễu kia
    # không bị đếm lặp theo (media rỗng vẫn đúng 5, ngày sai vẫn đúng 3).
    dup_src = [r for r in rows if r["campaign_id"] in ("CMP-2026-Q2", "CMP-2026-Q3")
               and r["is_published"] == "Y" and "/" not in r["schedule_date"]
               and r["media_link"]]
    dups = []
    for r in rng.sample(dup_src, NOISE_DUP_ROWS):
        d = dict(r)
        dt = datetime.strptime(d["schedule_date"], "%Y-%m-%d").date()
        d["schedule_date"] = (dt + timedelta(days=1)).isoformat()
        d["_is_dup"] = "Y"
        dups.append(d)

    physical = logical + dups
    physical.sort(key=lambda r: (r["campaign_id"], r["asset_id"], r.get("_is_dup", "")))
    return logical, physical


# ════════════════════════════════════════════════════════════════════════════
# 3. YouTube export (★c)
# ════════════════════════════════════════════════════════════════════════════
YT_FIELDS = ["video_id", "post_id", "campaign_id", "publish_date", "title", "views",
             "impressions", "ctr", "avg_view_duration_sec", "avg_percentage_viewed",
             "watch_time_min", "likes", "comments", "shares", "subscribers_gained"]


def build_youtube(rng: random.Random, src: dict, fb_by_id: dict) -> list[dict]:
    out = []
    for p in src["posts"]:
        vid = p.get("yt_video_id")
        if not vid:
            continue
        fb = fb_by_id[str(p["fb_post_id"])]
        fb_reach = to_int(fb["Số người tiếp cận"])
        fmt = FORMAT_MAP[p["format"]]
        lo, hi = YT_VIEW_RATIO[fmt]
        views = max(120, int(fb_reach * rng.uniform(lo, hi)))          # Signal #5: YT < FB
        ctr = round(rng.uniform(0.035, 0.092), 4)
        impressions = int(views / ctr)
        dur = rng.randint(150, 420) if fmt == "long_video" else rng.randint(28, 58)
        pct = rng.uniform(0.34, 0.62) if fmt == "long_video" else rng.uniform(0.52, 0.85)
        avd = round(dur * pct, 1)
        out.append({
            "video_id": vid,
            "post_id": p["post_code"],
            "campaign_id": p["campaign_id"],
            "publish_date": str(p["planned_date"])[:10],
            "title": p["title"],
            "views": views,
            "impressions": impressions,
            "ctr": ctr,
            "avg_view_duration_sec": avd,
            "avg_percentage_viewed": round(pct * 100, 1),
            "watch_time_min": round(views * avd / 60, 1),
            "likes": int(views * rng.uniform(0.021, 0.052)),
            "comments": int(views * rng.uniform(0.0018, 0.0062)),
            "shares": int(views * rng.uniform(0.0025, 0.0095)),
            "subscribers_gained": max(1, int(views / 1000 * rng.uniform(*YT_SUBS_PER_1000))),
        })
    return out


# ════════════════════════════════════════════════════════════════════════════
# 4. Leads (★b) — 7 file schema LỆCH NHAU
# ════════════════════════════════════════════════════════════════════════════
SRC_PREFIX = {"app": "APP", "hotline": "HL", "form": "FRM", "social_inbox": "SIB",
              "website": "WEB", "branch": "BRC", "qr_event": "QR"}
ATTR_SOURCE_W = {"form": 0.30, "website": 0.24, "social_inbox": 0.16,
                 "app": 0.14, "qr_event": 0.08, "hotline": 0.08}
NONATTR_SOURCE_W = {"branch": 0.34, "hotline": 0.22, "app": 0.18, "website": 0.10,
                    "form": 0.08, "qr_event": 0.05, "social_inbox": 0.03}


def build_leads(rng: random.Random, src: dict, calendar: list[dict], fb_by_id: dict):
    campaigns = {c["campaign_id"]: c for c in src["campaigns"]}
    pub = [r for r in calendar if r["is_published"] == "Y"]

    # 4.1 lead có gắn post (attributed) — theo cta_click × tỷ lệ chuyển của pillar
    attributed_plan: list[tuple[dict, int]] = []
    for r in pub:
        fb = fb_by_id[r["platform_native_id_fb"]]
        clicks = to_int(fb["Lượt click vào liên kết"])
        rate = PILLAR_LEAD_PER_CLICK[r["pillar_code"]]
        ach = CAMPAIGN_LEAD_ACHIEVEMENT[r["campaign_id"]]
        n = int(round(clicks * rate * ach * rng.uniform(0.82, 1.18)))
        if n > 0:
            attributed_plan.append((r, n))

    # 4.2 tổng lead theo campaign (Signal #4: Q3 hụt hẳn)
    campaign_total = {cid: int(round(to_int(c["target_leads"]) * CAMPAIGN_LEAD_ACHIEVEMENT[cid]))
                      for cid, c in campaigns.items()}
    attr_by_c = defaultdict(int)
    for r, n in attributed_plan:
        attr_by_c[r["campaign_id"]] += n

    leads: list[dict] = []
    seq = 0
    people: list[dict] = []   # để tạo lead trùng

    def region_branch():
        reg = pick(rng, list(REGIONS), REGION_WEIGHTS)
        return reg, rng.choice(REGIONS[reg])

    def new_lead(cid, post_row, source, when: datetime, pillar):
        nonlocal seq
        seq += 1
        reg, br = region_branch()
        hot_rate = PILLAR_HOT_RATE.get(pillar, 0.18)
        seg = pick(rng, ["hot", "warm", "nurture", "low_priority"],
                   [hot_rate, 0.34, 0.30, max(0.04, 1 - hot_rate - 0.64)])
        person_id = seq
        phone = "09" + f"{rng.randint(0, 99999999):08d}"
        rec = {
            "seq": seq,
            "lead_id": f"{SRC_PREFIX[source]}-{seq:05d}",
            "source": source,
            "created_at": when,
            "campaign_id": cid,
            "post_id": post_row["asset_id"] if post_row else "",
            "fb_post_id": post_row["platform_native_id_fb"] if post_row else "",
            "pillar_code": pillar or "",
            "product_interest": (CAMPAIGN_PRODUCT[cid] if rng.random() > 0.12
                                 else rng.choice(list(CAMPAIGN_PRODUCT.values()))),
            "region": reg,
            "branch": br,
            "need_type": pick(rng, NEED_TYPES, NEED_WEIGHTS),
            "lead_status": pick(rng, LEAD_STATUS_VI, LEAD_STATUS_W),
            "lead_segment": seg,
            "phone": phone,
            "name": f"Khách hàng {person_id:04d}",
            "person_key": person_id,
        }
        leads.append(rec)
        people.append(rec)
        return rec

    # 4.3 sinh lead attributed
    for r, n in attributed_plan:
        base = datetime.strptime(r["planned_publish_date"], "%Y-%m-%d")
        srcs = list(ATTR_SOURCE_W)
        wts = [ATTR_SOURCE_W[s] for s in srcs]
        for _ in range(n):
            when = base + timedelta(days=rng.randint(0, 21),
                                    hours=rng.randint(7, 22), minutes=rng.randint(0, 59))
            new_lead(r["campaign_id"], r, pick(rng, srcs, wts), when, r["pillar_code"])

    # 4.4 sinh lead KHÔNG gắn post cho đủ tổng campaign
    srcs = list(NONATTR_SOURCE_W)
    wts = [NONATTR_SOURCE_W[s] for s in srcs]
    for cid, c in campaigns.items():
        need = campaign_total[cid] - attr_by_c[cid]
        start = datetime.strptime(str(c["start_date"])[:10], "%Y-%m-%d")
        end = datetime.strptime(str(c["end_date"])[:10], "%Y-%m-%d")
        span = (end - start).days
        for _ in range(max(0, need)):
            when = start + timedelta(days=rng.randint(0, span),
                                     hours=rng.randint(8, 20), minutes=rng.randint(0, 59))
            new_lead(cid, None, pick(rng, srcs, wts), when, "")

    # 4.5 ~4% lead TRÙNG: cùng người, nguồn khác, lệch vài giờ (bài dedupe)
    n_dup = int(round(len(leads) * LEAD_DUP_RATE))
    for orig in rng.sample(people, n_dup):
        seq += 1
        other = [s for s in SRC_PREFIX if s != orig["source"]]
        s2 = rng.choice(other)
        d = dict(orig)
        d["seq"] = seq
        d["lead_id"] = f"{SRC_PREFIX[s2]}-{seq:05d}"
        d["source"] = s2
        d["created_at"] = orig["created_at"] + timedelta(hours=rng.randint(1, 60))
        d["lead_status"] = pick(rng, LEAD_STATUS_VI, LEAD_STATUS_W)
        d["_dup_of"] = orig["lead_id"]
        if s2 == "branch":
            d["post_id"] = ""
            d["fb_post_id"] = ""
        leads.append(d)

    leads.sort(key=lambda x: (x["created_at"], x["lead_id"]))
    return leads, campaign_total


def fmt_phone(rng: random.Random, phone: str, style: str) -> str:
    p = phone
    if style == "plain":
        return p
    if style == "dash":
        return f"{p[:4]}-{p[4:7]}-{p[7:]}"
    if style == "intl":
        return f"+84 {p[1:4]} {p[4:7]} {p[7:]}"
    if style == "space":
        return f"{p[:4]} {p[4:7]} {p[7:]}"
    return p


def write_leads(rng: random.Random, leads: list[dict], out_raw: Path) -> dict[str, int]:
    """7 file, 7 schema khác nhau — tên cột, định dạng ngày, cột thừa/thiếu đều lệch."""
    by = defaultdict(list)
    for l in leads:
        by[l["source"]].append(l)
    counts = {}
    d = out_raw / "leads"

    # (1) app — snake_case tiếng Việt, ngày = epoch MILLIgiây, có app_version thừa
    rows = []
    for l in by["app"]:
        rows.append({
            "lead_id": l["lead_id"],
            "ma_chien_dich": l["campaign_id"],
            "ma_bai_viet": l["fb_post_id"],           # nối qua fb_post_id
            "sdt": fmt_phone(rng, l["phone"], "plain"),
            "ho_ten": l["name"],
            "created_at": int(l["created_at"].replace(tzinfo=timezone.utc).timestamp() * 1000),
            "san_pham_quan_tam": l["product_interest"],
            "khu_vuc": l["region"],
            "chi_nhanh": l["branch"],
            "nhu_cau": l["need_type"],
            "trang_thai": LEAD_STATUS_EN[l["lead_status"]],
            "phan_loai": l["lead_segment"],
            "app_version": rng.choice(["4.2.1", "4.3.0", "4.3.1", "5.0.0"]),
        })
    counts["lead_app.csv"] = w(d / "lead_app.csv", rows, list(rows[0]))

    # (2) hotline — PascalCase tiếng Anh, ngày dd-MM-yyyy HH:mm, nối qua post_code
    rows = []
    for l in by["hotline"]:
        rows.append({
            "LeadID": l["lead_id"],
            "Phone": fmt_phone(rng, l["phone"], "intl"),
            "CustomerName": l["name"],
            "CallTime": l["created_at"].strftime("%d-%m-%Y %H:%M"),
            "Campaign": l["campaign_id"],
            "PostCode": l["post_id"],                  # nối qua post_code
            "Product": l["product_interest"],
            "Region": l["region"],
            "Branch": l["branch"],
            "NeedType": l["need_type"],
            "Status": l["lead_status"],
            "Segment": l["lead_segment"],
            "AgentName": f"CSKH-{rng.randint(1, 24):02d}",
            "CallDurationSec": rng.randint(45, 620),
        })
    counts["lead_hotline.csv"] = w(d / "lead_hotline.csv", rows, list(rows[0]))

    # (3) form — gần canonical nhất, ngày ISO date (KHÔNG có giờ), có UTM
    rows = []
    for l in by["form"]:
        rows.append({
            "lead_id": l["lead_id"],
            "so_dien_thoai": fmt_phone(rng, l["phone"], "dash"),
            "ten_khach": l["name"],
            "ngay_tao": l["created_at"].date().isoformat(),
            "campaign_id": l["campaign_id"],
            "fb_post_id": l["fb_post_id"],
            "product_interest": l["product_interest"],
            "region": l["region"],
            "branch": l["branch"],
            "need_type": l["need_type"],
            "lead_status": l["lead_status"],
            "lead_segment": l["lead_segment"],
            "utm_source": "facebook" if l["fb_post_id"] else "direct",
            "utm_campaign": l["campaign_id"].lower(),
        })
    counts["lead_form.csv"] = w(d / "lead_form.csv", rows, list(rows[0]))

    # (4) social_inbox — tên cột cụt, THIẾU hẳn cột branch, ngày ISO datetime
    rows = []
    for l in by["social_inbox"]:
        rows.append({
            "id": l["lead_id"],
            "phone": fmt_phone(rng, l["phone"], "space"),
            "name": l["name"],
            "created_at": l["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "campaign": l["campaign_id"],
            "post_id": l["post_id"],
            "product": l["product_interest"],
            "region": l["region"],
            "need": l["need_type"],
            "status": LEAD_STATUS_EN[l["lead_status"]],
            "quality": l["lead_segment"],
            "channel_page": rng.choice(["KPIM Bank", "KPIM Bank - CSKH"]),
        })
    counts["lead_social_inbox.csv"] = w(d / "lead_social_inbox.csv", rows, list(rows[0]))

    # (5) website — ngày = epoch GIÂY, có landing_page + utm_medium
    rows = []
    for l in by["website"]:
        rows.append({
            "lead_id": l["lead_id"],
            "phone_number": fmt_phone(rng, l["phone"], "plain"),
            "full_name": l["name"],
            "created_at": int(l["created_at"].replace(tzinfo=timezone.utc).timestamp()),
            "campaign_id": l["campaign_id"],
            "post_id": l["post_id"],
            "landing_page": f"/lp/{l['campaign_id'].lower()}",
            "product_interest": l["product_interest"],
            "region": l["region"],
            "branch": l["branch"],
            "need_type": l["need_type"],
            "lead_status": LEAD_STATUS_EN[l["lead_status"]],
            "lead_segment": l["lead_segment"],
            "utm_medium": rng.choice(["cpc", "organic", "referral", "email"]),
        })
    counts["lead_website.csv"] = w(d / "lead_website.csv", rows, list(rows[0]))

    # (6) branch — tiếng Việt không dấu PascalCase, ngày dd/MM/yyyy, KHÔNG có post, segment tiếng Việt
    rows = []
    for l in by["branch"]:
        rows.append({
            "MaLead": l["lead_id"],
            "SoDienThoai": fmt_phone(rng, l["phone"], "plain"),
            "HoTen": l["name"],
            "NgayTiepNhan": l["created_at"].strftime("%d/%m/%Y"),
            "MaChienDich": l["campaign_id"],
            "MaBaiViet": "",                            # quầy không biết bài nào
            "SanPham": l["product_interest"],
            "Vung": l["region"],
            "ChiNhanh": l["branch"],
            "NhuCau": l["need_type"],
            "TrangThai": l["lead_status"],
            "PhanLoai": SEGMENT_VI[l["lead_segment"]],  # nhãn tiếng Việt — phải chuẩn hoá
            "GiaoDichVien": f"GDV-{rng.randint(1, 60):03d}",
        })
    counts["lead_branch.csv"] = w(d / "lead_branch.csv", rows, list(rows[0]))

    # (7) qr_event — ngày ISO8601 có Z (UTC), có event_name + qr_code_id
    rows = []
    for l in by["qr_event"]:
        rows.append({
            "lead_id": l["lead_id"],
            "sdt": fmt_phone(rng, l["phone"], "dash"),
            "ten": l["name"],
            "scan_time": l["created_at"].replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "campaign_id": l["campaign_id"],
            "post_id": l["post_id"],
            "product": l["product_interest"],
            "region": l["region"],
            "branch": l["branch"],
            "need_type": l["need_type"],
            "status": l["lead_status"],
            "segment": l["lead_segment"],
            "event_name": rng.choice(["Hội chợ tài chính", "Ngày hội khách hàng",
                                      "Roadshow chi nhánh", "Sự kiện toà nhà văn phòng"]),
            "qr_code_id": f"QR-{rng.randint(1, 40):03d}",
        })
    counts["lead_qr_event.csv"] = w(d / "lead_qr_event.csv", rows, list(rows[0]))
    return counts


# ════════════════════════════════════════════════════════════════════════════
# 5. kpi_target (★d) + cost_by_post
# ════════════════════════════════════════════════════════════════════════════
KPI_FIELDS = ["campaign_id", "platform", "pillar_code", "format", "metric_name", "period",
              "target_value", "unit", "baseline_median", "baseline_source", "baseline_n"]
FORMAT_REACH_W = {"fb_reel": 3.0, "long_video": 2.0, "fb_post": 1.2}


def build_kpi_target(src: dict, calendar: list[dict], fb_by_id: dict, yt: list[dict]):
    campaigns = {c["campaign_id"]: c for c in src["campaigns"]}
    yt_by_post = {y["post_id"]: y for y in yt}

    # (platform, pillar, period) → danh sách asset
    cells: dict[str, dict[tuple, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in calendar:
        period = r["planned_publish_date"][:7]
        for plat, flag in (("facebook", r["on_facebook"]), ("youtube", r["on_youtube"])):
            if flag == "Y":
                cells[r["campaign_id"]][(plat, r["pillar_code"], period)].append(r)

    # thực tế theo (platform, pillar) để tính baseline_median cho quý sau
    hist_reach: dict[tuple, list[tuple[str, int]]] = defaultdict(list)
    hist_leads: dict[tuple, list[tuple[str, int]]] = defaultdict(list)
    for r in calendar:
        if r["is_published"] != "Y":
            continue
        q = r["quarter"]
        fb = fb_by_id[r["platform_native_id_fb"]]
        hist_reach[("facebook", r["pillar_code"])].append((q, to_int(fb["Số người tiếp cận"])))
        if r["on_youtube"] == "Y" and r["asset_id"] in yt_by_post:
            hist_reach[("youtube", r["pillar_code"])].append(
                (q, yt_by_post[r["asset_id"]]["views"]))

    q_order = ["Q1", "Q2", "Q3", "Q4"]

    def baseline(plat, pillar, quarter, store):
        prior = [v for (q, v) in store.get((plat, pillar), [])
                 if q_order.index(q) < q_order.index(quarter)]
        prior = prior[-10:]
        if not prior:
            return "", "", 0
        src_name = "fb_post_summary_median" if plat == "facebook" else "youtube_export_median"
        return int(statistics.median(prior)), src_name, len(prior)

    rows = []
    for cid in sorted(campaigns):
        c = campaigns[cid]
        quarter = c["quarter"]
        keys = sorted(cells[cid])
        # -- reach --
        wts = [sum(FORMAT_REACH_W[a["format"]] for a in cells[cid][k]) *
               (0.55 if k[0] == "youtube" else 1.0) for k in keys]
        vals = largest_remainder(wts, to_int(c["target_reach"]))
        for k, v in zip(keys, vals):
            plat, pillar, period = k
            bm, bs, bn = baseline(plat, pillar, quarter, hist_reach)
            rows.append({"campaign_id": cid, "platform": plat, "pillar_code": pillar,
                         "format": "", "metric_name": "reach", "period": period,
                         "target_value": v, "unit": "người",
                         "baseline_median": bm, "baseline_source": bs, "baseline_n": bn})
        # -- leads (chỉ Facebook + kênh có CTA thu lead) --
        lkeys = [k for k in keys if k[0] == "facebook"]
        lw = [len(cells[cid][k]) * PILLAR_LEAD_PER_CLICK[k[1]] * 10 for k in lkeys]
        lvals = largest_remainder(lw, to_int(c["target_leads"]))
        for k, v in zip(lkeys, lvals):
            plat, pillar, period = k
            bm, bs, bn = baseline(plat, pillar, quarter, hist_leads)
            rows.append({"campaign_id": cid, "platform": plat, "pillar_code": pillar,
                         "format": "", "metric_name": "leads", "period": period,
                         "target_value": v, "unit": "lead",
                         "baseline_median": bm, "baseline_source": bs, "baseline_n": bn})
    return rows


COST_FIELDS = ["post_id", "campaign_id", "period", "format", "pillar_code",
               "cost", "currency", "allocation_method", "allocation_weight"]
FORMAT_COST_W = {"long_video": 3.2, "fb_reel": 2.4, "fb_post": 1.0}


def build_cost(src: dict, calendar: list[dict]) -> list[dict]:
    campaigns = {c["campaign_id"]: c for c in src["campaigns"]}
    rows = []
    for cid in sorted(campaigns):
        assets = [r for r in calendar if r["campaign_id"] == cid]
        wts = [FORMAT_COST_W[a["format"]] for a in assets]
        vals = largest_remainder(wts, to_int(campaigns[cid]["budget_vnd"]))
        for a, v in zip(assets, vals):
            rows.append({
                "post_id": a["asset_id"], "campaign_id": cid,
                "period": a["planned_publish_date"][:7], "format": a["format"],
                "pillar_code": a["pillar_code"], "cost": v, "currency": "VND",
                "allocation_method": "budget_vnd chia theo trọng số định dạng (video 3.2 · reel 2.4 · ảnh 1.0)",
                "allocation_weight": FORMAT_COST_W[a["format"]],
            })
    return rows


# ════════════════════════════════════════════════════════════════════════════
# 6. execution_log (★e) · content_review (★f) · cta_lead_bridge (★g)
# ════════════════════════════════════════════════════════════════════════════
EXEC_FIELDS = ["run_id", "post_id", "channel", "processed_timestamp", "status",
               "error_message", "draft_link"]


def build_execution_log(rng: random.Random, physical_calendar: list[dict]) -> list[dict]:
    rows = []
    seen: set[str] = set()
    n = 0
    base = datetime(2026, 7, 20, 6, 0, 0)
    for r in sorted(physical_calendar, key=lambda x: (x["campaign_id"], x["asset_id"],
                                                      x.get("_is_dup", ""))):
        channels = []
        if r["on_facebook"] == "Y":
            channels.append("facebook")
        if r["on_youtube"] == "Y":
            channels.append("youtube")
        for ch in channels:
            n += 1
            ts = base + timedelta(minutes=n * 3 + rng.randint(0, 2))
            key = f"{r['asset_id']}|{ch}"
            if key in seen:
                status, err, link = "error", f"post_id trùng — đã xử lý ở run trước trong cùng batch: {r['asset_id']}", ""
            elif not r["media_link"]:
                status, err, link = "skipped", "Thiếu media_link — không tạo được nội dung đăng", ""
            elif r["approval_status"] != "Approved":
                status, err, link = "need_review", f"approval_status = {r['approval_status']}", ""
            elif rng.random() < 0.05:
                status, err, link = "error", rng.choice([
                    "API trả 429 Too Many Requests — thử lại sau",
                    "Timeout khi tải media lên kho tạm",
                    "Caption vượt giới hạn ký tự của kênh",
                ]), ""
            elif rng.random() < 0.06:
                status, err, link = "pending", "", ""
            else:
                status, err = "drafted", ""
                link = f"https://drive.kpim.example/drafts/{r['asset_id']}-{ch}.docx"
            seen.add(key)
            rows.append({
                "run_id": f"RUN-2026-{n:04d}",
                "post_id": r["asset_id"],
                "channel": ch,
                "processed_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "error_message": err,
                "draft_link": link,
            })
    return rows


REVIEW_FIELDS = ["post_id", "content_type", "prompt_used", "ai_draft_excerpt", "review_status",
                 "reviewer", "review_timestamp", "revision_note",
                 "checklist_claim_ok", "checklist_pii_ok", "checklist_tone_ok", "checklist_cta_ok"]
PROMPTS = {
    "website": "Viết bài web 600 từ cho sản phẩm {product}, persona {persona}, giọng {tone}, bám key message: {km}",
    "caption": "Viết caption Facebook ≤ 90 từ cho bài '{title}', pillar {pillar}, CTA '{cta}', kèm 2 hashtag",
    "media_prompt": "Mô tả ảnh/video cho bài '{title}': bố cục, màu thương hiệu KPIM, không hiển thị thông tin định danh",
}
REVISION_NOTES = {
    "Need Revision": [
        "Thiếu dòng 'Điều kiện & điều khoản áp dụng' bắt buộc với bài Promo",
        "Con số lãi suất chưa kèm thời hạn hiệu lực",
        "Giọng văn quá quảng cáo, chỉnh về tông tư vấn",
        "CTA chưa khớp landing page của chiến dịch",
    ],
    "Rejected": [
        "Dùng từ tuyệt đối 'cao nhất thị trường' — vi phạm quy tắc truyền thông",
        "Ảnh nháp hiển thị số thẻ khách hàng — vi phạm quy tắc PII",
        "Trích dẫn testimonial chưa có văn bản đồng ý của khách hàng",
    ],
    "Need Review": ["Chờ Compliance đọc lần 2"],
}


def build_content_review(rng: random.Random, calendar: list[dict], src: dict) -> list[dict]:
    campaigns = {c["campaign_id"]: c for c in src["campaigns"]}
    rows = []
    base = datetime(2026, 7, 18, 9, 0, 0)
    n = 0
    for r in calendar:
        c = campaigns[r["campaign_id"]]
        for ct in ("website", "caption", "media_prompt"):
            n += 1
            st = r["approval_status"]
            claim_ok = pii_ok = tone_ok = cta_ok = "TRUE"
            note = ""
            if st == "Rejected":
                note = rng.choice(REVISION_NOTES["Rejected"])
                if "PII" in note:
                    pii_ok = "FALSE"
                elif "đồng ý" in note:
                    claim_ok = "FALSE"
                else:
                    claim_ok = "FALSE"
            elif st == "Need Revision":
                note = rng.choice(REVISION_NOTES["Need Revision"])
                if "CTA" in note:
                    cta_ok = "FALSE"
                elif "Giọng" in note:
                    tone_ok = "FALSE"
                else:
                    claim_ok = "FALSE"
            elif st == "Need Review":
                note = REVISION_NOTES["Need Review"][0]
            excerpt = {
                "website": f"{r['title']} — KPIM Bank giới thiệu {CAMPAIGN_PRODUCT[r['campaign_id']]} với "
                           f"{CAMPAIGN_KEY_MESSAGE[r['campaign_id']]}",
                "caption": r["caption"][:120],
                "media_prompt": f"Ảnh chủ đề {PILLAR_META[r['pillar_code']][0]}, tông màu thương hiệu KPIM, "
                                f"chủ thể chính minh hoạ '{r['title'][:48]}'",
            }[ct]
            prompt = PROMPTS[ct].format(
                product=CAMPAIGN_PRODUCT[r["campaign_id"]],
                persona=CAMPAIGN_PERSONA[r["campaign_id"]][0],
                tone=CAMPAIGN_TONE[r["campaign_id"]],
                km=CAMPAIGN_KEY_MESSAGE[r["campaign_id"]],
                title=r["title"], pillar=r["pillar_code"], cta=r["cta_label"])
            rows.append({
                "post_id": r["asset_id"], "content_type": ct,
                "prompt_used": prompt, "ai_draft_excerpt": excerpt,
                "review_status": "Approved" if st == "Approved" else st,
                "reviewer": rng.choice(REVIEWERS) if st != "Draft" else "",
                "review_timestamp": "" if st == "Draft" else
                                    (base + timedelta(minutes=n * 7)).strftime("%Y-%m-%d %H:%M:%S"),
                "revision_note": note,
                "checklist_claim_ok": claim_ok, "checklist_pii_ok": pii_ok,
                "checklist_tone_ok": tone_ok, "checklist_cta_ok": cta_ok,
            })
    return rows


BRIDGE_FIELDS = ["post_id", "campaign_id", "cta_type", "cta_link", "landing_page", "lead_id",
                 "lead_source", "lead_created_at"]


def build_bridge(calendar: list[dict], leads: list[dict]) -> list[dict]:
    cal = {r["asset_id"]: r for r in calendar}
    rows = []
    posts_with_lead = set()

    def link(r):
        return (f"https://kpimbank.example/lp/{r['campaign_id'].lower()}"
                f"?utm_source={'facebook' if r['on_facebook'] == 'Y' else 'youtube'}"
                f"&utm_medium=social&utm_campaign={r['campaign_id'].lower()}"
                f"&utm_content={r['asset_id']}")

    for l in leads:
        pid = l.get("post_id")
        if not pid or pid not in cal:
            continue
        r = cal[pid]
        posts_with_lead.add(pid)
        rows.append({
            "post_id": pid, "campaign_id": r["campaign_id"], "cta_type": r["cta_type"],
            "cta_link": link(r), "landing_page": f"/lp/{r['campaign_id'].lower()}",
            "lead_id": l["lead_id"], "lead_source": l["source"],
            "lead_created_at": l["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
        })
    # bài có CTA nhưng KHÔNG ra lead nào — giữ để tính lead-per-post = 0, không phải BLANK
    for pid, r in cal.items():
        if pid in posts_with_lead or r["cta_type"] == "none":
            continue
        rows.append({
            "post_id": pid, "campaign_id": r["campaign_id"], "cta_type": r["cta_type"],
            "cta_link": link(r), "landing_page": f"/lp/{r['campaign_id'].lower()}",
            "lead_id": "", "lead_source": "", "lead_created_at": "",
        })
    rows.sort(key=lambda x: (x["post_id"], x["lead_id"]))
    return rows


# ════════════════════════════════════════════════════════════════════════════
# 7. instance.yml · pillars.csv · brief.yml
# ════════════════════════════════════════════════════════════════════════════
def write_instance(out_content: Path) -> None:
    wtext(out_content / "instance.yml", """\
## instance.yml — KPIM Bank (BỘ MẪU MÔ PHỎNG cho khoá MKA-101)
##
## ⚠️ ĐÂY LÀ DỮ LIỆU MÔ PHỎNG. KPIM Bank là ngân hàng GIẢ ĐỊNH dựng riêng cho học liệu.
## Không có khách hàng thật, không có PII, không có credential, không kết nối API nào.
## Số điện thoại/tên khách trong dữ liệu lead là chuỗi sinh máy (`Khách hàng 0421`).
name: KPIM
label: KPIM Bank — bộ dữ liệu mẫu MKA-101 Marketing Analytics
brand: kpim-bank
autonomy: suggest          # chỉ đọc + đề xuất; adapter publish LUÔN từ chối chạy thật
language: vi
timezone: Asia/Ho_Chi_Minh
currency: VND

data_kind: simulated       # simulated | real  — gate an toàn cho mọi script publish
generated_by: scripts/courseware/generate_kpim_bank.py
generator_seed: 20260721

roots:
  content: content/KPIM
  data:    data/KPIM
  reports: reports/KPIM

channels:
  - platform: facebook
    handle: KPIM Bank
    page_id: "100055500000001"        # giả lập, khớp cột "ID Trang" của file export
  - platform: youtube
    handle: KPIM Bank
    channel_id: ""                    # bộ mẫu không có kênh thật

source_of_truth:
  plan_xlsx: KPIM_Bank_Marketing_Plan.xlsx   # sheet Campaign (4) + Post (60) — CHỈ ĐỌC
  facebook_export:
    - data/KPIM/raw/Facebook Post Summary.csv
    - data/KPIM/raw/Facebook Post Daily.csv
  note: >
    Hai file Facebook là export gốc, GIỮ NGUYÊN 95 cột (56 cột rỗng hoàn toàn).
    Việc dọn cột rỗng chính là bài lab S04 — đừng dọn sẵn cho học viên.

course:
  code: MKA-101
  sessions_supported: [S02, S03, S04, S05, S06]
""")


PILLAR_FIELDS = ["pillar_code", "pillar_name", "goal", "target_share",
                 "crosswalk_personal", "crosswalk_course", "default_funnel_stage",
                 "default_cta_type"]


def build_pillars() -> list[dict]:
    rows = []
    for code in PILLARS:
        name, goal, share, personal, funnel, cta = PILLAR_META[code]
        rows.append({
            "pillar_code": code, "pillar_name": name, "goal": goal,
            "target_share": share, "crosswalk_personal": personal,
            "crosswalk_course": code, "default_funnel_stage": funnel,
            "default_cta_type": cta,
        })
    return rows


def write_briefs(out_content: Path, src: dict, calendar: list[dict]) -> list[str]:
    written = []
    for c in src["campaigns"]:
        cid = c["campaign_id"]
        assets = [r for r in calendar if r["campaign_id"] == cid]
        pub = sum(1 for r in assets if r["is_published"] == "Y")
        p1, p2 = CAMPAIGN_PERSONA[cid]
        comp = COMPLIANCE_BASE + [
            f"Chiến dịch {cid}: mọi nội dung nhắc '{CAMPAIGN_PRODUCT[cid]}' phải dẫn về "
            f"landing page chính thức /lp/{cid.lower()} và nêu rõ thời hạn chương trình."
        ]
        comp_yaml = "\n".join(f"  - {x}" for x in comp)
        wtext(out_content / "02_campaigns" / cid / "brief.yml", f"""\
## brief.yml — {cid} · {c['campaign_name']}
## Sinh từ sheet Campaign của KPIM_Bank_Marketing_Plan.xlsx + bổ sung persona / key message /
## tone / ràng buộc tuân thủ (4 nhóm này KHÔNG có trong nguồn — sinh bù cho học liệu).
campaign_id: {cid}
campaign_name: {c['campaign_name']}
brand: kpim-bank
quarter: {c['quarter']}
product_or_topic: {c['product']}
segment: {c['segment']}
objective: {c['objective']}
big_idea: {CAMPAIGN_KEY_MESSAGE[cid]}

start_date: {str(c['start_date'])[:10]}
end_date: {str(c['end_date'])[:10]}

persona_primary: {p1}
persona_secondary: {p2}
key_message: {CAMPAIGN_KEY_MESSAGE[cid]}
tone: {CAMPAIGN_TONE[cid]}

funnel_goal: business
channels: [facebook, youtube]
pillars: [{', '.join(PILLARS)}]

primary_kpi: {c['primary_kpi']}
secondary_kpi: Chi phí trên mỗi lead (CPL)
target_reach: {to_int(c['target_reach'])}
target_leads: {to_int(c['target_leads'])}
budget: {to_int(c['budget_vnd'])}
currency: VND

assets_total: {len(assets)}       # {pub} bài đã đăng + {len(assets) - pub} bài kế hoạch chưa đăng
status: {c['status']}
owner: {c['owner']}

compliance_notes:
{comp_yaml}
""")
        written.append(str(out_content / "02_campaigns" / cid / "brief.yml"))
    return written


# ════════════════════════════════════════════════════════════════════════════
# 8. DATA DICTIONARY
# ════════════════════════════════════════════════════════════════════════════
def write_dictionary(out_content: Path, stats: dict) -> None:
    wtext(out_content / "DATA_DICTIONARY.md", f"""\
# DATA DICTIONARY — bộ dữ liệu KPIM Bank (MKA-101)

> **Dữ liệu mô phỏng.** KPIM Bank là ngân hàng giả định. Không có PII thật, không có
> credential, không gọi API nào. Sinh bằng `scripts/courseware/generate_kpim_bank.py`
> (seed `20260721` — chạy lại ra kết quả y hệt).

Tài liệu này dành cho **giảng viên**: mọi "nhiễu" trong dữ liệu đều là cố ý và được liệt
kê đầy đủ ở mục [Nhiễu cố ý](#nhiễu-cố-ý-đáp-án-cho-giảng-viên).

---

## 0. Ba tên của cùng một khoá

Cùng một mã bài (`P-Q1-01`) mang **ba tên** ở ba nơi — đây chính là bài học crosswalk:

| Nơi | Tên cột | Ghi chú |
|---|---|---|
| `templates/schema/model.yml` (canonical) | `asset_id` | khoá chính của `dim_asset` |
| `KPIM_Bank_Marketing_Plan.xlsx` sheet Post | `post_code` | nguồn gốc |
| Tài liệu MKA-101 & các bảng lab (`execution_log`, `content_review`, `cta_lead_bridge`) | `post_id` | tên học viên gặp trong đề bài |

**Giá trị giống hệt nhau** ⇒ join trực tiếp được, không cần bảng trung gian.
`calendar.csv` mang cả `asset_id` lẫn `post_code` để thấy rõ điều đó.

Khoá nối sang số liệu Facebook: `platform_native_id_fb` ↔ cột `ID bài viết` của cả hai
file export (khớp {stats['fb_match']}/60).

---

## 1. `content/KPIM/instance.yml`
Khai báo instance: tên, mức tự trị (`suggest` — cấm publish), 3 gốc thư mục, kênh,
và `data_kind: simulated` (gate an toàn để script publish từ chối chạy trên bộ mẫu).

## 2. `content/KPIM/01_brand/pillars.csv`
**Grain:** 1 dòng = 1 content pillar của KPIM Bank. **Khoá:** `pillar_code`. **{stats['pillars']} dòng.**

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `pillar_code` | string | Mã pillar — **trùng nguyên văn** giá trị `content_pillar` của sheet Post ⇒ join thẳng, không cần map |
| `pillar_name` | string | Tên tiếng Việt hiển thị trên dashboard |
| `goal` | string | Pillar này tồn tại để làm gì |
| `target_share` | decimal 0–1 | Tỷ trọng bài kỳ vọng; tổng = 1.00 |
| `crosswalk_personal` | string | Ánh xạ sang hệ pillar A..F của kênh cá nhân (51.01) |
| `crosswalk_course` | string | Ánh xạ sang `content_pillar` của KPIM Bank (ở đây = chính nó) |
| `default_funnel_stage` | enum | Tầng phễu mặc định, dùng khi calendar không khai riêng |
| `default_cta_type` | enum `cta_type` | CTA mặc định của pillar |

## 3. `content/KPIM/02_campaigns/<campaign_id>/brief.yml`
**Grain:** 1 file = 1 chiến dịch (4 file). Lấy 16 cột từ sheet `Campaign` + **sinh bù 4 nhóm
không có trong nguồn**: `persona_primary/secondary`, `key_message`, `tone`, `compliance_notes`.
`compliance_notes` cố tình viết theo giọng pháp chế ngân hàng để bài S03 (kiểm nội dung AI)
có tiêu chí chấm thật.

## 4. `content/KPIM/02_campaigns/<campaign_id>/calendar.csv` ★
**Grain:** 1 dòng = 1 asset (chưa unpivot theo kênh). **Khoá:** `asset_id`.
**Số dòng:** {stats['cal_q1']} · {stats['cal_q2']} · {stats['cal_q3']} · {stats['cal_q4']}
(tổng {stats['cal_total']} dòng vật lý = {stats['cal_logical']} dòng logic + {NOISE_DUP_ROWS} dòng lặp cố ý).

Mỗi quý = **15 bài đã đăng** (nguyên văn sheet Post) **+ 10 bài kế hoạch chưa đăng**.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `asset_id` | string | Khoá chính. = `post_code` = `post_id` |
| `post_code` | string | Giá trị gốc từ sheet Post (giữ để truy vết) |
| `campaign_id` | string | FK → `brief.yml` / sheet Campaign |
| `quarter` | string | Q1..Q4 |
| `planned_publish_date` | date ISO | `planned_date` của sheet Post |
| `schedule_date` | date | Ngày hẹn đăng của workflow (**có 3 dòng sai định dạng — cố ý**) |
| `pillar_code` | string | FK → `pillars.csv` |
| `format_source` | string | Giá trị gốc tiếng Việt: Ảnh · Video · Thước phim · Liên kết |
| `format` | enum `format` | Canonical sau `value_map` của crosswalk: fb_post · long_video · fb_reel |
| `funnel_stage` | enum | Suy ra từ pillar |
| `platform_primary` | enum `platform` | Kênh chính của asset |
| `on_facebook` / `on_youtube` | Y/N | **Giữ nguyên dạng 2 cột cờ** của nguồn — unpivot về grain `platform` là bài tập S04 |
| `title` | string | Tiêu đề bài |
| `caption` | string | **Sinh bù** — caption tiếng Việt theo pillar + CTA + hashtag |
| `media_link` | string | **Sinh bù** — đường dẫn giả `media/Q1/P-Q1-01.jpg` (**5 dòng để trống — cố ý**) |
| `cta_label` | string | Nhãn CTA của kế hoạch (cột `cta` của nguồn) — **khác** `cta_clicks` (số đo) |
| `cta_type` | enum `cta_type` | Canonical |
| `approval_status` | enum `approval_status_course` | Draft · Need Review · Approved · Need Revision · Rejected |
| `status` | enum `status` | Canonical, map từ `approval_status` (+ `published` khi đã đăng) |
| `is_published` | Y/N | **Cột trọng tài** — xem mục dưới |
| `platform_native_id_fb` | string | `fb_post_id` — khoá nối sang 2 file Facebook |
| `platform_native_id_yt` | string | `yt_video_id` — khoá nối sang `youtube_export.csv` |
| `owner` | string | Chủ sở hữu |

### Cách xử lý mâu thuẫn "60/60 đều Đã đăng" ⚠️ ĐỌC KỸ
Nguồn có 60/60 bài `status = "Đã đăng"`, nên nút **IF Approved** của n8n không có gì để lọc.
Giải pháp đã chọn (nhất quán, không mâu thuẫn với dữ liệu Facebook có thật):

1. **Thêm cột `is_published`.** 60 bài có `fb_post_id` thật → `is_published = Y`,
   `approval_status = Approved`, `status = published`. Không đụng vào sự thật đã đăng.
2. **Thêm 40 bài KẾ HOẠCH** (10 bài/quý, `asset_id` = `P-Qn-16` … `P-Qn-25`),
   `is_published = N`, **không có** `fb_post_id`/`yt_video_id`. Toàn bộ các trạng thái
   duyệt khác nằm ở đây.
3. Phân bố trên **{stats['cal_logical']} dòng logic**: {stats['st_approved']} Approved ({stats['st_approved']}%) ·
   {stats['st_needreview']} Need Review · {stats['st_draft']} Draft ·
   {stats['st_needrev']} Need Revision · {stats['st_rejected']} Rejected.
   Trong đó **{stats['approved_unpublished']} bài Approved nhưng chưa đăng** — đây chính là tập
   mà nhánh "IF Approved" của n8n phải chạy qua.

**Quy tắc bất biến:** `is_published = Y` ⟹ `approval_status = Approved` (không có ngoại lệ).
Ngược lại thì không: Approved mà chưa đăng là hợp lệ (đang chờ tới lịch).

## 5. `content/KPIM/03_approvals/content_review.csv` ★
**Grain:** 1 dòng = 1 (`post_id` × `content_type`). **{stats['review']} dòng** = {stats['cal_logical']} bài × 3 loại nội dung.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `post_id` | string | FK → `calendar.asset_id` |
| `content_type` | enum | `website` · `caption` · `media_prompt` |
| `prompt_used` | string | Prompt đã dùng để sinh nháp (có persona + tone + key message của brief) |
| `ai_draft_excerpt` | string | Trích đoạn nháp AI |
| `review_status` | enum | Need Review · Approved · Need Revision · Rejected — **luôn khớp `calendar.approval_status` của cùng post** |
| `reviewer` | string | Người duyệt; rỗng khi còn `Draft` |
| `review_timestamp` | datetime | Rỗng khi còn `Draft` |
| `revision_note` | string | Lý do trả về — viết theo ngôn ngữ pháp chế ngân hàng |
| `checklist_claim_ok` | bool | Tuyên bố/con số có kèm điều kiện? |
| `checklist_pii_ok` | bool | Không lộ thông tin định danh? |
| `checklist_tone_ok` | bool | Đúng tone brief? |
| `checklist_cta_ok` | bool | CTA khớp landing page? |

Checklist `FALSE` **luôn** đi kèm `review_status` ∈ (Need Revision, Rejected) — dùng làm
đáp án cho bài "vì sao nội dung này bị chặn".

## 6. `content/KPIM/04_published/execution_log.csv` ★
**Grain:** 1 dòng = 1 lần workflow n8n xử lý (`post_id` × `channel`). **{stats['exec']} dòng.**

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `run_id` | string | `RUN-2026-0001`… |
| `post_id` | string | FK → calendar |
| `channel` | enum | facebook · youtube |
| `processed_timestamp` | datetime | Thời điểm node xử lý |
| `status` | enum | `pending` · `drafted` · `skipped` · `error` · `need_review` |
| `error_message` | string | Rỗng khi thành công |
| `draft_link` | string | Chỉ có khi `drafted` |

**Ca lỗi cài sẵn (để học viên phải xử lý):**
| Ca | Điều kiện sinh ra | status | Số dòng |
|---|---|---|---|
| Thiếu media | `media_link` rỗng | `skipped` | {stats['exec_skipped']} |
| Trùng post_id | `asset_id` đã xuất hiện ở run trước cùng batch | `error` | {stats['exec_dup_error']} |
| Chưa duyệt | `approval_status` ≠ Approved | `need_review` | {stats['exec_needreview']} |
| Lỗi hạ tầng | 429 / timeout / caption quá dài | `error` | {stats['exec_other_error']} |
| Chưa tới lượt | — | `pending` | {stats['exec_pending']} |

## 7. `data/KPIM/raw/youtube_export.csv` ★
**Grain:** 1 dòng = 1 video (trọn đời). **Khoá:** `video_id`. **{stats['yt']} dòng** — đúng {stats['yt']} bài có `yt_video_id`.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `video_id` | string | = `yt_video_id` của sheet Post |
| `post_id` | string | FK → calendar (tiện lợi, YouTube Studio thật không có cột này) |
| `campaign_id` | string | FK |
| `publish_date` | date ISO | |
| `title` | string | |
| `views` | int | **Neo theo reach Facebook của chính bài đó** (18–46%) ⇒ hai kênh so được với nhau |
| `impressions` | int | = views / ctr |
| `ctr` | decimal 0–1 | 3,5–9,2% |
| `avg_view_duration_sec` | decimal | |
| `avg_percentage_viewed` | decimal 0–100 | |
| `watch_time_min` | decimal | = views × AVD / 60 |
| `likes` / `comments` / `shares` | int | |
| `subscribers_gained` | int | {YT_SUBS_PER_1000[0]}–{YT_SUBS_PER_1000[1]} sub/1000 view |

## 8. `data/KPIM/raw/leads/lead_*.csv` ★ — 7 FILE, 7 SCHEMA LỆCH NHAU
**Tổng {stats['lead_total']} lead.** Đây là **bài luyện chuẩn hoá & append đa nguồn của buổi S05**:
7 file cố ý **không** cùng tên cột, **không** cùng định dạng ngày, **không** cùng bộ cột.

| File | Dòng | Cột khoá | Cột SĐT | Định dạng ngày | Cột lệch đáng chú ý |
|---|---|---|---|---|---|
| `lead_app.csv` | {stats['ld_app']} | `lead_id` · `ma_chien_dich` · `ma_bai_viet`(=fb_post_id) | `sdt` | **epoch mili giây** | thừa `app_version`; `trang_thai` tiếng **Anh** |
| `lead_hotline.csv` | {stats['ld_hotline']} | `LeadID` · `Campaign` · `PostCode`(=post_code) | `Phone` (+84 …) | `dd-MM-yyyy HH:mm` | PascalCase; thừa `AgentName`, `CallDurationSec` |
| `lead_form.csv` | {stats['ld_form']} | `lead_id` · `campaign_id` · `fb_post_id` | `so_dien_thoai` | `yyyy-MM-dd` (**không có giờ**) | thừa `utm_source`, `utm_campaign` |
| `lead_social_inbox.csv` | {stats['ld_social']} | `id` · `campaign` · `post_id` | `phone` | `yyyy-MM-dd HH:mm:ss` | **THIẾU hẳn cột `branch`**; thừa `channel_page` |
| `lead_website.csv` | {stats['ld_web']} | `lead_id` · `campaign_id` · `post_id` | `phone_number` | **epoch giây** | thừa `landing_page`, `utm_medium` |
| `lead_branch.csv` | {stats['ld_branch']} | `MaLead` · `MaChienDich` | `SoDienThoai` | `dd/MM/yyyy` | `MaBaiViet` **luôn rỗng** (khách tới quầy); `PhanLoai` là nhãn **tiếng Việt** (Nóng/Ấm/Cần nuôi/Ưu tiên thấp) |
| `lead_qr_event.csv` | {stats['ld_qr']} | `lead_id` · `campaign_id` · `post_id` | `sdt` | **ISO 8601 có `Z`** (UTC) | thừa `event_name`, `qr_code_id` |

**Trường tối thiểu quy về được** (sau chuẩn hoá, đúng `fact_lead` của model.yml):
`lead_id` · `source` · `created_at` · `campaign_id` · `post_id` · `product_interest` ·
`region` · `branch` · `need_type` · `lead_status` · `lead_segment`.

- `source` **không có sẵn trong file** — suy từ tên file (đúng `lead_source` enum: app · hotline ·
  form · social_inbox · website · branch · qr_event). Tiền tố `lead_id` cũng mã hoá nguồn
  (`APP-` · `HL-` · `FRM-` · `SIB-` · `WEB-` · `BRC-` · `QR-`).
- **Nối về bài viết theo 2 đường khác nhau**: `lead_app` và `lead_form` dùng `fb_post_id`
  (khớp `calendar.platform_native_id_fb`); các file còn lại dùng `post_id`/`PostCode`
  (khớp `calendar.asset_id`). Cố ý — để học viên gặp cả hai kiểu khoá.
- **KHÔNG PII:** SĐT là chuỗi sinh máy `09xxxxxxxx` (định dạng hiển thị khác nhau theo nguồn),
  tên dạng `Khách hàng 0421`.
- **KHÔNG có cột `is_duplicate_of` trong file thô** — phát hiện trùng là việc của học viên.

## 9. `data/KPIM/raw/Facebook Post Summary.csv` · `Facebook Post Daily.csv`
**Copy nguyên si từ nguồn — KHÔNG dọn cột rỗng.** Summary giữ đủ 95 cột (56 cột rỗng hoàn
toàn) vì dọn cột rỗng là bài lab S04. Bẫy đã biết: cột `Ngày` của Summary là hằng số
`"Trọn đời"`, chỉ Daily mới có ngày thật; `Thời gian đăng` theo định dạng **MM/DD/YYYY**.

## 10. `data/KPIM/star/kpi_target.csv` ★
**Grain:** `campaign_id` × `platform` × `pillar_code` × `metric_name` × `period` (tháng).
**{stats['kpi']} dòng.** Đúng schema `dim_kpi_target` của model.yml.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `campaign_id` | string | FK |
| `platform` | enum | facebook · youtube |
| `pillar_code` | string | FK |
| `format` | enum | để trống ở bộ này (target không tách theo định dạng) |
| `metric_name` | string | `reach` · `leads` |
| `period` | string | `YYYY-MM` |
| `target_value` | decimal | **Tổng theo campaign khớp đúng `target_reach` / `target_leads` của sheet Campaign** (chia bằng largest-remainder nên không lệch do làm tròn) |
| `unit` | string | người · lead |
| `baseline_median` | decimal | Median của các bài **cùng platform + cùng pillar ở các quý TRƯỚC** |
| `baseline_source` | string | `fb_post_summary_median` · `youtube_export_median`; **rỗng = chưa đủ mẫu, KHÔNG điền số đoán** |
| `baseline_n` | int | Số mẫu. **Q1 luôn = 0** (không có lịch sử). `< 10` ⇒ dashboard phải hiện "chưa đủ mẫu" |

## 11. `data/KPIM/star/cost_by_post.csv`
**Grain:** 1 dòng = 1 asset. **{stats['cost']} dòng.** Tồn tại vì **không nguồn nào có chi phí cấp post**
(`budget_vnd` chỉ có ở cấp campaign — xem `crosswalk.yml` mục `cost.gap: true`).
`cost` = `budget_vnd` chia theo trọng số định dạng (long_video 3.2 · fb_reel 2.4 · fb_post 1.0);
`allocation_method` và `allocation_weight` ghi rõ cách chia để học viên biết đây là **số phân bổ,
không phải số kế toán**. Tổng `cost` theo campaign = đúng `budget_vnd`.

## 12. `data/KPIM/star/cta_lead_bridge.csv` ★
**Grain:** 1 dòng = 1 (post × lead). **{stats['bridge']} dòng.** Mắt xích nối **S04 (số liệu bài)** sang
**S05 (lead)**.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `post_id` | string | FK → calendar |
| `campaign_id` | string | FK |
| `cta_type` | enum | Từ calendar |
| `cta_link` | string | Có UTM đầy đủ: `utm_source` · `utm_medium` · `utm_campaign` · `utm_content=<post_id>` |
| `landing_page` | string | `/lp/cmp-2026-qn` |
| `lead_id` | string | **Rỗng** ⇒ bài có CTA nhưng không ra lead nào (giữ dòng để lead-per-post = 0 chứ không BLANK) |
| `lead_source` | string | Nguồn của lead đó |
| `lead_created_at` | datetime | |

---

## Nhiễu cố ý (đáp án cho giảng viên)

| # | Nhiễu | Ở đâu | Số lượng | Học viên phải làm gì |
|---|---|---|---|---|
| 1 | `media_link` rỗng | `calendar.csv` | **{NOISE_MISSING_MEDIA}** dòng | Lọc trước khi đưa vào workflow ⇒ tương ứng {stats['exec_skipped']} dòng `skipped` trong `execution_log` |
| 2 | `schedule_date` sai định dạng (`dd/MM/yyyy` lẫn trong ISO) | `calendar.csv` | **{NOISE_BAD_DATE}** dòng | Ép kiểu ngày tường minh, không để Power Query tự đoán locale |
| 3 | Lặp `asset_id` (bản sao lệch `schedule_date` 1 ngày) | `calendar.csv` | **{NOISE_DUP_ROWS}** dòng | Dedupe theo `asset_id`, giữ bản mới nhất ⇒ tương ứng {stats['exec_dup_error']} dòng `error` |
| 4 | Lead trùng người (cùng SĐT + tên, khác nguồn, lệch vài giờ) | 7 file lead | **{stats['lead_dup']}** cặp (~{LEAD_DUP_RATE:.0%}) | Dedupe theo (SĐT chuẩn hoá + tên); **không** có cột đánh dấu sẵn |
| 5 | 3 định dạng ngày + 4 kiểu hiển thị SĐT | 7 file lead | toàn bộ | Chuẩn hoá về ISO datetime + SĐT 10 số |
| 6 | Nhãn trạng thái/segment lẫn Anh–Việt | `lead_app`, `lead_social_inbox`, `lead_website` (Anh) vs `lead_branch` (Việt) | toàn bộ | Map về 1 bộ giá trị |
| 7 | `lead_social_inbox` thiếu hẳn cột `branch` | 1 file | toàn bộ | Append đa nguồn phải xử lý cột thiếu, không được để lệch cột |
| 8 | 56 cột rỗng hoàn toàn trong Post Summary | file gốc | 56 cột | Dọn cột rỗng (bài S04) |
| 9 | `Ngày` = `"Trọn đời"` trong Summary | file gốc | 60 dòng | Lấy trục thời gian từ `Thời gian đăng` |
| 10 | `baseline_median`/`baseline_source` rỗng (chưa đủ mẫu) | `kpi_target.csv` | {stats['kpi_nobase']}/{stats['kpi']} dòng — **toàn bộ {stats['kpi_q1']} dòng của Q1** (không có quý trước) | Hiện "chưa đủ mẫu", **không** thay bằng số đoán. Thêm nữa: {stats['kpi_base_lt10']} dòng có baseline nhưng `baseline_n < 10` ⇒ theo model.yml vẫn phải hiện "chưa đủ mẫu" |

---

## Câu chuyện dữ liệu — 5 insight bộ dữ liệu được thiết kế để học viên tìm ra

1. **Video và Reel ăn đứt Ảnh về tương tác.** Engagement rate (`Cảm xúc, bình luận và lượt
   chia sẻ` / `Số người tiếp cận`): Thước phim ≈ {stats['er_reel']:.2f}% · Video ≈ {stats['er_video']:.2f}%
   so với Ảnh ≈ {stats['er_photo']:.2f}% và Liên kết ≈ {stats['er_link']:.2f}%. Reel còn có reach trung vị
   cao gấp ~2,3 lần Ảnh. ⇒ Khuyến nghị dịch tỷ trọng định dạng, không phải tăng số bài.

2. **Bẫy kinh điển: Promo click nhiều nhất nhưng ra khách kém nhất.** Promo chiếm
   {stats['promo_click_share']:.0f}% tổng lượt click vào liên kết ({stats['promo_clicks_n']:,} click)
   nhưng chỉ đổi được **{stats['lpc_promo']:.2f} lead/click** — **thấp nhất** trong 6 pillar, trong khi
   Education {stats['lpc_edu']:.2f} · HowTo {stats['lpc_howto']:.2f}
   (cao nhất: {stats['lpc_best']} {stats['lpc_best_v']:.2f}).
   ⇒ Nếu chấm hiệu quả bằng CTR, Promo thắng; chấm bằng lead, Promo thua. Dạy học viên
   **đo tới cuối phễu**.

3. **Education + HowTo cho lead chất lượng cao nhất.** Tỷ lệ `lead_segment = hot` trên lead
   gắn được về bài: {stats['hot1']} ≈ {stats['hot1_v']:.0%} · {stats['hot2']} ≈ {stats['hot2_v']:.0%},
   so với Promo ≈ {stats['hot_promo']:.0%} · Brand ≈ {stats['hot_brand']:.0%}.
   ⇒ Nội dung "dạy" nuôi phễu tốt hơn nội dung "giảm giá". Kết hợp với insight #2: Promo vừa
   ra ít lead trên mỗi click, vừa ra lead nguội hơn.

4. **Q3 hụt mục tiêu lead rõ rệt.** `CMP-2026-Q3` đặt target {stats['t_q3']} lead nhưng thực
   tế chỉ {stats['a_q3']} lead (**{stats['p_q3']:.0f}%**), trong khi Q1 {stats['p_q1']:.0f}% ·
   Q2 {stats['p_q2']:.0f}% · Q4 {stats['p_q4']:.0f}%. ⇒ Trang "KPI vs Actual" có một quý
   đỏ để phân tích: reach vẫn đạt, nhưng chuyển đổi sang lead sụp — vấn đề ở CTA/landing,
   không ở phân phối.

5. **YouTube nhỏ hơn nhưng "đắt" hơn.** Với {stats['yt']} bài chạy cả hai kênh, tổng view
   YouTube ({stats['yt_views']:,}) chỉ bằng ~{stats['yt_vs_fb']:.0f}% reach Facebook của
   chính các bài đó ({stats['fb_reach_yt_posts']:,}). Nhưng YouTube đổi được
   ~{stats['yt_subs_per_1k']:.2f} subscriber/1000 view, trong khi cùng nhóm bài đó Facebook chỉ ra
   ~{stats['fb_leads_per_1k']:.2f} lead/1000 reach. ⇒ Kênh nhỏ không có nghĩa là kênh kém;
   phải so bằng chỉ số chuyển đổi chứ không bằng quy mô.
   *(Lưu ý khi chấm bài: subscriber và lead là hai sự kiện chuyển đổi khác nhau nên đây là so
   sánh **định hướng**, không phải so ngang hàng. Kết luận đúng mà học viên cần rút ra là
   "phải chuẩn hoá theo quy mô trước khi kết luận kênh nào tốt hơn" — chứ không phải
   "YouTube tốt hơn Facebook".)*
""")


# ════════════════════════════════════════════════════════════════════════════
# 9. Validate
# ════════════════════════════════════════════════════════════════════════════
def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def validate(out_content: Path, out_data: Path, src_dir: Path) -> int:
    print("\n" + "=" * 74)
    print("VALIDATE — kiểm tra bộ dữ liệu đã sinh")
    print("=" * 74)
    fails = 0

    def chk(ok: bool, label: str, detail: str = ""):
        nonlocal fails
        mark = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"  [{mark}] {label}{('  — ' + detail) if detail else ''}")

    src = load_sources(src_dir)
    fb_ids = {str(r["ID bài viết"]) for r in src["fb_summary"]}
    daily_ids = {str(r["ID bài viết"]) for r in src["fb_daily"]}

    cal = []
    for cid in ["CMP-2026-Q1", "CMP-2026-Q2", "CMP-2026-Q3", "CMP-2026-Q4"]:
        cal += read_csv(out_content / "02_campaigns" / cid / "calendar.csv")
    pub = [r for r in cal if r["is_published"] == "Y"]
    seen, logical = set(), []
    for r in cal:
        if r["asset_id"] not in seen:
            seen.add(r["asset_id"])
            logical.append(r)

    # 1. 60/60 post_id nối được về Facebook CSV (đếm trên dòng LOGIC, bỏ 2 dòng lặp cố ý)
    pub_logical = [r for r in logical if r["is_published"] == "Y"]
    matched = sum(1 for r in pub_logical if r["platform_native_id_fb"] in fb_ids)
    matched_d = sum(1 for r in pub_logical if r["platform_native_id_fb"] in daily_ids)
    chk(matched == 60 and matched_d == 60 and len(pub_logical) == 60,
        "60/60 bài đã đăng nối được về cả 2 file Facebook",
        f"Summary {matched}/{len(pub_logical)} · Daily {matched_d}/{len(pub_logical)} "
        f"(chưa kể {len(pub) - len(pub_logical)} dòng lặp cố ý)")

    # 2. 29/29 yt_video_id có dòng trong youtube_export
    yt = read_csv(out_data / "raw" / "youtube_export.csv")
    yt_ids = {r["video_id"] for r in yt}
    src_yt = {str(p["yt_video_id"]) for p in src["posts"] if p.get("yt_video_id")}
    chk(yt_ids == src_yt and len(yt) == len(src_yt),
        f"{len(src_yt)}/{len(src_yt)} yt_video_id có dòng trong youtube_export.csv",
        f"export {len(yt)} dòng")

    # 3. campaign_id hợp lệ ở calendar + lead
    valid_c = {c["campaign_id"] for c in src["campaigns"]}
    bad_cal = {r["campaign_id"] for r in cal} - valid_c
    lead_dir = out_data / "raw" / "leads"
    lead_files = sorted(lead_dir.glob("lead_*.csv"))
    bad_lead, lead_rows, per_file = set(), [], {}
    CID_COL = {"lead_app.csv": "ma_chien_dich", "lead_hotline.csv": "Campaign",
               "lead_form.csv": "campaign_id", "lead_social_inbox.csv": "campaign",
               "lead_website.csv": "campaign_id", "lead_branch.csv": "MaChienDich",
               "lead_qr_event.csv": "campaign_id"}
    for f in lead_files:
        rows = read_csv(f)
        per_file[f.name] = len(rows)
        col = CID_COL[f.name]
        for r in rows:
            bad_lead.add(r[col]) if r[col] not in valid_c else None
            lead_rows.append((f.name, r))
    chk(not bad_cal and not bad_lead, "Mọi campaign_id trong calendar + 7 file lead đều tồn tại ở sheet Campaign",
        f"calendar lạ={sorted(bad_cal)} · lead lạ={sorted(bad_lead)}")

    # 4. tổng lead theo campaign vs target_leads (cả TRƯỚC và SAU dedupe)
    PH = {"lead_app.csv": "sdt", "lead_hotline.csv": "Phone", "lead_form.csv": "so_dien_thoai",
          "lead_social_inbox.csv": "phone", "lead_website.csv": "phone_number",
          "lead_branch.csv": "SoDienThoai", "lead_qr_event.csv": "sdt"}
    NM = {"lead_app.csv": "ho_ten", "lead_hotline.csv": "CustomerName", "lead_form.csv": "ten_khach",
          "lead_social_inbox.csv": "name", "lead_website.csv": "full_name",
          "lead_branch.csv": "HoTen", "lead_qr_event.csv": "ten"}

    def norm_phone(s):
        return "".join(ch for ch in str(s) if ch.isdigit())[-9:]

    print("\n  Lead thực tế vs target_leads (raw = đọc thẳng 7 file · dedup = sau khi gộp người trùng):")
    tot, tot_dedup, seen_person = defaultdict(int), defaultdict(int), set()
    for fn, r in lead_rows:
        cid = r[CID_COL[fn]]
        tot[cid] += 1
        k = (norm_phone(r[PH[fn]]), r[NM[fn]])
        if k not in seen_person:
            seen_person.add(k)
            tot_dedup[cid] += 1
    for c in src["campaigns"]:
        cid = c["campaign_id"]
        t = to_int(c["target_leads"])
        a, ad = tot[cid], tot_dedup[cid]
        flag = "  <-- HUT RO RET" if ad / t < 0.8 else ""
        print(f"      {cid}: target {t:>5,} · raw {a:>5,} ({a / t * 100:5.1f}%) · "
              f"dedup {ad:>5,} ({ad / t * 100:5.1f}%){flag}")
    print(f"      TONG      : target {sum(to_int(c['target_leads']) for c in src['campaigns']):>5,} · "
          f"raw {sum(tot.values()):>5,} · dedup {sum(tot_dedup.values()):>5,}")

    # 5. nhiễu cố ý đếm đúng
    print("\n  Nhiễu cố ý:")
    n_media = sum(1 for r in logical if not r["media_link"].strip())
    n_baddate = sum(1 for r in cal if "/" in r["schedule_date"])
    n_dup = len(cal) - len(logical)
    chk(n_media == NOISE_MISSING_MEDIA, f"media_link rỗng = {NOISE_MISSING_MEDIA}", f"đếm được {n_media}")
    chk(n_baddate == NOISE_BAD_DATE, f"schedule_date sai định dạng = {NOISE_BAD_DATE}", f"đếm được {n_baddate}")
    chk(n_dup == NOISE_DUP_ROWS, f"dòng lặp asset_id = {NOISE_DUP_ROWS}", f"đếm được {n_dup}")

    # lead trùng
    seen_p, dups = {}, 0
    for fn, r in lead_rows:
        k = (norm_phone(r[PH[fn]]), r[NM[fn]])
        if k in seen_p:
            dups += 1
        seen_p[k] = 1
    exp_dup = int(round((len(lead_rows) / (1 + LEAD_DUP_RATE)) * LEAD_DUP_RATE))
    chk(abs(dups - exp_dup) <= 3, f"lead trùng ≈ {LEAD_DUP_RATE:.0%}",
        f"đếm được {dups} cặp / {len(lead_rows)} lead = {dups / len(lead_rows) * 100:.2f}%")

    # 6. toàn vẹn khoá ngoại các bảng lab
    ids = {r["asset_id"] for r in cal}
    for name, path, col in [
        ("execution_log", out_content / "04_published" / "execution_log.csv", "post_id"),
        ("content_review", out_content / "03_approvals" / "content_review.csv", "post_id"),
        ("cta_lead_bridge", out_data / "star" / "cta_lead_bridge.csv", "post_id"),
        ("cost_by_post", out_data / "star" / "cost_by_post.csv", "post_id"),
    ]:
        rows = read_csv(path)
        bad = {r[col] for r in rows} - ids
        chk(not bad, f"{name}.{col} ⊆ calendar.asset_id ({len(rows)} dòng)", f"lạ={sorted(bad)[:5]}")

    # 7. kpi_target tổng khớp target campaign
    kpi = read_csv(out_data / "star" / "kpi_target.csv")
    agg = defaultdict(int)
    for r in kpi:
        agg[(r["campaign_id"], r["metric_name"])] += int(r["target_value"])
    ok_kpi = True
    for c in src["campaigns"]:
        cid = c["campaign_id"]
        if agg[(cid, "reach")] != to_int(c["target_reach"]):
            ok_kpi = False
        if agg[(cid, "leads")] != to_int(c["target_leads"]):
            ok_kpi = False
    chk(ok_kpi, f"kpi_target tổng theo campaign khớp target_reach/target_leads ({len(kpi)} dòng)")

    cost = read_csv(out_data / "star" / "cost_by_post.csv")
    cagg = defaultdict(int)
    for r in cost:
        cagg[r["campaign_id"]] += int(r["cost"])
    ok_cost = all(cagg[c["campaign_id"]] == to_int(c["budget_vnd"]) for c in src["campaigns"])
    chk(ok_cost, "cost_by_post tổng theo campaign khớp budget_vnd")

    # 8. trạng thái duyệt
    st = defaultdict(int)
    for r in logical:
        st[r["approval_status"]] += 1
    print(f"\n  approval_status trên {len(logical)} dòng logic: " +
          " · ".join(f"{k}={v}" for k, v in sorted(st.items())))
    inv = [r["asset_id"] for r in logical if r["is_published"] == "Y" and r["approval_status"] != "Approved"]
    chk(not inv, "Bất biến: is_published=Y ⟹ approval_status=Approved", f"vi phạm={inv[:5]}")
    appr_unpub = sum(1 for r in logical if r["approval_status"] == "Approved" and r["is_published"] == "N")
    chk(appr_unpub > 0, f"Có {appr_unpub} bài Approved chưa đăng cho nhánh 'IF Approved' của n8n")

    shutil.rmtree(src["tmp"], ignore_errors=True)
    print("\n" + ("KẾT QUẢ: TẤT CẢ PASS" if fails == 0 else f"KẾT QUẢ: {fails} MỤC FAIL"))
    return fails


# ════════════════════════════════════════════════════════════════════════════
# main
# ════════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh bộ dữ liệu mẫu KPIM Bank cho MKA-101")
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "content" / "KPIM"),
                    help="thư mục content của instance (mặc định content/KPIM/)")
    ap.add_argument("--data-dir", default=None,
                    help="thư mục data (mặc định <repo>/data/KPIM)")
    ap.add_argument("--src-dir", default=str(DEFAULT_SRC), help="thư mục dữ liệu nguồn KPIM Bank")
    ap.add_argument("--validate", action="store_true", help="chỉ kiểm tra bộ đã sinh, không ghi lại")
    args = ap.parse_args()

    out_content = Path(args.out_dir)
    out_data = Path(args.data_dir) if args.data_dir else REPO_ROOT / "data" / "KPIM"
    src_dir = Path(args.src_dir)

    if args.validate:
        return validate(out_content, out_data, src_dir)

    random.seed(SEED)
    rng = random.Random(SEED)

    print("Đọc nguồn (copy ra %TEMP% trước khi mở)…")
    src = load_sources(src_dir)
    fb_by_id = {str(r["ID bài viết"]): r for r in src["fb_summary"]}
    print(f"  Campaign {len(src['campaigns'])} · Post {len(src['posts'])} · "
          f"FB Summary {len(src['fb_summary'])} · FB Daily {len(src['fb_daily'])}")

    written: dict[str, int] = {}

    # --- content ---
    write_instance(out_content)
    written["content/KPIM/instance.yml"] = -1

    pillars = build_pillars()
    written["content/KPIM/01_brand/pillars.csv"] = w(
        out_content / "01_brand" / "pillars.csv", pillars, PILLAR_FIELDS)

    logical, physical = build_calendar(rng, src)
    cal_counts = {}
    for cid in sorted({r["campaign_id"] for r in physical}):
        rows = [r for r in physical if r["campaign_id"] == cid]
        n = w(out_content / "02_campaigns" / cid / "calendar.csv", rows, CALENDAR_FIELDS)
        cal_counts[cid] = n
        written[f"content/KPIM/02_campaigns/{cid}/calendar.csv"] = n

    for p in write_briefs(out_content, src, logical):
        written[str(Path(p).relative_to(REPO_ROOT)).replace("\\", "/")] = -1

    review = build_content_review(rng, logical, src)
    written["content/KPIM/03_approvals/content_review.csv"] = w(
        out_content / "03_approvals" / "content_review.csv", review, REVIEW_FIELDS)

    exec_log = build_execution_log(rng, physical)
    written["content/KPIM/04_published/execution_log.csv"] = w(
        out_content / "04_published" / "execution_log.csv", exec_log, EXEC_FIELDS)

    # --- data/raw ---
    out_raw = out_data / "raw"
    out_raw.mkdir(parents=True, exist_ok=True)
    for name in (FB_SUMMARY, FB_DAILY):
        shutil.copy2(src["tmp"] / name, out_raw / name)   # copy nguyên si, KHÔNG dọn cột
        written[f"data/KPIM/raw/{name}"] = -2

    yt = build_youtube(rng, src, fb_by_id)
    written["data/KPIM/raw/youtube_export.csv"] = w(out_raw / "youtube_export.csv", yt, YT_FIELDS)

    leads, campaign_total = build_leads(rng, src, logical, fb_by_id)
    lead_counts = write_leads(rng, leads, out_raw)
    for k, v in lead_counts.items():
        written[f"data/KPIM/raw/leads/{k}"] = v

    # --- data/star ---
    kpi = build_kpi_target(src, logical, fb_by_id, yt)
    written["data/KPIM/star/kpi_target.csv"] = w(out_data / "star" / "kpi_target.csv", kpi, KPI_FIELDS)

    cost = build_cost(src, logical)
    written["data/KPIM/star/cost_by_post.csv"] = w(out_data / "star" / "cost_by_post.csv", cost, COST_FIELDS)

    bridge = build_bridge(logical, leads)
    written["data/KPIM/star/cta_lead_bridge.csv"] = w(
        out_data / "star" / "cta_lead_bridge.csv", bridge, BRIDGE_FIELDS)

    # --- thống kê cho data dictionary ---
    def er(fmt_src):
        rs = [fb_by_id[r["platform_native_id_fb"]] for r in logical
              if r["is_published"] == "Y" and r["format_source"] == fmt_src]
        return statistics.mean(to_int(x["Cảm xúc, bình luận và lượt chia sẻ"]) /
                               to_int(x["Số người tiếp cận"]) for x in rs) * 100

    total_link_clicks = sum(to_int(r["Lượt click vào liên kết"]) for r in src["fb_summary"])
    promo_clicks = sum(to_int(fb_by_id[r["platform_native_id_fb"]]["Lượt click vào liên kết"])
                       for r in logical if r["is_published"] == "Y" and r["pillar_code"] == "Promo")

    # -- ĐO LẠI tín hiệu trên dữ liệu ĐÃ SINH (không lấy hằng số thiết kế) --
    pillar_of = {r["asset_id"]: r["pillar_code"] for r in logical}
    leads_by_post = defaultdict(int)
    hot_by_pillar = defaultdict(lambda: [0, 0])
    for l in leads:
        pid = l.get("post_id")
        if not pid:
            continue
        leads_by_post[pid] += 1
        pc = pillar_of.get(pid)
        if pc:
            hot_by_pillar[pc][1] += 1
            if l["lead_segment"] == "hot":
                hot_by_pillar[pc][0] += 1
    clicks_by_pillar = defaultdict(int)
    leads_by_pillar = defaultdict(int)
    for r in logical:
        if r["is_published"] != "Y":
            continue
        clicks_by_pillar[r["pillar_code"]] += to_int(
            fb_by_id[r["platform_native_id_fb"]]["Lượt click vào liên kết"])
        leads_by_pillar[r["pillar_code"]] += leads_by_post[r["asset_id"]]
    lpc = {p: leads_by_pillar[p] / clicks_by_pillar[p] for p in clicks_by_pillar}
    hotr = {p: v[0] / v[1] for p, v in hot_by_pillar.items() if v[1]}
    lpc_sorted = sorted(lpc.items(), key=lambda x: x[1])
    hot_sorted = sorted(hotr.items(), key=lambda x: -x[1])
    yt_posts = {y["post_id"] for y in yt}
    fb_reach_ytp = sum(to_int(fb_by_id[r["platform_native_id_fb"]]["Số người tiếp cận"])
                       for r in logical if r["asset_id"] in yt_posts)
    yt_views = sum(y["views"] for y in yt)
    yt_subs = sum(y["subscribers_gained"] for y in yt)
    leads_on_ytposts = sum(1 for l in leads if l.get("post_id") in yt_posts)

    st = defaultdict(int)
    for r in logical:
        st[r["approval_status"]] += 1
    ex = defaultdict(int)
    for r in exec_log:
        ex[r["status"]] += 1
    dup_err = sum(1 for r in exec_log if r["status"] == "error" and "trùng" in r["error_message"])
    lead_by_src = defaultdict(int)
    for l in leads:
        lead_by_src[l["source"]] += 1
    targets = {c["campaign_id"]: to_int(c["target_leads"]) for c in src["campaigns"]}
    actual = defaultdict(int)
    for l in leads:
        actual[l["campaign_id"]] += 1

    stats = {
        "fb_match": sum(1 for r in logical if r["platform_native_id_fb"] in fb_by_id),
        "pillars": len(pillars),
        "cal_q1": cal_counts["CMP-2026-Q1"], "cal_q2": cal_counts["CMP-2026-Q2"],
        "cal_q3": cal_counts["CMP-2026-Q3"], "cal_q4": cal_counts["CMP-2026-Q4"],
        "cal_total": len(physical), "cal_logical": len(logical),
        "st_approved": st["Approved"], "st_needreview": st["Need Review"],
        "st_draft": st["Draft"], "st_needrev": st["Need Revision"], "st_rejected": st["Rejected"],
        "approved_unpublished": sum(1 for r in logical if r["approval_status"] == "Approved"
                                    and r["is_published"] == "N"),
        "review": len(review), "exec": len(exec_log),
        "exec_skipped": ex["skipped"], "exec_needreview": ex["need_review"],
        "exec_dup_error": dup_err, "exec_other_error": ex["error"] - dup_err,
        "exec_pending": ex["pending"],
        "yt": len(yt), "lead_total": len(leads),
        "ld_app": lead_counts["lead_app.csv"], "ld_hotline": lead_counts["lead_hotline.csv"],
        "ld_form": lead_counts["lead_form.csv"], "ld_social": lead_counts["lead_social_inbox.csv"],
        "ld_web": lead_counts["lead_website.csv"], "ld_branch": lead_counts["lead_branch.csv"],
        "ld_qr": lead_counts["lead_qr_event.csv"],
        "lead_dup": int(round(len(leads) / (1 + LEAD_DUP_RATE) * LEAD_DUP_RATE)),
        "kpi": len(kpi), "kpi_q1": sum(1 for r in kpi if r["campaign_id"] == "CMP-2026-Q1"),
        "kpi_nobase": sum(1 for r in kpi if not r["baseline_source"]),
        "kpi_base_lt10": sum(1 for r in kpi if r["baseline_source"] and int(r["baseline_n"]) < 10),
        "cost": len(cost), "bridge": len(bridge),
        "er_reel": er("Thước phim"), "er_video": er("Video"),
        "er_photo": er("Ảnh"), "er_link": er("Liên kết"),
        "promo_click_share": promo_clicks / total_link_clicks * 100,
        "t_q3": targets["CMP-2026-Q3"], "a_q3": actual["CMP-2026-Q3"],
        "p_q1": actual["CMP-2026-Q1"] / targets["CMP-2026-Q1"] * 100,
        "p_q2": actual["CMP-2026-Q2"] / targets["CMP-2026-Q2"] * 100,
        "p_q3": actual["CMP-2026-Q3"] / targets["CMP-2026-Q3"] * 100,
        "p_q4": actual["CMP-2026-Q4"] / targets["CMP-2026-Q4"] * 100,
        "yt_views": yt_views, "fb_reach_yt_posts": fb_reach_ytp,
        "yt_vs_fb": yt_views / fb_reach_ytp * 100,
        "yt_subs_per_1k": yt_subs / yt_views * 1000,
        "fb_leads_per_1k": leads_on_ytposts / fb_reach_ytp * 1000,
        # tín hiệu đo lại trên dữ liệu đã sinh
        "lpc_promo": lpc["Promo"], "lpc_howto": lpc["HowTo"], "lpc_edu": lpc["Education"],
        "lpc_worst": lpc_sorted[0][0], "lpc_best": lpc_sorted[-1][0], "lpc_best_v": lpc_sorted[-1][1],
        "hot1": hot_sorted[0][0], "hot1_v": hotr[hot_sorted[0][0]],
        "hot2": hot_sorted[1][0], "hot2_v": hotr[hot_sorted[1][0]],
        "hot_promo": hotr["Promo"], "hot_brand": hotr["Brand"],
        "promo_leads": leads_by_pillar["Promo"], "promo_clicks_n": clicks_by_pillar["Promo"],
    }
    write_dictionary(out_content, stats)
    written["content/KPIM/DATA_DICTIONARY.md"] = -1

    shutil.rmtree(src["tmp"], ignore_errors=True)

    print("\nĐã ghi:")
    for k, v in written.items():
        tag = {-1: "(yml/md)", -2: "(copy nguyên si)"}.get(v, f"{v:>6,} dòng")
        print(f"  {tag:>16}  {k}")
    print(f"\nTổng lead {len(leads):,} · calendar {len(physical)} dòng · "
          f"youtube {len(yt)} · kpi_target {len(kpi)} · bridge {len(bridge)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
