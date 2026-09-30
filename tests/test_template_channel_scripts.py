# -*- coding: utf-8 -*-
"""Khuôn script cấp kênh (`templates/station/_channel/`) — ba lệch do nghiệm thu Mac 1.1.0 tìm ra.

· **P1-15** `send_newsletter.py`: `_cfg()` chỉ chép `script_url/site_base/repo` từ
  `channel.yml:brand`, trong khi `_build_email` đọc `a`, `b`, `email_accent`, `gh_repo` ⇒ thư
  gửi ra "From:  <…>", tiêu đề không tên kênh, mất link video trong Release.
· **P2-19** `build-index.ps1`: gradient nút đăng ký, nhịp sáng và chữ "đã đăng ký" ghi cứng
  `#00f0ff/#39ff7a` ⇒ kênh có bộ màu khác không dùng được khuôn. Nay qua `web_cta_from` /
  `web_cta_to`; KHÔNG khai thì trang ra y hệt trước.
· **P1-16 (cùng họ)** regex đường dẫn chỉ khớp `\\` ⇒ trên macOS khớp 0 file, index dựng RỖNG
  rồi `git push`. Cổng dưới giữ mọi regex đường dẫn trong khuôn nhận cả `\\` lẫn `/`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KHUON = ROOT / "templates" / "station" / "_channel"
PS = shutil.which("powershell") or shutil.which("pwsh")


# ── P1-15: thư gửi ra mang đúng tên kênh ─────────────────────────────────────────────

def _nap_newsletter(tmp_path, monkeypatch, channel_yml: str):
    kenh = tmp_path / "kenh-thu"
    kenh.mkdir()
    shutil.copy(KHUON / "send_newsletter.py", kenh / "send_newsletter.py")
    (kenh / "channel.yml").write_text(channel_yml, encoding="utf-8")
    bi_mat = tmp_path / "email-config.json"
    bi_mat.write_text(json.dumps({"secret": "s", "smtp_user": "gui@example.com",
                                  "smtp_app_password": "x"}), encoding="utf-8")
    monkeypatch.setenv("EMAIL_CONFIG", str(bi_mat))
    spec = importlib.util.spec_from_file_location("send_newsletter_thu", kenh / "send_newsletter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BAN_TIN = {"week": "39", "range": "22/09 – 28/09", "tldr": "tóm tắt",
           "items": [{"hot_rank": 1, "title": "Tin nóng nhất", "url": "https://example.com/1"}]}


def test_newsletter_chep_DU_khoa_nhan_dien_tu_channel_yml(tmp_path, monkeypatch):
    mod = _nap_newsletter(tmp_path, monkeypatch, (
        "id: kenh-thu\n"
        "theme:\n  email_accent: \"#123456\"\n"
        "brand:\n  a: Kenh\n  b: Thu\n  gh_repo: chu/kho\n"
        "  site_base: https://example.com/news\n  script_url: https://example.com/s\n"))
    cfg = mod._cfg()
    assert (cfg["a"], cfg["b"], cfg["gh_repo"], cfg["email_accent"]) == \
        ("Kenh", "Thu", "chu/kho", "#123456"), cfg
    msg = mod._build_email(cfg, "2026-09-26", "2026/09/w39.html", BAN_TIN, "nhan@example.com")
    assert msg["From"] == "Kenh Thu <gui@example.com>", msg["From"]
    assert msg["Subject"].startswith("Kenh Thu tuần 39"), msg["Subject"]
    html = msg.get_body(("html",)).get_content()
    assert "https://github.com/chu/kho/releases/download/media-2026-09-26/2026-09-26.mp4" in html
    assert "color:#123456" in html


def test_newsletter_email_accent_trong_brand_THANG_theme(tmp_path, monkeypatch):
    mod = _nap_newsletter(tmp_path, monkeypatch, (
        "id: kenh-thu\ntheme:\n  email_accent: \"#111111\"\n"
        "brand:\n  a: Kenh\n  b: Thu\n  email_accent: \"#222222\"\n"
        "  site_base: https://example.com/news\n"))
    assert mod._cfg()["email_accent"] == "#222222"


# ── P2-19: màu nút đăng ký qua cấu hình, mặc định giữ nguyên ─────────────────────────

def _dung_index(tmp_path, them: dict | None = None) -> tuple[str, str]:
    repo = tmp_path / "web"
    (repo / "2026" / "09").mkdir(parents=True)
    (repo / "2026" / "09" / "2026-09-25.html").write_text(
        '<div class="card">x</div><div class="tldr">tóm tắt</div>', encoding="utf-8")
    cfg = {"site_base": "https://example.com/news", "a": "Kenh", "b": "Thu",
           "tagline": "Câu định vị", "author": "Tác giả", "home_url": "https://example.com",
           "script_url": "https://example.com/s"}
    cfg.update(them or {})
    cf = tmp_path / "cfg.json"
    cf.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    p = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", str(KHUON / "build-index.ps1"), "-Repo", str(repo),
                        "-Config", str(cf)], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    idx = (repo / "index.html").read_text(encoding="utf-8")
    # Regex đường dẫn nhận cả `\` và `/`: thiếu thì trên macOS 0 bản tin (P1-16).
    assert "2026/09/2026-09-25.html" in idx, "không quét được bản tin — regex đường dẫn?"
    return idx, (repo / "rss.html").read_text(encoding="utf-8")


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_build_index_KHONG_khai_mau_cta_thi_giu_nguyen_hai_mau_cu(tmp_path):
    idx, rss = _dung_index(tmp_path)
    assert idx.count("linear-gradient(90deg,#00f0ff,#39ff7a)") == 2, "nút nav + nút form"
    assert "box-shadow:0 0 0 0 rgba(0,240,255,.45)" in idx
    assert "box-shadow:0 0 0 8px rgba(0,240,255,0)" in idx
    assert "#subMsg{font-size:.88rem;color:#39ff7a;font-weight:600}" in idx
    assert 'ms.style.color="#39ff7a"' in idx
    assert "linear-gradient(90deg,#00f0ff,#39ff7a)" in rss


@pytest.mark.skipif(not PS, reason="khong co PowerShell")
def test_build_index_KHAI_mau_cta_thi_moi_cho_an_theo(tmp_path):
    idx, rss = _dung_index(tmp_path, {"web_cta_from": "#34f5a4", "web_cta_to": "#38bdf8"})
    assert idx.count("linear-gradient(90deg,#34f5a4,#38bdf8)") == 2
    assert "rgba(52,245,164,.45)" in idx and "rgba(52,245,164,0)" in idx
    assert 'ms.style.color="#38bdf8"' in idx and "color:#38bdf8;font-weight:600" in idx
    assert "#39ff7a" not in idx, "còn chỗ ghi cứng màu cũ"
    assert "linear-gradient(90deg,#34f5a4,#38bdf8)" in rss


# ── Cổng: regex đường dẫn trong khuôn nhận cả `\` và `/` ─────────────────────────────

_REGEX_OP = re.compile(r"-match|-replace|-split|\[regex\]|re\.(search|match|fullmatch|sub|split|"
                       r"findall|compile)")
# Hai gạch ngược liền nhau (= một `\` literal trong regex) KHÔNG nằm trong lớp `[\\/]`.
_CHI_GACH_NGUOC = re.compile(r"(?<!\[)\\\\(?!/\])")


def test_regex_duong_dan_trong_khuon_nhan_ca_hai_dau_phan_cach():
    sai = []
    for f in sorted(KHUON.parent.rglob("*")):
        if f.suffix not in (".ps1", ".py") or not f.is_file():
            continue
        for i, dong in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
            if _REGEX_OP.search(dong) and _CHI_GACH_NGUOC.search(dong):
                sai.append(f"{f.relative_to(ROOT).as_posix()}:{i}: {dong.strip()[:100]}")
    assert not sai, ("regex đường dẫn chỉ khớp `\\` — trên macOS khớp 0 file; dùng `[\\\\/]`:\n  "
                     + "\n  ".join(sai))


def test_cong_regex_bat_duoc_dung_loi_P1_16():
    """Cổng của cổng: mẫu lỗi thật (bản trạm Windows trước vá) phải bị bắt, bản vá thì không."""
    loi = r"$_.FullName -match '\\(\d{4})\\(\d{2})\\((\d{4}-\d{2}-\d{2})|(w\d{2}))\.html$'"
    dung = r"$_.FullName -match '[\\/](\d{4})[\\/](\d{2})[\\/]((\d{4}-\d{2}-\d{2})|(w\d{2}))\.html$'"
    assert _CHI_GACH_NGUOC.search(loi)
    assert not _CHI_GACH_NGUOC.search(dung)
