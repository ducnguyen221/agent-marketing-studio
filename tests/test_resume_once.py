# -*- coding: utf-8 -*-
"""Cổng P1-23: lượt truyện quá trần (mã 124) mà dải còn dở thì tự chạy tiếp ĐÚNG MỘT LẦN.

Mac mini 02/10/2026: lượt 301–310 bị giết lúc 08:30 sau 9/10 chương; người phải
`launchctl kickstart` tay. Ba kịch bản Đức chốt (SUBTASK-WIN-RUNTIME-2 §1):

* 124 + có `_resume.json` ⇒ chạy tiếp đúng 1 lần (kèm tin ⏳ "từ chương X");
* 124 + KHÔNG có `_resume.json` ⇒ không chạy tiếp;
* lượt chạy tiếp lại 124 ⇒ dừng, không lặp.

Cộng hai thứ chỉ hỏng khi ráp với phần còn lại: trần của wrapper ngoài (plist, `-Register`)
phải ≥ tổng hai trần của runner, và runner phải thật sự gọi qua bộ canh.
"""
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STORY = REPO / "scripts" / "runners" / "story"
sys.path.insert(0, str(STORY))
import resume_once as RO  # noqa: E402


def _mark(tmp_path, start=301, end=310, co=(301, 302, 303)):
    out = tmp_path / "truyen-out"
    cache = out / "pntt-p2__atunv1"
    cache.mkdir(parents=True)
    for n in co:
        (cache / f"Chuong_{n}.wav").write_bytes(b"RIFF")
    m = out / RO.RESUME_MARK
    m.write_text(json.dumps({"slug": "pntt-p2", "start": start, "end": end, "voice": "a-tun-v1",
                             "cache_dir": "pntt-p2__atunv1", "stamp": "20261002_0000"}),
                 encoding="utf-8")
    return str(m)


class Run:
    """Thay `notify_run.chay_lenh`: trả mã theo kịch bản, ghi lại trần từng lượt."""

    def __init__(self, *codes):
        self.codes, self.trans = list(codes), []

    def __call__(self, cmd, tran=None):
        self.trans.append(tran)
        ma = self.codes[len(self.trans) - 1]
        return ma, [], ma == RO.MA_QUA_GIO


def test_124_co_dau_dai_do_thi_chay_tiep_DUNG_MOT_LAN(tmp_path, capsys):
    tin, run = [], Run(124, 0)
    ma = RO.chay(["x"], "Truyen · p2", 30600, 10800, _mark(tmp_path), run=run, send=tin.append)
    assert ma == 0
    assert run.trans == [30600, 10800], "lượt đầu trần 30600, lượt tiếp trần 10800 — đúng 2 lượt"
    assert len(tin) == 1 and tin[0].startswith("⏳")
    assert "chương <b>304</b>" in tin[0], "chương X = chương đầu CHƯA có Chuong_<n>.wav"
    out = capsys.readouterr().out
    assert "RESUME_ONCE=start from=304 range=301-310" in out
    assert "RESUME_ONCE=done code=0" in out


def test_124_KHONG_co_dau_thi_KHONG_chay_tiep(tmp_path):
    tin, run = [], Run(124, 0)
    ma = RO.chay(["x"], "T", 30600, 10800, str(tmp_path / "khong-co.json"), run=run, send=tin.append)
    assert ma == 124 and len(run.trans) == 1 and tin == []


def test_chua_biet_tram_giong_thi_KHONG_chay_tiep():
    run = Run(124, 0)
    assert RO.chay(["x"], "T", 30600, 10800, None, run=run, send=lambda _t: None) == 124
    assert len(run.trans) == 1


def test_luot_chay_tiep_lai_124_thi_DUNG_khong_lap(tmp_path, capsys):
    run = Run(124, 124, 0)
    ma = RO.chay(["x"], "T", 30600, 10800, _mark(tmp_path), run=run, send=lambda _t: None)
    assert ma == 124
    assert len(run.trans) == 2, "lượt chạy tiếp quá trần lần nữa ⇒ dừng, KHÔNG có lượt thứ ba"
    assert "DỪNG, không lặp" in capsys.readouterr().out


@pytest.mark.parametrize("ma", [0, 1, 2, 4])
def test_ma_khac_124_thi_khong_dung_den_dau(tmp_path, ma):
    run = Run(ma)
    assert RO.chay(["x"], "T", 30600, 10800, _mark(tmp_path), run=run, send=lambda _t: None) == ma
    assert len(run.trans) == 1


def test_tin_cho_hong_KHONG_chan_luot_chay_tiep(tmp_path):
    def hong(_t):
        raise RuntimeError("mạng chết")
    run = Run(124, 0)
    assert RO.chay(["x"], "T", 30600, 10800, _mark(tmp_path), run=run, send=hong) == 0
    assert len(run.trans) == 2


def test_doc_du_chuong_thi_bao_con_dung_video(tmp_path):
    m = _mark(tmp_path, co=range(301, 311))
    assert RO.chuong_tiep(RO.dai_do(m), m) is None
    tin = RO.tin_cho("T", 30600, 10800, RO.dai_do(m), None)
    assert "đã đọc đủ chương" in tin


@pytest.mark.parametrize("noi_dung", ["{hỏng", "[]", '{"start": 5}', '{"start": 9, "end": 3}'])
def test_dau_hong_hoac_thieu_dai_coi_nhu_KHONG_co(tmp_path, noi_dung):
    p = tmp_path / RO.RESUME_MARK
    p.write_text(noi_dung, encoding="utf-8")
    assert RO.dai_do(str(p)) is None


def test_quá_tran_THAT_giet_ca_cay_roi_chay_tiep(tmp_path):
    """Không giả `chay_lenh`: lượt đầu ngủ 60 s, trần 2 s ⇒ bị giết (124) ⇒ lượt tiếp thoát 0."""
    dem = tmp_path / "dem.txt"
    con = tmp_path / "con.py"
    con.write_text(textwrap.dedent(f"""
        import pathlib, sys, time
        p = pathlib.Path(r"{dem}")
        n = int(p.read_text()) if p.exists() else 0
        p.write_text(str(n + 1))
        print("luot", n + 1, flush=True)
        if n == 0:
            time.sleep(60)
        sys.exit(0)
    """), encoding="utf-8")
    tin = []
    ma = RO.chay([sys.executable, str(con)], "T", 2, 30, _mark(tmp_path), send=tin.append)
    assert ma == 0 and dem.read_text() == "2" and len(tin) == 1


def test_cli_chay_that_qua_python(tmp_path):
    """Đúng dòng lệnh mà run-daily-truyen.ps1 gọi (`python resume_once.py … -- lệnh`)."""
    m = _mark(tmp_path)
    con = [sys.executable, "-c", "import sys; sys.exit(124)"]
    r = subprocess.run([sys.executable, str(STORY / "resume_once.py"), "--title", "T",
                        "--budget", "30", "--resume-budget", "30", "--mark", m, "--", *con],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**__import__("os").environ, "TG_CONFIG": str(tmp_path / "khong.json")})
    assert r.returncode == 124
    assert r.stdout.count("RESUME_ONCE=start") == 1 and "RESUME_ONCE=done code=124" in r.stdout


# ── ráp với phần còn lại ───────────────────────────────────────────────────────

def test_ten_dau_KHOP_daily_truyen():
    t = (STORY / "daily_truyen.py").read_text(encoding="utf-8")
    assert f'RESUME_MARK = "{RO.RESUME_MARK}"' in t


def _ps1():
    return (REPO / "scripts" / "runners" / "run-daily-truyen.ps1").read_text(encoding="utf-8")


def test_runner_GOI_QUA_bo_canh_khong_goi_thang_daily():
    t = _ps1()
    assert re.search(r"&\s*\$py\s+-u\s+\$guard\b.*--\s+\$py\s+-u\s+\$daily", t, re.S)
    assert not re.search(r"&\s*\$py\s+-u\s+\$daily\s+--state", t), \
        "gọi thẳng daily_truyen.py là mất trần + mất chạy tiếp"


def test_mac_dinh_tran_KHOP_giua_runner_va_bo_canh():
    t = _ps1()
    assert re.search(rf"\[int\]\$Budget\s*=\s*{RO.TRAN_DAU}\b", t)
    assert re.search(rf"\[int\]\$ResumeBudget\s*=\s*{RO.TRAN_TIEP}\b", t)


def test_tran_lot_dau_KHONG_ha_sat_luot_that():
    assert RO.TRAN_DAU >= 30600, "lượt rảnh đo ~6 h 05; trần cũ 6 h giết lượt vừa đọc xong"


def test_tran_wrapper_plist_LON_HON_tong_hai_tran_runner():
    """Wrapper giết trước khi runner kịp chạy tiếp thì P1-23 vô nghĩa — im lặng."""
    import plistlib
    p = REPO / "templates" / "launchd" / "studio.marketing.daily-story.plist"
    a = plistlib.loads(p.read_bytes())["ProgramArguments"]
    tran = int(a[a.index("--timeout") + 1])
    assert tran >= RO.TRAN_DAU + RO.TRAN_TIEP + 600


def test_register_windows_tinh_ExecutionTimeLimit_tu_hai_tran():
    t = _ps1()
    assert re.search(r"New-TimeSpan\s+-Seconds\s+\(\$Budget\s*\+\s*\$ResumeBudget\s*\+\s*\d+\)", t)
    assert "NOTIFY_RUN" in t, "-Register phải đi qua wrapper báo cáo (luật E2 của máy chạy lịch)"


def test_bi_giet_luc_DANG_DANG_thi_KHONG_chay_tiep(tmp_path, capsys):
    """Review 02/10: dấu `phase=publish` ⇒ có thể đã lên YouTube mà chưa ghi state; chạy tiếp =
    dựng lại + upload lần hai = video trùng công khai."""
    m = _mark(tmp_path)
    d = json.loads(Path(m).read_text(encoding="utf-8"))
    d["phase"] = "publish"
    Path(m).write_text(json.dumps(d), encoding="utf-8")
    tin, run = [], Run(124, 0)
    assert RO.chay(["x"], "T", 30600, 10800, m, run=run, send=tin.append) == 124
    assert len(run.trans) == 1 and tin == []
    out = capsys.readouterr().out
    assert "RESUME_ONCE=skip reason=publish range=301-310" in out
    import compose_report as CR
    assert "KHÔNG tự chạy lại" in CR.build("T", 124, "08:30:00", out)


def test_daily_truyen_ghi_pha_publish_TRUOC_khi_dang():
    t = (STORY / "daily_truyen.py").read_text(encoding="utf-8")
    assert t.index('_m["phase"] = "publish"') < t.index('os.path.join(HERE, "truyen_publish.py")')


def test_khong_con_dau_va_chay_tiep_lai_124_deu_co_loi_huong_dan(tmp_path, capsys):
    import compose_report as CR
    RO.chay(["x"], "T", 30600, 10800, str(tmp_path / "khong.json"), run=Run(124),
            send=lambda _t: None)
    assert "không còn dấu dải dở" in CR.build("T", 124, "08:30", capsys.readouterr().out)
    RO.chay(["x"], "T", 30600, 10800, _mark(tmp_path), run=Run(124, 124), send=lambda _t: None)
    assert "CŨNG quá trần" in CR.build("T", 124, "11:30", capsys.readouterr().out)


def test_chuong_ghi_NGUYEN_TU(tmp_path):
    """Có `Chuong_<n>.wav` = chương xong. Bị giết giữa lúc ghi không được để lại file cụt mang
    tên thật — lượt chạy tiếp sẽ dùng nó như chương hoàn chỉnh."""
    t = (STORY / "read_story.py").read_text(encoding="utf-8")
    assert "ov_engine.save(wav, tmp_wav, sr)" in t and "os.replace(tmp_wav, per_wav)" in t
    assert "ov_engine.save(wav, per_wav, sr)" not in t


def test_qua_tran_giet_CA_CHAU_khong_chi_con(tmp_path):
    """Con đẻ cháu (như daily_truyen → audio_truyen → ffmpeg); quá trần phải giết cả cháu."""
    nhip = tmp_path / "nhip.txt"
    chau = tmp_path / "chau.py"
    chau.write_text(textwrap.dedent(f"""
        import pathlib, time
        p = pathlib.Path(r"{nhip}")
        for i in range(600):
            p.write_text(str(i)); time.sleep(0.1)
    """), encoding="utf-8")
    con = tmp_path / "con.py"
    con.write_text(textwrap.dedent(f"""
        import subprocess, sys, time
        subprocess.Popen([sys.executable, r"{chau}"])
        time.sleep(60)
    """), encoding="utf-8")
    import time
    RO.chay([sys.executable, str(con)], "T", 2, 30, None, send=lambda _t: None)
    time.sleep(1.5)
    truoc = nhip.read_text()
    time.sleep(1.5)
    assert nhip.read_text() == truoc, "tiến trình cháu vẫn sống sau khi quá trần"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX: session riêng của nhóm con")
def test_bo_canh_bi_SIGTERM_thi_giet_nhom_con(tmp_path):
    """Review 02/10 NS1: wrapper launchd giết nhóm của nó; nhóm con (session riêng) phải bị bộ
    canh giết theo, không thì daily_truyen + TTS mồ côi chạy đè lượt hôm sau."""
    import signal
    import time
    nhip = tmp_path / "nhip.txt"
    con = tmp_path / "con.py"
    con.write_text(textwrap.dedent(f"""
        import pathlib, time
        p = pathlib.Path(r"{nhip}")
        for i in range(600):
            p.write_text(str(i)); time.sleep(0.1)
    """), encoding="utf-8")
    p = subprocess.Popen([sys.executable, str(STORY / "resume_once.py"), "--budget", "60",
                          "--mark", str(tmp_path / "khong.json"), "--", sys.executable, str(con)])
    time.sleep(2)
    p.send_signal(signal.SIGTERM)
    p.wait(timeout=30)
    time.sleep(1)
    truoc = nhip.read_text()
    time.sleep(1)
    assert nhip.read_text() == truoc


def test_luot_THEO_LICH_gap_dau_publish_cung_dai_thi_DUNG_khong_dang_lai():
    """Review 02/10 vòng 2: lượt đêm sau chạy lại đúng dải (last_end chưa tăng) — không chặn ở
    daily_truyen thì nó ghi đè dấu (mất `phase`) rồi upload lần hai."""
    t = (STORY / "daily_truyen.py").read_text(encoding="utf-8")
    chan = t.index('_mark.get("phase") == "publish"')
    assert chan < t.index("sweep_old(st, log, keep=resume_keep(")
    assert chan < t.index('json.dump({"slug": slug')
    assert "PUBLISH_GUARD=blocked" in t
    import compose_report as CR
    msg = CR.build("T", 1, "00:00:05", "PUBLISH_GUARD=blocked range=301-310\n")
    assert "kể cả lượt theo lịch" in msg
