#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`doctor` — khám một bản cài: trạm nằm đâu, rào còn sống không, thiếu gì thì cài tiếp.

Gọi từ `init_station.py` (bước cuối của bộ cài) và chạy tay bất cứ lúc nào. Nó **chỉ đọc**:
không tạo, không sửa, không xoá — một công cụ chẩn đoán mà tự sửa thì lần sau không ai
biết máy đã hỏng cái gì.

Mã thoát theo hợp đồng ba trạm (`scripts/lib/studio_contract.py`):

    0  đủ để chạy (có thể còn cảnh báo)
    2  cấu hình sai — hai nguồn sự thật, rào `.gitignore` bị thủng: phải SỬA
    3  chưa cài xong — chưa có TRẠM NỘI DUNG: phải CÀI TIẾP

Phân biệt 2 với 3 là để người đọc biết mình đang ở đâu: "làm tiếp bước còn thiếu" khác
hẳn "cái bạn đã làm đang sai".

## PHÂN TẦNG NĂNG LỰC (chỉ đạo 21/09/2026) — luật quyết định cái gì được đỏ

    LÕI            viết bài + đăng. Chạy được chỉ với trạm nội dung. Lõi hỏng ⇒ ĐỎ.
    NĂNG LỰC THÊM  giọng (`agent-voice-studio`) · video (`agent-video-studio`).
                   Thiếu ⇒ **chưa bật**, KHÔNG phải hỏng ⇒ một dòng thông tin, **mã 0**.

Cài xong repo này là viết bài và đăng được ngay; hai trạm kia chỉ cần khi người dùng thật
sự muốn lồng tiếng hoặc dựng video. Bản trước trả mã 3 khi thiếu trạm giọng, tức bảo người
vừa cài xong rằng máy họ "CHƯA CÀI XONG" vì một thứ họ chưa định dùng — và dạy họ rằng
`doctor` hay kêu oan. Một cổng bị bỏ qua thì không còn là cổng.

Lời đề nghị cài trạm nằm ở **chỗ chạm**, không ở đây: `scripts/lib/voice.py` và
`scripts/lib/video.py` ném `StationMissing` (mã 3) kèm đúng các bước cài, ngay khi một
bước thật sự cần tới chúng.

Bản này khám ba phần: **F17** (hai chế độ cài), **hai trạm năng lực** của hợp đồng ba
trạm — trạm giọng `agent-voice-studio`, trạm video `agent-video-studio` — và **thư mục
`<trạm>/engine`** (cuối file). Hai phần sau nối vào qua `KHAM_THEM`, một danh sách, để
thêm mục không phải sửa lại luồng.
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
# `agent_call` NẰM Ở `lib/`, và `pipeline/` có một file trùng tên (CLI mỏng). Nhập ở đây,
# ngay sau khi `lib/` lên đầu `sys.path`, thay vì nhập muộn trong thân hàm: nhập muộn thì
# lấy đúng thứ gì đang nằm trong `sys.modules` lúc đó, và ai nhập trước sẽ quyết hộ.
import agent_call as AC  # noqa: E402
import engine_dir as ED  # noqa: E402
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
TEN_CLOUD = ("OneDrive", "Google Drive", "My Drive", "GoogleDrive", "Dropbox",
             "iCloud Drive", "com~apple~CloudDocs", "CloudStorage", "SharePoint")
PHAI_BI_IGNORE = (SP.WORKSPACE, ".env", SP.LOCAL_CONFIG)

# Múi giờ các kênh của repo đang khai (`channel.yml: timezone`) — dùng làm ví dụ cụ thể
# trong lời nhắc thiếu dữ liệu múi giờ, để người đọc thấy đúng thứ sẽ hỏng.
MUI_GIO_CHUAN = "Asia/Ho_Chi_Minh"

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


# Ký tự được phép đứng ngay sau tên nhà cung cấp: `OneDrive - <công ty>`,
# `OneDrive-<công ty>`, `My Drive (<tài khoản>)`. Không có danh sách này thì
# `onedriver-notes` cũng thành cloud.
_SAU_TEN_CLOUD = " -_.("


def _trong_cloud(p: Path) -> str | None:
    """Tên nhà cung cấp là TIỀN TỐ của thành phần đường dẫn, không phải cả thành phần.

    So khớp tuyệt đối không bao giờ nổ ở nơi có tài khoản doanh nghiệp: thư mục thật tên
    `OneDrive - <tên công ty>`, và macOS còn đặt ở `Library/CloudStorage/OneDrive-…`. Một
    cảnh báo không bao giờ nổ là một cảnh báo không tồn tại (REVIEW-P2 N4)."""
    for x in p.parts:
        x = x.strip().lower()
        for t in TEN_CLOUD:
            ten = t.lower()
            if x == ten or (x.startswith(ten) and x[len(ten):len(ten) + 1] in _SAU_TEN_CLOUD):
                return t
    return None


_BIEN_PY = re.compile(r"""secret_env\(\s*["']([A-Z][A-Z0-9_]+)["']""")
_BIEN_PS = re.compile(r"\$env:([A-Z][A-Z0-9_]+)")


def _bien_doc_duoc(repo: Path) -> tuple[set, set]:
    """(biến Python đọc QUA `.env`, biến chỉ PowerShell đọc) — quét chính bản clone.

    Quét mã nguồn chứ không giữ một danh sách hằng: một danh sách chép tay sẽ lệch, và
    lệch ở đây nghĩa là `doctor` nói dối về chuyện biến nào có tác dụng."""
    py, ps = set(), set()
    for d, mau, kho in ((repo / "scripts", _BIEN_PY, py), (repo, _BIEN_PS, ps)):
        if not d.is_dir():
            continue
        for p in d.rglob("*.p*"):
            if p.suffix.lower() not in (".py", ".ps1") or "__pycache__" in p.parts:
                continue
            try:
                kho.update(mau.findall(p.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    return py, ps


def _kham_env_khong_ai_doc(so: So, repo: Path) -> None:
    """Biến khai trong `.env` mà KHÔNG script nào đọc được từ đó.

    Chế độ `embedded` hứa "điền `.env` là xong". Lời hứa đó chỉ đúng với biến đi qua
    `studio_paths.secret_env`; biến đọc thẳng `os.environ`, và mọi biến mà **PowerShell**
    đọc (`$env:X` — PS không có cách nào đọc `.env`), thì điền vào đó là điền vào chỗ
    không ai nhìn. Fail-closed nên không mất dữ liệu; nhưng im lặng thì người dùng mất
    buổi chiều đi tìm (REVIEW-P2 N11).

    **Chỉ tính dòng ĐÃ ĐIỀN.** Bộ cài `embedded` chép nguyên `.env.example` thành `.env`,
    nên một bản cài mới tinh đã có sẵn hàng chục dòng `TÊN=` rỗng. Kêu về chúng là chào
    người vừa clone repo bằng một cảnh báo về thứ họ chưa làm; câu cảnh báo này nói "bạn
    điền vào chỗ không ai nhìn", và chưa điền thì chưa có gì để nói."""
    khai = {k for k, v in SP.doc_env_file(repo).items() if (v or "").strip()}
    if not khai:
        return
    py, ps = _bien_doc_duoc(repo)
    cau = sorted(khai - py)
    if not cau:
        return
    chi_ps = [b for b in cau if b in ps]
    so.nhac(f"{len(cau)} biến ĐÃ ĐIỀN trong .env mà KHÔNG script Python nào đọc từ đó: "
            f"{', '.join(cau[:8])}"
            + (f" — trong đó {', '.join(chi_ps[:5])} là biến của `.ps1`, và PowerShell "
               f"không có cách nào đọc .env." if chi_ps else "")
            + " `.env` chỉ tới được script Python của repo này: không tới `.ps1`, và không "
              "tới tiến trình con của hook đăng bài. Những dòng đó phải đặt ở cấp user "
              "(setx / khối EnvironmentVariables của plist) mới có tác dụng. "
              "Xem docs/WORKSPACE.md mục `.env`.")


def _kham_du_lieu_mui_gio(so: So) -> None:
    """Máy có dữ liệu múi giờ IANA không — thứ Windows KHÔNG kèm sẵn.

    NHẮC, không THIẾU: bản cài không có `tzdata` vẫn viết bài và vẫn đăng được. Cái hỏng
    là hẹp và cụ thể — `agent_call` không đọc nổi `resets 7:50pm (Asia/Ho_Chi_Minh)`
    trong dòng lỗi hết hạn mức, nên mã 4 đi ra mà không kèm `resets_at` và lịch không
    biết phải đợi tới lúc nào. Đỏ cả bản cài vì chuyện đó là nói quá.

    Vì sao doctor phải hỏi câu này: `tzdata` đã khai trong `requirements.txt`, nhưng máy
    của Đức có sẵn gói đó do một thứ khác kéo về, nên chạy ở đây thì ngon còn CI Windows
    (máy sạch) thì đỏ. Thiếu một phụ thuộc đã khai là thứ chỉ máy sạch mới thấy — doctor
    là chỗ duy nhất trong repo biết hỏi máy đang chạy, nên nó phải hỏi.
    """
    try:
        co = AC._co_du_lieu_mui_gio()
    except Exception as e:                  # noqa: BLE001 - không kiểm được thì nói thế
        so.nhac(f"không kiểm được dữ liệu múi giờ ({e.__class__.__name__}: {e})")
        return
    if not co:
        so.nhac(AC.THIEU_TZ.format(ten=MUI_GIO_CHUAN))


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
        else:
            if os.name != "nt":
                quyen = f_env.stat().st_mode & 0o777
                if quyen & 0o077:
                    so.nhac(f".env đang mở cho người khác đọc ({oct(quyen)}) — chmod 600 {f_env}")
            _kham_env_khong_ai_doc(so, repo)

    # 4. Repo/trạm nằm trong thư mục đồng bộ đám mây
    for ten, p in (("repo", repo), ("trạm", st)):
        if p:
            c = _trong_cloud(p)
            if c:
                so.nhac(f"{ten} nằm trong thư mục đồng bộ {c} ({p}) — git ở đó hay hỏng index, "
                        "và mọi thứ trong đó đi lên cloud. Cân nhắc dời ra ngoài.")

    # 5. Thứ máy được cho là "có sẵn" mà không phải máy nào cũng có
    _kham_du_lieu_mui_gio(so)

    for them in KHAM_THEM:                  # trạm giọng, trạm video
        them(so, st)

    return {"code": so.code, "mode": che_do, "station": str(st), "source": nguon,
            "repo": str(repo) if repo else None,
            "fail": so.fail, "warn": so.warn, "info": so.info}


# ══ HAI TRẠM NĂNG LỰC — hợp đồng ba trạm (§2.4) ══════════════════════════════════════
#
# Ba mức, và lý do từng mức. **Không mức nào ở đây được gọi `so.thieu()`** — mã 3 nghĩa là
# "bản cài chưa xong", và một bản cài thiếu trạm giọng thì vẫn viết bài và đăng được:
#
#   chưa khai gì       → GHI một dòng "chưa bật — cần khi bạn muốn …". Người chỉ viết blog
#                        không cần trạm giọng; dòng này nói cho họ biết cái gì còn ở đó
#                        chờ họ, chứ không bảo họ đang thiếu.
#   đã khai, chưa đủ   → NHẮC. Biến trỏ vào một trạm dựng dở, hay một kênh khai
#                        `voice_profile` mà máy chưa có trạm giọng: nói TRƯỚC rằng bước
#                        lồng tiếng sẽ dừng ở mã 3, nhưng không làm cả bản cài đỏ theo.
#   khai sai           → ĐỎ mã 2, và CHỈ khi năng lực đã bật: profile khai trong
#                        `channel.yml` mà kho giọng có thật lại không có. Đó là mâu thuẫn
#                        trong cấu hình của chính người dùng — "sửa cái đang sai".
#
# Cổng canh chính luật này: `test_doctor_stations.py::test_KHONG_nhanh_nao_cua_phan_
# NANG_LUC_duoc_phep_bao_THIEU` (chặn `so.thieu` rồi chạy qua bảy cảnh).

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


_PHIEN_BAN = re.compile(r"\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(.*)")


def _so(v) -> tuple:
    """Phiên bản -> tuple so sánh được, LUÔN 4 phần.

    Hai bẫy đã đo (REVIEW-P2 N12):
    · `("1","0") < ("1","0","0")` là True ⇒ trạm khai `API_VERSION = "1.0"` bị đỏ mã 3 oan.
      Độ dài phải cố định, thiếu thì bù 0.
    · `1.0.0-rc1` và `1.0.0` bằng nhau nếu chỉ nhặt chữ số ⇒ bản thử nghiệm lọt cổng.
      Phần thứ tư: 0 cho bản có hậu tố `-…`, 1 cho bản chính thức."""
    m = _PHIEN_BAN.match(str(v))
    if not m:
        return (0, 0, 0, 0)
    return tuple(int(x or 0) for x in m.groups()[:3]) + (
        0 if (m.group(4) or "").strip().startswith("-") else 1,)


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


# Mỗi năng lực: (tên, việc nó làm, biến định vị, repo cài, lệnh init).
# `viec` đi thẳng vào câu "cần khi bạn muốn <viec>" — nó phải là lời người dùng nghĩ khi
# họ cần năng lực đó, không phải tên kỹ thuật của trạm.
VIEC = {"giọng": "lồng tiếng (podcast, video có giọng đọc)", "video": "dựng video"}
BIEN_TRAM = {"giọng": "VOICE_STATION", "video": "VIDEO_STATION"}


def _kham_mot_tram(so: So, ten: str, goc, can: bool, ly_do: str, repo: str,
                   huong_dan: str, lenh_init: str) -> Path | None:
    """-> gốc trạm khi nó dùng được; None khi năng lực chưa bật. Ghi sổ đúng một lần.

    KHÔNG BAO GIỜ gọi `so.thieu()`: xem khối luật ở trên.
    """
    if goc is None:
        if can:
            so.nhac(f"{ten}: chưa bật, nhưng {ly_do} — bước cần {VIEC[ten]} sẽ dừng với "
                    f"mã 3 và in đúng các bước cài. Viết bài và đăng vẫn chạy bình thường."
                    f"\n{huong_dan}")
        else:
            so.ghi(f"{ten}: chưa bật — cần khi bạn muốn {VIEC[ten]}. Viết bài và đăng "
                   f"KHÔNG cần nó. Bật: cài `{repo}` rồi đặt {BIEN_TRAM[ten]} "
                   f"(docs/ONBOARDING.md bước 8).")
        return None
    if not goc.is_dir():
        so.nhac(f"{ten}: chưa dùng được — khai ở {goc} nhưng thư mục không tồn tại."
                f"\n{huong_dan}")
        return None
    if not (goc / "station.json").is_file():
        so.nhac(f"{ten}: chưa dùng được — {goc} chưa có station.json. Chạy `{lenh_init} "
                f"--station {goc}` bằng python của trạm giọng.")
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
        so.nhac(f"giọng: chưa dùng được — kho giọng {kho} chưa có. Tạo profile bằng "
                f"`voice-studio make-profile`.")
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
    if vi_kenh:
        vi_kenh += " đang cần nó"

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
            so.nhac(f"giọng/video: chưa dùng được — {e}")
    if py is None:
        return

    ban = _hoi_phien_ban(py)
    if ban is None:
        so.nhac(f"giọng/video: chưa dùng được — không hỏi được phiên bản hợp đồng qua {py}, "
                f"python của trạm giọng chạy không nổi. Dựng lại venv rồi `pip install -e` "
                f"hai repo trạm.")
        return
    for goi in can_goi:
        dang = ban.get(goi)
        can = CAN_PHIEN_BAN[goi]
        ten = "giọng" if goi == "voice_studio" else "video"
        if not dang:
            so.nhac(f"{ten}: chưa dùng được — venv {py} chưa có `{goi}`. Chạy:\n"
                    f"  {py} -m pip install -e <đường dẫn>/agent-{goi.replace('_', '-')}")
        elif _so(dang) < _so(can):
            so.nhac(f"{ten}: chưa dùng được — `{goi}` đang là {dang}, hợp đồng cần >= {can} "
                    f"(requirements-{goi.split('_')[0]}.txt). Cập nhật repo trạm rồi "
                    f"`pip install -e` lại.")
        else:
            so.ghi(f"{goi}: {dang} (cần >= {can})")

    if giong and khai_kenh:
        _kham_profile(so, giong, khai_kenh)


KHAM_THEM.append(kham_nang_luc)


# ══ `<trạm>/engine` — hoặc không tồn tại, hoặc đủ bộ chạy ════════════════════════════
#
# Luật, sự cố đã trả giá và lý do mã 2: `scripts/lib/engine_dir.py`. Ở đây chỉ nối vào
# `doctor` để máy THẬT báo đỏ, chứ không phải chỉ bộ test biết. Một luật sống trong tests
# mà không sống trong `doctor` thì nó chỉ canh được các trạm giả.

def kham_engine(so: So, tram: Path):
    kq = ED.kiem(tram)
    for x in kq["fail"]:
        so.hong(x)
    if kq["state"] == "vang":
        so.ghi(f"engine: không có {kq['engine']} — `run.ps1` dùng đường lùi (hợp lệ)")
    elif kq["state"] == "du":
        so.ghi(f"engine: {kq['engine']} đủ bộ chạy ({', '.join(ED.RUNNER_BAT_BUOC)})")


KHAM_THEM.append(kham_engine)


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
