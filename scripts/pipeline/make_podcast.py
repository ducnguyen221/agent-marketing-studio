# -*- coding: utf-8 -*-
"""make_podcast.py — kịch bản podcast (txt) + meta → một file audio, qua TRẠM GIỌNG.

    python make_podcast.py --script F --meta meta.json --out <thư mục>/audio.mp3 [--profile P]

Chạy bằng python BÌNH THƯỜNG của repo marketing. Nó không nạp model, không cần torch:
việc đó thuộc về trạm giọng (`agent-voice-studio`), gọi qua `scripts/lib/voice.py` —
**một lần cho cả bài**, nên model chỉ nạp một lần.

Đổi so với bản trước (P2-G3), và vì sao:

- **Hết đường lùi vào bố cục của MỘT máy.** Bản cũ nhét thư mục engine của máy chủ repo
  vào `sys.path` rồi import module private trong đó. Ai clone repo về cũng chạy trúng
  đường đó, và khi nó không tồn tại thì lỗi hiện ra là `ModuleNotFoundError` — không ai
  đoán được phải cài gì. Nay thiếu trạm giọng là **mã 3** kèm đúng các bước cài.
- **Hết tên giọng mặc định.** Bản cũ mặc định một profile có thật của chủ repo. Tên giọng
  là danh tính, không phải hằng số của engine: không khai `--profile` thì trạm giọng dùng
  profile mặc định CỦA KHO, và kho không có mặc định thì nó dừng ở mã 2.
- **Hết tự cắt đoạn + tự chèn khoảng lặng.** Cắt câu và vuốt mối nối là việc của engine
  (`voice-studio speak` làm sẵn). Hai nơi cùng cắt thì nhịp đọc phụ thuộc vào nơi nào cắt
  trước. Ở đây chỉ còn **gỡ markdown** — dấu `**`, backtick, `#` mà lọt vào engine thì bị
  đọc thành tiếng.

Mã thoát theo hợp đồng ba trạm: 0 ok · 1 engine hỏng · 2 gọi/cấu hình sai · 3 trạm thiếu.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402
import voice as VOICE  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

PROG = "make_podcast"


def clean_script(text: str) -> str:
    """Bỏ markdown nhẹ, gộp mỗi đoạn thành một dòng -> text cho engine đọc.

    Giữ RANH GIỚI ĐOẠN (dòng trống) vì engine dùng nó để ngắt hơi; bỏ ngắt dòng giữa
    đoạn vì đó là cách trình bày, không phải chỗ nghỉ.
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    doan = []
    for blk in re.split(r"\n\s*\n", text.strip()):
        mot_dong = " ".join(d.strip() for d in blk.splitlines() if d.strip())
        if mot_dong:
            doan.append(mot_dong)
    return "\n\n".join(doan)


def make_podcast(script_text: str, out: str, profile: str | None = None,
                 language: str | None = None) -> dict:
    """Đọc cả bài thành một file audio -> dict kết quả của trạm giọng."""
    sach = clean_script(script_text)
    if not sach:
        raise SC.ContractError("kịch bản rỗng — không có gì để đọc")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="make-podcast-") as tam:
        # Đưa qua FILE chứ không qua `--text`: một bài dài vượt giới hạn dòng lệnh của
        # Windows (~32 000 ký tự) và lỗi khi đó là "tham số sai", không ai lần ra vì sao.
        f = Path(tam) / "loi-doc.txt"
        f.write_text(sach, encoding="utf-8", newline="\n")
        return VOICE.speak(file=str(f), out=out, profile=profile, lang=language)


def chay(args) -> dict:
    kich = Path(args.script)
    if not kich.is_file():
        raise SC.ContractError(f"không thấy kịch bản {args.script}")
    if args.meta and os.path.isfile(args.meta):
        # `meta` chỉ để người đọc log biết đang dựng bài nào; nội dung không vào bản đọc.
        try:
            with open(args.meta, encoding="utf-8-sig") as m:
                SC.log(f"[{PROG}] bài: {(json.load(m) or {}).get('title', '(không tiêu đề)')}")
        except (OSError, ValueError):
            SC.log(f"[{PROG}] meta {args.meta} đọc không được — bỏ qua, không chặn")
    ra = make_podcast(kich.read_text(encoding="utf-8"), args.out,
                      profile=args.profile or None, language=args.language or None)
    duong = (ra.get("outputs") or [{}])[0].get("path") or args.out
    SC.log(f"[{PROG}] xong: {duong}")
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog=PROG, description="Kịch bản podcast → audio, qua trạm giọng (không nạp model ở đây).")
    ap.add_argument("--script", required=True, help="file .txt/.md chứa kịch bản")
    ap.add_argument("--meta", default="", help="meta.json của bài (chỉ để log)")
    ap.add_argument("--out", required=True, help="file audio ra (.mp3 hoặc .wav)")
    ap.add_argument("--profile", default="",
                    help="tên profile giọng; bỏ trống = profile mặc định của kho giọng")
    ap.add_argument("--language", default="", help="tên ngôn ngữ cho engine")
    ap.add_argument("--json", action="store_true", help="một dòng JSON kết quả cuối stdout")
    args, ma = SC.parse(ap, argv)
    if args is None:
        return ma
    args.prog = PROG
    if args.json:
        return SC.run(chay, args, as_json=True)
    try:
        ra = chay(args)
    except Exception as e:                # noqa: BLE001 — biên CLI: lỗi phải thành mã thoát
        SC.log(f"[{PROG}] LỖI ({SC.classify(e)}): {e}")
        return SC.classify(e)
    print(f"OK {os.path.abspath((ra.get('outputs') or [{}])[0].get('path') or args.out)}")
    return SC.OK


if __name__ == "__main__":
    sys.exit(main())
