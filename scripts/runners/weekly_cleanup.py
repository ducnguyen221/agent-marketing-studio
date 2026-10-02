# -*- coding: utf-8 -*-
"""Dọn dung lượng hằng tuần: dời media đã đăng sang `_trash`, đổ `_trash` cũ, xoay vòng log, báo cỡ.

    python scripts/runners/weekly_cleanup.py --dry-run        # chỉ in — không chạm một byte
    python scripts/runners/weekly_cleanup.py                  # làm thật (job tuần gọi thế này)

Job lịch: `studio.marketing.weekly-cleanup` (launchd, Chủ nhật 04:00) · `run-weekly-cleanup.ps1
-Register` (Task Scheduler). Cả hai CHỈ nạp khi gọi đích danh — xem `install_launchd.py`.

## Vì sao (Mac mini 02/10/2026)

Mỗi lượt tự dọn lượt trước (truyện: `sweep_old`; tin: xoá mp4 sau khi YouTube có bản), nên
dung lượng có trần. Hai lỗ hổng còn lại: `prune_media.py` — lưới an toàn theo BẰNG CHỨNG đã
đăng — chưa gắn lịch trên máy nào (`docs/RETENTION.md` §7), và log không xoay vòng (~0,5 MB/lượt
truyện, lớn mãi).

## Bốn bước, mỗi bước độc lập (một bước hỏng không chặn bước sau)

1. **Dời** media đã đăng và quá `--days` ngày (14): `prune_media.py --video-policy published
   --audio-policy web-first --move-to <trạm>/_trash/<hôm nay>` trên các thư mục của trạm
   marketing + trạm giọng + trạm video. Không bằng chứng ⇒ GIỮ (luật của `prune_media`). Dời,
   không xoá; kê khai `manifest-prune-media.json` nằm trong chính thư mục ngày đó — hoàn tác
   bằng cách chép ngược theo kê khai (`docs/RETENTION.md` §6).
2. **Đổ `_trash`**: thư mục `_trash/<YYYY-MM-DD>` có NGÀY DỜI cũ hơn `--trash-days` (30) bị xoá.
   Tính theo tên thư mục (ngày dời), không theo mtime của file (file dời giữ mtime gốc — tính
   theo đó là xoá luôn thứ vừa dời hôm nay). Tên không phải ngày ⇒ không đụng.
3. **Xoay vòng log**: `<trạm giọng>/omnivoice/truyen-out/daily-logs/` và `<trạm>/logs/launchd/`:
   file cũ hơn `--log-days` (60) bị xoá; file lớn hơn `--log-max-mb` (5) bị CẮT, giữ 1 MB cuối
   (log của launchd mở chế độ nối đuôi — cắt tại chỗ, không xoá, nên job đang ghi vẫn ghi tiếp).
4. **Báo cỡ** từng trạm + `_trash`. Dòng `CLEANUP_*` ra stdout cho `compose_report.py`: cả
   wrapper launchd (`notify_run.py`) lẫn wrapper Task Scheduler gọi nó, nên tin Telegram của hai
   máy cùng một nội dung.

`--dry-run`: `prune_media` ở chế độ chỉ-in, bước 2–3 chỉ liệt kê. Không chạm gì.

Mã thoát (hợp đồng ba trạm): 0 ổn · 1 có bước hỏng (đọc dòng `ĐỎ`) · 2 tham số sai hoặc
`prune_media` từ chối (cầu dao vượt trần — có gì đó sai ở tầng trên, xem tay) · 3 chưa có trạm.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

PROG = "weekly_cleanup.py"
REPO = Path(__file__).resolve().parents[2]
PRUNE = REPO / "scripts" / "pipeline" / "prune_media.py"
TRASH = "_trash"
NGAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GIU_DUOI = 1024 * 1024            # cắt log lớn: giữ ngần này byte cuối
# Thư mục cấp một của trạm marketing KHÔNG quét media: thùng rác của chính job này, log, sổ
# kê khai của prune_media, và mọi thứ bắt đầu bằng `_`/`.` (state nội bộ: `_agent-call`…).
KHONG_QUET = {"logs", "prune-media-log"}
SO_DANG = ("truyen-state.json", "playlist-youtube.json")


def _in(dong: str) -> None:
    """Dòng máy đọc (CLEANUP_*) — stdout, để vào log của lượt chạy."""
    print(dong, flush=True)


def _mb(b: int) -> str:
    return f"{b / 1024 ** 2:,.1f} MB" if b < 1024 ** 3 else f"{b / 1024 ** 3:,.2f} GB"


def co_thu_muc(p: Path) -> int:
    """Tổng byte dưới `p`, KHÔNG đi xuyên symlink/junction (đếm trùng hoặc đếm cây ngoài trạm)."""
    tong, ngan = 0, [str(p)]
    while ngan:
        d = ngan.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_symlink() or getattr(e, "is_junction", lambda: False)():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            ngan.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            tong += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return tong


# ── 1. dời media đã đăng ───────────────────────────────────────────────────────

def goc_quet(tram: Path, giong: Path | None, video: Path | None) -> list[str]:
    """`NHÃN=ĐƯỜNG` cho prune_media. Thư mục con của trạm marketing (không gồm `_trash`), cộng
    nguyên trạm giọng/video. `_trash` không bao giờ là gốc: prune_media từ chối `--move-to`
    nằm trong gốc, và quét thùng rác là dời đi dời lại chính nó."""
    ra = []
    if tram.is_dir():
        for d in sorted(tram.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")) and d.name not in KHONG_QUET:
                ra.append(f"{d.name}={d}")
    for nhan, p in (("tram-giong", giong), ("tram-video", video)):
        if p is not None and Path(p).is_dir() and Path(p).resolve() != tram.resolve():
            ra.append(f"{nhan}={p}")
    return ra


def so_dang(tram: Path) -> list[str]:
    """Sổ đăng của trạm (`truyen-state.json`, `playlist-youtube.json` ở `<kênh>/<chiến dịch>/`)."""
    ra = []
    for ten in SO_DANG:
        ra += [str(p) for p in sorted(tram.glob(f"*/*/{ten}"))]
    return ra


def doi_media(tram: Path, goc: list[str], dich: Path, days: int, dry: bool) -> tuple[int, dict]:
    """Gọi prune_media (tiến trình con — cách ly, đúng dòng lệnh người chạy tay). -> (mã, kq)."""
    if not goc:
        SC.log("[dọn] 1. không có thư mục media nào để quét")
        return 0, {}
    cmd = [sys.executable, str(PRUNE), "--video-policy", "published", "--audio-policy",
           "web-first", "--days", str(days), "--json"]
    for g in goc:
        cmd += ["--root", g]
    for e in so_dang(tram):
        cmd += ["--evidence", e]
    if not dry:
        cmd += ["--move-to", str(dich)]
    SC.log(f"[dọn] 1. prune_media ({'chỉ in' if dry else 'DỜI → ' + str(dich)}) · "
           f"{len(goc)} gốc · quá {days} ngày + có bằng chứng đã đăng")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    for d in (r.stderr or "").splitlines():
        SC.log("    " + d)
    kq = {}
    for d in reversed((r.stdout or "").splitlines()):
        d = d.strip()
        if d.startswith("{") and d.endswith("}"):
            try:
                kq = json.loads(d)
            except ValueError:
                pass
            break
    return r.returncode, kq


# ── 2. đổ thùng rác ────────────────────────────────────────────────────────────

def do_rac(rac: Path, tran_ngay: int, hom_nay: _dt.date, dry: bool) -> tuple[list, list]:
    """Xoá `_trash/<YYYY-MM-DD>` có ngày dời cũ hơn `tran_ngay`. -> ([(đường, byte)], [lỗi])."""
    xoa, loi = [], []
    if not rac.is_dir():
        return xoa, loi
    for d in sorted(rac.iterdir()):
        if not (d.is_dir() and NGAY_RE.match(d.name)):
            continue
        try:
            ngay = _dt.date.fromisoformat(d.name)
        except ValueError:
            continue
        if (hom_nay - ngay).days <= tran_ngay:
            continue
        b = co_thu_muc(d)
        if not dry:
            try:
                shutil.rmtree(d)
            except OSError as e:
                loi.append(f"{d}: {e}")
                continue
        xoa.append((d, b))
    return xoa, loi


# ── 3. xoay vòng log ───────────────────────────────────────────────────────────

def cat_duoi(p: Path, giu: int = GIU_DUOI) -> None:
    """Giữ `giu` byte cuối (bắt đầu từ đầu một dòng), cắt tại chỗ — không xoá, không đổi inode."""
    with open(p, "r+b") as f:
        f.seek(0, os.SEEK_END)
        n = f.tell()
        if n <= giu:
            return
        f.seek(n - giu)
        duoi = f.read()
        nl = duoi.find(b"\n")
        if 0 <= nl < len(duoi) - 1:
            duoi = duoi[nl + 1:]
        f.seek(0)
        f.write(b"[weekly_cleanup: da cat phan dau cua log]\n" + duoi)
        f.truncate()


def xoay_log(thu_muc: list[Path], tran_ngay: int, tran_mb: float, bay_gio: float,
             dry: bool) -> tuple[list, list, list]:
    """-> ([đã xoá], [đã cắt], [lỗi]). Chỉ file trực tiếp trong mỗi thư mục, không đệ quy."""
    xoa, cat, loi = [], [], []
    tran_b = int(tran_mb * 1024 * 1024)
    for d in thu_muc:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.is_symlink():
                continue
            try:
                st = f.stat()
                if bay_gio - st.st_mtime > tran_ngay * 86400:
                    if not dry:
                        f.unlink()
                    xoa.append(f)
                elif st.st_size > tran_b:
                    if not dry:
                        cat_duoi(f)
                    cat.append(f)
            except OSError as e:
                loi.append(f"{f}: {e}")
    return xoa, cat, loi


def thu_muc_log(tram: Path, giong: Path | None) -> list[Path]:
    ra = [tram / "logs" / "launchd"]
    if giong is not None:
        ra.append(Path(giong) / "omnivoice" / "truyen-out" / "daily-logs")
    return ra


# ── việc chính ─────────────────────────────────────────────────────────────────

def lam(a) -> dict:
    tram, nguon = SP.resolve_station(a.station)
    if not tram.is_dir():
        raise SC.StationMissing(f"chưa có trạm marketing {tram} (nguồn: {nguon})")
    giong, video = SP.voice_station(), SP.video_station()
    hom_nay = _dt.date.today()
    rac = tram / TRASH
    dich = rac / hom_nay.isoformat()
    dry = a.dry_run
    SC.log(f"[dọn] {'XEM TRƯỚC (dry-run) — không chạm gì' if dry else 'chạy thật'} · trạm {tram}")
    do: list[str] = []
    ma_prune = 0

    # 1
    ma_prune, kq = doi_media(tram, goc_quet(tram, giong, video), dich, a.days, dry)
    t = (kq.get("totals") or {})
    doi_f = (t.get("prune") or {}).get("files", 0)
    doi_b = (t.get("prune") or {}).get("bytes", 0)
    giu_f = (t.get("keep") or {}).get("files", 0)
    if ma_prune:
        do.append(f"prune_media mã {ma_prune} (xem log phía trên)")
    _in(f"CLEANUP_PRUNE mode={'dry-run' if dry else 'move'} files={doi_f} bytes={doi_b} "
        f"kept={giu_f} code={ma_prune}")

    # 2
    xoa_rac, loi_rac = do_rac(rac, a.trash_days, hom_nay, dry)
    do += loi_rac
    for d, b in xoa_rac:
        SC.log(f"[dọn] 2. {'sẽ xoá' if dry else 'đã xoá'} {d} ({_mb(b)})")
    _in(f"CLEANUP_TRASH mode={'dry-run' if dry else 'purge'} dirs={len(xoa_rac)} "
        f"bytes={sum(b for _d, b in xoa_rac)}")

    # 3
    xoa_log, cat_log, loi_log = xoay_log(thu_muc_log(tram, giong), a.log_days, a.log_max_mb,
                                         _dt.datetime.now().timestamp(), dry)
    do += loi_log
    for f in xoa_log:
        SC.log(f"[dọn] 3. {'sẽ xoá' if dry else 'đã xoá'} log {f}")
    for f in cat_log:
        SC.log(f"[dọn] 3. {'sẽ cắt' if dry else 'đã cắt'} log {f} (> {a.log_max_mb} MB)")
    _in(f"CLEANUP_LOGS mode={'dry-run' if dry else 'rotate'} deleted={len(xoa_log)} "
        f"truncated={len(cat_log)}")

    # 4
    co = {}
    for nhan, p in (("marketing", tram), ("giong", giong), ("video", video), ("trash", rac)):
        if p is not None and Path(p).is_dir():
            b = co_thu_muc(Path(p)) if nhan != "marketing" else co_thu_muc(tram) - co_thu_muc(rac)
            co[nhan] = b
            _in(f"CLEANUP_SIZE label={nhan} bytes={b} path={p}")
    SC.log("[dọn] 4. dung lượng: " + " · ".join(f"{k} {_mb(v)}" for k, v in co.items()))

    for x in do:
        SC.log(f"  ĐỎ   {x}")
    _in(f"CLEANUP_DONE ok={0 if do else 1}")
    ra = {"dry_run": dry, "moved": {"files": doi_f, "bytes": doi_b}, "kept_files": giu_f,
          "trash_purged": len(xoa_rac), "logs_deleted": len(xoa_log),
          "logs_truncated": len(cat_log), "sizes": co,
          "manifest": kq.get("manifest")}
    if ma_prune == SC.CONTRACT_ERROR:
        raise SC.ContractError("prune_media từ chối (cầu dao hoặc tham số) — KHÔNG dời gì; "
                               "đọc log phía trên rồi xem tay")
    if do:
        raise SC.EngineError(f"{len(do)} bước/mục hỏng — đọc các dòng ĐỎ")
    return ra


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog=PROG, description="Dọn dung lượng hằng tuần (dời media đã "
                                 "đăng sang _trash, đổ _trash cũ, xoay vòng log, báo cỡ).")
    ap.add_argument("--station", help="gốc trạm marketing (mặc định: trạm đang phân giải)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in — không dời, không xoá, không cắt")
    ap.add_argument("--days", type=int, default=14, help="media quá ngần này ngày (mặc định 14)")
    ap.add_argument("--trash-days", type=int, default=30,
                    help="đổ thư mục _trash/<ngày dời> cũ hơn ngần này ngày (mặc định 30)")
    ap.add_argument("--log-days", type=int, default=60, help="xoá log cũ hơn (mặc định 60 ngày)")
    ap.add_argument("--log-max-mb", type=float, default=5,
                    help="cắt log lớn hơn ngần này MB, giữ 1 MB cuối (mặc định 5)")
    ap.add_argument("--json", action="store_true", help="in một dòng JSON kết quả")
    return ap


def main(argv=None) -> int:
    args, ma = SC.parse(_parser(), argv)
    if args is None:
        return ma
    if args.days < 1 or args.trash_days < 1 or args.log_days < 1 or args.log_max_mb <= 1:
        SC.log("--days/--trash-days/--log-days phải ≥ 1 và --log-max-mb phải > 1 "
               "(cắt giữ 1 MB cuối)")
        return SC.CONTRACT_ERROR
    args.prog = PROG
    return SC.run(lam, args, args.json)


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    sys.exit(main())
