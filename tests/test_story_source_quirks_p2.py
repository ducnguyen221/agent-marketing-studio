# -*- coding: utf-8 -*-
"""Regression test cho QUÁI TÍNH CỦA NGUỒN PHẦN 2 (phamnhantutien.org).

Chạy: <OMNIVOICE_PY> -m pytest tests/test_story_source_quirks_p2.py   (KHÔNG cần mạng)

Song sinh với test_source_quirks.py (nguồn tamhoan/P1). Mỗi test ứng với một quái tính THẬT
đã quan sát được khi khảo sát nguồn — đừng xoá khi refactor:

  P2-T1  Nguồn đăng chương TÁCH ĐÔI: hai trang CÙNG số chương, nội dung KHÁC nhau
         (chuong-1170-thuc-tinh + chuong-1170-2-thuc-tinh-2; tương tự 1173). Không gộp thì
         cache Chuong_1170.txt/.wav ghi đè lẫn nhau và mục lục video có 2 mốc trùng số.

  P2-T2  Chương CUỐI (1395) KHÔNG có nút "Chương sau" — đó là tín hiệu HẾT TRUYỆN duy nhất
         (không có tổng số chương nào đáng tin ở chỗ khác).

  P2-T3  Trang "-2" nằm NGAY SAU mốc dừng của lượt chạy: phải gộp nốt RỒI mới dừng, nếu
         không phần 2 của chương cuối lượt bị bỏ mất vĩnh viễn (lượt sau đọc từ chương kế).

  P2-T4  #dt-content lẫn dòng credit dịch giả / ——oOo—— / chú thích (T/g: ...) — đọc lên
         thành tiếng thì lộ hết, phải lọc.

  P2-T5  Nút "Chương sau" trỏ host lạ (link rác/quảng cáo) => KHÔNG được đi theo.

  P2-T6  Tiêu đề có dạng "Chương 0 : Ngoại truyện" (SPACE trước dấu hai chấm) vẫn phải ra số 0.

  P2-T7  Batch ĐẦU TIÊN của phần mới (last_end = -1 -> đọc 0..10, 11 chương) phải qua được
         chốt chặn sane_end, còn dải điên thì vẫn phải bị chặn.

  P2-T8  Mất con trỏ next_url -> resolve số chương -> URL bằng <select> mục lục có sẵn
         trong MỌI trang chương.
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
BASE = "https://phamnhantutien.org/truyen/pham-nhan-tu-tien-phan-2-chi-tien-gioi-thien/"


def check(name, cond, detail=""):
    if cond:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} :: {detail}")
        FAILED.append(name)


def page(title, paras, next_url=None, bottom=False):
    """Dựng HTML một trang chương giống cấu trúc thật (h1 + nút lật + div#dt-content)."""
    nav = ""
    if next_url:
        cls = "dt-bottom-btn dt-btn-blue" if bottom else "dt-nav-btn"
        nav = f'<a class="{cls}" href="{next_url}">Chương sau ▶</a>'
    body = "".join(f"<p>{t}</p>" for t in paras)
    return ('<html><body>'
            f'<h1>{title}</h1>'
            '<div class="dt-nav-bar"><a class="dt-nav-btn" href="#">◀ Chương trước</a>'
            f'{nav}</div>'
            f'<div id="dt-content" class="dt-content-chu">{body}</div>'
            '</body></html>')


def u(name):
    return BASE + name + "/"


def fake_site(pages):
    """pages: {url -> html}. Trả (get_fn, log các URL đã fetch)."""
    fetched = []

    def get_fn(url):
        fetched.append(url)
        if url not in pages:
            raise AssertionError(f"crawler đòi URL ngoài kịch bản: {url}")
        return pages[url]

    return get_fn, fetched


def run_crawl(pages, start, target=None, cap=10):
    get_fn, fetched = fake_site(pages)
    tmp = tempfile.mkdtemp()
    try:
        chapters, next_url, exhausted = read_story.crawl_pntt2(
            start, cap, tmp, target_end_no=target, polite=0, get_fn=get_fn)
        cached = sorted(os.listdir(tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return chapters, next_url, exhausted, fetched, cached


# ---------------------------------------------------------------- P2-T1
def test_chuong_tach_doi_duoc_gop():
    a, b, b2, c, d = u("chuong-1169-x"), u("chuong-1170-thuc-tinh"), \
        u("chuong-1170-2-thuc-tinh-2"), u("chuong-1171-y"), u("chuong-1172-z")
    pages = {
        a: page("Chương 1169: Tên chương A", ["A1", "A2"], next_url=b),
        b: page("Chương 1170: Thức tỉnh", ["phần một câu một", "phần một câu hai"], next_url=b2),
        b2: page("Chương 1170: Thức tỉnh 2", ["phần hai câu một"], next_url=c),
        c: page("Chương 1171: Tên chương C", ["C1"], next_url=d),
        d: page("Chương 1172: Tên chương D", ["D1"], next_url=None),
    }
    chapters, next_url, exhausted, _f, cached = run_crawl(pages, a, target=1171)
    nos = [ch["no"] for ch in chapters]
    check("P2-T1 ra đúng 3 chương 1169/1170/1171", nos == [1169, 1170, 1171], f"nhận {nos}")
    merged = [ch for ch in chapters if ch["no"] == 1170]
    check("P2-T1 chương 1170 GỘP cả 2 phần",
          bool(merged) and merged[0]["paras"] == ["phần một câu một", "phần một câu hai",
                                                  "phần hai câu một"],
          f"paras = {merged[0]['paras'] if merged else None}")
    check("P2-T1 cache KHÔNG có file trùng số", cached == ["Chuong_1169.txt", "Chuong_1170.txt",
                                                           "Chuong_1171.txt"], f"cache {cached}")
    check("P2-T1 next_url trỏ chương CHƯA đọc (1172)", next_url == d, f"next_url={next_url}")
    check("P2-T1 chưa hết truyện", exhausted is False, f"exhausted={exhausted}")


# ---------------------------------------------------------------- P2-T2
def test_het_truyen_khi_mat_nut_chuong_sau():
    a, b = u("chuong-1394-dai-ket-cuc"), u("chuong-1395-cam-nghi")
    pages = {
        a: page("Chương 1394: Đại kết cục", ["A1"], next_url=b),
        b: page("Chương 1395: Cảm nghĩ", ["B1"], next_url=None),   # trang CUỐI: không có nút
    }
    chapters, next_url, exhausted, _f, _c = run_crawl(pages, a, target=1400)
    nos = [ch["no"] for ch in chapters]
    check("P2-T2 giữ nguyên phần đã đọc", nos == [1394, 1395], f"nhận {nos}")
    check("P2-T2 cắm cờ source_exhausted", exhausted is True, f"exhausted={exhausted}")
    check("P2-T2 next_url = None", next_url is None, f"next_url={next_url}")


# ---------------------------------------------------------------- P2-T3
def test_trang_phan_2_ngay_sau_moc_dung():
    """target=1170 và trang kế là phần '-2' của CHÍNH chương 1170 -> phải gộp nốt rồi mới dừng."""
    a, b, b2, c = u("chuong-1169-x"), u("chuong-1170-thuc-tinh"), \
        u("chuong-1170-2-thuc-tinh-2"), u("chuong-1171-y")
    pages = {
        a: page("Chương 1169: Tên chương A", ["A1"], next_url=b),
        b: page("Chương 1170: Thức tỉnh", ["phần một"], next_url=b2),
        b2: page("Chương 1170: Thức tỉnh 2", ["phần hai"], next_url=c),
        c: page("Chương 1171: Tên chương C", ["C1"], next_url=None),
    }
    chapters, next_url, exhausted, fetched, _c = run_crawl(pages, a, target=1170)
    nos = [ch["no"] for ch in chapters]
    check("P2-T3 dừng đúng ở 1170", nos == [1169, 1170], f"nhận {nos}")
    check("P2-T3 gộp nốt phần '-2' trước khi dừng",
          chapters[-1]["paras"] == ["phần một", "phần hai"], f"paras={chapters[-1]['paras']}")
    check("P2-T3 next_url = trang 1171 (chưa đọc)", next_url == c, f"next_url={next_url}")
    check("P2-T3 KHÔNG nuốt mất chương 1171", 1171 not in nos, f"nhận {nos}")
    check("P2-T3 chưa cắm cờ hết truyện", exhausted is False, f"exhausted={exhausted}")


# ---------------------------------------------------------------- P2-T4
def test_loc_junk_dich_gia_va_trang_tri():
    a = u("chuong-0-ngoai-truyen")
    junky = ["Dịch giả : Độc Hành", "Nhóm dịch Phàm Nhân Tông",
             "Nhóm: Phàm Nhân Tông",   # biến thể GẶP THẬT ở chương 1 (UAT 14/08) — không có chữ "dịch"
             "Câu văn truyện thứ nhất.", "(T/g: một ghi chú của tác giả)",
             "Câu văn truyện thứ hai.", "——oOo——"]
    pages = {a: page("Chương 0 : Ngoại truyện", junky, next_url=None)}
    chapters, _n, _e, _f, _c = run_crawl(pages, a, target=0)
    paras = chapters[0]["paras"]
    check("P2-T4 giữ đúng 2 câu văn truyện",
          paras == ["Câu văn truyện thứ nhất.", "Câu văn truyện thứ hai."], f"paras={paras}")
    for bad in ("Dịch giả", "Nhóm dịch", "Nhóm:", "T/g", "oOo"):
        check(f"P2-T4 đã lọc {bad!r}", not any(bad in p for p in paras), f"còn trong {paras}")


# ---------------------------------------------------------------- P2-T5
def test_guard_nut_tro_host_la():
    a = u("chuong-5-x")
    evil = "https://quang-cao-la.example.com/chuong-6-gia/"
    pages = {a: page("Chương 5: Tên chương", ["A1"], next_url=evil)}
    chapters, next_url, exhausted, fetched, _c = run_crawl(pages, a, target=99)
    check("P2-T5 KHÔNG fetch host lạ", all("example.com" not in f for f in fetched),
          f"đã fetch {fetched}")
    check("P2-T5 coi như hết chương", exhausted is True and next_url is None,
          f"exhausted={exhausted} next_url={next_url}")
    check("P2-T5 vẫn giữ chương đã đọc", [c["no"] for c in chapters] == [5])


# ---------------------------------------------------------------- P2-T6
def test_parse_tieu_de():
    html = page("Chương 0 : Ngoại truyện", ["nội dung"], next_url=u("chuong-1-x"))
    no, title, paras, nxt = read_story.parse_chapter_pntt2(html, u("chuong-0-ngoai-truyen"))
    check("P2-T6 'Chương 0 : ...' -> số 0", no == 0, f"no={no}")
    check("P2-T6 lấy được next_url", nxt == u("chuong-1-x"), f"nxt={nxt}")

    bad = page("Lời nói đầu của người dịch", ["nội dung"], next_url=u("chuong-1-x"))
    try:
        read_story.parse_chapter_pntt2(bad, u("loi-noi-dau"))
        check("P2-T6 tiêu đề không số -> UnparsableTitle", False, "không ném gì cả")
    except read_story.UnparsableTitle as e:
        check("P2-T6 tiêu đề không số -> UnparsableTitle", True)
        check("P2-T6 exception mang theo next_url để crawl bước qua được",
              getattr(e, "next_url", None) == u("chuong-1-x"),
              f"next_url={getattr(e, 'next_url', None)}")
    except Exception as e:
        check("P2-T6 tiêu đề không số -> UnparsableTitle", False,
              f"ném nhầm loại {type(e).__name__}")

    # Nút ở CUỐI trang (dt-bottom-btn dt-btn-blue) cũng phải nhận ra.
    hb = page("Chương 7: Tên chương", ["x"], next_url=u("chuong-8-y"), bottom=True)
    _n, _t, _p, nxt2 = read_story.parse_chapter_pntt2(hb, u("chuong-7-x"))
    check("P2-T6 nhận nút 'Chương sau' ở CUỐI trang", nxt2 == u("chuong-8-y"), f"nxt={nxt2}")


# ---------------------------------------------------------------- P2-T7
def test_sane_end_batch_dau():
    import daily_truyen
    f = daily_truyen.sane_end
    check("P2-T7 batch đầu 0..10 được nhận", f(0, 10, 0, 10, 10) is True)
    check("P2-T7 batch đầu thiếu vài số vẫn nhận", f(0, 10, 0, 8, 10) is True)
    check("P2-T7 CHẶN dải điên 0..150", f(0, 10, 0, 150, 10) is False)
    check("P2-T7 dải thường P2 vẫn nhận", f(11, 20, 11, 20, 10) is True)


# ---------------------------------------------------------------- P2-T8
def test_resolve_url_tu_select_muc_luc():
    target = u("chuong-700-bieu-dien-ky-xao")
    opts = "".join(f'<option value="{u(f"chuong-{n}-x")}">Chương {n}: Tên chương</option>'
                   for n in (0, 1, 2, 699, 701))
    opts += f'<option value="{target}">Chương 700: Biểu diễn kỹ xảo</option>'
    html = ('<html><body><div class="dt-nav-bar"><select>' + opts +
            '</select></div><div id="dt-content"><p>x</p></div></body></html>')
    orig = read_story._pntt2_get
    read_story._pntt2_get = lambda url, **kw: html
    try:
        got = read_story.resolve_url_pntt2(u("chuong-0-ngoai-truyen"), 700)
        check("P2-T8 resolve chương 700 -> đúng URL", got == target, f"trả về {got}")
        # Chương KHÔNG tồn tại -> SystemExit có thông điệp hướng dẫn, KHÔNG phải crash mơ hồ.
        try:
            read_story.resolve_url_pntt2(u("chuong-0-ngoai-truyen"), 99999)
            check("P2-T8 chương không tồn tại -> SystemExit", False, "không ném gì cả")
        except SystemExit as e:
            check("P2-T8 chương không tồn tại -> SystemExit", "last_end" in str(e),
                  f"thông điệp: {e}")
    finally:
        read_story._pntt2_get = orig


if __name__ == "__main__":
    for fn in (test_chuong_tach_doi_duoc_gop,
               test_het_truyen_khi_mat_nut_chuong_sau,
               test_trang_phan_2_ngay_sau_moc_dung,
               test_loc_junk_dich_gia_va_trang_tri,
               test_guard_nut_tro_host_la,
               test_parse_tieu_de,
               test_sane_end_batch_dau,
               test_resolve_url_tu_select_muc_luc):
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
