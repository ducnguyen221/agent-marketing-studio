#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo bài mới trong một chiến dịch: thư mục + meta.json + research.md + content.md,
rồi thêm dòng vào bảng Content của campaign.md. Một bài, hoặc cả loạt bằng --bulk.

Bài sinh ra ở trạng thái `proposed`. **Script không tự đặt `approved`** — Cổng 1 là của
người. Ô `g1` để trống cho tới khi người điền ngày.

═══ HỢP ĐỒNG ĐỌC — agent viết bài PHẢI đọc đủ ba thứ trước khi viết một chữ ═══
  1. `campaign.md` của chiến dịch  — bài toán kinh doanh, đối tượng, thông điệp, trụ nội
     dung, và MỤC "KHÔNG LÀM". Bài không bám chiến dịch là bài lạc.
  2. `profile.md` của kênh         — tác giả là ai, giọng gì, chính kiến gì, không bao giờ
     viết gì. Đọc KHÔNG ĐƯỢC thì DỪNG, đừng viết với chính kiến rỗng.
  3. `research.md` của CHÍNH bài đó — mục tiêu nghiên cứu và nguồn của riêng bài này.
Script chặn ở (1): campaign.md còn chữ mẫu là không đẻ bài. (2) và (3) là kỷ luật của
bước viết — blog_gates bắt hậu quả (G05 nguồn, G11 giọng), không bắt được việc có đọc hay
không. Vì vậy nó nằm ở đây, thành chữ, để agent nào mở script cũng thấy.

--bulk: tạo NHIỀU bài một lượt từ file TSV. Đọc chiến dịch + hồ sơ MỘT LẦN rồi nghiên cứu
và viết cả loạt, thay vì lặp lại vòng đọc cho từng bài.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import post_paths as PP  # noqa: E402
import studio_paths as SP  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TPL = REPO / "templates"


# Trường BẮT BUỘC phải điền xong trong campaign.md trước khi đẻ bài đầu tiên.
# Vì sao chặn ở đây: bài viết ra từ một chiến dịch chưa rõ đối tượng và thông điệp thì
# viết xong mới biết lệch, và lúc đó đã tốn cả vòng nghiên cứu + dựng tiếng + dựng hình.
# Chặn ở khâu tạo rẻ hơn nhiều.
BAT_BUOC = ["business_problem", "campaign_goal", "target_audience", "audience_pain_points",
            "key_message", "content_pillar", "channels", "primary_cta"]

# Trường CHỌN TỪ DANH SÁCH: mẫu chọn sẵn một giá trị hợp lệ, nên trùng mẫu KHÔNG có nghĩa
# là chưa điền. Kiểm chúng bằng "có giá trị" thôi (riêng content_pillar so với channel.yml).
CHON_TU_DANH_SACH = {"channels", "primary_cta", "content_pillar"}


def _gia_tri_mau() -> dict:
    """Đọc giá trị mẫu THẲNG TỪ `templates/campaign.md`.

    Bản trước so với một danh sách chuỗi chép tay, nên chỉ bắt được 3 trong 8 trường:
    `campaign_goal: "Kết quả mong muốn, đo được"` lọt qua và bài vẫn đẻ ra từ một chiến
    dịch rỗng. Chép tay thì template đổi một chữ là cổng mù, mà không gì báo.
    """
    try:
        fm, _ = md_io.read_fm(TPL / "campaign.md")
        return {k: (v.strip() if isinstance(v, str) else v) for k, v in fm.items()}
    except Exception:      # noqa: BLE001 — thiếu template thì cổng vẫn phải chạy được
        return {}


def _campaign_da_du(fm: dict, pillars: list | None = None) -> list[str]:
    """Trả về danh sách trường CHƯA điền. Rỗng = đủ.

    Hai loại trường, kiểm khác nhau — gộp một luật là sai một trong hai chiều:

    · **Văn xuôi** (`business_problem`, `key_message`…): giá trị mẫu là câu MÔ TẢ CHỖ CẦN
      ĐIỀN ("Kết quả mong muốn, đo được"). Trùng mẫu = chưa điền, chắc chắn.
    · **Chọn từ danh sách** (`channels`, `primary_cta`): mẫu chọn sẵn một giá trị HỢP LỆ.
      Một chiến dịch đăng cả ba kênh thì `channels` trùng mẫu là câu trả lời THẬT — bắt lỗi
      ở đây là cổng kêu oan, mà cổng kêu oan thì người ta tắt cổng.
      Với `content_pillar`, phép thử đúng là **có nằm trong `pillars` của kênh không**.
    """
    mau = _gia_tri_mau()
    thieu = []
    for k in BAT_BUOC:
        v = fm.get(k)
        if v is None or v == "" or v == []:
            thieu.append(k)
            continue
        vs = v.strip() if isinstance(v, str) else v
        if isinstance(vs, str) and "{{" in vs:
            thieu.append(k + " (còn chữ mẫu)")
        elif k == "content_pillar":
            if pillars and vs not in pillars:
                thieu.append(f"content_pillar={vs!r} không có trong pillars của kênh {pillars}")
            elif not pillars and k in mau and vs == mau[k]:
                thieu.append(k + " (còn nguyên giá trị mẫu)")
        elif k not in CHON_TU_DANH_SACH and k in mau and vs == mau[k]:
            thieu.append(k + " (còn nguyên giá trị mẫu)")
    return thieu


# Ba cột cuối giữ URL THẬT sau khi đăng — register_publish ghi vào. Đây là chỗ mở lại bài
# mà không phải đi lục từng publish.json.
COT = ["content_id", "content_name", "pillar", "angle", "funnel", "priority",
       "status", "g1", "g2", "schedule", "published", "folder",
       "web", "youtube", "facebook"]


def _tim_campaign(chi_dinh: str, station=None) -> Path:
    p = Path(chi_dinh)
    if (p / "campaign.md").is_file():
        return p.resolve()
    for c in SP.channels(station):
        q = c["dir"] / chi_dinh
        if (q / "campaign.md").is_file():
            return q.resolve()
    raise FileNotFoundError(f"không tìm ra chiến dịch {chi_dinh!r} — truyền đường dẫn "
                            f"hoặc id có trong một kênh của CHANNELS.md")


def _bulk(a, cam_dir: Path, fm_cam: dict) -> int:
    """Tạo cả loạt bài từ TSV. Đọc trước TOÀN BỘ file và kiểm hết trước khi tạo bất kỳ thư
    mục nào: nửa loạt thành công nửa loạt lỗi là trạng thái khó dọn nhất."""
    dong_tsv = []
    for i, ln in enumerate(Path(a.bulk).read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        o = [x.strip() for x in ln.split("\t")]
        if len(o) < 3:
            sys.stderr.write(f"{a.bulk}:{i} cần ít nhất id<TAB>slug<TAB>title\n")
            return 2
        dong_tsv.append((o[0], o[1], o[2], o[3] if len(o) > 3 else ""))

    prefix = fm_cam.get("id_prefix", "")
    _, dong_co = md_io.read_table(md_io.read_fm(cam_dir / "campaign.md")[1], "CONTENT")
    da_co = {d.get("content_id") for d in dong_co}
    loi = []
    for cid, slug, _t, _g in dong_tsv:
        if prefix and not cid.startswith(prefix + "-"):
            loi.append(f"{cid} không khớp id_prefix {prefix!r}")
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            loi.append(f"slug {slug!r} phải a-z0-9-")
        if (cam_dir / f"{cid}_{slug}").exists():
            loi.append(f"{cid}_{slug} đã có — không ghi đè")
        if cid in da_co:
            loi.append(f"{cid} đã có trong bảng Content — không ghi đè dòng cũ")
    if len({c for c, *_ in dong_tsv}) != len(dong_tsv):
        loi.append("có content_id trùng nhau trong file")
    if loi:
        sys.stderr.write("KHÔNG tạo bài nào — sửa hết rồi chạy lại:\n  · "
                         + "\n  · ".join(loi) + "\n")
        return 2

    if a.dry_run:
        print(f"  [dry-run] sẽ tạo {len(dong_tsv)} bài trong {cam_dir}")
        return 0

    for cid, slug, tieu_de, goc in dong_tsv:
        con = argparse.Namespace(**vars(a))
        con.bulk, con.id, con.slug, con.title = None, cid, slug, tieu_de
        con.angle = goc or a.angle
        rc = main([x for x in _lai_argv(con)])
        if rc != 0:
            sys.stderr.write(f"dừng ở {cid} (đã tạo {dong_tsv.index((cid, slug, tieu_de, goc))} bài)\n")
            return rc
    print(f"  đã tạo {len(dong_tsv)} bài. Agent viết bài: đọc campaign.md + profile.md "
          f"của kênh + research.md của TỪNG bài trước khi viết.")
    return 0


def _lai_argv(n) -> list[str]:
    """Dựng lại argv cho một bài — đi qua đúng main() để không có hai đường tạo bài."""
    v = ["--campaign", n.campaign, "--id", n.id, "--slug", n.slug, "--title", n.title,
         "--funnel", n.funnel, "--priority", n.priority, "--audio", n.audio,
         "--video", n.video, "--short", n.short, "--bo-qua-cong"]
    for c, x in (("--pillar", n.pillar), ("--angle", n.angle), ("--schedule", n.schedule),
                 ("--station", n.station)):
        if x:
            v += [c, str(x)]
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tạo bài mới trong một chiến dịch.")
    ap.add_argument("--campaign", required=True, help="đường dẫn thư mục chiến dịch, hoặc id")
    ap.add_argument("--id", help="content_id, vd AST-002 (bỏ qua nếu dùng --bulk)")
    ap.add_argument("--slug")
    ap.add_argument("--title")
    ap.add_argument("--bulk", help="file TSV: id<TAB>slug<TAB>title[<TAB>angle] — mỗi dòng một bài")
    ap.add_argument("--pillar", default="")
    ap.add_argument("--angle", default="")
    ap.add_argument("--funnel", default="awareness")
    ap.add_argument("--priority", default="medium")
    ap.add_argument("--schedule", default="")
    ap.add_argument("--audio", default="yes", choices=["yes", "no"])
    ap.add_argument("--video", default="yes", choices=["yes", "no"])
    ap.add_argument("--short", default="no", choices=["yes", "no"])
    ap.add_argument("--station", default=None)
    ap.add_argument("--bo-qua-cong", action="store_true",
                    help="bỏ chặn campaign.md chưa đủ thông tin (biết mình làm gì)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not a.bulk and not (a.id and a.slug and a.title):
        sys.stderr.write("cần --id --slug --title, hoặc --bulk <file.tsv>\n")
        return 2
    if a.slug and not re.fullmatch(r"[a-z0-9-]+", a.slug):
        sys.stderr.write(f"--slug phải a-z0-9-: {a.slug!r}\n")
        return 2
    try:
        cam_dir = _tim_campaign(a.campaign, a.station)
    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        return 2

    fm_cam, body_cam = md_io.read_fm(cam_dir / "campaign.md")

    # pillars của kênh: phép thử đúng cho content_pillar. Đọc được thì dùng; không đọc
    # được (kênh lạ, file hỏng) thì lùi về so với mẫu — cổng không được TẮT vì thiếu dữ liệu.
    pillars = None
    try:
        import yaml
        for c in SP.channels(a.station):
            if (c["dir"] / "channel.yml").is_file() and cam_dir.is_relative_to(c["dir"]):
                pillars = (yaml.safe_load((c["dir"] / "channel.yml").read_text(encoding="utf-8"))
                           or {}).get("pillars")
                break
    except Exception:      # noqa: BLE001
        pillars = None

    thieu = _campaign_da_du(fm_cam, pillars)
    if thieu and not a.bo_qua_cong:
        sys.stderr.write("\n".join([
            "campaign.md CHƯA ĐỦ THÔNG TIN — chưa tạo bài được.",
            "Thiếu: " + ", ".join(thieu),
            "",
            "Điền xong hãy tạo bài. Agent và người cùng hoàn thiện campaign.md trước:",
            "  · frontmatter — brief một câu (thứ mọi bài trong chiến dịch bám vào)",
            "  · Mục 1-3      — bối cảnh, đối tượng, thông điệp (bản dài)",
            "  · Mục 4        — trụ nội dung và CÁI KHÔNG LÀM",
            "",
            "Biết mình đang làm gì thì --bo-qua-cong bỏ chặn này.",
            ""]))
        return 2

    if a.bulk:
        return _bulk(a, cam_dir, fm_cam)

    prefix = fm_cam.get("id_prefix", "")
    if prefix and not a.id.startswith(prefix + "-"):
        sys.stderr.write(f"--id {a.id!r} không khớp id_prefix {prefix!r} của chiến dịch\n")
        return 2

    # content_id đã có trong bảng = bài đã tồn tại, dù slug khác. Trước bản vá này chỉ kiểm
    # THƯ MỤC, nên `--id THU-001 --slug b` khi THU-001 đang `approved` sẽ ghi đè dòng đó về
    # `proposed` với ô g1 rỗng: MÁY XOÁ quyết định của NGƯỜI ở Cổng 1, và không báo gì.
    _, dong_co = md_io.read_table(body_cam, "CONTENT")
    if any(d.get("content_id") == a.id for d in dong_co):
        sys.stderr.write(f"{a.id} đã có trong bảng Content của {cam_dir.name} — dừng.\n"
                         f"Đổi --id, hoặc sửa thẳng dòng đó trong campaign.md.\n")
        return 2

    dich = cam_dir / f"{a.id}_{a.slug}"
    if dich.exists():
        sys.stderr.write(f"đã có {dich} — dừng, không ghi đè\n")
        return 2
    if a.dry_run:
        print(f"  [dry-run] sẽ tạo {dich} và thêm dòng vào {cam_dir / 'campaign.md'}")
        return 0

    PP.tao_thu_muc(dich)

    # meta.json — định danh máy đọc. Giữ đúng hình dạng đang chạy.
    cat = {"powerbi": "bi", "fabric": "de", "ai-agent": "ai", "career": "strategy"}
    pillar = a.pillar or fm_cam.get("content_pillar", "")
    json.dump({
        "post_id": a.id, "campaign_id": fm_cam.get("id", ""),
        "title": a.title, "slug": a.slug,
        "pillar": pillar, "category": cat.get(pillar, "ai"),
        "angle": a.angle, "schedule_date": a.schedule,
        "hashtags": [],
    }, (dich / "meta.json").open("w", encoding="utf-8", newline="\n"),
        ensure_ascii=False, indent=2)

    # research.md — frontmatter mang brief chi tiết
    shutil.copy2(TPL / "research.md", PP.p(dich, "research"))
    fm_r, body_r = md_io.read_fm(PP.p(dich, "research"))
    fm_r.update({"content_id": a.id, "campaign_id": fm_cam.get("id", ""),
                 "audio": a.audio, "video": a.video, "short": a.short})
    body_r = body_r.replace("# research.md — XXX-001 · Tên bài",
                            f"# research.md — {a.id} · {a.title}")
    md_io.write_fm(PP.p(dich, "research"), fm_r, body_r)

    # content.md
    shutil.copy2(TPL / "content.md", PP.p(dich, "content"))
    fm_c, body_c = md_io.read_fm(PP.p(dich, "content"))
    fm_c.update({"content_id": a.id, "campaign_id": fm_cam.get("id", ""),
                 "content_name": a.title})
    md_io.write_fm(PP.p(dich, "content"), fm_c, body_c)

    # dòng trong bảng Content — status=proposed, g1 TRỐNG (Cổng 1 là của người)
    body_cam = md_io.upsert_row(body_cam, "CONTENT", "content_id", {
        "content_id": a.id, "content_name": a.title, "pillar": pillar,
        "angle": a.angle, "funnel": a.funnel, "priority": a.priority,
        "status": "proposed", "g1": "", "g2": "",
        "schedule": a.schedule, "published": "", "folder": f"./{dich.name}/"}, COT)
    md_io.write_fm(cam_dir / "campaign.md", fm_cam, body_cam)

    print(f"  bài  : {dich}")
    print(f"  sổ   : {cam_dir / 'campaign.md'} (bảng Content, status=proposed)")
    print(f"  ⚠️ Cổng 1 là của NGƯỜI: điền status=approved và ngày vào ô g1 rồi mới viết bài.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
