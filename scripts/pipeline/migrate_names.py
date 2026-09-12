#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Di trú DỮ LIỆU TRÊN ĐĨA từ bộ tên tiếng Việt sang tiếng Anh (12/09/2026).

## Nó đụng vào cái gì

Đợt đổi tên 12/09 đổi cả **tên khoá và tên thư mục trạng thái** — thứ đã nằm sẵn trên đĩa
của chiến dịch đang chạy. Code mới đọc tên mới, nên nếu không chạy file này thì hàng chờ
cũ nằm im mãi trong thư mục không ai đọc, và sổ sự kiện cũ không lọc được theo bài.

| Trên đĩa | Cũ | Mới |
|---|---|---|
| Sổ sự kiện | `logs/su-kien.jsonl` | `logs/events.jsonl` |
| Phản hồi | `logs/tg-phan-hoi.json` | `logs/feedback.json` |
| Hàng chờ | `logs/viec/{cho,dang-lam,xong,hong}/` | `logs/jobs/{pending,running,done,failed}/` |
| Đếm lần viết | `<bài>/.viet-lan.json` | `<bài>/.write-count.json` |
| Chấm cổng | `gates.json` khoá tiếng Việt | khoá tiếng Anh |

## Ba luật của file này

1. **KHÔNG XOÁ GÌ.** Đổi tên và ghi bản mới; bản cũ được đổi đuôi `.bak-<ngày>` chứ không
   biến mất. Di trú sai mà đã xoá nguồn thì không còn đường lùi.
2. **CHẠY LẠI ĐƯỢC.** Gọi hai lần cho kết quả như gọi một lần. Di trú hay bị ngắt giữa
   chừng — lần chạy thứ hai phải đi tiếp chứ không được hỏng.
3. **`--dry-run` là mặc định của người cẩn thận.** In ra sẽ đổi gì rồi mới thật sự đổi.

⚠️ `logs/tg-approve.json` **cố tình không di trú token đang chờ**: nó chỉ giữ con trỏ
`offset` và các token chưa dùng. Tệ nhất là phải gửi lại tin duyệt — rẻ hơn nhiều so với
rủi ro dịch sai một cấu trúc chỉ sống 48 giờ. Giữ `offset`, dọn danh sách token.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Khoá dùng chung cho sổ sự kiện và việc trong hàng chờ.
KHOA = {
    "luc": "at", "viec": "job", "bai": "post", "boi": "by", "qua": "via",
    "buoc": "step", "ma_viec": "job_id", "ma": "job_id", "ly_do": "reason",
    "ly_do_hong": "error", "hong_luc": "failed_at", "xong_luc": "finished_at",
    "se_thu_lai": "will_retry", "tao_luc": "created_at", "so_lan": "attempts",
    "nguon": "source", "ghi_chu": "note", "noi_dung": "text", "ket_qua": "result",
    "thu_muc": "folder", "vinh_vien": "permanent",
}

# Khoá riêng của `gates.json`.
KHOA_GATES = {
    "thu_muc": "folder", "mien_tru": "waived", "tong": "total", "xanh": "pass",
    "do_chan": "fail_block", "do_canh_bao": "fail_warn", "thieu": "missing",
    "ket_luan": "verdict", "cong": "gates", "ma": "id", "do_duoc": "measured",
    "luat": "rule", "trang_thai": "status", "muc": "level", "ghi_chu": "note",
}
# Giá trị trong `gates.json` cũng là từ tiếng Việt, không chỉ khoá.
GIA_TRI_GATES = {"xanh": "pass", "do": "fail", "thieu": "missing",
                 "chan": "block", "canh_bao": "warn"}

# Tên bước — nằm trong sổ sự kiện và trong việc của hàng chờ.
BUOC = {"cho-G1": "await-G1", "cho-G2": "await-G2", "cho-G3": "await-G3",
        "dung-bai": "create-post", "soan": "write", "cham-cong": "check-gates",
        "sua-loi-cong": "fix-gates", "dung-trang": "build-page",
        "phat-hanh": "release", "xong": "done", "tiep": "next"}

# Tên SỰ KIỆN trong sổ — cũng là chuỗi tiếng Việt đã ghi ra đĩa.
SU_KIEN = {"viec_bat_dau": "job_started", "viec_xong": "job_done",
           "viec_hong": "job_failed", "viec_bo_qua": "job_skipped",
           "cham_tran_viet_lai": "rewrite_limit_hit", "phan_hoi": "feedback",
           "g1_duyet": "g1_approved", "g2_duyet": "g2_approved", "g3_duyet": "g3_approved",
           "g1_tu_choi": "g1_rejected", "g2_tu_choi": "g2_rejected",
           "g3_tu_choi": "g3_rejected"}

O_CU_MOI = {"cho": "pending", "dang-lam": "running", "xong": "done", "hong": "failed"}


def loi(m: str) -> None:
    sys.stderr.write(f"migrate_names: {m}\n")


def _doi_khoa(d: dict, bang: dict, gia_tri: dict | None = None) -> dict:
    ra = {}
    for k, v in d.items():
        k2 = bang.get(k, k)
        if isinstance(v, dict):
            v = _doi_khoa(v, bang, gia_tri)
        elif isinstance(v, list):
            v = [_doi_khoa(x, bang, gia_tri) if isinstance(x, dict) else x for x in v]
        elif isinstance(v, str):
            if gia_tri and v in gia_tri:
                v = gia_tri[v]
            elif v in BUOC:
                v = BUOC[v]
        ra[k2] = v
    return ra


def _sao_luu(p: Path) -> None:
    """Giữ bản cũ cạnh bản mới. Di trú sai mà đã xoá nguồn thì không còn đường lùi."""
    bak = p.with_suffix(p.suffix + f".bak-{date.today():%Y%m%d}")
    if not bak.exists():
        shutil.copy2(p, bak)


def _doi_ten_su_kien(dong: list[str]) -> tuple[list[str], int]:
    ra, dem = [], 0
    for l in dong:
        try:
            d = json.loads(l)
        except json.JSONDecodeError:
            ra.append(l)
            continue
        if d.get("job") in SU_KIEN:
            d["job"] = SU_KIEN[d["job"]]
            dem += 1
        ra.append(json.dumps(d, ensure_ascii=False))
    return ra, dem


def ten_su_kien(campaign: Path, *, that: bool) -> list[str]:
    """Đổi tên sự kiện trong sổ ĐÃ di trú khoá. Tách riêng để chạy lại được nhiều lần."""
    p = campaign / "logs" / "events.jsonl"
    if not p.is_file():
        return []
    dong = [x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    _, dem = _doi_ten_su_kien(dong)
    if not dem:
        return []
    ra = [f"tên sự kiện trong sổ: {dem} dòng"]
    if that:
        _sao_luu(p)
        moi, _ = _doi_ten_su_kien(dong)
        p.write_text("\n".join(moi) + "\n", encoding="utf-8", newline="\n")
    return ra


def so_su_kien(campaign: Path, *, that: bool) -> list[str]:
    cu, moi = campaign / "logs" / "su-kien.jsonl", campaign / "logs" / "events.jsonl"
    if not cu.is_file():
        return []
    ra = [f"sổ sự kiện: {cu.name} → {moi.name}"]
    if not that:
        return ra
    _sao_luu(cu)
    dong = []
    for l in cu.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        try:
            dong.append(json.dumps(_doi_khoa(json.loads(l), KHOA), ensure_ascii=False))
        except json.JSONDecodeError:
            dong.append(l)          # dòng hỏng thì chép nguyên — sổ là bằng chứng, không sửa
    with moi.open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    cu.unlink()
    return ra


def hang_cho(campaign: Path, *, that: bool) -> list[str]:
    cu, moi = campaign / "logs" / "viec", campaign / "logs" / "jobs"
    if not cu.is_dir():
        return []
    ra = []
    for o_cu, o_moi in O_CU_MOI.items():
        d = cu / o_cu
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            ra.append(f"hàng chờ: viec/{o_cu}/{f.name} → jobs/{o_moi}/{f.name}")
            if not that:
                continue
            dich = moi / o_moi
            dich.mkdir(parents=True, exist_ok=True)
            try:
                v = _doi_khoa(json.loads(f.read_text(encoding="utf-8")), KHOA)
            except json.JSONDecodeError:
                loi(f"{f} hỏng — chép nguyên sang jobs/failed/")
                dich = moi / "failed"
                dich.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dich / f.name)
                continue
            (dich / f.name).write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
    if that and ra:
        shutil.rmtree(cu, ignore_errors=True)
    return ra


def gates(campaign: Path, *, that: bool) -> list[str]:
    ra = []
    for p in sorted(campaign.glob("*/gates.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loi(f"{p} hỏng — bỏ qua")
            continue
        if "verdict" in d:
            continue                # đã di trú rồi
        ra.append(f"chấm cổng: {p.parent.name}/gates.json")
        if not that:
            continue
        _sao_luu(p)
        p.write_text(json.dumps(_doi_khoa(d, KHOA_GATES, GIA_TRI_GATES),
                                ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
    return ra


def file_le(campaign: Path, *, that: bool) -> list[str]:
    ra = []
    cap = [(campaign / "logs" / "tg-phan-hoi.json", campaign / "logs" / "feedback.json")]
    cap += [(p, p.parent / ".write-count.json")
            for p in sorted(campaign.glob("*/.viet-lan.json"))]
    for cu, moi in cap:
        if not cu.is_file() or moi.exists():
            continue
        ra.append(f"đổi tên: {cu.name} → {moi.name}")
        if that:
            d = json.loads(cu.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                d = {k: [_doi_khoa(x, KHOA) if isinstance(x, dict) else x for x in v]
                     if isinstance(v, list) else v for k, v in d.items()}
            moi.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
            cu.unlink()
    return ra


def tg_state(campaign: Path, *, that: bool) -> list[str]:
    """Giữ `offset`, DỌN token đang chờ. Xem cảnh báo ở đầu file."""
    p = campaign / "logs" / "tg-approve.json"
    if not p.is_file():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if "cho" not in d:
        return []
    ra = [f"Telegram: giữ offset, dọn {len(d.get('cho') or {})} token đang chờ"]
    if that:
        _sao_luu(p)
        p.write_text(json.dumps({"offset": d.get("offset"), "pending": {}},
                                ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
    return ra


def di_tru(campaign: Path, *, that: bool) -> list[str]:
    ra = []
    for ham in (so_su_kien, ten_su_kien, hang_cho, gates, file_le, tg_state):
        ra += ham(campaign, that=that)
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Di trú tên dữ liệu sang tiếng Anh.")
    ap.add_argument("campaign", nargs="+", help="một hoặc nhiều thư mục chiến dịch")
    ap.add_argument("--apply", action="store_true",
                    help="thật sự đổi; không có cờ này thì chỉ in ra sẽ đổi gì")
    a = ap.parse_args(argv)

    tong = 0
    for x in a.campaign:
        campaign = Path(x)
        if not (campaign / "campaign.md").is_file():
            loi(f"bỏ qua {campaign} — không thấy campaign.md")
            continue
        viec = di_tru(campaign, that=a.apply)
        print(f"\n## {campaign.name} — {len(viec)} việc")
        for v in viec:
            print(f"  {'✔' if a.apply else '·'} {v}")
        tong += len(viec)
    if not a.apply:
        print(f"\n{tong} việc. Chạy lại với --apply để thật sự đổi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
