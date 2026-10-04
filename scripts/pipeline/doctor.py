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
`<trạm>/engine`** (cuối file), và **skill cho ứng dụng AI** (skill gốc + adapter Claude;
việc host nạp skill là `NOT_CHECKED`). Các phần sau nối vào qua `KHAM_THEM`, một danh sách,
để thêm mục không phải sửa lại luồng.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
# Đuôi danh sách (không chen trước `lib/`): `install_launchd` (đọc launchd.json như bộ cài) và
# `truyen_paths` (dò ffmpeg như make_video) — doctor phải hỏi ĐÚNG thứ runner sẽ dùng.
sys.path.append(str(Path(__file__).resolve().parents[1] / "runners"))
sys.path.append(str(Path(__file__).resolve().parents[1] / "runners" / "story"))
# `agent_call` NẰM Ở `lib/`, và `pipeline/` có một file trùng tên (CLI mỏng). Nhập ở đây,
# ngay sau khi `lib/` lên đầu `sys.path`, thay vì nhập muộn trong thân hàm: nhập muộn thì
# lấy đúng thứ gì đang nằm trong `sys.modules` lúc đó, và ai nhập trước sẽ quyết hộ.
import agent_call as AC  # noqa: E402
import engine_dir as ED  # noqa: E402
import runner_deps as RD  # noqa: E402
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

# Windows chưa bật long path thì git/Python không mở được đường dài hơn 259 ký tự (MAX_PATH
# 260 kể cả ký tự kết thúc — cùng con số `init_station.py:GIOI_HAN_DUONG`, nhưng con số đó chỉ
# canh đường TRẠM). Đường tracked dài nhất của repo là 107 ký tự (một file trong
# `examples/example-studio/`); hằng này làm tròn lên có dư. Cổng canh nó không tụt dưới thực
# tế: `tests/test_doctor_stations.py::test_hang_duong_tracked_KHONG_ngan_hon_thuc_te`.
GIOI_HAN_DUONG_WIN = 259
DUONG_TRACKED_DAI_NHAT = 110

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
        self.not_checked: list[str] = []
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

    def chua_kiem(self, msg):
        """NOT_CHECKED — thứ doctor KHÔNG đo được từ đây. Không đỏ, không xanh: in rõ
        để không ai đọc "đủ để chạy" thành "đã kiểm hết"."""
        self.not_checked.append(msg)


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
    # Con trỏ bí mật (`YT_TOKEN_PATH`, `FB_CONFIG`… kèm hậu tố kênh) CÓ đường đi từ `.env`:
    # `studio_paths.hook_env()` mang chúng sang hook đăng bài, và `install_launchd.py` điền
    # chúng vào plist. Kêu về chúng là báo oan.
    cau = sorted(k for k in khai - py if not SP.la_con_tro_bi_mat(k))
    if not cau:
        return
    chi_ps = [b for b in cau if b in ps]
    so.nhac(f"{len(cau)} biến ĐÃ ĐIỀN trong .env mà KHÔNG script Python nào đọc từ đó: "
            f"{', '.join(cau[:8])}"
            + (f" — trong đó {', '.join(chi_ps[:5])} là biến của `.ps1`, và PowerShell "
               f"không có cách nào đọc .env." if chi_ps else "")
            + " `.env` chỉ tới được script Python của repo này (và con trỏ bí mật tới hook "
              "đăng bài): không tới `.ps1`. Những dòng đó phải đặt ở cấp user "
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


def _la_windows() -> bool:
    """Tách riêng để test giả được Windows mà không phải sửa `os.name` của cả tiến trình."""
    return os.name == "nt"


def _kham_duong_clone(so: So, repo: Path | None) -> None:
    """Bản clone nằm sâu tới mức file tracked dài nhất vượt 259 ký tự trên Windows.

    Chỉ NHẮC, không đỏ, mã thoát không đổi: `doctor` chạy được tức checkout đã xong, và máy
    có thể đã bật `core.longpaths` / LongPathsEnabled — doctor không hỏi git hay registry để
    biết. Nhắc để người dùng hiểu vì sao `git pull` sau này có thể báo "Filename too long"."""
    if not repo or not _la_windows():
        return
    dai = len(str(repo)) + 1 + DUONG_TRACKED_DAI_NHAT
    if dai > GIOI_HAN_DUONG_WIN:
        so.nhac(f"bản clone nằm sâu ({len(str(repo))} ký tự) — file tracked dài nhất sẽ thành "
                f"~{dai} ký tự, vượt {GIOI_HAN_DUONG_WIN} của Windows nếu chưa bật long path; "
                "git có thể báo 'Filename too long'. Bật `git config --global core.longpaths "
                "true`, hoặc clone vào đường ngắn hơn (xem docs/troubleshooting.md).")


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

    # 4b. Bản clone nằm quá sâu trên Windows
    _kham_duong_clone(so, repo)

    # 5. Thứ máy được cho là "có sẵn" mà không phải máy nào cũng có
    _kham_du_lieu_mui_gio(so)

    for them in KHAM_THEM:                  # trạm giọng, trạm video
        them(so, st)

    return {"code": so.code, "mode": che_do, "station": str(st), "source": nguon,
            "repo": str(repo) if repo else None,
            "fail": so.fail, "warn": so.warn, "info": so.info, "not_checked": so.not_checked}


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
                   f"KHÔNG cần nó. Bật: clone `{repo}` vào cùng thư mục cha chứa repo này "
                   f"rồi `init` nó (embedded) — tự nhận, không cần khai; trạm ở chỗ khác "
                   f"thì khai {BIEN_TRAM[ten]} trong <repo>/.env (docs/ONBOARDING.md bước 8).")
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
    # So tên ở dạng NFC CẢ HAI vế (P1-4): file nhập từ Windows sang macOS mang tên tiếng Việt
    # dạng NFD, còn `channel.yml` viết NFC — so chuỗi thô thì "Giọng tiên hiệp" ≠ "Giọng tiên
    # hiệp" và doctor đỏ GIẢ trong khi engine giọng vẫn mở được file.
    co = {unicodedata.normalize("NFC", p.stem) for p in kho.glob("*.wav")
          if not p.name.startswith("_")}
    for kenh, khai in khai_kenh:
        ten = unicodedata.normalize("NFC", str(khai.get("voice_profile") or "").strip())
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
    repo = SP.repo_root()
    if kq["state"] == "vang":
        # Trạng thái ĐÚNG từ 1.1.0: không còn `<trạm>/engine`, runner nằm trong repo.
        noi = repo / "scripts" / "runners" if repo else "`<repo>/scripts/runners`"
        so.ghi(f"engine: không có {kq['engine']} — runner chạy từ {noi} (đúng từ 1.1.0)")
    elif kq["state"] == "du":
        if repo and all((repo / "scripts" / "runners" / r).is_file() for r in ED.RUNNER_BAT_BUOC):
            so.nhac(f"engine: {kq['engine']} là BẢN CŨ — từ 1.1.0 `run.ps1` chạy runner trong "
                    f"{repo / 'scripts' / 'runners'} trước. Xoá thư mục này sau MỘT lượt xanh "
                    f"bằng bản repo (CHANGELOG 1.1.0, mục nâng cấp).")
        else:
            so.ghi(f"engine: {kq['engine']} đủ bộ chạy ({', '.join(ED.RUNNER_BAT_BUOC)})")


KHAM_THEM.append(kham_engine)


# ══ Bộ chạy tin/truyện (`scripts/runners/`) — thứ ngoài repo mà runner cần ═══════════════
#
# Chỉ kiểm khi trạm có chiến dịch dùng runner tin/truyện (`runtime.runner`): người chỉ viết
# blog không cần venv giọng hay last30days, và một dòng nhắc thường trực là dòng không ai đọc.
# Thiếu gói/last30days/nhạc nền là NHẮC, kèm đúng lệnh sửa. ĐỎ (mã 2) chỉ cho thứ CHẮC CHẮN
# giết lượt đã bật — sau hàng giờ TTS, khi không còn ai ngồi xem (01/10/2026, Mac mini, ba lỗi
# liên tiếp của lượt truyện đầu):
#   P1-19  job launchd gọi `<chiến dịch>/run.ps1` không có          → `kham_run_ps1`
#   P0-8   faster-whisper + PyAV 19: import được, `decode_audio` vỡ → kiểm HÀNH VI
#   P0-9   ffmpeg Homebrew core thiếu drawtext/subtitles/ass         → kiểm BỘ LỌC
# `doctor` không gọi `claude -p` — đăng nhập là NOT_CHECKED (P0-6). Xem `scripts/lib/runner_deps.py`.

def kham_run_ps1(so: So, tram: Path):
    """Job launchd đã khai (`<trạm>/launchd.json`) gọi file không có ⇒ ĐỎ. Chiến dịch khai
    `runtime.runner` mà thiếu `run.ps1` (điểm vào chuẩn) ⇒ NHẮC: lịch Windows có thể gọi
    thẳng runner, nhưng sang máy launchd là hỏng ngay lượt đầu."""
    repo = SP.repo_root()
    try:
        import install_launchd as IL  # noqa: E402 — nhập muộn: `scripts/runners` vào path ở đầu file
        khai = IL.doc_khai(tram)
        thieu = IL.runner_thieu(tram, khai)
    except SC.StudioError as e:
        so.hong(f"launchd.json: {e}")
        return
    for label, p in thieu:
        so.hong(f"run.ps1: job {label} sẽ gọi {p} — KHÔNG có (launchd mã 64 sau 0 s, P1-19). "
                + (f"Tạo điểm vào chuẩn: {RD.lenh_scaffold_run_ps1(repo, p.parent)}"
                   if p.name == RD.RUN_PS1 else "Sửa `runner` trong launchd.json."))
    da_bao = {p.parent.resolve() for _, p in thieu}
    for c in RD.chien_dich_co_runner(tram):
        if Path(c["dir"]).resolve() in da_bao or (c["dir"] / RD.RUN_PS1).is_file():
            continue
        so.nhac(f"run.ps1: chiến dịch {c['dir']} khai runner {c['runner']} nhưng KHÔNG có "
                f"run.ps1 — lịch launchd gọi run.ps1 sẽ hỏng. Tạo: "
                f"{RD.lenh_scaffold_run_ps1(repo, c['dir'])}")


KHAM_THEM.append(kham_run_ps1)


def _kham_truyen(so: So, py: str | None):
    """Hai thứ `make_video.py`/`read_story.py` cần mà import thành công KHÔNG chứng minh được."""
    # P0-9 — ffmpeg ĐÚNG file pipeline truyện sẽ gọi, đủ bộ lọc.
    import truyen_paths as TP  # noqa: E402 — `scripts/runners/story` vào path ở đầu file
    ff = TP.ff_exe("ffmpeg")
    thieu = RD.ffmpeg_thieu_bo_loc(ff)
    if thieu is None:
        so.hong(f"ffmpeg: không chạy được `{ff}` — truyện dựng video bằng ffmpeg. Cài: "
                f"{RD.lenh_cai_ffmpeg()}")
    elif thieu:
        so.hong(f"ffmpeg: {ff} THIẾU bộ lọc {', '.join(thieu)} — make_video.py chết ở pass 1 "
                f"SAU khi đọc xong cả lượt (P0-9). Cài: {RD.lenh_cai_ffmpeg()}")
    else:
        so.ghi(f"ffmpeg: {ff} đủ bộ lọc {', '.join(RD.BO_LOC_TRUYEN)}")
    # P0-8 — faster-whisper + PyAV: gọi đúng `decode_audio` trên wav 1 giây.
    if not py:
        return
    ok, chi_tiet = RD.kiem_decode_audio(py)
    if ok:
        so.ghi(f"faster-whisper: decode_audio chạy được ({chi_tiet})")
    elif ok is None:
        so.nhac(f"faster-whisper: không chạy được {py} để kiểm decode_audio ({chi_tiet})")
    else:
        so.hong(f"faster-whisper: decode_audio HỎNG trong {py} — {chi_tiet}. Truyện chết ở bước "
                f"căn phụ đề (P0-8: PyAV ngoài khoảng ghim). Chạy: {py} -m pip install -r "
                f"{(SP.repo_root() or Path('.')) / RD.REQ_FILE}")


def kham_runner(so: So, tram: Path):
    dung = RD.runner_dang_dung(tram)
    tin = sorted(dung & set(RD.RUNNER_TIN))
    truyen = sorted(dung & set(RD.RUNNER_TRUYEN))
    if not (tin or truyen):
        return
    so.ghi(f"runner: chiến dịch đang dùng {', '.join(tin + truyen)} (scripts/runners)")

    # P0-6 — claude CLI: có trên PATH không đo được đăng nhập; đăng nhập = NOT_CHECKED.
    cl = shutil.which("claude")
    if not cl:
        so.nhac("claude-cli: không thấy lệnh `claude` trên PATH — runner tin gọi `claude -p` để "
                "nghiên cứu; job launchd chỉ thấy PATH khai trong plist (có ~/.local/bin).")
    so.chua_kiem(f"claude-cli: đăng nhập chưa kiểm (doctor không gọi `claude -p`) — tự chạy: "
                 f"claude -p \"tra loi dung mot chu: OK\"" + (f"  [{cl}]" if cl else ""))

    # last30days — lớp cài máy cài; repo chỉ tìm.
    if tin:
        l30 = RD.tim_last30days()
        if l30:
            so.ghi(f"last30days: {l30}")
        else:
            so.nhac("last30days: không thấy script — runner tin DỪNG trước `claude -p`. Cài plugin "
                    "Claude `last30days`, hoặc đặt L30_SCRIPT (env / <repo>/.env / launchd.json vars).")

    # P0-3 — gói Python của runner trong VENV GIỌNG.
    giong = SP.voice_station()
    py = None
    if giong:
        try:
            py = VOICE.python_exe(giong)
        except SC.StudioError:
            py = None
    if not py:
        so.nhac("runner: chưa có python của trạm giọng (OMNIVOICE_PY) — không kiểm được gói của "
                f"{RD.REQ_FILE}. Xem phần trạm giọng ở trên.")
    else:
        thieu = RD.thieu_module(py)
        repo = SP.repo_root()
        req = (repo / RD.REQ_FILE) if repo else Path(RD.REQ_FILE)
        if thieu is None:
            so.nhac(f"runner: không chạy được {py} để kiểm gói — dựng lại venv giọng.")
        elif thieu:
            so.nhac(f"runner: venv giọng {py} THIẾU module {', '.join(thieu)} — bước đăng YouTube/"
                    f"đọc truyện sẽ đỏ. Chạy:\n  {py} -m pip install -r {req}")
        else:
            so.ghi(f"runner: venv giọng đủ gói ({RD.REQ_FILE})")

    if truyen:
        _kham_truyen(so, py if (py and RD.thieu_module(py, ("faster_whisper",)) == []) else None)

    # `gh` — nhánh dự phòng của bản tin tuần (YouTube không dùng được ⇒ GitHub Release). Mac mini
    # 03/10/2026 không có `gh`: nhánh chưa từng chạy, nhưng chạy là hỏng. Runner nay tự BỎ nhánh đó
    # khi thiếu lệnh (trang tuần không có video) — doctor nói trước để người cài cho đủ.
    can_gh = RD.kenh_can_gh(tram) if RD.RUNNER_TUAN in tin else []
    if can_gh:
        gh = shutil.which("gh")
        if not gh:
            so.nhac(f"gh: kênh {', '.join(can_gh)} khai `brand.gh_repo` — bản tin tuần dùng lệnh `gh` "
                    "ở nhánh dự phòng (YouTube không dùng được ⇒ đăng video lên GitHub Release), máy "
                    "này KHÔNG có. Thiếu thì runner bỏ nhánh đó: trang tuần lên KHÔNG có video. Cài: "
                    "macOS `brew install gh` rồi người dùng tự `gh auth login`; Windows "
                    "`winget install --id GitHub.cli -e`. Job launchd chỉ thấy PATH trong plist "
                    "(có /opt/homebrew/bin).")
        else:
            so.chua_kiem(f"gh: đăng nhập chưa kiểm (doctor không gọi mạng) — tự chạy: gh auth status  [{gh}]")

    # P0-4 — nhạc nền: style khai mà thiếu mp3. Chỉ NHẮC, không có lệnh sinh nhạc.
    if tin:
        nn = RD.kiem_nhac_nen(RD.thu_muc_nhac_nen())
        if not nn["co_thu_vien"]:
            so.chua_kiem(f"nhạc nền: không thấy bgm-library.json ({nn['dir'] or 'chưa có trạm video'}"
                         f" — đặt VOICE_BGM_DIR); video tin sẽ không có nhạc nền")
        elif nn["thieu_mp3"]:
            so.nhac(f"nhạc nền: {len(nn['thieu_mp3'])}/{len(nn['styles'])} style thiếu mp3 trong "
                    f"{nn['dir']}: {', '.join(nn['thieu_mp3'])} — AI sẽ không được chọn chúng; chép "
                    f"<style>.mp3 vào thư viện")
        else:
            so.ghi(f"nhạc nền: {len(nn['styles'])} style đủ mp3 ({nn['dir']})")


KHAM_THEM.append(kham_runner)


# ── Tên model agy trong `engines.json` còn nằm trong `agy models` không (P1-27) ──────────────
#
# Mac mini 03/10/2026: agy tự cập nhật (1.2.16) và bỏ `claude-opus-4-6-thinking` khỏi danh mục;
# mẫu đầu `order` trả `model_access` mọi lượt suốt hai ngày, chuỗi lùi lặng lẽ chạy bằng Gemini.
# `agy models` là 0 token (~3 s) nên doctor hỏi được. Lệch chỉ NHẮC: chuỗi lùi vẫn cứu lượt chạy,
# nhưng nó chạy bằng engine khác cái Đức chọn — đó là thứ phải thấy được.

def _muc_agy(cfg: dict) -> list[str]:
    """Mọi model agy mà trạm sẽ dùng: `order`, `engines.agy.best`, `TRUYEN_HOOK_ENGINE`."""
    ra = []
    tho = cfg.get("order") or []
    if isinstance(tho, str):
        tho = [x for x in tho.split(",") if x.strip()]
    for muc in tho:
        eng, _, mdl = str(muc).partition(":")
        if eng.strip() == "agy":
            ra.append(mdl.strip() or "best")
    hook = (SP.secret_env("TRUYEN_HOOK_ENGINE") or "").strip()
    if hook.startswith("agy:"):
        ra.append(hook.partition(":")[2].strip() or "best")
    best = str(((cfg.get("engines") or {}).get("agy") or {}).get("best") or "")
    ra = [best if m == "best" else m for m in ra]
    return [m for i, m in enumerate(ra) if m and m not in ra[:i]]


def kham_agy_model(so: So, tram: Path, models=None):
    # Trạm chưa khai `engines.json` và không chiến dịch nào chạy runner tin/truyện thì không ai gọi
    # agent — kiểm agy ở đó là dòng nhắc thường trực cho người chỉ viết blog.
    try:
        co_cau_hinh = AC.config_path(tram).is_file()
    except (OSError, SC.StudioError):
        co_cau_hinh = False
    if not co_cau_hinh and not RD.runner_dang_dung(tram):
        return
    try:
        cfg = AC.load_config(station=tram)
    except SC.StudioError as e:
        so.hong(f"agent-call: {e}")
        return
    muc = _muc_agy(cfg)
    if not muc:
        return
    if models is None:
        tho = ((cfg.get("engines") or {}).get("agy") or {}).get("cmd") or "agy"
        lenh = tho[0] if isinstance(tho, (list, tuple)) and tho else tho
        if not shutil.which(str(lenh)):
            so.nhac(f"agy: `engines.json` dùng agy ({', '.join(muc)}) nhưng không thấy lệnh `{lenh}` "
                    f"trên PATH — chuỗi sẽ lùi sang engine kế ở mọi lượt.")
            return
        models = AC.agy_models(cfg, timeout=30, cache=False)
    if not models:
        so.chua_kiem(f"agy: không hỏi được `agy models` — chưa kiểm tên model ({', '.join(muc)}).")
        return
    import difflib
    for m in muc:
        that = AC.chon_model_agy(m, models)
        if AC.la_mau_model(m):
            if that:
                so.ghi(f"agy: `{m}` → {that} (theo `agy models`)")
            else:
                so.nhac(f"agy: mẫu `{m}` không khớp model nào trong `agy models` — chuỗi lùi sang "
                        f"engine kế ở mọi lượt. Có: {', '.join(models)}.")
        elif m not in models:
            gan = difflib.get_close_matches(m, models, n=2, cutoff=0.4)
            goi_y = (f" Gần nhất: {', '.join(gan)}." if gan else "")
            so.nhac(f"agy: model `{m}` KHÔNG còn trong `agy models` (agy tự cập nhật đổi tên model) — "
                    f"mọi lượt dùng nó sẽ `model_access` rồi lùi sang engine kế.{goi_y} Sửa "
                    f"`_agent-call/engines.json`, nên dùng mẫu bền như `claude-opus-*-high` / "
                    f"`gemini-*-flash-high` (phân giải theo `agy models` lúc chạy).")
        else:
            so.ghi(f"agy: model `{m}` có trong `agy models`")


KHAM_THEM.append(kham_agy_model)


# ══ Skill cho các ứng dụng AI (host) ═══════════════════════════════════════════════════
#
# Đo được từ đây: skill gốc có mặt, adapter của Claude khớp skill gốc. KHÔNG đo được từ
# đây: host có thật sự nạp skill hay không — việc đó chỉ thấy trong một phiên MỚI của host
# mở tại thư mục repo. Nên phần đó là NOT_CHECKED, không phải xanh.
HOSTS = ("claude", "codex", "antigravity")


def kham_host(so: So, tram: Path):
    repo = SP.repo_root()
    goc = (repo / ".agents" / "skills") if repo else None
    if not goc or not goc.is_dir():
        so.nhac("không thấy .agents/skills trong bản clone — ứng dụng AI sẽ không có skill nào")
        return
    ten = sorted(p.parent.name for p in goc.glob("*/SKILL.md"))
    so.ghi(f"skill: {len(ten)} skill gốc ở .agents/skills ({', '.join(ten)})")
    sinh = repo / "scripts" / "build_host_adapters.py"
    if sinh.is_file():
        try:
            r = subprocess.run([sys.executable, str(sinh), "--check"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            so.chua_kiem(f"adapter Claude: không chạy được bộ kiểm ({e.__class__.__name__})")
        else:
            if r.returncode == 0:
                so.ghi("adapter Claude: .claude/skills khớp skill gốc")
            else:
                so.nhac("adapter Claude lệch skill gốc — chạy `python scripts/build_host_adapters.py`"
                        " rồi xem diff: " + " · ".join((r.stdout or r.stderr).split("\n")[:3]))
    for h in HOSTS:
        so.chua_kiem(f"host {h}: chưa kiểm việc nạp skill — mở phiên MỚI của {h} tại thư mục "
                     f"repo và hỏi danh sách skill; doctor không mở ứng dụng AI")


KHAM_THEM.append(kham_host)


# ══ Bài mẫu offline (`samples/`) ═══════════════════════════════════════════════════════
#
# Chấm lại `samples/bai-mau` bằng đúng 24 cổng của `blog_gates.py` — TRONG BỘ NHỚ, không
# ghi `gates.json` (doctor chỉ đọc) — rồi so từng trạng thái với `samples/gates-expected.json`.
# Không mạng, không token, không trạm giọng/video: đây là phép thử đầu tiên của một máy vừa
# cài, chạy được ở mọi nơi.
#
#   PASS         khớp từng cổng           → một dòng thông tin
#   WARN         lệch ít nhất một cổng    → cảnh báo (bài mẫu bị sửa, hoặc cổng đổi luật mà
#                                            chưa cập nhật kỳ vọng); KHÔNG đỏ — bài mẫu là
#                                            phép thử, không phải điều kiện để chạy
#   NOT_CHECKED  bản cài không kèm samples/ → nói rõ là chưa kiểm, không giả xanh
BAI_MAU = "samples"
KY_VONG = "gates-expected.json"


def _trang_thai_cong(r: dict) -> str:
    return r["status"] if r["status"] != "fail" else f"fail_{r['level']}"


def kiem_bai_mau(repo) -> tuple[str, str]:
    """-> (mức, chi tiết). Mức ∈ `pass` · `warn` · `not_checked`. Không ném lỗi."""
    goc = Path(repo) / BAI_MAU if repo else None
    f = goc / KY_VONG if goc else None
    if not f or not f.is_file():
        return "not_checked", f"không có {BAI_MAU}/{KY_VONG} (bản cài không kèm bài mẫu)"
    try:
        kv = json.loads(f.read_text(encoding="utf-8"))
        bai = goc / str(kv["post"])
        if not bai.is_dir():
            return "warn", f"thiếu thư mục bài mẫu {bai}"
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import blog_gates as BG  # noqa: E402 — nhập muộn: chỉ cần khi có bài mẫu
        kq = BG.run_cmd(bai, str(kv["home_domain"]), stage=str(kv.get("stage") or "write"))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return "warn", f"không chấm được bài mẫu ({e.__class__.__name__}: {e})"
    thay = {r["id"]: _trang_thai_cong(r) for r in kq["gates"]}
    cho = dict(kv.get("gates") or {})
    lech = sorted(k for k in set(thay) | set(cho) if thay.get(k) != cho.get(k))
    chi_tiet = [f"{x} {thay.get(x)}≠{cho.get(x)}" for x in lech[:6]]
    if kq["verdict"] != kv.get("verdict"):
        chi_tiet.insert(0, f"verdict {kq['verdict']}≠{kv.get('verdict')}")
    if chi_tiet:
        return "warn", "lệch kỳ vọng ở " + ", ".join(chi_tiet)
    return "pass", (f"{len(thay)} cổng khớp {BAI_MAU}/{KY_VONG} "
                    f"(verdict {kq['verdict']}, chấm offline)")


def kham_bai_mau(so: So, tram: Path):
    muc, chi_tiet = kiem_bai_mau(SP.repo_root())
    if muc == "pass":
        so.ghi(f"samples: PASS — {chi_tiet}")
    elif muc == "warn":
        so.nhac(f"samples: WARN — {chi_tiet}. Xem `git status samples/` và samples/README.md")
    else:
        so.chua_kiem(f"samples: {chi_tiet}")


KHAM_THEM.append(kham_bai_mau)


def _in(kq: dict):
    for x in kq["info"]:
        SC.log("  " + x)
    for x in kq["fail"]:
        SC.log(f"  ĐỎ   {x}")
    for x in kq["warn"]:
        SC.log(f"  nhắc {x}")
    for x in kq.get("not_checked", []):
        SC.log(f"  NOT_CHECKED {x}")
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
