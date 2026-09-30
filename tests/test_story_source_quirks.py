"""Regression test cho các QUÁI TÍNH CỦA NGUỒN (tamhoan) từng làm chết pipeline audio truyện.

Chạy: <OMNIVOICE_PY> -m pytest tests/test_story_source_quirks.py   (không cần mạng)

Mỗi test ứng với một sự cố THẬT đã xảy ra — đừng xoá khi refactor:

  T1  08/08/2026: nguồn GÕ SAI số chương (id 108551 ghi 'Chương 2538' trong khi nằm giữa
      2437 và 2439 => thật ra là 2438). crawl tin số của nguồn => last_end nhảy lên 2538
      => pipeline kẹt CỨNG 5 đêm liền (10 lượt chạy hỏng).

  T2  Cùng sự cố, tầng sau: xin chương 2539 (không tồn tại) => resolve_start_id dò trúng
      trang tiêu đề KHÔNG CÓ SỐ ('Tự Chương : Đêm Mưa') => fetch_chapter raise => chết ngay,
      vòng dò không bao giờ bước qua được.

  T3  Chốt chặn cuối: dù crawler có sai kiểu gì, state KHÔNG được phép nhiễm độc.
      Xin 10 chương mà nhận về 108 chương => phải TỪ CHỐI ghi tiến độ.
"""
import os
import shutil
import sys
import tempfile

import pytest

# `read_story` chạy trong VENV GIỌNG (numpy, soundfile, bs4, voice_studio) — không có ở venv
# của repo/CI thì bỏ qua cả file, nói rõ lý do (máy có venv giọng chạy được đầy đủ).
for _m in ("numpy", "soundfile", "bs4", "voice_studio"):
    pytest.importorskip(_m, reason=f"cần venv giọng ({_m}) — chạy bằng OMNIVOICE_PY -m pytest")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts", "runners", "story"))
import read_story  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} :: {detail}")
        FAILED.append(name)


# ---------------------------------------------------------------- T1
def test_crawl_bo_qua_so_chuong_go_sai():
    """Nguồn gõ sai 2438 -> '2538': ID vẫn liên tục, nội dung vẫn liên tục.
    crawl phải NHẬN RA là số gõ sai và dùng số thật (prev+1), KHÔNG được nhảy cóc."""
    pages = {
        108550: (2437, "Chương 2437: Long đảo"),
        108551: (2538, "Chương 2538: Thu hoạch"),   # <-- GÕ SAI, thật ra là 2438
        108552: (2439, "Chương 2439: Trao đổi, đại hội"),
        108553: (2440, "Chương 2440: Đắc quả"),
        108554: (2441, "Chương 2441: Biến đổi của Nhân tộc"),
    }

    def fake_fetch(slug, cid):
        no, title = pages[cid]
        return no, title, [f"đoạn văn của {title}"]

    tmp = tempfile.mkdtemp()
    try:
        chapters = read_story.crawl("pham-nhan-tu-tien", 108550, 10, tmp,
                                    polite=0, fetch_fn=fake_fetch, target_end_no=2440)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    nos = [c["no"] for c in chapters]
    check("T1 dải chương đúng 2437..2440", nos == [2437, 2438, 2439, 2440],
          f"nhận được {nos}")
    check("T1 không dừng sớm ở số gõ sai", nos and nos[-1] == 2440,
          f"chương cuối = {nos[-1] if nos else None} (kỳ vọng 2440)")


# ---------------------------------------------------------------- T2
def test_resolve_bo_qua_trang_khong_co_so():
    """Vòng dò id đâm phải trang tiêu đề không có số => phải BƯỚC QUA, không được chết."""
    anchor_no, anchor_id = read_story.ANCHORS["pham-nhan-tu-tien"]
    target = anchor_no + 4                 # guess = anchor_id + 4
    bad_id = anchor_id + 4                 # đúng ngay ô đoán đầu tiên
    good_id = anchor_id + 5

    def fake_fetch(slug, cid):
        if cid == bad_id:
            raise read_story.UnparsableTitle(
                "cannot parse chapter number from title: 'Tự Chương : Đêm Mưa'")
        if cid == good_id:
            return target, f"Chương {target}: ok", ["nội dung"]
        return anchor_no, f"Chương {anchor_no}: xa", ["nội dung"]

    orig = read_story.fetch_chapter
    read_story.fetch_chapter = fake_fetch
    try:
        got = read_story.resolve_start_id("pham-nhan-tu-tien", target)
        check("T2 dò qua được trang rác", got == good_id, f"trả về id {got}, kỳ vọng {good_id}")
    except Exception as e:
        check("T2 dò qua được trang rác", False, f"vẫn nổ: {type(e).__name__}: {e}")
    finally:
        read_story.fetch_chapter = orig


# ---------------------------------------------------------------- T2b
def test_fetch_chapter_nem_dung_loai_exception():
    """MẮT XÍCH: fetch_chapter phải ném ĐÚNG UnparsableTitle — đó là loại mà resolve_start_id
    bắt để bước qua. Đổi về RuntimeError trần = T2 mất tác dụng và pipeline kẹt lại y như 08/08."""
    PAGE = ('<html><body><h2 class="fs-4">{title}</h2>'
            '<div class="content"><p>Một đoạn văn của chương.</p></div></body></html>')

    class FakeResp:
        def __init__(self, html):
            self.text = html

        def raise_for_status(self):
            pass

    def make_get(html):
        return lambda url, **kw: FakeResp(html)

    orig = read_story.requests.get
    try:
        read_story.requests.get = make_get(PAGE.format(title="Tự Chương : Đêm Mưa"))
        try:
            read_story.fetch_chapter("pham-nhan-tu-tien", 108656)
            check("T2b tiêu đề không số -> UnparsableTitle", False, "không ném gì cả")
        except read_story.UnparsableTitle:
            check("T2b tiêu đề không số -> UnparsableTitle", True)
        except Exception as e:
            check("T2b tiêu đề không số -> UnparsableTitle", False,
                  f"ném nhầm loại {type(e).__name__}")

        # Chốt ngược: tiêu đề bình thường vẫn phải parse ra số (test không tự đúng một cách rỗng).
        read_story.requests.get = make_get(PAGE.format(title="Chương 2439: Trao đổi, đại hội"))
        no, _, paras = read_story.fetch_chapter("pham-nhan-tu-tien", 108552)
        check("T2b tiêu đề bình thường vẫn parse được", no == 2439 and len(paras) == 1,
              f"no={no}, {len(paras)} đoạn")
    finally:
        read_story.requests.get = orig


# ---------------------------------------------------------------- T3
def test_chot_chan_dai_chuong_vo_ly():
    import daily_truyen
    f = daily_truyen.sane_end

    check("T3 dải bình thường được nhận", f(2431, 2440, 2431, 2440, 10) is True)
    check("T3 nguồn skip vài số vẫn nhận", f(2431, 2440, 2431, 2438, 10) is True)
    check("T3 lố 1 chương vẫn nhận", f(2431, 2440, 2431, 2441, 10) is True)
    check("T3 CHẶN dải 108 chương (sự cố 08/08)", f(2431, 2440, 2431, 2538, 10) is False)
    check("T3 CHẶN dải gấp đôi batch", f(2431, 2440, 2431, 2455, 10) is False)
    check("T3 CHẶN act_end lùi về trước start", f(2431, 2440, 2431, 2430, 10) is False)


if __name__ == "__main__":
    for fn in (test_crawl_bo_qua_so_chuong_go_sai,
               test_resolve_bo_qua_trang_khong_co_so,
               test_fetch_chapter_nem_dung_loai_exception,
               test_chot_chan_dai_chuong_vo_ly):
        print(f"\n{fn.__name__}:")
        try:
            fn()
        except Exception as e:
            check(fn.__name__, False, f"{type(e).__name__}: {e}")
    print("\n" + ("=" * 60))
    if FAILED:
        print(f"FAILED {len(FAILED)}: " + ", ".join(FAILED))
        sys.exit(1)
    print("TẤT CẢ PASS")
