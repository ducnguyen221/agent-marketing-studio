# -*- coding: utf-8 -*-
"""append_excel_log.py — ghi 1 dòng nhật ký mỗi lần chạy task tin tức vào
`Auto Task.xlsx` trong trạm (paths.station()), mỗi task 1 sheet
(Daily AI / Daily Data / Weekly AI / Weekly Data).

Đường dẫn lấy qua paths.auto_task_xlsx() — KHÔNG hardcode, KHÔNG tự ghép.
Sổ ĐÃ RỜI Desktop ngày 05/09/2026: Desktop máy nguồn bị dịch vụ đám mây đồng bộ,
nên mỗi dòng ghi là một lần đẩy file lên cloud và một cơ hội đẻ bản sao xung
đột. `paths.auto_task_xlsx()` vẫn tự lùi về bản Desktop nếu bản mới chưa có.

Chạy bằng PYTHON HỆ THỐNG (có openpyxl). Best-effort: lỗi KHÔNG được làm hỏng run,
NHƯNG không được im lặng — nếu không ghi được file gốc thì rơi xuống bản pending
nằm cạnh script này (thư mục luôn tồn tại), và chỉ báo lỗi thật khi cả hai đều hỏng.

  python append_excel_log.py --sheet "Daily AI" --row row.json [--log run.log]

row.json = { time_start, time_end, status, script, title, video_location, post, note }
- video_location: đường dẫn file mp4 nội bộ → ô có hyperlink mở được ngay.
- note: nếu rỗng và có --log → tự tóm tắt dòng bất thường trong log.
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import auto_task_xlsx, station  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = auto_task_xlsx()
# Hàng đợi nằm trong TRẠM, không trong engine: engine là mã dùng chung đi theo gói
# sang máy khác, còn những dòng Excel chưa ghi được là dữ liệu riêng của một máy.
PENDING_DIR = os.path.join(station(), "_xlsx-pending")
COLS = ["time_start", "time_end", "status", "script", "title", "video_location", "post", "note"]
SHEETS = ["Daily AI", "Daily Data", "Weekly AI", "Weekly Data"]
_ANOM = re.compile(r"(?i)(error|lỗi|warn|cảnh báo|fail|crash|traceback|exception|⚠)")


def summarize_log(path, max_lines=3):
    """Tóm tắt dòng bất thường trong log cho cột note."""
    if not path or not os.path.isfile(path):
        return ""
    hits = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for ln in f:
                s = ln.strip()
                if s and _ANOM.search(s) and "No accelerated colorspace" not in s:
                    hits.append(s[:160])
    except OSError:
        return ""
    if not hits:
        return ""
    uniq = list(dict.fromkeys(hits))[-max_lines:]
    return " | ".join(uniq)


def _load_or_create():
    from openpyxl import Workbook, load_workbook
    if os.path.isfile(XLSX):
        return load_workbook(XLSX)
    wb = Workbook()
    wb.remove(wb.active)  # bỏ sheet rỗng mặc định
    return wb


def _ensure_sheet(wb, name):
    from openpyxl.styles import Font
    if name in wb.sheetnames:
        return wb[name]
    ws = wb.create_sheet(title=name)
    ws.append(COLS)
    for c in range(1, len(COLS) + 1):
        ws.cell(row=1, column=c).font = Font(bold=True)
    widths = [19, 19, 10, 34, 52, 16, 60, 50]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    return ws


def _write(wb, sheet, row):
    ws = _ensure_sheet(wb, sheet)
    r = ws.max_row + 1
    for ci, key in enumerate(COLS, 1):
        cell = ws.cell(row=r, column=ci)
        val = row.get(key, "")
        if key == "video_location" and val:
            p = str(val).replace("\\", "/")
            cell.value = "Mở video"
            cell.hyperlink = "file:///" + p
            cell.style = "Hyperlink"
        else:
            cell.value = str(val) if val is not None else ""
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--row", required=True, help="file JSON chứa 8 cột")
    ap.add_argument("--log", default="", help="log để tự tóm tắt note nếu thiếu")
    args = ap.parse_args()

    with open(args.row, encoding="utf-8-sig") as f:
        row = json.load(f)
    # note = ghi chú do runner truyền (vd trạng thái FB) + tóm tắt bất thường đọc từ log
    base = (row.get("note") or "").strip()
    logsum = summarize_log(args.log) if args.log else ""
    if logsum:
        row["note"] = (base + " | ⚠ " + logsum) if base else ("⚠ " + logsum)
    else:
        row["note"] = base or ("OK" if str(row.get("status", "")).lower().startswith(
            ("ok", "success", "thành")) else "")

    last_err = None
    for attempt in range(3):  # OneDrive/Excel có thể đang khoá file
        try:
            wb = _load_or_create()
            r = _write(wb, args.sheet, row)
            wb.save(XLSX)
            print(f"EXCEL_OK sheet={args.sheet!r} row={r} file={XLSX}")
            return 0
        except PermissionError as e:
            last_err = e
            time.sleep(4)
        except Exception as e:  # mọi lỗi khác: thử fallback rồi thoát
            last_err = e
            break

    # Fallback: file gốc khoá/hỏng -> ghi bản pending vào thư mục CẠNH SCRIPT NÀY.
    # Cố ý KHÔNG đặt cạnh XLSX: nếu Desktop chính là thứ đang hỏng (OneDrive đổi
    # chủ, thư mục biến mất) thì bản dự phòng nằm đó cũng chết theo — đúng lỗi đã
    # xảy ra 21/07/2026, mất trắng 1 dòng log mà vẫn báo thành công.
    try:
        os.makedirs(PENDING_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        alt = os.path.join(PENDING_DIR, f"Auto Task.pending-{ts}.xlsx")
        from openpyxl import Workbook
        wb = Workbook(); wb.remove(wb.active)
        _write(wb, args.sheet, row)
        wb.save(alt)
        print(f"EXCEL_PENDING ghi file gốc hỏng ({type(last_err).__name__}: {last_err}); "
              f"đã giữ dòng log -> {alt} (chạy merge_excel_pending.py để gộp lại)")
        return 0  # dữ liệu đã được giữ -> không đánh hỏng cả run publish
    except Exception as e:
        # Cả file gốc lẫn bản dự phòng đều hỏng -> dòng log MẤT THẬT. Phải báo ❌.
        print(f"EXCEL_FAIL mất dòng log: gốc={type(last_err).__name__}: {last_err} | "
              f"pending={type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
