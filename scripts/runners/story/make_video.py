# -*- coding: utf-8 -*-
"""make_video.py — turn a narrated story (audio + manifest from read_story.py) into a finished
MP4 like the YouTube reference:
  - looping background video
  - looping background music (low volume), kept under the narration
  - per-chapter title overlay "CHƯƠNG <số>" + "<tên>" that fades IN/OUT at each chapter start
  - outro audio appended at the very end
  - video + audio fade in at start and fade out at the end
Uses the system (Gyan) ffmpeg.

Example:
  python make_video.py --manifest ".../sample_voice.mp3.manifest.json" --out ".../sample.mp4"
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# Script da doi sang apps/truyen/ (2026-08-26). DU LIEU (venv, assets, truyen-out,
# _vtitles, voices) VAN O GOC ENGINE - neo vao day, khong neo vao HERE.
import truyen_paths  # noqa: E402  — phân giải Windows + macOS
ENGINE = truyen_paths.engine_dir()
# Asset (nền/nhạc/logo/lửa) để LOCAL trong trạm giọng — CỐ Ý không đọc thẳng từ thư mục
# đồng bộ đám mây: 07/2026 đổi tài khoản đồng bộ làm mọi hardcode cũ chết, pipeline đứt mà
# không ai biết. Bản local còn tránh luôn rủi ro tệp chỉ-trên-mây treo >60s.
# Nguồn gốc (đồng bộ tay khi đổi asset): …\Nghe Tiên Truyện\2. Raw Media\Ảnh & Media
ASSETS = os.path.join(ENGINE, "assets")
# Bản "clean" re-encode 1 luồng (bản gốc có frame hỏng làm h264 segfault khi loop video 2 tiếng).
BG = os.path.join(ASSETS, "Background Image Tiên hiệp 1 clean.mp4")
if not os.path.isfile(BG):
    BG = os.path.join(ASSETS, "Background Image Tiên hiệp 1.mp4")
BGM = os.path.join(ASSETS, "Nhạc nền tiên hiệp 1.mp3")
OUTRO = os.path.join(ASSETS, "Outro PNTT.mp3")
INTRO = os.path.join(ASSETS, "Intro PNTT.mp3")
LOGO = os.path.join(ASSETS, "Logo nghe tiên truyện 2.png")
FIRE = os.path.join(ASSETS, "Lửa tiêu đề clean.mp4")  # clip lửa-trên-nền-đen (Mixkit License)
if not os.path.isfile(FIRE):  # bản gốc có frame hỏng → h264 crash khi loop; dùng bản clean re-encode
    FIRE = os.path.join(ASSETS, "Lửa tiêu đề.mp4")
# Font + title textfiles live INSIDE TITLE_DIR and are referenced by RELATIVE name from there
# (ffmpeg is run with cwd=TITLE_DIR). A drive-letter ':' inside a filtergraph path makes ffmpeg's
# parser fail no matter how it's escaped, so we avoid colons in filtergraph paths entirely.
# Font tiêu đề phải có dấu tiếng Việt: TRUYEN_FONT → <engine>/assets/fonts/title.ttf → font hệ
# thống theo OS (Windows arialbd.ttf, macOS Arial Bold.ttf). Thiếu thì DỪNG, không im lặng mất dấu.
# Phân giải LÚC DỰNG (main), không lúc import.
TITLE_DIR = os.path.join(ENGINE, "_vtitles")   # KHONG hardcode duong dan may


def ffexe(name):
    return shutil.which(name) or name


def dur(path):
    r = subprocess.run([ffexe("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nokey=1:noprint_wrappers=1", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def build_looped_bg(src, total, workdir):
    """Nối `src` (clip nền liền-mạch, no-bframe) đủ dài >= total bằng CONCAT DEMUXER `-c copy`
    (COPY packet, KHÔNG decode) → 1 file LINEAR. Tránh HẲN bug ffmpeg `-stream_loop` gây
    cabac decode error + crash 0xc0000005 ở mốc lặp (non-deterministic, càng dài càng chắc chết
    — xem memory project_nghe_tien_truyen). Trả None nếu lỗi → caller fallback `-stream_loop`."""
    try:
        clip = dur(src)
        if clip <= 0:
            return None
        n = int(total // clip) + 2
        listf = os.path.join(workdir, "_bglist.txt")
        with open(listf, "w", encoding="utf-8", newline="\n") as f:
            f.write(("file '" + os.path.abspath(src).replace("\\", "/") + "'\n") * n)
        outf = os.path.join(workdir, "_bgloop.mp4")
        rc = subprocess.run([ffexe("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                             "-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", outf]).returncode
        return outf if (rc == 0 and os.path.isfile(outf)) else None
    except Exception:
        return None


SUB_BAND = "iw:ih*0.20:0:ih*0.78"      # dải phụ đề: 20% dưới (Alignment=2, MarginV=30)
CTRL_BAND = "iw:ih*0.45:0:ih*0.05"     # dải đối chứng: nửa trên, KHÔNG bao giờ có phụ đề


def _psnr_band(ref, test, t, crop):
    """PSNR giữa 1 khung của `ref` và `test` tại giây `t`, chỉ trong vùng `crop`."""
    fc = f"[0:v]crop={crop},format=gray[a];[1:v]crop={crop},format=gray[b];[a][b]psnr"
    p = subprocess.run([ffexe("ffmpeg"), "-hide_banner", "-v", "info",
                        "-ss", f"{t:.3f}", "-i", ref, "-ss", f"{t:.3f}", "-i", test,
                        "-filter_complex", fc, "-frames:v", "1", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"PSNR\s+y:([0-9.]+|inf)", p.stderr or "")
    if not m:
        return None
    return float("inf") if m.group(1) == "inf" else float(m.group(1))


def _cue_times(srt_path):
    """Mốc GIỮA của các cue đủ dài — đo đúng lúc chữ đang nằm trên màn hình."""
    try:
        txt = open(srt_path, encoding="utf-8-sig", errors="replace").read()
    except OSError:
        return []
    pat = re.compile(r"(\d\d):(\d\d):(\d\d),(\d{3})\s*-->\s*(\d\d):(\d\d):(\d\d),(\d{3})")
    out = []
    for m in pat.finditer(txt):
        g = [int(x) for x in m.groups()]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        b = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        if b - a >= 0.8:
            out.append((a + b) / 2.0)
    return out


def subs_really_burned(ref_nosubs, out_abs, srt_path):
    """ĐO xem phụ đề có THẬT SỰ nằm trên khung hình không — KHÔNG tin returncode.

    Vì sao phải đo: 14/09/2026 pass 2 hỏng 4/4 lần, code copy bản không phụ đề ra rồi báo
    thành công; video lên YouTube thiếu phụ đề mà mọi thứ vẫn ✅. Bốn tập đã hỏng theo kiểu
    "xanh giả" này. `rc == 0` KHÔNG đồng nghĩa có phụ đề.

    Phép đo VI SAI: pass 2 mã hoá lại nên MỌI điểm ảnh đều lệch chút ít so với bản nền —
    so sánh tuyệt đối vô nghĩa. Ta so dải phụ đề với dải đối chứng:
      có phụ đề    -> dải phụ đề khác HẲN (đo 20/09: chênh 24-36 dB)
      không phụ đề -> hai dải lệch như nhau (đo 20/09: chênh -0,9 dB)
    Ngưỡng 6 dB nằm giữa hai cụm, biên rất rộng.
    """
    times = _cue_times(srt_path)
    if not times:
        return None, "không đọc được cue nào từ srt -> không kết luận được"
    picks = [times[int(len(times) * f)] for f in (0.05, 0.5, 0.9) if int(len(times) * f) < len(times)]
    hits, detail = 0, []
    for t in picks:
        ps = _psnr_band(ref_nosubs, out_abs, t, SUB_BAND)
        pc = _psnr_band(ref_nosubs, out_abs, t, CTRL_BAND)
        if ps is None or pc is None:
            detail.append(f"t={t:.1f}s:không đo được")
            continue
        hit = (pc - ps) >= 6.0 and ps < 40.0
        hits += hit
        detail.append(f"t={t:.1f}s:{'CÓ' if hit else 'KHÔNG'}(phụ đề {ps:.1f}dB/đối chứng {pc:.1f}dB)")
    return (hits >= max(1, len(picks) - 1)), "  ".join(detail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--show", type=float, default=6.0, help="giây hiển thị tên mỗi chương")
    ap.add_argument("--fade", type=float, default=0.8, help="fade in/out của text (giây)")
    ap.add_argument("--bgm-vol", dest="bgm_vol", type=float, default=0.06)  # 1/2 mức cũ (0.12)
    ap.add_argument("--no-outro", action="store_true")
    ap.add_argument("--vfade", type=float, default=1.5, help="fade in/out toàn video (giây)")
    ap.add_argument("--title-scale", dest="title_scale", type=float, default=2.0,
                    help="hệ số phóng to chữ tiêu đề (2.0 = gấp đôi)")
    ap.add_argument("--no-logo", action="store_true")
    ap.add_argument("--logo-w", dest="logo_w", type=int, default=150, help="bề rộng logo (px)")
    ap.add_argument("--pad", type=int, default=26, help="lề logo từ góc (px)")
    ap.add_argument("--no-subs", action="store_true")
    ap.add_argument("--sub-size", dest="sub_size", type=int, default=18, help="cỡ chữ phụ đề")
    ap.add_argument("--bgm-file", dest="bgm_file", default=None,
                    help="Ghi đè nhạc nền (mặc định 'Nhạc nền tiên hiệp 1.mp3').")
    # --- hiệu ứng lửa THẬT (Mức 2): clip lửa-trên-nền-đen ghép sau chữ tiêu đề ---
    ap.add_argument("--fire-file", dest="fire_file", default=None,
                    help="Clip lửa-trên-nền-đen ghép quanh tiêu đề (mặc định asset 'Lửa tiêu đề.mp4').")
    ap.add_argument("--no-fire", dest="no_fire", action="store_true", help="Tắt lửa thật.")
    ap.add_argument("--fire-opacity", dest="fire_opacity", type=float, default=0.90,
                    help="Độ đậm của lửa (0-1).")
    ap.add_argument("--fire-h", dest="fire_h", type=float, default=0.20,
                    help="Chiều cao dải lửa (tỉ lệ H). Nhỏ = băng mỏng.")
    ap.add_argument("--fire-y", dest="fire_y", type=float, default=0.09,
                    help="Mép trên dải lửa (tỉ lệ H). Đặt trên đầu dòng chữ.")
    ap.add_argument("--flicker-rate", dest="flicker_rate", type=float, default=3.0,
                    help="Tốc độ nhấp nháy chữ (rad/s; thấp = chậm hơn. Cũ=20).")
    args = ap.parse_args()

    bgm = os.path.abspath(args.bgm_file) if args.bgm_file else BGM
    if not os.path.isfile(bgm):
        raise SystemExit(f"Không thấy file nhạc nền: {bgm}")

    man = json.load(open(args.manifest, encoding="utf-8"))
    voice = man["audio"]
    voice_dur = float(man["voice_dur"])
    chapters = man["chapters"]
    W, H = args.w, args.h
    use_outro = (not args.no_outro) and os.path.isfile(OUTRO)
    outro_dur = dur(OUTRO) if use_outro else 0.0
    total = voice_dur + outro_dur
    os.makedirs(TITLE_DIR, exist_ok=True)
    for f in os.listdir(TITLE_DIR):  # clear leftovers so libass doesn't scan them as "fonts"
        if f.endswith((".mp4", ".srt", ".txt")):
            try:
                os.remove(os.path.join(TITLE_DIR, f))
            except OSError:
                pass
    shutil.copyfile(truyen_paths.title_font(ENGINE), os.path.join(TITLE_DIR, "font.ttf"))  # relative font, no drive colon

    use_logo = (not args.no_logo) and os.path.isfile(LOGO)
    logo_idx = (3 + (1 if use_outro else 0)) if use_logo else None  # input index after audio inputs
    fire_path = os.path.abspath(args.fire_file) if args.fire_file else FIRE
    use_fire = False  # BỎ lửa (2026-06-20, user) — tiêu đề chỉ fade in/out
    fire_idx = (3 + (1 if use_outro else 0) + (1 if use_logo else 0)) if use_fire else None
    srt = man.get("srt")
    use_subs = (not args.no_subs) and bool(srt) and os.path.isfile(srt) and os.path.getsize(srt) > 0
    if use_subs:
        shutil.copyfile(srt, os.path.join(TITLE_DIR, "sub.srt"))
    ts = args.title_scale
    fs1, fs2 = int(50 * ts), int(34 * ts)          # cỡ chữ (đã giảm; tên chương tự xuống dòng)
    gb1, gb2 = int(10 * ts), int(8 * ts)           # quầng cam (glow halo)
    cb = max(2, int(2 * ts))                       # viền chữ sắc nét

    # ---- VIDEO: bg loop -> [thẻ MỞ ĐẦU: dải chương] -> tiêu đề từng chương (lửa) ->
    #             logo -> subtitles -> global fade ----
    first_n, last_n = chapters[0]["num"], chapters[-1]["num"]
    lead = float(chapters[0]["start"])  # = lead-in (mọi mốc đã dời +lead trong read_story)
    # Thẻ mở đầu: hiện "PHÀM NHÂN TU TIÊN / Chương <đầu> - <cuối>" trong lúc 'chờ' đầu video,
    # cùng format+hiệu ứng tiêu đề chương, rồi fade trước khi vào chương 1.
    intro_win = (0.3, lead - 0.4) if lead >= (0.3 + 2 * args.fade + 0.4) else None

    def wrap_text(text, max_chars):
        """Bẻ dòng theo TỪ để mỗi dòng <= max_chars (không cắt giữa từ)."""
        words, lines, cur = text.split(), [], ""
        for w in words:
            if cur and len(cur) + 1 + len(w) > max_chars:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w) if cur else w
        if cur:
            lines.append(cur)
        return lines or [text]

    def title_block(in_label, s, e, line1, line2, tag):
        """Dòng 1 (CHƯƠNG n) + TÊN chương tự XUỐNG DÒNG cho vừa bề ngang. Quầng cam + chữ vàng,
        chỉ fade in/out (KHÔNG lửa, KHÔNG nhấp nháy)."""
        fd = args.fade
        env = f"max(0\\,min(min(1\\,(t-{s:.3f})/{fd})\\,({e:.3f}-t)/{fd}))"
        en = f"between(t\\,{s:.3f}\\,{e:.3f})"
        aC, aG = env, f"{env}*0.6"
        # số ký tự/dòng để KHÔNG tràn ngang (Arial bold ~0.52*fontsize mỗi ký tự, chừa lề 8%)
        max_chars = max(8, int(W * 0.92 / (fs2 * 0.52)))
        parts = [(line1, fs1, gb1, "0xFFE38A")] + [
            (ln, fs2, gb2, "0xFFD27A") for ln in wrap_text(line2, max_chars)]
        y = int(H * 0.30)
        cur = in_label
        for i, (txt, sz, gb, col) in enumerate(parts):
            nm = f"{tag}_{i}.txt"
            open(os.path.join(TITLE_DIR, nm), "w", encoding="utf-8", newline="\n").write(txt)
            v.append(f"[{cur}]drawtext=fontfile=font.ttf:textfile={nm}:fontsize={sz}:x=(w-tw)/2:y={y}:"
                     f"fontcolor=0xFF4500:borderw={gb}:bordercolor=0xFF9A2A:alpha={aG}:enable={en}[g{i}_{tag}]")
            v.append(f"[g{i}_{tag}]drawtext=fontfile=font.ttf:textfile={nm}:fontsize={sz}:x=(w-tw)/2:y={y}:"
                     f"fontcolor={col}:borderw={cb}:bordercolor=0x5C1200:"
                     f"shadowcolor=0x000000@0.55:shadowx=2:shadowy=2:alpha={aC}:enable={en}[c{i}_{tag}]")
            cur = f"c{i}_{tag}"
            y += int(sz * 1.18)
        return cur

    v = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
         f"setsar=1,fps=30,trim=0:{total:.3f},setpts=PTS-STARTPTS[bg]"]
    cur = "bg"
    # ---- LỬA THẬT (Mức 2): clip lửa-trên-nền-đen -> bỏ nền đen (lumakey) -> dải ngang trên chữ,
    #      CHỈ hiện trong cửa sổ tiêu đề (gồm cả thẻ mở đầu) ----
    if use_fire:
        FH = int(args.fire_h * H)     # chiều cao dải lửa (băng ngang mỏng)
        FY = int(args.fire_y * H)     # mép trên dải lửa (đặt TRÊN đầu dòng chữ)
        wins = []
        if intro_win:
            wins.append(f"between(t\\,{intro_win[0]:.3f}\\,{intro_win[1]:.3f})")
        for ch in chapters:
            s = float(ch["start"]); e = min(s + args.show, voice_dur)
            wins.append(f"between(t\\,{s:.3f}\\,{e:.3f})")
        union = "+".join(wins)
        # LOOP bằng FILTER (không dùng -stream_loop ở input: clip lửa 15s bị crash ở mốc lặp).
        fire_frames = max(1, int(dur(fire_path) * 30) - 1)
        v.append(f"[{fire_idx}:v]fps=30,scale={W}:{FH},setsar=1,format=yuva420p,"
                 f"lumakey=0.06:0.20:0.10,colorchannelmixer=aa={args.fire_opacity:.2f},"
                 f"loop=loop=-1:size={fire_frames}:start=0,setpts=N/(30*TB)[fa]")
        v.append(f"[bg][fa]overlay=0:{FY}:enable='{union}':eof_action=pass[bgf]")
        cur = "bgf"
    if intro_win:
        cur = title_block(cur, intro_win[0], intro_win[1],
                          "PHÀM NHÂN TU TIÊN", f"Chương {first_n} - {last_n}", "intro")
    for ch in chapters:
        s = float(ch["start"])
        e = min(s + args.show, voice_dur)
        cur = title_block(cur, s, e, f"CHƯƠNG {ch['num']}", ch["name"], f"c{ch['num']}")
    if use_logo:
        v.append(f"[{logo_idx}:v]scale={args.logo_w}:-1[lg]")
        v.append(f"[{cur}][lg]overlay=W-w-{args.pad}:{args.pad}[vlg]")
        cur = "vlg"
    # Phụ đề KHÔNG nằm trong graph này — burn ở pass 2 riêng (libass crash 0xC0000005 khi
    # chạy trong filtergraph phức tạp; tách pass đơn giản + fallback => không bao giờ corrupt).
    v.append(f"[{cur}]fade=t=in:st=0:d={args.vfade},"
             f"fade=t=out:st={max(0, total - args.vfade):.3f}:d={args.vfade}[v]")

    # ---- AUDIO: (voice [+ outro]) mixed under looped bgm, with global fade in/out ----
    a = []
    a.append(f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,asetpts=PTS-STARTPTS[vo]")
    if use_outro:
        a.append(f"[3:a]aformat=sample_rates=44100:channel_layouts=stereo,asetpts=PTS-STARTPTS[ou]")
        a.append(f"[vo][ou]concat=n=2:v=0:a=1[narr]")
    else:
        a.append(f"[vo]anull[narr]")
    a.append(f"[2:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={args.bgm_vol},"
             f"atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
             f"afade=t=out:st={max(0, total - 3):.3f}:d=3[bgm]")
    a.append(f"[narr][bgm]amix=inputs=2:duration=first:normalize=0[mx]")
    a.append(f"[mx]afade=t=in:st=0:d={args.vfade},"
             f"afade=t=out:st={max(0, total - args.vfade):.3f}:d={args.vfade}[a]")

    filtergraph = ";".join(v + a)
    out_abs = os.path.abspath(args.out)
    pass1_out = os.path.join(TITLE_DIR, "_pass1.mp4") if use_subs else out_abs

    print(f"[video] {W}x{H}, voice {voice_dur:.1f}s + outro {outro_dur:.1f}s = {total:.1f}s, "
          f"{len(chapters)} chương | text x{ts} | logo={'có' if use_logo else 'không'} | "
          f"phụ đề={'có' if use_subs else 'không'} | outro={'có' if use_outro else 'không'} | "
          f"lửa={'có' if use_fire else 'không'} (flicker {args.flicker_rate})")

    # ---- PASS 1: video (nền+tiêu đề+logo+audio), KHÔNG phụ đề — ổn định ----
    # Nền: nối sẵn bằng concat-copy thành 1 file LINEAR đủ dài (no `-stream_loop` → hết crash
    # 0xc0000005 ở mốc lặp). Fallback `-stream_loop` nếu concat lỗi (best-effort).
    bg_lin = build_looped_bg(BG, total, TITLE_DIR)
    bg_in = (["-i", bg_lin] if bg_lin
             else ["-stream_loop", "-1", "-err_detect", "ignore_err", "-i", BG])
    # -err_detect ignore_err: clip lửa có vài frame hỏng (decode glitch) → bỏ qua, KHÔNG abort.
    cmd = [ffexe("ffmpeg"), "-y", "-hide_banner", "-loglevel", "warning", "-stats",
           *bg_in, "-i", voice, "-stream_loop", "-1", "-i", bgm]
    if use_outro:
        cmd += ["-i", OUTRO]
    if use_logo:
        cmd += ["-i", LOGO]
    if use_fire:
        cmd += ["-err_detect", "ignore_err", "-i", fire_path]  # loop bằng filter, không stream_loop
    # -filter_complex_threads 1: bộ lọc 1 luồng — chậm hơn nhưng hết crash đua-luồng
    # (loop+overlay+nhiều drawtext) ở mốc lặp clip lửa. Encode libx264 vẫn đa luồng.
    cmd += ["-filter_complex_threads", "1",
            "-filter_complex", filtergraph, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
            "-movflags", "+faststart", pass1_out]
    print("[video] pass 1/2 — dựng video (không phụ đề) ...")
    _rc = subprocess.run(cmd, cwd=TITLE_DIR).returncode
    if _rc != 0:
        print("FFMPEG_CMD: " + " ".join((f'"{c}"' if (" " in c or ";" in c) else c) for c in cmd))
        raise SystemExit(f"FFMPEG pass 1 (video nền) lỗi (returncode={_rc} / hex={_rc & 0xFFFFFFFF:#010x}).")

    # ---- PASS 2: burn phụ đề riêng; fail thì giữ bản không phụ đề (luôn ra video hợp lệ) ----
    if use_subs:
        style = ("FontName=Arial\\,FontSize=%d\\,PrimaryColour=&H00FFFFFF\\,"
                 "OutlineColour=&H00000000\\,BorderStyle=1\\,Outline=2\\,Shadow=0\\,"
                 "Alignment=2\\,MarginV=30") % args.sub_size
        sub_cmd = [ffexe("ffmpeg"), "-y", "-hide_banner", "-loglevel", "warning", "-stats",
                   "-i", pass1_out, "-filter_complex_threads", "1",
                   "-filter_complex", f"[0:v]subtitles=sub.srt:force_style={style}[v]",
                   "-map", "[v]", "-map", "0:a", "-c:a", "copy",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", out_abs]
        ok = False
        # Không tất định. Đo trên 29 log 19/08-14/09: ~71% số LẦN THỬ hỏng, 8/29 lượt hỏng cả
        # 4 lần (0,71^4 = 25% ≈ 28% quan sát được). NHƯNG đo lại 20/09 ở đúng quy mô thật
        # (input 1,87 GB / 8013 s): 11/11 lần SẠCH. Tức bệnh KHÔNG tái hiện được nữa trên máy
        # này — chưa rõ vì sao (nghi tranh chấp tài nguyên lúc 03:00: cùng giờ còn 6 task
        # update Office/Adobe/OneDrive/PCA chạy chung). Vì chưa chốt được nguyên nhân, GIỮ
        # nguyên vòng thử lại 4 lần và thêm cổng đo phụ đề bên dưới.
        for attempt in range(4):
            print(f"[video] pass 2/2 — burn phụ đề (lần {attempt + 1}) ...")
            rc = subprocess.run(sub_cmd, cwd=TITLE_DIR).returncode
            if rc != 0 or not os.path.isfile(out_abs):
                # GHI LẠI MÃ THOÁT. Bản cũ vứt đi nên không ai biết nó chết vì gì: 0xC0000005
                # (sập thật) khác hẳn rc=1 (thiếu file/sai tham số) — hai bệnh, hai cách chữa.
                print(f"[video] pass 2 lần {attempt + 1} HỎNG: returncode={rc} "
                      f"/ hex={rc & 0xFFFFFFFF:#010x}")
                time.sleep(10)
                continue
            # rc==0 CHƯA đủ: phải ĐO phụ đề có thật trên khung hình không (xem subs_really_burned)
            burned, why = subs_really_burned(pass1_out, out_abs, os.path.join(TITLE_DIR, "sub.srt"))
            if burned is None:
                print(f"[video] ⚠ không kiểm được phụ đề ({why}) — chấp nhận theo returncode.")
                ok = True
                break
            print(f"[video] kiểm phụ đề bằng điểm ảnh: {why}")
            if burned:
                ok = True
                break
            print(f"[video] ⚠ pass 2 lần {attempt + 1} rc=0 NHƯNG khung hình KHÔNG có phụ đề "
                  f"— coi như hỏng, thử lại.")
            time.sleep(10)
        if not ok:
            # KHÔNG im lặng: 14/09 video thiếu phụ đề vẫn lên YouTube kèm ✅ vì dòng này quá hiền.
            # Dòng bắt đầu bằng '[' nên khớp $stepRe của notify-run.ps1 -> hiện trong Telegram.
            print("[video] ⚠⚠ PHỤ ĐỀ HỎNG 4/4 LẦN — video XUẤT RA KHÔNG CÓ PHỤ ĐỀ.")
            print("[video] ⚠⚠ Vẫn giữ bản không phụ đề (hợp lệ, đăng được) nhưng CẦN DỰNG LẠI.")
            shutil.copyfile(pass1_out, out_abs)
        try:
            os.remove(pass1_out)
        except OSError:
            pass
    for tmp in ("_bgloop.mp4", "_bglist.txt"):  # dọn nền linear tạm
        try:
            os.remove(os.path.join(TITLE_DIR, tmp))
        except OSError:
            pass
    print(f"[done] -> {out_abs} ({dur(out_abs):.1f}s)")


if __name__ == "__main__":
    main()
