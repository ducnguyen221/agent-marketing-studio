# -*- coding: utf-8 -*-
r"""make_podcast.py — podcast script (txt) + meta → audio.mp3 (giọng my-voice).

Tái dùng logic synth của OmniVoice trong mcp_server.py (_get_model / _synth /
_save) + voice_profiles để dùng giọng clone `my-voice`. Cắt script thành đoạn
ngắn (theo dòng trống + câu) để model đọc ổn định, ghép lại 1 file mp3.

CLI (theo PIPELINE_CONTRACT):
  python make_podcast.py --script F --meta meta.json --out FOLDER\audio.mp3 --profile my-voice
→ in dòng cuối `OK <abs_path mp3>`.

Chạy bằng PYTHON của OmniVoice venv (có torch/omnivoice/soundfile). Model ~3.2GB
load 1 lần (GPU nếu có). Lần đầu chạy thật sẽ nạp model — verify ast-parse không cần model.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

OMNI_DIR = r"C:\Users\DucNguyen\.tts\omnivoice"
if OMNI_DIR not in sys.path:
    sys.path.insert(0, OMNI_DIR)

# Offline mặc định (model đã cache) — giống mcp_server.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


_SENT_RE = re.compile(r"(?<=[.!?…])\s+")


def split_script(text, max_chars=320):
    """Cắt script thành các đoạn <= max_chars: theo dòng trống, rồi theo câu.
    Bỏ markdown nhẹ để giọng đọc sạch."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    blocks = re.split(r"\n\s*\n", text.strip())
    chunks = []
    for blk in blocks:
        blk = " ".join(line.strip() for line in blk.splitlines() if line.strip())
        if not blk:
            continue
        if len(blk) <= max_chars:
            chunks.append(blk)
            continue
        cur = ""
        for sent in _SENT_RE.split(blk):
            if not sent.strip():
                continue
            if len(cur) + len(sent) + 1 <= max_chars:
                cur = (cur + " " + sent).strip()
            else:
                if cur:
                    chunks.append(cur)
                cur = sent.strip()
        if cur:
            chunks.append(cur)
    return [c for c in chunks if c.strip()]


def make_podcast(script_text, out_mp3, profile="my-voice", language="Vietnamese", gap=0.35):
    """Synth từng đoạn bằng giọng profile, ghép thành 1 mp3."""
    import numpy as np
    import mcp_server as ov
    import voice_profiles as vp

    chunks = split_script(script_text)
    if not chunks:
        raise ValueError("Script rỗng — không có nội dung để đọc.")

    model = ov._get_model()
    sr = model.sampling_rate
    # Chọn profile: ưu tiên profile truyền vào, nếu không có thì default.
    prof = profile or vp.get_default() or vp.ensure_default(model)
    silence = np.zeros(int(sr * gap), dtype=np.float32)

    parts = []
    for i, ch in enumerate(chunks, 1):
        print(f"  [podcast] đoạn {i}/{len(chunks)} ({len(ch)} ký tự) ...", flush=True)
        audio = ov._synth(model, ch, language, instruct="", speed=1.0, voice_profile=prof)
        parts.append(np.asarray(audio, dtype=np.float32))
        parts.append(silence)
    full = np.concatenate(parts)

    # _save tự convert .mp3 (libmp3lame) qua imageio-ffmpeg.
    path = ov._save(full, out_mp3, sr)
    dur = len(full) / sr
    print(f"  [podcast] tổng {dur:.1f}s @ {sr}Hz, giọng={prof}", flush=True)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="podcast script → audio.mp3 (OmniVoice my-voice)")
    ap.add_argument("--script", required=True)
    ap.add_argument("--meta", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="my-voice")
    ap.add_argument("--language", default="Vietnamese")
    args = ap.parse_args(argv)

    script_text = _read(args.script)
    if args.meta and os.path.isfile(args.meta):
        # meta chỉ để log/branding, không bắt buộc dùng trong synth.
        try:
            with open(args.meta, encoding="utf-8-sig") as f:
                json.load(f)
        except Exception:
            pass

    path = make_podcast(script_text, args.out, profile=args.profile, language=args.language)
    print(json.dumps({"out": os.path.abspath(path), "profile": args.profile},
                     ensure_ascii=False, indent=2))
    print(f"OK {os.path.abspath(path)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
