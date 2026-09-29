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
      "studio.marketing.daily-story":  { "channel": "truyen", "campaign": "hang-ngay",
                                         "runner": "run-daily-truyen-p2.ps1",
                                         "env": ["YT_TOKEN_PATH__TRUYEN"],
                                         "schedule": { "Hour": 0, "Minute": 30 } } }

Dạng chuỗi `<kênh>/<chiến dịch>` là dạng rút gọn của object. Khoá của object:

    channel, campaign   bắt buộc
    runner              tên file `.ps1` trong thư mục chiến dịch mà job gọi; mặc định
                        `run.ps1`. Chỉ là TÊN FILE (không `/`, không `..`) — job không được
                        chạy thứ gì nằm ngoài thư mục chiến dịch của nó.
    env                 tên biến CON TRỎ bí mật thêm cho job này (hậu tố theo kênh/tài
                        khoản, vd `YT_TOKEN_PATH__TRUYEN`). Chỉ nhận tên thuộc bộ con trỏ
                        (`studio_paths.CON_TRO_BI_MAT`); giá trị lấy như mọi con trỏ khác, và
                        thiếu giá trị là mã 2 — bạn đã khai nó, nên thiếu là cấu hình sai.
    schedule            thay lịch của mẫu: một object (hoặc danh sách object) khoá
                        `Minute`/`Hour`/`Day`/`Weekday`/`Month`. Bỏ trống = lịch đã chốt
                        trong mẫu. Job không có lịch (worker, poller) mà khai thì mã 2.

Thiếu khai cho một label được chọn ⇒ **mã 2** và nói rõ thiếu label nào. Không đoán:
đoán sai thì job chạy đúng giờ vào **nhầm chiến dịch**, và nó vẫn báo ✅.

## Con trỏ bí mật: TÊN ở mẫu, GIÁ TRỊ từ máy

Mẫu khai tên biến (`<key>YT_TOKEN_PATH</key><string>__ENV_YT_TOKEN_PATH__</string>`). Bộ cài
điền giá trị theo đúng thứ tự của `studio_paths.secret_env`: biến môi trường → `<repo>/.env`
(chế độ embedded). launchd không đọc `.env` và không đọc `~/.zshrc`, nên đây là chỗ DUY
NHẤT giá trị đi vào môi trường của job. Ba luật:

    · giá trị phải là ĐƯỜNG DẪN (trừ `TG_CHAT`, là tên chat) — token trần thì mã 2, và
      thông báo không in giá trị;
    · chưa khai ở đâu thì BỎ cả dòng khỏi plist (không ghi chuỗi rỗng) và in TÊN ra;
    · log và JSON kết quả chỉ mang TÊN biến, không bao giờ mang giá trị.

Plist ghi ra có quyền 600: nó chứa đường tới file bí mật của bạn.

## Chế độ embedded

Không có biến trạm nào ⇒ trạm là `<repo>/workspace/` (thứ tự phân giải ở
`studio_paths.resolve_station`), và `<trạm>/launchd.json` nằm trong đó.

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

# Khai theo label trong `<trạm>/launchd.json` — xem docstring.
KHOA_KHAI = ("channel", "campaign", "runner", "env", "schedule")
RUNNER_MAC_DINH = "run.ps1"
_TEN_RUNNER = re.compile(r"^[A-Za-z0-9][\w.-]*\.ps1$")
KHOA_LICH = {"Minute": (0, 59), "Hour": (0, 23), "Day": (1, 31), "Weekday": (0, 7),
             "Month": (1, 12)}

# Dòng con trỏ bí mật trong mẫu: `<key>TÊN</key><string>__ENV_TÊN__</string>`.
_DONG_BI_MAT = re.compile(r"^[ \t]*<key>([A-Z][A-Z0-9_]*)</key><string>__ENV_\1__</string>[ \t]*\r?\n",
                          re.M)
_CHO_THEM = re.compile(r"^[ \t]*<!-- __ENV_EXTRA__ -->[ \t]*\r?\n", re.M)
# Tên duy nhất trong bộ con trỏ mà giá trị KHÔNG phải đường dẫn (tên chat trong file cấu
# hình Telegram — `telegram_io.py`).
KHONG_PHAI_DUONG_DAN = ("TG_CHAT",)


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
    """`<trạm>/launchd.json` -> {label: {channel, campaign[, runner, env, schedule]}}."""
    p = SP.root(station) / KHAI_FILE
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise SC.ContractError(f"{p} không đọc được: {e}") from e
    if not isinstance(d, dict):
        raise SC.ContractError(f"{p} phải là một object {{label: 'kênh/chiến dịch'}}")
    return {k: muc_khai(k, v, nguon=str(p)) for k, v in d.items()}


def muc_khai(label: str, v, nguon: str = "--map") -> dict:
    """Một mục khai -> dict đã kiểm. MỌI lỗi hình dạng là `ContractError` (mã 2).

    Không để `AttributeError`/`TypeError` lọt ra: `classify` xếp nó vào mã 1 = thử lại được,
    và bộ lập lịch sẽ thử lại mãi một file khai viết sai (REVIEW-P2 Ghi nhận 18)."""
    if isinstance(v, str):
        kenh, cd = _tach(v, label)
        return {"channel": kenh, "campaign": cd}
    if not isinstance(v, dict):
        raise SC.ContractError(
            f"{nguon}: khai {label!r} là {type(v).__name__}, chờ chuỗi `<kênh>/<chiến dịch>` "
            f"hoặc object {{channel, campaign, runner, env, schedule}}")
    la = sorted(set(v) - set(KHOA_KHAI))
    if la:
        raise SC.ContractError(f"{nguon}: {label} có khoá lạ {la} (nhận: {list(KHOA_KHAI)})")
    kenh, cd = _tach(f"{v.get('channel') or ''}/{v.get('campaign') or ''}", label)
    muc = {"channel": kenh, "campaign": cd}
    if "runner" in v:
        r = v["runner"]
        if not (isinstance(r, str) and _TEN_RUNNER.match(r) and ".." not in r):
            raise SC.ContractError(
                f"{nguon}: {label}.runner = {r!r} — phải là TÊN FILE `.ps1` trong thư mục "
                f"chiến dịch (không `/`, không `..`), vd `run.ps1`")
        muc["runner"] = r
    if "env" in v:
        ds = v["env"]
        if not (isinstance(ds, list) and all(isinstance(x, str) for x in ds)):
            raise SC.ContractError(f"{nguon}: {label}.env phải là danh sách TÊN biến")
        sai = [x for x in ds if not SP.la_con_tro_bi_mat(x)]
        if sai:
            raise SC.ContractError(
                f"{nguon}: {label}.env chỉ nhận tên con trỏ bí mật "
                f"({', '.join(SP.CON_TRO_BI_MAT)} + hậu tố kênh), không nhận {sai}")
        muc["env"] = list(dict.fromkeys(ds))
    if "schedule" in v:
        muc["schedule"] = _lich(label, v["schedule"], nguon)
    return muc


def _lich(label: str, v, nguon: str):
    ds = v if isinstance(v, list) else [v]
    if not ds or not all(isinstance(x, dict) and x for x in ds):
        raise SC.ContractError(
            f"{nguon}: {label}.schedule phải là object (hoặc danh sách object) khoá "
            f"{list(KHOA_LICH)}")
    for x in ds:
        for k, so in x.items():
            if k not in KHOA_LICH:
                raise SC.ContractError(f"{nguon}: {label}.schedule có khoá lạ {k!r}")
            lo, hi = KHOA_LICH[k]
            if not (isinstance(so, int) and not isinstance(so, bool) and lo <= so <= hi):
                raise SC.ContractError(
                    f"{nguon}: {label}.schedule.{k} = {so!r} — phải là số nguyên {lo}–{hi}")
    return v if isinstance(v, list) else dict(v)


def _tach(gia: str, label: str) -> tuple[str, str]:
    phan = [x for x in gia.replace("\\", "/").split("/") if x]
    if len(phan) != 2 or any(x in (".", "..") for x in phan):
        raise SC.ContractError(
            f"{label}: khai {gia!r} không đúng dạng `<kênh>/<chiến dịch>`")
    return phan[0], phan[1]


# ── con trỏ bí mật ───────────────────────────────────────────────────────────

def ten_bi_mat(label: str) -> list[str]:
    """Tên con trỏ bí mật mà MẪU của label khai (theo thứ tự trong file)."""
    f = MAU_DIR / f"{label}.plist"
    return _DONG_BI_MAT.findall(f.read_text(encoding="utf-8")) if f.is_file() else []


def gia_bi_mat(ten: list[str], repo=None) -> tuple[dict, list[str]]:
    """-> ({tên: giá trị đã mở rộng ~}, [tên chưa khai ở đâu]).

    Cùng thứ tự với mọi chỗ khác trong repo (`studio_paths.secret_env`): biến môi trường →
    `<repo>/.env` khi embedded. Giá trị KHÔNG phải đường dẫn là mã 2, và thông báo không
    in giá trị — một giá trị sai chỗ có thể chính là bí mật, và nó không được đi
    tiếp vào log."""
    co, thieu = {}, []
    for n in ten:
        g = SP.secret_env(n, repo)
        if not g:
            thieu.append(n)
            continue
        if n in KHONG_PHAI_DUONG_DAN:
            co[n] = g
            continue
        if not SP.la_duong_dan(g):
            raise SC.ContractError(
                f"{n} phải là ĐƯỜNG DẪN tới file bí mật (tuyệt đối hoặc bắt đầu bằng ~), "
                f"không phải giá trị bí mật — sửa ở biến môi trường hoặc <repo>/.env. "
                f"Xem knowledge/toolchains/SECRETS.md")
        co[n] = str(Path(g).expanduser())
    return co, thieu


# ── render ───────────────────────────────────────────────────────────────────

def nhan() -> list[str]:
    if not MAU_DIR.is_dir():
        raise SC.StationMissing(f"không thấy thư mục mẫu {MAU_DIR}")
    return sorted(p.stem for p in MAU_DIR.glob("*.plist"))


def render(label: str, bang: dict, bi_mat: dict | None = None,
           them: list[str] | None = None, lich=None) -> bytes:
    """Điền một mẫu. Còn sót chỗ trống nào là LỖI — không bao giờ ghi ra một plist dở.

    Giá trị được THOÁT XML trước khi thay. `~/Code/AI & Data Studio` là tên thư mục hợp lệ
    trên macOS, và một dấu `&` thô phá cả file: `plistlib.loads` ném `ExpatError`, thứ mà
    `SC.classify` xếp vào **mã 1 = thử lại được**. Bộ lập lịch thử lại mã 1, nên một lỗi
    cấu hình thành vòng lặp vô hạn trên thứ không bao giờ tự khỏi (REVIEW-P2 N14).

    Thay MỘT LƯỢT bằng regex (không `replace` lần lượt từng khoá): giá trị vừa điền không
    bao giờ bị quét lại, nên một đường dẫn tình cờ chứa `__HOME__` không bị thay lần hai.

    `bi_mat` = {tên: giá trị} của con trỏ bí mật. Dòng `__ENV_<TÊN>__` của mẫu mà tên KHÔNG
    có trong `bi_mat` thì bị BỎ cả dòng — không ghi chuỗi rỗng: script đọc `os.environ[...]`
    gặp chuỗi rỗng sẽ chết bằng một lỗi khó hiểu, gặp biến vắng thì nêu đúng tên biến.
    `them` = tên con trỏ thêm của job (khoá `env` của launchd.json), chèn ở `__ENV_EXTRA__`.
    `lich` = lịch thay cho `StartCalendarInterval` của mẫu (khoá `schedule`)."""
    f = MAU_DIR / f"{label}.plist"
    if not f.is_file():
        raise SC.StationMissing(f"không có mẫu {f}")
    bi_mat = dict(bi_mat or {})
    t = f.read_text(encoding="utf-8")
    t = _DONG_BI_MAT.sub(lambda m: m.group(0) if m.group(1) in bi_mat else "", t)
    bang = {**bang, **{f"__ENV_{n}__": v for n, v in bi_mat.items()}}
    sot: set[str] = set()

    def _thay(m):
        k = m.group(0)
        if k in bang:
            return saxutils.escape(str(bang[k]))
        if k != "__ENV_EXTRA__":
            sot.add(k)
        return k

    t = _CHO_TRONG.sub(_thay, t)
    if them and not _CHO_THEM.search(t):
        raise SC.ContractError(f"{label}: mẫu không có chỗ `__ENV_EXTRA__` cho khoá env")
    sot = sorted(sot)
    if sot:
        raise SC.ContractError(f"{label}: còn chỗ trống chưa điền {sot}")
    dong_them = []
    for n in them or []:
        if not SP.la_con_tro_bi_mat(n) or n not in bi_mat:
            raise SC.ContractError(f"{label}: con trỏ thêm {n} chưa có giá trị")
        dong_them.append(f"    <key>{n}</key><string>{saxutils.escape(str(bi_mat[n]))}"
                         f"</string>\n")
    t = _CHO_THEM.sub(lambda m: "".join(dong_them), t)
    b = t.encode("utf-8")
    try:
        plistlib.loads(b)      # XML hỏng thì hỏng NGAY ở đây, không phải lúc launchctl nạp
    except ExpatError as e:
        raise SC.ContractError(
            f"{label}: plist dựng ra không phải XML hợp lệ ({e}). Đây là lỗi CẤU HÌNH — "
            f"một giá trị trong bảng thay thế mang ký tự mà XML không chịu; chạy lại "
            f"nguyên trạng là vô ích. Kiểm các đường dẫn trong `studio.local.json`.") from e
    if lich is not None:
        d = plistlib.loads(b)
        if "StartCalendarInterval" not in d:
            raise SC.ContractError(
                f"{label}: job này không chạy theo lịch (KeepAlive) — khoá schedule không áp "
                f"được, bỏ nó khỏi launchd.json")
        d["StartCalendarInterval"] = lich
        # Dựng lại từ dict thì mất chú thích của mẫu; chỉ xảy ra khi người dùng tự đổi lịch.
        b = plistlib.dumps(d)
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

    tram, nguon_tram = SP.resolve_station(a.station)
    SC.log(f"[launchd] trạm: {tram} (nguồn: {nguon_tram})")
    bang, nhac = cho_trong(a.station)
    for d in nhac:
        SC.log(f"[launchd] nhắc: {d}")

    khai = doc_khai(a.station)
    for x in a.map:
        if "=" not in x:
            raise SC.ContractError(f"--map phải là `<label>=<kênh>/<chiến dịch>`, nhận {x!r}")
        k, v = x.split("=", 1)
        k = k.strip()
        # --map chỉ đổi kênh/chiến dịch; runner/env/schedule khai ở launchd.json vẫn giữ.
        khai[k] = {**khai.get(k, {}), **muc_khai(k, v.strip())}

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
              f"{tram / KHAI_FILE} (định dạng: docs/launchd.md)")

    for l in chon:
        k = khai[l]
        kenh, cd = k["channel"], k["campaign"]
        co_runner = "__RUNNER__" in (MAU_DIR / f"{l}.plist").read_text(encoding="utf-8")
        runner = k.get("runner") or RUNNER_MAC_DINH
        if k.get("runner") and not co_runner:
            SC.log(f"[launchd] nhắc: {l} chạy runner của repo — khoá runner bị bỏ qua")
        them = k.get("env") or []
        bi_mat, chua_khai = gia_bi_mat(ten_bi_mat(l) + them)
        thieu_them = [n for n in them if n in chua_khai]
        if thieu_them:
            raise SC.ContractError(
                f"{l}: launchd.json khai env {thieu_them} nhưng biến chưa có giá trị ở biến "
                f"môi trường hay <repo>/.env — đặt nó (ĐƯỜNG DẪN tới file bí mật) rồi chạy lại")
        if chua_khai:
            SC.log(f"[launchd] nhắc: {l} chưa có {', '.join(chua_khai)} — bỏ dòng đó khỏi "
                   f"plist; bước nào cần sẽ dừng và nêu tên biến")
        noi_dung = render(l, {**bang, "__CHANNEL__": kenh, "__CAMPAIGN__": cd,
                              "__RUNNER__": runner},
                          bi_mat=bi_mat, them=them, lich=k.get("schedule"))
        dich = dich_dir / f"{l}.plist"
        # Chỉ TÊN biến đi vào log/JSON — không bao giờ giá trị.
        muc = {"label": l, "channel": kenh, "campaign": cd, "plist": str(dich),
               "bytes": len(noi_dung), "secret_env": sorted(bi_mat),
               "secret_env_missing": sorted(chua_khai)}
        if co_runner:
            muc["runner"] = runner
        if k.get("schedule") is not None:
            muc["schedule"] = k["schedule"]
        if a.dry_run:
            SC.log(f"[launchd] (xem trước) {l} → {dich} ({len(noi_dung)} B) "
                   f"· {kenh}/{cd}{'/' + runner if co_runner else ''} "
                   f"· con trỏ bí mật: {', '.join(sorted(bi_mat)) or '(không)'} "
                   f"· KHÔNG gọi launchctl")
            muc["dry_run"] = True
            ra.append(muc)
            continue
        dich_dir.mkdir(parents=True, exist_ok=True)
        dich.write_bytes(noi_dung)
        if os.name != "nt":
            os.chmod(dich, 0o600)      # chứa đường tới file bí mật: chỉ chủ máy đọc
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
