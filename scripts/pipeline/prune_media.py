#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dọn media quá hạn ở các trạm — mặc định CHỈ IN, dời/xoá phải gõ ra.

Đường ống tự động sinh audio/video liên tục; đĩa thì không tự lớn. Luật giữ là **14 ngày**,
và bước tìm-media-quá-hạn chạy TRƯỚC mỗi lượt tự động, không phải sau khi đĩa đầy.

## Vì sao audio và video không cùng một luật

- **Video**: bản ở lại là bản đã đăng (YouTube/Facebook). File trên trạm là bản render —
  quá hạn thì dọn, không hỏi gì thêm.
- **Audio**: bản ở lại là bản trong **repo web**. Nên trước khi dọn một `.mp3`/`.wav`,
  script phải THẤY bản web đó — cụ thể là thư mục `<repo web>/<kênh>/audio/<ngày>/`.
  Không thấy ⇒ **giữ**, và ghi lý do vào báo cáo. Đây là khác biệt cố ý: mất một bản
  render video là mất vài chục phút GPU, mất bản audio duy nhất là mất hẳn.

Trạm mà audio chỉ là bản render trung gian (không có repo web nào để mà đối chiếu) thì
dùng `--audio-policy age`. Nó phải được GÕ RA: mặc định im lặng dọn audio theo tuổi là
đúng cái bẫy ở trên, chỉ khác là không ai thấy lúc nó xảy ra.

## Thứ script này không bao giờ đụng tới

`.raw/` (giọng gốc để clone) · `voices/` · `assets/` · `.venv`, `venv`, `site-packages`,
`node_modules`, `__pycache__`, `.git` — và mọi đuôi ngoài danh sách media (`.json` cạnh
file `.wav` là bảng cue, xoá nó là hỏng bản dựng; `.md`, ảnh cũng vậy).

`site-packages` trong danh sách không phải đề phòng suông: trạm video có một `.venv` với
mấy chục file `.wav` mẫu của `scipy` nằm sâu bên trong. Quét theo đuôi file mà không loại
thư mục công cụ thì lượt dọn đầu tiên sẽ tháo rời chính cái venv đang chạy đường ống.

Một `--root` trỏ thẳng vào thư mục cấm bị TỪ CHỐI (mã 2) — đó là cách dễ nhất để vượt rào
mà vẫn trông như một lệnh hợp lệ.

## Ba chế độ

    (mặc định)      chỉ in — không chạm một byte nào trên đĩa
    --move-to DIR   dời, GIỮ NGUYÊN cấu trúc tương đối, tự ghi manifest vào DIR
    --delete        xoá thật — chỉ khi gõ ra

Mã thoát theo hợp đồng ba trạm: 0 ổn · 2 tham số/cấu hình sai · 3 thiếu trạm (đường dẫn
không có thật). Xem `scripts/lib/studio_contract.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402

PROG = "prune_media"
NGAY = 86400.0
MAC_DINH_NGAY = 14
TEN_MANIFEST = "manifest-prune-media.json"

DUOI_VIDEO = {".mp4", ".mov", ".webm"}
DUOI_AUDIO = {".mp3", ".wav"}

# Tên thư mục KHÔNG bao giờ đi vào: so khớp theo TỪNG THÀNH PHẦN của đường dẫn, không
# phải theo tiền tố chuỗi — `assets` nằm ở tầng thứ tư vẫn phải bị loại.
THU_MUC_CAM = {".raw", "voices", "assets", ".venv", "venv", "site-packages",
               "node_modules", "__pycache__", ".git"}

CHINH_SACH_AUDIO = ("web-first", "age", "keep")
_NGAY_TRONG_TEN = re.compile(r"(\d{4}-\d{2}-\d{2})")

Goc = namedtuple("Goc", "label path")


def no_duong(p) -> Path:
    """`~` và biến môi trường mở ra, dấu gạch chéo nào cũng được — người gõ trên macOS và
    người gõ trên Windows phải dùng được cùng một dòng lệnh."""
    return Path(os.path.expandvars(str(p))).expanduser().resolve()


def _nhan_hop_le(nhan: str) -> bool:
    """Nhãn là MỘT đoạn thư mục: không tách, không đi lên. Nhãn `../..` biến `--move-to`
    thành lệnh ghi ra ngoài thư mục người dùng chỉ định."""
    return bool(nhan) and nhan not in (".", "..") and not set(nhan) & set("/" + chr(92))


def doc_goc(gia_tri: str) -> Goc:
    """`NHÃN=ĐƯỜNG` hoặc `ĐƯỜNG` (nhãn = tên thư mục cuối). Tách ở dấu `=` ĐẦU TIÊN vì
    đường dẫn Windows có dấu hai chấm nhưng không có dấu bằng."""
    nhan, dau, duong = gia_tri.partition("=")
    if not dau:
        p = no_duong(gia_tri)
        return Goc(p.name or "root", p)
    if not _nhan_hop_le(nhan):
        raise SC.ContractError(
            f"nhãn {nhan!r} không hợp lệ — nhãn là MỘT tên thư mục, không chứa dấu gạch "
            f"chéo và không phải `..`")
    return Goc(nhan, no_duong(duong))


def _co_phan_cam(p: Path) -> str | None:
    for phan in p.parts:
        if phan in THU_MUC_CAM:
            return phan
    return None


def _dang_khoa(p: Path) -> bool:
    """Mở được để GHI thì coi như rảnh. Không mở được ⇒ có thể đang có tiến trình giữ nó,
    hoặc file chỉ-đọc — cả hai đều là lý do chính đáng để không đụng vào.

    Đây là phép đo YẾU trên POSIX (không có khoá bắt buộc). Nó nói đúng cái nó đo được:
    "không mở được để ghi", chứ không tự xưng là "đang có tiến trình khác dùng"."""
    try:
        with open(p, "rb+"):
            return False
    except OSError:
        return True


def _ngay_cua(rel: Path, mtime: float) -> str:
    """Ngày của một file: lấy từ TÊN thư mục/ tên file nếu có (`…/2026-09-18/x.mp3`),
    không có thì lấy theo `mtime`. Ưu tiên tên vì đường ống đặt tên theo ngày XUẤT BẢN,
    còn `mtime` đổi mỗi lần ai đó chạm vào file."""
    for phan in reversed(rel.parts):
        m = _NGAY_TRONG_TEN.search(phan)
        if m:
            return m.group(1)
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")


def _kenh_cua(rel: Path, nhan: str) -> str:
    return rel.parts[0] if len(rel.parts) > 1 else nhan


def _ban_web(web_repo: Path | None, kenh: str, ngay: str, anh_xa: dict) -> Path | None:
    """Thư mục bản web của (kênh, ngày) nếu có thật. Ánh xạ tên kênh khai bằng cờ —
    KHÔNG đoán: tên trên trạm (`ai-news`) và tên trên web (`ai`) khác nhau là chuyện
    bình thường, và một cái đoán sai ở đây là một file bị dọn nhầm."""
    if not web_repo:
        return None
    seg = anh_xa.get(kenh, kenh)
    d = web_repo / seg / "audio" / ngay
    return d if d.is_dir() else None


def quet(gocs, days=MAC_DINH_NGAY, web_repo=None, web_channel=None,
         audio_policy="web-first", now=None) -> dict:
    """Lập KẾ HOẠCH (không chạm đĩa): mỗi file media một mục `prune`/`keep` + lý do."""
    if audio_policy not in CHINH_SACH_AUDIO:
        raise SC.ContractError(f"--audio-policy phải là một trong {CHINH_SACH_AUDIO}")
    if days < 0:
        raise SC.ContractError("--days không âm")
    web_repo = Path(web_repo).resolve() if web_repo else None
    anh_xa = dict(web_channel or {})
    now = time.time() if now is None else now
    han = now - days * NGAY

    entries = []
    for g in gocs:
        cam = _co_phan_cam(g.path)
        if cam:
            raise SC.ContractError(
                f"--root {g.path} nằm trong/là thư mục CẤM ĐỤNG ({cam!r}) — đây là kho "
                f"giọng gốc, assets hoặc thư mục công cụ, không phải chỗ để dọn")
        if not g.path.is_dir():
            raise SC.StationMissing(f"không thấy thư mục {g.path}")
        for p in sorted(g.path.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            duoi = p.suffix.lower()
            if duoi not in DUOI_VIDEO and duoi not in DUOI_AUDIO:
                continue
            rel = p.relative_to(g.path)
            if _co_phan_cam(rel):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            muc = {"label": g.label, "root": g.path.as_posix(), "rel": rel.as_posix(),
                   "path": p.as_posix(), "bytes": st.st_size,
                   "mtime": datetime.fromtimestamp(st.st_mtime,
                                                   tz=timezone.utc).strftime("%Y-%m-%d"),
                   "kind": "video" if duoi in DUOI_VIDEO else "audio"}
            entries.append({**muc, **_quyet(p, rel, st.st_mtime, han, days, muc["kind"],
                                            g.label, web_repo, anh_xa, audio_policy)})
    return {"schema": "prune-media/1", "days": days, "audio_policy": audio_policy,
            "web_repo": web_repo.as_posix() if web_repo else None,
            "generated_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(
                timespec="seconds"),
            "roots": [{"label": g.label, "path": g.path.as_posix()} for g in gocs],
            "entries": entries, "totals": tong(entries)}


def _quyet(p, rel, mtime, han, days, loai, nhan, web_repo, anh_xa, chinh_sach) -> dict:
    if mtime > han:
        return {"action": "keep", "reason": f"còn trong hạn {days} ngày"}
    if _dang_khoa(p):
        return {"action": "keep",
                "reason": "không mở được để ghi (có thể đang bị khoá / đang ghi) — bỏ qua"}
    if loai == "video":
        return {"action": "prune", "reason": f"video quá {days} ngày"}
    if chinh_sach == "keep":
        return {"action": "keep", "reason": "audio quá hạn — `--audio-policy keep`"}
    if chinh_sach == "age":
        return {"action": "prune", "reason": f"audio quá {days} ngày (`--audio-policy age`)"}
    ngay = _ngay_cua(rel, mtime)
    kenh = _kenh_cua(rel, nhan)
    d = _ban_web(web_repo, kenh, ngay, anh_xa)
    if d:
        return {"action": "prune", "reason": f"audio quá hạn, bản web đã có ở {d.as_posix()}"}
    if not web_repo:
        return {"action": "keep",
                "reason": "audio quá hạn nhưng chưa khai repo web (`--web-repo`) để đối "
                          "chiếu — giữ"}
    return {"action": "keep",
            "reason": f"audio quá hạn nhưng CHƯA thấy bản web "
                      f"{anh_xa.get(kenh, kenh)}/audio/{ngay} — giữ"}


def tong(entries) -> dict:
    ra = {"prune": {"files": 0, "bytes": 0}, "keep": {"files": 0, "bytes": 0},
          "by_root": {}, "by_dir": {}}
    for e in entries:
        ra[e["action"]]["files"] += 1
        ra[e["action"]]["bytes"] += e["bytes"]
        for khoa, o in (("by_root", e["label"]),
                        ("by_dir", f"{e['label']}/{Path(e['rel']).parts[0]}"
                                   if len(Path(e["rel"]).parts) > 1 else e["label"])):
            d = ra[khoa].setdefault(o, {"prune_files": 0, "prune_bytes": 0,
                                        "keep_files": 0, "keep_bytes": 0})
            d[f"{e['action']}_files"] += 1
            d[f"{e['action']}_bytes"] += e["bytes"]
    return ra


# ── thi hành ─────────────────────────────────────────────────────────────────

def _dich(move_to: Path, e: dict) -> Path:
    return move_to / e["label"] / Path(e["rel"])


def thuc_thi(ke_hoach: dict, move_to=None, delete=False) -> list[str]:
    """Dời hoặc xoá những mục `prune`. Trả danh sách lỗi (rỗng = trọn vẹn).

    KHÔNG đè lên file đã có ở đích: đè là mất dữ liệu một cách im lặng, đúng thứ cả lượt
    dọn này sinh ra để tránh. Gặp trùng thì bỏ qua file đó và báo lỗi."""
    loi = []
    for e in ke_hoach["entries"]:
        if e["action"] != "prune":
            continue
        p = Path(e["path"])
        try:
            if move_to:
                d = _dich(Path(move_to), e)
                if d.exists():
                    loi.append(f"{e['rel']}: đích đã có file — không đè, bỏ qua")
                    continue
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(d))
                e["moved_to"] = d.as_posix()
            elif delete:
                p.unlink()
                e["deleted"] = True
        except OSError as ex:
            loi.append(f"{e['rel']}: {ex}")
    return loi


def _mb(n) -> str:
    return f"{n / 1048576:.1f} MB"


def _bao_cao(kq: dict, che_do: str):
    SC.log(f"\n  chế độ: {che_do} · giữ {kq['days']} ngày · audio: {kq['audio_policy']}")
    for o, d in sorted(kq["totals"]["by_dir"].items()):
        SC.log(f"    {o:44} dọn {d['prune_files']:4} ({_mb(d['prune_bytes']):>10}) · "
               f"giữ {d['keep_files']:4} ({_mb(d['keep_bytes']):>10})")
    t = kq["totals"]
    SC.log(f"  ── tổng: dọn {t['prune']['files']} file ({_mb(t['prune']['bytes'])}) · "
           f"giữ {t['keep']['files']} file ({_mb(t['keep']['bytes'])})")
    ly_do = {}
    for e in kq["entries"]:
        if e["action"] == "keep":
            ly_do[e["reason"]] = ly_do.get(e["reason"], 0) + 1
    for r, n in sorted(ly_do.items(), key=lambda x: -x[1]):
        SC.log(f"    giữ {n:4} vì: {r}")


def _lam(args) -> dict:
    if not args.root:
        raise SC.ContractError("phải có ít nhất một `--root [NHÃN=]ĐƯỜNG_DẪN`")
    if args.move_to and args.delete:
        raise SC.ContractError("`--move-to` và `--delete` loại trừ nhau — chọn một")
    gocs = [doc_goc(r) for r in args.root]

    move_to = no_duong(args.move_to) if args.move_to else None
    if move_to:
        for g in gocs:
            if move_to == g.path or g.path in move_to.parents:
                raise SC.ContractError(
                    f"`--move-to` ({move_to}) nằm TRONG gốc đang quét ({g.path}) — lượt sau "
                    f"sẽ quét lại chính chỗ vừa dời")

    # Repo web mặc định đọc từ biến môi trường — KHÔNG có đường cứng nào trong mã: bố
    # cục đĩa của một máy không phải hằng số của chương trình.
    web_repo = args.web_repo or (os.environ.get("WEB_REPO_DIR") or "").strip() or None
    anh_xa = {}
    for c in (args.web_channel or []):
        ten, dau, seg = c.partition("=")
        if not (dau and ten and seg):
            raise SC.ContractError(f"--web-channel phải là `KÊNH=THƯ_MỤC_WEB`, nhận {c!r}")
        anh_xa[ten] = seg
    if web_repo:
        web_repo = no_duong(web_repo)
        if not web_repo.is_dir():
            raise SC.StationMissing(f"không thấy repo web {web_repo}")

    kq = quet(gocs, days=args.days, web_repo=web_repo, web_channel=anh_xa,
              audio_policy=args.audio_policy)

    che_do = "DỜI" if move_to else ("XOÁ" if args.delete else "chỉ in (dry-run)")
    loi = []
    if move_to or args.delete:
        loi = thuc_thi(kq, move_to=move_to, delete=args.delete)
        kq["totals"] = tong(kq["entries"])
    _bao_cao(kq, che_do)

    manifest = no_duong(args.manifest) if args.manifest else (
        move_to / TEN_MANIFEST if move_to else None)
    if manifest:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(kq, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
        SC.log(f"  kê khai: {manifest}")
    for x in loi:
        SC.log(f"  ĐỎ   {x}")
    if loi:
        raise SC.EngineError(f"{len(loi)} file không dời/xoá được (xem stderr)")
    return {"days": kq["days"], "totals": kq["totals"],
            "manifest": manifest.as_posix() if manifest else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog=PROG, description="Tìm media quá hạn ở các trạm; mặc định chỉ in.")
    ap.add_argument("--root", action="append", metavar="[NHÃN=]ĐƯỜNG",
                    help="thư mục cần quét; lặp lại được. NHÃN là tên thư mục con ở đích "
                         "khi dời (mặc định: tên thư mục cuối của ĐƯỜNG)")
    ap.add_argument("--days", type=int, default=MAC_DINH_NGAY,
                    help=f"giữ media mới hơn ngần này ngày (mặc định {MAC_DINH_NGAY})")
    ap.add_argument("--dry-run", action="store_true",
                    help="chỉ in (đây đã là mặc định; cờ để gõ cho rõ ý)")
    ap.add_argument("--move-to", metavar="THU_MUC",
                    help="dời media quá hạn vào đây, giữ nguyên cấu trúc tương đối")
    ap.add_argument("--delete", action="store_true", help="XOÁ THẬT media quá hạn")
    ap.add_argument("--web-repo", metavar="ĐƯỜNG",
                    help="repo web để đối chiếu bản audio đã đăng; bỏ trống thì đọc biến "
                         "môi trường WEB_REPO_DIR")
    ap.add_argument("--web-channel", action="append", metavar="KÊNH=THƯ_MỤC_WEB",
                    help="ánh xạ tên kênh ở trạm sang tên thư mục trên repo web")
    ap.add_argument("--audio-policy", choices=CHINH_SACH_AUDIO, default="web-first",
                    help="web-first (mặc định): chỉ dọn audio đã có bản web · age: dọn "
                         "theo tuổi · keep: không bao giờ dọn audio")
    ap.add_argument("--manifest", metavar="FILE",
                    help=f"nơi ghi kê khai (mặc định khi dời: <move-to>/{TEN_MANIFEST})")
    ap.add_argument("--json", action="store_true")
    args, ma = SC.parse(ap, argv)
    if args is None:
        return ma
    args.prog = PROG
    return SC.run(_lam, args, as_json=args.json)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
