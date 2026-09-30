# -*- coding: utf-8 -*-
"""Tự-chữa pipeline truyện: khi MỘT lỗi lặp lại tới lần 2, gọi headless Claude đánh giá +
sửa script tối thiểu, validate, rồi để daily_truyen re-run kiểm chứng.

Chạy KHÔNG người giám sát (task lịch 1h/3h/5h) nên MỌI nhánh phải fail-safe: heal hỏng
KHÔNG được làm hỏng pipeline — cùng lắm quay về đúng trạng thái "fail như cũ".

Rào an toàn:
  - backup 4 script trước khi Claude sửa -> revert nếu py_compile fail / abort / timeout / re-run fail.
  - TỐI ĐA 1 lần heal / mỗi chữ ký lỗi (không đốt token mỗi đêm; user xoá _heal_state.json để mở lại).
  - Claude chạy --permission-mode acceptEdits (sửa file được, KHÔNG bash phá hoại). Validate THẬT
    do chính module này làm (py_compile + re-run), không tin lời Claude.
  - Concurrency: task đặt IgnoreNew nên re-run dài không đè lượt kế -> an toàn chạy tới thành công.
"""
import os
import re
import sys
import json
import shutil
import hashlib
import datetime
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# Script da doi sang apps/truyen/ (2026-08-26). DU LIEU (venv, assets, truyen-out,
# _vtitles, voices) VAN O GOC ENGINE - neo vao day, khong neo vao HERE.
import truyen_paths  # noqa: E402  — phân giải Windows + macOS
ENGINE = truyen_paths.engine_dir()
_LOGDIR = os.path.join(ENGINE, "truyen-out", "daily-logs")   # sweep GIỮ (tên thư mục có 'log')
HEAL_STATE = os.path.join(_LOGDIR, "_heal_state.json")
HEAL_AUDIT = os.path.join(_LOGDIR, "_heal_audit.log")
# Memory Claude của home: slug = đường thư mục nhà, mọi ký tự không phải chữ/số -> "-"
# (cùng quy ước Claude Code dùng cho thư mục project, trên cả hai OS).
MEM_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                       re.sub(r"[^A-Za-z0-9]", "-", os.path.expanduser("~")), "memory")
CLAUDE = shutil.which("claude")
HEAL_TIMEOUT = 1500  # 25 phút cho Claude sửa
_SCRIPTS = [os.path.join(HERE, f) for f in
            ("read_story.py", "make_video.py", "audio_truyen.py", "daily_truyen.py")]


# Dòng "bọc" của runner — KHÔNG được dùng làm chữ ký. Chính chúng đã gây ra bug:
# quét ngược từ cuối log thì dòng cuối luôn là "BƯỚC LỖI (exit 1)." và nó khớp ngay,
# nên mọi sự cố khác nhau đều nhận CÙNG một chữ ký. Hậu quả thật (07-09/08/2026):
# lỗi "nguồn trả HTTP 500" và lỗi "không parse được tiêu đề chương" bị gom làm một;
# sig đó đã bị đánh dấu healed từ 21/07 nên auto-heal tắt câm cho cả hai.
_WRAPPER = re.compile(
    r"^(BƯỚC LỖI|LỖI build|\[daily\]|\[sweep\]|exit \d+|Traceback \(most recent|"
    r"\s+File \"|\s+\^+\s*$|\s+raise |\s+return )", re.I)
# Dòng exception THẬT: "RuntimeError: ...", "ValueError: ...", "requests.HTTPError: ..."
_SPECIFIC = re.compile(r"^[\w.]*(?:Error|Exception|Exit)\b[^:]*:\s*\S")


def _sig(text):
    """Chữ ký lỗi ỔN ĐỊNH: dòng exception CỤ THỂ nhất, bỏ số/id -> hash.

    Ưu tiên dòng `XxxError: ...`; không có thì lấy dòng cuối KHÔNG phải dòng bọc.
    """
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    err = ""
    for l in reversed(lines):
        if _SPECIFIC.match(l.strip()):
            err = l.strip()
            break
    if not err:
        for l in reversed(lines):
            if not _WRAPPER.match(l):
                err = l.strip()
                break
    err = err or (lines[-1].strip() if lines else "unknown")
    # Bỏ số VÀ url cụ thể: cùng một lỗi ở chương khác nhau phải ra cùng chữ ký.
    norm = re.sub(r"https?://\S+", "<url>", err)
    norm = re.sub(r"\d+", "#", norm)[:200]
    return hashlib.sha1(norm.encode("utf-8", "replace")).hexdigest()[:12], norm


# Lỗi do NGUỒN hoặc do MÔI TRƯỜNG: sửa script không giúp được gì. Không tính vào quota
# heal, và không bao giờ gọi Claude đi sửa code — làm vậy vừa tốn quota vừa có nguy cơ
# "sửa" hỏng một script vốn đang đúng.
_NOT_OUR_FAULT = re.compile(
    r"(5\d\d Server Error|Internal Server Error|502 Bad Gateway|503 Service|504 Gateway|"
    r"ConnectionError|Max retries exceeded|getaddrinfo failed|SSLError|ReadTimeout|"
    r"ConnectTimeout|429|rate.?limit|quota exceeded|No space left|ENOSPC|"
    # Nguồn CHẶN scrape (403/captcha/cloudflare) = ngoại cảnh. Cho Claude đi "sửa" một
    # crawler vốn đang đúng chỉ tổ hỏng thứ đang lành — đúng bài học tamhoan HTTP 500.
    r"403 Client Error|Forbidden|\bblocked\b|captcha|cloudflare)", re.I)


def is_external(text):
    """True nếu lỗi nằm ngoài tầm kiểm soát của code này."""
    return bool(_NOT_OUR_FAULT.search(text or ""))


def _load():
    try:
        return json.load(open(HEAL_STATE, encoding="utf-8"))
    except Exception:
        return {}


def _save(d):
    os.makedirs(_LOGDIR, exist_ok=True)
    json.dump(d, open(HEAL_STATE, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)


def record_failure(err_text):
    """Ghi 1 lần lỗi. Trả (sig, count, already_healed, norm)."""
    sig, norm = _sig(err_text)
    d = _load()
    e = d.get(sig, {"count": 0, "healed": False})
    e["count"] += 1
    e["norm"] = norm
    e["external"] = is_external(err_text)   # lỗi nguồn/môi trường -> không phải việc của heal
    e["last"] = datetime.datetime.now().isoformat(timespec="seconds")
    d[sig] = e
    _save(d)
    return sig, e["count"], bool(e.get("healed")), norm


def should_heal(sig):
    """Chỉ heal khi: có claude CLI + lỗi ĐÃ xảy ra >= 2 lần + CHƯA heal sig này
    + lỗi KHÔNG phải do nguồn/môi trường.

    Điều kiện cuối là bài học 08/2026: nguồn tamhoan trả HTTP 500 bốn đêm liền, nếu để
    heal chạy thì Claude sẽ đi "sửa" một crawler vốn đang đúng — tốn quota và có thể làm
    hỏng thứ đang lành.
    """
    e = _load().get(sig, {})
    if e.get("external"):
        return False
    if _trong_ban_git() and os.environ.get("TRUYEN_HEAL") != "1":
        # Bản trong REPO: để agent sửa file ở đây là làm bẩn cây git của máy chạy lịch —
        # `studio.py update` từ chối kéo bản mới, và bản vá không qua review/CI nào. Chỉ bật
        # khi người vận hành đặt TRUYEN_HEAL=1 có chủ ý.
        return False
    return bool(CLAUDE) and e.get("count", 0) >= 2 and not e.get("healed")


def _trong_ban_git(start=None):
    """Thư mục script có nằm trong một bản clone git không (đi lên tìm `.git`)."""
    d = os.path.abspath(start or HERE)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return True
        cha = os.path.dirname(d)
        if cha == d:
            return False
        d = cha


def _mark(sig, note):
    """Đánh dấu đã heal (thành công hay không) -> KHÔNG auto-retry sig này nữa."""
    d = _load()
    e = d.get(sig, {})
    e["healed"] = True
    e["heal_note"] = note
    e["heal_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    d[sig] = e
    _save(d)
    try:
        with open(HEAL_AUDIT, "a", encoding="utf-8") as f:
            f.write(f"{e['heal_at']} {sig} {note}\n")
    except Exception:
        pass


def _backup(stamp):
    bdir = os.path.join(_LOGDIR, f"_heal_bak_{stamp}")
    os.makedirs(bdir, exist_ok=True)
    for p in _SCRIPTS:
        if os.path.isfile(p):
            shutil.copy2(p, bdir)
    return bdir


def _restore(bdir):
    for p in _SCRIPTS:
        b = os.path.join(bdir, os.path.basename(p))
        if os.path.isfile(b):
            shutil.copy2(b, p)


def _compile_ok():
    r = subprocess.run([sys.executable, "-m", "py_compile", *_SCRIPTS],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "")[:400]


def _prompt(norm, tail):
    return f"""Pipeline audio truyện ở {HERE} (scheduled task 1h/3h/5h) đã FAIL 2 lần liên tiếp CÙNG MỘT lỗi.
Nhiệm vụ: tìm ROOT CAUSE và sửa TỐI THIỂU để chạy được, KHÔNG phá hành vi hiện có.

Lỗi (đã chuẩn hoá, số thay bằng #): {norm}

Đuôi log thật:
---
{tail}
---

RÀNG BUỘC CỨNG (vi phạm = coi như hỏng):
- CHỈ sửa file .py trong {HERE}: read_story.py / make_video.py / audio_truyen.py / daily_truyen.py. Sửa NHỎ NHẤT.
- KHÔNG xoá file, KHÔNG git push/commit, KHÔNG đụng .env / secret / thư mục ngoài {HERE} (trừ ghi memory ở cuối).
- Nếu lỗi do NGUỒN dữ liệu (web đổi HTML / trùng chương / nhảy số / mất field): làm crawler/parse CHỊU ĐƯỢC
  (skip / bỏ qua / không abort), ĐỪNG hard-code một chương/một id cụ thể.
- Nếu KHÔNG chắc root cause hoặc fix rủi ro cao: KHÔNG sửa gì, in đúng "HEAL_ABORT: <lý do>" rồi dừng.
- py_compile phải pass (bên ngoài sẽ kiểm lại + chạy thật để nghiệm thu; đừng tin cảm tính).
- XONG, in ĐÚNG 1 dòng: "HEAL_SUMMARY: <mô tả ngắn cái đã sửa, 1 câu>"  (để đưa lên Telegram).
- Rồi lưu bài học vào memory {MEM_DIR}: tạo/cập nhật 1 file .md (frontmatter type: project),
  thêm 1 dòng vào MEMORY.md, link [[nghe-tien-truyen-source-quirks]]. Dedup nếu đã có mục tương tự.
"""


def attempt(norm, log_path, rerun_fn, log):
    """Gọi Claude sửa -> validate -> re-run. Trả True nếu re-run OK (pipeline đi tiếp được)."""
    sig, _ = _sig(norm)  # sig ổn định từ norm
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = _backup(stamp)
    log(f"[HEAL] lỗi lặp lần 2 — gọi Claude đánh giá & tự sửa. Backup script: {bdir}")

    try:
        with open(log_path, encoding="utf-8") as f:
            tail = "".join(f.readlines()[-120:])
    except Exception:
        tail = norm

    try:
        r = subprocess.run(
            [CLAUDE, "-p", _prompt(norm, tail),
             "--add-dir", HERE, "--add-dir", MEM_DIR,
             "--permission-mode", "acceptEdits"],
            capture_output=True, text=True, timeout=HEAL_TIMEOUT, cwd=HERE)
        out = (r.stdout or "") + "\n" + (r.stderr or "")
    except subprocess.TimeoutExpired:
        _restore(bdir)
        log(f"[HEAL] ❌ Claude quá {HEAL_TIMEOUT//60} phút — revert, bỏ heal.")
        _mark(sig, "timeout -> revert")
        return False
    except Exception as e:
        _restore(bdir)
        log(f"[HEAL] ❌ gọi Claude lỗi ({e}) — revert.")
        _mark(sig, f"invoke-error {e} -> revert")
        return False

    summ = ""
    for l in out.splitlines():
        if "HEAL_ABORT:" in l:
            _restore(bdir)
            log(f"[HEAL] ❌ Claude tự abort: {l.split('HEAL_ABORT:', 1)[1].strip()[:150]} — revert.")
            _mark(sig, "claude-abort -> revert")
            return False
        if "HEAL_SUMMARY:" in l:
            summ = l.split("HEAL_SUMMARY:", 1)[1].strip()

    ok, cerr = _compile_ok()
    if not ok:
        _restore(bdir)
        log(f"[HEAL] ❌ sửa xong nhưng py_compile FAIL — revert.\n{cerr}")
        _mark(sig, "compile-fail -> revert")
        return False

    log(f"[HEAL] Claude sửa xong: {summ or '(không summary)'} — chạy lại pipeline kiểm chứng...")
    try:
        rc = rerun_fn()
    except Exception as e:
        rc = 1
        log(f"[HEAL] re-run ném lỗi: {e}")
    if rc == 0:
        log(f"[HEAL] ✅ TỰ CHỮA THÀNH CÔNG: {summ}")
        _mark(sig, f"healed OK: {summ}")
        return True
    _restore(bdir)
    log(f"[HEAL] ❌ re-run vẫn fail (exit {rc}) — revert về bản gốc. Cần người xem.")
    _mark(sig, f"rerun-fail(exit {rc}) -> revert")
    return False
