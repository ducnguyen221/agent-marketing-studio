# -*- coding: utf-8 -*-
"""daily_truyen.py — chạy 1 lần/ngày: lấy N chương TIẾP THEO của Phàm Nhân Tu Tiên, dựng 1 video
(giọng A-Tũn + nhạc nền tiên hiệp 2 + ngọn lửa ngang trên tiêu đề), lưu THẲNG vào
"truyen-out\\out\\PNTT <đầu>-<cuối>.mp4" (LOCAL, cạnh script), ĐĂNG CÔNG KHAI lên kênh
@nghe-tien-truyen (playlist "Phàm Nhân Tu Tiên (P1)") kèm mốc thời gian từng chương, rồi
XOÁ mọi file phụ (mp3/json/srt/cache/scratch) — chỉ giữ lại đúng 1 video.

Tiến độ theo truyen-state.json (last_end). Chỉ tăng tiến độ KHI DỰNG VIDEO XONG (publish là
best-effort: thiếu token thì bỏ qua, video vẫn nằm ở truyen-out\\out để đăng tay sau).
Dùng bởi Windows Task Scheduler (3h sáng).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Script da doi sang apps/truyen/ (2026-08-26). DU LIEU (venv, assets, truyen-out,
# _vtitles, voices) VAN O GOC ENGINE - neo vao day, khong neo vao HERE.
# Phân giải đường (Windows + macOS) gom ở truyen_paths.py: OMNIVOICE_DIR → VOICE_STATION/omnivoice.
import truyen_paths  # noqa: E402
ENGINE = truyen_paths.engine_dir()
PY = truyen_paths.venv_python(ENGINE)            # venv torch (đọc + dựng video)
# Python cho bước publish (cần google-api-python-client): dò LÚC ĐĂNG bằng
# truyen_paths.publish_python() — TRUYEN_PUBLISH_PY → python/python3/py trên PATH.
# State MẶC ĐỊNH = state P1 ở gốc (giữ hành vi cũ cho ai gọi trần). Từ 14/08/2026 mỗi PHẦN
# truyện có state riêng trong pham_nhan_tu_tien_phan_<n>\ và được truyền qua --state.
# Bản trong repo (`scripts/runners/story/`) KHÔNG có state cạnh script: state là DỮ LIỆU của
# chiến dịch trong trạm, nên `--state` là bắt buộc (runner `run-daily-truyen.ps1` luôn truyền).
DEFAULT_STATE = None
LOGDIR = os.path.join(ENGINE, "truyen-out", "daily-logs")
WORK = os.path.join(ENGINE, "truyen-out", "_work")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", HF_HUB_OFFLINE="0")

# TẤT CẢ để LOCAL trong trạm giọng — không ghi/đọc gì trên thư mục đồng bộ đám mây.
# 07/2026: đổi tài khoản đồng bộ làm cây thư mục làm việc đổi đường; mọi path hardcode cũ
# chết cùng lúc.
# Thêm nữa: mỗi video ~1,5-2 GB × 3 lần/ngày sync lên cloud hoàn toàn vô ích vì xoá ngay
# sau khi đăng YouTube xong.
ASSETS = os.path.join(ENGINE, "assets")
OUT_DIR = os.path.join(ENGINE, "truyen-out", "out")
BGM2 = os.path.join(ASSETS, "Nhạc nền tiên hiệp 2.mp3")
VOICE = "a-tun"          # giọng cũ — giữ làm phao cứu sinh, xem pick_voice()

# Luân phiên HAI giọng — Đức quyết 31/08/2026 sau khi nghe A/B.
# Pool cũ ["a-tun-v1","a-tun-v2","a-tun-v3"] đã bỏ: clone chép cả NHỊP NÓI của clip mẫu
# nên luân phiên = đổi tốc độ đọc theo ngày. Tốc độ đo trên cùng một đoạn (speed 0.9):
#     a-tun 2.53  ·  a-tun-v1 2.55 (+0.8%)  ·  a-tun-v3 2.89 (+14%)
# a-tun và a-tun-v1 lệch nhau 0.8% — tai gần như không phân biệt được về nhịp, nên
# luân phiên giữa hai giọng này AN TOÀN, vẫn có chút đổi màu giọng giữa các tập.
# v2/v3 KHÔNG quay lại vòng: v3 nhanh hơn 14% và từng làm giọng "nhanh, ngang cứng".
# Âm lượng đã chuẩn ở tầng engine (mcp_server.normalize_rms) nên đổi giọng không đổi độ to.
# `a-tun-truyen-ma` vẫn ngoài vòng — khác thể loại.
VOICE_POOL = ["a-tun", "a-tun-v1"]


def pick_voice(voices_dir=None, today=None, end=None, batch=10):
    """Chọn giọng luân phiên trong VOICE_POOL.

    Có `end` (chương cuối YÊU CẦU của dải) ⇒ chọn theo DẢI CHƯƠNG: `(end // batch) % n`.
    Chạy lại cùng dải (lượt trước bị giết / build lỗi) ra ĐÚNG giọng cũ ⇒ cùng thư mục cache
    `truyen-out/<slug>__<giọng>` ⇒ resume được chương đã đọc (F1-ANALYSIS §7.4). Theo ngày thì
    hôm sau đổi giọng, cache hôm trước vô dụng. Mốc `end // batch` giữ đúng nhịp đã chạy:
    dải 271-280 (29/09) = a-tun, 281-290 = a-tun-v1, …

    Không có `end` ⇒ hành vi cũ theo ngày trong năm (giữ cho ai gọi trần).

    Profile nào thiếu file thì BỎ QUA thay vì làm gãy cả lượt chạy đêm — và nếu không còn
    profile nào thì rơi về giọng cũ `a-tun`.
    """
    import datetime
    voices_dir = voices_dir or os.path.join(ENGINE, "voices")
    have = [v for v in VOICE_POOL if os.path.isfile(os.path.join(voices_dir, v + ".wav"))]
    if not have:
        return VOICE
    if end is not None:
        return have[(int(end) // max(1, int(batch))) % len(have)]
    doy = (today or datetime.date.today()).timetuple().tm_yday
    return have[doy % len(have)]


# Dấu "dải đang dở": ghi SAU sweep ở đầu lượt, xoá khi lượt ghi xong tiến độ. Lượt bị giết /
# build lỗi thì dấu còn đó ⇒ lượt sau cùng (slug, dải, giọng) được chừa thư mục cache chương.
# Tên KHÔNG chứa "log" (sweep giữ mọi tên có "log" — không muốn dấu sống mãi vì lý do đó).
RESUME_MARK = "_resume.json"


def cache_dir_name(slug, vtag):
    """Tên thư mục cache wav theo giọng — khớp audio_truyen.py (read_out_dir)."""
    return slug + vtag.replace("_", "__")


def resume_keep(mark, slug, start, end, voice):
    """-> tập tên trong truyen-out được chừa khi sweep (rỗng nếu dấu không khớp lượt này)."""
    want = {"slug": slug, "start": int(start), "end": int(end), "voice": voice}
    if not isinstance(mark, dict) or any(mark.get(k) != v for k, v in want.items()):
        return set()
    name = mark.get("cache_dir")
    return {name, RESUME_MARK} if name else set()
# Token kênh truyện: CON TRỎ `YT_TOKEN_PATH__NGHE_TIEN_TRUYEN` (đường dẫn tới file trong kho
# secret của máy), KHÔNG đường lùi viết trong mã — tên tài khoản là dữ liệu của máy, không
# phải của repo. Windows: biến vừa setx chưa tới tiến trình thì đọc registry (truyen_paths).
TOKEN_TRUYEN = os.path.expanduser(truyen_paths.getenv("YT_TOKEN_PATH__NGHE_TIEN_TRUYEN") or "")
ENDING_TEXT = ("Tập hôm nay của chúng ta tạm dừng tại đây, cảm ơn các thính giả đã lắng nghe "
               "và đừng quên nhấn nút theo dõi để đón chờ những tập mới và cùng tại hạ dõi theo "
               "con đường tu tiên của Hàn Lập nhé.")


def _drop_readonly(func, path, _exc=None):
    """Gỡ cờ ReadOnly rồi thử lại — handler cho shutil.rmtree.

    Windows: thư mục mang FILE_ATTRIBUTE_READONLY thì RemoveDirectory() trả về
    ERROR_ACCESS_DENIED (WinError 5) — KHÔNG phải lỗi quyền/ACL, cũng không phải file đang
    bị giữ. Cờ này nằm rải khắp `<engine>/**` của trạm giọng Windows (đo 2026-09-20: truyen-out, out, _work,
    _vtitles, pntt-p2__atun*/cache đều có) nên rmtree chết ngay ở os.rmdir cuối cùng và báo
    đúng đường dẫn CỦA CHÍNH THƯ MỤC ĐÓ — dấu vân tay của bệnh này.
    os.chmod(..., S_IWRITE) xoá cờ đó; với thư mục Windows bỏ qua phần bit quyền.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def rm_path(p):
    """Xoá file/thư mục, chịu được cờ ReadOnly. Ném OSError nếu vẫn không xoá nổi."""
    if os.path.isdir(p) and not os.path.islink(p):
        if sys.version_info >= (3, 12):      # 3.12 đổi tên onerror -> onexc (onerror deprecated)
            shutil.rmtree(p, onexc=_drop_readonly)
        else:
            shutil.rmtree(p, onerror=lambda f, pa, e: _drop_readonly(f, pa, e))
        return
    try:
        os.remove(p)
    except PermissionError:
        _drop_readonly(os.remove, p)


def sweep_old(st, log, keep=()):
    """Dọn sản phẩm của lần chạy TRƯỚC. Chạy ở ĐẦU run này, KHÔNG phải cuối run trước.

    Vì sao đầu-run-sau chứ không phải cuối-run-này:
      - mp3 / wav / txt / manifest / srt / video của run vừa chạy được GIỮ NGUYÊN tới lần
        chạy kế tiếp -> lỗi gì còn nguyên hiện trường mà truy vết (trước đây dọn ngay,
        hỏng là mất sạch dấu vết).
      - video vừa đăng còn nằm đó phòng khi YouTube xử lý chậm / cần đăng lại.
    CHỈ dọn khi run trước publish OK. Publish lỗi -> giữ TẤT CẢ để đăng tay + truy vết.
    GIỮ mọi log. Chỉ đụng "PNTT *.mp4" trong OUT_DIR -> thư mục assets/ nằm ngoài OUT_DIR
    nên không bao giờ bị quét.
    Lỗi xoá 1 file không được làm hỏng run -> nuốt lỗi từng file, chỉ ghi log.
    """
    if not st.get("last_publish_ok"):
        log("[sweep] BỎ QUA: run trước chưa publish OK -> giữ nguyên toàn bộ để truy vết/đăng tay.")
        return

    failed = []                              # (đường dẫn, lỗi) — báo to ở cuối, xem ghi chú dưới

    out = os.path.join(ENGINE, "truyen-out")
    for name in sorted(os.listdir(out)):
        if "log" in name.lower():          # daily-logs/, atun-logs/, *.log -> GIỮ
            continue
        if name in keep:                   # cache chương của dải đang dở (resume) -> GIỮ
            log(f"[sweep] chừa {name} (dải đang dở — resume)")
            continue
        p = os.path.join(out, name)
        try:
            rm_path(p)
            log(f"[sweep] xoá {p}")
        except OSError as e:
            failed.append((p, e))
            log(f"[sweep] bỏ qua {p}: {e}")

    for name in os.listdir(ENGINE):          # _vtitles, scratch _firetest*, _clonetmp*
        if name == "_vtitles" or name.startswith(("_firetest", "_clonetmp")):
            p = os.path.join(ENGINE, name)
            try:
                rm_path(p)
                log(f"[sweep] xoá {p}")
            except OSError as e:
                failed.append((p, e))
                log(f"[sweep] bỏ qua {p}: {e}")

    # Video lần trước trong OUT_DIR (local) — mỗi cái ~1,5-2 GB, giữ tới lần chạy sau rồi xoá.
    if os.path.isdir(OUT_DIR):
        for name in sorted(os.listdir(OUT_DIR)):
            if not (name.startswith("PNTT ") and name.lower().endswith(".mp4")):
                continue
            p = os.path.join(OUT_DIR, name)
            try:
                rm_path(p)
                log(f"[sweep] xoá video cũ {p}")
            except OSError as e:
                failed.append((p, e))
                log(f"[sweep] bỏ qua {p}: {e}")

    # KHÔNG nuốt lỗi câm: dọn hụt thì đĩa phình dần (mỗi lượt ~1,5-2 GB) và chẳng ai thấy,
    # vì lượt vẫn ✅ OK. Một dòng "[sweep] ⚠" khớp $stepRe của notify-run.ps1 nên lọt vào
    # phần "Đã chạy tới" của Telegram. VẪN không ném — dọn hụt không đáng làm gãy cả lượt.
    if failed:
        log(f"[sweep] ⚠ DỌN HỤT {len(failed)} mục — đĩa sẽ phình dần, cần xem tay:")
        for p, e in failed[:10]:
            log(f"[sweep] ⚠   {p}  <- {e.__class__.__name__}: {e}")
    else:
        log("[sweep] dọn sạch, không sót mục nào.")


def sane_end(start, end, act_start, act_end, batch, tol=4):
    """Dải chương THỰC crawl được có hợp lý so với dải YÊU CẦU không?

    Chốt chặn cuối trước khi ghi tiến độ. Bài học 08/08/2026: nguồn gõ sai số chương
    (2438 -> '2538'), crawler tin luôn, last_end nhảy 100 chương => 5 đêm sau đều xin
    chương không tồn tại => kẹt CỨNG 10 lượt chạy. Thà hỏng ĐÚNG MỘT ĐÊM còn hơn nhiễm state.

    Nới tol chương để vẫn chấp nhận việc nguồn skip/gộp số chương ở mức bình thường.
    """
    if act_end < act_start:                      # dải lùi
        return False
    if act_end < start - tol:                    # kết thúc trước cả dải yêu cầu
        return False
    if act_end - act_start + 1 > batch + tol:    # nhận về nhiều hơn hẳn số chương đã xin
        return False
    return act_end <= end + tol


def main():
    ap = argparse.ArgumentParser(description="Chạy 1 lượt đọc+dựng+đăng cho MỘT phần truyện.")
    ap.add_argument("--state", default=DEFAULT_STATE, required=DEFAULT_STATE is None,
                    help="File state của phần truyện (<chiến dịch>/truyen-state.json).")
    args = ap.parse_args()
    STATE = args.state

    if not os.path.isfile(STATE):
        sys.exit(f"Thiếu state file: {STATE}")
    st = json.load(open(STATE, encoding="utf-8"))
    slug = st.get("slug", "pham-nhan-tu-tien")
    url = st.get("url")
    site = st.get("site", "tamhoan")
    batch = int(st.get("batch", 10))
    last = int(st["last_end"])
    # Kết tại MỐC CHẴN CHỤC tiếp theo (vd last=1391 -> end=1400), TỰ re-align khi nguồn skip/gộp số
    # chương (read_story dừng theo SỐ chương đạt 'end' qua --end-chapter, KHÔNG đếm trang).
    start = last + 1
    end = (last // batch + 1) * batch
    if last < 0:
        # Batch ĐẦU TIÊN của một phần mới: nguồn đánh số từ chương 0 nên công thức chẵn-chục
        # thường sẽ cho 0..0. Đọc 0..batch (batch+1 trang) để từ lượt sau mốc chẵn chục thẳng hàng.
        start, end = 0, batch
    # State ghi đè vẫn thắng (ép giọng cho một chương cụ thể); không ghi đè thì luân phiên
    # THEO DẢI CHƯƠNG (chạy lại cùng dải = cùng giọng = dùng lại cache — xem pick_voice).
    voice = st.get("voice") or pick_voice(end=end, batch=batch)

    # Hậu tố tên file theo GIỌNG — phải khớp TỪNG KÝ TỰ với audio_truyen.py:106,
    # vì file do bên đó đặt tên còn bên này đi tìm. Trước 2026-08-26 chỗ này hardcode
    # "_atun"; khi giọng thành a-tun-v1/v2/v3 thì audio_truyen ghi ra "..._atunv3_..."
    # còn daily_truyen tìm "..._atun_..." -> build xong vài giờ GPU rồi mới chết, và
    # chết ở NGOÀI run_build() nên heal_agent không bao giờ được gọi.
    _is_default_voice = voice.strip().lower() in ("giọng tiên hiệp", "giong tien hiep")
    vtag = "" if _is_default_voice else "_" + re.sub(r"[^a-z0-9]+", "", voice.lower())
    playlist = st.get("playlist", "Phàm Nhân Tu Tiên (P1)")
    title_prefix = st.get("title_prefix", "PNTT")
    next_url = st.get("next_url")

    os.makedirs(LOGDIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    logf = open(os.path.join(LOGDIR, f"{slug}_{start}-{end}_{stamp}.log"), "w", encoding="utf-8", newline="\n")

    def log(m):
        print(m); logf.write(m + "\n"); logf.flush()

    log(f"[daily] {stamp}: chương {start}-{end} ({slug} · {site}) | giọng {voice} "
        f"+ lửa + nhạc tiên hiệp 2 | playlist {playlist}")

    # ---- 0) dọn sản phẩm lần chạy TRƯỚC (giữ log) — phải TRƯỚC khi tạo _work của run này ----
    out_root = os.path.join(ENGINE, "truyen-out")
    mark_path = os.path.join(out_root, RESUME_MARK)
    try:
        _mark = json.load(open(mark_path, encoding="utf-8"))
    except (OSError, ValueError):
        _mark = None
    sweep_old(st, log, keep=resume_keep(_mark, slug, start, end, voice))
    os.makedirs(WORK, exist_ok=True)
    try:        # dấu dải đang dở — best-effort: hỏng ghi thì chỉ mất resume, không mất lượt
        with open(mark_path, "w", encoding="utf-8", newline="\n") as _f:
            json.dump({"slug": slug, "start": start, "end": end, "voice": voice,
                       "cache_dir": cache_dir_name(slug, vtag), "stamp": stamp}, _f, ensure_ascii=False)
    except OSError as e:
        log(f"[daily] WARN: không ghi được dấu resume ({e}).")

    # ---- 1) crawl + đọc (A-Tũn) + dựng video (lửa mới) vào WORK ----
    cmd = [PY, "-u", os.path.join(HERE, "audio_truyen.py"),
           "--slug", slug, "--start", str(start), "--end", str(end), "--video",
           "--voice", voice, "--bgm-file", BGM2, "--out-dir", WORK,
           "--ending-text", ENDING_TEXT,
           "--no-outro"]  # lời kết đã đọc bằng giọng clone; outro mp3 cũ gây LẶP câu chào
    if url:
        cmd += ["--url", url]
    if site == "pntt2":
        # Nguồn phamnhantutien.org: lật chương bằng nút "Chương sau" -> cần con trỏ URL.
        # next_url = trang CHƯA đọc kế tiếp (do manifest lượt trước trả về); thiếu nó thì
        # read_story tự resolve từ --url qua mục lục <select> trong trang chương.
        cmd += ["--site", "pntt2"]
        if next_url:
            cmd += ["--start-url", next_url]

    def run_build():
        return subprocess.run(cmd, env=ENV, cwd=HERE, stdout=logf, stderr=subprocess.STDOUT).returncode

    logpath = logf.name
    r = run_build()
    if r != 0:
        # Ghi lỗi + đếm số lần lặp. Tới lần 2 CÙNG lỗi -> gọi Claude tự đánh giá & sửa (heal_agent),
        # rồi re-run kiểm chứng. Heal hỏng luôn revert về bản gốc -> pipeline không tệ đi.
        try:
            logf.flush()
            with open(logpath, encoding="utf-8") as _f:
                err_tail = "".join(_f.readlines()[-40:])
        except Exception:
            err_tail = f"exit {r}"
        healed = False
        try:
            import heal_agent
            sig, count, already, norm = heal_agent.record_failure(err_tail)
            log(f"[daily] LỖI build (exit {r}) — lỗi này đã xảy ra {count} lần (sig {sig}).")
            if heal_agent.should_heal(sig):
                healed = heal_agent.attempt(norm, logpath, run_build, log)
        except Exception as e:
            log(f"[daily] heal_agent lỗi ({e}) — bỏ qua, xử lý như fail thường.")
        if not healed:
            log(f"[daily] State GIỮ NGUYÊN để chạy lại lượt/đêm sau (retry 1h/3h/5h).")
            sys.exit(r or 1)
        log("[daily] tiếp tục sau khi tự chữa thành công.")

    vtag_mp4 = os.path.join(WORK, f"{slug}{vtag}_{start}-{end}.mp4")
    manifest = os.path.join(WORK, f"{slug}{vtag}_{start}-{end}.mp3.manifest.json")
    if not os.path.isfile(vtag_mp4):
        log(f"[daily] LỖI: không thấy video {vtag_mp4}.")
        sys.exit(1)

    # Nguồn ĐÔI KHI nhảy số chương (vd thiếu 1243) -> số chương THỰC cuối khác 'end' yêu cầu.
    # Lấy dải THỰC từ manifest để đặt tên file + tiến độ ĐÚNG (tránh đăng trùng/sót chương đêm sau).
    act_start, act_end = start, end
    man_next_url, source_exhausted = None, False
    try:
        _m = json.load(open(manifest, encoding="utf-8"))
        act_start = int(_m["chapters"][0]["num"])
        act_end = int(_m["chapters"][-1]["num"])
        # Con trỏ resume của nguồn lật-theo-nút (pntt2); site cũ trả None/False -> không đổi gì.
        man_next_url = _m.get("next_url")
        source_exhausted = bool(_m.get("source_exhausted"))
        if (act_start, act_end) != (start, end):
            log(f"[daily] dải THỰC TẾ {act_start}-{act_end} (yêu cầu {start}-{end}) — nguồn nhảy số chương.")
    except Exception as e:
        log(f"[daily] WARN: không đọc được manifest lấy dải thực ({e}); dùng {start}-{end}.")

    # Chốt chặn: dải vô lý (nguồn gõ sai số) -> KHÔNG đổi tên, KHÔNG publish, KHÔNG ghi tiến độ.
    if not sane_end(start, end, act_start, act_end, batch):
        log(f"[daily] LỖI: dải THỰC {act_start}-{act_end} VÔ LÝ so với yêu cầu {start}-{end} "
            f"(batch {batch}) — nhiều khả năng nguồn GÕ SAI SỐ CHƯƠNG.")
        log(f"[daily] KHÔNG publish, KHÔNG ghi tiến độ (state giữ last_end cũ để không kẹt). "
            f"Kiểm tra bằng tay: {manifest} và video {vtag_mp4}.")
        sys.exit(1)

    # ---- 2) đổi tên + chuyển vào OUT_DIR local: "PNTT <đầu>-<cuối>.mp4" ----
    os.makedirs(OUT_DIR, exist_ok=True)
    final_mp4 = os.path.join(OUT_DIR, f"PNTT {act_start}-{act_end}.mp4")
    shutil.move(vtag_mp4, final_mp4)
    log(f"[daily] video -> {final_mp4}")

    # ---- 3) publish công khai lên @nghe-tien-truyen (best-effort; cần manifest còn sống) ----
    pub_ok = False
    if os.path.isfile(TOKEN_TRUYEN) and os.path.isfile(manifest):
        cache_dir = os.path.join(ENGINE, "truyen-out", slug + vtag.replace("_", "__"), "cache")
        pub_py = truyen_paths.publish_python()
        log(f"[daily] publish bằng {' '.join(pub_py)}")
        pub = subprocess.run(pub_py + [os.path.join(HERE, "truyen_publish.py"),
                              "--manifest", manifest, "--video", final_mp4,
                              "--cache-dir", cache_dir,
                              "--playlist", playlist, "--title-prefix", title_prefix],
                             env=dict(ENV, YT_TOKEN_PATH=TOKEN_TRUYEN),
                             cwd=HERE, stdout=logf, stderr=subprocess.STDOUT)
        pub_ok = pub.returncode == 0
        log("[daily] publish: " + ("OK" if pub_ok else f"LỖI exit {pub.returncode}"))
    else:
        log(f"[daily] BỎ QUA publish (thiếu token — YT_TOKEN_PATH__NGHE_TIEN_TRUYEN={TOKEN_TRUYEN or '(chưa đặt)'}). "
            f"Đăng tay sau bằng truyen_publish.py với video ở {OUT_DIR}.")

    # ---- 4) KHÔNG dọn ở đây nữa: giữ mp3/wav/txt/manifest/srt + video cho tới LẦN CHẠY SAU
    #         (sweep_old ở bước 0) -> lỗi gì còn nguyên hiện trường để truy vết. ----
    if pub_ok:
        log("[daily] giữ file phụ + video để truy vết; lần chạy sau sẽ dọn (sweep_old).")
    else:
        log(f"[daily] publish CHƯA XONG -> giữ nguyên tất cả để đăng tay: {manifest}")

    # ---- 5) tăng tiến độ ----
    st["last_end"] = act_end
    st["last_run"] = stamp
    # KHONG ghi lai key "voice": dong 156 doc `st.get("voice") or pick_voice()`,
    # nen ghi lai la KHOA CUNG giong cua dem dau tien, luan phien chet vinh vien.
    # Giu dau vet bang key khac de con tra cuu.
    st["_voice_last"] = voice
    # Cờ cho sweep_old ở LẦN CHẠY SAU: chỉ được dọn khi run này đã publish OK.
    st["last_publish_ok"] = pub_ok
    st["last_video"] = final_mp4
    st["history"] = (st.get("history", []) + [f"{act_start}-{act_end}@{stamp}"])[-50:]
    # Con trỏ resume: chỉ ghi CÙNG LÚC với last_end (tức là đã qua sane_end) — không bao giờ
    # để state nhiễm một URL của lượt hỏng.
    if man_next_url:
        st["next_url"] = man_next_url
    json.dump(st, open(STATE, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    try:        # dải đã xong -> bỏ dấu resume (lượt sau sweep được như thường)
        os.remove(mark_path)
    except OSError:
        pass

    log(f"[daily] OK chương {act_start}-{act_end}. last_end -> {act_end}.")
    if source_exhausted:
        log(f"[daily] ***** NGUỒN BÁO HẾT CHƯƠNG sau {act_end} — phần truyện này có thể ĐÃ KẾT "
            f"THÚC. Kiểm tra nguồn rồi quyết định dừng task đêm. *****")
    logf.close()


if __name__ == "__main__":
    main()
