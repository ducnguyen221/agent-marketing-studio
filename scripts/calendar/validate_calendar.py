# -*- coding: utf-8 -*-
"""
Kiểm tra content calendar trước khi cho đi tiếp trong pipeline.

Đọc schema canonical ở schema/ nên KHÔNG hardcode luật ở đây —
sửa enums.yml/model.yml là validator đổi theo.

    python validate_calendar.py <calendar.csv> [--pillars pillars.csv]
                               [--commercial-cta-episodes 3]
                               [--forbidden-terms a,b,c] [--strict]

Exit code: 0 = sạch (hoặc chỉ có warning), 1 = có error, 2 = không chạy được.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Thiếu pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Ký tự Unicode "mathematical bold/italic" — dấu hiệu heading bị hỏng khi copy
FANCY_UNICODE = re.compile(r"[\U0001D400-\U0001D7FF]")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, row: str, msg: str) -> None:
        self.errors.append(f"[{row}] {msg}")

    def warn(self, row: str, msg: str) -> None:
        self.warnings.append(f"[{row}] {msg}")


def load_schema() -> tuple[dict, dict]:
    with open(SCHEMA_DIR / "model.yml", encoding="utf-8") as f:
        model = yaml.safe_load(f)
    with open(SCHEMA_DIR / "enums.yml", encoding="utf-8") as f:
        enums = yaml.safe_load(f)
    return model, enums


def enum_values(enums: dict, name: str) -> set[str]:
    node = enums.get(name, {})
    values = node.get("values", [])
    if isinstance(values, dict):          # format: {long_video: {...}, ...}
        return set(values.keys())
    return set(values)


def status_rank(enums: dict, status: str) -> int:
    order = enums["status"]["values"]
    return order.index(status) if status in order else -1


def check(rows: list[dict], model: dict, enums: dict, args) -> Report:
    rep = Report()
    asset_cols = model["tables"]["dim_asset"]["columns"]
    ids = [r.get("asset_id", "") for r in rows]

    # ── cấp tập tin ────────────────────────────────────────────────────────
    missing_cols = [c for c, spec in asset_cols.items()
                    if spec.get("required") and c not in (rows[0] if rows else {})]
    if missing_cols:
        rep.error("FILE", f"thiếu cột bắt buộc: {', '.join(missing_cols)}")

    dupes = [i for i, n in Counter(ids).items() if n > 1 and i]
    for d in dupes:
        rep.error("FILE", f"asset_id trùng: {d}")

    known_ids = set(ids)
    fmt_spec = enums["format"]["values"]
    commercial_eps = {str(e) for e in args.commercial_cta_episodes}
    approved_rank = status_rank(enums, "approved")
    scheduled_rank = status_rank(enums, "scheduled")
    forbidden = [t.strip().lower() for t in args.forbidden_terms if t.strip()]

    for r in rows:
        rid = r.get("asset_id") or "?"

        # -- trường bắt buộc
        for col, spec in asset_cols.items():
            if spec.get("required") and col in r and not (r.get(col) or "").strip():
                rep.error(rid, f"{col} bắt buộc nhưng rỗng")

        # -- enum
        for col, enum_name in (("format", "format"), ("platform", "platform"),
                               ("funnel_stage", "funnel_stage"), ("status", "status"),
                               ("cta_type", "cta_type")):
            val = (r.get(col) or "").strip()
            if val and val not in enum_values(enums, enum_name):
                rep.error(rid, f"{col}='{val}' không thuộc enum {enum_name}")

        # -- khoá ngoại tự tham chiếu
        parent = (r.get("parent_asset_id") or "").strip()
        if parent and parent not in known_ids:
            rep.error(rid, f"parent_asset_id='{parent}' không tồn tại")
        if parent and parent == rid:
            rep.error(rid, "parent_asset_id trỏ vào chính nó")

        # -- ngày
        d = (r.get("planned_publish_date") or "").strip()
        if d and not ISO_DATE.match(d):
            rep.error(rid, f"planned_publish_date='{d}' không phải ISO yyyy-mm-dd")

        # -- hashtag theo định dạng
        fmt = (r.get("format") or "").strip()
        tags = (r.get("hashtags") or "").split()
        rule = fmt_spec.get(fmt, {}) if isinstance(fmt_spec, dict) else {}
        lo, hi = rule.get("hashtag_min"), rule.get("hashtag_max")
        if tags:
            if hi and len(tags) > hi:
                rep.error(rid, f"{len(tags)} hashtag > tối đa {hi} của {fmt}")
            if lo and len(tags) < lo:
                rep.error(rid, f"{len(tags)} hashtag < tối thiểu {lo} của {fmt}")
            bad = [t for t in tags if not re.fullmatch(r"#[\wÀ-ỹ]+", t)]
            for b in bad:
                rep.error(rid, f"hashtag không hợp lệ: {b}")
        elif fmt in ("fb_post", "short", "long_video"):
            rep.warn(rid, f"chưa có hashtag (định dạng {fmt} cần)")

        # -- CTA thương mại
        if (r.get("has_commercial_cta") or "").upper() == "TRUE":
            ep = (r.get("episode_no") or "").strip()
            if commercial_eps and ep not in commercial_eps:
                rep.error(rid, f"CTA thương mại ở tập #{ep}, chỉ cho phép tập "
                               f"#{','.join(sorted(commercial_eps))}")

        # -- cổng kiểm chứng & duyệt
        st = (r.get("status") or "").strip()
        rank = status_rank(enums, st)
        try:
            verif = int(r.get("verification_open") or 0)
        except ValueError:
            verif = 0
            rep.error(rid, "verification_open không phải số")
        if verif > 0 and rank >= scheduled_rank >= 0:
            rep.error(rid, f"còn {verif} chỗ [KIỂM CHỨNG] chưa đóng nhưng status='{st}'")
        if rank >= approved_rank >= 0:
            if not (r.get("approved_by") or "").strip():
                rep.error(rid, f"status='{st}' nhưng thiếu approved_by")
            if not (r.get("approved_at") or "").strip():
                rep.error(rid, f"status='{st}' nhưng thiếu approved_at")
        if st == "published" and not (r.get("platform_native_id") or "").strip():
            rep.error(rid, "status='published' nhưng chưa có platform_native_id")

        # -- HRS
        hrs = (r.get("hrs_score") or "").strip()
        if hrs:
            try:
                if float(hrs) >= 3:
                    rep.warn(rid, "hrs_score ≥ 3 → BẮT BUỘC gắn nhãn 'chưa kiểm chứng đầy đủ'")
            except ValueError:
                rep.error(rid, f"hrs_score='{hrs}' không phải số")
        else:
            rep.warn(rid, "chưa chấm hrs_score")
        if not (r.get("tos_score") or "").strip():
            rep.warn(rid, "chưa chấm tos_score")

        # -- lộ tên tool nội bộ / ký tự hỏng
        blob = " ".join(str(v) for v in r.values()).lower()
        for term in forbidden:
            if term in blob:
                rep.error(rid, f"lộ tên nội bộ '{term}' trong nội dung công khai")
        for col in ("title_draft", "hashtags"):
            if FANCY_UNICODE.search(r.get(col) or ""):
                rep.error(rid, f"{col} chứa ký tự Unicode bold/italic dễ hỏng font")

    return rep


def check_pillars(path: Path, rows: list[dict], rep: Report) -> None:
    with open(path, encoding="utf-8-sig", newline="") as f:
        pillars = list(csv.DictReader(f))
    codes = {p["pillar_code"] for p in pillars}
    for r in rows:
        for col in ("pillar_primary", "pillar_secondary"):
            v = (r.get(col) or "").strip()
            if v and v not in codes:
                rep.error(r.get("asset_id", "?"), f"{col}='{v}' không có trong pillars.csv")
    shares = [float(p["target_share"]) for p in pillars if (p.get("target_share") or "").strip()]
    blank = [p["pillar_code"] for p in pillars if not (p.get("target_share") or "").strip()]
    total = round(sum(shares), 4)
    if blank:
        rep.warn("PILLARS", f"pillar chưa có target_share: {', '.join(blank)} "
                            f"(tổng hiện tại {total})")
    elif total != 1.0:
        rep.error("PILLARS", f"tổng target_share = {total}, phải bằng 1.0")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("calendar")
    ap.add_argument("--pillars")
    ap.add_argument("--commercial-cta-episodes", default="",
                    help="danh sách tập được phép có CTA thương mại, vd '3'")
    ap.add_argument("--forbidden-terms", default="",
                    help="tên tool nội bộ không được lộ, phân cách dấu phẩy")
    ap.add_argument("--strict", action="store_true", help="coi warning là error")
    args = ap.parse_args()
    args.commercial_cta_episodes = [x for x in args.commercial_cta_episodes.split(",") if x]
    args.forbidden_terms = args.forbidden_terms.split(",")

    cal = Path(args.calendar)
    if not cal.exists():
        print(f"Không thấy file: {cal}", file=sys.stderr)
        return 2

    with open(cal, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("Calendar rỗng", file=sys.stderr)
        return 2

    model, enums = load_schema()
    rep = check(rows, model, enums, args)
    if args.pillars:
        check_pillars(Path(args.pillars), rows, rep)

    print(f"── validate_calendar · {cal.name} · {len(rows)} asset ──")
    fmt_count = Counter(r.get("format") for r in rows)
    print("   " + " · ".join(f"{k}={v}" for k, v in sorted(fmt_count.items())))
    today = date.today().isoformat()
    late = [r["asset_id"] for r in rows
            if (r.get("planned_publish_date") or "9999") < today
            and (r.get("status") or "") not in ("published", "measured", "archived")]
    if late:
        rep.warn("LỊCH", f"{len(late)} asset đã quá ngày dự kiến mà chưa published: "
                         f"{', '.join(late[:6])}{' …' if len(late) > 6 else ''}")

    # Gom warning trùng nội dung lại một dòng — nếu không, một lỗi hệ thống
    # lặp trên 31 asset sẽ nhấn chìm những cảnh báo chỉ xuất hiện một lần.
    def emit(items: list[str], mark: str) -> None:
        grouped: dict[str, list[str]] = {}
        for it in items:
            rid, _, msg = it.partition("] ")
            grouped.setdefault(msg, []).append(rid.lstrip("["))
        for msg, rids in grouped.items():
            if len(rids) == 1:
                print(f"  {mark} [{rids[0]}] {msg}")
            else:
                head = ", ".join(rids[:3])
                more = f" … (+{len(rids) - 3})" if len(rids) > 3 else ""
                print(f"  {mark} {msg} — {len(rids)} asset: {head}{more}")

    emit(rep.warnings, "⚠")
    emit(rep.errors, "✖")
    print(f"\n   Errors: {len(rep.errors)} · Warnings: {len(rep.warnings)}")

    if rep.errors:
        return 1
    if args.strict and rep.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

