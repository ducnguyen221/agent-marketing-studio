# -*- coding: utf-8 -*-
"""Xoay vòng log NGAY TRONG lượt chạy: xoá log quá hạn, cắt log quá cỡ, xoá gói chẩn đoán cũ.

    python scripts/lib/log_rotate.py --dir <thư mục log> [--dir …] [--old-dirs <thư mục>] \\
        [--days 60] [--max-mb 5] [--dry-run]

## Vì sao (SUBTASK-WIN-RUNTIME-3 §4, Mac mini 03/10/2026)

Đức gỡ job dọn tuần (`weekly-cleanup`): mỗi quy trình đã tự dọn media của nó (truyện quét lượt
trước, tin xoá mp4 sau khi lên YouTube, tuần giữ 14 thư mục video + 54 bản audio). Lỗ hổng duy
nhất còn lại là **log không xoay vòng** (~0,5 MB/lượt truyện, ~200 MB/năm). Nên xoay vòng đi theo
chính các lượt chạy — đầu mỗi lượt truyện và mỗi lượt tin — không cần job riêng.

## Luật (giống bước 3 của `weekly_cleanup.py`, nay dùng chung từ đây)

* `--dir`: CHỈ file trực tiếp (không đệ quy) khớp `--glob` (mặc định `*.log`); tên bắt đầu `_`
  (state/sổ kiểm của heal_agent: `_heal_state.json`, `_heal_audit.log`) KHÔNG đụng.
  Sửa lần cuối quá `--days` (60) ngày ⇒ xoá. Lớn hơn `--max-mb` (5) ⇒ CẮT tại chỗ, giữ 1 MB cuối
  (không xoá, không đổi inode — launchd vẫn nối đuôi vào đúng file).
* File vừa ghi trong `DANG_GHI_GIAY` (1 h) thì KHÔNG cắt: có thể chính lượt này (hoặc lượt khác)
  đang ghi; `daily-logs` mở chế độ `"w"`, cắt dưới chân nó để lại một khoảng byte 0.
* `--old-dirs`: thư mục CON trực tiếp (gói chẩn đoán `render-stuck/<giờ>/`) quá `--days` ⇒ xoá.
* **Không bao giờ làm hỏng lượt chạy**: thư mục không có thì bỏ qua, lỗi từng file chỉ in `WARN`,
  mã thoát luôn 0 (trừ tham số sai = 2). Một dòng tổng `LOG_ROTATE deleted=… truncated=…
  dirs=… errors=…` cho log của runner.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
import time
from pathlib import Path

GIU_DUOI = 1024 * 1024            # cắt log lớn: giữ ngần này byte cuối
DANG_GHI_GIAY = 3600              # log sửa trong ngần này giây = có thể đang được ghi ⇒ không cắt
NGAY = 60
TRAN_MB = 5.0


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


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
        f.write(b"[log_rotate: da cat phan dau cua log]\n" + duoi)
        f.truncate()


def xoay_log(thu_muc, tran_ngay: int, tran_mb: float, bay_gio: float, dry: bool,
             mau: str | None = None, log=_log) -> tuple[list, list, list]:
    """-> ([đã xoá], [đã cắt], [lỗi]). Chỉ file trực tiếp trong mỗi thư mục, không đệ quy.

    `mau` (vd `*.log`): chỉ file khớp mẫu, và bỏ qua tên bắt đầu `_`. `None` = mọi file (hành vi
    của job dọn tuần trên hai thư mục log thuần).
    """
    xoa, cat, loi = [], [], []
    tran_b = int(tran_mb * 1024 * 1024)
    for d in thu_muc:
        d = Path(d)
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.is_symlink():
                continue
            if mau is not None and (f.name.startswith("_") or not fnmatch.fnmatch(f.name, mau)):
                continue
            try:
                st = f.stat()
                if bay_gio - st.st_mtime > tran_ngay * 86400:
                    if not dry:
                        f.unlink()
                    xoa.append(f)
                elif st.st_size > tran_b and bay_gio - st.st_mtime < DANG_GHI_GIAY:
                    log(f"[log] bỏ qua cắt {f} — vừa ghi trong {DANG_GHI_GIAY // 60} phút, "
                        f"có thể đang được ghi; lượt sau cắt")
                elif st.st_size > tran_b:
                    if not dry:
                        cat_duoi(f)
                    cat.append(f)
            except OSError as e:
                loi.append(f"{f}: {e}")
    return xoa, cat, loi


def xoa_thu_muc_cu(goc, tran_ngay: int, bay_gio: float, dry: bool) -> tuple[list, list]:
    """Thư mục CON trực tiếp của mỗi `goc` sửa lần cuối quá `tran_ngay` ⇒ xoá. -> ([xoá], [lỗi])."""
    xoa, loi = [], []
    for g in goc:
        g = Path(g)
        if not g.is_dir():
            continue
        for d in sorted(g.iterdir()):
            if not d.is_dir() or d.is_symlink():
                continue
            try:
                if bay_gio - d.stat().st_mtime > tran_ngay * 86400:
                    if not dry:
                        shutil.rmtree(d)
                    xoa.append(d)
            except OSError as e:
                loi.append(f"{d}: {e}")
    return xoa, loi


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="log_rotate.py",
                                 description="Xoay vòng log trong lượt chạy (xoá quá hạn, cắt quá cỡ).")
    ap.add_argument("--dir", action="append", default=[], help="thư mục log (lặp được)")
    ap.add_argument("--old-dirs", action="append", default=[],
                    help="thư mục chứa thư mục con theo giờ (gói chẩn đoán) — xoá con quá hạn")
    ap.add_argument("--glob", default="*.log", help="mẫu tên file log (mặc định *.log)")
    ap.add_argument("--days", type=int, default=NGAY, help=f"xoá cũ hơn (mặc định {NGAY} ngày)")
    ap.add_argument("--max-mb", type=float, default=TRAN_MB,
                    help=f"cắt file lớn hơn (mặc định {TRAN_MB:g} MB), giữ 1 MB cuối")
    ap.add_argument("--dry-run", action="store_true", help="chỉ liệt kê, không chạm gì")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 2
    if a.days < 1 or a.max_mb <= 1:
        _log("--days phải ≥ 1 và --max-mb phải > 1 (cắt giữ 1 MB cuối)")
        return 2
    bay_gio = time.time()
    try:
        xoa, cat, loi = xoay_log(a.dir, a.days, a.max_mb, bay_gio, a.dry_run, mau=a.glob)
        xoa_d, loi_d = xoa_thu_muc_cu(a.old_dirs, a.days, bay_gio, a.dry_run)
    except Exception as e:  # noqa: BLE001 — xoay log hỏng không được làm hỏng lượt chạy
        print(f"WARN: xoay vong log loi - {e}", flush=True)
        return 0
    dong = "se " if a.dry_run else ""
    for f in xoa:
        print(f"log: {dong}xoa {f} (> {a.days} ngay)", flush=True)
    for f in cat:
        print(f"log: {dong}cat {f} (> {a.max_mb:g} MB, giu 1 MB cuoi)", flush=True)
    for d in xoa_d:
        print(f"log: {dong}xoa thu muc {d} (> {a.days} ngay)", flush=True)
    for e in loi + loi_d:
        print(f"WARN: log: {e}", flush=True)
    print(f"LOG_ROTATE mode={'dry-run' if a.dry_run else 'rotate'} deleted={len(xoa)} "
          f"truncated={len(cat)} dirs={len(xoa_d)} errors={len(loi) + len(loi_d)}", flush=True)
    return 0


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    sys.exit(main())
