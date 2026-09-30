# -*- coding: utf-8 -*-
"""triage.py — biến log kỹ thuật của scheduled task thành BÁO CÁO NGƯỜI ĐỌC ĐƯỢC.

Vì sao có file này: tin Telegram khi task fail đang là 12 dòng traceback. Nhìn vào đó
không trả lời được câu duy nhất người ta cần biết lúc 5 giờ sáng: *"có phải việc của tôi
không, hay chờ là xong?"*. Ví dụ thật (09/08/2026): pipeline audio truyện fail 4 đêm liền
với traceback Python dài — nguyên nhân thật chỉ là tamhoan.com trả HTTP 500. Không có gì
để sửa, chỉ cần chờ. Nhưng tin nhắn không nói được điều đó.

Ba tầng, tầng sau chỉ làm đẹp thêm chứ không được phép làm hỏng tầng trước:
  1. PHÂN LOẠI bằng luật (offline, tất định, luôn chạy) -> loại lỗi + ai phải xử lý
  2. DIỄN GIẢI bằng Claude headless (tuỳ chọn, có timeout) -> nguyên nhân + đề xuất
  3. GHI SỔ Excel + trả về text cho Telegram

KHÔNG gọi qua a2a-bridge dù bridge có governor/ledger: đường báo lỗi PHẢI độc lập tối đa
với thứ có thể đang hỏng. Cầu dao bridge mở đúng lúc mọi thứ đang fail thì ta mất luôn
báo cáo — hỏng đúng khoảnh khắc cần nó nhất.

Chạy:
  python triage.py --title "Audio Truyen Daily" --exit 1 --log run.log [--no-ai] [--json out.json]
In ra stdout: phần thân tin Telegram (đã sẵn sàng để gửi).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# stdout của Python trên Windows mặc định là cp1252 -> in emoji/tiếng Việt là ném
# UnicodeEncodeError và mất TOÀN BỘ báo cáo. Ép UTF-8 ngay từ đầu; đây là đường báo lỗi,
# nó không được phép tự chết vì một ký tự.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CLAUDE = shutil.which("claude") or os.path.join(
    os.path.expanduser("~"), ".local", "bin", "claude.exe")
AI_TIMEOUT = 120          # giây. Quá hạn thì bỏ phần diễn giải, KHÔNG bỏ báo cáo.
AI_BUDGET_USD = "0.10"

# ── Tầng 1: phân loại bằng luật ─────────────────────────────────────────────
# Thứ tự QUAN TRỌNG: xét từ cụ thể tới chung. Mỗi mục:
#   (mã, nhãn tiếng Việt, regex, ai_xu_ly, chờ_là_hết, gợi ý mặc định)
# `ai_xu_ly`: "chờ" = không ai phải làm gì · "Đức" = cần người · "agent" = sửa được bằng code.
RULES = [
    ("nguon_sap", "Nguồn sập", "chờ", True,
     r"(5\d\d Server Error|502 Bad Gateway|503 Service|504 Gateway|Internal Server Error)",
     "Máy chủ của trang nguồn đang lỗi. Pipeline sẽ tự chạy lại ở lượt sau, không cần làm gì."),

    ("nguon_mat_trang", "Nguồn đổi/xoá nội dung", "Đức", False,
     r"(404 Client Error|404 Not Found|HTTP Error 404)",
     "Đường dẫn bên nguồn không còn tồn tại — có thể trang đã đổi cấu trúc URL hoặc gỡ nội dung."),

    ("nguon_doi_dinh_dang", "Nguồn đổi định dạng dữ liệu", "agent", False,
     r"(cannot parse|không parse|unexpected format|no such element|NoneType' object has no attribute|"
     r"IndexError: list index out of range|selector .* not found)",
     "Dữ liệu bên nguồn không còn đúng khuôn mà script đang mong đợi — cần sửa phần bóc tách."),

    # PHẢI đứng TRƯỚC lớp `quota` chung. Chuỗi của Claude Code không chứa "429",
    # "rate limit" hay "quota exceeded" nên lớp dưới KHÔNG khớp — ba lượt chết liên tiếp
    # (Daily AI 04/09, Daily Data 05/09, Data Weekly 05/09) đều rơi vào "chưa phân loại
    # được", và Excel `Lỗi Task` ghi sai nguyên nhân ba lần. Chuỗi thật, nguyên văn:
    #     You've hit your session limit · resets 9:40pm (Asia/Ho_Chi_Minh)
    # Giờ mở lại nằm SẴN trong chuỗi, nên báo cáo nói được KHI NÀO chạy lại được —
    # khác hẳn "chờ hết chu kỳ" chung chung của lớp dưới.
    ("quota_claude", "Hết hạn mức phiên Claude", "chờ", True,
     r"(hit your (session|usage) limit|session limit[^\n]{0,40}resets|usage limit reached)",
     "Hết hạn mức phiên Claude — KHÔNG phải lỗi code, pipeline vẫn nguyên vẹn. Giờ mở lại "
     "nằm ngay trong dòng log ('resets ...'); chạy lại sau giờ đó là xong, thử lại ngay thì "
     "chắc chắn hỏng tiếp. Lưu ý: phiên Claude Code tương tác dùng CHUNG hạn mức với pipeline, "
     "nên làm việc nặng sát giờ chạy task là tự cắt chân mình."),

    ("quota", "Hết hạn mức / bị chặn tốc độ", "chờ", True,
     r"(429|rate.?limit|quota exceeded|too many requests|max_budget|budget exceeded)",
     "Đã chạm hạn mức của dịch vụ. Chờ hết chu kỳ hoặc nâng hạn mức."),

    ("xac_thuc", "Hết hạn đăng nhập / thiếu quyền", "Đức", False,
     r"(401 |403 |Unauthorized|Forbidden|invalid_grant|token (expired|invalid)|credential)",
     "Token hoặc phiên đăng nhập đã hết hạn — cần đăng nhập lại, agent không tự làm được."),

    ("mang", "Trục trặc mạng", "chờ", True,
     r"(ConnectionError|Connection aborted|Max retries exceeded|getaddrinfo failed|"
     r"Temporary failure in name resolution|SSLError|ReadTimeout|ConnectTimeout)",
     "Không nối được tới máy chủ. Thường tự hết ở lượt sau."),

    ("o_dia", "Hết dung lượng ổ đĩa", "Đức", False,
     r"(No space left|ENOSPC|not enough space|Disk full|đĩa đầy)",
     "Ổ đĩa đầy. Phải dọn chỗ trước khi chạy lại."),

    ("phu_thuoc", "Thiếu thư viện / công cụ", "agent", False,
     r"(ModuleNotFoundError|ImportError|is not recognized as an internal|command not found|"
     r"The term '.*' is not recognized)",
     "Thiếu một thư viện hoặc chương trình mà script cần."),

    ("treo", "Chạy quá lâu rồi bị cắt", "agent", False,
     r"(TimeoutExpired|timed out after|đã giết cả cây tiến trình|Process terminated)",
     "Một bước chạy quá lâu và bị cắt. Cần xem bước nào chậm bất thường."),

    ("loi_script", "Lỗi trong code", "agent", False,
     r"(TypeError|AttributeError|KeyError|NameError|ValueError|ZeroDivisionError|"
     r"SyntaxError|UnboundLocalError|AssertionError)",
     "Lỗi lập trình trong pipeline — sửa được bằng code."),

    ("gpu", "GPU / mô hình cục bộ", "Đức", False,
     r"(CUDA out of memory|CUDA error|no kernel image|torch\.cuda)",
     "GPU hết bộ nhớ hoặc driver trục trặc."),
]

FALLBACK = ("khong_ro", "Chưa phân loại được", "Đức", False,
            "Chưa nhận ra dạng lỗi này. Cần đọc log để biết chuyện gì xảy ra.")


def classify(log_text):
    """Trả (ma, nhan, ai_xu_ly, cho_la_het, goi_y, bang_chung)."""
    for code, label, owner, waitable, pattern, hint in RULES:
        m = re.search(pattern, log_text, re.IGNORECASE)
        if m:
            # Bằng chứng = nguyên dòng chứa dấu hiệu, để người đọc kiểm chứng được ngay.
            line = ""
            for ln in log_text.splitlines():
                if m.group(0).lower() in ln.lower():
                    line = ln.strip()
                    break
            return code, label, owner, waitable, hint, (line or m.group(0))[:300]
    code, label, owner, waitable, hint = FALLBACK
    tail = [l.strip() for l in log_text.splitlines() if l.strip()]
    return code, label, owner, waitable, hint, (tail[-1] if tail else "")[:300]


def error_signature_line(log_text):
    """Dòng lỗi CỤ THỂ nhất, dùng làm bằng chứng và làm chữ ký.

    Bỏ qua các dòng bọc chung chung ('BƯỚC LỖI (exit 1)', 'exit code…') — chính chúng đã
    làm chữ ký lỗi của heal_agent gom mọi sự cố khác nhau vào một rọ.
    """
    generic = re.compile(r"^(BƯỚC LỖI|LỖI build|\[daily\]|exit \d+|Traceback \(most recent)", re.I)
    specific = re.compile(r"^[A-Za-z_.]*(Error|Exception)\b.*:|^RuntimeError:|^\w+Error:")
    lines = [l.strip() for l in log_text.splitlines() if l.strip()]
    for ln in reversed(lines):
        if specific.search(ln):
            return ln[:300]
    for ln in reversed(lines):
        if not generic.match(ln):
            return ln[:300]
    return lines[-1][:300] if lines else ""


# ── Tầng 2: nhờ Claude diễn giải ────────────────────────────────────────────
PROMPT = """Bạn là kỹ sư trực ca, đang viết báo cáo sự cố cho một người KHÔNG đọc code.

Đây là log của một tác vụ tự động vừa chạy hỏng.

TÊN TÁC VỤ: {title}
MÃ THOÁT: {code}
PHÂN LOẠI SƠ BỘ (bằng luật, có thể sai): {label}
DÒNG LỖI CỤ THỂ: {errline}

--- LOG (phần đuôi) ---
{log}
--- HẾT LOG ---

Trả về DUY NHẤT một object JSON, không kèm giải thích, không kèm dấu ``` :
{{
  "cause": "Nguyên nhân, 1-2 câu, tiếng Việt, KHÔNG dùng thuật ngữ lập trình. Nói cho người không biết code hiểu chuyện gì đã xảy ra.",
  "action": "Việc cần làm tiếp theo, 1-2 câu, cụ thể. Nếu chỉ cần chờ thì nói rõ là chờ và chờ tới khi nào.",
  "owner": "cho" | "duc" | "agent",
  "severity": "thap" | "trung" | "cao",
  "category_confirm": "đồng ý với phân loại sơ bộ, hoặc nêu phân loại đúng hơn bằng vài từ"
}}

Quy tắc:
- "owner": "cho" = không ai phải làm gì, tự hết. "duc" = cần con người. "agent" = sửa được bằng code.
- "severity": "cao" chỉ khi mất dữ liệu hoặc hỏng kéo dài; nguồn sập tạm thời là "thap".
- Nếu log cho thấy nguyên nhân nằm NGOÀI tầm kiểm soát (máy chủ bên thứ ba lỗi), phải nói thẳng
  là không cần sửa gì.
"""


def ask_claude(title, code, label, errline, log_tail):
    """Nhờ Claude diễn giải. Trả dict hoặc None — None thì dùng gợi ý mặc định của luật."""
    if not os.path.isfile(CLAUDE):
        return None
    prompt = PROMPT.format(title=title, code=code, label=label, errline=errline,
                           log=log_tail[-6000:])
    try:
        p = subprocess.run(
            [CLAUDE, "-p", "--safe-mode", "--output-format", "json",
             "--tools", "Read", "--max-budget-usd", AI_BUDGET_USD],
            input=prompt, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=AI_TIMEOUT)
        if p.returncode != 0:
            return None
        outer = json.loads(p.stdout)
        raw = (outer.get("result") or "").strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None      # diễn giải là phần THÊM — hỏng thì báo cáo vẫn phải ra


# ── Tầng 3: ghi Excel + soạn tin ────────────────────────────────────────────
SHEET = "Lỗi Task"
COLS = ["thoi_gian", "tac_vu", "exit", "loai_loi", "muc_do", "nguyen_nhan",
        "de_xuat", "ai_xu_ly", "cho_la_het", "dong_loi", "log_path"]


def append_excel(row):
    """Ghi 1 dòng vào Auto Task.xlsx (sheet 'Lỗi Task').

    Theo đúng kỷ luật của append_excel_log.py: best-effort, nhưng KHÔNG im lặng —
    ghi được file gốc thì thôi, không thì rơi xuống bản pending cạnh script.
    """
    try:
        from paths import auto_task_xlsx
        xlsx = auto_task_xlsx()
    except Exception:
        # Đường lùi neo vào TRẠM, không vào engine: engine là mã dùng chung đi theo gói
        # sang máy khác, còn sổ là dữ liệu của một máy. Ghi sổ vào engine nghĩa là lần
        # đóng gói kế tiếp mang theo số liệu của máy cũ.
        from paths import station
        xlsx = os.path.join(station(), "Auto Task.xlsx")
    try:
        import openpyxl
        if os.path.isfile(xlsx):
            wb = openpyxl.load_workbook(xlsx)
        else:
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
        ws = wb[SHEET] if SHEET in wb.sheetnames else wb.create_sheet(SHEET)
        # Sheet vừa tạo đã CÓ SẴN dòng 1 rỗng, nên append(COLS) sẽ đẩy header xuống dòng 2
        # và để lại một dòng trống trên cùng. Ghi thẳng vào ô của dòng 1.
        if ws.max_row == 1 and all(c.value is None for c in ws[1]):
            for i, name in enumerate(COLS, start=1):
                ws.cell(row=1, column=i, value=name)
        ws.append([row.get(c, "") for c in COLS])
        wb.save(xlsx)
        return xlsx
    except Exception as e:
        from paths import station
        pend = os.path.join(station(), "_xlsx-pending")
        os.makedirs(pend, exist_ok=True)
        name = datetime.datetime.now().strftime("trierr-%Y%m%d-%H%M%S.json")
        try:
            json.dump(row, open(os.path.join(pend, name), "w", encoding="utf-8", newline="\n"),
                      ensure_ascii=False, indent=2)
            return f"(pending: {name} — {e})"
        except Exception:
            return f"(KHÔNG ghi được Excel lẫn pending: {e})"


OWNER_TEXT = {"cho": "⏳ Không cần làm gì — chờ là hết",
              "duc": "🙋 Cần anh xử lý",
              "agent": "🤖 Sửa được bằng code"}
SEV_ICON = {"thap": "🟢", "trung": "🟡", "cao": "🔴"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--exit", type=int, default=1)
    ap.add_argument("--log", required=True)
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--json", help="ghi kết quả triage ra file JSON")
    # Đường ra ĐÁNG TIN cho người gọi: stdout đi qua console nên bị codepage OEM của
    # runspace gọi nó bóp méo (đã dính thật: tiếng Việt ra "Nguß╗ôn sß║¡p" trên Telegram).
    # Ghi file UTF-8 thì không có tầng console nào xen vào.
    ap.add_argument("--out", help="ghi thân tin (UTF-8) ra file thay vì chỉ in stdout")
    a = ap.parse_args()

    try:
        with open(a.log, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        print(f"(triage: không đọc được log — {e})")
        return 0

    code, label, owner, waitable, hint, evidence = classify(text)
    errline = error_signature_line(text)

    ai = None if a.no_ai else ask_claude(a.title, a.exit, label, errline, text)
    cause = (ai or {}).get("cause") or hint
    action = (ai or {}).get("action") or ("Chờ lượt chạy sau." if waitable else "Xem log để biết chi tiết.")
    owner_k = (ai or {}).get("owner") or {"chờ": "cho", "Đức": "duc", "agent": "agent"}[owner]
    if owner_k not in OWNER_TEXT:
        owner_k = "duc"
    sev = (ai or {}).get("severity") or ("thap" if waitable else "trung")
    if sev not in SEV_ICON:
        sev = "trung"

    xlsx = append_excel({
        "thoi_gian": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tac_vu": a.title, "exit": a.exit, "loai_loi": label, "muc_do": sev,
        "nguyen_nhan": cause, "de_xuat": action, "ai_xu_ly": owner_k,
        "cho_la_het": "co" if waitable else "khong",
        "dong_loi": errline, "log_path": os.path.abspath(a.log),
    })

    if a.json:
        try:
            json.dump({"category": code, "label": label, "severity": sev, "owner": owner_k,
                       "cause": cause, "action": action, "errline": errline,
                       "waitable": waitable, "xlsx": xlsx},
                      open(a.json, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
        except Exception:
            pass

    # Thân tin Telegram: KHÔNG có traceback. Ai cần chi tiết thì mở log/Excel.
    parts = [
        f"{SEV_ICON[sev]} <b>{esc(label)}</b>",
        f"<b>Chuyện gì:</b> {esc(cause)}",
        f"<b>Nên làm:</b> {esc(action)}",
        f"<b>Ai xử lý:</b> {OWNER_TEXT[owner_k]}",
    ]
    if errline:
        parts.append(f"<i>Dấu vết kỹ thuật:</i> <code>{esc(errline[:180])}</code>")
    if not (ai):
        parts.append("<i>(phân loại bằng luật — chưa diễn giải được bằng AI)</i>")
    body = "\n".join(parts)

    if a.out:
        try:
            with open(a.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
        except Exception as e:
            print(f"(triage: không ghi được --out — {e})")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
