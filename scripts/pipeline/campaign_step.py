#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Chạy MỘT bước của chiến dịch blog. Không phải cả chuỗi — có chủ đích.

```
dung-bai ──[ Cổng 1 ]── soan ──[ Cổng 2 ]── dang
```

## Vì sao ba bước rời

Script điều phối gộp đã bị gỡ 04/09/2026 vì nó *"gộp dựng và đăng vào một lệnh, nên một
bước hỏng là phải chạy lại từ đầu, và cổng duyệt của người bị nuốt vào giữa chuỗi"*. Gộp
lại dưới một cái tên khác là dựng lại đúng cái đã bỏ. Mỗi bước ở đây chạy lại được độc
lập, và hai cổng nằm RÕ giữa các bước chứ không lẫn vào trong.

## Vì sao logic nằm ở Python còn runner chỉ là vỏ PowerShell

Bước `dung-bai` phải đọc bảng Content trong Markdown để biết bài nào tới hạn. PowerShell
5.1 trên máy đích không đọc nổi YAML/Markdown có cấu trúc — đó chính là lý do
`campaign_cfg.py` ra đời. Viết lại bộ đọc bảng bằng PowerShell là đi ngược một bài học đã
trả giá. PowerShell chỉ giữ vai nó làm tốt: mặt tiền cho Task Scheduler.

## Cổng tự trị

`channel.yml:autonomy` quyết mỗi cổng dừng hay tự mở:

| Mức | Hành vi |
|---|---|
| `suggest` (mặc định) | Dừng, gửi Telegram xin duyệt |
| `full` | Tự mở cổng, chạy thẳng |

Giá trị lạ → coi như `suggest`. **Fail-closed**: một khoá gõ sai không được biến thành
quyền đăng ra ngoài. Và chỉ NGƯỜI sửa được `channel.yml` — agent không tự nâng quyền.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
sys.path.insert(0, str(_HERE))
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402
import approve_bus as AB  # noqa: E402

TRUOC_MAC_DINH = 7


def loi(m: str) -> None:
    sys.stderr.write(f"campaign_step: {m}\n")


# ── Slug ────────────────────────────────────────────────────────────────────

def slug_hoa(tieu_de: str) -> str:
    """Tiêu đề tiếng Việt -> slug `a-z0-9-` mà `new_post.py` chấp nhận.

    `Đ`/`đ` là NGOẠI LỆ CỨNG: `unicodedata.normalize("NFD", "đ")` KHÔNG tách được nó
    thành `d` + dấu, vì đó là một chữ cái riêng chứ không phải `d` có dấu phụ. Không thay
    tay thì nó bị bỏ hẳn và `đường` thành `uong`. Cùng cái bẫy `fb_format.py` đã dính.
    """
    s = tieu_de.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s or "bai"


# ── Đọc bảng ────────────────────────────────────────────────────────────────

def _doc(cam: Path):
    fm, than = md_io.read_fm(cam / "campaign.md")
    _, dong = md_io.read_table(than, "CONTENT")
    return fm, than, dong


def _autonomy(cam: Path) -> str:
    import yaml
    kenh = SP.channel_of(cam / "campaign.md")
    d = yaml.safe_load((kenh / SP.MOC_KENH).read_text(encoding="utf-8")) or {}
    muc = str(d.get("autonomy") or "suggest").strip()
    # Giá trị lạ -> mức CHẶT nhất. Một khoá gõ sai không được thành quyền đăng ra ngoài.
    return muc if muc in ("suggest", "auto_safe", "full") else "suggest"


def bai_toi_han(cam: Path, truoc: int, hom_nay: date | None = None) -> list[dict]:
    """Bài có `schedule` trong [hôm nay, hôm nay+truoc] và CHƯA có thư mục."""
    hom_nay = hom_nay or date.today()
    _, _, dong = _doc(cam)
    ra = []
    for d in dong:
        if (d.get("folder") or "").strip():
            continue                       # đã dựng rồi
        lich = (d.get("schedule") or "").strip()
        if not lich:
            continue                       # thiếu lịch: bỏ qua, không đoán
        try:
            n = date.fromisoformat(lich)
        except ValueError:
            loi(f"{d.get('content_id')}: schedule {lich!r} không đọc được — bỏ qua.")
            continue
        if hom_nay <= n <= hom_nay.fromordinal(hom_nay.toordinal() + truoc):
            ra.append(d)
    return ra


def bai_cho_soan(cam: Path) -> list[dict]:
    """Qua Cổng 1, chưa qua Cổng 2, đã có thư mục."""
    _, _, dong = _doc(cam)
    return [d for d in dong
            if (d.get("g1") or "").strip()
            and not (d.get("g2") or "").strip()
            and (d.get("folder") or "").strip()]


def bai_san_sang_dang(cam: Path) -> list[dict]:
    """Qua Cổng 2 và CHƯA đăng. Thiếu g2 = chưa ai duyệt — tuyệt đối không đăng."""
    _, _, dong = _doc(cam)
    return [d for d in dong
            if (d.get("g2") or "").strip()
            and not (d.get("published") or "").strip()
            and (d.get("folder") or "").strip()]


# ── Cổng ────────────────────────────────────────────────────────────────────

def mo_cong(cam: Path, cong: str, cids: list[str], *, bot, hom_nay: date | None = None,
            lo: int | None = None) -> dict:
    """`suggest` -> gửi Telegram xin duyệt. `full` -> tự mở cổng."""
    hom_nay = hom_nay or date.today()
    muc = _autonomy(cam)
    if not cids:
        return {"cong": cong, "muc": muc, "so_bai": 0}
    if muc == "full":
        bay_gio = datetime.combine(hom_nay, datetime.min.time()).astimezone()
        xong = AB._ap_dung(cam, cong, cids, boi="tự động (autonomy=full)",
                           ghi_chu="autonomy=full — không có cổng người", bay_gio=bay_gio)
        return {"cong": cong, "muc": muc, "tu_duyet": xong}
    # Hỏi ĐÚNG những bài bước này vừa xử lý. Để `gui_cong` tự truy vấn thì nó hỏi cả nhóm
    # đang chờ, trong khi nhánh `full` ngay trên chỉ duyệt `cids` — hai chế độ lệch nhau.
    kq = AB.gui_cong(cam, cong, bot=bot, lo=lo, cids=cids)
    return {"cong": cong, "muc": muc, **kq}


# ── Bước 1: dựng bài ────────────────────────────────────────────────────────

def buoc_dung_bai(cam: Path, *, bot, truoc: int | None = None,
                  hom_nay: date | None = None, dry_run=False) -> dict:
    fm, _, _ = _doc(cam)
    rt = fm.get("runtime") or {}
    truoc = truoc if truoc is not None else int(rt.get("lookahead_days") or TRUOC_MAC_DINH)
    ds = bai_toi_han(cam, truoc, hom_nay)
    if not ds:
        return {"buoc": "dung-bai", "tao": 0, "ly_do": "không có bài nào tới hạn"}

    tsv = cam / "logs" / "bulk.tsv"
    tsv.parent.mkdir(parents=True, exist_ok=True)
    tsv.write_text("".join(
        f"{d['content_id']}\t{slug_hoa(d['content_name'])}\t{d['content_name']}\t"
        f"{d.get('angle', '')}\n" for d in ds), encoding="utf-8", newline="\n")

    if dry_run:
        return {"buoc": "dung-bai", "dry_run": True,
                "se_tao": [d["content_id"] for d in ds]}

    # `--dien-vao-dong`: bảng Content của chiến dịch dài kỳ được lập lịch TRƯỚC, thư mục
    # dựng SAU. Không có cờ này thì `new_post.py` đâm vào cổng trùng content_id và không
    # tạo được bài nào — UAT 10/09 bắt được đúng chỗ này.
    r = subprocess.run(
        [sys.executable, str(_HERE / "new_post.py"), "--campaign", str(cam),
         "--bulk", str(tsv), "--dien-vao-dong"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    tsv.unlink(missing_ok=True)            # file trung gian, xoá ngay trong cùng bước
    if r.returncode != 0:
        loi(f"new_post --bulk thất bại:\n{r.stdout}{r.stderr}")
        return {"buoc": "dung-bai", "loi": r.stderr.strip()[:400], "exit": r.returncode}

    cong = mo_cong(cam, "g1", [d["content_id"] for d in ds], bot=bot, hom_nay=hom_nay)
    return {"buoc": "dung-bai", "tao": len(ds),
            "content_ids": [d["content_id"] for d in ds], "cong": cong}


# ── Bước 2: soạn ────────────────────────────────────────────────────────────

def _da_viet(bai: Path) -> bool:
    """`content.md` đã có chữ THẬT chưa, hay còn là khung rỗng?"""
    p = bai / "content.md"
    if not p.is_file():
        return False
    than = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
    than = re.sub(r"(?m)^\s*#.*$", "", than)
    than = re.sub(r"\{\{[^}]*\}\}", "", than)
    return len(than.strip()) > 400


def buoc_soan(cam: Path, *, bot, hom_nay: date | None = None, dry_run=False) -> dict:
    ds = bai_cho_soan(cam)
    if not ds:
        return {"buoc": "soan", "xu_ly": 0, "ly_do": "không có bài nào qua Cổng 1 mà chưa qua Cổng 2"}

    xong, cho_viet, hong = [], [], []
    for d in ds:
        bai = cam / (d.get("folder") or "").strip().lstrip("./")
        if not bai.is_dir():
            hong.append({"id": d["content_id"], "vi_sao": "không thấy thư mục bài"})
            continue
        if not _da_viet(bai):
            # Script KHÔNG viết được bài. Nói thẳng thay vì dựng ra một bài rỗng rồi
            # đẩy tiếp — bài rỗng đi qua được vài bước nữa mới hỏng, ở chỗ khó truy.
            cho_viet.append(d["content_id"])
            continue
        if dry_run:
            xong.append(d["content_id"])
            continue
        ok = True
        # `register_publish init` PHẢI chạy ở đây, trước Cổng 2. Cổng 2 duyệt bằng
        # `register_publish approve`, mà lệnh đó cần `publish.json` có sẵn — thiếu nó thì
        # người bấm nút duyệt và KHÔNG có gì được ghi. Đúng kiểu hỏng câm ở chỗ đắt nhất.
        for lenh in (["register_publish.py", str(bai), "init"],
                     ["gen_article.py", "--content-md", str(bai / "content.md"),
                      "--meta", str(bai / "meta.json"), "--out-dir", str(bai)],
                     ["blog_gates.py", str(bai)]):
            r = subprocess.run([sys.executable, str(_HERE / lenh[0]), *lenh[1:]],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            if r.returncode != 0:
                hong.append({"id": d["content_id"], "vi_sao": lenh[0],
                             "chi_tiet": (r.stdout + r.stderr).strip()[:300]})
                ok = False
                break
        if ok:
            xong.append(d["content_id"])

    cong = mo_cong(cam, "g2", xong, bot=bot, hom_nay=hom_nay) if xong else None
    return {"buoc": "soan", "xu_ly": len(xong), "san_sang": xong,
            "cho_nguoi_viet": cho_viet, "hong": hong, "cong": cong}


# ── Bước 3: đăng ────────────────────────────────────────────────────────────

def buoc_dang(cam: Path, *, bot, uat=False, dry_run=False) -> dict:
    ds = bai_san_sang_dang(cam)
    if not ds:
        return {"buoc": "dang", "dang": 0, "ly_do": "không có bài nào qua Cổng 2 mà chưa đăng"}

    ra = []
    for d in ds:
        bai = cam / (d.get("folder") or "").strip().lstrip("./")
        cmd = [sys.executable, str(_HERE / "web_publish.py"), "--bai", str(bai)]
        if uat:
            cmd.append("--uat")
        if dry_run:
            cmd.append("--dry-run")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        ra.append({"id": d["content_id"], "exit": r.returncode,
                   "ra": r.stdout.strip()[-300:] or r.stderr.strip()[-300:]})
    return {"buoc": "dang", "dang": len([x for x in ra if x["exit"] == 0]), "chi_tiet": ra}


BUOC = {"dung-bai": buoc_dung_bai, "soan": buoc_soan, "dang": buoc_dang}


def ma_thoat(kq: dict) -> int:
    """Mã thoát suy TỪ KẾT QUẢ, không phải từ "hàm đã chạy xong".

    ĐÃ TRẢ GIÁ 10/09/2026: `main()` trả 0 vô điều kiện, nên một lượt `dung-bai` thất bại
    hoàn toàn (`new_post` từ chối cả 3 bài) vẫn cho `exit=0`. Chạy theo lịch thì
    `notify-run.ps1` đọc mã thoát đó và báo ✅ cho một lượt KHÔNG LÀM ĐƯỢC GÌ.

    Không có bài nào để làm ≠ thất bại: đó là 0. Có việc mà làm hỏng mới là khác 0.
    """
    if kq.get("loi"):
        return 3
    if kq.get("hong"):
        return 3
    if any(x.get("exit") not in (0, None) for x in (kq.get("chi_tiet") or [])):
        return 3
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Chạy một bước của chiến dịch blog.")
    ap.add_argument("campaign")
    ap.add_argument("buoc", choices=sorted(BUOC))
    ap.add_argument("--truoc", type=int, default=None, help="dựng trước bao nhiêu ngày")
    ap.add_argument("--uat", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cam = Path(a.campaign).resolve()
    if not (cam / "campaign.md").is_file():
        loi(f"không thấy {cam / 'campaign.md'}")
        return 2

    import telegram_io
    try:
        bot = telegram_io.Bot()
    except (FileNotFoundError, ValueError) as e:
        # Không có Telegram thì vẫn chạy được ở `autonomy: full` và ở `--dry-run`.
        # Ở `suggest` mà thiếu bot thì bước sẽ dừng tại cổng và nói rõ vì sao.
        loi(f"không dựng được bot Telegram ({e}) — chỉ chạy được phần không cần cổng.")
        bot = None

    kw = {"bot": bot, "dry_run": a.dry_run}
    if a.buoc == "dung-bai":
        kw["truoc"] = a.truoc
    if a.buoc == "dang":
        kw["uat"] = a.uat
        kw.pop("dry_run", None)
        kw["dry_run"] = a.dry_run
    kq = BUOC[a.buoc](cam, **kw)
    print(json.dumps(kq, ensure_ascii=False, indent=2))
    return ma_thoat(kq)


if __name__ == "__main__":
    sys.exit(main())
