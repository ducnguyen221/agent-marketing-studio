# -*- coding: utf-8 -*-
"""Phân giải đường dẫn 4 tầng: STATION → kênh → chiến dịch → bài.

KÊNH KHÔNG BẮT BUỘC NẰM TRONG STATION. Người dùng có thể để một kênh ở ổ khác, thư mục
công ty, hay đâu tuỳ ý. `CHANNELS.md` ở STATION giữ địa chỉ; đó là **cạnh duy nhất** được
phép trỏ ra ngoài cây. Vì thế mọi script tìm kênh qua `CHANNELS.md`, KHÔNG dò thư mục —
dò thư mục thì kênh ngoài STATION vô hình.

Đi lên thì tìm bằng file mốc (`channel.yml`, `campaign.md`) chứ không đếm số cấp thư mục:
đếm cấp là giả định người không bao giờ lồng thêm thư mục, mà giả định đó sai sớm muộn.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_io  # noqa: E402

MOC_KENH = "channel.yml"
MOC_CHIEN_DICH = "campaign.md"
SO_KENH = "CHANNELS.md"


def root(station=None) -> Path:
    """STATION: --station > $MARKETING_STUDIO_DATA > ~/.marketing."""
    return Path(station or os.environ.get("MARKETING_STUDIO_DATA")
                or Path.home() / ".marketing").expanduser()


def _no_duong(p: str, goc: Path) -> Path:
    """Mở rộng ~ và ${BIEN}; đường tương đối tính theo thư mục chứa CHANNELS.md."""
    p = os.path.expandvars(str(p)).strip()
    q = Path(p).expanduser()
    return q if q.is_absolute() else (goc / q).resolve()


def channels(station=None) -> list[dict]:
    """Đọc CHANNELS.md. Mỗi mục có thêm khoá `dir` = Path đã phân giải.

    Không có CHANNELS.md -> trả [] (STATION rỗng là trạng thái hợp lệ, không phải lỗi).
    """
    goc = root(station)
    so = goc / SO_KENH
    if not so.is_file():
        return []
    fm, _ = md_io.read_fm(so)
    ra = []
    for c in (fm.get("channels") or []):
        c = dict(c)
        c["dir"] = _no_duong(c.get("path", ""), goc)
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
