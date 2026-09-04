#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo MỘT kênh mới và ghi địa chỉ nó vào CHANNELS.md.

⚠️ `--path` KHÔNG CÓ GIÁ TRỊ MẶC ĐỊNH, và đó là chủ ý.

Chỗ lưu kênh là quyết định của người, không phải của máy: kênh có thể cần nằm trên ổ khác,
trong thư mục công ty, hay trong một kho được đồng bộ riêng. Agent đoán hộ rồi tạo ra một
cây thư mục ở chỗ người dùng không ngờ tới là bắt họ đi dọn.

Thiếu `--path` → exit 3 và in ra đúng câu cần hỏi. Agent gặp mã 3 thì HỎI NGƯỜI DÙNG,
không tự chọn.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import studio_paths as SP  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TPL = REPO / "templates"

CAU_HOI = """Chưa biết lưu kênh ở đâu.

HỎI NGƯỜI DÙNG: "Anh muốn lưu kênh này ở đâu?"
  · trong STATION  → --path ./<ten-kenh>
  · nơi khác       → --path "D:/duong/dan/rieng"   (kênh KHÔNG bắt buộc nằm trong STATION;
                                                     CHANNELS.md sẽ giữ địa chỉ)
Đừng tự chọn hộ."""


PLATFORM_HOP_LE = {"web_blog", "youtube", "facebook"}


def _loc_platforms(yml: str, giu: list[str]) -> str:
    """Bỏ khỏi `channel.yml` những mục `- channel: X` không nằm trong `giu`.

    Cắt theo dòng, không dùng thư viện YAML: `yaml.safe_dump` sẽ **xoá sạch chú thích**, mà
    chú thích trong file này chính là phần giải thích vì sao mỗi trường tồn tại — thứ người
    mở file ra cần đọc nhất.
    """
    ra, bo = [], False
    for d in yml.splitlines():
        if d.startswith("  - channel:"):
            bo = d.split(":", 1)[1].strip() not in giu
        elif bo and d and not d[0].isspace():
            bo = False          # hết khối platforms
        if not bo:
            ra.append(d)
    return "\n".join(ra) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tạo kênh mới.")
    ap.add_argument("--id", required=True, help="a-z0-9- ; cũng là tên thư mục")
    ap.add_argument("--label", required=True)
    ap.add_argument("--path", default=None, help="BẮT BUỘC — hỏi người dùng, đừng đoán")
    ap.add_argument("--station", default=None)
    ap.add_argument("--platforms", default="web_blog,youtube,facebook",
                    help="nền tảng kênh này đăng, phân tách bằng dấu phẩy")
    ap.add_argument("--home-domain", default="")
    ap.add_argument("--owner", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not a.path:
        sys.stderr.write(CAU_HOI + "\n")
        return 3
    if not a.id.replace("-", "").isalnum() or a.id != a.id.lower():
        sys.stderr.write(f"--id phải là a-z0-9- viết thường: {a.id!r}\n")
        return 2

    # resolve() cả hai vế: nếu không, relative_to() bên dưới trượt và CHANNELS.md ghi
    # đường TUYỆT ĐỐI cho một kênh vốn nằm ngay trong STATION — chép STATION sang máy khác
    # là đường đó chết.
    station = SP.root(a.station).resolve()
    dich = Path(a.path).expanduser()
    dich = dich.resolve() if dich.is_absolute() else (station / a.path).resolve()
    if (dich / "channel.yml").exists():
        sys.stderr.write(f"đã có kênh ở {dich} — dừng, không ghi đè\n")
        return 2

    if a.dry_run:
        print(f"  [dry-run] sẽ tạo {dich} và thêm dòng vào {station / 'CHANNELS.md'}")
        return 0

    # --- thư mục kênh
    # Thư mục kênh chỉ có FILE PHẲNG + các thư mục chiến dịch. profile/ và memory/ trước
    # đây mỗi cái chứa đúng MỘT file — lồng thêm một cấp chỉ để phải bấm thêm một lần.
    dich.mkdir(parents=True, exist_ok=True)
    (dich / "continuity.json").write_text("[]\n", encoding="utf-8", newline="\n")

    yml = (TPL / "channel.yml").read_text(encoding="utf-8")
    yml = (yml.replace("id: ten-kenh", f"id: {a.id}")
              .replace('label: "Tên kênh đọc được"', f'label: "{a.label}"')
              .replace("created: 2026-01-01", f"created: {date.today()}"))
    if a.home_domain:
        yml = yml.replace("home_domain: example.vn", f"home_domain: {a.home_domain}")
    if a.owner:
        yml = yml.replace('owner: "Người phụ trách"', f'owner: "{a.owner}"')

    # --platforms: trước bản vá này CỜ NÀY BỊ BỎ QUA HOÀN TOÀN — người dùng khai
    # `--platforms web_blog` rồi nhận về một channel.yml có đủ ba nền tảng, không ai báo.
    # Cờ khai ra mà không làm gì tệ hơn không có cờ: nó nói dối về việc mình đã làm.
    chon = [x.strip() for x in a.platforms.split(",") if x.strip()]
    la = [x for x in chon if x not in PLATFORM_HOP_LE]
    if la:
        sys.stderr.write(f"--platforms có giá trị lạ: {la}. Hợp lệ: "
                         f"{', '.join(sorted(PLATFORM_HOP_LE))}\n")
        return 2
    if set(chon) != PLATFORM_HOP_LE:
        yml = _loc_platforms(yml, chon)
    (dich / "channel.yml").write_text(yml, encoding="utf-8", newline="\n")

    cam = (TPL / "CAMPAIGNS.md").read_text(encoding="utf-8")
    cam = (cam.replace("channel: ten-kenh", f"channel: {a.id}")
              .replace("updated: 2026-01-01", f"updated: {date.today()}")
              .replace("# Sổ chiến dịch — Tên kênh", f"# Sổ chiến dịch — {a.label}"))
    (dich / "CAMPAIGNS.md").write_text(cam, encoding="utf-8", newline="\n")

    if not (dich / "profile.md").exists():
        (dich / "profile.md").write_text(
            "# Hồ sơ kênh — giọng, tác phong, chính kiến\n\n"
            "> MỘT file cho toàn bộ hồ sơ của kênh: tác giả là ai, viết cho ai, giọng thế nào,\n"
            "> phân tích một chủ đề theo lăng kính gì, câu nào hay dùng, điều gì không bao giờ viết.\n"
            ">\n"
            "> Chứa thông tin cá nhân và tổ chức thật — **không bao giờ vào repo**.\n"
            ">\n"
            "> Bước viết bài đọc file này **FAIL-CLOSED**: đọc không được thì DỪNG, không viết\n"
            "> tiếp với chính kiến rỗng. Ba bài đầu của một kênh cũ từng viết với chính kiến\n"
            "> rỗng suốt mà không ai biết, vì tham số là optional và script im lặng chạy tiếp.\n\n"
            "## Ai là tác giả\n\n## Viết cho ai\n\n## Cách phân tích một chủ đề\n\n"
            "## Giọng và chính kiến\n\n## Không bao giờ viết\n",
            encoding="utf-8", newline="\n")

    # --- ghi vào sổ kênh
    so = station / "CHANNELS.md"
    if not so.exists():
        station.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TPL / "CHANNELS.md", so)
        fm, body = md_io.read_fm(so)
        fm["channels"] = []
        body = body.replace("## ten-kenh\nKênh này của ai, đăng ở đâu, vì sao tách riêng.\n", "")
        md_io.write_fm(so, fm, body)

    fm, body = md_io.read_fm(so)
    ds = [c for c in (fm.get("channels") or []) if c.get("id") != a.id]
    try:
        p_ghi = "./" + str(dich.relative_to(station)).replace("\\", "/")
    except ValueError:
        p_ghi = str(dich).replace("\\", "/")      # kênh nằm NGOÀI station -> đường tuyệt đối
    ds.append({"id": a.id, "label": a.label, "path": p_ghi, "status": "active", "note": ""})
    fm["channels"] = ds
    fm["updated"] = str(date.today())
    md_io.write_fm(so, fm, body)

    print(f"  kênh   : {dich}")
    print(f"  sổ kênh: {so}  ({len(ds)} kênh)")
    print(f"  tiếp   : new_campaign.py --channel {a.id} --id CMP-YYMM-slug --name \"…\" --prefix XXX")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
