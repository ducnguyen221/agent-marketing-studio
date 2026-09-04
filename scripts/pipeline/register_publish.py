#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sổ đăng bài: publish.json — thay cho sheet Post của mô hình Excel cũ.

Đóng bốn mắt xích trước đây phải làm tay, và mỗi mắt xích là một cơ hội quên:
  · thay {{BLOG_URL}} / {{YOUTUBE_URL}} trong file kênh
  · verify link còn sống TRƯỚC khi ghi sổ
  · ghi publish.json + cập nhật ngược campaign.md, CAMPAIGNS.md, continuity.json
  · để lại DẤU VẾT cho Cổng 2 (ai duyệt, lúc nào, nói gì)

HAI ĐIỂM THIẾT KẾ ĐÁNG NHỚ:

1. **Facebook KHÔNG verify bằng HTTP.** Permalink Facebook trả 200 kể cả khi đó là trang
   đăng nhập hoặc id sai — kiểm HTTP ở đây là cấp một lời bảo đảm sai. Với Facebook, điều
   kiện là có `platform_id`, và với bài thường thì có cả `comment_id` (vì luật hiện hành
   là thân bài 0 URL, link nằm ở comment — thiếu comment là bài mồ côi).

2. **Cổng 2 có dấu vết, không phải cờ.** `approve` ghi ai duyệt, lúc nào, và NGUYÊN VĂN
   câu duyệt. Ô Excel người tự tick đã mất khi bỏ Excel; đây là thứ thay thế. Agent chỉ
   được chạy `approve` khi trong phiên có câu duyệt tường minh của người.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import md_io  # noqa: E402
import post_paths as PP  # noqa: E402
import studio_paths as SP  # noqa: E402

SCHEMA = "publish/2"
_URL = re.compile(r"https?://\S+", re.I)
PLACEHOLDER = {"youtube": "{{YOUTUBE_URL}}", "web_blog": "{{BLOG_URL}}",
               "facebook": "{{FB_URL}}"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _doc_json(p: Path, mac_dinh=None):
    if not p.is_file():
        return mac_dinh
    return json.loads(p.read_text(encoding="utf-8"))


def _ghi_json(p: Path, d) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- dựng khung

def _khung(post_id, content_id, channel, post_format, kpi) -> dict:
    return {
        "post_id": post_id, "content_id": content_id,
        "channel": channel, "post_format": post_format,
        "post_role": "", "post_content": SP.NEO.get(post_format, ""),
        "asset_ref": "", "quality_check": "", "agent_status": "draft",
        "review": {"status": "pending", "feedback": "", "approved_by": "",
                   "approved_at": "", "note": ""},
        "post_status": "not_created",
        "publish": {"plan": "", "status": "not_published", "link": "",
                    "platform_id": "", "comment_id": "", "at": "", "http": None},
        "target": {"view": kpi.get(channel), "interaction": None},
        "actual": {"view": None, "interaction": None, "reaction": None, "comment": None,
                   "share": None, "click": None, "reach": None, "updated_at": None},
        "updated_at": _now(),
    }


def _ngu_canh(bai: Path):
    """Trả về (meta, campaign_dir, fm_campaign, channel_dir, cfg_channel)."""
    import yaml
    meta = _doc_json(bai / "meta.json", {})
    cam_dir = SP.campaign_of(bai)
    fm_cam, _ = md_io.read_fm(cam_dir / "campaign.md")
    kenh_dir = SP.channel_of(bai)
    cfg = yaml.safe_load((kenh_dir / "channel.yml").read_text(encoding="utf-8")) or {}
    return meta, cam_dir, fm_cam, kenh_dir, cfg


# ---------------------------------------------------------------- lệnh

def cmd_init(bai: Path) -> int:
    meta, cam_dir, fm_cam, kenh_dir, cfg = _ngu_canh(bai)
    content = (PP.p(bai, "content").read_text(encoding="utf-8")
               if PP.p(bai, "content").is_file() else "")
    kpi = fm_cam.get("kpi") or {}
    cho_phep = set(fm_cam.get("channels") or [])

    pj = _doc_json(PP.p(bai, "publish"), {}) or {}
    cu = {p["post_id"]: p for p in pj.get("posts", [])}
    posts = []
    for nen in (cfg.get("platforms") or []):
        ch = nen.get("channel")
        if cho_phep and ch not in cho_phep:
            continue
        for fmt in (nen.get("post_formats") or []):
            neo = SP.NEO.get(fmt, "")
            if neo and f"## {neo}" not in content:
                continue                      # content.md chưa có khối này -> chưa phải post
            pid = SP.post_id(meta.get("post_id", ""), ch, fmt)
            posts.append(cu.get(pid) or _khung(pid, meta.get("post_id", ""), ch, fmt, kpi))

    pj.update({"schema": SCHEMA, "post_id": meta.get("post_id", ""),
               "campaign_id": fm_cam.get("id", ""), "channel_id": cfg.get("id", ""),
               "slug": meta.get("slug", ""), "title": meta.get("title", ""),
               "posts": posts})
    pj.setdefault("summary", "")
    pj.setdefault("key_terms_explained", [])
    pj.setdefault("claims_cited", [])
    _ghi_json(PP.p(bai, "publish"), pj)
    print(f"  {len(posts)} post: " + " · ".join(p['post_id'] for p in posts))
    return 0


def cmd_approve(bai: Path, by: str, note: str, chi_post: str, feedback: str,
                override_qa: str) -> int:
    if not by.strip():
        sys.stderr.write("--by bắt buộc: Cổng 2 phải biết AI duyệt.\n")
        return 2
    if not note.strip():
        sys.stderr.write(
            "--note bắt buộc: chép NGUYÊN VĂN câu duyệt của người.\n"
            "Cổng 2 là dấu vết, không phải cái cờ bật lên. Không có câu duyệt tường minh\n"
            "trong phiên thì KHÔNG được chạy lệnh này.\n")
        return 2
    pj = _doc_json(PP.p(bai, "publish"))
    if not pj:
        sys.stderr.write("chưa có publish.json — chạy `init` trước.\n")
        return 2
    loc = set(chi_post.split(",")) if chi_post else None
    n = 0
    for p in pj["posts"]:
        if loc and p["post_id"].rsplit("-", 1)[-1] not in loc:
            continue
        if p.get("quality_check") == "failed" and not override_qa:
            sys.stderr.write(f"{p['post_id']}: cổng kỹ thuật ĐỎ. Muốn duyệt vẫn được nhưng "
                             f"phải nêu lý do: --override-qa \"…\"\n")
            return 2
        p["review"] = {"status": "approved", "feedback": feedback,
                       "approved_by": by, "approved_at": str(date.today()),
                       "note": note + (f" [override-qa: {override_qa}]" if override_qa else "")}
        p["post_status"] = "approved"
        p["updated_at"] = _now()
        n += 1
    _ghi_json(PP.p(bai, "publish"), pj)
    _mirror_g2(bai, str(date.today()))
    print(f"  duyệt {n} post bởi {by} — đã ghi dấu vết vào publish.json và ô g2")
    return 0


def cmd_qa(bai: Path) -> int:
    g = _doc_json(PP.p(bai, "gates"))
    if not g:
        sys.stderr.write("chưa có gates.json — chạy blog_gates.py trước.\n")
        return 2
    pj = _doc_json(PP.p(bai, "publish"))
    kq = "passed" if g.get("ket_luan") == "xanh" else "failed"
    for p in pj["posts"]:
        p["quality_check"] = kq
        p["agent_status"] = "completed" if kq == "passed" else "blocked"
        p["updated_at"] = _now()
    _ghi_json(PP.p(bai, "publish"), pj)
    print(f"  quality_check = {kq} ({g.get('do_chan', 0)} cổng đỏ-chặn)")
    return 0


def _verify(channel: str, post_format: str, link: str, platform_id: str,
            comment_id: str, bo_qua: bool) -> tuple[bool, int | None, str]:
    if bo_qua:
        return True, None, "bỏ qua verify theo yêu cầu"
    if channel == "facebook":
        # Permalink Facebook trả 200 cả khi là trang đăng nhập -> HTTP vô nghĩa ở đây.
        if not platform_id:
            return False, None, "thiếu platform_id (id bài Facebook)"
        if post_format == "facebook_post" and not comment_id:
            return False, None, ("thiếu comment_id — luật hiện hành là thân bài 0 URL nên "
                                 "link nằm ở comment; không có comment là bài mồ côi")
        return True, None, "xác nhận bằng platform_id + comment_id"
    if not link:
        return False, None, "thiếu link"
    import requests
    try:
        r = requests.get(link, timeout=30, allow_redirects=True)
    except Exception as e:
        return False, None, f"không gọi được: {type(e).__name__}"
    return (r.status_code == 200), r.status_code, f"HTTP {r.status_code}"


def _thay_placeholder(bai: Path, channel: str, link: str) -> list[str]:
    ph = PLACEHOLDER.get(channel)
    if not ph:
        return []
    doi = []
    for khoa in PP.FILE_CONG_KHAI:
        f = PP.p(bai, khoa)
        if not f.is_file():
            continue
        s = f.read_text(encoding="utf-8")
        if ph in s:
            f.write_text(s.replace(ph, link), encoding="utf-8", newline="\n")
            doi.append(PP.LAYOUT[khoa])
    return doi


def cmd_set(bai: Path, chi_post: str, link: str, platform_id: str, comment_id: str,
            at: str, no_verify: bool) -> int:
    pj = _doc_json(PP.p(bai, "publish"))
    if not pj:
        sys.stderr.write("chưa có publish.json — chạy `init` trước.\n")
        return 2
    hop = [p for p in pj["posts"] if p["post_id"].rsplit("-", 1)[-1] == chi_post]
    if len(hop) != 1:
        sys.stderr.write(f"--post {chi_post!r} khớp {len(hop)} post. Có: "
                         + ", ".join(p["post_id"].rsplit("-", 1)[-1] for p in pj["posts"]) + "\n")
        return 2
    p = hop[0]
    if p["review"]["status"] != "approved":
        sys.stderr.write(f"{p['post_id']}: chưa qua Cổng 2 (review={p['review']['status']}). "
                         f"Chạy `approve --by … --note \"…\"` trước.\n")
        return 2

    ok, code, vi_sao = _verify(p["channel"], p["post_format"], link, platform_id,
                               comment_id, no_verify)
    if not ok:
        sys.stderr.write(f"KHÔNG ghi sổ: {vi_sao}\n")
        return 1

    doi = _thay_placeholder(bai, p["channel"], link)
    con = [PP.LAYOUT[k] for k in PP.FILE_CONG_KHAI
           if PP.p(bai, k).is_file() and PLACEHOLDER.get(p["channel"], "\0")
           in PP.p(bai, k).read_text(encoding="utf-8")]
    if con:
        sys.stderr.write(f"KHÔNG ghi sổ: còn placeholder sau khi thay ở {con}\n")
        return 1

    p["publish"] = {"plan": p["publish"].get("plan", ""), "status": "published",
                    "link": link, "platform_id": platform_id, "comment_id": comment_id,
                    "at": at or _now(), "http": code}
    p["post_status"] = "published"
    p["updated_at"] = _now()

    moc = [q["publish"]["at"] for q in pj["posts"] if q["publish"].get("at")]
    pj["published_at"] = min(moc) if moc else ""
    _mirror_v1(pj)
    _ghi_json(PP.p(bai, "publish"), pj)
    _cap_nhat_nguoc(bai, pj)

    print(f"  {p['post_id']} → published ({vi_sao})")
    if doi:
        print(f"  đã thay {PLACEHOLDER[p['channel']]} trong: {', '.join(doi)}")
    return 0


def cmd_metrics(bai: Path, chi_post: str, **so) -> int:
    pj = _doc_json(PP.p(bai, "publish"))
    hop = [p for p in pj["posts"] if p["post_id"].rsplit("-", 1)[-1] == chi_post]
    if len(hop) != 1:
        sys.stderr.write(f"--post {chi_post!r} khớp {len(hop)} post\n")
        return 2
    p = hop[0]
    for k, v in so.items():
        if v is not None:
            p["actual"][k] = v
    p["actual"]["updated_at"] = _now()
    p["updated_at"] = _now()
    _ghi_json(PP.p(bai, "publish"), pj)
    print(f"  {p['post_id']} actual = " + " · ".join(f"{k}={v}" for k, v in p["actual"].items()
                                                     if v is not None and k != "updated_at"))
    print("  nhớ append một dòng vào Mục 9 (Báo cáo) của campaign.md — actual GHI ĐÈ, "
          "chỗ đó mới giữ được diễn biến")
    return 0


def cmd_migrate(bai: Path) -> int:
    pj = _doc_json(PP.p(bai, "publish"))
    if not pj:
        sys.stderr.write("không có publish.json\n")
        return 2
    if pj.get("schema") == SCHEMA:
        print("  đã là publish/2 — không đổi gì")
        return 0
    meta, cam_dir, fm_cam, kenh_dir, cfg = _ngu_canh(bai)
    kpi = fm_cam.get("kpi") or {}
    posts = []

    def them(ch, fmt, link, pid_nen="", cid="", http=None):
        if not (link or pid_nen):
            return
        p = _khung(SP.post_id(meta.get("post_id", pj.get("post_id", "")), ch, fmt),
                   pj.get("post_id", ""), ch, fmt, kpi)
        p["quality_check"] = "passed"
        p["agent_status"] = "completed"
        p["review"] = {"status": "approved", "feedback": "", "approved_by": "Đức",
                       "approved_at": (pj.get("published_at", "") or "")[:10],
                       "note": "di trú từ publish/1 — bài đã đăng, duyệt qua chat trước khi "
                               "đăng, không có mốc giờ chính xác"}
        p["post_status"] = "published"
        p["publish"] = {"plan": "", "status": "published", "link": link,
                        "platform_id": pid_nen, "comment_id": cid,
                        "at": pj.get("published_at", ""), "http": http}
        posts.append(p)

    v = pj.get("verified") or {}
    them("youtube", "youtube_video", pj.get("youtube_url", ""))
    them("web_blog", "blog_article", pj.get("blog_url") or pj.get("url", ""),
         http=v.get("blog_http"))
    them("facebook", "facebook_post", pj.get("fb_permalink", ""),
         pj.get("fb_post_id", ""), pj.get("fb_comment_id", ""))

    pj.update({"schema": SCHEMA, "migrated_from": "publish/1", "posts": posts,
               "campaign_id": fm_cam.get("id", pj.get("campaign_id", "")),
               "channel_id": cfg.get("id", ""), "title": pj.get("title", meta.get("title", ""))})
    _ghi_json(PP.p(bai, "publish"), pj)
    print(f"  publish/1 → publish/2 · {len(posts)} post: "
          + " · ".join(p["post_id"] for p in posts))
    return 0


def cmd_show(bai: Path, ra_json: bool) -> int:
    pj = _doc_json(PP.p(bai, "publish"))
    if not pj:
        sys.stderr.write("không có publish.json\n")
        return 2
    if ra_json:
        print(json.dumps(pj, ensure_ascii=False, indent=2))
        return 0
    print(f"  {pj.get('post_id')} · {pj.get('title', '')[:60]}")
    for p in pj["posts"]:
        print(f"    {p['post_id']:<16} {p['channel']:<10} qa={p['quality_check'] or '-':<7} "
              f"duyệt={p['review']['status']:<9} đăng={p['publish']['status']:<13} "
              f"{p['publish']['link'][:52]}")
    return 0


# ---------------------------------------------------------------- ghi ngược

def _mirror_v1(pj: dict) -> None:
    """Giữ các khoá phẳng của publish/1 — continuity.json và build_blog_html còn đọc chúng."""
    for p in pj.get("posts", []):
        if p["publish"]["status"] != "published":
            continue
        if p["channel"] == "youtube":
            pj["youtube_url"] = p["publish"]["link"]
        elif p["channel"] == "web_blog":
            pj["blog_url"] = pj["url"] = p["publish"]["link"]
        elif p["channel"] == "facebook":
            pj["fb_permalink"] = p["publish"]["link"]
            pj["fb_post_id"] = p["publish"]["platform_id"]
            pj["fb_comment_id"] = p["publish"]["comment_id"]


def _mirror_g2(bai: Path, ngay: str) -> None:
    cam_dir = SP.campaign_of(bai)
    meta = _doc_json(bai / "meta.json", {})
    fm, body = md_io.read_fm(cam_dir / "campaign.md")
    body = md_io.upsert_row(body, "CONTENT", "content_id",
                            {"content_id": meta.get("post_id", ""), "g2": ngay})
    md_io.write_fm(cam_dir / "campaign.md", fm, body)


def _cap_nhat_nguoc(bai: Path, pj: dict) -> None:
    """campaign.md · CAMPAIGNS.md · continuity.json — ba nơi phải khớp sau khi đăng."""
    cam_dir = SP.campaign_of(bai)
    kenh_dir = SP.channel_of(bai)
    da_dang = [p for p in pj["posts"] if p["publish"]["status"] == "published"]
    ngay = (pj.get("published_at") or "")[:10]

    fm, body = md_io.read_fm(cam_dir / "campaign.md")
    if da_dang:
        # URL THẬT vào bảng Content — Đức yêu cầu 04/09: mở lại bài sau này không phải đi
        # lục từng publish.json, và campaign.html render được thành nút bấm.
        # Duyệt theo THỨ TỰ MẪU, không theo thứ tự trong publish.json: cột sinh ra theo thứ
        # tự đăng thì mỗi kênh một kiểu bảng, đọc chéo giữa các chiến dịch là rối.
        COT_LINK = [("web_blog", "web"), ("youtube", "youtube"), ("facebook", "facebook")]
        dong = {"content_id": pj.get("post_id", ""), "status": "published", "published": ngay}
        link = {p["channel"]: p["publish"].get("link") for p in da_dang}
        for kenh_p, c in COT_LINK:
            if link.get(kenh_p):
                dong[c] = link[kenh_p]
        # them_cot: bảng cũ chưa có 3 cột link thì nới ra, đừng nuốt URL.
        body = md_io.upsert_row(body, "CONTENT", "content_id", dong, them_cot=True)
    md_io.write_fm(cam_dir / "campaign.md", fm, body)

    _, body2 = md_io.read_fm(cam_dir / "campaign.md")
    dong_ct = md_io.read_table(body2, "CONTENT")[1]
    so = kenh_dir / "CAMPAIGNS.md"
    fm3, body3 = md_io.read_fm(so)
    body3 = md_io.upsert_row(body3, "CAMPAIGNS", "campaign_id", {
        "campaign_id": fm.get("id", ""), "bài": str(len(dong_ct)),
        "đã đăng": str(sum(1 for d in dong_ct if d.get("status") == "published"))})
    fm3["updated"] = str(date.today())
    md_io.write_fm(so, fm3, body3)

    # continuity.json — sổ ở cấp kênh, B0 dùng để khỏi trùng đề tài
    cont = kenh_dir / "continuity.json"
    ds = _doc_json(cont, []) or []
    ban = {k: pj.get(k) for k in ("post_id", "slug", "title", "url", "youtube_url",
                                  "fb_permalink", "fb_post_id", "fb_comment_id",
                                  "published_at", "summary", "key_terms_explained",
                                  "claims_cited") if pj.get(k)}
    ds = [x for x in ds if x.get("post_id") != pj.get("post_id")] + [ban]
    cont.parent.mkdir(parents=True, exist_ok=True)
    _ghi_json(cont, ds)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sổ đăng bài (publish.json).")
    ap.add_argument("bai", help="thư mục bài")
    sub = ap.add_subparsers(dest="lenh", required=True)
    sub.add_parser("init")
    sub.add_parser("qa")
    pa = sub.add_parser("approve")
    pa.add_argument("--by", required=True, help="ai duyệt")
    pa.add_argument("--note", required=True, help="NGUYÊN VĂN câu duyệt của người")
    pa.add_argument("--post", default="", help="giới hạn: yt,web,fb")
    pa.add_argument("--feedback", default="")
    pa.add_argument("--override-qa", default="", help="lý do duyệt dù cổng kỹ thuật đỏ")
    ps = sub.add_parser("set")
    ps.add_argument("--post", required=True, help="yt | web | fb | short | reel")
    ps.add_argument("--link", default="")
    ps.add_argument("--platform-id", default="")
    ps.add_argument("--comment-id", default="")
    ps.add_argument("--at", default="")
    ps.add_argument("--no-verify", action="store_true")
    pm = sub.add_parser("metrics")
    pm.add_argument("--post", required=True)
    for k in ("view", "interaction", "reaction", "comment", "share", "click", "reach"):
        pm.add_argument(f"--{k}", type=int, default=None)
    sub.add_parser("migrate")
    psh = sub.add_parser("show")
    psh.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    bai = Path(a.bai).resolve()
    if not bai.is_dir():
        sys.stderr.write(f"không phải thư mục: {bai}\n")
        return 2
    if a.lenh == "init":
        return cmd_init(bai)
    if a.lenh == "qa":
        return cmd_qa(bai)
    if a.lenh == "approve":
        return cmd_approve(bai, a.by, a.note, a.post, a.feedback, a.override_qa)
    if a.lenh == "set":
        return cmd_set(bai, a.post, a.link, a.platform_id, a.comment_id, a.at, a.no_verify)
    if a.lenh == "metrics":
        return cmd_metrics(bai, a.post, view=a.view, interaction=a.interaction,
                           reaction=a.reaction, comment=a.comment, share=a.share,
                           click=a.click, reach=a.reach)
    if a.lenh == "migrate":
        return cmd_migrate(bai)
    return cmd_show(bai, a.json)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
