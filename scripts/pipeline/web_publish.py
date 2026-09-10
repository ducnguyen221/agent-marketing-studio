#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Đăng MỘT bài lên web. Đích đăng khai bằng cấu hình, không khoá cứng vào site nào.

Thay bước làm tay B8 trong `knowledge/toolchains/ATLAS_CHANNEL.md`:
chép file → chạy lệnh hậu kỳ → `git add` đích danh → commit → push → **kiểm HTTP 200**.

## Khai đích ở `channel.yml`

```yaml
web_target:
  kind: git_static                      # đợt này chỉ có một loại
  repo: ~/Code/<repo trang web>
  content_dir: content/{category}       # {category} lấy từ meta.json của bài
  base_url: https://vi-du.test/content
  post_cmd: node generate-manifest.js   # tuỳ chọn, chạy trong repo
  branch: main                          # tuỳ chọn
  verify: http_200                      # tuỳ chọn, mặc định bật
  files:                                # tuỳ chọn, đè bảng mặc định bên dưới
    atlas/atlas.html: "{slug}.html"
```

Không khai `web_target` mà gọi script này thì **DỪNG**. Đoán đích đăng nghĩa là bài rơi vào
một thư mục nào đó không ai tìm ra — im lặng, và chỉ lộ khi có người đi tìm bài.

## Vì sao kiểm 200 trước khi báo thành công

`git push` xong không có nghĩa trang đã lên: GitHub Pages dựng lại mất vài chục giây, và
build có thể hỏng. Ghi `blog_url` vào sổ trước khi kiểm là ghi một URL chết — nó chỉ lộ ra
hàng tuần sau, lúc không còn nhớ bài nào hỏng vì sao.

## Vì sao KHÔNG BAO GIỜ `git add -A`

Máy này chạy nhiều phiên agent cùng lúc. `-A` gom cả file của phiên khác vào commit của
mình. Đã trả giá một lần. Ở đây chỉ `git add` **đúng những đường dẫn vừa chép**.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_paths as SP  # noqa: E402

# Bảng mặc định: nguồn trong thư mục bài -> tên trên web. Thiếu nguồn TUỲ CHỌN thì bỏ qua;
# thiếu nguồn BẮT BUỘC thì dừng. Chỉ `.html` là bắt buộc — bài không có trang thì đăng gì.
FILE_MAC_DINH = {
    "atlas/atlas.html": "{slug}.html",           # bắt buộc
    "atlas/cover.jpg": "{slug}.jpg",
    "youtube/thumbnail.png": "{slug}.png",
    "atlas/audio.mp3": "{slug}.mp3",
    "facebook/infographic.png": "{slug}-1.png",  # ảnh THÂN BÀI, cố ý không trùng {slug}
}
BAT_BUOC = "atlas/atlas.html"


def loi(msg: str) -> None:
    sys.stderr.write(f"web_publish: {msg}\n")


def _doc_yaml(p: Path) -> dict:
    import yaml
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _chay(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _kiem_http(url: str, gia_lap: str | None) -> int:
    """Trả mã HTTP. `gia_lap` CHỈ dùng trong test — không dùng khi chạy thật."""
    if gia_lap:
        return int(gia_lap)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def dang(bai: Path, *, uat=False, dry_run=False, khong_push=False,
         gia_lap_http=None) -> int:
    bai = bai.resolve()
    if not bai.is_dir():
        loi(f"không thấy thư mục bài: {bai}")
        return 2

    # ── Cấu hình đích ───────────────────────────────────────────────────────
    kenh = SP.channel_of(bai)
    cfg = _doc_yaml(kenh / "channel.yml")
    wt = cfg.get("web_target")
    if not wt:
        loi(f"{kenh / 'channel.yml'}: thiếu khối `web_target` — không đoán đích đăng.\n"
            f"  Khai `web_target` (xem docstring của script này) rồi chạy lại.")
        return 2
    if wt.get("kind", "git_static") != "git_static":
        loi(f"web_target.kind={wt.get('kind')!r} chưa hỗ trợ. Đợt này chỉ có `git_static`.")
        return 2

    # ── Bài ─────────────────────────────────────────────────────────────────
    mp = bai / "meta.json"
    if not mp.is_file():
        loi(f"không thấy {mp}")
        return 2
    meta = json.loads(mp.read_text(encoding="utf-8"))
    slug = (meta.get("slug") or "").strip()
    cat = (meta.get("category") or "").strip()
    if not slug:
        loi(f"{mp}: thiếu `slug`.")
        return 2
    if not cat:
        loi(f"{mp}: thiếu `category`. Nó do `build_blog_html.py` quyết — chạy bước đó trước.")
        return 2

    # ── Nguồn -> đích ───────────────────────────────────────────────────────
    anh_xa = wt.get("files") or FILE_MAC_DINH
    cap = []
    for nguon_rel, mau in anh_xa.items():
        n = bai / nguon_rel
        if not n.is_file():
            if nguon_rel == BAT_BUOC:
                loi(f"thiếu file bắt buộc: {n}")
                return 2
            continue
        cap.append((n, mau.format(slug=slug, category=cat)))
    if not cap:
        loi("không có file nào để đăng.")
        return 2

    # ── UAT: chép ra nháp CẠNH BÀI, không đụng repo web ─────────────────────
    if uat:
        nhap = bai / ".uat-web" / cat
        nhap.mkdir(parents=True, exist_ok=True)
        for n, ten in cap:
            shutil.copy2(n, nhap / ten)
        print(json.dumps({"uat": True, "thu_muc": str(nhap),
                          "files": [t for _, t in cap]}, ensure_ascii=False))
        return 0

    repo = Path(os.path.expanduser(str(wt["repo"]))).resolve()
    if not (repo / ".git").is_dir():
        loi(f"{repo} không phải repo git.")
        return 2
    dich_rel = str(wt["content_dir"]).format(category=cat, slug=slug)
    dich = repo / dich_rel

    if dry_run:
        print(json.dumps({"dry_run": True, "dich": str(dich),
                          "files": [t for _, t in cap]}, ensure_ascii=False))
        return 0

    # ── Chép ────────────────────────────────────────────────────────────────
    dich.mkdir(parents=True, exist_ok=True)
    da_chep = []
    for n, ten in cap:
        shutil.copy2(n, dich / ten)
        da_chep.append(f"{dich_rel}/{ten}".replace("\\", "/"))

    # ── Lệnh hậu kỳ (sinh manifest, build index…) ───────────────────────────
    if wt.get("post_cmd"):
        r = _chay(str(wt["post_cmd"]).split(), repo)
        if r.returncode != 0:
            loi(f"post_cmd thất bại: {wt['post_cmd']}\n{r.stdout}{r.stderr}")
            return 3
        # Lệnh hậu kỳ thường sửa thêm file (manifest). Thêm ĐÍCH DANH những file nó khai.
        for d in (wt.get("post_cmd_outputs") or []):
            da_chep.append(str(d))

    # ── git: add ĐÍCH DANH, không bao giờ gom cả cây ─────────────────────────
    r = _chay(["git", "add", "--", *da_chep], repo)
    if r.returncode != 0:
        loi(f"git add thất bại:\n{r.stdout}{r.stderr}")
        return 3
    r = _chay(["git", "commit", "-m", f"post: {slug}"], repo)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        loi(f"git commit thất bại:\n{r.stdout}{r.stderr}")
        return 3

    if not khong_push:
        nhanh = wt.get("branch") or "main"
        r = _chay(["git", "push", "origin", nhanh], repo)
        if r.returncode != 0:
            loi(f"git push thất bại:\n{r.stdout}{r.stderr}")
            return 3

    # ── Kiểm 200 TRƯỚC khi báo thành công ───────────────────────────────────
    url = f"{str(wt['base_url']).rstrip('/')}/{cat}/{slug}.html"
    if wt.get("verify", "http_200") == "http_200":
        ma = _kiem_http(url, gia_lap_http)
        if ma != 200:
            loi(f"đăng xong nhưng {url} trả HTTP {ma} — KHÔNG ghi sổ.\n"
                f"  Trang tĩnh cần vài chục giây để dựng lại; chạy lại bước kiểm sau ít phút.")
            return 4

    print(json.dumps({"blog_url": url, "category": cat,
                      "files": da_chep}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Đăng một bài lên web (đích khai bằng cấu hình).")
    ap.add_argument("--bai", required=True, help="thư mục bài")
    ap.add_argument("--uat", action="store_true",
                    help="chép ra .uat-web/ cạnh bài, KHÔNG đụng repo web")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in ra sẽ làm gì")
    ap.add_argument("--khong-push", action="store_true", help="commit nhưng không push")
    ap.add_argument("--gia-lap-http", default=None,
                    help="CHỈ DÙNG TRONG TEST — ép mã HTTP thay vì gọi mạng thật")
    a = ap.parse_args()
    return dang(Path(a.bai), uat=a.uat, dry_run=a.dry_run,
                khong_push=a.khong_push, gia_lap_http=a.gia_lap_http)


if __name__ == "__main__":
    sys.exit(main())
