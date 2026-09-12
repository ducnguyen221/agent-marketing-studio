#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Điều phối đường ống TRONG PHIÊN — lối vào một cửa cho agent.

## Nó là gì

Agent ngồi cùng người trong một phiên không cần biết mười trạng thái và năm lệnh con. Nó
gọi đúng một lệnh, và lệnh này:

1. suy bước kế tiếp của từng bài (`tinh_trang`),
2. chạy tới khi đụng **cổng người**,
3. **DỪNG** và trả về đúng thứ agent cần đọc cho người nghe: bài nào, chờ cổng nào, câu hỏi
   là gì, và **mở file nào để trả lời được câu hỏi đó**.

Nó **không bao giờ tự mở cổng**. Mở cổng cần câu nói của người, và câu đó phải đi qua
`cong_duyet.mo_cong(--nguyen-van ...)`.

## Khác gì `tho_viec.py`

Cùng chạy một đường ống, khác chủ:

| | `tho_viec.py` | `chay_quy_trinh.py` |
|---|---|---|
| ai gọi | scheduled task, chạy nền | **agent, trong phiên** |
| lấy việc từ | hàng chờ (`logs/viec/`) | người chỉ định, hoặc suy từ bảng |
| mỗi lượt | đúng MỘT việc rồi thoát | chạy tới khi đụng cổng |
| tới cổng thì | trả việc về, báo Telegram | **in ra cho agent hỏi người ngay** |

Hai đường dùng chung mọi thứ bên dưới — cùng `campaign_step`, cùng `tinh_trang`, cùng kho
cổng. Chạy đường nào cũng để lại cùng một dấu vết.

## Hai chế độ

- `tung-bai` — một bài đi trọn đường ống, dừng ở mỗi cổng. Dùng khi bài quan trọng, hoặc
  đang dò xem quy trình chạy đúng chưa.
- `theo-giai-doan` — chạy cùng một bước cho N bài rồi gom lại hỏi người MỘT LẦN ở cổng.
  Dùng khi chạy đều nhiều bài và không muốn bị ngắt liên tục.

## Lệnh

```
chay_quy_trinh.py <chiến dịch> tinh-hinh [--json]
chay_quy_trinh.py <chiến dịch> chay [--che-do tung-bai|theo-giai-doan]
                                    [--bai A,B | --so-bai N] [--toi-buoc <bước>]
                                    [--json] [--dry-run]
```

`--dry-run` in ra kế hoạch sẽ chạy mà không chạy gì — dùng để trình người xem trước.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
sys.path.insert(0, str(_HERE))
import cong_duyet as CD  # noqa: E402
import tho_viec as TV  # noqa: E402
import tinh_trang as TT  # noqa: E402

CHE_DO = ("tung-bai", "theo-giai-doan")
SO_BAI_MAC_DINH = 5

# Trần an toàn cho MỘT lượt gọi. Không phải giới hạn nghiệp vụ — nó chặn ca vòng lặp: một
# bước báo xong mà `tinh_trang` vẫn suy ra đúng bước đó thì hai bên quay tít cho tới hết
# quota. Trần nhỏ hơn số bước của đường ống là hụt, nên lấy gấp đôi.
TRAN_BUOC_MOI_BAI = 2 * len(TT.THU_TU)

# Bước KHÔNG có artefact riêng của một bài để hỏi. Danh sách này phải ngắn và có lý do:
# mỗi tên trong đây là một chỗ ta buộc phải tin mã thoát, tức một chỗ có thể hỏng câm.
KHONG_CO_ARTEFACT = {"dung-bai"}


def loi(m: str) -> None:
    sys.stderr.write(f"chay_quy_trinh: {m}\n")


# ── Đọc tình hình ───────────────────────────────────────────────────────────

def _dong_theo_ma(cam: Path) -> dict:
    return {d["content_id"]: d for d in CD.doc_bang(cam)[3]}


def tinh_hinh(cam: Path) -> dict:
    """Bài nào đang ở bước nào — gộp theo bước để người nhìn một cái là nắm."""
    cam = Path(cam)
    theo_buoc: dict[str, list[str]] = {}
    for d in CD.doc_bang(cam)[3]:
        theo_buoc.setdefault(TT.buoc_ke(cam, d), []).append(d["content_id"])
    return {"tong": sum(len(v) for v in theo_buoc.values()),
            # Theo ĐÚNG thứ tự đường ống, không theo thứ tự từ điển: người đọc cần thấy
            # bài đang tắc ở đâu trên đường, không cần bảng chữ cái.
            "theo_buoc": {b: theo_buoc[b] for b in TT.THU_TU if b in theo_buoc}}


def _cong_cua_buoc(buoc: str) -> str | None:
    return buoc.replace("cho-G", "g") if buoc in TT.CAN_NGUOI else None


def _ho_so_cong(cam: Path, cid: str, cong: str) -> dict:
    dong = _dong_theo_ma(cam).get(cid) or {}
    h = CD.ho_so_bai(cam, dong)
    h["cong"] = cong
    if cong == "g2":
        h["chua_duoc_hoi"] = CD.vi_sao_chua_duoc_hoi(cam, dong)
    return h


# ── Chọn bài ────────────────────────────────────────────────────────────────

def chon_bai(cam: Path, *, bai: list[str] | None, so_bai: int | None) -> list[str]:
    """Người chỉ định bài nào thì đúng bài đó. Không chỉ định thì lấy N bài ĐANG CHẠY ĐƯỢC.

    "Chạy được" = bước kế tiếp không phải cổng và không phải `xong`. Lấy cả bài đang chờ
    cổng vào lô là mời agent chạy một bước mà nó không được phép chạy.
    """
    cam = Path(cam)
    hien = _dong_theo_ma(cam)
    if bai:
        thieu = [c for c in bai if c not in hien]
        if thieu:
            raise ValueError(f"không có trong bảng Content: {', '.join(thieu)}")
        return list(bai)
    chay_duoc = [d["content_id"] for d in CD.doc_bang(cam)[3]
                 if TT.buoc_ke(cam, d) not in TT.CAN_NGUOI | {"xong"}]
    n = SO_BAI_MAC_DINH if so_bai is None else so_bai
    return chay_duoc if n <= 0 else chay_duoc[:n]


# ── Chạy ────────────────────────────────────────────────────────────────────

def _chay_mot_buoc(cam: Path, cid: str, buoc: str, *, chay) -> dict:
    """Chạy một bước cho một bài và kết luận theo ARTEFACT, không theo mã thoát.

    Cùng luật với `tho_viec._da_ra_artefact`: `blog_gates` trả mã 1 khi cổng đỏ và `soan`
    trả khác 0 khi bài chưa đạt — cả hai ĐÃ LÀM XONG VIỆC. Đọc mã thoát rồi kết luận hỏng
    thì đúng những bài cần đi tiếp lại bị làm lại rồi vứt đi.
    """
    dong = _dong_theo_ma(cam).get(cid) or {}
    thu_muc = (dong.get("folder") or "").strip().lstrip("./")
    bai_p = Path(cam) / thu_muc if thu_muc else Path(cam)

    lenh = TV.LENH.get(buoc, [buoc])
    ok_tat_ca, thong_diep = True, []
    for l in lenh:
        ok, ra = chay(cam, l, cid)
        ok_tat_ca = ok_tat_ca and ok
        if ra:
            thong_diep.append(ra)

    ra_artefact = TV._da_ra_artefact(buoc, bai_p)
    return {"bai": cid, "buoc": buoc,
            "ma_thoat_sach": ok_tat_ca,
            "ra_artefact": ra_artefact,
            # Xong hay chưa hỏi ARTEFACT. `dung-bai` là NGOẠI LỆ CÓ TÊN: nó tạo thư mục
            # cho nhiều bài cùng lúc nên không có artefact riêng của một bài để hỏi, đành
            # tin mã thoát. Ngoại lệ có tên khác hẳn với mặc định tin mã thoát.
            "xong": ra_artefact or (buoc in KHONG_CO_ARTEFACT and ok_tat_ca),
            "thong_diep": "\n".join(thong_diep)[-800:]}


def chay(cam: Path, *, che_do: str = "tung-bai", bai: list[str] | None = None,
         so_bai: int | None = None, toi_buoc: str | None = None,
         dry_run: bool = False, chay_buoc=None) -> dict:
    """Đẩy các bài đã chọn đi tới khi đụng cổng. KHÔNG BAO GIỜ tự mở cổng.

    `chay_buoc=None` được giải nghĩa TẠI ĐÂY chứ không đặt sẵn ở chữ ký hàm: giá trị mặc
    định của tham số bị đóng băng lúc `def` chạy, nên vá `TV._chay_buoc` sau đó không có
    tác dụng — test tưởng đang chạy bộ giả mà thật ra gọi tiến trình con thật.
    """
    cam = Path(cam)
    chay_buoc = chay_buoc or TV._chay_buoc
    if che_do not in CHE_DO:
        raise ValueError(f"chế độ lạ: {che_do!r} — chỉ có {', '.join(CHE_DO)}")
    ds = chon_bai(cam, bai=bai, so_bai=so_bai)
    kq: dict = {"che_do": che_do, "bai": ds, "da_chay": [], "hong": [],
                "dung_o_cong": {}, "xong_han": []}

    if dry_run:
        kq["ke_hoach"] = [{"bai": c,
                           "buoc_ke": TT.buoc_ke(cam, _dong_theo_ma(cam).get(c) or {})}
                          for c in ds]
        return kq

    if che_do == "tung-bai":
        for cid in ds:
            _day_mot_bai(cam, cid, kq, toi_buoc=toi_buoc, chay_buoc=chay_buoc)
    else:
        # Theo giai đoạn: mỗi vòng đẩy CẢ LÔ đúng một bước, để các bài tới cổng cùng lúc
        # rồi hỏi người một lần. Đẩy lần lượt từng bài tới cổng thì người bị hỏi N lần —
        # đúng thứ chế độ này sinh ra để tránh.
        for _ in range(TRAN_BUOC_MOI_BAI):
            da_lam = False
            for cid in list(ds):
                b = TT.buoc_ke(cam, _dong_theo_ma(cam).get(cid) or {})
                if b in TT.CAN_NGUOI:
                    _ghi_dung_o_cong(cam, cid, _cong_cua_buoc(b), kq)
                    ds = [x for x in ds if x != cid]
                    continue
                if b == "xong":
                    if cid not in kq["xong_han"]:
                        kq["xong_han"].append(cid)
                    ds = [x for x in ds if x != cid]
                    continue
                if toi_buoc and b == toi_buoc:
                    ds = [x for x in ds if x != cid]
                    continue
                r = _chay_mot_buoc(cam, cid, b, chay=chay_buoc)
                kq["da_chay"].append(r)
                da_lam = True
                if not r["xong"]:
                    kq["hong"].append(r)
                    ds = [x for x in ds if x != cid]     # bài hỏng thì thôi đẩy tiếp
            if not da_lam:
                break
    kq["tinh_hinh"] = tinh_hinh(cam)
    return kq


def _ghi_dung_o_cong(cam: Path, cid: str, cong: str, kq: dict) -> None:
    """Ghi một bài vào nhóm chờ cổng. KHÔNG ghi trùng: một bài chỉ hỏi người một lần."""
    ds = kq["dung_o_cong"].setdefault(cong, [])
    if cid not in [h["content_id"] for h in ds]:
        ds.append(_ho_so_cong(cam, cid, cong))


def _day_mot_bai(cam: Path, cid: str, kq: dict, *, toi_buoc: str | None, chay_buoc) -> None:
    for _ in range(TRAN_BUOC_MOI_BAI):
        b = TT.buoc_ke(cam, _dong_theo_ma(cam).get(cid) or {})
        if b in TT.CAN_NGUOI:
            _ghi_dung_o_cong(cam, cid, _cong_cua_buoc(b), kq)
            return
        if b == "xong":
            kq["xong_han"].append(cid)
            return
        if toi_buoc and b == toi_buoc:
            return
        r = _chay_mot_buoc(cam, cid, b, chay=chay_buoc)
        kq["da_chay"].append(r)
        if not r["xong"]:
            kq["hong"].append(r)
            return
    kq["hong"].append({"bai": cid, "buoc": "?",
                       "thong_diep": f"quá {TRAN_BUOC_MOI_BAI} bước mà chưa tới cổng — "
                                     "nghi bước báo xong nhưng trạng thái không tiến"})


# ── In cho người ────────────────────────────────────────────────────────────

def _in_tinh_hinh(t: dict) -> None:
    print(f"{t['tong']} bài\n")
    for b, ds in t["theo_buoc"].items():
        print(f"  {b:<14} {len(ds):>3}  {', '.join(ds[:12])}"
              + (" …" if len(ds) > 12 else ""))


def _in_ket_qua(kq: dict) -> None:
    if kq.get("ke_hoach") is not None:
        print("KẾ HOẠCH (chưa chạy gì):")
        for k in kq["ke_hoach"]:
            print(f"  {k['bai']:<10} → {k['buoc_ke']}")
        return

    if kq["da_chay"]:
        print("ĐÃ CHẠY")
        for r in kq["da_chay"]:
            dau = "✔" if r["xong"] else "✘"
            print(f"  {dau} {r['bai']:<10} {r['buoc']}")
        print()
    if kq["hong"]:
        print("HỎNG — dừng ở đây, cần xem log")
        for r in kq["hong"]:
            print(f"  ✘ {r['bai']} · {r.get('buoc')}")
            for d in (r.get("thong_diep") or "").splitlines()[-6:]:
                print(f"      {d}")
        print()
    for cong, ds in kq["dung_o_cong"].items():
        print(f"⛔ DỪNG Ở {cong.upper()} — {len(ds)} bài chờ người quyết\n")
        for h in ds:
            print(f"  · {h['content_id']} — {h['content_name']}")
            if h.get("chua_duoc_hoi"):
                print(f"      ⚠️ chưa được đem ra hỏi: {h['chua_duoc_hoi']}")
            for nhan, p in h["file"].items():
                print(f"      {nhan:<16} {p}")
            if h.get("web"):
                print(f"      {'bản thật':<16} {h['web']}")
        print(f"\n  Duyệt:   cong_duyet.py <chiến dịch> mo --cong {cong} "
              f"--bai <mã> --boi \"<tên>\" --nguyen-van \"<câu người nói>\"")
        print(f"  Từ chối: cong_duyet.py <chiến dịch> tu-choi --cong {cong} "
              f"--bai <mã> --boi \"<tên>\" --nguyen-van \"<nhận xét>\"\n")
    if kq["xong_han"]:
        print(f"✅ xong hẳn: {', '.join(kq['xong_han'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Điều phối đường ống trong phiên — chạy tới cổng rồi dừng hỏi người.")
    ap.add_argument("campaign")
    sub = ap.add_subparsers(dest="lenh", required=True)

    pt = sub.add_parser("tinh-hinh", help="bài nào đang ở bước nào")
    pt.add_argument("--json", action="store_true")

    pc = sub.add_parser("chay", help="đẩy các bài tới cổng gần nhất")
    pc.add_argument("--che-do", choices=list(CHE_DO), default="tung-bai")
    pc.add_argument("--bai", default=None, help="mã bài, phân tách bằng dấu phẩy")
    pc.add_argument("--so-bai", type=int, default=None,
                    help=f"lấy N bài đang chạy được (mặc định {SO_BAI_MAC_DINH}; 0 = hết)")
    pc.add_argument("--toi-buoc", default=None, help="dừng TRƯỚC bước này")
    pc.add_argument("--dry-run", action="store_true")
    pc.add_argument("--json", action="store_true")

    a = ap.parse_args(argv)
    cam = Path(a.campaign)
    if not (cam / "campaign.md").is_file():
        loi(f"không thấy {cam / 'campaign.md'}")
        return 2

    if a.lenh == "tinh-hinh":
        t = tinh_hinh(cam)
        print(json.dumps(t, ensure_ascii=False, indent=2) if a.json else "", end="")
        if not a.json:
            _in_tinh_hinh(t)
        return 0

    try:
        kq = chay(cam, che_do=a.che_do,
                  bai=[x.strip() for x in a.bai.split(",") if x.strip()] if a.bai else None,
                  so_bai=a.so_bai, toi_buoc=a.toi_buoc, dry_run=a.dry_run)
    except ValueError as e:
        loi(str(e))
        return 2

    if a.json:
        print(json.dumps(kq, ensure_ascii=False, indent=2))
    else:
        _in_ket_qua(kq)
    # Dừng ở cổng KHÔNG phải hỏng: đó là kết quả đúng của đường ống có cổng người.
    return 3 if kq["hong"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
