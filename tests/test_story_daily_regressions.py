# -*- coding: utf-8 -*-
"""Regression test cho HAI LỖI CỦA LƯỢT ĐÊM đã làm hỏng tập 261-270 (14/09/2026).

Chạy: python -m pytest tests/test_story_daily_regressions.py   (KHÔNG cần mạng, không GPU)

Song sinh với test_source_quirks*.py (quái tính của NGUỒN). File này giữ quái tính của
WINDOWS + FFMPEG phía dựng/dọn. Mỗi test ứng với một lỗi THẬT đọc được trong
truyen-out\\daily-logs\\pntt-p2_261-270_20260914_0300.log — đừng xoá khi refactor:

  D-T1  Cờ ReadOnly trên THƯ MỤC làm shutil.rmtree chết WinError 5 "Access is denied".
        Log 14/09 dòng 2-7: sweep bỏ qua _work, out, _vtitles, pntt-p2__atun*/cache.
        Đây KHÔNG phải lỗi ACL, cũng không phải file bị tiến trình khác giữ: Windows trả
        ERROR_ACCESS_DENIED cho RemoveDirectory() khi thư mục mang FILE_ATTRIBUTE_READONLY.
        Dấu vân tay: đường dẫn trong lỗi là CHÍNH THƯ MỤC ĐÓ (hoặc thư mục con đầu tiên),
        không phải một file nào bên trong.

  D-T2  rm_path() phải xoá được cây có cờ ReadOnly ở NHIỀU tầng (thư mục gốc, thư mục con,
        và cả file) — đúng hình dạng hiện trường: truyen-out\\pntt-p2__atun\\cache.

  D-T3  sweep_old() dọn hụt thì phải BÁO TO (dòng "[sweep] ⚠") chứ không được im lặng:
        lượt vẫn ✅ OK nên không ai biết đĩa đang phình ~1,5-2 GB mỗi lượt. Nhưng vẫn
        KHÔNG được ném lỗi — dọn hụt không đáng làm gãy cả lượt.

  D-T4  sweep_old() dọn sạch thì phải nói rõ "dọn sạch" — im lặng là mơ hồ, không phân biệt
        được với "chưa chạy".
"""
import os
import shutil
import stat
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNERS = os.path.join(ROOT, "scripts", "runners")
HERE = os.path.join(RUNNERS, "story")          # mã pipeline truyện trong repo
sys.path.insert(0, HERE)
# `daily_truyen` neo dữ liệu vào ENGINE lúc import; nạp nó TRONG test (sau khi trỏ
# OMNIVOICE_DIR vào sandbox bằng monkeypatch) để không một biến nào rò sang test khác.
daily_truyen = None

FAILED = []


def check(cond, name, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL {name} {detail}")


def mk_readonly_tree(root, files_readonly=False):
    """Dựng ĐÚNG hình dạng hiện trường: <root>/pntt-p2__atun/cache/<file>.

    Mặc định CHỈ thư mục mang cờ ReadOnly, file thì KHÔNG — đó là hiện trường thật đo được
    ngày 20/09 trên `<engine>/**` (trạm giọng Windows). Chính vì file sạch mà rmtree xoá hết nội dung rồi
    mới chết ở os.rmdir, nên lỗi trỏ vào THƯ MỤC. Nếu file cũng ReadOnly thì lỗi sẽ trỏ vào
    file và dấu vân tay khác hẳn — giữ phân biệt này để test đỏ đúng lý do.
    """
    cache = os.path.join(root, "pntt-p2__atun", "cache")
    os.makedirs(cache)
    f = os.path.join(cache, "voice.bin")
    with open(f, "wb") as fh:
        fh.write(b"x" * 16)
    if files_readonly:
        os.chmod(f, stat.S_IREAD)
    for d in (cache, os.path.dirname(cache)):
        os.chmod(d, stat.S_IREAD)                                # THƯ MỤC ReadOnly  <- thủ phạm
    return os.path.join(root, "pntt-p2__atun")


def t1_plain_rmtree_reproduces_winerror5():
    """D-T1 — chứng minh test ĐỎ ĐÚNG LÝ DO: rmtree trần phải chết WinError 5."""
    tmp = tempfile.mkdtemp(prefix="truyen_t1_")
    try:
        target = mk_readonly_tree(tmp)
        try:
            shutil.rmtree(target)
            check(False, "D-T1 rmtree trần chết WinError 5", "(xoá được -> không tái hiện được lỗi thật)")
        except OSError as e:
            win = getattr(e, "winerror", None)
            check(win == 5, "D-T1 rmtree trần chết WinError 5", f"(winerror={win}, path={e.filename})")
            # dấu vân tay: lỗi trỏ vào THƯ MỤC, không phải file bên trong
            check(e.filename is not None and os.path.basename(e.filename) == "cache",
                  "D-T1 lỗi trỏ vào THƯ MỤC (cache), không phải file bên trong",
                  f"(filename={e.filename})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t2_rm_path_survives_readonly():
    """D-T2 — rm_path() phải xoá sạch cây ReadOnly nhiều tầng."""
    tmp = tempfile.mkdtemp(prefix="truyen_t2_")
    try:
        for ro_files in (False, True):       # hiện trường thật, và bản nặng hơn (file cũng ReadOnly)
            sub = os.path.join(tmp, f"case_{int(ro_files)}")
            os.makedirs(sub)
            target = mk_readonly_tree(sub, files_readonly=ro_files)
            label = f"D-T2 rm_path xoá sạch cây ReadOnly (file_readonly={ro_files})"
            try:
                daily_truyen.rm_path(target)
                check(not os.path.exists(target), label)
            except (OSError, AttributeError) as e:
                check(False, label, f"({type(e).__name__}: {e})")

        # và với FILE ReadOnly đơn lẻ
        f = os.path.join(tmp, "ro.txt")
        with open(f, "w") as fh:
            fh.write("x")
        os.chmod(f, stat.S_IREAD)
        try:
            daily_truyen.rm_path(f)
            check(not os.path.exists(f), "D-T2 rm_path xoá được FILE ReadOnly")
        except (OSError, AttributeError) as e:
            check(False, "D-T2 rm_path xoá được FILE ReadOnly", f"({type(e).__name__}: {e})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _fake_engine():
    """Dựng cây ENGINE giả đúng hình dạng thật: truyen-out/{_work,out,daily-logs,pntt-p2__atun}."""
    eng = tempfile.mkdtemp(prefix="truyen_eng_")
    out = os.path.join(eng, "truyen-out")
    for sub in ("_work", "out", "daily-logs"):
        os.makedirs(os.path.join(out, sub))
    mk_readonly_tree(out)
    with open(os.path.join(out, "_work", "a.mp3"), "wb") as fh:
        fh.write(b"x" * 8)
    with open(os.path.join(out, "daily-logs", "keep.log"), "w") as fh:
        fh.write("giu lai")
    os.makedirs(os.path.join(eng, "_vtitles"))
    os.chmod(os.path.join(eng, "_vtitles"), stat.S_IREAD)
    with open(os.path.join(out, "out", "PNTT 1-10.mp4"), "wb") as fh:
        fh.write(b"x" * 8)
    return eng, out


def _run_sweep(eng, out, keep=()):
    """Gọi sweep_old với ENGINE/OUT_DIR trỏ vào cây giả; trả về các dòng log."""
    lines = []
    old_engine, old_out = daily_truyen.ENGINE, daily_truyen.OUT_DIR
    daily_truyen.ENGINE = eng
    daily_truyen.OUT_DIR = os.path.join(out, "out")
    try:
        daily_truyen.sweep_old({"last_publish_ok": True}, lines.append, keep=keep)
    finally:
        daily_truyen.ENGINE, daily_truyen.OUT_DIR = old_engine, old_out
    return lines


def t3_sweep_reports_and_does_not_raise():
    """D-T3/D-T4 — sweep_old dọn sạch cây ReadOnly, nói rõ, và không bao giờ ném."""
    eng, out = _fake_engine()
    try:
        try:
            lines = _run_sweep(eng, out)
            raised = None
        except Exception as e:                                   # noqa: BLE001
            lines, raised = [], e
        check(raised is None, "D-T3 sweep_old KHÔNG ném lỗi", f"({raised!r})")

        blob = "\n".join(lines)
        check(not os.path.exists(os.path.join(out, "pntt-p2__atun")),
              "D-T3 sweep_old dọn được thư mục ReadOnly (pntt-p2__atun)")
        check(not os.path.exists(os.path.join(eng, "_vtitles")),
              "D-T3 sweep_old dọn được _vtitles ReadOnly")
        check(os.path.exists(os.path.join(out, "daily-logs", "keep.log")),
              "D-T3 sweep_old GIỮ nguyên daily-logs")
        check("[sweep] dọn sạch" in blob, "D-T4 dọn sạch thì nói rõ", f"\n--- log ---\n{blob}")
        check("⚠" not in blob, "D-T4 dọn sạch thì KHÔNG có cảnh báo thừa")
    finally:
        shutil.rmtree(eng, ignore_errors=True)


def t4_sweep_shouts_when_it_cannot_clean():
    """D-T3 — không dọn được thì phải có dòng '[sweep] ⚠' để notify-run.ps1 bắt được."""
    eng, out = _fake_engine()
    try:
        if not hasattr(daily_truyen, "rm_path"):     # bản CHƯA sửa: báo đỏ chứ đừng crash cả file
            check(False, "D-T3 dọn hụt thì BÁO TO", "(daily_truyen chưa có rm_path)")
            return
        # Bẫy: thay rm_path bằng bản luôn hỏng -> mô phỏng "dọn hụt vì lý do khác ReadOnly"
        real = daily_truyen.rm_path
        daily_truyen.rm_path = lambda p: (_ for _ in ()).throw(
            PermissionError(13, "Access is denied", p))
        try:
            lines = _run_sweep(eng, out)
            raised = None
        except Exception as e:                                   # noqa: BLE001
            lines, raised = [], e
        finally:
            daily_truyen.rm_path = real

        blob = "\n".join(lines)
        check(raised is None, "D-T3 dọn hụt vẫn KHÔNG làm gãy lượt", f"({raised!r})")
        check("[sweep] ⚠ DỌN HỤT" in blob, "D-T3 dọn hụt thì BÁO TO", f"\n--- log ---\n{blob}")
        # notify-run.ps1 $stepRe = '^(===|---|\[|Step |...)' -> dòng phải bắt đầu bằng '['
        warn = [l for l in lines if "⚠" in l]
        check(bool(warn) and all(l.startswith("[") for l in warn),
              "D-T3 dòng cảnh báo khớp $stepRe của notify-run.ps1 (bắt đầu bằng '[')",
              f"({warn[:2]})")
    finally:
        shutil.rmtree(eng, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────────────────
# P-T* — phân giải đường Windows + macOS (truyen_paths.py). KHÔNG mạng, KHÔNG registry,
# HOME/trạm giả trong %TEMP%: không test nào được chạm trạm thật.
# R-T* — resume (F1-ANALYSIS §7.4): giọng theo DẢI chương + sweep chừa cache dải đang dở.
# ─────────────────────────────────────────────────────────────────────────────────────────
import truyen_paths  # noqa: E402


def _touch(*parts):
    p = os.path.join(*parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(b"x")
    return p


def _raises_exit(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except SystemExit as e:
        return str(e)
    return None


def tp1_engine_dir():
    tmp = tempfile.mkdtemp(prefix="truyen_home_")
    old = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
    try:
        check(truyen_paths.engine_dir({"OMNIVOICE_DIR": os.path.join(tmp, "e")}, registry=False)
              == os.path.join(tmp, "e"), "P-T1 OMNIVOICE_DIR thắng")
        check(truyen_paths.engine_dir({"VOICE_STATION": tmp}, registry=False)
              == os.path.join(tmp, "omnivoice"), "P-T1 VOICE_STATION -> <trạm>/omnivoice")
        check(truyen_paths.engine_dir({"OMNIVOICE_DIR": os.path.join(tmp, "e"), "VOICE_STATION": "/x"},
                                      registry=False) == os.path.join(tmp, "e"),
              "P-T1 OMNIVOICE_DIR (cụ thể) thắng VOICE_STATION (test sandbox không trượt ra trạm thật)")
        os.environ["HOME"] = tmp
        os.environ["USERPROFILE"] = tmp
        check(truyen_paths.engine_dir({"VOICE_STATION": "~/st"}, registry=False)
              == os.path.join(tmp, "st", "omnivoice"), "P-T1 '~' trong biến được nở tường minh")
        msg = _raises_exit(truyen_paths.engine_dir, {}, registry=False)
        check(bool(msg) and "VOICE_STATION" in msg, "P-T1 thiếu biến thì DỪNG và nói tên biến", f"({msg!r})")
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)


def tp2_venv_python():
    eng = tempfile.mkdtemp(prefix="truyen_venv_")
    try:
        check(truyen_paths.venv_python(eng, env={}) == sys.executable,
              "P-T2 không có venv -> interpreter đang chạy")
        mac = _touch(eng, ".venv", "bin", "python3")
        check(truyen_paths.venv_python(eng, env={}) == mac, "P-T2 venv kiểu macOS bin/python3")
        win = _touch(eng, ".venv", "Scripts", "python.exe")
        check(truyen_paths.venv_python(eng, env={}) == win, "P-T2 venv kiểu Windows Scripts/python.exe")
        check(truyen_paths.venv_python(eng, env={"OMNIVOICE_PY": mac}) == mac, "P-T2 OMNIVOICE_PY ép")
    finally:
        shutil.rmtree(eng, ignore_errors=True)


def tp3_title_font():
    eng = tempfile.mkdtemp(prefix="truyen_font_")
    try:
        msg = _raises_exit(truyen_paths.title_font, eng, env={}, system_fonts=[])
        check(bool(msg) and "TRUYEN_FONT" in msg, "P-T3 thiếu font thì KÊU (nêu TRUYEN_FONT)", f"({msg!r})")
        msg = _raises_exit(truyen_paths.title_font, eng, env={"TRUYEN_FONT": os.path.join(eng, "khong.ttf")})
        check(bool(msg) and "TRUYEN_FONT" in msg, "P-T3 TRUYEN_FONT trỏ sai thì KÊU, không lùi im lặng")
        sysf = _touch(eng, "sys", "Arial Bold.ttf")
        check(truyen_paths.title_font(eng, env={}, system_fonts=[sysf]) == sysf, "P-T3 font hệ thống")
        st = _touch(eng, "assets", "fonts", "title.ttf")
        check(truyen_paths.title_font(eng, env={}, system_fonts=[sysf]) == st,
              "P-T3 font của trạm thắng font hệ thống")
        own = _touch(eng, "x", "mine.ttf")
        check(truyen_paths.title_font(eng, env={"TRUYEN_FONT": own}) == own, "P-T3 TRUYEN_FONT thắng")
    finally:
        shutil.rmtree(eng, ignore_errors=True)


def tp4_upload_engine_dir():
    tmp = tempfile.mkdtemp(prefix="truyen_up_")
    try:
        here = os.path.join(tmp, "tram", "nghe-tien-truyen")
        os.makedirs(here)
        home = os.path.join(tmp, "home")
        data = os.path.join(tmp, "data")
        got = truyen_paths.upload_engine_dir({"MARKETING_STUDIO_DATA": data}, registry=False, home=home, here=here)
        check(got == os.path.join(tmp, "tram"),
              "P-T4 không ở đâu có youtube_upload.py -> trả ứng viên đầu (repo; import nổ nói rõ)", f"({got})")
        tram = os.path.dirname(_touch(tmp, "tram", "engine", "youtube_upload.py"))
        got = truyen_paths.upload_engine_dir({}, registry=False, home=home, here=here)
        check(got == tram, "P-T4 không có MARKETING_STUDIO_DATA -> <trạm chứa script>/engine", f"({got})")
        mine = os.path.dirname(_touch(data, "engine", "youtube_upload.py"))
        got = truyen_paths.upload_engine_dir({"MARKETING_STUDIO_DATA": data}, registry=False, home=home, here=here)
        check(got == mine, "P-T4 MARKETING_STUDIO_DATA/engine thắng bản trong trạm", f"({got})")
        repo = os.path.dirname(_touch(tmp, "tram", "youtube_upload.py"))
        got = truyen_paths.upload_engine_dir({"MARKETING_STUDIO_DATA": data}, registry=False, home=home, here=here)
        check(got == repo, "P-T4 bản của repo (cha của thư mục story) thắng mọi bản trong trạm", f"({got})")
        got = truyen_paths.upload_engine_dir({}, registry=False)
        check(os.path.isfile(os.path.join(got, "youtube_upload.py")) and os.path.samefile(got, RUNNERS),
              "P-T4 bản thật trong repo trỏ scripts/runners", f"({got})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tp5_publish_python():
    check(truyen_paths.publish_python({"TRUYEN_PUBLISH_PY": sys.executable}) == [sys.executable],
          "P-T5 TRUYEN_PUBLISH_PY ép")
    check(truyen_paths.publish_python({}, probe=lambda argv: False) == [sys.executable],
          "P-T5 không ứng viên nào có googleapiclient -> interpreter đang chạy")
    got = truyen_paths.publish_python({}, probe=lambda argv: True)
    check(isinstance(got, list) and bool(got) and os.path.basename(got[0]).lower().startswith(("python", "py")),
          "P-T5 ứng viên PATH đầu tiên qua được thăm dò", f"({got})")


def tp6_no_windows_hardcode():
    """Cổng: không đường máy Windows trong DÒNG MÃ của pipeline đang chạy (runbook Bước 5.3)."""
    import re
    files = [os.path.join(HERE, f) for f in ("daily_truyen.py", "audio_truyen.py", "make_video.py",
                                             "read_story.py", "truyen_publish.py", "heal_agent.py")]
    files.append(os.path.join(RUNNERS, "run-daily-truyen.ps1"))
    bad = re.compile(r"[A-Za-z]:\\\\?(Users|Windows)|\.tts[\\/]|import mcp_server|Scripts[\\/]+python\.exe")
    hits = []
    for f in files:
        with open(f, encoding="utf-8-sig") as fh:
            for i, line in enumerate(fh, 1):
                code = line.split("#", 1)[0] if not line.lstrip().startswith(("#", '"', "'")) else ""
                if bad.search(code):
                    hits.append(f"{os.path.basename(f)}:{i}: {line.strip()[:90]}")
    # Ngoại lệ có chủ đích: danh sách ứng viên venv trong .ps1 (Join-Path 'Scripts' 'python.exe')
    # không khớp mẫu vì đi qua Join-Path; truyen_paths.py KHÔNG nằm trong danh sách quét (nơi
    # DUY NHẤT được biết hình dạng venv của từng OS).
    check(not hits, "P-T6 0 đường máy Windows / import mcp_server trong dòng mã", "\n  " + "\n  ".join(hits))


def tr1_voice_by_range():
    vd = tempfile.mkdtemp(prefix="truyen_voices_")
    try:
        for v in daily_truyen.VOICE_POOL:
            _touch(vd, v + ".wav")
        import datetime as _dt
        a = daily_truyen.pick_voice(vd, today=_dt.date(2026, 9, 29), end=280, batch=10)
        b = daily_truyen.pick_voice(vd, today=_dt.date(2026, 9, 30), end=280, batch=10)
        check(a == b, "R-T1 chạy lại CÙNG dải hôm sau ra CÙNG giọng", f"({a} vs {b})")
        check(a == "a-tun" and daily_truyen.pick_voice(vd, end=290, batch=10) == "a-tun-v1",
              "R-T1 giữ đúng nhịp đã chạy (271-280 a-tun, 281-290 a-tun-v1)")
        check(daily_truyen.pick_voice(vd, today=_dt.date(2026, 9, 29)) == "a-tun",
              "R-T1 gọi trần (không dải) vẫn theo ngày như cũ")
        os.remove(os.path.join(vd, "a-tun.wav"))
        check(daily_truyen.pick_voice(vd, end=280, batch=10) == "a-tun-v1",
              "R-T1 profile thiếu file thì bỏ qua")
    finally:
        shutil.rmtree(vd, ignore_errors=True)


def tr2_resume_keep_and_sweep():
    name = daily_truyen.cache_dir_name("pntt-p2", "_atunv1")
    check(name == "pntt-p2__atunv1", "R-T2 tên thư mục cache khớp audio_truyen.py", f"({name})")
    mark = {"slug": "pntt-p2", "start": 281, "end": 290, "voice": "a-tun-v1", "cache_dir": name}
    keep = daily_truyen.resume_keep(mark, "pntt-p2", 281, 290, "a-tun-v1")
    check(keep == {name, daily_truyen.RESUME_MARK}, "R-T2 dấu khớp lượt này -> chừa cache + dấu", f"({keep})")
    check(daily_truyen.resume_keep(mark, "pntt-p2", 291, 300, "a-tun") == set(),
          "R-T2 dải khác -> không chừa gì (sweep như cũ)")
    check(daily_truyen.resume_keep(mark, "pntt-p2", 281, 290, "a-tun") == set(),
          "R-T2 giọng khác -> không chừa (cache giọng khác vô dụng)")
    check(daily_truyen.resume_keep(None, "pntt-p2", 281, 290, "a-tun-v1") == set(),
          "R-T2 không có dấu -> không chừa")
    eng, out = _fake_engine()
    try:
        _touch(out, name, "Chuong_281.wav")
        _touch(out, daily_truyen.RESUME_MARK)
        lines = _run_sweep(eng, out, keep=keep)
        blob = "\n".join(lines)
        check(os.path.isfile(os.path.join(out, name, "Chuong_281.wav")),
              "R-T2 sweep CHỪA wav chương đã đọc của dải đang dở", f"\n--- log ---\n{blob}")
        check(not os.path.exists(os.path.join(out, "_work")) and not os.path.exists(os.path.join(out, "pntt-p2__atun")),
              "R-T2 sweep vẫn dọn phần còn lại (_work, cache giọng khác)")
        check("[sweep] chừa" in blob, "R-T2 log nói rõ đã chừa gì")
    finally:
        shutil.rmtree(eng, ignore_errors=True)


TAT_CA = ("t1_plain_rmtree_reproduces_winerror5", "t2_rm_path_survives_readonly",
          "t3_sweep_reports_and_does_not_raise", "t4_sweep_shouts_when_it_cannot_clean",
          "tp1_engine_dir", "tp2_venv_python", "tp3_title_font", "tp4_upload_engine_dir",
          "tp5_publish_python", "tp6_no_windows_hardcode", "tr1_voice_by_range",
          "tr2_resume_keep_and_sweep")


@pytest.mark.parametrize("ten", TAT_CA)
def test_story_regression(ten, monkeypatch, tmp_path):
    """Mỗi hàm kiểm cũ là một test pytest. ENGINE trỏ vào thư mục tạm: không chạm trạm giọng thật."""
    global daily_truyen
    import importlib
    monkeypatch.setenv("OMNIVOICE_DIR", str(tmp_path / "engine"))
    if daily_truyen is None:
        daily_truyen = importlib.import_module("daily_truyen")
    else:
        daily_truyen = importlib.reload(daily_truyen)
    FAILED.clear()
    globals()[ten]()
    assert not FAILED, FAILED
