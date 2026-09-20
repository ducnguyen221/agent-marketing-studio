#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dọn media quá hạn ở các trạm — mặc định CHỈ IN, dời/xoá phải gõ ra.

Đường ống tự động sinh audio/video liên tục; đĩa thì không tự lớn. Nhưng tuổi file chỉ nói
file cũ — nó không nói sản phẩm đã ra khỏi máy. Một lượt render hỏng nửa chừng cũng già đi
đúng 14 ngày như một tập đã lên sóng.

## Luật hiện hành: BẰNG CHỨNG trước, tuổi sau

    dọn  ⇐  (có BẰNG CHỨNG đã đăng)  ∧  (quá `--days` ngày)
    giữ  ⇐  mọi trường hợp còn lại, kèm lý do nói rõ THIẾU bằng chứng nào

- **Video**: bằng chứng là đã lên YouTube — `video_id`/`short_id` trong `*.published.json`
  nằm cạnh file (tin), hoặc `truyen-state.json`/`playlist-youtube.json` khai bằng
  `--evidence` (truyện). Xem `scripts/lib/publish_evidence.py`.
- **Audio**: bằng chứng là bản trong **repo web** — ĐÚNG FILE đó, không phải "thư mục của
  ngày đó có tồn tại". Một `.mp3` anh em đã đăng không chứng minh gì cho `raw.wav` bên
  cạnh; so theo thư mục là cách mất bản audio duy nhất mà vẫn trông như đúng luật.

Không có bằng chứng ⇒ **giữ**, và ghi lý do vào báo cáo. Đây là khác biệt cố ý: mất một
bản render video là mất vài chục phút GPU, mất bản audio duy nhất là mất hẳn.

**14 ngày bây giờ là SÀN AN TOÀN, không phải luật chính.** YouTube xử lý chậm và có lúc
phải đăng lại — chính `sweep_old()` của `daily_truyen.py` giữ video của lượt trước tới tận
lượt sau vì lý do đó. Muốn dọn ngay khi có bằng chứng thì `--days 0` (khi XOÁ còn phải gõ
thêm `--allow-days-0`).

Trạm mà media chỉ là bản render trung gian, không sổ đăng nào đối chiếu được, thì dùng
`--audio-policy age` / `--video-policy age`. Đó là **ngoại lệ có chủ đích** và phải được
GÕ RA: mặc định im lặng dọn theo tuổi là đúng cái bẫy ở trên, chỉ khác là không ai thấy
lúc nó xảy ra. Trạm truyện đang dùng `--audio-policy age` vì kênh đó không đăng web.

Cơ chế `sweep_old()` của đường ống truyện **giữ nguyên**, không gộp vào đây: nó dọn sản
phẩm của lượt TRƯỚC ngay đầu lượt SAU và chỉ khi lượt trước publish OK — một luật khác,
sống ở trạm, và sẽ được bê sang Mac y hệt.

## Thứ script này không bao giờ đụng tới

`.raw/` (giọng gốc để clone) · `voices/` · `assets/` · `.venv`, `venv`, `site-packages`,
`node_modules`, `__pycache__`, `.git` — và mọi đuôi ngoài danh sách media (`.json` cạnh
file `.wav` là bảng cue, xoá nó là hỏng bản dựng; `.md`, ảnh cũng vậy).

`site-packages` trong danh sách không phải đề phòng suông: trạm video có một `.venv` với
mấy chục file `.wav` mẫu của `scipy` nằm sâu bên trong. Quét theo đuôi file mà không loại
thư mục công cụ thì lượt dọn đầu tiên sẽ tháo rời chính cái venv đang chạy đường ống.

Một `--root` trỏ thẳng vào thư mục cấm bị TỪ CHỐI (mã 2) — đó là cách dễ nhất để vượt rào
mà vẫn trông như một lệnh hợp lệ.

**Liên kết thư mục không bao giờ đi xuyên qua.** `Path.is_symlink()` trả `False` cho
junction của Windows (đo thật), nên một `mklink /J` trong trạm đủ để kéo cả một cây NGOÀI
trạm vào kế hoạch xoá — và với `--delete` thì xoá ở vị trí thật. Ở đây dò bằng cờ
`FILE_ATTRIBUTE_REPARSE_POINT` và chốt lại bằng `resolve()` phải còn nằm trong gốc.

## Ba chế độ

    (mặc định)      chỉ in — không chạm một byte nào trên đĩa
    --move-to DIR   dời, GIỮ NGUYÊN cấu trúc tương đối, tự ghi manifest vào DIR
    --delete        xoá thật — chỉ khi gõ ra

**Mọi lượt chạm đĩa đều để lại KÊ KHAI, và kê khai ghi TRƯỚC khi đụng byte đầu tiên.**
`--delete` không khai `--manifest` thì sổ vào `<gốc>/../prune-media-log/<ngày>…json`;
không ghi được sổ ⇒ mã 2 và **không xoá gì**. Lý do: chế độ này là chế độ sắp chạy theo
lịch, không người nhìn — một đêm `WEB_REPO_DIR` rơi mất là một lô file biến mất, và không
có sổ thì không ai dựng lại được danh sách đã mất gì.

**Cầu dao** `--max-files` / `--max-bytes` chặn trước khi thi hành: vượt trần ⇒ mã 2, không
chạm file nào. Một lượt tự động không bao giờ nên là lượt xoá cả kho.

Mã thoát theo hợp đồng ba trạm: 0 ổn · 2 tham số/cấu hình sai · 3 thiếu trạm (đường dẫn
không có thật). Xem `scripts/lib/studio_contract.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat as _stat
import sys
import time
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import publish_evidence as PE  # noqa: E402
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

PROG = "prune_media"
NGAY = 86400.0
MAC_DINH_NGAY = 14
TEN_MANIFEST = "manifest-prune-media.json"
# Sổ mặc định của `--delete` khi người gọi không khai `--manifest`: cạnh trạm, không TRONG
# trạm (trong trạm thì lượt sau quét lại chính sổ của lượt trước).
THU_MUC_SO = "prune-media-log"
# Cầu dao mặc định. Con số không thiêng; điều thiêng là có một con số. Một lượt chạy theo
# lịch dọn hơn ngần này là đã có gì đó sai ở tầng trên, và dừng lại rẻ hơn xoá tiếp.
MAC_DINH_MAX_FILES = 200
MAC_DINH_MAX_BYTES = 50 * 1024 ** 3

DUOI_VIDEO = {".mp4", ".mov", ".webm"}
DUOI_AUDIO = {".mp3", ".wav"}
# Cờ thuộc tính của Windows cho junction / symlink / mount point. `is_symlink()` KHÔNG
# thấy junction, nên không dò được bằng nó.
REPARSE_POINT = 0x400

# Tên thư mục KHÔNG bao giờ đi vào: so khớp theo TỪNG THÀNH PHẦN của đường dẫn, không
# phải theo tiền tố chuỗi — `assets` nằm ở tầng thứ tư vẫn phải bị loại.
THU_MUC_CAM = {".raw", "voices", "assets", ".venv", "venv", "site-packages",
               "node_modules", "__pycache__", ".git"}

CHINH_SACH_AUDIO = ("web-first", "age", "keep")
CHINH_SACH_VIDEO = ("published", "age", "keep")
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


def _ban_web(web_repo: Path | None, kenh: str, ngay: str, anh_xa: dict,
             stem: str) -> Path | None:
    """Bản web của ĐÚNG FILE này, nếu có thật.

    So theo TÊN FILE chứ không theo thư mục: `<web>/<kênh>/audio/<ngày>/` tồn tại chỉ
    chứng minh rằng MỘT file nào đó của ngày đó đã đăng. Bản trước so theo thư mục, nên
    một `raw.wav` chưa từng đăng bị dọn vì `podcast.mp3` cùng ngày đã đăng (REVIEW-P2 N2).

    Đuôi không cần khớp: web phát `.mp3` trong khi trạm giữ `.wav` của cùng bản dựng là
    chuyện bình thường; cùng `stem` là cùng một bản. Ánh xạ tên kênh khai bằng cờ — KHÔNG
    đoán: tên trên trạm (`ai-news`) và tên trên web (`ai`) khác nhau là chuyện bình thường,
    và một cái đoán sai ở đây là một file bị dọn nhầm."""
    if not web_repo:
        return None
    d = web_repo / anh_xa.get(kenh, kenh) / "audio" / ngay
    if not d.is_dir():
        return None
    for q in sorted(d.glob(glob_escape(stem) + ".*")):
        if q.is_file() and q.suffix.lower() in DUOI_AUDIO:
            return q
    return None


def glob_escape(s: str) -> str:
    """`[`, `]`, `?`, `*` trong tên file thật (`PNTT [2441-2446].wav`) làm hỏng mẫu glob."""
    return re.sub(r"([\[\]*?])", r"[\1]", s)


def _la_lien_ket(st) -> bool:
    """Liên kết thư mục theo NGHĨA RỘNG: symlink POSIX, symlink và junction Windows.

    `Path.is_symlink()` / `DirEntry.is_symlink()` trả **False** cho junction — đó là cách
    một file ngoài trạm lọt vào kế hoạch xoá (REVIEW-P2 N1)."""
    if _stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & REPARSE_POINT)


def _duyet(goc: Path):
    """Mọi file thường dưới `goc`, KHÔNG đi xuyên liên kết thư mục, bỏ luôn thư mục cấm.

    Tự đi cây thay vì `rglob` vì `rglob` không có cách nào bảo nó đừng đi xuyên qua."""
    that = goc.resolve()
    ngan = [goc]
    while ngan:
        d = ngan.pop()
        try:
            with os.scandir(d) as it:
                muc = sorted(it, key=lambda e: e.name)
        except OSError:
            continue
        for e in muc:
            try:
                st = e.stat(follow_symlinks=False)
                if _la_lien_ket(st):
                    continue
                if _stat.S_ISDIR(st.st_mode):
                    if e.name not in THU_MUC_CAM:
                        ngan.append(Path(e.path))
                elif _stat.S_ISREG(st.st_mode):
                    p = Path(e.path)
                    # Chốt lần hai: kể cả khi một tầng nào đó lọt, đường thật vẫn phải
                    # nằm trong gốc. Rẻ, và là thứ duy nhất không phụ thuộc hệ điều hành.
                    if p.resolve().is_relative_to(that):
                        yield p
            except OSError:
                continue


def quet(gocs, days=MAC_DINH_NGAY, web_repo=None, web_channel=None,
         audio_policy="web-first", video_policy="published", evidence=None,
         now=None) -> dict:
    """Lập KẾ HOẠCH (không chạm đĩa): mỗi file media một mục `prune`/`keep` + lý do."""
    if audio_policy not in CHINH_SACH_AUDIO:
        raise SC.ContractError(f"--audio-policy phải là một trong {CHINH_SACH_AUDIO}")
    if video_policy not in CHINH_SACH_VIDEO:
        raise SC.ContractError(f"--video-policy phải là một trong {CHINH_SACH_VIDEO}")
    if days < 0:
        raise SC.ContractError("--days không âm")
    web_repo = Path(web_repo).resolve() if web_repo else None
    anh_xa = dict(web_channel or {})
    bc = evidence if isinstance(evidence, PE.BangChung) else PE.BangChung.doc(evidence)
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
        for p in sorted(_duyet(g.path)):
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
            entries.append({**muc, "evidence": None,
                            **_quyet(p, rel, st.st_mtime, han, days, muc["kind"], g.label,
                                     web_repo, anh_xa, audio_policy, video_policy, bc)})
    return {"schema": "prune-media/2", "days": days, "audio_policy": audio_policy,
            "video_policy": video_policy,
            "web_repo": web_repo.as_posix() if web_repo else None,
            "evidence_sources": bc.nguon(),
            "generated_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(
                timespec="seconds"),
            "roots": [{"label": g.label, "path": g.path.as_posix()} for g in gocs],
            "entries": entries, "totals": tong(entries)}


def _quyet(p, rel, mtime, han, days, loai, nhan, web_repo, anh_xa, chinh_sach,
           cs_video, bc) -> dict:
    """Quyết định cho MỘT file. Thứ tự các vế là cố ý: sàn tuổi trước, vì nó rẻ và vì một
    file vừa sinh ra thì dù đã đăng cũng chưa đến lượt dọn."""
    if mtime > han:
        return {"action": "keep", "reason": f"còn trong hạn {days} ngày"}
    if _dang_khoa(p):
        return {"action": "keep",
                "reason": "không mở được để ghi (có thể đang bị khoá / đang ghi) — bỏ qua"}
    if loai == "video":
        if cs_video == "keep":
            return {"action": "keep", "reason": "video quá hạn — `--video-policy keep`"}
        if cs_video == "age":
            return {"action": "prune",
                    "reason": f"video quá {days} ngày (`--video-policy age` — ngoại lệ có "
                              f"chủ đích, trạm này không có sổ đăng để đối chiếu)"}
        bang = bc.cho_video(p)
        if bang:
            return {"action": "prune", "evidence": bang,
                    "reason": f"video quá {days} ngày và ĐÃ ĐĂNG "
                              f"({bang['key']}={bang['value']} trong {bang['source']})"}
        return {"action": "keep", "reason": f"video quá hạn nhưng {bc.vi_sao_chua(p)} — giữ"}
    if chinh_sach == "keep":
        return {"action": "keep", "reason": "audio quá hạn — `--audio-policy keep`"}
    if chinh_sach == "age":
        return {"action": "prune",
                "reason": f"audio quá {days} ngày (`--audio-policy age` — ngoại lệ có chủ "
                          f"đích, kênh này không đăng web)"}
    ngay = _ngay_cua(rel, mtime)
    kenh = _kenh_cua(rel, nhan)
    q = _ban_web(web_repo, kenh, ngay, anh_xa, p.stem)
    if q:
        return {"action": "prune",
                "evidence": {"source": q.as_posix(), "kind": "web-repo",
                             "key": "file", "value": q.name},
                "reason": f"audio quá hạn, bản web đã có ở {q.as_posix()}"}
    if not web_repo:
        return {"action": "keep",
                "reason": "audio quá hạn nhưng chưa khai repo web (`--web-repo`) để đối "
                          "chiếu — giữ"}
    return {"action": "keep",
            "reason": f"audio quá hạn nhưng CHƯA thấy bản web "
                      f"{anh_xa.get(kenh, kenh)}/audio/{ngay}/{p.stem}.* — giữ"}


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


def _cau_dao(kq: dict, max_files: int, max_bytes: int) -> None:
    """Chặn TRƯỚC khi thi hành. Vượt trần là mã 2 và không chạm file nào.

    Đây là cái van cho một lượt chạy theo lịch: `WEB_REPO_DIR` rơi mất, `--web-channel`
    sai một chữ, hay một `--root` trỏ nhầm đều biểu hiện ra cùng một cách — số file dọn
    đột nhiên lớn bất thường. Dừng lại rẻ hơn xoá tiếp rồi đi đọc sổ."""
    t = kq["totals"]["prune"]
    if max_files >= 0 and t["files"] > max_files:
        raise SC.ContractError(
            f"CẦU DAO: lượt này dọn {t['files']} file, quá trần `--max-files {max_files}` — "
            f"KHÔNG chạm file nào. Xem lại kế hoạch bằng `--dry-run`; nếu đúng ý thì nâng "
            f"trần cho lượt đó (`--max-files -1` là bỏ trần, gõ ra thì chịu trách nhiệm).")
    if max_bytes >= 0 and t["bytes"] > max_bytes:
        raise SC.ContractError(
            f"CẦU DAO: lượt này dọn {_mb(t['bytes'])}, quá trần `--max-bytes {max_bytes}` "
            f"({_mb(max_bytes)}) — KHÔNG chạm file nào.")


def _cho_ke_khai(args, gocs) -> Path | None:
    """Đích ghi kê khai. `--delete` LUÔN có một cái — thiếu chỗ ghi thì không xoá.

    Mặc định đặt CẠNH gốc thứ nhất chứ không TRONG nó: trong gốc thì lượt sau quét lại
    chính sổ của lượt trước, và sổ nằm trong thứ sắp bị dọn là sổ sắp mất."""
    if args.manifest:
        return no_duong(args.manifest)
    if args.move_to:
        return no_duong(args.move_to) / TEN_MANIFEST
    if args.delete:
        ngay = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return gocs[0].path.parent / THU_MUC_SO / f"{ngay}-{gocs[0].label}-prune-media.json"
    return None


def _ghi_ke_khai(manifest: Path, kq: dict, giai_doan: str) -> None:
    try:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({**kq, "status": giai_doan}, ensure_ascii=False,
                                       indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError as e:
        raise SC.ContractError(
            f"không ghi được kê khai {manifest} ({e}) — KHÔNG dọn gì. Xoá mà không để lại "
            f"danh sách thì lỗi sau này là không điều tra được; chọn `--manifest` khác.") from e


def _lam(args) -> dict:
    if not args.root:
        raise SC.ContractError("phải có ít nhất một `--root [NHÃN=]ĐƯỜNG_DẪN`")
    if args.move_to and args.delete:
        raise SC.ContractError("`--move-to` và `--delete` loại trừ nhau — chọn một")
    if args.delete and args.days < 1 and not args.allow_days_0:
        raise SC.ContractError(
            "`--days 0` cùng `--delete` xoá cả thứ vừa render xong trong ngày. Vẫn làm được, "
            "nhưng phải gõ thêm `--allow-days-0` — một ký tự gõ nhầm trong dòng lệnh của bộ "
            "lập lịch không được đủ để mở nó.")
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
    web_repo = args.web_repo or (SP.secret_env("WEB_REPO_DIR") or "").strip() or None
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
              audio_policy=args.audio_policy, video_policy=args.video_policy,
              evidence=[no_duong(e) for e in (args.evidence or [])])

    che_do = "DỜI" if move_to else ("XOÁ" if args.delete else "chỉ in (dry-run)")
    cham_dia = bool(move_to or args.delete)
    manifest = _cho_ke_khai(args, gocs)
    loi = []
    if cham_dia:
        _cau_dao(kq, args.max_files, args.max_bytes)
        # Kê khai đi TRƯỚC byte đầu tiên. Ghi sau thì một lần bị giết giữa chừng là mất
        # cả hai: file lẫn danh sách những gì đã mất (REVIEW-P2 C1.2).
        _ghi_ke_khai(manifest, kq, "planned")
        SC.log(f"  kê khai (kế hoạch): {manifest}")
        loi = thuc_thi(kq, move_to=move_to, delete=args.delete)
        kq["totals"] = tong(kq["entries"])
    _bao_cao(kq, che_do)

    if manifest:
        _ghi_ke_khai(manifest, kq, "done" if cham_dia else "planned")
        SC.log(f"  kê khai: {manifest}")
    for x in loi:
        SC.log(f"  ĐỎ   {x}")
    if loi:
        raise SC.EngineError(f"{len(loi)} file không dời/xoá được (xem stderr)")
    return {"days": kq["days"], "totals": kq["totals"],
            "evidence_sources": len(kq["evidence_sources"]),
            "manifest": manifest.as_posix() if manifest else None}


def _parser() -> argparse.ArgumentParser:
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
                    help="web-first (mặc định): chỉ dọn audio ĐÃ CÓ ĐÚNG FILE ĐÓ trên repo "
                         "web · age: dọn theo tuổi — NGOẠI LỆ CÓ CHỦ ĐÍCH cho kênh không "
                         "đăng web (trạm truyện), phải gõ ra · keep: không bao giờ dọn audio")
    ap.add_argument("--video-policy", choices=CHINH_SACH_VIDEO, default="published",
                    help="published (mặc định): chỉ dọn video đã lên YouTube (đọc "
                         "`*.published.json` cạnh file và các sổ khai bằng --evidence) · "
                         "age: dọn theo tuổi — NGOẠI LỆ CÓ CHỦ ĐÍCH, phải gõ ra · keep: "
                         "không bao giờ dọn video")
    ap.add_argument("--evidence", action="append", metavar="FILE",
                    help="sổ đăng để đối chiếu: `truyen-state.json`, `playlist-youtube.json`. "
                         "Lặp lại được. `*.published.json` nằm cạnh media thì tự nhặt, "
                         "không cần khai")
    ap.add_argument("--manifest", metavar="FILE",
                    help=f"nơi ghi kê khai (mặc định khi dời: <move-to>/{TEN_MANIFEST}; khi "
                         f"xoá: <gốc>/../{THU_MUC_SO}/<ngày>-<nhãn>-prune-media.json)")
    ap.add_argument("--max-files", type=int, default=MAC_DINH_MAX_FILES, metavar="N",
                    help=f"cầu dao: quá ngần này file thì DỪNG, không chạm gì (mặc định "
                         f"{MAC_DINH_MAX_FILES}; -1 = bỏ trần)")
    ap.add_argument("--max-bytes", type=int, default=MAC_DINH_MAX_BYTES, metavar="B",
                    help=f"cầu dao theo dung lượng (mặc định {MAC_DINH_MAX_BYTES}; -1 = bỏ trần)")
    ap.add_argument("--allow-days-0", action="store_true",
                    help="cho phép `--days 0` khi XOÁ (dọn ngay cả thứ vừa render trong ngày)")
    ap.add_argument("--json", action="store_true")
    return ap


def _args_thu(**doi):
    """Bộ tham số mặc định + ghi đè — dùng cho test gọi thẳng `_lam()` (không qua vỏ CLI).

    Mặc định lấy từ chính `_parser()` để test không bao giờ chạy với một bộ mặc định khác
    bộ mà người dùng thật nhận được."""
    ns = _parser().parse_args([])
    for k, v in doi.items():
        setattr(ns, k, v)
    ns.prog = PROG
    return ns


def main(argv=None) -> int:
    args, ma = SC.parse(_parser(), argv)
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
