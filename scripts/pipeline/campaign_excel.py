# -*- coding: utf-8 -*-
"""
Cổng vào/ra duy nhất giữa agent và workbook chiến dịch.

Vì sao tồn tại: nếu agent tự đọc Excel rồi tự quyết "bài này viết được rồi", cổng duyệt
chỉ còn là lời hứa. Ở đây luật cổng nằm trong `schema/model.yml` (khối `stages`), CLI đọc
luật đó và **chỉ trả về asset đã được người tick đúng cột**. Agent không có đường vòng.

    campaign_excel.py status   <wb.xlsx>
    campaign_excel.py list     <wb.xlsx> --stage draft [--json]
    campaign_excel.py approve  <wb.xlsx> --asset <id> --gate approve_topic --by "Duc"
    campaign_excel.py set      <wb.xlsx> --asset <id> --field status --value need_review
    campaign_excel.py content  <wb.xlsx> --asset <id> --type caption --body-file x.md
                               [--variant A] [--hashtags "#a #b"] [--select]
    campaign_excel.py publish-log <wb.xlsx> --asset <id> --platform youtube
                               --mode dry_run --autonomy suggest --status skipped [--error "..."]

Exit: 0 ok · 1 vi phạm luật cổng · 2 không chạy được.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
    from openpyxl import load_workbook
except ImportError as e:
    print(f"Thiếu thư viện: {e}. Cần: pip install pyyaml openpyxl", file=sys.stderr)
    sys.exit(2)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
TRUTHY = {"x", "true", "1", "yes", "y", "có", "co", "✓", "✔", "v"}
# Cột do NGƯỜI sở hữu — agent/script tuyệt đối không ghi qua `set`
HUMAN_ONLY = {"approve_topic", "approve_content", "approve_final",
              "tos_score", "hrs_score", "qa_passed", "approved_by", "approved_at"}


def is_true(v) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in TRUTHY


def load_stages() -> dict:
    with open(SCHEMA_DIR / "model.yml", encoding="utf-8") as f:
        return yaml.safe_load(f).get("stages", {})


class Sheet:
    """Bọc một worksheet; bỏ tiền tố emoji chủ sở hữu khỏi tên cột khi tra."""

    def __init__(self, ws):
        self.ws = ws
        self.col = {}
        for i, c in enumerate(ws[1], start=1):
            name = str(c.value or "").strip()
            for mark in ("🤖", "👤", "⚙️", "⚙"):
                name = name.replace(mark, "")
            self.col[name.strip()] = i

    def rows(self):
        for r in range(2, self.ws.max_row + 1):
            if self.ws.cell(r, 1).value in (None, ""):
                continue
            yield r, {n: self.ws.cell(r, i).value for n, i in self.col.items()}

    def find(self, key_col: str, value: str) -> int | None:
        for r, row in self.rows():
            if str(row.get(key_col) or "").strip() == value:
                return r
        return None

    def set(self, row: int, col: str, value) -> None:
        if col not in self.col:
            raise KeyError(f"sheet không có cột '{col}'")
        self.ws.cell(row, self.col[col], value)

    def append(self, values: dict) -> int:
        r = self.ws.max_row + 1
        while r > 2 and self.ws.cell(r - 1, 1).value in (None, ""):
            r -= 1
        for name, v in values.items():
            if name in self.col:
                self.ws.cell(r, self.col[name], v)
        return r


def open_wb(path: str):
    p = Path(path)
    if not p.exists():
        print(f"Không thấy workbook: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        return load_workbook(p), p
    except PermissionError:
        print("Workbook đang mở trong Excel — đóng file rồi chạy lại.", file=sys.stderr)
        sys.exit(2)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── lệnh ────────────────────────────────────────────────────────────────────
def cmd_status(args) -> int:
    wb, p = open_wb(args.workbook)
    cal = Sheet(wb["03_Calendar"])
    stages = load_stages()
    rows = [r for _, r in cal.rows()]
    print(f"── {p.name} · {len(rows)} asset ──")

    by_status: dict[str, int] = {}
    for r in rows:
        by_status[str(r.get("status") or "?")] = by_status.get(str(r.get("status") or "?"), 0) + 1
    print("   trạng thái: " + " · ".join(f"{k}={v}" for k, v in sorted(by_status.items())))

    for gate in ("approve_topic", "approve_content", "approve_final"):
        n = sum(1 for r in rows if is_true(r.get(gate)))
        print(f"   {gate}: {n}/{len(rows)} đã tick")

    print("   sẵn sàng theo stage:")
    for name in stages:
        n = len(eligible(rows, name, stages))
        print(f"      {name:<8} {n}")
    return 0


def eligible(rows: list[dict], stage: str, stages: dict) -> list[dict]:
    spec = stages.get(stage)
    if not spec:
        raise SystemExit(f"stage không hợp lệ: {stage}. Có: {', '.join(stages)}")
    ok = []
    for r in rows:
        if str(r.get("status") or "").strip() not in spec["from_status"]:
            continue
        gate = spec.get("requires_gate")
        if gate and not is_true(r.get(gate)):
            continue
        ok.append(r)
    return ok


def cmd_list(args) -> int:
    wb, _ = open_wb(args.workbook)
    rows = [r for _, r in Sheet(wb["03_Calendar"]).rows()]
    stages = load_stages()
    spec = stages[args.stage]
    ok = eligible(rows, args.stage, stages)

    if args.json:
        print(json.dumps(ok, ensure_ascii=False, default=str, indent=2))
        return 0

    gate = spec.get("requires_gate") or "—"
    print(f"── stage '{args.stage}' · cần status ∈ {spec['from_status']} · cổng: {gate}")
    if not ok:
        blocked = [r for r in rows if str(r.get("status") or "") in spec["from_status"]]
        if blocked and spec.get("requires_gate"):
            print(f"   0 asset. {len(blocked)} asset đúng trạng thái nhưng CHƯA tick '{gate}':")
            for r in blocked[:8]:
                print(f"      {r.get('asset_id')} — {str(r.get('title_draft') or '')[:60]}")
            print("   → Người phải tick cột đó trong Excel (hoặc dùng lệnh approve).")
        else:
            print("   0 asset đủ điều kiện.")
        return 0
    for r in ok:
        print(f"   {r.get('asset_id'):<22} {str(r.get('format') or ''):<12} "
              f"{str(r.get('title_draft') or '')[:56]}")
    print(f"   → {len(ok)} asset. Sau khi xử lý, đặt status = '{spec['to_status']}'.")
    return 0


def cmd_approve(args) -> int:
    wb, p = open_wb(args.workbook)
    sh = Sheet(wb["03_Calendar"])
    row = sh.find("asset_id", args.asset)
    if row is None:
        print(f"Không thấy asset {args.asset}", file=sys.stderr)
        return 1
    if args.gate not in ("approve_topic", "approve_content", "approve_final"):
        print("gate phải là approve_topic | approve_content | approve_final", file=sys.stderr)
        return 1
    sh.set(row, args.gate, "x")
    if args.gate == "approve_final":
        sh.set(row, "approved_by", args.by)
        sh.set(row, "approved_at", now())
    ap = Sheet(wb["05_Approval"])
    existing = sum(1 for _, r in ap.rows() if str(r.get("asset_id")) == args.asset)
    ap.append({
        "review_id": f"{args.asset}-R{existing + 1}",
        "asset_id": args.asset, "round_no": existing + 1,
        "reviewer": args.by, "decision": "Approved",
        "decided_at": now(), "comment": args.comment or "",
    })
    wb.save(p)
    print(f"✅ {args.asset}: tick {args.gate} bởi {args.by} (vòng {existing + 1})")
    return 0


def cmd_set(args) -> int:
    if args.field in HUMAN_ONLY:
        print(f"✖ '{args.field}' là cột của NGƯỜI — script không được ghi. "
              f"Dùng lệnh approve, hoặc sửa tay trong Excel.", file=sys.stderr)
        return 1
    wb, p = open_wb(args.workbook)
    sh = Sheet(wb["03_Calendar"])
    row = sh.find("asset_id", args.asset)
    if row is None:
        print(f"Không thấy asset {args.asset}", file=sys.stderr)
        return 1
    sh.set(row, args.field, args.value)
    wb.save(p)
    print(f"✅ {args.asset}.{args.field} = {args.value}")
    return 0


def cmd_content(args) -> int:
    wb, p = open_wb(args.workbook)
    cal = Sheet(wb["03_Calendar"])
    if cal.find("asset_id", args.asset) is None:
        print(f"Không thấy asset {args.asset} trong 03_Calendar", file=sys.stderr)
        return 1
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else (args.body or "")
    if not body.strip():
        print("Nội dung rỗng — từ chối ghi.", file=sys.stderr)
        return 1
    sh = Sheet(wb["04_Content"])
    cid = f"{args.asset}-{args.type}-{args.variant}"
    row = sh.find("content_id", cid)
    vals = {
        "content_id": cid, "asset_id": args.asset, "content_type": args.type,
        "variant": args.variant, "body": body, "char_count": len(body),
        "hashtags": args.hashtags or "", "language": args.language,
        "draft_path": args.draft_path or "", "ai_generated": "TRUE",
        "generated_at": now(), "is_selected": "TRUE" if args.select else "",
    }
    if row:
        for k, v in vals.items():
            if k in sh.col:
                sh.set(row, k, v)
        action = "cập nhật"
    else:
        sh.append(vals)
        action = "thêm"
    wb.save(p)
    print(f"✅ {action} 04_Content: {cid} ({len(body)} ký tự)")
    return 0


def cmd_publish_log(args) -> int:
    wb, p = open_wb(args.workbook)
    if args.mode == "live" and args.autonomy != "full":
        print(f"✖ CHẶN: mode=live nhưng autonomy='{args.autonomy}'. "
              f"Chỉ 'full' mới được đăng thật.", file=sys.stderr)
        return 1
    cal = Sheet(wb["03_Calendar"])
    row = cal.find("asset_id", args.asset)
    if row is None:
        print(f"Không thấy asset {args.asset}", file=sys.stderr)
        return 1
    asset = {n: cal.ws.cell(row, i).value for n, i in cal.col.items()}
    if not is_true(asset.get("approve_final")):
        print(f"✖ CHẶN: {args.asset} chưa tick approve_final.", file=sys.stderr)
        return 1
    try:
        verif = int(asset.get("verification_open") or 0)
    except (TypeError, ValueError):
        verif = 0
    if verif > 0:
        print(f"✖ CHẶN: còn {verif} chỗ [KIỂM CHỨNG] chưa đóng.", file=sys.stderr)
        return 1

    sh = Sheet(wb["06_Publish_Log"])
    n = sum(1 for _, r in sh.rows()
            if str(r.get("asset_id")) == args.asset and str(r.get("platform")) == args.platform)
    sh.append({
        "run_id": f"{args.asset}-{args.platform}-{n + 1}", "asset_id": args.asset,
        "platform": args.platform, "attempt_no": n + 1, "mode": args.mode,
        "autonomy_at_run": args.autonomy, "requested_at": now(),
        "scheduled_for": args.scheduled_for or "", "status": args.status,
        "platform_native_id": args.native_id or "", "live_url": args.live_url or "",
        "error_message": args.error or "",
    })
    if args.status == "published" and args.native_id:
        cal.set(row, "platform_native_id", args.native_id)
        cal.set(row, "live_url", args.live_url or "")
        cal.set(row, "actual_publish_datetime", now())
        cal.set(row, "status", "published")
    wb.save(p)
    print(f"✅ 06_Publish_Log: {args.asset} · {args.platform} · {args.mode} · {args.status}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status"); p.add_argument("workbook"); p.set_defaults(fn=cmd_status)

    p = sub.add_parser("list"); p.add_argument("workbook")
    p.add_argument("--stage", required=True)
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_list)

    p = sub.add_parser("approve"); p.add_argument("workbook")
    p.add_argument("--asset", required=True); p.add_argument("--gate", required=True)
    p.add_argument("--by", required=True); p.add_argument("--comment")
    p.set_defaults(fn=cmd_approve)

    p = sub.add_parser("set"); p.add_argument("workbook")
    p.add_argument("--asset", required=True); p.add_argument("--field", required=True)
    p.add_argument("--value", required=True); p.set_defaults(fn=cmd_set)

    p = sub.add_parser("content"); p.add_argument("workbook")
    p.add_argument("--asset", required=True); p.add_argument("--type", required=True)
    p.add_argument("--variant", default="final"); p.add_argument("--body")
    p.add_argument("--body-file"); p.add_argument("--hashtags")
    p.add_argument("--language", default="vi"); p.add_argument("--draft-path")
    p.add_argument("--select", action="store_true"); p.set_defaults(fn=cmd_content)

    p = sub.add_parser("publish-log"); p.add_argument("workbook")
    p.add_argument("--asset", required=True); p.add_argument("--platform", required=True)
    p.add_argument("--mode", default="dry_run", choices=["dry_run", "live"])
    p.add_argument("--autonomy", default="suggest", choices=["suggest", "auto_safe", "full"])
    p.add_argument("--status", default="skipped")
    p.add_argument("--native-id"); p.add_argument("--live-url")
    p.add_argument("--scheduled-for"); p.add_argument("--error")
    p.set_defaults(fn=cmd_publish_log)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
