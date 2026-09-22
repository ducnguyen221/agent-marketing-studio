# -*- coding: utf-8 -*-
"""Cài lịch chạy trên macOS: điền mẫu `templates/launchd/*.plist` rồi nạp bằng `launchctl`.

    python scripts/runners/install_launchd.py --list
    python scripts/runners/install_launchd.py --map studio.marketing.daily-news-a=tin/hang-ngay --dry-run
    python scripts/runners/install_launchd.py --only studio.marketing.daily-news-a
    python scripts/runners/install_launchd.py --uninstall --only studio.marketing.worker

## Vì sao không chép thẳng plist

Mẫu trong `templates/launchd/` là **khuôn trung tính**: mọi đường dẫn là chỗ trống
`__TÊN__`. Chép tay rồi sửa bằng mắt là cách sinh ra ba bản plist khác nhau trên ba máy,
và cái khác nhau không ai thấy cho tới lượt chạy 03:00 sáng. Script này điền một lần,
từ một nguồn: `studio_paths` — đúng nguồn mà mọi script khác trong repo đang dùng.

## Hai chỗ trống KHÔNG suy ra được: kênh và chiến dịch

`__CHANNEL__` / `__CAMPAIGN__` là nội dung của bạn, không phải cấu hình máy. Khai bằng
`--map <label>=<kênh>/<chiến dịch>`, hoặc một lần cho xong trong `<trạm>/launchd.json`:

    { "studio.marketing.daily-news-a": "tin/hang-ngay",
      "studio.marketing.worker":       "tin/hang-ngay" }

Thiếu khai cho một label được chọn ⇒ **mã 2** và nói rõ thiếu label nào. Không đoán:
đoán sai thì job chạy đúng giờ vào **nhầm chiến dịch**, và nó vẫn báo ✅.

## Hai pipeline, HAI cấu hình giọng — không gộp

Khối `EnvironmentVariables` của mẫu **không** giống nhau giữa các job, và đó là chủ đích:

    tin (daily-news-a/b, weekly-news-a/b, weekly-repo)
        `OMNIVOICE_DTYPE=float32`, KHÔNG khai `HF_DEACTIVATE_ASYNC_LOAD`
    truyện (daily-story)
        `OMNIVOICE_DTYPE=float16` + `HF_DEACTIVATE_ASYNC_LOAD=1`, trần giờ 30600 s
    worker / approve-poller
        không khai cái nào (không chạy TTS)

Lượt tin chỉ 4–12 phút trong cửa sổ 18:00–21:00 nên nó thừa thời gian để đổi tốc độ lấy
độ chính xác; lượt truyện đọc 5 h 47 nên thời gian mới là thứ khan hiếm, và fp16 trên MPS
thì `HF_DEACTIVATE_ASYNC_LOAD=1` là bắt buộc (thiếu là nổ lúc nạp model). Script này chỉ
chép nguyên khối đó từ mẫu sang plist — muốn đổi thì đổi ở `templates/launchd/`, và
`tests/test_launchd_templates.py` (bảng `GIONG`) sẽ đỏ nếu ai gộp hai bộ lại làm một.

## Mặc định không nạp ba job (F13)

`worker`, `approve-poller`, `daily-story` **không** nằm trong bộ mặc định. Ba job đó hoặc
chạy liên tục, hoặc chạy hàng giờ giữa đêm; bật chúng phải là một câu người ta gõ ra, không
phải hệ quả phụ của việc cài lịch. Muốn bật thì gọi đích danh bằng `--only`, hoặc `--all`.

## Mã thoát

0 ok · 2 thiếu khai kênh/chiến dịch hoặc tham số sai · 3 chưa có trạm / chưa có mẫu.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from xml.parsers.expat import ExpatError
from xml.sax import saxutils

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402
import voice as VOICE  # noqa: E402

PROG = "install_launchd.py"
REPO = Path(__file__).resolve().parents[2]
MAU_DIR = REPO / "templates" / "launchd"
KHAI_FILE = "launchd.json"
LAUNCH_AGENTS = Path("~/Library/LaunchAgents").expanduser()

# Ba job phải gõ tên mới bật — xem docstring (F13).
KHONG_MAC_DINH = ("studio.marketing.worker", "studio.marketing.approve-poller",
                  "studio.marketing.daily-story")

_CHO_TRONG = re.compile(r"__[A-Z_]+__")


# ── chỗ trống ────────────────────────────────────────────────────────────────

def _python_tram() -> str:
    """Python chạy các `.ps1`/`.py` của repo — cùng thứ tự với `Find-Python`."""
    bien = (SP.secret_env("MARKETING_STUDIO_PY") or "").strip()
    if bien:
        return bien
    for con in ("bin", "Scripts"):
        for ten in ("python3", "python"):
            p = REPO / ".venv" / con / ten
            if p.is_file():
                return str(p)
    return sys.executable


def _omnivoice_py(tram_giong: Path) -> str:
    """Python của venv trạm giọng. Chưa cài thì trả đường CHỜ, không nổ.

    Phân giải thật đi qua `voice.python_exe()` — chỗ DUY NHẤT trong repo biết thứ tự
    `OMNIVOICE_PY` → `station.json: venv` (đường tương đối tính từ gốc trạm) → dò
    `omnivoice/.venv`. Viết lại thứ tự đó ở đây là tự tạo một bản thứ hai sẽ lệch.

    Lý do không nổ khi thiếu: người ta cài lịch trước khi cài xong trạm giọng là chuyện
    thường. `doctor` mới là chỗ nói "thiếu gì"; ở đây chỉ cần plist có một giá trị đọc
    được, kèm một dòng nhắc để không ai tưởng nó đã sẵn sàng.
    """
    try:
        return VOICE.python_exe(tram_giong)
    except SC.StudioError:
        con = "Scripts" if os.name == "nt" else "bin"
        return str(tram_giong / "omnivoice" / ".venv" / con / "python")


def cho_trong(station=None) -> tuple[dict, list[str]]:
    """Bảng chỗ trống + danh sách cảnh báo (thứ phải đoán vì chưa khai)."""
    nhac: list[str] = []
    tram = SP.root(station)
    voice = SP.voice_station()
    video = SP.video_station()
    if voice is None:
        voice = Path.home() / ".voice"
        nhac.append(f"chưa khai VOICE_STATION — plist tạm ghi {voice} (kiểm bằng doctor)")
    if video is None:
        video = Path.home() / ".video"
        nhac.append(f"chưa khai VIDEO_STATION — plist tạm ghi {video} (kiểm bằng doctor)")
    ovpy = _omnivoice_py(voice)
    if not (ovpy and Path(ovpy).is_file()):
        nhac.append(f"OMNIVOICE_PY chưa chạy được ({ovpy or 'rỗng'}) — job có giọng sẽ đỏ")
    return {
        "__HOME__": str(Path.home()),
        "__REPO__": str(REPO),
        "__STATION__": str(tram),
        "__PY__": _python_tram(),
        "__VOICE_STATION__": str(voice),
        "__VIDEO_STATION__": str(video),
        "__OMNIVOICE_PY__": ovpy,
    }, nhac


# ── khai kênh/chiến dịch ─────────────────────────────────────────────────────

def doc_khai(station=None) -> dict:
    p = SP.root(station) / KHAI_FILE
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise SC.ContractError(f"{p} không đọc được: {e}") from e
    if not isinstance(d, dict):
        raise SC.ContractError(f"{p} phải là một object {{label: 'kênh/chiến dịch'}}")
    ra = {}
    for k, v in d.items():
        if isinstance(v, str):
            ra[k] = v
        elif isinstance(v, dict):
            ra[k] = f"{v.get('channel', '')}/{v.get('campaign', '')}"
        else:
            # Không để `AttributeError` lọt ra: `classify` xếp nó vào mã 1 = thử lại được,
            # và bộ lập lịch sẽ thử lại mãi một file khai viết sai (REVIEW-P2 Ghi nhận 18).
            raise SC.ContractError(
                f"{p}: khai {k!r} là {type(v).__name__}, chờ chuỗi `<kênh>/<chiến dịch>` "
                f"hoặc object {{channel, campaign}}")
    return ra


def _tach(gia: str, label: str) -> tuple[str, str]:
    phan = [x for x in gia.replace("\\", "/").split("/") if x]
    if len(phan) != 2:
        raise SC.ContractError(
            f"{label}: khai {gia!r} không đúng dạng `<kênh>/<chiến dịch>`")
    return phan[0], phan[1]


# ── render ───────────────────────────────────────────────────────────────────

def nhan() -> list[str]:
    if not MAU_DIR.is_dir():
        raise SC.StationMissing(f"không thấy thư mục mẫu {MAU_DIR}")
    return sorted(p.stem for p in MAU_DIR.glob("*.plist"))


def render(label: str, bang: dict) -> bytes:
    """Điền một mẫu. Còn sót chỗ trống nào là LỖI — không bao giờ ghi ra một plist dở.

    Giá trị được THOÁT XML trước khi thay. `~/Code/AI & Data Studio` là tên thư mục hợp lệ
    trên macOS, và một dấu `&` thô phá cả file: `plistlib.loads` ném `ExpatError`, thứ mà
    `SC.classify` xếp vào **mã 1 = thử lại được**. Bộ lập lịch thử lại mã 1, nên một lỗi
    cấu hình thành vòng lặp vô hạn trên thứ không bao giờ tự khỏi (REVIEW-P2 N14)."""
    f = MAU_DIR / f"{label}.plist"
    if not f.is_file():
        raise SC.StationMissing(f"không có mẫu {f}")
    t = f.read_text(encoding="utf-8")
    for k, v in bang.items():
        t = t.replace(k, saxutils.escape(str(v)))
    sot = sorted(set(_CHO_TRONG.findall(t)))
    if sot:
        raise SC.ContractError(f"{label}: còn chỗ trống chưa điền {sot}")
    b = t.encode("utf-8")
    try:
        plistlib.loads(b)      # XML hỏng thì hỏng NGAY ở đây, không phải lúc launchctl nạp
    except ExpatError as e:
        raise SC.ContractError(
            f"{label}: plist dựng ra không phải XML hợp lệ ({e}). Đây là lỗi CẤU HÌNH — "
            f"một giá trị trong bảng thay thế mang ký tự mà XML không chịu; chạy lại "
            f"nguyên trạng là vô ích. Kiểm các đường dẫn trong `studio.local.json`.") from e
    return b


# ── launchctl ────────────────────────────────────────────────────────────────

def _la_mac() -> bool:
    return sys.platform == "darwin"


def _launchctl(*doi: str) -> tuple[int, str]:
    r = subprocess.run(["launchctl", *doi], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def _muc_tieu(label: str) -> str:
    return f"gui/{os.getuid()}/{label}"                        # noqa: B009 — chỉ macOS


def nap(label: str, dich: Path) -> None:
    _launchctl("bootout", _muc_tieu(label))                    # cũ còn thì gỡ, lỗi kệ
    ma, ra = _launchctl("bootstrap", f"gui/{os.getuid()}", str(dich))
    if ma != 0:
        raise SC.EngineError(f"launchctl bootstrap {label} lỗi {ma}: {ra}")


def go(label: str, dich: Path) -> str:
    ma, ra = _launchctl("bootout", _muc_tieu(label))
    if dich.is_file():
        dich.unlink()
    return "đã gỡ" if ma == 0 else f"không nạp sẵn ({ra or ma})"


# ── việc chính ───────────────────────────────────────────────────────────────

def lam(a) -> dict:
    co = nhan()
    if a.list:
        for l in co:
            SC.log(f"  {l}{'   (phải gọi đích danh)' if l in KHONG_MAC_DINH else ''}")
        return {"labels": co}

    chon = list(a.only) if a.only else [l for l in co if a.all or l not in KHONG_MAC_DINH]
    la = [l for l in chon if l not in co]
    if la:
        raise SC.ContractError(f"không có mẫu cho: {la} (xem --list)")
    if not chon:
        raise SC.ContractError("không chọn được job nào")

    bang, nhac = cho_trong(a.station)
    for d in nhac:
        SC.log(f"[launchd] nhắc: {d}")

    khai = doc_khai(a.station)
    for x in a.map:
        if "=" not in x:
            raise SC.ContractError(f"--map phải là `<label>=<kênh>/<chiến dịch>`, nhận {x!r}")
        k, v = x.split("=", 1)
        khai[k.strip()] = v.strip()

    dich_dir = Path(a.out_dir).expanduser() if a.out_dir else LAUNCH_AGENTS
    ra = []

    if a.uninstall:
        for l in chon:
            dich = dich_dir / f"{l}.plist"
            if a.dry_run:
                SC.log(f"[launchd] (xem trước) sẽ gỡ {l} và xoá {dich}")
                ra.append({"label": l, "action": "uninstall", "dry_run": True})
                continue
            if not _la_mac():
                raise SC.ContractError("gỡ lịch chỉ chạy được trên macOS")
            SC.log(f"[launchd] {l}: {go(l, dich)}")
            ra.append({"label": l, "action": "uninstall"})
        return {"jobs": ra, "out_dir": str(dich_dir)}

    thieu = [l for l in chon if not khai.get(l)]
    if thieu:
        raise SC.ContractError(
            "chưa khai kênh/chiến dịch cho: " + ", ".join(thieu)
            + f" — dùng --map <label>=<kênh>/<chiến dịch>, hoặc khai trong "
              f"{SP.root(a.station) / KHAI_FILE}")

    for l in chon:
        kenh, cd = _tach(khai[l], l)
        noi_dung = render(l, {**bang, "__CHANNEL__": kenh, "__CAMPAIGN__": cd})
        dich = dich_dir / f"{l}.plist"
        muc = {"label": l, "channel": kenh, "campaign": cd, "plist": str(dich),
               "bytes": len(noi_dung)}
        if a.dry_run:
            SC.log(f"[launchd] (xem trước) {l} → {dich} ({len(noi_dung)} B) "
                   f"· {kenh}/{cd} · KHÔNG gọi launchctl")
            muc["dry_run"] = True
            ra.append(muc)
            continue
        dich_dir.mkdir(parents=True, exist_ok=True)
        dich.write_bytes(noi_dung)
        (SP.root(a.station) / "logs" / "launchd").mkdir(parents=True, exist_ok=True)
        if a.no_load or not _la_mac():
            SC.log(f"[launchd] {l}: đã ghi {dich} (chưa nạp — "
                   f"{'--no-load' if a.no_load else 'máy này không phải macOS'})")
            muc["loaded"] = False
        else:
            nap(l, dich)
            SC.log(f"[launchd] {l}: đã nạp · {kenh}/{cd}")
            muc["loaded"] = True
        ra.append(muc)

    SC.log(f"\nKiểm: launchctl print gui/$UID/<label> · log ở "
           f"{SP.root(a.station) / 'logs' / 'launchd'}")
    SC.log("Đổi máy (tắt/bật lịch đúng thứ tự): docs/RUNBOOK-DOI-MAY.md")
    return {"jobs": ra, "out_dir": str(dich_dir)}


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=PROG, description="Điền mẫu launchd và nạp bằng launchctl (macOS).")
    ap.add_argument("--station", help="gốc trạm (mặc định: trạm đang phân giải)")
    ap.add_argument("--only", action="append", default=[], metavar="LABEL",
                    help="chỉ job này (lặp được); gọi đích danh thì job ngoài bộ mặc "
                         "định cũng được bật")
    ap.add_argument("--all", action="store_true",
                    help="cả worker, poller và lượt truyện (mặc định: KHÔNG)")
    ap.add_argument("--map", action="append", default=[], metavar="LABEL=KÊNH/CHIẾN-DỊCH",
                    help="khai kênh/chiến dịch cho một job (lặp được)")
    ap.add_argument("--out-dir", help="thư mục ghi plist (mặc định ~/Library/LaunchAgents)")
    ap.add_argument("--uninstall", action="store_true", help="gỡ job và xoá plist")
    ap.add_argument("--no-load", action="store_true", help="ghi plist nhưng không launchctl")
    ap.add_argument("--dry-run", action="store_true",
                    help="chỉ báo sẽ làm gì: không ghi file, không gọi launchctl")
    ap.add_argument("--list", action="store_true", help="liệt kê label có mẫu rồi thoát")
    ap.add_argument("--json", action="store_true", help="in một dòng JSON kết quả")
    return ap


def main(argv=None) -> int:
    args, ma = SC.parse(_parser(), argv)
    if args is None:
        return ma
    args.prog = PROG
    return SC.run(lam, args, args.json)


if __name__ == "__main__":
    sys.exit(main())
