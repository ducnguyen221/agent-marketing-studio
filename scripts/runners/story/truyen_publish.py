# -*- coding: utf-8 -*-
"""truyen_publish.py — đăng 1 video truyện PNTT lên kênh "Nghe Tiên Truyện" (@nghe-tien-truyen).

Chạy bằng python có google-api-python-client (daily_truyen dò qua truyen_paths.publish_python()).
Tự dựng tiêu đề + MÔ TẢ (kèm mốc thời gian từng chương lấy từ manifest) rồi upload công khai
vào playlist "Phàm Nhân Tu Tiên (P1)".

  # xem trước title + description (KHÔNG upload, KHÔNG cần token, KHÔNG gọi agent — mô tả tĩnh;
  # thêm --with-hook để xem cả hook do agent viết, tốn hạn mức + ghi ledger):
  python truyen_publish.py --manifest <mp3.manifest.json> --video <mp4> --dry-run
  # đăng thật (cần youtube_token_truyen.json đã --auth chọn đúng kênh Nghe Tiên Truyện):
  python truyen_publish.py --manifest <...> --video <...>

Token kênh truyện: `--token` → YT_TOKEN_PATH__NGHE_TIEN_TRUYEN (riêng kênh, THẮNG) →
YT_TOKEN_PATH chung (truyen_paths.token_truyen; chỉ truyền ĐƯỜNG, script này không đọc token).
youtube_upload.py lấy từ `scripts/runners` của repo (truyen_paths.upload_engine_dir); bản đó đòi
YT_CLIENT_SECRET trong môi trường (không còn đường lùi cạnh file).
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# Da doi sang apps/truyen/ (2026-08-26); du lieu van o goc engine.
import truyen_paths  # noqa: E402  — phân giải Windows + macOS
ENGINE = truyen_paths.engine_dir()
# Nơi chứa youtube_upload.py dùng chung: `scripts/runners` của repo → <trạm>/engine (bản cũ)
# (chỉ nhận thư mục CÓ youtube_upload.py). Tên biến giữ AINEWS cho code dưới.
AINEWS = truyen_paths.upload_engine_dir()

# Chỉ là ĐƯỜNG tới token trong kho secret của máy — không mở file ở đây. Không đường lùi
# viết trong mã: tên tài khoản là dữ liệu của máy, không phải của repo.
# Biến RIÊNG kênh truyện thắng biến chung (P3-12) — xem truyen_paths.token_truyen.
DEFAULT_TOKEN = truyen_paths.token_truyen()
PLAYLIST = "Phàm Nhân Tu Tiên (P1)"

# Intro TĨNH (tác phẩm/nhân vật/cấp độ tu luyện) — DỜI sang MÔ TẢ PLAYLIST (main() set
# YT_PLAYLIST_DESC), KHÔNG lặp ở mọi tập nữa. Mỗi tập giờ có tóm tắt riêng do gen_hook() sinh.
INTRO_LONG = """📖 Tác phẩm: Phàm Nhân Tu Tiên
✍️ Tác giả: Vong Ngữ
📚 Thể loại: Tiên hiệp – Tu chân – Huyền huyễn

🌌 Giới thiệu tác phẩm:
Phàm Nhân Tu Tiên là một trong những bộ tiên hiệp kinh điển, mở ra kỷ nguyên truyện mạng Trung Quốc hiện đại. Không giống những truyện "trùng sinh nghịch thiên" hay nhân vật chính toàn là thiên tài, Phàm Nhân Tu Tiên kể về một người bình thường – Hàn Lập, xuất thân tầm thường, tư chất không cao, nhưng nhờ nghị lực, cơ duyên, và sự kiên nhẫn phi thường, từng bước leo lên con đường tu tiên đầy máu lửa. Bằng văn phong chậm rãi, chi tiết, thế giới tu chân trong truyện được xây dựng cực kỳ rộng lớn, logic và hấp dẫn. Hàn Lập không "gánh team", không hack cheat, mà thật sự tu luyện từ tầng thấp nhất – đúng chất "phàm nhân cầu đạo, bước từng bậc mà lên tiên giới".

🧘‍♂️ Nhân vật chính – Hàn Lập:
Hàn Lập là một thiếu niên nghèo, ban đầu chỉ mong đổi đời bằng con đường "bái nhập môn phái". Nhưng rồi, định mệnh cuốn anh vào thế giới tu chân đầy tàn khốc. Hắn là người cực kỳ thận trọng, giấu tài, không khoe khoang, luôn đặt sự sống còn lên đầu. Dù không phải người tốt tuyệt đối, nhưng lại rất đáng khâm phục vì ý chí vững như sắt, tu luyện nghiêm túc, không dao động trước sắc lợi. Trải qua vô số lần sinh tử, từng bước tiến từ phàm nhân đến cường giả đỉnh phong, Hàn Lập là hình mẫu lý tưởng cho những ai tin rằng: "Không cần thiên phú, chỉ cần không ngừng cố gắng".

🌀 Các cấp độ tu luyện trong Phàm Nhân Tu Tiên:
Tu chân giả trong truyện trải qua nhiều cảnh giới, từ thấp đến cao như sau:

1. Luyện Khí (Qi Refining) – Cấp độ sơ khởi, hấp thu linh khí, kéo dài tuổi thọ.
2. Trúc Cơ (Foundation Establishment) – Cảnh giới xây dựng nền tảng vững chắc, bắt đầu coi như chân chính bước vào tu chân.
3. Kết Đan (Core Formation) – Ngưng tụ Kim Đan, tăng mạnh pháp lực, thân thể cường hóa.
4. Nguyên Anh (Nascent Soul) – Linh hồn hóa hình, có thể rời khỏi thân thể, bước vào hàng ngũ cao nhân.
5. Hóa Thần (Spirit Severing) – Thoát ly thân xác, hóa thần thức, có thể du hành thiên địa.
6. Luyện Hư (Void Refining) – Hư hóa chân ý, bắt đầu hiểu quy luật đại đạo.
7. Hợp Thể (Body Integration) – Thân và thần hợp nhất, vượt qua cảnh giới phàm tục.
8. Đại Thừa (Great Ascension) – Cấp độ gần kề với phi thăng, mạnh mẽ cực độ.
9. Phi Thăng (Ascension) – Thoát khỏi phàm giới, bước vào Tiên giới chân chính.

Mỗi cảnh giới đều có ngưỡng cửa sinh tử, kỳ ngộ và thử thách riêng. Hành trình tu luyện của Hàn Lập kéo dài hàng nghìn năm, nhưng không hề nhàm chán nhờ cốt truyện chặt chẽ, thế giới phong phú, và nhân vật phụ sinh động.

🎧 Hãy cùng Nghe Tiên Truyện đồng hành với Hàn Lập qua từng bước tu luyện, vượt qua sinh tử hiểm nguy, và khám phá con đường phàm nhân nghịch thiên, tu thành chính quả."""

TAGS = ["Phàm Nhân Tu Tiên", "Vong Ngữ", "tiên hiệp", "tu tiên", "Hàn Lập",
        "nghe truyện", "truyện audio", "truyện tiên hiệp", "tu chân", "Nghe Tiên Truyện"]


def fmt_ts(sec):
    sec = max(0, int(round(sec)))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# Engine cho bước viết hook — 28/09/2026 Đức giao "chạy truyện với agy". Đi qua lớp gọi dùng
# chung agent_call của agent-marketing-studio (chuỗi lùi theo `order` trong
# <trạm>/_agent-call/engines.json khi agy hết hạn mức). Đặt TRUYEN_HOOK_ENGINE=claude-cli để
# quay về đường cũ. Mọi lỗi ở đây -> rơi xuống `claude -p` như trước, rồi mô tả tĩnh.
# Mẫu `*` phân giải theo `agy models` lúc chạy (P1-27: agy tự cập nhật đổi tên model).
HOOK_ENGINE = os.environ.get("TRUYEN_HOOK_ENGINE", "agy:claude-opus-*-high")


def _agent_call_json(prompt, timeout=300):
    eng, _, mdl = HOOK_ENGINE.partition(":")
    # Repo = nơi chứa CHÍNH file này (`<repo>/scripts/runners/story/`) -> MARKETING_STUDIO_HOME.
    # Không đoán thư mục chứa repo của máy nào.
    ung = [os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))]
    if os.environ.get("MARKETING_STUDIO_HOME"):
        ung.append(os.path.expanduser(os.environ["MARKETING_STUDIO_HOME"]))
    lib = next((os.path.join(h, "scripts", "lib") for h in ung
                if os.path.isfile(os.path.join(h, "scripts", "lib", "agent_call.py"))), None)
    if not lib:
        return None
    try:
        if lib not in sys.path:
            sys.path.insert(0, lib)
        import agent_call as AC
        import tempfile
        # station=None: agent_call phân giải trạm theo studio_paths (MARKETING_STUDIO_DATA →
        # studio.local.json → <repo>/workspace) — MỘT luật cho mọi script của repo.
        r = AC.call(prompt, engine=eng, model=mdl or "best", tools=(),
                    cwd=tempfile.gettempdir(), timeout=timeout,
                    on_quota="fallback", station=os.environ.get("MARKETING_STUDIO_DATA") or None)
        print(f"[hook] engine={r.get('engine')}:{r.get('model')} ok={r.get('ok')} "
              f"code={r.get('code')}", flush=True)
        if not r.get("ok"):
            return None
        m = re.search(r"\{.*\}", r.get("text") or "", re.S)
        return json.loads(m.group(0)) if m else None
    except Exception as e:
        print(f"[hook] agent_call lỗi ({e}) — lùi về claude -p", flush=True)
        return None


def _claude_json(prompt, timeout=180):
    """Viết hook qua HOOK_ENGINE (agent_call); hỏng thì lùi về `claude -p` trực tiếp."""
    if HOOK_ENGINE != "claude-cli":
        d = _agent_call_json(prompt)
        if isinstance(d, dict):
            return d
    return _claude_cli_json(prompt, timeout)


def _claude_cli_json(prompt, timeout=180):
    """Gọi `claude -p` (không cần API key) kỳ vọng trả JSON. MỌI lỗi -> None (KHÔNG raise):
    thiếu hook thì build() fallback về mô tả tĩnh, publish KHÔNG bao giờ gãy vì bước này."""
    import shutil
    import subprocess
    claude = shutil.which("claude")
    if not claude:
        return None
    try:
        # Prompt qua STDIN, KHÔNG qua arg: prompt tiếng Việt dài làm arg dòng lệnh Windows
        # vỡ encode cp1252 + đụng giới hạn độ dài -> subprocess ném lỗi. stdin (utf-8) né cả hai.
        r = subprocess.run([claude, "-p"], input=prompt, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    except Exception:
        return None
    out = (r.stdout or "").strip()
    m = re.search(r"\{.*\}", out, re.S)  # bóc khối JSON đầu tiên (kể cả khi bọc trong ```json)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _find_cache(base, first_num):
    """Tìm thư mục cache chứa Chuong_<first>.txt (đoạn mở đầu giúp tóm tắt sâu hơn). None nếu không có."""
    import glob
    for c in glob.glob(os.path.join(base, "truyen-out", "*", "cache")):
        if os.path.isfile(os.path.join(c, f"Chuong_{first_num}.txt")):
            return c
    return None


def gen_hook(chapters, cache_dir=None):
    """Sinh {title_hook, summary, closing} từ tên chương (+ đoạn mở đầu nếu có cache). None nếu lỗi."""
    base = ENGINE   # truyen-out o goc engine, khong canh script (doi 2026-08-26)
    first, last = chapters[0]["num"], chapters[-1]["num"]
    cdir = cache_dir if (cache_dir and os.path.isdir(cache_dir)) else _find_cache(base, first)
    ctx = []
    for ch in chapters:
        num, name = ch["num"], ch.get("name", "")
        head = ""
        if cdir:
            p = os.path.join(cdir, f"Chuong_{num}.txt")
            if os.path.isfile(p):
                try:
                    body = open(p, encoding="utf-8").read().split("\n\n", 1)[-1].replace("\n", " ")
                    head = " — " + body[:200]
                except Exception:
                    pass
        ctx.append(f"Chương {num}: {name}{head}")
    prompt = (
        "Bạn là biên tập viên kênh audio truyện tiên hiệp 'Nghe Tiên Truyện'. Dưới đây là "
        f"{len(chapters)} chương (số + tên + đoạn mở đầu) của tập audio Phàm Nhân Tu Tiên "
        f"chương {first}-{last}:\n\n" + "\n".join(ctx) + "\n\n"
        "Trả về CHỈ một JSON object (không giải thích, không markdown) gồm 3 khóa:\n"
        '- "title_hook": tiêu đề phụ 4-8 chữ, giật gân đúng diễn biến tập này, KHÔNG spoiler kết, <=40 ký tự.\n'
        '- "summary": 2 đoạn ngắn (tổng 60-110 từ) tóm tắt hấp dẫn tập này, gợi tò mò, tránh spoiler nặng.\n'
        '- "closing": 1 câu hỏi mở dẫn dắt sang tập kế tiếp.\n'
        "Văn phong tiếng Việt, giọng dẫn truyện. KHÔNG nhắc AI/công cụ/giọng máy. Trả JSON thuần."
    )
    d = _claude_json(prompt)
    if not isinstance(d, dict):
        return None
    hook = re.sub(r"[<>\r\n]", " ", str(d.get("title_hook", ""))).strip()[:40]
    summ = str(d.get("summary", "")).strip()
    close = str(d.get("closing", "")).strip()
    return {"title_hook": hook, "summary": summ, "closing": close} if (hook and summ) else None


def build(manifest, cache_dir=None, playlist=PLAYLIST, title_prefix="PNTT", with_hook=True):
    """Dựng (title, desc). playlist/title_prefix đi từ state của TỪNG PHẦN truyện (P1/P2...);
    hằng PLAYLIST chỉ còn là mặc định cho lúc gọi tay. `with_hook=False` = không gọi agent,
    đi thẳng nhánh mô tả tĩnh (dùng cho --dry-run: xem trước không được tốn hạn mức)."""
    man = json.load(open(manifest, encoding="utf-8"))
    chs = man["chapters"]
    first, last = chs[0]["num"], chs[-1]["num"]
    # YouTube cần mốc đầu = 0:00 -> trừ offset của chương đầu (gồm cả 5s lead-in).
    off = float(chs[0]["start"])
    lines = ["⏱ Mốc thời gian từng chương (bấm để nhảy tới):"]
    for ch in chs:
        lines.append(f"{fmt_ts(float(ch['start']) - off)} Chương {ch['num']} – {ch['name']}")
    ts_block = "\n".join(lines)

    if with_hook:
        hook = gen_hook(chs, cache_dir)
    else:
        print("[hook] bỏ qua (dry-run không --with-hook) — mô tả tĩnh, không gọi agent", flush=True)
        hook = None
    if hook:
        title = f"{title_prefix} Chương {first}-{last} | {hook['title_hook']}"[:100]
        parts = [hook["summary"], "", ts_block]
        if hook["closing"]:
            parts += ["", "❓ " + hook["closing"]]
        parts += ["",
                  f"▶️ Nghe trọn bộ trong playlist: {playlist}",
                  "🔔 Đăng ký kênh để mỗi ngày nghe tiếp hành trình tu tiên của Hàn Lập.",
                  "",
                  "📖 Phàm Nhân Tu Tiên — Vong Ngữ | Tiên hiệp · Tu chân · Huyền huyễn."]
        desc = "\n".join(parts)
    else:
        # FALLBACK (claude lỗi/timeout): mô tả tĩnh gọn + timestamps — publish KHÔNG gãy.
        # Phần-suffix ("(P2)") được giữ lại trong tiêu đề: P2 đánh số chương LẠI TỪ 0 nên nếu
        # bỏ suffix, tiêu đề fallback sẽ TRÙNG y hệt video P1 cũ trên cùng kênh.
        # title_prefix "PNTT" (P1) -> suffix rỗng -> tiêu đề giữ NGUYÊN như trước.
        part_sfx = title_prefix.replace("PNTT", "").strip()
        title = (f"Phàm Nhân Tu Tiên{' ' + part_sfx if part_sfx else ''} | Vong Ngữ "
                 f"(Chương {first}-{last})")
        desc = (f"📖 Phàm Nhân Tu Tiên — Vong Ngữ | Tiên hiệp · Tu chân · Huyền huyễn.\n\n"
                f"{ts_block}\n\n"
                f"▶️ Nghe trọn bộ trong playlist: {playlist}\n"
                f"🔔 Đăng ký kênh để nghe tiếp mỗi ngày cùng Hàn Lập.")
    return title, desc, first, last


def set_thumbnail(yu, video_id, video_path, thumb_at, attempts=4):
    """Trích frame thẻ mở đầu (hiện 'Chương <đầu>-<cuối>') tại giây thumb_at -> đặt ảnh đại diện.
    CÓ RETRY: lỗi SSL 'EOF occurred in violation of protocol' hay xảy ra NGAY SAU upload video
    (kết nối cũ chập chờn) -> thử lại với CLIENT + REQUEST MỚI mỗi lần."""
    import shutil
    import subprocess
    import time

    from googleapiclient.http import MediaFileUpload
    ff = shutil.which("ffmpeg") or "ffmpeg"
    thumb = os.path.join(os.path.dirname(os.path.abspath(video_path)), "_thumb.jpg")
    subprocess.run([ff, "-y", "-loglevel", "error", "-ss", str(thumb_at),
                    "-i", video_path, "-frames:v", "1", "-q:v", "2", thumb], check=True)
    last = None
    for k in range(1, attempts + 1):
        try:
            yt = yu._yt()  # client MỚI mỗi lần — tránh kết nối SSL hỏng sau upload
            yt.thumbnails().set(videoId=video_id,
                                media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
            try:
                os.remove(thumb)
            except OSError:
                pass
            print(f"THUMBNAIL_OK (lần {k})")
            return True
        except Exception as exc:
            last = exc
            print(f"[thumb] lần {k}/{attempts} lỗi: {exc}")
            time.sleep(2 * k)
    print(f"[warn] KHÔNG đặt được ảnh đại diện sau {attempts} lần (SSL/network?): {last}")
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="")
    ap.add_argument("--video", required=True)
    ap.add_argument("--set-thumb-only", dest="set_thumb_only", action="store_true",
                    help="CHỈ đặt LẠI ảnh đại diện cho --video-id (không upload).")
    ap.add_argument("--video-id", dest="video_id", default="",
                    help="ID video YouTube (dùng với --set-thumb-only).")
    ap.add_argument("--token", default=DEFAULT_TOKEN,
                    help="đường token kênh truyện (mặc định YT_TOKEN_PATH__NGHE_TIEN_TRUYEN, "
                         "rồi YT_TOKEN_PATH)")
    ap.add_argument("--playlist", default=PLAYLIST)
    ap.add_argument("--title-prefix", dest="title_prefix", default="PNTT",
                    help="Tiền tố tiêu đề video (P1: 'PNTT', P2: 'PNTT (P2)').")
    ap.add_argument("--privacy", default="public")
    ap.add_argument("--thumb-at", dest="thumb_at", type=float, default=3.0,
                    help="Giây trích frame thẻ mở đầu làm ảnh đại diện (hiện dải chương).")
    ap.add_argument("--dry-run", action="store_true",
                    help="chỉ in title+desc, không upload, không gọi agent (mô tả tĩnh)")
    ap.add_argument("--with-hook", dest="with_hook", action="store_true",
                    help="dùng với --dry-run: vẫn gọi agent viết hook (tốn hạn mức, ghi ledger)")
    ap.add_argument("--force", action="store_true", help="bỏ qua kiểm tra tên kênh")
    ap.add_argument("--cache-dir", dest="cache_dir", default="",
                    help="Thư mục cache Chuong_*.txt để tóm tắt sâu hơn (tự dò nếu bỏ trống).")
    args = ap.parse_args(argv)

    # Chế độ CHỈ đặt lại ảnh đại diện (sửa video ĐÃ đăng) — không cần manifest, không upload.
    if args.set_thumb_only:
        if not args.video_id:
            sys.exit("--set-thumb-only cần --video-id")
        if not os.path.isfile(args.video):
            sys.exit(f"Không thấy video: {args.video}")
        os.environ["YT_TOKEN_PATH"] = args.token
        sys.path.insert(0, AINEWS)
        import youtube_upload as yu
        return 0 if set_thumbnail(yu, args.video_id, args.video, args.thumb_at) else 1

    if not args.manifest:
        sys.exit("cần --manifest (hoặc --set-thumb-only --video-id để chỉ đặt ảnh).")
    title, desc, first, last = build(args.manifest, args.cache_dir or None,
                                     args.playlist, args.title_prefix,
                                     with_hook=not args.dry_run or args.with_hook)
    print(f"[playlist] {args.playlist}")   # thấy NGAY đang đăng vào playlist nào (log đêm/Telegram)
    print(f"=== TITLE ===\n{title}\n=== DESCRIPTION ({len(desc)} ký tự) ===\n{desc}\n=== END ===")
    if args.dry_run:
        return 0

    if not os.path.isfile(args.video):
        sys.exit(f"Không thấy video: {args.video}")
    # trỏ youtube_upload sang TOKEN kênh truyện TRƯỚC khi import
    os.environ["YT_TOKEN_PATH"] = args.token
    os.environ["YT_PLAYLIST_DESC"] = INTRO_LONG  # intro tĩnh (tác phẩm/nhân vật/cấp độ) sống ở PLAYLIST
    sys.path.insert(0, AINEWS)
    import youtube_upload as yu

    if not os.path.isfile(args.token):
        _up = os.path.join(AINEWS, 'youtube_upload.py')
        _cmd = (f"(PowerShell):  $env:YT_TOKEN_PATH='{args.token}'; python '{_up}' --auth"
                if os.name == "nt" else
                f"(sh):  YT_TOKEN_PATH='{args.token}' python3 '{_up}' --auth")
        sys.exit(f"CHƯA có token kênh truyện: {args.token}\n"
                 f"  Chạy 1 lần {_cmd}\n"
                 f"  -> đăng nhập Google, ở màn chọn kênh hãy chọn 'Nghe Tiên Truyện'.")

    # ---- AN TOÀN: xác minh token đang trỏ ĐÚNG kênh truyện, tránh đăng nhầm kênh AI ----
    yt = yu._yt()
    chans = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    cname = chans[0]["snippet"]["title"] if chans else "?"
    print(f"[kênh] token đang gắn: {cname}")
    if not args.force and "tiên truyện" not in cname.lower():
        sys.exit(f"DỪNG: token gắn kênh '{cname}', KHÔNG phải 'Nghe Tiên Truyện'. "
                 f"Auth lại đúng kênh, hoặc --force nếu chắc chắn.")

    vid = yu.upload(args.video, title, desc, TAGS, args.privacy,
                    playlist=args.playlist, category="24")  # 24 = Entertainment

    # ---- ẢNH ĐẠI DIỆN = frame thẻ mở đầu (hiện "Chương <đầu>-<cuối>"), CÓ retry SSL ----
    set_thumbnail(yu, vid, args.video, args.thumb_at)

    print(f"PUBLISHED https://youtu.be/{vid}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
