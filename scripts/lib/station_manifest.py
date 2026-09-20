# -*- coding: utf-8 -*-
"""Danh sách khai rõ: cái gì ĐƯỢC đi theo gói chuyển máy, cái gì ở lại.

Đây là phần khó nhất của `station.py export` và là lý do nó tách khỏi `studio.py backup`.
`backup` zip cả trạm cho chính mình; `export` là gói bàn giao, nên nó phải trả lời được
câu "gói này ĐỦ chưa" — mà muốn trả lời thì phải **khai ra** mình mang gì.

## Vì sao khai rõ (allow-list) chứ không "zip tất, trừ vài thứ"

Đo trên một trạm đang chạy: 929 MB, trong đó **906 MB nằm trong `out/`** là mp4 và ảnh —
dựng lại được. Cái KHÔNG dựng lại được chỉ vài trăm KB JSON, và mất từng cái một có hậu
quả riêng (kế hoạch §4):

    covered-repos.json   -> làm lại repo tuần đã làm
    truyen-state.json    -> đọc lại chương cũ, ĐĂNG TRÙNG
    continuity.json      -> viết trùng đề tài
    fb-state.json        -> ĐĂNG TRÙNG Facebook (chốt chống trùng duy nhất)
    *.published.json     -> chạy bù ngày cũ, UPLOAD YOUTUBE TRÙNG
    publish.json         -> mất dấu đã đăng gì, mất link

Một danh sách loại-trừ im lặng bỏ sót đúng những file đó mỗi khi cây thư mục mọc thêm
nhánh mới. Danh sách khai rõ thì chỗ bỏ sót là một test đỏ.

## Ba vùng lọc THEO TÊN FILE

`out/`, `logs/`, `truyen-out/` trộn lẫn "sản phẩm nặng dựng lại được" với "trạng thái
không dựng lại được", nên không loại cả thư mục mà lọc theo tên:

    out/         giữ `*-top.json` (đầu vào của lượt chạy) và `*.published.json` (chốt
                 chống upload trùng). Đúng bộ mà `.gitignore` của trạm giữ lại — một
                 nguồn sự thật, không phải hai.
    logs/        mặc định KHÔNG gì cả; `--include-logs-state` mở đúng bốn thứ có trạng
                 thái (`tg-approve.json`, `feedback.json`, `events.jsonl`,
                 `jobs/pending/*.json`). `jobs/running/` KHÔNG BAO GIỜ đi: đó là việc dở
                 của máy cũ, mang sang là hồi sinh một lượt chạy không còn tiến trình nào.
    truyen-out/  chỉ `_heal_state.json`; phần còn lại là cache TTS và video.

## `.git`

Mặc định KHÔNG kèm (§P0 (b), phương án C). `--with-git` thì kèm nguyên `.git/` trừ file
khoá của máy cũ. Bên nhận chạy `git update-index --refresh` vì stat cache khác hệ điều hành.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path

MANIFEST = "marketing-station-export.json"
KIND = "station-export"
FORMAT = 1

# ── loại ở MỌI cấp ────────────────────────────────────────────────────────────────────

THU_MUC_BO = ("__pycache__", ".venv", "venv", ".pytest_cache", ".uat-web", "node_modules",
              "_backup", "_task-backup", "_vtitles")
THU_MUC_BO_MAU = ("_migrated-*", ".tmp*")

# `campaign.html`/`index.html` là trang sinh ra từ nội dung; `*.lock` là khoá của tiến
# trình máy cũ; `*.bak*` là bản chép tay của một lần sửa đã xong.
FILE_BO_MAU = ("*.bak*", "*.pyc", "~$*", "*.log", "*.lock", "campaign.html", "index.html",
               ".DS_Store", "Thumbs.db")

# Bảng tính duy nhất được mang: sổ việc ở gốc trạm. `<chiến dịch>/<id>.xlsx` là bản xuất
# lại được từ `campaign.md`.
XLSX_DUOC_MANG = ("Auto Task.xlsx",)

# ── ba vùng lọc theo tên ──────────────────────────────────────────────────────────────

VUNG_OUT, VUNG_LOGS, VUNG_TRUYEN = "out", "logs", "truyen-out"
VUNG = (VUNG_OUT, VUNG_LOGS, VUNG_TRUYEN)

OUT_GIU = ("*-top.json", "*.published.json")
TRUYEN_GIU = ("_heal_state.json",)

# Trong `logs/` thì luật neo theo ĐƯỜNG tính từ `logs/`, không theo tên file. Một bộ tên
# không neo là một lỗ: `logs/jobs/running/feedback.json` trùng tên với file trạng thái
# được phép mang, và sẽ lọt vào gói mang theo cả một lượt chạy dở của máy cũ.
LOGS_GIU = ("tg-approve.json", "feedback.json", "events.jsonl")
LOGS_JOBS_GIU = "jobs/pending"      # hộp CHỜ đi theo; `jobs/running/` KHÔNG BAO GIỜ

# ── secret: không bao giờ tự động vào gói ─────────────────────────────────────────────
#
# Cùng bộ mẫu mà `studio.py backup` dùng — khai ở ĐÂY và để `studio.py` import về, vì hai
# bản sao của một danh sách secret sẽ lệch nhau, và cái lệch là cái rò.
MAU_GIONG_SECRET = ("*token*", "*secret*", "*credential*", ".env", ".env.*", "*.pem", "*.key")


def giong_secret(ten: str) -> bool:
    t = os.path.basename(str(ten)).lower()
    return t != ".env.example" and any(fnmatch.fnmatch(t, m) for m in MAU_GIONG_SECRET)


def kiem_secret(rels) -> list[str]:
    """Những đường TRONG GÓI trông giống secret.

    Chỉ xét thứ thực sự được chọn: một token nằm trong `_backup/` đã bị loại rồi, và từ
    chối vì nó là biến một thư mục rác thành cái khoá cửa vĩnh viễn.
    """
    return sorted(r for r in rels if giong_secret(r))


# ── chọn file ─────────────────────────────────────────────────────────────────────────

def _bo_thu_muc(ten: str) -> bool:
    return ten in THU_MUC_BO or any(fnmatch.fnmatch(ten, m) for m in THU_MUC_BO_MAU)


def _bo_file(ten: str) -> bool:
    return any(fnmatch.fnmatch(ten, m) for m in FILE_BO_MAU)


def _khop(ten: str, mau) -> bool:
    return any(fnmatch.fnmatch(ten, m) for m in mau)


def giu(rel: str, *, logs_state: bool = False) -> bool:
    """Một đường tương đối (dạng posix) có đi theo gói không. Không đụng đĩa."""
    phan = rel.split("/")
    ten = phan[-1]
    thu_muc = phan[:-1]
    if any(_bo_thu_muc(d) for d in thu_muc) or _bo_file(ten):
        return False
    if ten.lower().endswith(".xlsx") and rel not in XLSX_DUOC_MANG:
        return False

    vung = next((d for d in thu_muc if d in VUNG), None)
    if vung == VUNG_OUT:
        return _khop(ten, OUT_GIU)
    if vung == VUNG_TRUYEN:
        return _khop(ten, TRUYEN_GIU)
    if vung == VUNG_LOGS:
        if not logs_state:
            return False
        sau = "/".join(phan[thu_muc.index(VUNG_LOGS) + 1:])   # đường tính từ `logs/`
        return sau in LOGS_GIU or (sau.startswith(LOGS_JOBS_GIU + "/")
                                   and sau.count("/") == 2 and ten.endswith(".json"))
    return True


def chon(station, *, logs_state: bool = False, with_git: bool = False):
    """-> [(đường tuyệt đối, đường tương đối posix)] đã sắp xếp, theo đúng luật trên."""
    st = Path(station)
    ra = []
    for dp, dn, fn in os.walk(st):
        dn[:] = sorted(d for d in dn if not _bo_thu_muc(d) and d != ".git")
        for n in sorted(fn):
            f = Path(dp) / n
            rel = f.relative_to(st).as_posix()
            if giu(rel, logs_state=logs_state):
                ra.append((f, rel))
    if with_git:
        ra += _chon_git(st)
    return sorted(ra, key=lambda x: x[1])


def thu_muc_giu(station, rels) -> list[str]:
    """`<chiến dịch>/out/<ngày>/` phải CÓ MẶT trong gói dù lọc xong không còn file nào.

    Một lượt chạy hỏng để lại thư mục ngày chỉ có `clips/` — toàn media, không file trạng
    thái nào. Lọc theo tên thì thư mục ngày biến mất, và `check_tree.py` ở máy mới báo ĐỎ
    "bảng Content có out/<ngày> nhưng thư mục không tồn tại": một lỗi giả, ngay ở lần chạy
    đầu tiên trên máy mới, đúng lúc người ta chưa tin cái gì cả.

    Đây cũng chính là điều `.gitignore` của trạm đã chọn: chặn `out/**` nhưng mở lại
    `!*/*/out/*/` để giữ thư mục ngày. Gói bàn giao theo cùng một luật.
    """
    st = Path(station)
    cha = {r.rsplit("/", 1)[0] for r in rels if "/" in r}
    ra = set()
    for dp, dn, _fn in os.walk(st):
        dn[:] = [d for d in dn if not _bo_thu_muc(d) and d != ".git"]
        rel = Path(dp).relative_to(st).as_posix()
        phan = [] if rel == "." else rel.split("/")
        if len(phan) >= 2 and phan[-2] == VUNG_OUT and rel not in cha:
            ra.add(rel)
    return sorted(ra)


def _chon_git(st: Path):
    g = st / ".git"
    if not g.is_dir():
        return []
    ra = []
    for dp, dn, fn in os.walk(g):
        dn[:] = sorted(d for d in dn if d != "__pycache__")
        for n in sorted(fn):
            if _khop(n, ("*.lock", "*.pyc")):
                continue
            f = Path(dp) / n
            ra.append((f, f.relative_to(st).as_posix()))
    return ra


# ── kiểm kê file trạng thái §4 ────────────────────────────────────────────────────────
#
# (nhãn, mẫu khớp TÊN file, hậu quả nếu gói thiếu nó). Nhãn là khoá trong manifest nên
# nó là HỢP ĐỒNG: đổi nhãn là đổi manifest, và bên nhận đọc theo nhãn.

DEM_TRANG_THAI = (
    ("covered-repos.json", "covered-repos.json", "làm lại repo tuần đã làm"),
    ("truyen-state.json", "truyen-state.json", "đọc lại chương cũ -> đăng trùng"),
    ("playlist-youtube.json", "playlist-youtube.json", "backfill mất link"),
    ("continuity.json", "continuity.json", "viết trùng đề tài"),
    ("CAMPAIGNS.md", "CAMPAIGNS.md", "mất sổ chiến dịch của kênh"),
    ("campaign.md", "campaign.md", "pipeline tưởng bài chưa đăng -> đăng lại"),
    ("publish.json", "publish.json", "mất dấu đã đăng gì, mất link"),
    ("meta.json", "meta.json", "mất hồ sơ bài"),
    ("gates.json", "gates.json", "mất dấu ba cổng duyệt"),
    (".write-count.json", ".write-count.json", "mất số lần viết lại"),
    ("infographic.meta.json", "infographic.meta.json", "dựng lại ảnh Facebook"),
    ("fb-state.json", "fb-state.json", "ĐĂNG TRÙNG Facebook"),
    ("*.published.json", "*.published.json", "chạy bù ngày cũ -> upload YouTube trùng"),
    ("_heal_state.json", "_heal_state.json", "vòng tự-sửa lặp lại"),
    ("tg-approve.json", "tg-approve.json", "gửi lại tin duyệt"),
    ("Auto Task.xlsx", "Auto Task.xlsx", "mất lịch sử lượt chạy"),
)

HAU_QUA = {nhan: vi_sao for nhan, _, vi_sao in DEM_TRANG_THAI}


def kiem_ke(rels) -> dict:
    """Đếm từng loại file trạng thái §4 có trong gói -> {nhãn: số lượng}."""
    ten = [r.split("/")[-1] for r in rels]
    return {nhan: sum(1 for t in ten if fnmatch.fnmatch(t, mau))
            for nhan, mau, _ in DEM_TRANG_THAI}


def thieu(dem: dict) -> list[str]:
    """Loại nào đếm 0 -> một dòng báo kèm hậu quả.

    Đếm 0 KHÔNG phải lúc nào cũng là lỗi (trạm không có kênh truyện thì không có
    `truyen-state.json`). Nên đây là **báo**, không phải chặn: chỉ người dùng mới biết
    máy cũ của mình có loại nội dung nào.
    """
    return [f"gói không có file nào thuộc loại {nhan!r} — nếu máy cũ có, hậu quả: {HAU_QUA[nhan]}"
            for nhan, n in dem.items() if n == 0]


# ── băm ───────────────────────────────────────────────────────────────────────────────

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()
