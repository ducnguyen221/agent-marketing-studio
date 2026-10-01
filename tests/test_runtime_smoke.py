# -*- coding: utf-8 -*-
"""Smoke CHẠY THẬT cho công cụ ngoài repo mà lượt truyện cần — cổng CI 2 OS (P0-8, P0-9).

Test đơn vị (`test_runtime_deps_truyen.py`) giả mọi lệnh ngoài, nên chúng không bao giờ thấy
được điều đã giết lượt truyện đầu trên Mac mini (01/10/2026): ffmpeg THẬT thiếu `drawtext`,
PyAV THẬT bỏ tham số. Ở đây gọi đúng thứ runner gọi:

    · `make_video.py` dựng video 5 giây: nền lặp + nhạc nền + tiêu đề chương bằng `drawtext`
      (font hệ thống có dấu tiếng Việt) + logo + phụ đề `subtitles` (libass) — rồi đo phụ đề
      thật sự nằm trên khung hình (`subs_really_burned`), không tin returncode;
    · `faster_whisper.audio.decode_audio` trên wav 1 giây, bằng python đang chạy test.

Máy thiếu công cụ thì SKIP — trừ khi `MARKETING_STUDIO_REQUIRE_RUNTIME=1` (CI đặt sau khi cài
theo INSTALL): khi đó thiếu là ĐỎ. "Skip" trên CI trông y hệt "xanh", nên cổng phải tự đòi.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "runners" / "story"))
import runner_deps as RD  # noqa: E402
import truyen_paths as TP  # noqa: E402

BAT_BUOC = os.environ.get("MARKETING_STUDIO_REQUIRE_RUNTIME") == "1"
MAKE_VIDEO = ROOT / "scripts" / "runners" / "story" / "make_video.py"


def _thieu(ly_do: str):
    if BAT_BUOC:
        pytest.fail(f"MARKETING_STUDIO_REQUIRE_RUNTIME=1 mà {ly_do}")
    pytest.skip(ly_do)


def _ff():
    ff = TP.ff_exe("ffmpeg")
    thieu = RD.ffmpeg_thieu_bo_loc(ff)
    if thieu is None:
        _thieu(f"không chạy được ffmpeg ({ff}) — {RD.lenh_cai_ffmpeg()}")
    if thieu:
        _thieu(f"ffmpeg {ff} thiếu bộ lọc {thieu} (P0-9) — {RD.lenh_cai_ffmpeg()}")
    return ff


def _chay(argv, **kw):
    r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", **kw)
    assert r.returncode == 0, f"{argv[:3]}… mã {r.returncode}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    return r


def _engine_gia(goc: Path, ff: str) -> Path:
    """Engine giọng tối thiểu đúng bố cục make_video đọc: `assets/` nền + nhạc + logo."""
    a = goc / "assets"
    a.mkdir(parents=True)
    _chay([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "testsrc2=size=640x360:rate=30:duration=2", "-c:v", "libx264", "-bf", "0",
           "-pix_fmt", "yuv420p", str(a / "Background Image Tiên hiệp 1 clean.mp4")])
    _chay([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "sine=frequency=220:duration=3", "-c:a", "libmp3lame",
           str(a / "Nhạc nền tiên hiệp 1.mp3")])
    _chay([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "color=c=orange:size=120x120", "-frames:v", "1",
           str(a / "Logo nghe tiên truyện 2.png")])
    return goc


def _giong_wav(f: Path, giay: float):
    import math
    import struct
    n = int(16000 * giay)
    with wave.open(str(f), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 8.0)))
                               for i in range(n)))


def test_make_video_dung_duoc_video_CO_tieu_de_drawtext_VA_phu_de(tmp_path):
    ff = _ff()
    eng = _engine_gia(tmp_path / "omnivoice", ff)
    giong = tmp_path / "giong.wav"
    _giong_wav(giong, 5.0)
    srt = tmp_path / "giong.srt"
    srt.write_text("1\n00:00:00,500 --> 00:00:02,200\nChương một: thử nghiệm phụ đề\n\n"
                   "2\n00:00:02,600 --> 00:00:04,600\nĐạo hữu, xin dừng bước\n\n",
                   encoding="utf-8")
    man = tmp_path / "giong.wav.manifest.json"
    man.write_text(json.dumps({"audio": str(giong), "voice_dur": 5.0, "srt": str(srt),
                               "chapters": [{"num": 1, "start": 0.0,
                                             "name": "Khói lửa nhân gian"}]},
                              ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "ra.mp4"
    env = {**os.environ, "OMNIVOICE_DIR": str(eng), "PYTHONUTF8": "1",
           "PYTHONIOENCODING": "utf-8"}
    # FFMPEG_DIR chỉ đặt khi ffmpeg đang dùng KHÔNG nằm trên PATH (vd keg-only trên Mac): như
    # thế make_video tự phân giải giống hệt doctor, không phụ thuộc biến test tự thêm.
    r = _chay([sys.executable, str(MAKE_VIDEO), "--manifest", str(man), "--out", str(out),
               "--w", "640", "--h", "360", "--show", "3"], env=env, timeout=600)
    log = r.stdout + r.stderr
    assert out.is_file() and out.stat().st_size > 10_000, log[-2000:]
    assert "PHỤ ĐỀ HỎNG" not in log, log[-2000:]
    assert "kiểm phụ đề bằng điểm ảnh" in log and ":CÓ(" in log, log[-2000:]
    d = _chay([TP.ff_exe("ffprobe"), "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nokey=1:noprint_wrappers=1", str(out)]).stdout
    assert 4.5 <= float(d.strip()) <= 6.0


def test_decode_audio_THAT_trong_python_dang_chay():
    """Cặp faster-whisper + PyAV của `requirements-runners.txt` chạy được trên OS này."""
    try:
        import av
        import faster_whisper  # noqa: F401
    except ImportError as e:
        _thieu(f"chưa cài requirements-runners.txt ({e})")
    ok, chi_tiet = RD.kiem_decode_audio(sys.executable)
    assert ok is True, chi_tiet
    chinh = int(av.__version__.split(".")[0])
    assert 15 <= chinh < 19, f"PyAV {av.__version__} ngoài khoảng ghim av>=15,<19 (P0-8)"
