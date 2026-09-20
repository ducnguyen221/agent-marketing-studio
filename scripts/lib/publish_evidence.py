# -*- coding: utf-8 -*-
"""Bằng chứng ĐÃ ĐĂNG — sổ của đường ống, đọc để biết một file còn cần giữ hay không.

Luật kho (Đức chốt 2026-09-20) không còn là "quá 14 ngày thì xoá". Tuổi file chỉ nói
file cũ; nó không nói sản phẩm đã ra khỏi máy. Một lượt render hỏng nửa chừng cũng già
đi đúng 14 ngày như một tập đã lên sóng. Nên luật hiện hành là:

    dọn  ⇐  (có BẰNG CHỨNG đã đăng)  ∧  (quá `--days` ngày)
    giữ  ⇐  mọi trường hợp còn lại, kèm LÝ DO nói rõ thiếu bằng chứng nào

Module này chỉ trả lời vế đầu, cho **video**. Bằng chứng của audio là bản trong repo web,
đối chiếu ngay trên đĩa (`prune_media._ban_web`) nên không cần sổ.

## Ba cuốn sổ, khoá lấy từ đĩa chứ không đoán (đo 2026-09-20)

`*.published.json` — mỗi ngày một cuốn, nằm CÙNG THƯ MỤC với media của ngày đó:

    {"uploaded_at": "…", "fb_post_id": "…", "video_id": "…", "short_id": "…"}

`video_id` là bản 16:9, `short_id` là bản dọc. Hai bản là hai lần upload khác nhau, nên
`-short.mp4` phải soi `short_id`: lấy `video_id` cho nó là ghi nhận nhầm một video chưa
đăng thành đã đăng. Các file này ghi CÓ BOM — đọc bằng `utf-8` trần là `ValueError`, và
một cuốn sổ đọc-không-được lặng lẽ trở thành "chưa đăng".

`truyen-state.json` — sổ của đường ống truyện:

    {"last_publish_ok": true, "last_video": "…/PNTT 2441-2446.mp4",
     "history": ["2431-2438@20260808_0300", …]}

`last_publish_ok=false` nghĩa là lượt trước đăng hỏng; chính `sweep_old()` của
`daily_truyen.py` cũng giữ nguyên mọi thứ trong ca đó, và module này không được rộng tay
hơn nó. `history` giữ 50 dải chương gần nhất — đó là bằng chứng cho các tập cũ hơn lượt
cuối.

`playlist-youtube.json` — {tên playlist: [{title, video_id, published_at}]}. Tiêu đề chứa
dải chương (`… (Chương 1141-1150)`), nên nó là sổ đăng sống lâu nhất của kênh truyện:
`history` chỉ giữ 50 mục, playlist giữ tất.

## Vì sao phải KHAI sổ ra, không tự đi tìm

Sổ của truyện nằm ở trạm nội dung (`<trạm>/nghe-tien-truyen/`), còn video nằm ở trạm
giọng (`…/truyen-out/out/`) — hai cây khác nhau. Không có cách nào đoán đúng mà không
cắm đường dẫn của một cái máy vào mã nguồn. Nên: `*.published.json` được nhặt tự động vì
nó nằm ngay cạnh media, còn hai sổ kia phải `--evidence <đường>`. Khai một file không
phải sổ nào cả là **mã 2**, không phải cảnh báo: im lặng nhận nó là để người gõ tưởng
mình đã khai trong khi lượt dọn đang chạy với 0 bằng chứng.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_contract as SC  # noqa: E402

__all__ = ["BangChung", "SC", "TEN_PUBLISHED", "doc_json"]

TEN_PUBLISHED = "*.published.json"
# Dải chương trong tên file / tiêu đề: `PNTT 2441-2446.mp4`, `… (Chương 1141-1150)`.
_DAI = re.compile(r"(\d{1,6})\s*-\s*(\d{1,6})")
# Tên bản dọc: `…-short.mp4`, `…_short.mp4`, `short-2026-09-18.mp4`.
_LA_SHORT = re.compile(r"(?:^|[-_ ])short(?:[-_ .]|$)", re.I)


def doc_json(p: Path):
    """Đọc JSON của đường ống: LUÔN `utf-8-sig`.

    `utf-8-sig` đọc được cả file có BOM lẫn file không BOM; `utf-8` thì chỉ đọc được một
    nửa số file trên máy này. Chọn cái đọc được cả hai."""
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except OSError as e:
        raise SC.StationMissing(f"không đọc được sổ đăng {p}: {e}") from e
    try:
        return json.loads(raw)
    except ValueError as e:
        raise SC.ContractError(
            f"{p} không phải JSON hợp lệ ({e}) — sổ đăng hỏng thì mọi file trông như "
            f"CHƯA đăng, và lượt dọn sẽ giữ tất mà không ai hiểu vì sao") from e


def _dai_trong(s: str) -> set[tuple[int, int]]:
    return {(int(a), int(b)) for a, b in _DAI.findall(str(s))}


class BangChung:
    """Chỉ mục ba cuốn sổ. `cho_video(p)` -> dict bằng chứng, hoặc None khi CHƯA có."""

    def __init__(self):
        self._nguon: list[dict] = []
        self._theo_thu_muc: dict[str, list[tuple[Path, dict]]] = {}
        self._da_quet: set[str] = set()
        self._ten_video: dict[str, Path] = {}        # tên file đã đăng (truyện) -> sổ
        self._dai: dict[tuple[int, int], tuple[Path, str, str]] = {}

    # ── dựng ────────────────────────────────────────────────────────────────

    @classmethod
    def doc(cls, duong_ds) -> "BangChung":
        bc = cls()
        for d in (duong_ds or []):
            bc._nap(Path(d))
        return bc

    def nguon(self) -> list[dict]:
        return list(self._nguon)

    def _nap(self, p: Path) -> None:
        p = p.expanduser()
        if not p.is_file():
            raise SC.StationMissing(f"không thấy file bằng chứng {p}")
        d = doc_json(p)
        loai = self._nhan_dang(d)
        if loai is None:
            raise SC.ContractError(
                f"{p}: không nhận ra là sổ đăng nào. Chờ một trong ba: `*.published.json` "
                f"(khoá `video_id`/`short_id`), `truyen-state.json` (`last_publish_ok` + "
                f"`history`), `playlist-youtube.json` ({{playlist: [{{title, video_id}}]}}).")
        self._nguon.append({"path": p.as_posix(), "kind": loai})
        getattr(self, f"_nap_{loai.replace('-', '_')}")(p, d)

    @staticmethod
    def _nhan_dang(d) -> str | None:
        if not isinstance(d, dict):
            return None
        if "last_publish_ok" in d or ("last_video" in d and "history" in d):
            return "truyen-state"
        if {"video_id", "short_id", "uploaded_at", "fb_post_id"} & set(d):
            return "published-json"
        if d and all(isinstance(v, list) and all(isinstance(x, dict) and "video_id" in x
                                                 for x in v) for v in d.values()):
            return "playlist"
        return None

    def _nap_published_json(self, p: Path, d: dict) -> None:
        self._theo_thu_muc.setdefault(self._khoa(p.parent), []).append((p, d))

    def _nap_truyen_state(self, p: Path, d: dict) -> None:
        if not d.get("last_publish_ok"):
            # Lượt cuối đăng HỎNG: không ghi `last_video` vào chỉ mục. `history` thì vẫn
            # ghi — các tập trước đó đã đăng xong từ lâu, lỗi của lượt cuối không xoá
            # bằng chứng của chúng.
            pass
        elif d.get("last_video"):
            self._ten_video[Path(str(d["last_video"])).name.lower()] = p
        for muc in (d.get("history") or []):
            for dai in _dai_trong(str(muc).split("@", 1)[0]):
                self._dai.setdefault(dai, (p, "history", str(muc)))

    def _nap_playlist(self, p: Path, d: dict) -> None:
        for ds in d.values():
            for muc in ds:
                vid = str(muc.get("video_id") or "").strip()
                if not vid:
                    continue
                for dai in _dai_trong(muc.get("title") or ""):
                    self._dai.setdefault(dai, (p, "video_id", vid))

    # ── tra ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _khoa(d: Path) -> str:
        return d.expanduser().as_posix().rstrip("/").lower()

    def _so_cung_thu_muc(self, thu_muc: Path) -> list[tuple[Path, dict]]:
        """Sổ `*.published.json` nằm cạnh media — nhặt tự động, nhớ lại cho lượt sau.

        Sổ hỏng ở đây KHÔNG làm sập lượt quét: nó chỉ có nghĩa là thư mục đó chưa chứng
        minh được gì, và nhánh "chưa có bằng chứng ⇒ giữ" đã là nhánh an toàn. Sổ khai
        tường minh thì ngược lại — hỏng là mã 2, vì người gõ đã chỉ đích danh nó."""
        k = self._khoa(thu_muc)
        if k not in self._da_quet:
            self._da_quet.add(k)
            try:
                ds = sorted(thu_muc.glob(TEN_PUBLISHED))
            except OSError:
                ds = []
            for f in ds:
                try:
                    d = doc_json(f)
                except SC.StudioError:
                    continue
                if isinstance(d, dict) and self._nhan_dang(d) == "published-json":
                    self._theo_thu_muc.setdefault(k, []).append((f, d))
        return self._theo_thu_muc.get(k, [])

    def cho_video(self, p: Path) -> dict | None:
        """Bằng chứng video `p` đã lên YouTube, hoặc None. Không bao giờ ném lỗi khi thiếu —
        'chưa có bằng chứng' là một câu trả lời hợp lệ, và là câu trả lời an toàn."""
        p = Path(p)
        khoa = "short_id" if _LA_SHORT.search(p.stem) else "video_id"
        for f, d in self._so_cung_thu_muc(p.parent):
            gia = str(d.get(khoa) or "").strip()
            if gia:
                return {"source": f.as_posix(), "kind": "published-json",
                        "key": khoa, "value": gia}
        so = self._ten_video.get(p.name.lower())
        if so is not None:
            return {"source": so.as_posix(), "kind": "truyen-state",
                    "key": "last_video", "value": p.name}
        for dai in _dai_trong(p.stem):
            hit = self._dai.get(dai)
            if hit:
                f, khoa2, gia = hit
                return {"source": f.as_posix(),
                        "kind": "truyen-state" if khoa2 == "history" else "playlist",
                        "key": khoa2, "value": gia}
        return None

    def vi_sao_chua(self, p: Path) -> str:
        """Câu giải thích cho báo cáo — nói THIẾU GÌ, không nói chung chung."""
        khoa = "short_id" if _LA_SHORT.search(Path(p).stem) else "video_id"
        if not self._nguon and not self._theo_thu_muc:
            return (f"chưa có bằng chứng đã đăng: không thấy `{TEN_PUBLISHED}` cạnh file và "
                    f"chưa khai sổ nào (`--evidence`)")
        return (f"chưa có bằng chứng đã đăng: `{khoa}` trống/không có trong sổ cạnh file, "
                f"và tên file không khớp sổ nào đã khai")
