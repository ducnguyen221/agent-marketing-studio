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

Bản này khám hai phần: **F17** (hai chế độ cài) và **hai trạm năng lực** của hợp đồng ba
trạm — trạm giọng `agent-voice-studio`, trạm video `agent-video-studio` (cuối file).
Phần sau nối vào qua `KHAM_THEM`, một danh sách, để thêm mục không phải sửa lại luồng.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402
import video as VIDEO  # noqa: E402
import voice as VOICE  # noqa: E402

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

# Mỗi mục là `f(so, tram) -> None`; đăng ký ở cuối file. `tram` là gốc trạm nội dung đã
# phân giải — hàm khám không được tự phân giải lại, nếu không `doctor --station X` sẽ khám
# một trạm mà nó không được yêu cầu khám.
KHAM_THEM = []


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

    for them in KHAM_THEM:                  # trạm giọng, trạm video
        them(so, st)

    return {"code": so.code, "mode": che_do, "station": str(st), "source": nguon,
            "repo": str(repo) if repo else None,
            "fail": so.fail, "warn": so.warn, "info": so.info}


# ══ HAI TRẠM NĂNG LỰC — hợp đồng ba trạm (§2.4) ══════════════════════════════════════
#
# Luật phân biệt ba mức, và lý do từng mức:
#
#   chưa khai gì       → NHẮC. Người chỉ viết blog không cần trạm giọng. Bắt họ nhìn
#                        "CHƯA CÀI XONG" sau mỗi lần cài là dạy họ bỏ qua `doctor` —
#                        và một cổng bị bỏ qua thì không còn là cổng.
#   đã khai, chưa đủ   → ĐỎ mã 3. Biến trỏ vào một trạm không có `station.json`, hoặc một
#                        kênh khai `voice_profile`: người dùng ĐÃ nói mình cần. Không báo
#                        ở đây thì báo lúc 18h, giữa một lượt render.
#   khai sai           → ĐỎ mã 2. Profile khai trong `channel.yml` không có trong kho
#                        giọng: không phải "cài tiếp", mà là "sửa cái đang sai".

# Ngưỡng hợp đồng đọc từ `requirements-voice.txt` / `requirements-video.txt` (DỮ LIỆU,
# không phải hằng số trong mã).
CAN_PHIEN_BAN = dict(SC.min_version(x) for x in ("voice", "video"))

# Khoá trong `channel.yml` nói "kênh này cần trạm giọng".
KHOA_NANG_LUC = ("voice_profile", "bgm_style")

# Một lần gọi python trả về phiên bản hợp đồng của CẢ HAI package. Không dùng
# `import voice_studio, video_studio` một dòng: thiếu một cái là mất luôn thông tin về
# cái kia, và người đọc không biết mình thiếu gì.
_HOI_PHIEN_BAN = (
    "import json\n"
    "ra = {}\n"
    "for ten in ('voice_studio', 'video_studio'):\n"
    "    try:\n"
    "        ra[ten] = getattr(__import__(ten), 'API_VERSION', '')\n"
    "    except Exception as e:\n"
    "        ra[ten] = None\n"
    "print(json.dumps(ra))\n")


def _so(v) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3])


def _khai_trong_kenh(tram: Path) -> list[tuple[str, dict]]:
    """-> [(tên kênh, {khoá năng lực: giá trị})] đọc từ `channel.yml` của từng kênh.

    Lỗi đọc KHÔNG báo ở đây: `check_tree.py` là chỗ soi cây trạm, và hai công cụ cùng
    kêu về một file thì người đọc không biết sửa theo cái nào.
    """
    try:
        import yaml
    except ImportError:
        return []
    ra = []
    try:
        ds = SP.channels(tram)
    except (OSError, ValueError, SP.StudioPathsError):
        return []
    for c in ds:
        f = Path(c.get("dir") or "") / SP.MOC_KENH
        if not f.is_file():
            continue
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except (OSError, ValueError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        khai = {k: data[k] for k in KHOA_NANG_LUC if data.get(k)}
        if khai:
            ra.append((str(c.get("id") or f.parent.name), khai))
    return ra


def _hoi_phien_ban(py: str) -> dict | None:
    """-> {package: phiên bản | None}, hoặc None khi không chạy được python đó."""
    try:
        r = subprocess.run([py, "-c", _HOI_PHIEN_BAN], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    data = SC.last_json_line(r.stdout)
    return data if isinstance(data, dict) else None


def _kham_mot_tram(so: So, ten: str, goc, can: bool, ly_do: str, repo: str,
                   huong_dan: str, lenh_init: str) -> Path | None:
    """-> gốc trạm khi nó dùng được; None khi thiếu/chưa cần. Ghi sổ đúng một lần."""
    if goc is None:
        if can:
            so.thieu(f"cần trạm {ten} ({ly_do}) nhưng chưa khai chỗ nào.\n{huong_dan}")
        else:
            so.nhac(f"chưa dùng trạm {ten} — repo này chạy được mà không có nó. Khi nào cần "
                    f"{'lồng tiếng' if ten == 'giọng' else 'dựng video'} thì cài `{repo}` và "
                    f"đặt biến trạm; `doctor` sẽ kiểm tiếp từ đó.")
        return None
    if not goc.is_dir():
        so.thieu(f"trạm {ten} khai ở {goc} nhưng thư mục không tồn tại.\n{huong_dan}")
        return None
    if not (goc / "station.json").is_file():
        so.thieu(f"trạm {ten} {goc} chưa có station.json — chạy `{lenh_init} --station "
                 f"{goc}` bằng python của trạm giọng.")
        return None
    return goc


def _kham_profile(so: So, goc_giong: Path, khai_kenh):
    """Profile khai trong `channel.yml` phải có thật trong kho giọng."""
    try:
        kho = VOICE.voices_dir(goc_giong)
    except SC.StudioError as e:
        so.nhac(f"không xác định được kho giọng: {e}")
        return
    if not kho.is_dir():
        so.thieu(f"kho giọng {kho} chưa có — tạo profile bằng `voice-studio make-profile`.")
        return
    # Một profile tồn tại ⇔ có `<tên>.wav` trong kho — ĐÚNG luật mà engine giọng dùng
    # (`voice_studio.profiles.list_profiles` chỉ đếm `.wav`, `_exists` cũng chỉ hỏi `.wav`).
    # Nới ở đây (nhận cả `.txt` lẻ) là tự tạo XANH GIẢ: doctor bảo ổn, rồi `speak` trả mã 2
    # giữa lượt chạy. Cổng phải đo đúng thứ engine đo, không phải thứ trông hợp lý.
    co = {p.stem for p in kho.glob("*.wav") if not p.name.startswith("_")}
    for kenh, khai in khai_kenh:
        ten = str(khai.get("voice_profile") or "").strip()
        if ten and ten not in co:
            so.hong(f"kênh {kenh} khai voice_profile {ten!r} nhưng kho giọng {kho} không có "
                    f"{ten}.wav (đang có: {', '.join(sorted(co)) or '(rỗng)'}). Sửa "
                    f"channel.yml, hoặc tạo profile bằng `voice-studio make-profile`.")


def kham_nang_luc(so: So, tram: Path):
    """Phần trạm giọng / trạm video của `doctor`. Chỉ đọc, như cả phần còn lại."""
    if os.environ.get("OMNIVOICE_DIR") and not os.environ.get("VOICE_STATION"):
        so.nhac("OMNIVOICE_DIR là TÊN CŨ và trỏ thư mục ENGINE; đặt VOICE_STATION trỏ GỐC "
                "trạm giọng (thư mục CHA của nó) để không lệ thuộc cách dò lùi một cấp.")
    if os.environ.get("VIDEO_ROOT") and not os.environ.get("VIDEO_STATION"):
        so.nhac("VIDEO_ROOT là tên cũ — đặt VIDEO_STATION thay cho nó.")

    khai_kenh = _khai_trong_kenh(tram)
    vi_kenh = ", ".join(f"{k} khai {'/'.join(v)}" for k, v in khai_kenh)

    giong = _kham_mot_tram(
        so, "giọng", SP.voice_station(), bool(khai_kenh), vi_kenh or "đã khai biến",
        "agent-voice-studio", VOICE.HUONG_DAN, "voice-studio init")
    video = _kham_mot_tram(
        so, "video", SP.video_station(), False, "đã khai biến",
        "agent-video-studio", VIDEO.HUONG_DAN, "video-studio init")

    can_goi = [g for g, dung in (("voice_studio", giong), ("video_studio", video)) if dung]
    if not can_goi:
        return

    py = None
    for lay in ((lambda: VOICE.python_exe(giong)) if giong else None,
                (lambda: VIDEO.python_exe(video)) if video else None):
        if lay is None:
            continue
        try:
            py = lay()
            break
        except SC.StudioError as e:
            so.thieu(str(e))
    if py is None:
        return

    ban = _hoi_phien_ban(py)
    if ban is None:
        so.thieu(f"không hỏi được phiên bản hợp đồng qua {py} — python của trạm giọng chạy "
                 f"không nổi. Dựng lại venv rồi `pip install -e` hai repo trạm.")
        return
    for goi in can_goi:
        dang = ban.get(goi)
        can = CAN_PHIEN_BAN[goi]
        if not dang:
            so.thieu(f"venv {py} chưa có `{goi}` — chạy:\n"
                     f"  {py} -m pip install -e <đường dẫn>/agent-{goi.replace('_', '-')}")
        elif _so(dang) < _so(can):
            so.thieu(f"`{goi}` đang là {dang}, hợp đồng cần >= {can} "
                     f"(requirements-{goi.split('_')[0]}.txt) — cập nhật repo trạm rồi "
                     f"`pip install -e` lại.")
        else:
            so.ghi(f"{goi}: {dang} (cần >= {can})")

    if giong and khai_kenh:
        _kham_profile(so, giong, khai_kenh)


KHAM_THEM.append(kham_nang_luc)


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
