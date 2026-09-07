"""Gửi bản tin định kỳ qua email cho một kênh (tự chủ, SMTP Gmail).

Run by the wrapper AFTER a successful push. Best-effort: any failure prints a
warning and exits 0 so it never fails the weekly run.

Bí mật đọc từ biến môi trường EMAIL_CONFIG (mặc định: email-config.json cạnh script).
File này KHÔNG bao giờ vào git — nó chứa mật khẩu ứng dụng:
{
  "script_url": "https://script.google.com/macros/s/XXX/exec",
  "secret": "same SECRET as in subscribe.gs",
  "smtp_user": "ban@example.com",
  "smtp_app_password": "16-char Gmail App Password",
  "site_base": "https://vi-du.vn/news/<kênh>",
  "repo": "<đường dẫn repo web của kênh>"
}

Usage: python send_newsletter.py [--test you@example.com] [--date YYYY-MM-DD]
  --test: send ONLY to the given address (ignores the subscriber list).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import smtplib
import sys
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Bí mật SMTP dùng chung mọi kênh -> một file ở ~/.secret. Vẫn lùi về file cạnh
# script nếu biến chưa đặt, để bản cũ còn chạy được trong lúc chuyển.
CFG_PATH = (os.environ.get("EMAIL_CONFIG")
            or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "email-config.json"))


def _cfg():
    """Trộn hai nguồn: BÍ MẬT dùng chung + CẤU HÌNH riêng của kênh.

    05/09/2026 tách đôi `email-config.json` cũ: ba trường bí mật (`smtp_user`,
    `smtp_app_password`, `secret`) giống hệt nhau giữa các kênh nên gộp một bản ở
    `~/.secret/email/config.json`; còn `script_url`, `site_base`, `repo` KHÔNG phải bí mật —
    chúng khác nhau theo kênh nên về `brand.json`. Hàm này ghép lại đúng hình dạng cũ, để
    phần code bên dưới không phải đổi.

    Thiếu một trong hai nguồn thì DỪNG LỚN TIẾNG. Trước bản vá này, file thiếu chỉ làm
    newsletter bị bỏ qua im lặng — không ai biết tuần đó thư không gửi.
    """
    with open(CFG_PATH, encoding="utf-8-sig") as f:
        bi_mat = json.load(f)
    # Cấu hình KÊNH nay ở `channel.yml:brand` (07/09/2026), không còn `brand.json`.
    # Đọc thẳng YAML được vì đây là Python; PowerShell thì phải qua bản chụp JSON.
    # Thiếu file hoặc thiếu khối `brand:` -> ném lỗi, KHÔNG rơi về giá trị rỗng: newsletter
    # gửi đi với site_base rỗng là mọi link trong thư đều hỏng, mà không ai biết.
    import yaml
    cy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channel.yml")
    with open(cy, encoding="utf-8") as f:
        _kenh = yaml.safe_load(f) or {}
    brand = _kenh.get("brand") or {}
    if not brand:
        raise SystemExit("send_newsletter: %s thiếu khối `brand:` — không đủ cấu hình để gửi thư." % cy)
    ra = dict(bi_mat)
    for x in ("script_url", "site_base", "repo"):
        if brand.get(x):
            ra[x] = brand[x]
    return ra


def _cfg_cu():
    with open(CFG_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def _file_date(year, name):
    """Edition publish date: ISO date file, or wNN -> that week's Friday."""
    import datetime
    m = re.fullmatch(r"w(\d{2})", name, re.I)
    if m:
        jan4 = datetime.date(year, 1, 4)
        week1_mon = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
        return week1_mon + datetime.timedelta(weeks=int(m.group(1)) - 1, days=4)
    try:
        return datetime.date.fromisoformat(name)
    except ValueError:
        return None


def _latest_edition(repo, name=None):
    cands = []
    for fp in glob.glob(os.path.join(repo, "20*", "*", "*.html")):
        m = re.search(r"[\\/](\d{4})[\\/](\d{2})[\\/]([^\\/]+)\.html$", fp)
        if not m or not os.path.isfile(fp + ".json"):
            continue  # only editions with a sidecar can be mailed
        d = _file_date(int(m.group(1)), m.group(3))
        if d:
            cands.append((d, f"{m.group(1)}/{m.group(2)}/{m.group(3)}.html", fp))
    if name:
        cands = [c for c in cands if os.path.basename(c[2]) == name + ".html"]
    if not cands:
        raise SystemExit("no edition found")
    cands.sort()
    _pub, rel, html = cands[-1]
    with open(html + ".json", encoding="utf-8-sig") as f:
        d = json.load(f)
    # media (audio/video release tag) is keyed by the RUN date in the sidecar
    dd, mm, yyyy = d.get("date", "").split("/")
    media_date = f"{yyyy}-{mm}-{dd}"
    return media_date, rel, d


def _tok(email, secret):
    return hashlib.sha256((email + secret).encode("utf-8")).hexdigest()[:16]


def _subscribers(cfg):
    url = cfg["script_url"] + "?" + urllib.parse.urlencode(
        {"action": "list", "token": cfg["secret"]})
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if not d.get("ok"):
        raise RuntimeError(f"list failed: {d}")
    return d.get("emails", [])


def _build_email(cfg, date, rel, d, to_email):
    # Nhận diện kênh đến từ cấu hình, KHÔNG ghi cứng: bản mẫu này là repo công khai,
    # ghi cứng một tên là mọi người clone về đều gửi thư dưới danh nghĩa người khác.
    brand_a = cfg.get("a", "")
    brand_b = cfg.get("b", "")
    brand = (brand_a + " " + brand_b).strip()
    accent = cfg.get("email_accent") or "#0ea5b7"
    site_text = cfg["site_base"].split("//", 1)[-1].rstrip("/")
    week = d.get("week", "")
    page = f"{cfg['site_base']}/{rel}"
    yt = (d.get("youtube") or {}).get("recap", "")
    if yt:
        video = f"https://youtu.be/{yt}"
    else:
        # Không có video YouTube thì lùi về bản đính kèm trong Release của repo kênh.
        # `gh_repo` đến từ channel.yml:brand — ghi cứng owner/repo ở đây là mọi kênh
        # đều trỏ về kho của người viết ra bản mẫu này.
        gh = cfg.get("gh_repo")
        video = (f"https://github.com/{gh}/releases/download/"
                 f"media-{date}/{date}.mp4") if gh else page
    unsub = (cfg["script_url"] + "?" + urllib.parse.urlencode(
        {"action": "unsub", "email": to_email, "t": _tok(to_email, cfg["secret"])}))

    top5 = sorted([i for i in d.get("items", []) if i.get("hot_rank")],
                  key=lambda i: i["hot_rank"])
    tldr = d.get("tldr", "")

    rows = "".join(
        f'<tr><td style="padding:8px 10px;color:#0ea5b7;font-weight:700;'
        f'white-space:nowrap;vertical-align:top">#{i["hot_rank"]}</td>'
        f'<td style="padding:8px 0"><a href="{i["url"]}" '
        f'style="color:#111827;font-weight:600;text-decoration:none">'
        f'{i["title"]}</a></td></tr>'
        for i in top5)

    html = f"""<!doctype html><html><body style="margin:0;background:#f4f6fa;font-family:Segoe UI,Arial,sans-serif">
<div style="max-width:620px;margin:0 auto;padding:28px 16px">
  <div style="font-size:22px;font-weight:800;color:#111827">{brand_a} <span style="color:{accent}">{brand_b}</span>
    <span style="font-size:13px;font-weight:400;color:#6b7280"> · Tuần {week} · {d.get("range", "")}</span></div>
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px;margin-top:14px">
    <div style="font-size:13px;font-weight:700;letter-spacing:.06em;color:#0ea5b7;text-transform:uppercase">Tổng quan tuần này</div>
    <p style="color:#374151;line-height:1.65;margin:8px 0 0">{tldr}</p>
  </div>
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px;margin-top:14px">
    <div style="font-size:13px;font-weight:700;letter-spacing:.06em;color:#0ea5b7;text-transform:uppercase">🔥 Top 5 tin nóng</div>
    <table style="border-collapse:collapse;margin-top:6px">{rows}</table>
  </div>
  <div style="text-align:center;margin:22px 0">
    <a href="{page}" style="background:#0ea5b7;color:#fff;font-weight:700;padding:11px 22px;border-radius:9px;text-decoration:none">Đọc bản tin đầy đủ →</a>
    &nbsp;&nbsp;
    <a href="{video}" style="color:#0ea5b7;font-weight:600;text-decoration:none">🎬 Xem video recap</a>
  </div>
  <p style="color:#9ca3af;font-size:12px;text-align:center;line-height:1.6">
    Bạn nhận email này vì đã đăng ký tại <a href="{cfg['site_base']}/" style="color:#9ca3af">{site_text}</a>.<br>
    <a href="{unsub}" style="color:#9ca3af">Hủy đăng ký</a></p>
</div></body></html>"""

    text = (f"{brand} - Tuần {week} ({d.get('range', '')})\n\n{tldr}\n\nTOP 5:\n"
            + "\n".join(f"#{i['hot_rank']} {i['title']}\n   {i['url']}" for i in top5)
            + f"\n\nĐọc bản tin: {page}\nVideo recap: {video}\n\nHủy đăng ký: {unsub}\n")

    msg = EmailMessage()
    hot1 = next((i["title"] for i in top5 if i["hot_rank"] == 1), "")
    msg["Subject"] = f"{brand} tuần {week}: {hot1}"[:150]
    msg["From"] = f"{brand} <{cfg['smtp_user']}>"
    msg["To"] = to_email
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    return msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default="", help="send only to this address")
    ap.add_argument("--date", default="", help="edition date YYYY-MM-DD (default: latest)")
    args = ap.parse_args()

    try:
        cfg = _cfg()
        for k in ("script_url", "secret", "smtp_user", "smtp_app_password"):
            if not cfg.get(k) or "CHANGE_ME" in str(cfg.get(k)):
                print(f"[mail] config incomplete ({k}) - skipped")
                return 0
        date, rel, d = _latest_edition(cfg["repo"],
                                       args.date or None)
        recipients = [args.test] if args.test else _subscribers(cfg)
        if not recipients:
            print("[mail] 0 subscribers - nothing to send")
            return 0
        print(f"[mail] edition {date}, {len(recipients)} recipient(s)")

        ok = fail = 0
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
            s.starttls()
            s.login(cfg["smtp_user"], cfg["smtp_app_password"])
            for to in recipients:
                try:
                    s.send_message(_build_email(cfg, date, rel, d, to))
                    ok += 1
                    print(f"  sent -> {to}")
                except Exception as exc:
                    fail += 1
                    print(f"  [warn] {to}: {type(exc).__name__}: {exc}")
                time.sleep(0.8)  # gentle pacing, Gmail dislikes bursts
        print(f"[mail] DONE ok={ok} fail={fail}")
    except Exception as exc:
        print(f"[mail] [warn] newsletter skipped: {type(exc).__name__}: {exc}")
    return 0  # never fail the weekly run


if __name__ == "__main__":
    raise SystemExit(main())
