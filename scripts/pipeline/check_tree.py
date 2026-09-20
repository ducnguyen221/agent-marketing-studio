#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm liên kết 4 tầng: CHANNELS → kênh → chiến dịch → bài.

Vì sao cần cổng riêng thay vì nhét vào `blog_gates.py`: blog_gates là cổng của MỘT BÀI,
chạy được trên một thư mục rời không có kênh nào bên trên. Trộn vào là mọi test của nó
phải dựng cả cây, và cổng bài mất khả năng chạy độc lập.

Liên kết gãy hỏng theo kiểu IM LẶNG: script không tìm thấy file thì bỏ qua chứ không kêu,
trang HTML render ra thiếu một bài mà không ai biết thiếu. Đây là chỗ bắt chúng.

Ba trạng thái, giống blog_gates: xanh · đỏ (chặn) · cảnh báo. `--strict` biến cảnh báo
thành đỏ.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import post_paths as PP  # noqa: E402
import studio_paths as SP  # noqa: E402


class So:
    def __init__(self):
        self.do: list[str] = []
        self.canh_bao: list[str] = []

    def loi(self, msg):
        self.do.append(msg)

    def nhac(self, msg):
        self.canh_bao.append(msg)


def _doc_json(p: Path, mac_dinh=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return mac_dinh


def check_post(post: Path, cam_id: str, kenh_id: str, s: So) -> None:
    name = f"{cam_id}/{post.name}"
    meta = _doc_json(post / "meta.json")
    if meta is None:
        s.loi(f"{name}: meta.json thiếu hoặc JSON hỏng")
        return
    cid = meta.get("post_id", "")
    if not post.name.startswith(cid + "_"):
        s.loi(f"{name}: tên thư mục không bắt đầu bằng post_id {cid!r}")
    if meta.get("campaign_id") and meta["campaign_id"] != cam_id:
        s.loi(f"{name}: meta.campaign_id={meta['campaign_id']!r} ≠ thư mục cha {cam_id!r}")

    r = post / "research.md"
    if r.is_file():
        fm, _ = md_io.read_fm(r)
        if fm.get("campaign_id") and fm["campaign_id"] != cam_id:
            s.loi(f"{name}: research.campaign_id={fm['campaign_id']!r} ≠ {cam_id!r}")
        if fm.get("content_id") and fm["content_id"] != cid:
            s.loi(f"{name}: research.content_id={fm['content_id']!r} ≠ meta.post_id {cid!r}")

    pj = _doc_json(post / "publish.json")
    if pj is None:
        s.nhac(f"{name}: chưa có publish.json (chạy register_publish init)")
        return
    if pj.get("schema") != "publish/2":
        s.nhac(f"{name}: publish.json còn schema cũ — chạy `register_publish migrate`")
        return
    if pj.get("campaign_id") != cam_id:
        s.loi(f"{name}: publish.campaign_id={pj.get('campaign_id')!r} ≠ {cam_id!r}")
    if pj.get("channel_id") and pj["channel_id"] != kenh_id:
        s.loi(f"{name}: publish.channel_id={pj['channel_id']!r} ≠ kênh {kenh_id!r}")

    content = (post / "content.md").read_text(encoding="utf-8") if (post / "content.md").is_file() else ""
    for p in pj.get("posts", []):
        pid = p.get("post_id", "?")
        neo = p.get("post_content", "")
        if neo and content and f"## {neo}" not in content:
            s.loi(f"{name}/{pid}: trỏ neo {neo!r} mà content.md không có khối đó")
        # Giá trị trạng thái phải nằm trong tập code THẬT SỰ sinh ra. Không kiểm thì một
        # giá trị agent chép từ tài liệu cũ (`human_review`, `ai_qa_failed`…) nằm im trong sổ
        # rồi in thẳng ra Excel — không lệnh nào đặt được nó, và không ai định nghĩa nó.
        for truong, hop_le in PP.GIA_TRI_HOP_LE.items():
            gt = (p.get("review", {}).get("status") if truong == "review_status"
                  else p.get("publish", {}).get("status") if truong == "publish_status"
                  else p.get(truong))
            if gt is not None and gt not in hop_le:
                s.loi(f"{name}/{pid}: {truong}={gt!r} không hợp lệ; "
                      f"hợp lệ: {', '.join(sorted(x for x in hop_le if x))}")

        rv = p.get("review", {})
        if rv.get("status") == "approved" and not rv.get("approved_by"):
            s.loi(f"{name}/{pid}: đã approved nhưng không ghi AI duyệt — Cổng 2 phải có dấu vết")
        pb = p.get("publish", {})
        if pb.get("status") == "published" and not pb.get("link"):
            s.loi(f"{name}/{pid}: published nhưng link rỗng")
        if (p.get("channel") == "facebook" and p.get("post_format") == "facebook_post"
                and pb.get("status") == "published" and not pb.get("comment_id")):
            s.loi(f"{name}/{pid}: bài Facebook đã đăng mà không có comment_id — bài mồ côi")


def check_campaign(campaign: Path, kenh_id: str, pillars: list, nen_tang: set, s: So) -> dict:
    fm, body = md_io.read_fm(campaign / "campaign.md")
    cid = fm.get("id", "")
    if cid != campaign.name:
        s.loi(f"{campaign.name}: campaign.md id={cid!r} ≠ tên thư mục")
    if fm.get("channel") != kenh_id:
        s.loi(f"{campaign.name}: campaign.md channel={fm.get('channel')!r} ≠ kênh {kenh_id!r}")
    if fm.get("content_pillar") and pillars and fm["content_pillar"] not in pillars:
        s.loi(f"{campaign.name}: content_pillar={fm['content_pillar']!r} không có trong "
              f"channel.yml:pillars {pillars}")
    lac = set(fm.get("channels") or []) - nen_tang
    if lac:
        s.loi(f"{campaign.name}: channels {sorted(lac)} không có trong channel.yml:platforms")
    if fm.get("status") == "active":
        con = [k for k, v in fm.items() if isinstance(v, str) and "{{" in v]
        if con:
            s.loi(f"{campaign.name}: status=active mà frontmatter còn placeholder ở {con[:4]}")

    col, row = md_io.read_table(body, "CONTENT")
    if not col:
        s.loi(f"{campaign.name}: campaign.md thiếu bảng CONTENT (marker <!-- CONTENT:BEGIN -->)")
        return {"id": cid, "post": 0, "da_dang": 0}

    # HAI hình dạng bài, đều hợp lệ — cổng phải hiểu cả hai:
    #
    #   <mã>_<slug>/          bài viết tay: thư mục con TRỰC TIẾP, có meta.json.
    #   out/<ngày>/           một SỐ của chiến dịch chạy theo lịch: thư mục LỒNG, do
    #                         engine sinh, không có meta.json (nó không đi qua new_post.py).
    #
    # Trước 08/09/2026 cổng chỉ biết hình dạng đầu, nên mọi dòng trỏ `out/<ngày>` đều ĐỎ —
    # tức nạp ngược lịch sử vào bảng Content là không thể mà không phá cổng. Sửa cổng chứ
    # không bỏ cột `folder`: cột đó là thứ duy nhất nối một dòng sổ với sản phẩm của nó.
    tren_dia = {d.name for d in SP.posts(campaign)}
    trong_bang = {}
    for d in row:
        f = (d.get("folder") or "").strip("./ ")
        trong_bang[f] = d
        if not f:
            continue
        if "/" in f:
            # Đường dẫn lồng: chỉ cần thư mục CÓ THẬT. Không đòi meta.json vì engine
            # không sinh file đó, và đòi thêm cũng không chứng minh được gì hơn.
            if not (campaign / f).is_dir():
                s.loi(f"{campaign.name}: bảng Content có {f!r} nhưng thư mục không tồn tại")
        elif f not in tren_dia:
            s.loi(f"{campaign.name}: bảng Content có {f!r} nhưng thư mục không tồn tại")
    # Mồ côi CHỈ xét thư mục bài trực tiếp — `out/` không phải bài, và các thư mục con của
    # nó chỉ thành "số" khi có dòng trỏ tới; chưa nạp ngược không phải là lỗi.
    for t in tren_dia - set(trong_bang):
        s.loi(f"{campaign.name}: thư mục bài {t!r} không có dòng nào trong bảng Content (mồ côi)")

    for d in SP.posts(campaign):
        check_post(d, cid, kenh_id, s)

    # g1 ⇔ status: có ngày duyệt thì không còn là proposed
    for d in row:
        if d.get("g1") and d.get("status") == "proposed":
            s.nhac(f"{campaign.name}/{d.get('content_id')}: có g1 mà status vẫn proposed")
        if d.get("status") == "published" and not d.get("published"):
            s.nhac(f"{campaign.name}/{d.get('content_id')}: published mà thiếu ngày đăng")

    return {"id": cid, "post": len(row),
            "da_dang": sum(1 for d in row if d.get("status") == "published")}


def check_channel(channel: Path, kenh_id: str, s: So) -> None:
    cfg_f = channel / "channel.yml"
    if not cfg_f.is_file():
        s.loi(f"{kenh_id}: thiếu channel.yml tại {channel}")
        return
    cfg = yaml.safe_load(cfg_f.read_text(encoding="utf-8")) or {}
    if cfg.get("id") != kenh_id:
        s.loi(f"{kenh_id}: channel.yml id={cfg.get('id')!r} ≠ id trong CHANNELS.md")
    if channel.name != kenh_id:
        s.nhac(f"{kenh_id}: tên thư mục {channel.name!r} khác id")
    pillars = cfg.get("pillars") or []
    nen_tang = {p.get("channel") for p in (cfg.get("platforms") or [])}

    so_f = channel / "CAMPAIGNS.md"
    if not so_f.is_file():
        s.loi(f"{kenh_id}: thiếu CAMPAIGNS.md")
        return
    _, body = md_io.read_fm(so_f)
    col, row = md_io.read_table(body, "CAMPAIGNS")
    trong_so = {d.get("campaign_id"): d for d in row}
    tren_dia = {c.name: c for c in SP.campaigns(channel)}

    for cid in set(trong_so) - set(tren_dia):
        s.loi(f"{kenh_id}: CAMPAIGNS.md có {cid!r} nhưng thư mục không tồn tại")
    for cid in set(tren_dia) - set(trong_so):
        s.loi(f"{kenh_id}: thư mục chiến dịch {cid!r} không có dòng trong CAMPAIGNS.md (mồ côi)")

    for cid, campaign in sorted(tren_dia.items()):
        result = check_campaign(campaign, kenh_id, pillars, nen_tang, s)
        d = trong_so.get(cid)
        if d:
            for cot_ten, that in (("bài", result["post"]), ("đã đăng", result["da_dang"])):
                if (d.get(cot_ten) or "").strip() not in ("", str(that)):
                    s.nhac(f"{kenh_id}: CAMPAIGNS.md ghi {cot_ten}={d[cot_ten]!r} cho {cid}, "
                           f"đếm thật là {that}")


def run_cmd(station=None, chi_kenh=None) -> So:
    s = So()
    ds = SP.channels(station)
    if not ds:
        s.nhac(f"không có kênh nào khai trong {SP.root(station) / 'CHANNELS.md'}")
        return s
    for c in ds:
        if chi_kenh and c.get("id") != chi_kenh:
            continue
        d = c.get("dir")
        if not d or not Path(d).is_dir():
            s.loi(f"{c.get('id')}: path {c.get('path')!r} không tồn tại "
                  f"(đã phân giải thành {d})")
            continue
        check_channel(Path(d), c.get("id", ""), s)
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm liên kết 4 tầng của STATION.")
    ap.add_argument("--station", default=None)
    ap.add_argument("--channel", default=None, help="chỉ kiểm một kênh")
    ap.add_argument("--strict", action="store_true", help="cảnh báo cũng tính là đỏ")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    s = run_cmd(a.station, a.channel)
    if a.json:
        print(json.dumps({"fail": s.do, "warn": s.canh_bao}, ensure_ascii=False, indent=2))
    else:
        for x in s.do:
            print(f"  ĐỎ   {x}")
        for x in s.canh_bao:
            print(f"  nhắc {x}")
        print(f"\n  {len(s.do)} đỏ · {len(s.canh_bao)} cảnh báo")
        # Hai công cụ, hai câu hỏi khác nhau — và không gộp có chủ đích: `check_tree` hỏi
        # "cây trạm có liền mạch không", `doctor` hỏi "bản CÀI có đủ để chạy không" (rào
        # của chế độ embedded, trạm giọng, trạm video). Gộp thì một lỗi cấu hình máy hiện
        # ra như một lỗi nội dung, và người đọc đi sửa nhầm chỗ.
        print("  (kiểm bản cài — rào, trạm giọng, trạm video: "
              "python scripts/pipeline/doctor.py)")
    return 1 if (s.do or (a.strict and s.canh_bao)) else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
