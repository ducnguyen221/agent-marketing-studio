# -*- coding: utf-8 -*-
"""Chạy một lệnh con rồi báo kết quả về Telegram — wrapper cho bộ lập lịch.

    python notify_run.py --title "Tin hằng ngày" \\
        [--composer-dir <trạm>/engine] [--link-domains blog.example.com] \\
        [--timeout 7200] -- pwsh -NoProfile -File <chiến dịch>/run.ps1

## Vì sao có file này

Máy lịch Windows bọc mọi scheduled task bằng một wrapper PowerShell nằm NGOÀI repo (hạ tầng
của một cái máy). Trên macOS/launchd không có Windows PowerShell 5.1, và repo public thì phải
tự đủ — nên đây là bản Python, cùng hợp đồng:

· **Mã thoát = mã của lệnh con, nguyên vẹn** (0 ok · 1 lỗi engine · 2 hợp đồng sai · 3 trạm
  thiếu). Bộ lập lịch chỉ nhìn mã thoát; đổi nó là nói dối về lượt chạy.
· **✅** tiêu đề + MỌI link sản phẩm trích từ log (YouTube, Facebook, và các miền khai qua
  `--link-domains`). **❌** hỏng ở bước nào + đã xong bước nào + (log đuôi | báo cáo triage).
· **Báo cáo không bao giờ làm hỏng lượt chạy.** Thiếu cấu hình, mạng lỗi, composer hỏng —
  tất cả chỉ in cảnh báo ra stderr; mã thoát vẫn là mã con.
· Đầu log in `which` của `pwsh node ffprobe python npx`: launchd chạy với PATH tối thiểu, và
  "không thấy ffprobe" là lỗi phổ biến nhất khi dời máy — đọc đầu log là biết ngay.

## `--timeout` — vì sao wrapper phải tự canh giờ

Task Scheduler của Windows có `ExecutionTimeLimit`: lượt chạy quá giờ thì **bộ lập lịch** giết
nó. **launchd không có khoá tương đương** — không `ExecutionTimeLimit`, không `TimeOut` cho
job theo lịch (`ExitTimeOut` chỉ là thời gian ân hạn giữa SIGTERM và SIGKILL *khi đã bảo nó
dừng*). Một lượt treo trên macOS treo **vô hạn**, giữ nguyên nhãn job, nên lượt kế tiếp theo
lịch bị launchd bỏ qua — và không có gì báo, vì cũng chẳng có lượt nào kết thúc để báo.

Nên trần giờ phải nằm ở đây, chỗ duy nhất bọc mọi lượt chạy. `--timeout <giây>` bật đồng hồ:
hết giờ thì giết **cả nhóm tiến trình** con (không chỉ tiến trình đầu — `run.ps1` đẻ ffmpeg,
node, python; giết mỗi vỏ là để lại một đàn mồ côi), rồi gửi tin ❌ nói rõ "quá <giây>s".

**Đây là NGOẠI LỆ DUY NHẤT của luật "mã thoát = mã con".** Quá giờ thì không có mã con để
trả: tiến trình bị giết. Wrapper trả **1** (lỗi engine, thử lại được) và nói rõ lý do trong
cả log lẫn tin báo. Không đặt `--timeout` thì hành vi y như trước: chờ đến khi nào xong.

## Ba tầng soạn tin (giống wrapper Windows)

1. `--composer-dir/compose_report.py` → văn người đọc (nếu có).
2. `--composer-dir/triage.py` → khi FAIL, phân tích sự cố (trần 180 s).
3. Định dạng dự phòng: icon + giờ + exit + link + bước + log đuôi.

## Secret

Token CHỈ đến từ file cấu hình Telegram (`TG_CONFIG` → `~/.secret/telegram/config.json`),
đọc qua `scripts/lib/telegram_io.py` — chỗ duy nhất trong repo gọi Bot API. Không đọc token
từ biến môi trường (xem docstring `telegram_io`). Mọi thông báo lỗi đi qua `_che_token`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import telegram_io as tg  # noqa: E402

CONG_CU = ("pwsh", "node", "ffprobe", "python", "npx")
TRAN_TIN = 3900
TRAN_COMPOSE = 120      # giây
TRAN_TRIAGE = 180       # giây — notify không được phép treo bộ lập lịch

LINK_GOC = (r"youtube\.com/(?:watch\?v=|shorts/)[\w-]+|youtu\.be/[\w-]+"
            r"|facebook\.com/\S+|fb\.watch/\S+")
BUOC_RE = re.compile(r"^(===|---|\[|Step |Launching|Rendering|Publishing|Uploading|Crawling"
                     r"|DONE|OK |Registered|publish: (OK|DONE|YouTube|Facebook|Excel|web))")
TOKEN_RE = re.compile(r"\d{5,}:[A-Za-z0-9_-]{20,}")


def _loi(msg: str) -> None:
    print(_che_token(msg), file=sys.stderr, flush=True)


def _che_token(s: str) -> str:
    """Che mọi chuỗi có hình dạng token bot Telegram — lỗi mạng có thể mang URL chứa token."""
    return TOKEN_RE.sub("<token-da-che>", str(s))


def _esc(s: str) -> str:
    return html.escape(str(s), quote=False)


# ── Trích từ log ─────────────────────────────────────────────────────────────

def _mien(ds: list[str]) -> list[str]:
    ra = []
    for muc in ds:
        for d in muc.split(","):
            d = re.sub(r"^https?://", "", d.strip().lower()).strip("/")
            if d and d not in ra:
                ra.append(d)
    return ra


def link_re(mien: list[str]) -> re.Pattern:
    them = "".join(r"|(?:[\w-]+\.)*" + re.escape(d) + r"/\S+" for d in mien)
    return re.compile(r"https?://(?:www\.)?(?:" + LINK_GOC + them + ")")


def trich_link(dong: list[str], mien: list[str]) -> list[str]:
    rx = link_re(mien)
    ra: list[str] = []
    for d in dong:
        for m in rx.finditer(d):
            l = m.group(0).rstrip(".,);\"'")
            if l not in ra:
                ra.append(l)
    return ra


def trich_buoc(dong: list[str]) -> list[str]:
    return [d for d in dong if BUOC_RE.match(d)][-12:]


def trich_do_phu(dong: list[str]) -> tuple[list[str], str]:
    trong, khoi, tt = False, [], ""
    for d in dong:
        if "FB_REACH_BEGIN" in d:
            trong = True
            continue
        if "FB_REACH_END" in d:
            trong = False
            continue
        if trong:
            khoi.append(re.sub(r"^\d{2}:\d{2}:\d{2}\s{2}", "", d))
        m = re.search(r"FB_REACH_STATUS=(\w+)", d)
        if m and not tt:
            tt = m.group(1)
    return khoi, tt


# ── Chạy ─────────────────────────────────────────────────────────────────────

def in_which() -> None:
    for t in CONG_CU:
        print(f"notify_run: which {t}={shutil.which(t) or '(không thấy)'}", flush=True)
    print(f"notify_run: sys.executable={sys.executable}", flush=True)


def _giet_chum(p: "subprocess.Popen") -> None:
    """Giết CẢ NHÓM tiến trình con, không chỉ tiến trình đầu.

    `run.ps1` đẻ ra ffmpeg, node, python… Giết mỗi cái vỏ là để lại một đàn mồ côi vẫn
    ngốn CPU và vẫn giữ file — đúng kiểu hỏng mà trần giờ sinh ra để tránh.
    """
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            return
        nhom = os.getpgid(p.pid)
        os.killpg(nhom, signal.SIGTERM)
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(nhom, signal.SIGKILL)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        _loi(f"notify: không giết được tiến trình con — {e}")


def chay_lenh(cmd: list[str], tran: int | None = None) -> tuple[int, list[str], bool]:
    """Chạy lệnh con, gộp stderr vào stdout, vừa in ra (cho log của bộ lập lịch) vừa gom lại.

    `tran` (giây) > 0 ⇒ quá giờ thì giết cả nhóm con. Trả `(mã, dòng, quá_giờ)`.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    # Nhóm tiến trình riêng — chỉ khi có trần giờ, để không đổi hành vi của lượt chạy
    # bình thường (Ctrl-C của người đang ngồi xem phải tới được cả chùm).
    khoi: dict = {}
    if tran:
        if os.name == "nt":
            khoi["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            khoi["start_new_session"] = True
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=env, **khoi)
    except OSError as e:
        d = f"notify_run: không chạy được lệnh {cmd[0]!r} — {e}"
        print(d, flush=True)
        return 1, [d], False

    qua_gio = threading.Event()

    def _het_gio():
        qua_gio.set()
        print(f"notify_run: QUÁ GIỜ {tran}s — giết lệnh con.", flush=True)
        _giet_chum(p)

    dong_ho = threading.Timer(tran, _het_gio) if tran else None
    if dong_ho:
        dong_ho.daemon = True
        dong_ho.start()
    dong: list[str] = []
    try:
        with p:
            assert p.stdout is not None
            for b in p.stdout:
                s = b.decode("utf-8", errors="replace").rstrip("\r\n")
                dong.append(s)
                print(s, flush=True)
            ma = p.wait()
    finally:
        if dong_ho:
            dong_ho.cancel()
    if ma < 0:                       # POSIX: chết vì tín hiệu -> quy ước shell 128+N
        ma = 128 - ma
    if qua_gio.is_set():
        # Ngoại lệ DUY NHẤT của luật "mã thoát = mã con": không có mã con để trả.
        d = (f"notify_run: lệnh con bị giết vì quá {tran}s "
             f"(launchd không có ExecutionTimeLimit — trần giờ nằm ở wrapper).")
        dong.append(d)
        print(d, flush=True)
        ma = 1
    return ma, dong, qua_gio.is_set()


def _goi_composer(script: Path, args: list[str], log_txt: str, tran: int) -> str:
    """Chạy một composer; trả văn bản (rỗng nếu hỏng). Không bao giờ ném."""
    fd_log, log = tempfile.mkstemp(prefix="notify-src-", suffix=".log")
    fd_out, out = tempfile.mkstemp(prefix="notify-msg-", suffix=".txt")
    os.close(fd_out)
    os.remove(out)
    try:
        with os.fdopen(fd_log, "w", encoding="utf-8") as f:
            f.write(log_txt)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable, str(script), *args, "--log", log, "--out", out],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       env=env, timeout=tran)
        p = Path(out)
        return p.read_text(encoding="utf-8").strip() if p.is_file() else ""
    except subprocess.TimeoutExpired:
        _loi(f"notify: {script.name} quá {tran}s — bỏ qua.")
        return ""
    except Exception as e:  # noqa: BLE001 — cải tiến báo cáo không được làm mất báo cáo
        _loi(f"notify: {script.name} lỗi — {e}")
        return ""
    finally:
        for x in (log, out):
            try:
                os.remove(x)
            except OSError:
                pass


# ── Soạn tin ─────────────────────────────────────────────────────────────────

def _cat(t: str) -> str:
    if len(t) <= TRAN_TIN:
        return t
    t = t[:TRAN_TIN]
    if t.rfind("<") > t.rfind(">"):          # đừng để nửa thẻ HTML — Telegram từ chối cả tin
        t = t[:t.rfind("<")]
    amp = t.rfind("&")
    if amp > t.rfind(";") and len(t) - amp < 10:   # nửa thực thể `&am` cũng làm hỏng HTML
        t = t[:amp]
    for the in ("pre", "code", "b"):
        if t.count(f"<{the}>") > t.count(f"</{the}>"):
            t += f"</{the}>"
    return t + "\n(…cắt bớt)"


def soan_tin(title: str, ma: int, dur: str, dong: list[str], mien: list[str],
             composer: Path | None) -> str:
    links = trich_link(dong, mien)
    buoc = trich_buoc(dong)
    log_txt = "\n".join(dong)

    msg = ""
    if composer and (composer / "compose_report.py").is_file():
        msg = _goi_composer(composer / "compose_report.py",
                            ["--title", title, "--exit", str(ma), "--duration", dur],
                            log_txt, TRAN_COMPOSE)
    composed = bool(msg)
    if not composed:
        icon = "✅" if ma == 0 else "❌"
        msg = (f"{icon} <b>{_esc(title)}</b>\n"
               f"{_dt.datetime.now():%d/%m/%Y %H:%M} · chạy {dur} · exit {ma}")
        if links:
            msg += "\n\n<b>Link tạo được:</b>" + "".join(f"\n• {_esc(l)}" for l in links)
        elif ma == 0:
            msg += "\n(không phát hiện link sản phẩm trong log)"

    if ma != 0:
        if not composed:
            if buoc:
                msg += f"\n\n<b>Hỏng ở bước:</b> <code>{_esc(buoc[-1])}</code>"
                if len(buoc) > 1:
                    msg += "\n<b>Đã xong:</b>\n<pre>" + _esc("\n".join(buoc[-6:-1])) + "</pre>"
            else:
                msg += "\n\n<b>Hỏng ở bước:</b> (log không có dòng bước nào — xem log đuôi)"
        triaged = False
        if composer and (composer / "triage.py").is_file():
            bc = _goi_composer(composer / "triage.py",
                               ["--title", title, "--exit", str(ma)], log_txt, TRAN_TRIAGE)
            if bc:
                msg += "\n\n" + bc
                triaged = True
        if not triaged and not composed:
            msg += ("\n\n<b>Log đuôi (fail ở đây):</b>\n<pre>"
                    + _esc("\n".join(dong[-12:])) + "</pre>")

    khoi, tt = trich_do_phu(dong)
    if khoi and not composed:
        tieu = {"low": "🔴 <b>CẢNH BÁO: bài trước không ai xem</b>",
                "ok": "🟢 <b>Độ phủ Facebook</b>",
                "error": "⚠️ <b>Không kiểm được độ phủ</b>",
                "nodata": "<b>Độ phủ Facebook</b> (chưa đủ dữ liệu)"}.get(tt, "<b>Độ phủ Facebook</b>")
        msg += f"\n\n{tieu}\n<pre>" + _esc("\n".join(khoi[:16])) + "</pre>"
    return _cat(msg)


# ── Gửi ──────────────────────────────────────────────────────────────────────

def gui(text: str) -> bool:
    """Gửi tin. Không bao giờ ném — mọi lỗi chỉ ra stderr (đã che token)."""
    p = tg.duong_dan_cau_hinh()
    try:
        bot = tg.Bot(p)
    except FileNotFoundError:
        _loi(f"notify: không thấy cấu hình Telegram tại {p} "
             f"(đặt env TG_CONFIG nếu để chỗ khác) — bỏ qua gửi.")
        return False
    except Exception as e:  # noqa: BLE001
        _loi(f"notify: đọc cấu hình Telegram {p} lỗi — {e} — bỏ qua gửi.")
        return False
    try:
        bot.gui(text, html=True)
    except Exception as e:  # noqa: BLE001
        _loi(f"notify: gửi Telegram lỗi — {e}")
        return False
    print("notify: đã gửi Telegram.", flush=True)
    return True


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(
        prog="notify_run.py",
        description="Chạy lệnh con, báo kết quả về Telegram, trả nguyên mã thoát của lệnh con.",
        usage="%(prog)s --title T [--composer-dir DIR] [--link-domains D[,D]] "
              "[--timeout GIÂY] -- LỆNH [ĐỐI SỐ…]")
    ap.add_argument("--title", required=True, help="tên task hiện trên tin báo")
    ap.add_argument("--composer-dir", help="thư mục có compose_report.py / triage.py (engine)")
    ap.add_argument("--link-domains", action="append", default=[],
                    help="miền web của thương hiệu, tính là link sản phẩm (lặp hoặc dấu phẩy)")
    ap.add_argument("--timeout", type=int, default=0, metavar="GIÂY",
                    help="trần giờ cho lệnh con (launchd KHÔNG có ExecutionTimeLimit); "
                         "quá giờ = giết cả nhóm con, tin ❌, mã thoát 1")
    if "--" in argv:
        i = argv.index("--")
        opts, cmd = argv[:i], argv[i + 1:]
    else:
        opts, cmd = argv, []
    a = ap.parse_args(opts)
    if not cmd:
        ap.error("thiếu lệnh con sau `--`")
    if a.timeout < 0:
        ap.error("--timeout phải ≥ 0 (0 = không đặt trần)")

    composer = Path(a.composer_dir).expanduser() if a.composer_dir else None
    if composer and not composer.is_dir():
        _loi(f"notify: --composer-dir không tồn tại: {composer} — dùng định dạng dự phòng.")
        composer = None

    print(f"notify_run: {a.title} · {_dt.datetime.now():%Y-%m-%d %H:%M:%S}", flush=True)
    in_which()
    t0 = time.monotonic()
    ma, dong, qua_gio = chay_lenh(cmd, a.timeout or None)
    giay = int(time.monotonic() - t0)
    dur = f"{giay // 3600:02d}:{giay % 3600 // 60:02d}:{giay % 60:02d}"
    print(f"notify_run: lệnh con thoát mã {ma} sau {dur}", flush=True)

    tieu_de = f"{a.title} — QUÁ GIỜ {a.timeout}s" if qua_gio else a.title
    try:
        tin = soan_tin(tieu_de, ma, dur, dong, _mien(a.link_domains), composer)
        gui(tin)
    except Exception as e:  # noqa: BLE001 — báo cáo hỏng không được đổi mã thoát
        _loi(f"notify: soạn/gửi tin lỗi — {e}")
    return ma


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    sys.exit(main())
