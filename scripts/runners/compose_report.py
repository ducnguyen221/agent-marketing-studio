# -*- coding: utf-8 -*-
"""compose_report.py — biến log máy thành TIN NGƯỜI ĐỌC cho Telegram.

VÌ SAO CÓ FILE NÀY:
Tin báo cũ dán thẳng marker (`FB_POST_ID=... FB_MODE=... STATUS=...`) và danh sách link.
Đọc lúc 6 giờ sáng thì không trả lời được câu duy nhất cần biết: **việc của tôi xong chưa,
có gì cần làm không?** Người phải tự dịch marker sang nghĩa — đó là việc của máy.

File này đọc log, đối chiếu ĐIỀU KIỆN CỤ THỂ, rồi viết câu tiếng Việt. Nguyên tắc:
- Chỉ kể thứ THẬT SỰ xảy ra. Không có bước nào thì không nhắc bước đó.
- Bất thường phải nói TRƯỚC cái bình thường (người đọc lướt, đọc 2 dòng đầu là đóng).
- Vẫn giữ ĐỦ LINK sản phẩm (luật E2) nhưng để cuối, sau phần diễn giải.
- Hỏng thì nói HỎNG Ở ĐÂU + ĐÃ XONG TỚI ĐÂU, không dán traceback.

DÙNG (notify-run.ps1 gọi, đọc kết quả qua FILE để tránh mojibake console):
    python compose_report.py --title "..." --exit 0 --duration "00:29:13" \
        --log <file.log> --out <report.txt>

Kỷ luật: hỏng thì KHÔNG ghi gì ra --out, để notify-run rơi về định dạng cũ.
Một cải tiến báo cáo mà làm mất luôn báo cáo thì tệ hơn không có.
"""
import argparse
import io
import os
import re
import sys


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def humanize_duration(d):
    """'00:29:13' -> '29 phút'. Người không cần độ chính xác tới giây."""
    m = re.match(r"(\d+):(\d+):(\d+)", d or "")
    if not m:
        return d or ""
    h, mi, s = (int(x) for x in m.groups())
    if h:
        return f"{h} tiếng {mi} phút" if mi else f"{h} tiếng"
    if mi:
        return f"{mi} phút"
    return f"{s} giây"


def _khi(iso):
    """'2026-08-18T20:10' -> 'hôm nay lúc 20:10' / 'ngày mai lúc 09:00' / '20/08 lúc 09:00'.

    Người đọc tin lúc nửa đêm cần biết 'bao giờ' theo cách người nói, không phải ISO.
    """
    import datetime as dt
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", iso or "")
    if not m:
        return iso
    y, mo, d, hh, mi = (int(x) for x in m.groups())
    try:
        day = dt.date(y, mo, d)
    except ValueError:
        return iso
    delta = (day - dt.date.today()).days
    khi = {0: "hôm nay", 1: "ngày mai", -1: "hôm qua"}.get(delta, f"{d:02d}/{mo:02d}")
    return f"{khi} lúc {hh:02d}:{mi:02d}"


def _co(b):
    """Byte -> '3,00 GB' / '7,0 MB' (dấu phẩy thập phân, như người Việt đọc)."""
    b = int(b)
    s = f"{b / 1024 ** 3:.2f} GB" if b >= 1024 ** 3 else f"{b / 1024 ** 2:.1f} MB"
    return s.replace(".", ",")


TEN_TRAM = {"marketing": "marketing", "giong": "giọng", "video": "video", "trash": "thùng rác"}


def find(rx, text, group=1, default=""):
    m = re.search(rx, text)
    return m.group(group) if m else default


def build(title, code, duration, log):
    ok = code == 0
    L = []                                   # các câu kể
    warn = []                                # bất thường -> đẩy lên đầu
    links = []

    # ── YouTube ──────────────────────────────────────────────────────────────
    yt = re.findall(r"PUBLISHED (https://youtu\.be/[\w-]+)", log)
    if not yt:
        yt = ["https://youtu.be/" + v for v in re.findall(r"VIDEO_ID=([\w-]{6,})", log)]
    yt = list(dict.fromkeys(yt))
    if len(yt) >= 2:
        L.append("Video dài và bản ngắn đã lên YouTube.")
    elif len(yt) == 1:
        L.append("Video đã lên YouTube.")
        warn.append("Chỉ thấy 1 video trên YouTube — thường phải có cả bản dài và bản ngắn.")
    elif "skip YouTube upload" in log or "bo qua upload" in log:
        L.append("Bỏ qua YouTube (chạy ở chế độ không upload).")
    links += yt

    # ── Facebook ─────────────────────────────────────────────────────────────
    mode = find(r"FB_MODE=([a-z-]+)", log)
    status = find(r"FB_REEL_COVER=\S+\s+(?:FB_REEL_AT=\S+\s+)?(?:FB_MODE=\S+\s+)?"
                  r"(?:FB_COMMENT_ID=\S+\s+)?STATUS=(.+)", log).strip()
    if not status:
        status = find(r"FB status: (.+)", log).strip()
    reel_id = find(r"FB_REEL_ID=(\d+)", log)
    cmt_id = find(r"FB_COMMENT_ID=([\w-]+)", log)
    fb_txt = find(r"FB: (chưa thiết lập token|thiếu facebook_post|brief không có facebook_post)", log)

    if fb_txt:
        warn.append(f"Không đăng được Facebook: {fb_txt}.")
    elif status.startswith("error"):
        chi_tiet = status[6:].strip()
        # PHÂN BIỆT cho rõ: lỗi comment ≠ mất bài. Gộp chung làm người đọc tưởng
        # bài không lên, hốt hoảng vô ích lúc nửa đêm.
        if chi_tiet.startswith("comment:") and reel_id:
            L.append("Trên Facebook, Reel đã đăng kèm bài viết đầy đủ.")
            warn.append("Reel LÊN BÌNH THƯỜNG, nhưng comment chứa link không gắn được: "
                        + chi_tiet[8:].strip()[:140]
                        + ". Người xem sẽ không có đường về website.")
            links.append(f"https://www.facebook.com/reel/{reel_id}")
        else:
            warn.append("Đăng Facebook LỖI: " + chi_tiet[:160] + ".")
    elif status.startswith("scheduled@"):
        L.append(f"Bài Facebook đã hẹn đăng {_khi(status.split('@', 1)[1])}.")
        if reel_id:
            links.append(f"https://www.facebook.com/reel/{reel_id}")
    elif reel_id:
        if mode == "reel-main":
            L.append("Trên Facebook, Reel đã đăng kèm bài viết đầy đủ.")
        else:
            L.append("Đã đăng Facebook.")
        if cmt_id and cmt_id != "-":
            L.append("Comment chứa link cũng đã tự gắn ngay dưới bài.")
        elif "--comment-file" in log or "fb-comment" in log:
            warn.append("Reel đã lên nhưng COMMENT LINK không gắn được — người xem sẽ "
                        "không có đường về website.")
        links.append(f"https://www.facebook.com/reel/{reel_id}")

    if "FB_REEL_COVER=failed" in log:
        warn.append("Ảnh bìa Reel đặt không thành công (Reel vẫn lên bình thường).")

    # ── Web + sổ sách ────────────────────────────────────────────────────────
    if re.search(r"git: .*main -> main", log) or "DONE. Page:" in log:
        L.append("Trang web đã cập nhật.")
    page = find(r"DONE\. Page: (\S+)", log)
    if page:
        links.append(page)
    if "EXCEL_OK" in log:
        L.append("Đã ghi sổ Auto Task.")
    elif "xlsx-pending" in log or "pending" in log.lower() and "EXCEL" in log:
        warn.append("Không ghi được Excel — file đang mở? Bản tạm đã lưu cạnh script.")

    covered = find(r"Covered log: \+(\S+) \(tong (\d+)", log)
    if covered:
        n = find(r"Covered log: \+\S+ \(tong (\d+)", log)
        L.append(f"Đã ghi repo <b>{esc(covered)}</b> vào sổ chống lặp (tổng {n}).")

    # ── Hậu kiểm độ phủ (bài của LẦN TRƯỚC) ──────────────────────────────────
    rs = find(r"FB_REACH_STATUS=(\w+)", log)
    rn = find(r"FB_REACH_STATUS=\w+ n=(\d+)", log)
    rl = find(r"FB_REACH_STATUS=\w+ n=\d+ low=(\d+)", log)
    reach = ""
    if rs == "low" and rl and rn:
        # Vách ngăn "LƯỢT TRƯỚC" là BẮT BUỘC, không phải trang trí: khối này nói về bài CŨ,
        # nhưng nó nằm ngay dưới đoạn báo thành công của lượt HIỆN TẠI. Đêm 05/09/2026 Đức
        # đọc tin ✅ của số W36 và tưởng lượt chạy hỏng, chỉ vì dòng 📉 đứng sát bên dưới.
        reach = (f"📉 <b>Các bài đăng TRƯỚC ĐÓ</b> (không liên quan lượt này): "
                 f"<b>{rl}/{rn} bài chưa có ai xem hay tương tác.</b> "
                 "Bài lên được nhưng Facebook chưa đẩy tới ai.")
    elif rs == "ok" and rn:
        reach = f"📈 {rn} bài đăng trước đó đều có người xem — phân phối đang chạy."
    elif rs == "error":
        warn.append("Không kiểm được độ phủ của bài trước.")

    # ── Truyện: quá trần rồi tự chạy tiếp (story/resume_once.py, P1-23) ─────────
    rs_tu = find(r"RESUME_ONCE=start from=(\S+)", log)
    if rs_tu:
        dai = find(r"RESUME_ONCE=start from=\S+ range=(\S+)", log)
        tu = "dựng video (đã đọc đủ chương)" if rs_tu == "build" else f"chương {rs_tu}"
        warn.append(f"Lượt đầu quá trần — đã tự chạy tiếp MỘT lần từ {tu}"
                    + (f" (dải {dai})" if dai else "") + ", dùng cache chương đã đọc.")
        if "RESUME_ONCE=done code=124" in log:
            warn.append("Lượt chạy tiếp CŨNG quá trần — đã dừng, không lặp. Cache chương còn "
                        "nguyên: lượt theo lịch kế tiếp đọc tiếp đúng dải (hoặc kickstart tay).")
    if "RESUME_ONCE=skip reason=publish" in log or "PUBLISH_GUARD=blocked" in log:
        warn.append("Lượt truyện bị dừng lúc ĐANG ĐĂNG — KHÔNG tự chạy lại (kể cả lượt theo lịch "
                    "đêm sau) để tránh đăng trùng. Kiểm kênh YouTube rồi chạy lệnh in trong log: "
                    "ĐÃ có tập ⇒ daily_truyen.py --confirm-published (tự ghi last_end/next_url); "
                    "CHƯA có ⇒ --clear-publish-guard.")
    elif "RESUME_ONCE=skip reason=no-mark" in log:
        warn.append("Quá trần nhưng không còn dấu dải dở (_resume.json) — không tự chạy tiếp; "
                    "lượt theo lịch kế tiếp chạy lại từ đầu dải.")

    # ── Render kẹt (video-studio `RENDER_STUCK:` · preflight mã 5 · Navigation timeout) ──
    # `Navigation timeout` chỉ tính khi lượt HỎNG: render_project in stderr của mọi lần thử
    # hỏng, kể cả khi lần sau qua — lượt ✅ không được mang cảnh báo kẹt.
    ket = ("RENDER_STUCK" in log or "RENDER_PREFLIGHT=stuck" in log
           or (not ok and "Navigation timeout" in log))
    if ket:
        warn.append("MÔI TRƯỜNG RENDER KẸT (HyperFrames không mở được trang) — khởi động lại "
                    "máy rồi chạy lại (kiểm nhanh: video-studio probe).")
    elif "RENDER_PREFLIGHT=failed" in log:
        warn.append("Phép thử render hỏng TRƯỚC các bước tốn kém (chưa tốn agent/TTS) — chạy "
                    "video-studio doctor --hf; không rõ nguyên nhân thì khởi động lại máy.")
    elif "RENDER_PREFLIGHT=config" in log:
        warn.append("Cấu hình render sai (video-studio probe mã 2) — sửa cấu hình; chạy lại vô ích.")
    elif "RENDER_PREFLIGHT=missing" in log:
        warn.append("Thiếu công cụ render (npx/Node, Chromium, hoặc gói video_studio trong venv "
                    "trạm giọng) — chạy video-studio doctor.")
    elif "RENDER_PREFLIGHT=skipped" in log:
        warn.append("Chưa có phép thử render (video-studio < 0.2.5) — nâng video-studio.")

    # ── Dọn dung lượng tuần (weekly_cleanup.py) ──────────────────────────────
    sizes = re.findall(r"CLEANUP_SIZE label=(\w+) bytes=(\d+)", log)
    pr = re.search(r"CLEANUP_PRUNE mode=(\S+) files=(\d+) bytes=(\d+) kept=(\d+)", log)
    pr_hong = re.search(r"CLEANUP_PRUNE mode=move files=\? .*code=(\d+) manifest=(.+)$", log, re.M)
    if pr_hong:
        warn.append(f"Bước dời media HỎNG (prune_media mã {pr_hong.group(1)}) — chưa rõ đã dời bao "
                    f"nhiêu file. Kê khai để đối chiếu/hoàn tác: {pr_hong.group(2).strip()}")
    if "CLEANUP_PRUNE_REFUSED" in log:
        warn.append("prune_media TỪ CHỐI (cầu dao vượt trần hoặc tham số sai) — KHÔNG dời gì. Lượt "
                    "đầu trên trạm tồn nhiều file hay gặp: chạy -DryRun, dời tay một lần với "
                    "--max-files theo cỡ thật (docs/RETENTION.md §7).")
    for nhan, bien in re.findall(r"CLEANUP_SKIP label=(\w+) reason=no-station var=(\w+)", log):
        warn.append(f"Bỏ qua trạm {TEN_TRAM.get(nhan, nhan)}: chưa phân giải được ({bien}) — "
                    f"không quét, không xoay log, không đo.")
    xem = bool(pr and pr.group(1) == "dry-run")
    if pr:
        if xem:
            L.append(f"XEM TRƯỚC (dry-run), chưa chạm gì: sẽ dời {pr.group(2)} file "
                     f"({_co(pr.group(3))}) đã đăng quá hạn sang _trash; giữ {pr.group(4)} file.")
        else:
            L.append(f"Đã dời {pr.group(2)} file ({_co(pr.group(3))}) đã đăng quá hạn sang "
                     f"_trash; giữ {pr.group(4)} file chưa đủ bằng chứng hoặc còn hạn.")
    tr = re.search(r"CLEANUP_TRASH mode=\S+ dirs=(\d+) bytes=(\d+)(?: days=(\d+))?", log)
    if tr and tr.group(1) != "0":
        L.append(f"{'Sẽ đổ' if xem else 'Đổ'} {tr.group(1)} thư mục thùng rác dời quá "
                 f"{tr.group(3) or 30} ngày ({_co(tr.group(2))}).")
    lg = re.search(r"CLEANUP_LOGS mode=\S+ deleted=(\d+) truncated=(\d+)", log)
    if lg and (lg.group(1) != "0" or lg.group(2) != "0"):
        L.append(f"Log: {'sẽ ' if xem else ''}xoá {lg.group(1)} log cũ, cắt {lg.group(2)} log "
                 f"quá cỡ.")
    if "CLEANUP_DONE ok=0" in log:
        do_ = [re.sub(r"^\s*ĐỎ\s+", "", d) for d in log.splitlines() if re.match(r"^\s*ĐỎ\s", d)]
        warn.append("Job dọn có bước hỏng" + (": " + "; ".join(do_[:3])[:300] if do_ else
                                               " — đọc các dòng ĐỎ trong log."))

    # ── Ráp tin ──────────────────────────────────────────────────────────────
    icon = "✅" if ok else "❌"
    out = [f"{icon} <b>{esc(title)}</b>"]

    if ok:
        out.append(f"Chạy xong sau {humanize_duration(duration)}.")
    else:
        # 'failed'/'complete' là dấu KẾT THÚC, không phải tên bước — nói "dừng ở bước
        # failed" thì vô nghĩa với người đọc. Lùi lại tới mốc bước thật gần nhất.
        steps = [s.strip() for s in re.findall(r"=== ([^=]+?) ===", log)]
        steps = [s for s in steps if s.lower() not in ("failed", "complete", "done")]
        last = steps[-1] if steps else ""
        out.append(f"<b>Chạy thất bại</b> sau {humanize_duration(duration)}"
                   + (f", dừng ở bước “{esc(last)}”." if last else "."))
        err = [l for l in log.splitlines() if re.search(r"\bERROR\b", l)]
        if err:
            # bỏ timestamp đầu dòng + nhãn ERROR: cho gọn, giữ nguyên nội dung lỗi
            msg = re.sub(r"^\d{2}:\d{2}:\d{2}\s+", "", err[-1].strip())
            msg = re.sub(r"^(ERROR|WARN)\s*:\s*", "", msg)
            out.append("Nguyên nhân: " + esc(msg[:200]))

    if warn:
        out.append("")
        out += ["⚠️ " + esc(w) if not w.startswith(("Reel", "Đăng")) else "⚠️ " + esc(w) for w in warn]

    if L:
        out.append("")
        out.append(" ".join(L))

    if reach:
        out.append("")
        out.append(reach)

    if sizes:
        out.append("")
        out.append("<b>Dung lượng:</b> " + " · ".join(
            f"{esc(TEN_TRAM.get(n, n))} {_co(b)}" for n, b in sizes))

    links = [l for l in dict.fromkeys(links) if l]
    if links:
        out.append("")
        out.append("<b>Xem tại:</b>")
        out += ["• " + esc(l) for l in links]

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--exit", type=int, default=0)
    ap.add_argument("--duration", default="")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if not os.path.isfile(a.log):
        return 1
    with open(a.log, encoding="utf-8", errors="replace") as f:
        log = f.read()

    msg = build(a.title, a.exit, a.duration, log)
    if not msg or len(msg) < 20:            # soạn ra rỗng -> để notify dùng bản cũ
        return 1
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(msg)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(1)              # im lặng thất bại -> notify-run rơi về bản cũ
