# -*- coding: utf-8 -*-
"""Phân giải đường dẫn 4 tầng: STATION → kênh → chiến dịch → bài.

KÊNH KHÔNG BẮT BUỘC NẰM TRONG STATION. Người dùng có thể để một kênh ở ổ khác, thư mục
công ty, hay đâu tuỳ ý. `CHANNELS.md` ở STATION giữ địa chỉ; đó là **cạnh duy nhất** được
phép trỏ ra ngoài cây. Vì thế mọi script tìm kênh qua `CHANNELS.md`, KHÔNG dò thư mục —
dò thư mục thì kênh ngoài STATION vô hình.

Đi lên thì tìm bằng file mốc (`channel.yml`, `campaign.md`) chứ không đếm số cấp thư mục:
đếm cấp là giả định người không bao giờ lồng thêm thư mục, mà giả định đó sai sớm muộn.

## Hai chế độ cài (F17) — và vì sao thứ tự phân giải nằm ở ĐÂY, một chỗ duy nhất

Trạm là một KHÁI NIỆM, không phải một đường dẫn cố định. Người dùng cài theo hai kiểu:

    embedded   trạm = `<repo>/workspace/`, biến cấu hình ở `<repo>/.env` — "mở một folder
               là thấy hết". MẶC ĐỊNH và là khuyến nghị cho người mới.
    separate   trạm ngoài repo (thư mục người dùng chọn, gợi ý `~/.marketing`), biến đặt
               ở cấp user, bí mật ở kho secret của máy — cho người nhiều máy, hoặc repo
               public của chính họ.

Lựa chọn ghi ở `<repo>/studio.local.json` (bị gitignore). Thứ tự phân giải trạm:

    --station → MARKETING_STUDIO_DATA → studio.local.json → <repo>/workspace/

Biến môi trường đứng TRƯỚC `studio.local.json` là có chủ đích: máy nào đã đặt biến từ
trước (máy chạy lịch thật) thì một file cấu hình lạc vào repo không được phép cướp trạm.

Không có gì khai ⇒ trạm là `<repo>/workspace/` (có thật hay chưa). KHÔNG có đường lùi về
một thư mục trong nhà người dùng: trạm ngoài repo chỉ có khi người dùng chỉ định (biến,
`--station`, hoặc chọn `separate` lúc cài). Đường lùi ngầm về `~/.marketing` từng làm một
bản clone mới "tìm thấy" trạm của bản cài khác trên cùng máy mà không ai hỏi.

Bí mật đi theo thứ tự riêng: biến môi trường → `<repo>/.env` (**chỉ** khi `mode=embedded`)
→ kho secret của máy. Luật ba tầng không đổi: biến/`.env` giữ **đường dẫn**, file ngoài git
giữ **giá trị**. Chế độ `separate` KHÔNG bao giờ tự nạp `.env` — ở đó repo có thể là repo
public của chính người dùng, và tự nạp một file lạ trong repo là mở cửa cho nó.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_io  # noqa: E402

MOC_KENH = "channel.yml"
MOC_CHIEN_DICH = "campaign.md"
SO_KENH = "CHANNELS.md"

# Hợp đồng F17 — tên file/thư mục dùng chung với `agent-voice-studio`, `agent-video-studio`.
LOCAL_CONFIG = "studio.local.json"
WORKSPACE = "workspace"
MODES = ("embedded", "separate")


class StudioPathsError(Exception):
    """Cấu hình đường dẫn hỏng: phải SỬA rồi chạy lại, chạy lại nguyên trạng thì vẫn thế."""


def repo_root() -> Path | None:
    """Gốc bản clone repo: `$MARKETING_STUDIO_HOME` → thư mục chứa chính file này.

    Trả `None` khi không xác định được (file lib bị chép đi nơi khác) — người gọi phải
    xử lý, vì đoán bừa một gốc repo là đoán bừa luôn chỗ đặt trạm.
    """
    ung = []
    bien = (os.environ.get("MARKETING_STUDIO_HOME") or "").strip()
    if bien:
        ung.append(Path(bien).expanduser())
    ung.append(Path(__file__).resolve().parents[2])
    for p in ung:
        if (p / "scripts" / "lib").is_dir() and (p / "install.ps1").is_file():
            return p.resolve()
    return None


def _doc_json(p: Path) -> dict:
    """File không có ⇒ {}. JSON hỏng ⇒ LỖI có tên file — không nuốt, vì nuốt ở đây nghĩa là
    lặng lẽ rơi về trạm mặc định và người dùng mất cả cây nội dung mà không biết vì sao."""
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise StudioPathsError(f"{p.name} hỏng ({p}): {e} — sửa tay hoặc xoá rồi chạy lại")
    if not isinstance(data, dict):
        raise StudioPathsError(f"{p.name} không phải object JSON ({p})")
    return data


def local_config(repo=None) -> dict:
    """Nội dung `<repo>/studio.local.json` (lựa chọn chế độ cài); {} nếu chưa có."""
    repo = Path(repo) if repo else repo_root()
    return _doc_json(repo / LOCAL_CONFIG) if repo else {}


def mode(repo=None) -> str | None:
    """Chế độ cài đã chọn: `embedded` · `separate` · None (chưa chạy bộ cài)."""
    m = (local_config(repo).get("mode") or "").strip()
    return m if m in MODES else None


def resolve_station(station=None) -> tuple[Path, str]:
    """-> (gốc trạm, nguồn). Nguồn ∈ `--station` · MARKETING_STUDIO_DATA · studio.local.json
    · workspace · default. Đọc lại MỖI LẦN gọi (không đóng băng lúc import).

    `default` = không ai khai gì: trạm là `<repo>/workspace/` dù thư mục chưa có (hàm này
    KHÔNG tạo nó — bộ cài tạo, `doctor` báo thiếu). Không xác định được repo mà cũng không
    có gì khai → `StudioPathsError`, không đoán một thư mục trong nhà."""
    if station:
        return Path(station).expanduser().resolve(), "--station"
    bien = (os.environ.get("MARKETING_STUDIO_DATA") or "").strip()
    if bien:
        return Path(bien).expanduser().resolve(), "MARKETING_STUDIO_DATA"
    repo = repo_root()
    if repo:
        sp = str(local_config(repo).get("station_path") or "").strip()
        if sp:
            q = Path(sp).expanduser()
            return (q if q.is_absolute() else (repo / q)).resolve(), LOCAL_CONFIG
        ws = repo / WORKSPACE
        if ws.is_dir():
            return ws.resolve(), WORKSPACE
        return ws.resolve(), "default"
    raise StudioPathsError(
        "không xác định được trạm: không có --station, biến MARKETING_STUDIO_DATA chưa đặt, "
        "và không tìm ra bản clone repo (đặt MARKETING_STUDIO_HOME) để dùng <repo>/workspace/")


def root(station=None) -> Path:
    """STATION theo thứ tự F17.3 (xem docstring module)."""
    return resolve_station(station)[0]


def workspace_dir(repo=None) -> Path | None:
    """`<repo>/workspace/` — chỗ trạm nằm ở chế độ embedded (có tồn tại hay chưa thì tuỳ)."""
    repo = Path(repo) if repo else repo_root()
    return (repo / WORKSPACE) if repo else None


# ── bí mật: biến môi trường → <repo>/.env (chỉ embedded) → kho secret của máy ──────────

def env_file(repo=None) -> Path | None:
    """`<repo>/.env` khi và CHỈ KHI chế độ là `embedded` và file có thật; không thì None."""
    repo = Path(repo) if repo else repo_root()
    if not repo or mode(repo) != "embedded":
        return None
    f = repo / ".env"
    return f if f.is_file() else None


def doc_env_file(repo=None) -> dict:
    """Đọc `<repo>/.env` thành dict. Định dạng tối giản, CỐ Ý không hỗ trợ gì thêm:
    `TEN=giá trị` mỗi dòng, bỏ qua dòng trống và dòng `#`, bỏ `export ` đầu dòng, gỡ một
    lớp nháy bao ngoài. Không nội suy `$BIEN`, không nối dòng — mỗi tính năng thêm là một
    cách nữa để một file text trở thành mã chạy được."""
    f = env_file(repo)
    if not f:
        return {}
    ra = {}
    for dong in f.read_text(encoding="utf-8", errors="replace").splitlines():
        d = dong.strip()
        if not d or d.startswith("#") or "=" not in d:
            continue
        if d.startswith("export "):
            d = d[len("export "):]
        ten, _, gia = d.partition("=")
        ten, gia = ten.strip(), gia.strip()
        if len(gia) >= 2 and gia[0] == gia[-1] and gia[0] in "\"'":
            gia = gia[1:-1]
        if ten:
            ra[ten] = gia
    return ra


def secret_env(name: str, repo=None) -> str | None:
    """Giá trị của một biến hợp đồng: `os.environ` → `<repo>/.env` (chỉ embedded) → None.

    Trả ĐƯỜNG DẪN hoặc cấu hình, không bao giờ là token: luật ba tầng của repo này nói
    biến giữ đường dẫn, file ngoài git giữ giá trị (`knowledge/toolchains/SECRETS.md`).
    """
    gia = (os.environ.get(name) or "").strip()
    if gia:
        return gia
    gia = (doc_env_file(repo).get(name) or "").strip()
    return gia or None


# ── con trỏ bí mật: biến giữ ĐƯỜNG DẪN tới file bí mật (không bao giờ giữ bí mật) ────────
#
# Tên gốc + hậu tố theo kênh/tài khoản (`YT_TOKEN_PATH__KENH_B`, `FB_CONFIG_A` — xem
# `knowledge/toolchains/SECRETS.md`). Đây là bộ tên mà `hook_env()` được phép mang từ
# `<repo>/.env` sang tiến trình con và `install_launchd.py` được phép ghi vào plist. Bộ lọc
# theo TÊN là rào: `.env` có thể chứa thứ khác, và thứ khác không được đi theo.
CON_TRO_BI_MAT = ("TG_CONFIG", "YT_CLIENT_SECRET", "YT_TOKEN_PATH", "FB_CONFIG",
                  "EMAIL_CONFIG", "CODEX_BRIDGE")
_TEN_CON_TRO = re.compile(r"^(?:" + "|".join(CON_TRO_BI_MAT) + r")(?:_[A-Z0-9_]+)?$")


def la_con_tro_bi_mat(name: str) -> bool:
    """Tên có thuộc bộ con trỏ bí mật (kể cả hậu tố theo kênh) không."""
    return bool(_TEN_CON_TRO.match(name or ""))


def la_duong_dan(gia: str) -> bool:
    """Giá trị trông như một ĐƯỜNG DẪN (tuyệt đối, `~`, hoặc ổ đĩa Windows).

    Dùng để từ chối ghi một token trần vào nơi chỉ được giữ đường dẫn (plist, môi trường
    của hook): token trần trong biến môi trường thì mọi tiến trình con đều đọc được."""
    g = (gia or "").strip()
    return g.startswith(("/", "~")) or bool(re.match(r"^[A-Za-z]:[\\/]", g))


def secret_path(name: str, repo=None) -> str:
    """Đường tới file bí mật mà biến `name` trỏ tới — cùng thứ tự với `secret_env`
    (biến môi trường → `<repo>/.env` khi embedded), `~` đã mở rộng.

    Thiếu thì NÉM `StudioPathsError` nêu đúng tên biến và hai chỗ đặt nó — không trả chuỗi
    rỗng để nơi gọi đi tiếp rồi chết bằng một `FileNotFoundError` không ai hiểu. Giá trị
    không phải đường dẫn cũng ném, và thông báo KHÔNG in giá trị (có thể là token trần)."""
    gia = secret_env(name, repo)
    if not gia:
        raise StudioPathsError(
            f"thiếu biến {name}: đặt nó (đường dẫn tới file bí mật, không phải bí mật) ở "
            f"biến môi trường, hoặc trong <repo>/.env nếu cài chế độ embedded. "
            f"Xem knowledge/toolchains/SECRETS.md")
    if not la_duong_dan(gia):
        raise StudioPathsError(
            f"{name} phải là ĐƯỜNG DẪN tới file bí mật, không phải giá trị bí mật — "
            f"xem knowledge/toolchains/SECRETS.md")
    return str(Path(gia).expanduser())


def hook_env(repo=None) -> dict:
    """Môi trường cho tiến trình con (hook đăng bài): `os.environ` + các CON TRỎ bí mật chỉ
    khai ở `<repo>/.env` (chế độ embedded).

    Biến môi trường thật luôn thắng — cùng luật với `secret_env`. Chỉ tên thuộc
    `CON_TRO_BI_MAT` (kèm hậu tố kênh) được mang sang, và chỉ khi giá trị là đường dẫn:
    `.env` không phải kênh để đẩy thứ tuỳ ý vào môi trường của một script đăng bài."""
    ra = dict(os.environ)
    for ten, gia in doc_env_file(repo).items():
        if (la_con_tro_bi_mat(ten) and not (ra.get(ten) or "").strip()
                and la_duong_dan(gia)):
            ra[ten] = str(Path(gia.strip()).expanduser())
    return ra


# ── hai trạm năng lực kia (hợp đồng ba trạm, §2.4a của kế hoạch) ───────────────────────

def _tram_ngoai(ten_moi, ten_cu, khoa, len_mot_cap=False, repo=None) -> Path | None:
    """Tên biến được truyền vào dưới dạng GIÁ TRỊ đã đọc, nhưng nơi gọi phải viết
    `os.environ.get("TÊN")` bằng chữ literal — cổng `test_docs_drift` quét theo mẫu đó để
    bắt mọi biến code đang đọc. Đọc qua một biến trung gian là biến mất khỏi cổng."""
    v = (ten_moi or "").strip()
    if v:
        return Path(v).expanduser().resolve()
    v = (ten_cu or "").strip()
    if v:
        p = Path(v).expanduser().resolve()
        return p.parent if len_mot_cap else p
    v = str(local_config(repo).get(khoa) or "").strip()
    return Path(v).expanduser().resolve() if v else None


def voice_station(repo=None) -> Path | None:
    """Trạm giọng: `VOICE_STATION` → `OMNIVOICE_DIR` (tên CŨ = thư mục ENGINE, lùi một cấp)
    → `studio.local.json: voice_station` → None (chưa cài `agent-voice-studio`)."""
    return _tram_ngoai(secret_env("VOICE_STATION", repo), secret_env("OMNIVOICE_DIR", repo),
                       "voice_station", len_mot_cap=True, repo=repo)


def video_station(repo=None) -> Path | None:
    """Trạm video: `VIDEO_STATION` → `VIDEO_ROOT` (tên cũ) → `studio.local.json: video_station`
    → None (chưa cài `agent-video-studio`)."""
    return _tram_ngoai(secret_env("VIDEO_STATION", repo), secret_env("VIDEO_ROOT", repo),
                       "video_station", repo=repo)


def _no_duong(p: str, src: Path) -> Path:
    """Mở rộng ~ và ${BIEN}; đường tương đối tính theo thư mục chứa CHANNELS.md."""
    p = os.path.expandvars(str(p)).strip()
    q = Path(p).expanduser()
    return q if q.is_absolute() else (src / q).resolve()


def channels(station=None) -> list[dict]:
    """Đọc CHANNELS.md. Mỗi mục có thêm khoá `dir` = Path đã phân giải.

    Không có CHANNELS.md -> trả [] (STATION rỗng là trạng thái hợp lệ, không phải lỗi).
    """
    src = root(station)
    so = src / SO_KENH
    if not so.is_file():
        return []
    fm, _ = md_io.read_fm(so)
    ra = []
    for c in (fm.get("channels") or []):
        c = dict(c)
        c["dir"] = _no_duong(c.get("path", ""), src)
        ra.append(c)
    return ra


def channel_dir(channel_id: str, station=None) -> Path:
    for c in channels(station):
        if c.get("id") == channel_id:
            return c["dir"]
    raise KeyError(f"không có kênh {channel_id!r} trong {root(station) / SO_KENH}. "
                   f"Kênh phải được khai ở đó, kể cả khi nằm ngoài STATION.")


def _di_len(bat_dau, moc: str) -> Path:
    p = Path(bat_dau).resolve()
    for q in [p, *p.parents]:
        if (q / moc).is_file():
            return q
    raise FileNotFoundError(f"đi lên từ {p} không thấy {moc}")


def channel_of(path) -> Path:
    """Thư mục kênh chứa `path` (tìm ngược lên tới file có channel.yml)."""
    return _di_len(path, MOC_KENH)


def campaign_of(path) -> Path:
    """Thư mục chiến dịch chứa `path`."""
    return _di_len(path, MOC_CHIEN_DICH)


def campaigns(channel_dir_: Path) -> list[Path]:
    """Mọi thư mục chiến dịch của một kênh (có campaign.md), sắp theo tên."""
    return sorted(d for d in Path(channel_dir_).iterdir()
                  if d.is_dir() and (d / MOC_CHIEN_DICH).is_file())


def posts(campaign_dir: Path) -> list[Path]:
    """Mọi thư mục bài của một chiến dịch (có meta.json)."""
    return sorted(d for d in Path(campaign_dir).iterdir()
                  if d.is_dir() and (d / "meta.json").is_file())


# Hậu tố post_id theo nền tảng × định dạng. post_id = "<content_id>-<hậu tố>".
HAU_TO = {
    ("web_blog", "blog_article"): "web",
    ("youtube", "youtube_video"): "yt",
    ("youtube", "youtube_short"): "short",
    ("facebook", "facebook_post"): "fb",
    ("facebook", "reel"): "reel",
    ("facebook", "carousel"): "car",
    ("facebook", "infographic"): "info",
}

# Neo trong content.md mà mỗi định dạng lấy text từ đó.
NEO = {
    "blog_article": "post:blog_article",
    "youtube_video": "post:youtube_desc",
    "youtube_short": "post:youtube_short",
    "facebook_post": "post:facebook_post",
    "reel": "post:reel",
    "carousel": "post:carousel",
    "infographic": "post:infographic",
}


def post_id(content_id: str, channel: str, post_format: str) -> str:
    hau = HAU_TO.get((channel, post_format))
    if not hau:
        raise KeyError(f"chưa khai hậu tố cho ({channel}, {post_format}) — thêm vào HAU_TO")
    return f"{content_id}-{hau}"
