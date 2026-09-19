#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`doctor` — khám một bản cài: trạm nằm đâu, rào còn sống không, thiếu gì thì cài tiếp.

Gọi từ `init_station.py` (bước cuối của bộ cài) và chạy tay bất cứ lúc nào. Nó **chỉ đọc**:
không tạo, không sửa, không xoá — một công cụ chẩn đoán mà tự sửa thì lần sau không ai
biết máy đã hỏng cái gì.

Mã thoát theo hợp đồng ba trạm (`scripts/lib/studio_contract.py`):

    0  đủ để chạy (có thể còn cảnh báo)
    2  cấu hình sai — hai nguồn sự thật, rào `.gitignore` bị thủng: phải SỬA
    3  chưa cài xong — chưa có trạm: phải CÀI TIẾP

Phân biệt 2 với 3 là để người đọc biết mình đang ở đâu: "làm tiếp bước còn thiếu" khác
hẳn "cái bạn đã làm đang sai".

Bản này khám phần **F17** (hai chế độ cài). Phần trạm giọng / trạm video của hợp đồng ba
trạm thêm vào `KHAM_THEM` ở cuối file (gói P2-G3) — một danh sách, để thêm mục không phải
sửa lại luồng.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

PROG = "doctor"
# Thư mục đồng bộ đám mây: git trong đó là index hỏng/treo, và `.env` trong đó là secret
# đã lên cloud của người khác. Cảnh báo chứ không chặn — có người cố ý làm thế.
TEN_CLOUD = ("OneDrive", "Google Drive", "My Drive", "Dropbox", "iCloud Drive",
             "com~apple~CloudDocs")
PHAI_BI_IGNORE = (SP.WORKSPACE, ".env", SP.LOCAL_CONFIG)

KHAM_THEM = []       # P2-G3 nối thêm hàm kham(so) -> None vào đây (trạm giọng / trạm video)


class So:
    """Ba mức: đỏ-chặn (mã 2) · thiếu (mã 3) · cảnh báo. Giống `check_tree.py`."""

    def __init__(self):
        self.fail: list[str] = []
        self.warn: list[str] = []
        self.info: list[str] = []
        self.code = SC.OK

    def hong(self, msg):
        self.fail.append(msg)
        self.code = max(self.code, SC.CONTRACT_ERROR)

    def thieu(self, msg):
        self.fail.append(msg)
        self.code = max(self.code, SC.STATION_MISSING)

    def nhac(self, msg):
        self.warn.append(msg)

    def ghi(self, msg):
        self.info.append(msg)


def _git_bo_qua(repo: Path, duong: str) -> bool | None:
    """`git check-ignore` của CHÍNH bản clone. None = không kiểm được (không git/không có git)."""
    if not (repo / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--no-index", duong],
                           capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.returncode == 0


def _trong_cloud(p: Path) -> str | None:
    phan = {x.lower() for x in p.parts}
    for t in TEN_CLOUD:
        if t.lower() in phan:
            return t
    return None


def kham(station=None) -> dict:
    so = So()
    repo = SP.repo_root()
    st, nguon = SP.resolve_station(station)
    che_do = SP.mode(repo) if repo else None
    so.ghi(f"repo  : {repo or '(không xác định được)'}")
    so.ghi(f"trạm  : {st}  (nguồn: {nguon})")
    so.ghi(f"chế độ: {che_do or '(chưa chạy bộ cài)'}")

    # 1. Trạm có thật chưa
    if not st.is_dir():
        so.thieu(f"chưa có trạm ở {st} — chạy bộ cài: python scripts/pipeline/init_station.py")
    elif not (st / SP.SO_KENH).is_file():
        so.thieu(f"{st} chưa có {SP.SO_KENH} — chạy lại bộ cài, hoặc trỏ --station đúng chỗ")

    # 2. HAI NGUỒN SỰ THẬT — lỗi nặng nhất của mô hình hai chế độ
    ws = SP.workspace_dir(repo)
    if ws and ws.is_dir() and ws.resolve() != st:
        so.hong(f"hai nguồn sự thật: {ws} tồn tại nhưng trạm đang dùng là {st} (nguồn {nguon}). "
                f"Giữ MỘT chỗ: dời {ws} đi, hoặc gỡ biến/`{SP.LOCAL_CONFIG}` đang trỏ chỗ kia.")

    # 3. Rào của chế độ embedded
    if repo and che_do == "embedded":
        for d in PHAI_BI_IGNORE:
            bo_qua = _git_bo_qua(repo, d if d != SP.WORKSPACE else f"{SP.WORKSPACE}/a")
            if bo_qua is False:
                so.hong(f"git KHÔNG bỏ qua {d!r} — nội dung riêng sẽ commit được. "
                        f"Khôi phục dòng {d!r} trong .gitignore.")
            elif bo_qua is None:
                so.nhac(f"không kiểm được `git check-ignore {d}` (không phải bản clone git?)")
        hook = repo / ".git" / "hooks" / "pre-commit"
        if (repo / ".git").is_dir() and not hook.is_file():
            so.nhac("chưa có hook .git/hooks/pre-commit — chạy lại bộ cài để cài rào thứ hai")
        f_env = repo / ".env"
        if not f_env.is_file():
            so.nhac(f"chưa có {f_env} — chép từ .env.example rồi điền đường dẫn của bạn")
        elif os.name != "nt":
            quyen = f_env.stat().st_mode & 0o777
            if quyen & 0o077:
                so.nhac(f".env đang mở cho người khác đọc ({oct(quyen)}) — chmod 600 {f_env}")

    # 4. Repo/trạm nằm trong thư mục đồng bộ đám mây
    for ten, p in (("repo", repo), ("trạm", st)):
        if p:
            c = _trong_cloud(p)
            if c:
                so.nhac(f"{ten} nằm trong thư mục đồng bộ {c} ({p}) — git ở đó hay hỏng index, "
                        "và mọi thứ trong đó đi lên cloud. Cân nhắc dời ra ngoài.")

    for them in KHAM_THEM:                  # P2-G3: trạm giọng, trạm video
        them(so)

    return {"code": so.code, "mode": che_do, "station": str(st), "source": nguon,
            "repo": str(repo) if repo else None,
            "fail": so.fail, "warn": so.warn, "info": so.info}


def _in(kq: dict):
    for x in kq["info"]:
        SC.log("  " + x)
    for x in kq["fail"]:
        SC.log(f"  ĐỎ   {x}")
    for x in kq["warn"]:
        SC.log(f"  nhắc {x}")
    ket = {SC.OK: "đủ để chạy", SC.CONTRACT_ERROR: "cấu hình SAI — sửa rồi chạy lại",
           SC.STATION_MISSING: "CHƯA CÀI XONG — làm nốt bước còn thiếu"}[kq["code"]]
    SC.log(f"\n  {len(kq['fail'])} đỏ · {len(kq['warn'])} cảnh báo — {ket}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog=PROG, description="Khám bản cài: trạm, rào, thứ còn thiếu.")
    ap.add_argument("--station", help="khám một trạm cụ thể thay vì trạm đang phân giải")
    ap.add_argument("--json", action="store_true")
    args, ma = SC.parse(ap, argv)
    if args is None:
        return ma
    kq = kham(args.station)
    _in(kq)
    if args.json:
        SC.emit({"ok": kq["code"] == SC.OK, **kq})
    return kq["code"]


if __name__ == "__main__":
    sys.exit(main())
