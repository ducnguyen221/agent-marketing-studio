# -*- coding: utf-8 -*-
"""`scripts/pipeline/web_publish.py` — đăng một bài lên web, đích khai bằng cấu hình.

Thay bước làm tay B8 (chép file → generate-manifest → git add → push → kiểm 200).

Mỗi test dưới đây chặn một cách hỏng đã biết:

· **Đoán đích đăng** — thiếu `web_target` mà vẫn chạy thì bài rơi vào một thư mục nào đó
  không ai tìm ra. Phải dừng.
· **`git add -A`** — máy chạy nhiều phiên agent cùng lúc; `-A` cướp file của phiên khác vào
  commit của mình. Đã trả giá một lần.
· **Ghi sổ URL chết** — push xong không có nghĩa là trang đã lên. Không kiểm 200 trước khi
  báo thành công thì `blog_url` trong sổ trỏ vào 404, và chỉ lộ ra hàng tuần sau.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WP = ROOT / "scripts" / "pipeline" / "web_publish.py"


def _tram(tmp_path, *, web_target=True, co_html=True, category="ai"):
    """Trạm tối thiểu: 1 kênh + 1 chiến dịch + 1 bài đã dựng xong asset."""
    channel = tmp_path / "tram" / "kenh-thu"
    post = channel / "cd-thu" / "T-001_bai-thu"
    (post / "atlas").mkdir(parents=True)

    cy = ["schema: channel/1", "id: kenh-thu", 'label: "K"',
          "platforms:", "  - channel: web_blog", "    post_formats: [blog_article]"]
    if web_target:
        cy += ["web_target:",
               "  kind: git_static",
               f"  repo: {(tmp_path / 'web').as_posix()}",
               "  content_dir: content/{category}",
               "  base_url: https://vi-du.test/content",
               "  verify: http_200"]
    (channel / "channel.yml").write_text("\n".join(cy) + "\n", encoding="utf-8")

    meta = {"post_id": "T-001", "slug": "bai-thu", "title": "Bài thử", "pillar": "ai-agent"}
    if category is not None:
        meta["category"] = category
    (post / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    if co_html:
        (post / "atlas" / "atlas.html").write_text("<h1>Bài thử</h1>", encoding="utf-8")
    return post


def _repo_web(tmp_path):
    """Repo đích thật (git init) — để `git add` đích danh kiểm được."""
    w = tmp_path / "web"
    w.mkdir(parents=True, exist_ok=True)
    for c in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", *c], cwd=w, capture_output=True)
    (w / "san-co.txt").write_text("file cua nguoi khac", encoding="utf-8")
    return w


def _chay(post, *add):
    return subprocess.run([sys.executable, str(WP), "--post", str(post), *add],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


# ── Fail-closed ─────────────────────────────────────────────────────────────

def test_thieu_web_target_thi_dung_han_khong_doan(tmp_path):
    post = _tram(tmp_path, web_target=False)
    r = _chay(post, "--dry-run")
    assert r.returncode != 0, "thiếu web_target mà vẫn chạy — sẽ đoán đích đăng"
    assert "web_target" in (r.stdout + r.stderr)


def test_thieu_category_thi_dung_han(tmp_path):
    """`category` do `build_blog_html.py` quyết. Thiếu = chưa chạy bước đó."""
    post = _tram(tmp_path, category=None)
    r = _chay(post, "--dry-run")
    assert r.returncode != 0
    assert "category" in (r.stdout + r.stderr)


def test_thieu_file_nguon_thi_dung_TRUOC_khi_dung_repo_dich(tmp_path):
    w = _repo_web(tmp_path)
    post = _tram(tmp_path, co_html=False)
    r = _chay(post, "--dry-run")
    assert r.returncode != 0
    assert not list((w / "content").rglob("*")) if (w / "content").exists() else True


# ── git add đích danh ───────────────────────────────────────────────────────

def test_khong_bao_gio_git_add_tat_ca(tmp_path):
    """`git add -A` cướp file của phiên agent khác vào commit của mình."""
    source = WP.read_text(encoding="utf-8")
    for xau in ('"-A"', "'-A'", '"--all"', "'--all'", '"."]'):
        assert xau not in source, f"web_publish.py có {xau} trong lệnh git — cấm"


def test_dry_run_khong_dung_gi_vao_repo(tmp_path):
    w = _repo_web(tmp_path)
    post = _tram(tmp_path)
    r = _chay(post, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    con = subprocess.run(["git", "status", "--porcelain"], cwd=w,
                         capture_output=True, text=True).stdout
    assert "content/" not in con, f"dry-run mà đã chép file vào repo: {con}"


# ── Verify HTTP 200 ─────────────────────────────────────────────────────────

def test_khong_200_thi_that_bai_va_KHONG_in_blog_url(tmp_path):
    """Ghi sổ một URL chết còn tệ hơn báo lỗi: nó lộ ra hàng tuần sau."""
    _repo_web(tmp_path)
    post = _tram(tmp_path)
    r = _chay(post, "--no-push", "--fake-http", "404")
    assert r.returncode != 0, "404 mà vẫn báo thành công"
    assert "blog_url" not in r.stdout, "in blog_url dù trang chưa lên"


def test_200_thi_in_blog_url_dung_dinh_dang(tmp_path):
    _repo_web(tmp_path)
    post = _tram(tmp_path)
    r = _chay(post, "--no-push", "--fake-http", "200")
    assert r.returncode == 0, r.stdout + r.stderr
    ra = json.loads([d for d in r.stdout.splitlines() if d.startswith("{")][-1])
    assert ra["blog_url"] == "https://vi-du.test/content/ai/bai-thu.html"


def test_file_duoc_chep_dung_cho(tmp_path):
    w = _repo_web(tmp_path)
    post = _tram(tmp_path)
    r = _chay(post, "--no-push", "--fake-http", "200")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (w / "content" / "ai" / "bai-thu.html").is_file()


def test_uat_khong_push_va_khong_doi_nhanh_chinh(tmp_path):
    w = _repo_web(tmp_path)
    post = _tram(tmp_path)
    r = _chay(post, "--uat")
    assert r.returncode == 0, r.stdout + r.stderr
    lich = subprocess.run(["git", "log", "--oneline"], cwd=w,
                          capture_output=True, text=True).stdout
    assert not lich.strip(), f"UAT mà đã commit vào repo web: {lich}"
