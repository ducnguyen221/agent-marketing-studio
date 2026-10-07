#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto Pipeline by Calendar — Điều phối tự động theo lịch chiến dịch (2 Pha).

## Mục đích
Thay vì chỉ chạy một lượt ad-hoc, module này bám sát timeline trong `campaign.md`
và phân phối nội dung theo lịch:
1. Pha 1 (Reconciliation - Đối soát): Kiểm tra các bài đã đăng hoặc hẹn giờ (fb-state.json),
   tự động gắn comment và chia sẻ vào Group khi bài đã phát sóng.
2. Pha 2 (Calendar Execution - Thực thi theo lịch):
   - Quét bài đến hạn hôm nay (due_today) và bài quá hạn an toàn <= lookback_days.
   - Chặn bão bài quá hạn lâu (> 7 ngày) vào stale_overdue.
   - Hybrid Mode:
     - Bài đã qua Cổng 2 -> Xuất bản ngay ra Web, Page & Group share teaser.
     - Bài mới có ý tưởng:
       - Autonomy full -> tự động đẩy chuỗi dựng bài.
       - Autonomy suggest -> dừng tại Cổng 2, ghi nhận waiting_approval và thoát sạch.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
sys.path.insert(0, str(_HERE))

import approval_gate as AG  # noqa: E402
import fb_publish as FB  # noqa: E402
import md_io  # noqa: E402
import pipeline_state as PS  # noqa: E402
import run_pipeline as RP  # noqa: E402
import studio_paths as SP  # noqa: E402


def _tim_fb_config(campaign_dir: Path) -> dict | None:
    """Tìm cấu hình Facebook từ biến môi trường, secret pointer hoặc file config."""
    cand_files = [
        campaign_dir / "facebook_config.json",
        campaign_dir / "fb_config.json",
    ]
    fb_env = SP.secret_env("FB_CONFIG")
    if fb_env and os.path.isfile(fb_env):
        cand_files.insert(0, Path(fb_env))

    for cf in cand_files:
        if cf.is_file():
            try:
                return FB._cfg(str(cf))
            except Exception:
                continue
    return None


def run_calendar_pipeline(
    campaign: Path | str,
    *,
    target_date: date | str | None = None,
    lookback_days: int = 3,
    max_posts_per_run: int = 3,
    share_to_group: str = "",
    station: str | None = None,
    dry_run: bool = False,
    attach_fn=None,
    release_fn=None,
    step_runner=None,
) -> dict:
    """Hàm lõi thực thi pipeline 2 pha theo lịch chiến dịch."""
    camp_path = Path(campaign).resolve()
    campaign_dir = camp_path if camp_path.is_dir() else camp_path.parent
    campaign_file = campaign_dir / "campaign.md"
    if not campaign_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy {campaign_file}")

    if target_date is None:
        cur_date = date.today()
    elif isinstance(target_date, str):
        cur_date = date.fromisoformat(target_date.strip())
    else:
        cur_date = target_date

    # ══════════════════════════════════════════════════════════════════════════
    # PHA 1: RECONCILIATION (ĐỐI SOÁT & HOÀN TẤT DỞ DANG)
    # ══════════════════════════════════════════════════════════════════════════
    reconciliation_results: list[dict] = []
    fb_cfg = None if dry_run else _tim_fb_config(campaign_dir)

    if dry_run:
        # Dry-run: quét các file state để phát hiện bài cần đối soát mà không đọc secret
        for sf in sorted(campaign_dir.rglob(FB.TRANG_THAI)):
            try:
                sd = json.loads(sf.read_text(encoding="utf-8"))
                needs_cmt = not bool(sd.get("comment_id"))
                st_target = sd.get("share_to_group_id") or (sd.get("group_share") or {}).get("group_id") or share_to_group
                needs_sh = bool(st_target and (sd.get("group_share") or {}).get("status") != "shared")
                if needs_cmt or needs_sh:
                    reconciliation_results.append({
                        "file": str(sf),
                        "post_id": sd.get("post_id", ""),
                        "status": "would_reconcile",
                        "needs_comment": needs_cmt,
                        "needs_share": needs_sh,
                    })
                else:
                    reconciliation_results.append({
                        "file": str(sf),
                        "post_id": sd.get("post_id", ""),
                        "status": "done",
                    })
            except Exception as e:
                reconciliation_results.append({
                    "file": str(sf),
                    "status": "error",
                    "reason": str(e),
                })
    else:
        if attach_fn:
            reconciliation_results = attach_fn(campaign_dir)
        elif fb_cfg:
            try:
                reconciliation_results = FB.attach_pending(fb_cfg, campaign_dir)
            except Exception as e:
                reconciliation_results.append({
                    "status": "failed",
                    "reason": f"attach_pending error: {e}",
                })
        else:
            # Chỉ cảnh báo nếu thực sự có file state dở dang cần đối soát
            pending_files = list(campaign_dir.rglob("fb-state.json"))
            has_pending = False
            for pf in pending_files:
                try:
                    sd = json.loads(pf.read_text(encoding="utf-8"))
                    needs_comment = not bool(sd.get("comment_id"))
                    share_target = sd.get("share_to_group_id") or (sd.get("group_share") or {}).get("group_id")
                    needs_share = bool(share_target and (sd.get("group_share") or {}).get("status") != "shared")
                    if needs_comment or needs_share:
                        has_pending = True
                        break
                except Exception:
                    pass
            if has_pending:
                reconciliation_results.append({
                    "status": "skipped",
                    "reason": "Có bài cần đối soát nhưng chưa cấu hình facebook_config để gọi Graph API",
                })

    # ══════════════════════════════════════════════════════════════════════════
    # PHA 2: CALENDAR EXECUTION (THỰC THI THEO LỊCH)
    # ══════════════════════════════════════════════════════════════════════════
    _, _, _, rows = AG.read_content_table(campaign_dir)

    due_today: list[dict] = []
    overdue_recoverable: list[dict] = []
    stale_overdue: list[dict] = []
    overdue_ignored: list[dict] = []
    upcoming: list[dict] = []
    already_published: list[dict] = []
    unscheduled: list[dict] = []

    for r in rows:
        cid = r.get("content_id", "")
        pub = (r.get("published") or "").strip()
        if pub:
            already_published.append(r)
            continue

        sched_str = (r.get("schedule") or "").strip()
        if not sched_str:
            unscheduled.append(r)
            continue

        try:
            sched_date = date.fromisoformat(sched_str)
        except ValueError:
            unscheduled.append(r)
            continue

        delta = (cur_date - sched_date).days
        if delta == 0:
            due_today.append(r)
        elif delta > 0:
            max_rec = min(lookback_days, 7)
            if delta <= max_rec:
                overdue_recoverable.append(r)
            elif delta > 7:
                stale_overdue.append(r)
            else:
                overdue_ignored.append(r)
        else:
            upcoming.append(r)

    candidates = due_today + overdue_recoverable
    to_execute = candidates[:max_posts_per_run]
    throttled = candidates[max_posts_per_run:]

    executed_results: list[dict] = []
    waiting_approval_results: list[dict] = []

    for r in to_execute:
        cid = r.get("content_id", "")
        folder = (r.get("folder") or "").strip().lstrip("./")
        post_dir = campaign_dir / folder if folder else campaign_dir
        step = PS.next_step(campaign_dir, r)

        level, src = FB._muc_tu_tri(str(post_dir) if post_dir.is_dir() else str(campaign_dir), station)

        # ── Nhánh A: Sẵn sàng phát hành (chỉ duy nhất khi đã qua Cổng 2 / Cổng 3 và tới bước release) ──────────────
        if step == "release":
            if dry_run:
                executed_results.append({
                    "post": cid,
                    "step": step,
                    "action": "dry_run_release",
                    "status": "ready_to_publish",
                })
            else:
                if release_fn:
                    res = release_fn(campaign_dir, cid, share_to_group=share_to_group)
                else:
                    import campaign_step as CS
                    def custom_run_cmd(cmd, **kw):
                        is_fb = any(("fb_publish" in str(arg) or "post_facebook" in str(arg)) for arg in cmd)
                        if share_to_group and is_fb:
                            if "--share-to-group" not in cmd:
                                cmd = list(cmd) + ["--share-to-group", share_to_group]
                        elif share_to_group and any("facebook" in str(arg).lower() for arg in cmd):
                            sys.stderr.write(f"[WARN] facebook hook không nhận diện được để inject --share-to-group: {cmd}\n")
                        import subprocess
                        return subprocess.run(
                            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            stdin=subprocess.DEVNULL, env=SP.hook_env(), **kw)

                    res = CS.step_release(campaign_dir, bot=None, only_post=cid, run_cmd=custom_run_cmd)

                # Kiểm tra lỗi phát hành lồng nhau
                failed_items = [f for f in (res.get("failed") or []) if f.get("post") in (cid, "*")] if isinstance(res, dict) else []
                if failed_items:
                    executed_results.append({
                        "post": cid,
                        "step": step,
                        "action": "release_failed",
                        "error": "; ".join(f.get("reason", "") for f in failed_items),
                        "result": res,
                    })
                else:
                    executed_results.append({
                        "post": cid,
                        "step": step,
                        "action": "released",
                        "result": res,
                    })

        # ── Nhánh B: Đang chờ duyệt Cổng người (G1, G2, hoặc G3) ──────────────
        elif step in PS.NEEDS_HUMAN:
            gate = step.replace("await-", "").lower()
            gate_info = AG.post_files(campaign_dir, r)
            gate_info["gate"] = gate
            if gate == "g2":
                gate_info["not_ready"] = AG.why_not_ready(campaign_dir, r)
            waiting_approval_results.append({
                "post": cid,
                "step": step,
                "gate": gate,
                "content_name": r.get("content_name", ""),
                "info": gate_info,
            })

        # ── Nhánh C: Các bước máy móc trước Cổng (Just-in-Time) ───────────────
        else:
            if dry_run:
                executed_results.append({
                    "post": cid,
                    "step": step,
                    "action": f"dry_run_advance_{step}",
                    "level": level,
                })
            else:
                until_step = None if level == "full" else "await-G2"
                pipe_res = RP.run(
                    campaign_dir,
                    mode="per-post",
                    post=[cid],
                    until=until_step,
                    run_step=step_runner,
                )
                if pipe_res.get("failed"):
                    executed_results.append({
                        "post": cid,
                        "step": step,
                        "action": "advance_failed",
                        "error": "; ".join(f.get("message", f.get("step", "")) for f in pipe_res.get("failed", [])),
                        "pipeline_result": pipe_res,
                    })
                else:
                    executed_results.append({
                        "post": cid,
                        "step": step,
                        "action": "advanced",
                        "pipeline_result": pipe_res,
                    })
                # Kiểm tra nếu sau khi chạy đã dừng ở cổng
                if pipe_res.get("waiting"):
                    for g_name, w_list in pipe_res["waiting"].items():
                        for w_item in w_list:
                            waiting_approval_results.append({
                                "post": w_item.get("content_id", cid),
                                "step": f"await-{g_name.upper()}",
                                "gate": g_name.lower(),
                                "content_name": w_item.get("content_name", ""),
                                "info": w_item,
                            })

    return {
        "campaign": str(campaign_dir),
        "target_date": cur_date.isoformat(),
        "lookback_days": lookback_days,
        "max_posts_per_run": max_posts_per_run,
        "dry_run": dry_run,
        "phase1_reconciliation": reconciliation_results,
        "phase2_calendar": {
            "due_today": [r["content_id"] for r in due_today],
            "overdue_recoverable": [r["content_id"] for r in overdue_recoverable],
            "stale_overdue": [r["content_id"] for r in stale_overdue],
            "overdue_ignored": [r["content_id"] for r in overdue_ignored],
            "throttled": [r["content_id"] for r in throttled],
            "executed": executed_results,
            "waiting_approval": waiting_approval_results,
        },
    }


def format_report(result: dict) -> str:
    """Định dạng báo cáo kết quả thực thi dạng Markdown trực quan."""
    lines = [
        "# Báo cáo Vận hành Lịch Chiến dịch (Auto Pipeline by Calendar)",
        f"- **Chiến dịch**: `{result.get('campaign')}`",
        f"- **Ngày mục tiêu**: `{result.get('target_date')}`",
        f"- **Ngưỡng quét bù (lookback)**: `{result.get('lookback_days')} ngày`",
        f"- **Trần bài / lượt**: `{result.get('max_posts_per_run')}`",
        f"- **Chế độ**: `{'DRY-RUN (Thử nghiệm)' if result.get('dry_run') else 'THỰC THI THẬT'}`",
        "",
        "## Pha 1: Đối soát & Hoàn tất Dở dang (Reconciliation)",
    ]

    p1 = result.get("phase1_reconciliation", [])
    if not p1:
        lines.append("  (Không có bài nào dở dang cần đối soát)")
    else:
        for r in p1:
            st = r.get("status", "unknown")
            pid = r.get("post_id", "-")
            if st in ("failed", "error"):
                lines.append(f"  - ❌ Post `{pid}`: **{st.upper()}** — {r.get('reason') or ''}")
            elif st == "skipped":
                lines.append(f"  - ⚠️ Post `{pid}`: **{st.upper()}** — {r.get('reason') or ''}")
            else:
                lines.append(f"  - ✅ Post `{pid}`: **{st.upper()}** {r.get('reason') or ''}")

    lines.extend([
        "",
        "## Pha 2: Thực thi theo Lịch (Calendar Execution)",
    ])
    p2 = result.get("phase2_calendar", {})
    lines.append(f"- **Đến hạn hôm nay ({len(p2.get('due_today', []))})**: {', '.join(p2.get('due_today', [])) or '(không có)'}")
    lines.append(f"- **Quá hạn trong ngưỡng an toàn ({len(p2.get('overdue_recoverable', []))})**: {', '.join(p2.get('overdue_recoverable', [])) or '(không có)'}")
    
    ignored = p2.get("overdue_ignored", [])
    if ignored:
        lines.append(f"- ⏳ **Quá hạn ngoài ngưỡng bù ({len(ignored)})**: `{', '.join(ignored)}` (vượt lookback nhưng <= 7 ngày)")

    stale = p2.get("stale_overdue", [])
    if stale:
        lines.append(f"- ⚠️ **Quá hạn lâu (> 7 ngày) - ĐÃ CHẶN TỰ ĐỘNG ({len(stale)})**: `{', '.join(stale)}`")
        lines.append("  *Cần người vận hành kiểm tra và cập nhật lại lịch trong campaign.md!*")

    throttled = p2.get("throttled", [])
    if throttled:
        lines.append(f"- ⏳ **Tạm hoãn do vượt trần ({len(throttled)})**: {', '.join(throttled)}")

    lines.append("")
    lines.append("### Kết quả Thực thi:")
    executed = p2.get("executed", [])
    if not executed:
        lines.append("  (Không có tác vụ thực thi nào)")
    else:
        for ex in executed:
            act = ex.get('action')
            post = ex.get('post')
            step = ex.get('step')
            if "failed" in str(act):
                lines.append(f"  - ❌ **{post}**: `{act}` (step: `{step}`) — Lỗi: {ex.get('error') or 'không xác định'}")
            else:
                lines.append(f"  - ✅ **{post}**: `{act}` (step: `{step}`)")

    waiting = p2.get("waiting_approval", [])
    if waiting:
        lines.append("")
        lines.append(f"### ⛔ Cần người duyệt ({len(waiting)} bài):")
        for w in waiting:
            lines.append(f"  - **{w.get('post')}** (`{w.get('step')}`): {w.get('content_name')}")
            info = w.get("info", {})
            if info.get("not_ready"):
                lines.append(f"      ⚠️ Lý do: {info.get('not_ready')}")
            for lbl, pth in info.get("file", {}).items():
                p_abs = Path(pth).resolve()
                lines.append(f"      · {lbl}: [{p_abs.name}]({p_abs.as_uri()}) (`{p_abs}`)")

    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Auto Pipeline by Calendar — vận hành theo lịch chiến dịch.")
    ap.add_argument("campaign", help="Đường dẫn tới thư mục chiến dịch hoặc file campaign.md")
    ap.add_argument("--date", default="", help="Ngày thực thi YYYY-MM-DD (mặc định: hôm nay)")
    ap.add_argument("--lookback", type=int, default=3, help="Số ngày cho phép đăng bù (mặc định 3)")
    ap.add_argument("--max-posts", type=int, default=3, help="Số bài tối đa xuất bản mỗi lượt (mặc định 3)")
    ap.add_argument("--share-to-group", default="", help="Facebook Group ID để chia sẻ bài viết kèm teaser")
    ap.add_argument("--station", default=None, help="Trạm chứa CHANNELS.md")
    ap.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm không gọi API hay ghi file")
    ap.add_argument("--json", action="store_true", help="Xuất kết quả JSON")
    args = ap.parse_args(argv)

    try:
        t_date = args.date.strip() if args.date else None
        res = run_calendar_pipeline(
            args.campaign,
            target_date=t_date,
            lookback_days=args.lookback,
            max_posts_per_run=args.max_posts,
            share_to_group=args.share_to_group,
            station=args.station,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(format_report(res))
        return 0
    except Exception as e:
        sys.stderr.write(f"calendar_pipeline error: {e}\n")
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
