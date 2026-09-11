# -*- coding: utf-8 -*-
"""Hàng chờ việc — THƯ MỤC là trạng thái, `rename` là phép giành lượt.

## Vì sao cần hàng chờ

Poller đang giữ khoá đọc Telegram. Cho nó tự chạy agent viết bài (~10 phút) thì **cổng
duyệt điếc suốt 10 phút đó**: nhịp tim đứng lại, lượt sau tưởng nó chết rồi cướp khoá, và
ta quay lại đúng vòng lặp đã làm sập máy ngày 11/09/2026.

Nên poller chỉ **ghi một dòng việc** rồi đi tiếp, xong trong vài mili giây.

## Vì sao THƯ MỤC chứ không phải một file danh sách

```
logs/viec/cho/      việc đang chờ
logs/viec/dang-lam/ đã có thợ nhận
logs/viec/xong/     xong
logs/viec/hong/     hỏng quá số lần cho phép
```

Giành lượt = `os.rename(cho/x → dang-lam/x)`. **`rename` trong cùng ổ đĩa là nguyên tử**:
hai thợ cùng giành thì đúng một con thắng, con thua nhận `FileNotFoundError`. Không cần
khoá, không cần đọc-sửa-ghi, nên không có cuộc đua nào để mà thua.

Một file danh sách thì ngược lại: mỗi lần nhận việc phải đọc cả file, sửa, ghi lại — đúng
hình dạng read-modify-write đã làm **MẤT CÚ BẤM của người** ngày 10/09/2026.

Thêm một lợi ích không nhỏ: mở File Explorer ra là **thấy hàng chờ bằng mắt**.

## Việc hỏng thì sao

Việc mang theo `so_lan`. Thợ làm hỏng thì việc quay lại `cho/` với số lần +1; quá
`TRAN_LAN` thì sang `hong/` và **dừng hẳn** — không quay tít. Mỗi vòng viết lại đốt ~10
phút agent, nên vòng lặp vô hạn ở đây là đốt tiền thật.

## Thợ chết giữa chừng

Việc nằm lại `dang-lam/`. Quá `QUA_HAN_GIAY` mà không ai đụng tới thì coi như mồ côi và
được trả về `cho/`. Không có tiến trình nào phải trông giữ điều đó — `nhat()` tự dọn.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

TRAN_LAN = 3                       # làm hỏng quá ngần này lần thì thôi, đừng quay tít
QUA_HAN_GIAY = 30 * 60             # việc nằm `dang-lam` lâu hơn ngần này = thợ đã chết

CAC_O = ("cho", "dang-lam", "xong", "hong")


def _goc(cam: Path) -> Path:
    return Path(cam) / "logs" / "viec"


def _o(cam: Path, ten: str) -> Path:
    p = _goc(cam) / ten
    p.mkdir(parents=True, exist_ok=True)
    return p


def them(cam: Path, viec: str, *, bai: str | None = None, **chi_tiet) -> str:
    """Xếp một việc vào cuối hàng. Trả mã việc.

    Tên file bắt đầu bằng thời gian nên **thứ tự chữ cái chính là thứ tự thời gian** —
    không cần đọc nội dung file để biết việc nào tới trước.
    """
    ma = f"{datetime.now().astimezone():%Y%m%dT%H%M%S}-{secrets.token_hex(4)}"
    d = {"ma": ma, "viec": viec, "bai": bai, "so_lan": 0,
         "tao_luc": datetime.now().astimezone().isoformat(), **chi_tiet}
    (_o(cam, "cho") / f"{ma}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ma


def _tra_viec_mo_coi(cam: Path, *, bay_gio: float | None = None) -> int:
    """Việc nằm `dang-lam` quá lâu = thợ đã chết. Trả về `cho` để làm lại."""
    bay_gio = bay_gio if bay_gio is not None else time.time()
    n = 0
    for p in _o(cam, "dang-lam").glob("*.json"):
        try:
            if bay_gio - p.stat().st_mtime <= QUA_HAN_GIAY:
                continue
            os.replace(p, _o(cam, "cho") / p.name)
            n += 1
        except OSError:
            continue                  # con khác vừa đụng vào; không phải lỗi của ta
    return n


def nhat(cam: Path, *, bay_gio: float | None = None) -> dict | None:
    """Giành MỘT việc cũ nhất. `None` nếu hàng rỗng.

    Giành bằng `os.replace` — nguyên tử. Hai thợ cùng nhắm một việc thì đúng một con thắng;
    con thua thấy `OSError` và **đi thử việc kế tiếp**, không phải lỗi.
    """
    _tra_viec_mo_coi(cam, bay_gio=bay_gio)
    for p in sorted(_o(cam, "cho").glob("*.json")):
        dich = _o(cam, "dang-lam") / p.name
        try:
            os.replace(p, dich)
        except OSError:
            continue
        try:
            return json.loads(dich.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            os.replace(dich, _o(cam, "hong") / p.name)   # việc rách, đừng chặn hàng
            continue
    return None


def xong(cam: Path, ma: str, **ket_qua) -> None:
    _chuyen(cam, ma, "xong", ket_qua)


def hong(cam: Path, ma: str, ly_do: str) -> str:
    """Thợ làm hỏng. Còn lượt thì trả về hàng chờ; hết lượt thì sang `hong/`.

    Trả về ô đích để chỗ gọi biết mà báo người: `"cho"` là sẽ thử lại, `"hong"` là bỏ cuộc.
    """
    p = _o(cam, "dang-lam") / f"{ma}.json"
    if not p.is_file():
        return "hong"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        os.replace(p, _o(cam, "hong") / p.name)
        return "hong"
    d["so_lan"] = int(d.get("so_lan") or 0) + 1
    d["ly_do_hong"] = ly_do
    d["hong_luc"] = datetime.now().astimezone().isoformat()
    dich = "cho" if d["so_lan"] < TRAN_LAN else "hong"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(p, _o(cam, dich) / p.name)
    return dich


def _chuyen(cam: Path, ma: str, o_dich: str, them_truong: dict) -> None:
    p = _o(cam, "dang-lam") / f"{ma}.json"
    if not p.is_file():
        return
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        d = {"ma": ma}
    d.update(them_truong)
    d["xong_luc"] = datetime.now().astimezone().isoformat()
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(p, _o(cam, o_dich) / p.name)


def dem(cam: Path) -> dict:
    """Số việc trong từng ô — để báo trạng thái mà không phải mở từng file."""
    return {o: len(list(_o(cam, o).glob("*.json"))) for o in CAC_O}
