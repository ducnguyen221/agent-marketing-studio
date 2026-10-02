# -*- coding: utf-8 -*-
"""
read_story.py — crawl chapters from tamhoan.com and read them aloud with OmniVoice,
using a saved voice profile (default: "Giọng tiên hiệp") for a consistent narrator.

Pipeline (per the spec):
  1. Fetch a chapter page, extract ONLY the story text:
       - title  = <h2 class="fs-4 ...">  e.g. "Chương 1141: Chặn giết"
       - body   = <p> paragraphs inside <div class="content ...">
     (nothing else on the page is read).
  2. Move to the next chapter by incrementing the trailing numeric id in the URL,
     then VERIFY its title's chapter number is exactly previous + 1.
  3. Concatenate chapters: each = title (read first) + body. Audio for several
     chapters is joined with a ~1 minute silence between chapters.
  4. Narrate with OmniVoice voice profile, sentence-level pauses for "nhấn nhá".

Uses the published voice-studio engine API (voice_studio.engine: load / synth / save),
so CLI and agent paths stay identical. Runs offline on GPU.

Example:
  python read_story.py --start-id 107258 --chapters 2 --voice "Giọng tiên hiệp"
"""
import argparse
import os
import re
import sys
import time

import subprocess

import numpy as np
import requests
import soundfile as sf
from bs4 import BeautifulSoup

# Engine giọng qua API ĐÃ PHÁT HÀNH của agent-voice-studio (voice_studio.engine, API 1.x) — không
# còn nạp shim `mcp_server` của trạm, chỉ tìm thấy nhờ .pth trỏ đường máy Windows.
# Khác duy nhất so với shim cũ: profile giọng hỏng/thiếu thì engine.synth NÉM LỖI thay vì lặng lẽ
# đọc bằng giọng ngẫu nhiên (compat._synth lùi về instruct) — lượt đêm hỏng to còn hơn đăng
# 2 tiếng sai giọng. Import rẻ (không nạp torch), tự đặt HF offline như shim cũ.
from voice_studio import engine as ov_engine


def _add_bgm(mp3_path, music_path, vol, total_dur):
    """Ghép nhạc nền nhẹ dưới giọng đọc (loop nhạc cho đủ dài, fade in/out, giọng giữ độ to)."""
    ff = ov_engine.ffmpeg()
    tmp = mp3_path + ".__bgm.mp3"
    fo = max(0.0, total_dur - 2.5)
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", mp3_path,
           "-stream_loop", "-1", "-i", music_path, "-filter_complex",
           f"[1:a]volume={vol},afade=t=in:st=0:d=2,afade=t=out:st={fo:.2f}:d=2.5[bg];"
           f"[0:a][bg]amix=inputs=2:duration=first:normalize=0[a]",
           "-map", "[a]", "-c:a", "libmp3lame", "-q:a", "2", tmp]
    subprocess.run(cmd, check=True, capture_output=True)
    os.replace(tmp, mp3_path)
    print(f"[bgm] đã ghép nhạc nền (vol {vol}) -> {mp3_path}")

_HERE = os.path.dirname(os.path.abspath(__file__))
# Da doi sang apps/truyen/ (2026-08-26); du lieu van o goc engine.
import truyen_paths  # noqa: E402  — phân giải Windows + macOS
ENGINE = truyen_paths.engine_dir()

BASE = "https://tamhoan.com/{slug}/{id}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
JUNK = ("tamhoan.com", "chia sẻ", "báo lỗi", "bình luận", "nguồn:", "vui lòng bật javascript")

# Seed (chapter_no, url_id) per slug to resolve "chương N" -> URL id (no parseable index page;
# ids are ~sequential, so guess by offset then walk ±1 verifying the real title number).
ANCHORS = {"pham-nhan-tu-tien": (1141, 107258)}

# Nguồn ĐÔI KHI bỏ vài số chương (1242 -> 1244) — hợp lệ. Nhưng nhảy XA hơn ngần này trong khi
# ID vẫn liên tục thì không phải "skip", mà là GÕ SAI SỐ (08/08/2026: id 108551 nằm giữa 2437 và
# 2439 nhưng đề 'Chương 2538'). Tin con số đó => last_end nhảy 100 chương => pipeline kẹt cứng.
JUMP_MAX = 10

# Số trang LIỀN NHAU không đánh số mà crawl chịu được trước khi coi là "hết chương đánh số"
# (13/08/2026: truyện kết ở 'Chương 2446: Đại Kết Cục', các id sau đều là 'Phàm Nhân ngoại
# truyện (1..n)'). Chỉ áp dụng khi ĐÃ đọc được ít nhất 1 chương trong lượt này.
MAX_UNNUMBERED_RUN = 3


class UnparsableTitle(RuntimeError):
    """Trang có cấu trúc hợp lệ nhưng tiêu đề KHÔNG chứa số chương.

    Gặp ở ngoại truyện / phần mở đầu ('Phàm Nhân ngoại truyện (1)', 'Tự Chương : Đêm Mưa').
    Tách riêng khỏi RuntimeError để vòng dò id BƯỚC QUA được thay vì chết cả lượt chạy.
    """


def resolve_start_id(slug, target_chapter, max_walk=60):
    """Find the URL id whose title is exactly 'Chương <target_chapter>' for this slug."""
    if slug not in ANCHORS:
        raise SystemExit(f"Chưa có anchor cho slug '{slug}'. Hãy truyền --start-id trực tiếp.")
    cno, cid = ANCHORS[slug]
    guess = cid + (target_chapter - cno)
    step, skipped = 1, 0
    for _ in range(max_walk):
        try:
            chap_no, _, _ = fetch_chapter(slug, guess)
        except UnparsableTitle as e:
            # Trang không đánh số xen giữa: đi tiếp THEO HƯỚNG ĐANG DÒ, đừng bỏ cuộc.
            skipped += 1
            print(f"[resolve] id {guess} không có số chương ({e}) — bỏ qua, dò tiếp.", flush=True)
            guess += step
            continue
        if chap_no == target_chapter:
            return guess
        step = 1 if chap_no < target_chapter else -1
        guess += step
    raise SystemExit(
        f"Không resolve được id cho chương {target_chapter} (slug {slug}) sau {max_walk} bước"
        + (f", đã bỏ qua {skipped} trang không đánh số" if skipped else "")
        + f". Nhiều khả năng chương {target_chapter} CHƯA TỒN TẠI trên nguồn — kiểm tra "
          f"'last_end' trong truyen-state.json xem có bị đẩy quá xa không.")


def fetch_chapter(slug, cid, retries=6):
    """Return (chapter_number:int, title:str, paragraphs:list[str]) for one page.

    Site hay chậm/timeout lúc rạng sáng (20260706: cả 3 lượt 01/03/05h chết vì
    read-timeout 30s x3 retry) → timeout 60s + backoff luỹ thừa tối đa ~2 phút/lần,
    tổng chịu đựng ~6 phút thay vì ~1.5 phút.
    """
    url = BASE.format(slug=slug, id=cid)
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            break
        except Exception as e:  # transient network: back off and retry
            last = e
            wait = min(120, 5 * (2 ** attempt))
            print(f"[fetch] lỗi lần {attempt + 1}/{retries} ({e}) — chờ {wait}s rồi thử lại", flush=True)
            time.sleep(wait)
    else:
        raise RuntimeError(f"fetch failed for {url}: {last}")

    s = BeautifulSoup(r.text, "lxml")
    h2 = s.select_one("h2.fs-4")
    content = s.select_one("div.content")
    if not h2 or not content:
        raise RuntimeError(f"structure not found on {url} (h2={bool(h2)} content={bool(content)})")
    title = h2.get_text(strip=True)
    m = re.search(r"Chương\s+(\d+)", title)
    if not m:
        raise UnparsableTitle(f"cannot parse chapter number from title: {title!r}")
    chap_no = int(m.group(1))

    paras = []
    for p in content.find_all("p"):
        t = p.get_text(" ", strip=True)
        if not t:
            continue
        low = t.lower()
        if any(j in low for j in JUNK):
            continue
        if t == title:  # title sometimes echoed inside content
            continue
        paras.append(t)
    if not paras:
        raise RuntimeError(f"no story paragraphs extracted on {url}")
    return chap_no, title, paras


# ---- truyenfull.today: chương ở /<slug>/chuong-N/ (số trực tiếp, KHÔNG cần resolve id) ----
TF_HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
              "Accept": "text/html,application/xhtml+xml", "Accept-Language": "vi,en;q=0.8"}
TF_JUNK = ("truyenfull", "nguồn:", "đọc truyện", "vui lòng", "quảng cáo", "bạn đang đọc",
           "chương trước", "chương sau", "mục lục")


def fetch_chapter_truyenfull(slug, chap_no, retries=3):
    """(chapter_no, title, paragraphs) cho truyenfull.today — content #chapter-c, tách <br>."""
    url = f"https://truyenfull.today/{slug}/chuong-{chap_no}/"
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=TF_HEADERS, timeout=30)
            r.raise_for_status()
            break
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"fetch failed for {url}: {last}")
    s = BeautifulSoup(r.text, "lxml")
    c = s.select_one("#chapter-c") or s.select_one(".chapter-c")
    if not c:
        raise RuntimeError(f"#chapter-c not found on {url}")
    for tag in c.select("script,style,ins,iframe,[class*=ads],[id*=ads],.ad"):
        tag.decompose()
    for br in c.find_all("br"):
        br.replace_with("\n")
    paras = []
    for ln in c.get_text("\n").split("\n"):
        ln = ln.strip()
        if not ln or any(j in ln.lower() for j in TF_JUNK):
            continue
        paras.append(ln)
    if not paras:
        raise RuntimeError(f"no story text extracted on {url}")
    return chap_no, f"Chương {chap_no}", paras


# ---------------------------------------------------------------------------------------
# phamnhantutien.org (PHẦN 2) — lật chương bằng NÚT "Chương sau", KHÔNG đoán id/số trong URL.
#
# Vì sao khác hẳn tamhoan: URL chương ở đây là slug chữ (`/chuong-700-bieu-dien-ky-xao/`),
# không có id số để cộng trừ. Nguồn tự cho sẵn con trỏ đi tiếp (nút "Chương sau") và một
# mục lục ĐẦY ĐỦ nằm ngay trong mỗi trang (thẻ <select> trong dt-nav-bar) -> dùng cả hai:
# nút để đi tiếp, <select> để nhảy tới một chương bất kỳ khi mất con trỏ.
# ---------------------------------------------------------------------------------------
PNTT2_HOST = "phamnhantutien.org"

# Dòng KHÔNG phải văn truyện, nhận diện theo ĐẦU DÒNG (đã lower + strip).
PNTT2_JUNK_PREFIX = ("dịch giả", "dịch :", "dịch:", "nhóm dịch", "nhóm:", "nhóm :",
                     "converter", "biên tập",
                     "độc hành lưu ký", "(t/g", "nguồn:", "——", "--oo", "—oOo—".lower())
# "nhóm:"/"nhóm :" thêm 2026-08-14 (UAT): chương 1 mở đầu bằng credit `Nhóm: Phàm Nhân Tông`
# — biến thể của "Nhóm dịch ..." mà recon chưa gặp; văn truyện không có dòng nào mở đầu "Nhóm:".
# Dòng chứa các cụm này ở bất kỳ đâu -> bỏ (quảng cáo / lời nhắc của web).
PNTT2_JUNK_SUB = ("vui lòng bật javascript", "quảng cáo", "phamnhantutien.org")

# Trang chương "tách đôi": nguồn đăng 2 trang CÙNG số chương, nội dung KHÁC nhau
# (vd `chuong-1170-thuc-tinh` + `chuong-1170-2-thuc-tinh-2`, tương tự 1173).
# Phải GỘP vào một chương, nếu không cache `Chuong_<no>.txt`/`.wav` sẽ ghi đè lẫn nhau
# và mục lục video sẽ có 2 mốc trùng số.


def _pntt2_get(url, retries=6):
    """FETCH DUY NHẤT của nguồn pntt2 — MỌI caller (crawl, resolver, peek-merge) phải đi qua đây.

    Bài học 08/2026 (tamhoan): lớp phòng thủ retry chỉ được lắp ở resolve_start_id còn crawl()
    thì không, nên nguồn chập chờn vẫn giết cả lượt chạy. Một cửa vào = một chỗ để vá.
    """
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=TF_HEADERS, timeout=60)
            r.raise_for_status()
            return r.text
        except Exception as e:  # transient network: back off and retry
            last = e
            wait = min(120, 5 * (2 ** attempt))
            print(f"[fetch] lỗi lần {attempt + 1}/{retries} ({e}) — chờ {wait}s rồi thử lại", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"fetch failed for {url}: {last}")


def _pntt2_is_junk(line, title):
    low = line.lower().strip()
    if not low:
        return True
    if line.strip() == title.strip():          # tiêu đề đôi khi lặp trong thân bài
        return True
    if low.startswith(PNTT2_JUNK_PREFIX):
        return True
    if any(j in low for j in PNTT2_JUNK_SUB):
        return True
    if not re.search(r"[0-9a-zA-ZÀ-ỹ]", line):  # dòng chỉ toàn ký tự trang trí: ——oOo——, ***
        return True
    return False


def _pntt2_next_url(soup, cur_url):
    """href của nút 'Chương sau' (đầu hoặc cuối trang). None = trang CUỐI TRUYỆN.

    Guard link rác: chỉ nhận URL cùng host pntt2 và có '/chuong-'. Sai -> coi như KHÔNG có
    next (thà dừng đúng chỗ còn hơn đi lạc sang trang khác rồi đọc nhầm nội dung).
    """
    from urllib.parse import urljoin
    for a in soup.select("a.dt-nav-btn, a.dt-bottom-btn, a.dt-btn-blue"):
        if "chương sau" not in a.get_text(" ", strip=True).lower():
            continue
        href = urljoin(cur_url, (a.get("href") or "").strip())
        if PNTT2_HOST in href and "/chuong-" in href:
            return href
        print(f"[crawl][warn] nút 'Chương sau' trỏ link LẠ ({href!r}) — bỏ qua, coi như hết chương.")
        return None
    return None


def parse_chapter_pntt2(html, url):
    """(chap_no, title, paras, next_url) từ HTML một trang chương pntt2.

    Tiêu đề không có số -> raise UnparsableTitle (kèm thuộc tính .next_url để vòng crawl vẫn
    BƯỚC QUA được trang đó thay vì chết cả lượt — cùng chính sách với tamhoan).
    """
    s = BeautifulSoup(html, "lxml")
    nxt = _pntt2_next_url(s, url)

    h1 = s.select_one("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    m = re.search(r"Chương\s+(\d+)", title)
    if not m:
        e = UnparsableTitle(f"cannot parse chapter number from title: {title!r} ({url})")
        e.next_url = nxt
        raise e
    chap_no = int(m.group(1))

    content = s.select_one("#dt-content")
    if not content:
        raise RuntimeError(f"#dt-content not found on {url}")
    for tag in content.select("script,style,ins,iframe,[class*=ads],[id*=ads],.ad"):
        tag.decompose()
    paras = []
    for p in content.find_all("p", recursive=False) or content.find_all("p"):
        t = p.get_text(" ", strip=True)
        if not _pntt2_is_junk(t, title):
            paras.append(t)
    if not paras:
        raise RuntimeError(f"no story paragraphs extracted on {url}")
    return chap_no, title, paras, nxt


def resolve_url_pntt2(any_chapter_url, target_no):
    """URL của 'Chương <target_no>' đọc từ mục lục <select> có sẵn trong MỌI trang chương.

    Dùng khi mất con trỏ next_url (state mới / reset tay). Không thấy -> SystemExit với
    thông điệp kiểu P1 để người đọc log biết ngay là do 'last_end' bị đẩy quá xa.
    """
    if not any_chapter_url:
        raise SystemExit("pntt2: cần --url (một trang chương bất kỳ) để resolve số chương -> URL.")
    s = BeautifulSoup(_pntt2_get(any_chapter_url), "lxml")
    opts = s.select("div.dt-nav-bar select option") or s.select("select option")
    pat = re.compile(rf"^\s*Chương\s+{target_no}\b")
    for o in opts:
        if pat.match(o.get_text(" ", strip=True)):
            href = (o.get("value") or "").strip()
            if PNTT2_HOST in href and "/chuong-" in href:
                return href
    raise SystemExit(
        f"Không tìm thấy chương {target_no} trong mục lục nguồn ({len(opts)} mục). "
        f"Nhiều khả năng chương {target_no} CHƯA TỒN TẠI trên nguồn — kiểm tra 'last_end' "
        f"trong truyen-state.json xem có bị đẩy quá xa không.")


def _pntt2_cache(cache_dir, no, title, paras):
    with open(os.path.join(cache_dir, f"Chuong_{no}.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(title + "\n\n" + "\n".join(paras))


def crawl_pntt2(start_url, n_pages_cap, cache_dir, target_end_no=None, polite=2.0, get_fn=None):
    """Crawl pntt2 theo NÚT 'Chương sau'. Trả (chapters, next_url, source_exhausted).

      next_url        = URL trang CHƯA đọc kế tiếp -> con trỏ resume cho lượt sau (state).
      source_exhausted= True khi trang cuối KHÔNG còn nút 'Chương sau' = HẾT TRUYỆN.
    """
    os.makedirs(cache_dir, exist_ok=True)
    getf = get_fn or (lambda u: _pntt2_get(u))
    chapters, prev_no, unnumbered = [], None, 0
    url, next_url, source_exhausted = start_url, None, False
    max_pages = n_pages_cap if target_end_no is None else max(n_pages_cap, 1) + 4

    for _ in range(max_pages):
        try:
            no, title, paras, nxt = parse_chapter_pntt2(getf(url), url)
        except UnparsableTitle as e:
            # Trang hợp lệ nhưng tiêu đề KHÔNG có số (ngoại truyện / lời bạt): BỎ QUA, đi tiếp.
            nxt = getattr(e, "next_url", None)
            unnumbered += 1
            print(f"[crawl][skip] {url} không có số chương ({e}) — bỏ qua, đi tiếp.")
            if nxt is None:
                source_exhausted = True
                break
            url = next_url = nxt
            if chapters and unnumbered >= MAX_UNNUMBERED_RUN:
                print(f"[crawl] {unnumbered} trang liền không đánh số sau chương {prev_no} "
                      f"=> coi như HẾT chương đánh số — dừng, giữ phần đã đọc.")
                break
            time.sleep(polite)
            continue
        unnumbered = 0

        if prev_no is not None:
            if no == prev_no:
                same = (chapters and len(paras) == len(chapters[-1]["paras"])
                        and paras[:1] == chapters[-1]["paras"][:1])
                if same:
                    print(f"[crawl][skip] {url} là bản LẶP của chương {no} — bỏ qua.")
                else:
                    # CHƯƠNG TÁCH ĐÔI (1170, 1173): cùng số, nội dung KHÁC -> GỘP làm một.
                    chapters[-1]["paras"] += paras
                    _pntt2_cache(cache_dir, no, chapters[-1]["title"], chapters[-1]["paras"])
                    print(f"[crawl][merge] {url} là PHẦN TIẾP của chương {no} "
                          f"(+{len(paras)} đoạn) — đã gộp vào chương {no}.")
                if nxt is None:
                    source_exhausted = True
                    break
                url = next_url = nxt
                time.sleep(polite)
                continue
            if no < prev_no:
                raise RuntimeError(
                    f"chapter sequence broke: {url} là 'Chương {no}' nhưng KHÔNG tăng "
                    f"(prev={prev_no}). Dừng để tránh đọc nhầm/lặp chương.")
            if no > prev_no + JUMP_MAX:
                # Chuỗi nút liên tục mà số nhảy cả trăm => nguồn GÕ SAI SỐ (bài học 08/08/2026).
                fixed = prev_no + 1
                print(f"[crawl][typo] {url} đề 'Chương {no}' nhưng đi liền sau chương {prev_no} "
                      f"=> nguồn GÕ SAI SỐ. Dùng số thật {fixed}.")
                title = re.sub(r"Chương\s+\d+", f"Chương {fixed}", title, count=1)
                no = fixed
            elif no > prev_no + 1:
                print(f"[crawl][warn] nguồn NHẢY số chương {prev_no} -> {no}; "
                      f"số {prev_no + 1}..{no - 1} không có trên nguồn — đọc tiếp theo nút.")

        _pntt2_cache(cache_dir, no, title, paras)
        print(f"[crawl] {url}  ->  Chương {no}: {title.split(':', 1)[-1].strip()}  "
              f"({len(paras)} đoạn, {sum(len(p) for p in paras)} ký tự)")
        chapters.append({"no": no, "title": title, "paras": paras})
        prev_no = no

        if target_end_no is not None and no >= target_end_no:
            # ĐẠT MỐC: nhưng chương này có thể còn PHẦN TIẾP ở trang sau (tách đôi). PEEK cho
            # tới khi trang kế mang SỐ KHÁC, rồi mới dừng — nếu không, phần 2 của chương cuối
            # sẽ bị bỏ mất vĩnh viễn (lượt sau bắt đầu từ chương kế tiếp).
            while nxt:
                try:
                    no2, _t2, paras2, nxt2 = parse_chapter_pntt2(getf(nxt), nxt)
                except UnparsableTitle:
                    break          # để trang đó cho lượt sau xử lý
                if no2 != no:
                    break          # chương mới -> chưa đọc, để dành lượt sau
                chapters[-1]["paras"] += paras2
                _pntt2_cache(cache_dir, no, chapters[-1]["title"], chapters[-1]["paras"])
                print(f"[crawl][merge] {nxt} là PHẦN TIẾP của chương {no} "
                      f"(+{len(paras2)} đoạn) — đã gộp trước khi dừng.")
                nxt = nxt2
            next_url = nxt
            source_exhausted = nxt is None
            print(f"[crawl] đạt mốc kết: chương {no} >= {target_end_no} — dừng.")
            break

        if nxt is None:
            source_exhausted = True
            next_url = None
            print(f"[crawl] chương {no} KHÔNG còn nút 'Chương sau' => HẾT TRUYỆN trên nguồn.")
            break
        url = next_url = nxt
        time.sleep(polite)

    return chapters, next_url, source_exhausted


def crawl(slug, start_id, n_chapters, cache_dir, polite=1.0, fetch_fn=fetch_chapter, target_end_no=None):
    """Crawl chapters starting at start_id, verifying sequential chapter numbers.
    target_end_no đặt -> DỪNG khi SỐ chương cuối >= target (luôn kết ĐÚNG mốc chẵn chục dù nguồn
    skip/gộp số chương, vd 1400 chứ không 1401); n_chapters khi đó chỉ là TRẦN AN TOÀN số trang.
    None -> đọc đúng n_chapters trang (count-based, như cũ).
    Caches each chapter's text to cache_dir/Chuong_<no>.txt so re-runs skip the network."""
    os.makedirs(cache_dir, exist_ok=True)
    chapters = []
    prev_no = None
    cid = start_id
    max_pages = n_chapters if target_end_no is None else max(n_chapters, 1) + 4
    unnumbered = 0
    for i in range(max_pages):
        try:
            chap_no, title, paras = fetch_fn(slug, cid)
        except UnparsableTitle as e:
            # Trang hợp lệ nhưng tiêu đề KHÔNG có số chương (ngoại truyện / tự chương / lời bạt).
            # 13/08/2026: đọc xong 'Chương 2446: Đại Kết Cục' thì id kế là 'Phàm Nhân ngoại
            # truyện (1)' -> nổ giữa batch, mất cả 6 chương đã crawl. Cùng chính sách với
            # resolve_start_id: BỎ QUA trang đó, đọc tiếp ID sau, KHÔNG abort cả lượt.
            unnumbered += 1
            print(f"[crawl][skip] id {cid} không có số chương ({e}) — bỏ qua, đọc tiếp ID sau.")
            cid += 1
            if chapters and unnumbered >= MAX_UNNUMBERED_RUN:
                print(f"[crawl] {unnumbered} trang liền không đánh số sau chương {prev_no} "
                      f"=> coi như HẾT chương đánh số trên nguồn — dừng, giữ phần đã đọc.")
                break
            time.sleep(polite)
            continue
        unnumbered = 0
        # Chương GỘP: nguồn đôi khi gộp nhiều chương vào 1 trang, vd "Chương 1216+1217: ...".
        # Lấy DẢI số trong phần đầu tiêu đề (trước dấu ':'): start = số đầu, end = số cuối.
        _head = title.split(":", 1)[0]
        _nums = [int(x) for x in re.findall(r"\d+", _head)] or [chap_no]
        start_no, end_no = _nums[0], _nums[-1]
        if prev_no is not None:
            if start_no <= prev_no:
                # Nguồn ĐÔI KHI đăng LẶP một chương (cùng số, cùng nội dung) dưới 1 id khác,
                # vd id 107975 và 107976 đều là 'Chương 1862' y hệt nhau. Nếu đúng là bản lặp
                # của chương vừa đọc -> BỎ QUA, đọc tiếp ID kế (KHÔNG abort cả batch).
                if (start_no == prev_no and chapters
                        and chapters[-1]["no"] == chap_no
                        and len(paras) == len(chapters[-1]["paras"])
                        and paras[:1] == chapters[-1]["paras"][:1]):
                    print(f"[crawl][skip] id {cid} là bản LẶP của chương {chap_no} "
                          f"(cùng nội dung, đã đọc) — bỏ qua, đọc tiếp ID sau.")
                    cid += 1
                    continue
                # Lùi số / lặp KHÁC nội dung = lệch ID thật sự -> DỪNG để tránh đọc nhầm chương.
                raise RuntimeError(
                    f"chapter sequence broke: id {cid} là 'Chương {chap_no}' nhưng KHÔNG tăng "
                    f"(prev={prev_no}). Dừng để tránh đọc nhầm/lặp chương.")
            if start_no > prev_no + JUMP_MAX:
                # ID liên tục mà số chương nhảy CẢ TRĂM => nguồn GÕ SAI SỐ, không phải skip.
                # Sự cố 08/08/2026: id 108551 đề 'Chương 2538' nhưng nằm ngay giữa 2437 và 2439.
                # Lấy số THẬT theo vị trí (prev+1) và sửa luôn tiêu đề để mục lục video/YouTube
                # không mang số sai. Chương gộp bị gõ sai thì coi như chương đơn — hiếm & an toàn.
                fixed = prev_no + 1
                print(f"[crawl][typo] id {cid} đề 'Chương {start_no}' nhưng ID liên tục ngay sau "
                      f"chương {prev_no} => nguồn GÕ SAI SỐ. Dùng số thật {fixed}.")
                title = re.sub(r"Chương\s+\d+", f"Chương {fixed}", title, count=1)
                chap_no = start_no = end_no = fixed
            elif start_no > prev_no + 1:
                # Nguồn ĐÔI KHI bỏ qua 1 số chương (vd 1242 -> 1244): ID vẫn liên tục nên
                # đây là chương kế tiếp hợp lệ. Cảnh báo + đọc tiếp thay vì abort cả batch.
                print(f"[crawl][warn] nguồn NHẢY số chương {prev_no} -> {start_no} (id {cid}); "
                      f"số {prev_no + 1}..{start_no - 1} không có trên nguồn — đọc tiếp theo ID.")
        cache_path = os.path.join(cache_dir, f"Chuong_{chap_no}.txt")
        with open(cache_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(title + "\n\n" + "\n".join(paras))
        print(f"[crawl] id={cid}  ->  Chương {chap_no}: {title.split(':',1)[-1].strip()}  "
              f"({len(paras)} đoạn, {sum(len(p) for p in paras)} ký tự)")
        chapters.append({"no": chap_no, "title": title, "paras": paras})
        prev_no = end_no  # chương gộp: nhảy tới số CUỐI để trang kế (số đầu) khớp liên tục
        cid += 1
        if target_end_no is not None and end_no >= target_end_no:
            print(f"[crawl] đạt mốc kết: chương {end_no} >= {target_end_no} — dừng (kết chẵn chục).")
            break
        time.sleep(polite)
    return chapters


_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")

# --- Vietnamese number reading so "Chương 1141" is spoken clearly as words, not digits ---
_U = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read_below_hundred(n):
    tens, unit = divmod(n, 10)
    if tens == 0:
        return _U[unit] if unit else ""
    if tens == 1:
        if unit == 0:
            return "mười"
        return "mười " + ("lăm" if unit == 5 else _U[unit])
    s = _U[tens] + " mươi"
    if unit == 0:
        return s
    return s + " " + ("mốt" if unit == 1 else "lăm" if unit == 5 else _U[unit])


def _read_below_1000(n, force_hundred=False):
    h, rem = divmod(n, 100)
    if h == 0 and not force_hundred:
        return _read_below_hundred(rem)
    out = _U[h] + " trăm"
    if rem:
        out += " " + ("lẻ " + _U[rem] if rem < 10 else _read_below_hundred(rem))
    return out


def num2words_vi(n):
    """Read a non-negative integer (chapter range) as Vietnamese words."""
    if n == 0:
        return "không"
    if n < 1000:
        return _read_below_1000(n)
    th, rem = divmod(n, 1000)
    out = _read_below_1000(th) + " nghìn"
    if rem:
        out += " " + _read_below_1000(rem, force_hundred=True)
    return out


def spoken_title(title):
    """Normalize 'Chương 1141: Chặn giết' -> 'Chương 1141. Chặn giết.'  The chapter number is
    kept as DIGITS on purpose: ASR tests showed OmniVoice reads digit numbers reliably but
    mangles long spelled-out number-words ('một nghìn một trăm...' -> collapses to '141')."""
    m = re.match(r"\s*Chương\s+(\d+)\s*[:\.\-]?\s*(.*)$", title)
    if not m:
        return title.rstrip(" .") + "."
    num, name = m.group(1), m.group(2).strip().rstrip(".")
    return f"Chương {num}. {name}." if name else f"Chương {num}."


def make_chunks(title, paras, max_chars=380, preview_sents=0):
    """Body split into <=max_chars chunks at sentence boundaries (never mid-sentence, pauses
    naturally at '.'). The spoken title (number as words) is MERGED into the first chunk —
    a standalone tiny title chunk makes the clone voice render unstably / drop words, so it
    is read as the lead of the opening utterance instead. If preview_sents>0, keep only the
    first N sentences of the body."""
    sents = []
    for para in paras:
        for sent in _SENT_SPLIT.split(para):
            sent = sent.strip()
            if sent:
                sents.append(sent)
    if preview_sents > 0:
        sents = sents[:preview_sents]
    chunks = []
    buf = ""
    for sent in sents:
        if len(sent) > max_chars:  # câu dài: cắt tại DẤU PHẨY (ngắt tự nhiên), không cắt giữa cụm
            if buf:
                chunks.append(buf)
                buf = ""
            cl_buf = ""
            for cl in re.split(r"(?<=[,;:])\s+", sent):
                if len(cl_buf) + 1 + len(cl) <= max_chars:
                    cl_buf = (cl_buf + " " + cl).strip()
                else:
                    if cl_buf:
                        chunks.append(cl_buf)
                    if len(cl) > max_chars:   # cụm vẫn quá dài (hiếm) -> cắt theo space
                        for piece in re.findall(r".{1," + str(max_chars) + r"}(?:\s|$)", cl):
                            chunks.append(piece.strip())
                        cl_buf = ""
                    else:
                        cl_buf = cl
            if cl_buf:
                chunks.append(cl_buf)
            continue
        if len(buf) + 1 + len(sent) <= max_chars:
            buf = (buf + " " + sent).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = sent
    if buf:
        chunks.append(buf)
    # Lead the FIRST chunk with the title. A standalone short title chunk renders unstably
    # (verified: clone drops 'Chương'/mangles the number); embedded at the head of a longer
    # utterance the model has enough context to read 'Chương <số>' in full.
    title_txt = spoken_title(title)
    if chunks:
        chunks[0] = title_txt + " " + chunks[0]
    else:
        chunks = [title_txt]
    return chunks


# ── SEED GHIM (30/08/2026) ────────────────────────────────────────────────────────────
# `model.generate()` KHÔNG có tham số seed — phải ghim qua torch NGAY TRƯỚC mỗi lần gọi.
# Đã đo trên máy này: cùng seed => audio trùng khít từng byte; không seed thì mỗi lần một
# khác và ĐỘ DÀI cũng đổi (70320 vs 72240 mẫu cho cùng một câu).
# Seed suy từ (thứ tự chunk, lượt thử) chứ KHÔNG phải một hằng số duy nhất: vòng retry
# verify tiêu đề dựa vào việc mỗi lượt thử ra một bản KHÁC để chọn bản đọc đủ chữ.
# Ghim chết một seed cho mọi lượt = mọi lượt giống hệt nhau = giết luôn cơ chế retry.
_SEED = int(os.environ.get("OMNIVOICE_SEED", "42"))


def _synth(model, voice, text, speed):
    """Một clip bằng profile `voice` (API công khai; seed do caller ghim)."""
    wav, _sr = ov_engine.synth(text, voice, language="Vietnamese", speed=speed, model=model)
    return wav


def _synth_seeded(model, voice, text, speed, idx, attempt=0):
    """_synth nhưng ghim seed theo (idx, attempt) -> chạy lại cùng chương ra cùng audio."""
    import torch
    s = (_SEED + idx * 97 + attempt * 100003) % (2 ** 31 - 1)
    torch.manual_seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)
    return np.asarray(_synth(model, voice, text, speed), dtype=np.float32)


# LƯU Ý: _synth_best hiện KHÔNG được gọi ở đâu (code chết). Nếu dùng lại thì phải đổi sang
# _synth_seeded với attempt=k, nếu không mọi lượt thử sẽ ra cùng một bản.
def _synth_best(model, voice, text, speed, tries):
    """Synthesize `text` `tries` times and keep the LONGEST take. The clone voice randomly
    rushes/truncates very short inputs (e.g. a title alone: 0.6s vs 1.9s vs 3.3s for the same
    line); the fullest take is the one that actually read every word."""
    best, best_len = None, -1
    for _ in range(max(1, tries)):
        a = np.asarray(_synth(model, voice, text, speed), dtype=np.float32)
        if len(a) > best_len:
            best, best_len = a, len(a)
    return best


def synth_chapter(model, voice, title, paras, speed, gap_chunk, max_chars,
                  preview_sents=0, verify_fn=None, title_retries=4):
    """Synthesize a whole chapter to one numpy waveform with sentence-level pauses.
    The title is embedded at the head of the first chunk (see make_chunks). If verify_fn is
    given, the first (title) chunk is re-rendered until ASR confirms the chapter number."""
    sr = model.sampling_rate
    sil_chunk = np.zeros(int(gap_chunk * sr), dtype=np.float32)
    chunks = make_chunks(title, paras, max_chars=max_chars, preview_sents=preview_sents)
    mnum = re.search(r"Chương\s+(\d+)", title)
    expect = mnum.group(1) if mnum else None
    pieces, cues, local = [], [], 0.0
    for idx, ch in enumerate(chunks):
        if idx == 0 and verify_fn is not None and expect:
            audio = None
            for attempt in range(title_retries):
                cand = _synth_seeded(model, voice, ch, speed, idx, attempt=attempt)
                if verify_fn(cand, expect):
                    audio = cand
                    print(f"    [synth] 1/{len(chunks)} (tiêu đề OK lần {attempt + 1}, "
                          f"{len(cand) / sr:.1f}s)")
                    break
                audio = cand  # keep last attempt as fallback
            else:
                print(f"    [synth] 1/{len(chunks)} ⚠ tiêu đề chưa verify được số {expect} "
                      f"sau {title_retries} lần — giữ bản cuối.")
        else:
            audio = _synth_seeded(model, voice, ch, speed, idx)
            print(f"    [synth] {idx + 1}/{len(chunks)}  ({len(ch)} ký tự, {len(audio) / sr:.1f}s)")
        d = len(audio) / sr
        # subtitle cues: split this chunk into sentences, share its duration by char length
        sents = [s.strip() for s in _SENT_SPLIT.split(ch) if s.strip()] or [ch]
        tot = sum(len(s) for s in sents) or 1
        t0 = local
        for sname in sents:
            seg = d * len(sname) / tot
            cues.append([round(t0, 3), round(t0 + seg, 3), sname])
            t0 += seg
        local += d + gap_chunk  # chunk audio + trailing silence
        pieces.append(audio)
        pieces.append(sil_chunk)
    wav = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
    # chuẩn âm lượng theo CẢ CHƯƠNG: đều giữa các tập, vẫn giữ to-nhỏ tự nhiên bên trong
    return ov_engine.normalize(wav), cues


def synth_plain(model, voice, text, speed, gap_chunk, max_chars):
    """Synthesize plain text (KHÔNG có tiêu đề/số chương) -> (wav, cues). Dùng cho lời kết."""
    sr = model.sampling_rate
    sil = np.zeros(int(gap_chunk * sr), dtype=np.float32)
    sents = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    chunks, buf = [], ""
    for s in sents:
        if len(buf) + 1 + len(s) <= max_chars:
            buf = (buf + " " + s).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    if not chunks:
        chunks = [text.strip()]
    pieces, cues, local = [], [], 0.0
    for _i, ch in enumerate(chunks):
        # offset 9000: lời kết KHÔNG được trùng dải seed với thân chương
        audio = _synth_seeded(model, voice, ch, speed, 9000 + _i)
        print(f"    [kết] ({len(ch)} ký tự, {len(audio) / sr:.1f}s)")
        d = len(audio) / sr
        ss = [x.strip() for x in _SENT_SPLIT.split(ch) if x.strip()] or [ch]
        tot = sum(len(x) for x in ss) or 1
        t0 = local
        for sn in ss:
            seg = d * len(sn) / tot
            cues.append([round(t0, 3), round(t0 + seg, 3), sn])
            t0 += seg
        local += d + gap_chunk
        pieces.append(audio)
        pieces.append(sil)
    wav = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
    # lời kết chuẩn CÙNG mức với thân chương, để nghe không bị hẫng ở cuối tập
    return ov_engine.normalize(wav), cues


def _srt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms >= 1000:
        ms -= 1000
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path, cues):
    """cues = list of [start_sec, end_sec, text] (global timeline)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{_srt_time(a)} --> {_srt_time(max(b, a + 0.3))}\n{txt}\n\n")


def main():
    import json
    ap = argparse.ArgumentParser(description="Crawl tamhoan.com chapters and narrate with OmniVoice.")
    ap.add_argument("--slug", default="pham-nhan-tu-tien")
    ap.add_argument("--url", default=None,
                    help="URL truyện (suy ra slug), vd https://tamhoan.com/pham-nhan-tu-tien/")
    ap.add_argument("--site", default=None, choices=("tamhoan", "truyenfull", "pntt2"),
                    help="Nguồn (mặc định: tự nhận từ --url).")
    ap.add_argument("--start-url", dest="start_url", default=None,
                    help="pntt2: URL trang chương BẮT ĐẦU (con trỏ resume; khỏi resolve).")
    ap.add_argument("--start-id", type=int, default=None, help="ID URL chương đầu (nếu đã biết).")
    ap.add_argument("--start-chapter", dest="start_chapter", type=int, default=None,
                    help="Số chương bắt đầu — tự resolve ID từ anchor.")
    ap.add_argument("--end-chapter", dest="end_chapter", type=int, default=None,
                    help="Số chương kết thúc (dùng cùng --start-chapter).")
    ap.add_argument("--chapters", type=int, default=2, help="Số chương (nếu không dùng --end-chapter).")
    ap.add_argument("--voice", default="Giọng tiên hiệp", help="Saved voice profile name.")
    ap.add_argument("--out-dir", default=None, help="Output dir (default truyen-out/<slug>).")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--gap-chapter", type=float, default=60.0, help="Silence between chapters (s).")
    ap.add_argument("--lead-in", dest="lead_in", type=float, default=0.0,
                    help="Giây nền yên ở đầu (chưa đọc/chưa hiện tiêu đề) trước khi vào chương 1.")
    ap.add_argument("--ending-text", dest="ending_text", default="",
                    help="Lời kết đọc sau chương cuối (rỗng = không đọc).")
    ap.add_argument("--ending-gap", dest="ending_gap", type=float, default=5.0,
                    help="Giây nghỉ sau chương cuối trước khi đọc lời kết.")
    ap.add_argument("--bgm", default=None, help="File nhạc nền (ghép nhẹ dưới giọng đọc).")
    ap.add_argument("--bgm-vol", dest="bgm_vol", type=float, default=0.03, help="Âm lượng nhạc nền.")
    ap.add_argument("--gap-chunk", type=float, default=0.35, help="Pause between sentences (s).")
    ap.add_argument("--max-chars", type=int, default=450)
    ap.add_argument("--polite", type=float, default=1.0, help="Delay between page fetches (s).")
    ap.add_argument("--preview-sents", type=int, default=0,
                    help="Quick test: read only the first N sentences of each chapter's body "
                         "(0 = full chapter). Bypasses the per-chapter audio cache.")
    ap.add_argument("--out-file", default=None, help="Write the combined MP3 to this exact path.")
    ap.add_argument("--verify-title", dest="verify_title", action="store_true", default=True,
                    help="ASR-check each chapter title and re-render it until the number is right.")
    ap.add_argument("--no-verify-title", dest="verify_title", action="store_false")
    ap.add_argument("--title-retries", type=int, default=4)
    args = ap.parse_args()
    preview = args.preview_sents > 0

    slug = args.slug
    site = args.site or "tamhoan"
    if args.url and not args.site:      # tự nhận nguồn từ URL truyện
        if PNTT2_HOST in args.url:
            site = "pntt2"
        elif "truyenfull" in args.url:
            site = "truyenfull"
    # BẪY SLUG: URL pntt2 có dạng /truyen/<ten-truyen>/chuong-.../ nên path-segment ĐẦU là
    # "truyen" — suy slug từ URL sẽ cho slug rác. Nguồn này LUÔN dùng --slug từ CLI/state.
    if args.url and site != "pntt2":
        ms = re.search(r"https?://[^/]+/([^/?#]+)", args.url)
        if ms:
            slug = ms.group(1)
    fetch_fn = fetch_chapter_truyenfull if site == "truyenfull" else fetch_chapter
    start_id = args.start_id
    start_url = args.start_url
    n_chapters = args.chapters
    target_end_no = None
    if args.start_chapter is not None:
        if site == "pntt2":
            pass                                     # resolve bằng URL, xử lý ngay dưới
        elif site == "truyenfull":
            start_id = args.start_chapter            # truyenfull: số chương = trực tiếp, khỏi resolve
        else:
            print(f"[resolve] chương {args.start_chapter} -> id ...")
            start_id = resolve_start_id(slug, args.start_chapter)
            print(f"[resolve] chương {args.start_chapter} = id {start_id}")
        if args.end_chapter is not None:
            n_chapters = args.end_chapter - args.start_chapter + 1
            target_end_no = args.end_chapter   # DỪNG theo SỐ chương -> kết đúng mốc, bền với skip/gộp
    if site == "pntt2":
        if not start_url:
            if args.start_chapter is None:
                ap.error("pntt2: cần --start-url hoặc --start-chapter")
            print(f"[resolve] chương {args.start_chapter} -> URL (mục lục trong trang) ...")
            start_url = resolve_url_pntt2(args.url, args.start_chapter)
            print(f"[resolve] chương {args.start_chapter} = {start_url}")
    elif start_id is None:
        ap.error("cần --start-id hoặc --start-chapter")

    out_dir = args.out_dir or os.path.join(ENGINE, "truyen-out", slug)
    cache_dir = os.path.join(out_dir, "cache")
    os.makedirs(out_dir, exist_ok=True)

    next_url, source_exhausted = None, False
    if site == "pntt2":
        print(f"=== CRAWL tối đa {n_chapters} chương từ {start_url} ({slug} · pntt2) ===")
        chapters, next_url, source_exhausted = crawl_pntt2(
            start_url, n_chapters, cache_dir, target_end_no=target_end_no,
            polite=max(args.polite, 2.0))
    else:
        print(f"=== CRAWL {n_chapters} chương từ {start_id} ({slug} · {site}) ===")
        chapters = crawl(slug, start_id, n_chapters, cache_dir, polite=args.polite, fetch_fn=fetch_fn, target_end_no=target_end_no)
    if not chapters:
        # crawl bỏ qua được trang không đánh số -> có thể về rỗng. Hỏng RÕ ở đây, đừng để
        # tầng dựng audio nổ mơ hồ vì danh sách chương trống.
        raise SystemExit(f"Không crawl được chương nào từ {start_url or f'id {start_id}'} ({slug}) — "
                         f"nhiều khả năng đã hết chương đánh số trên nguồn (ngoại truyện?). "
                         f"Kiểm tra 'last_end'.")

    print(f"=== LOAD model + voice profile '{args.voice}' ===")
    model = ov_engine.load()
    sr = model.sampling_rate

    verify_fn = None
    if args.verify_title:
        print("[verify] nạp Whisper (small, cpu) để kiểm tiêu đề ...")
        from faster_whisper import WhisperModel
        _asr = WhisperModel("small", device="cpu", compute_type="int8")
        _vtmp = os.path.join(out_dir, "_verify_title.wav")

        def verify_fn(audio, expect):
            sf.write(_vtmp, audio, sr)
            segs, _ = _asr.transcribe(_vtmp, language="vi", beam_size=5)
            digits = re.sub(r"\D", "", "".join(s.text for s in segs))
            return expect in digits
    sil_chapter = np.zeros(int(args.gap_chapter * sr), dtype=np.float32)

    combined, manifest, all_cues, cur = [], [], [], 0.0
    for ci, ch in enumerate(chapters):
        per_wav = os.path.join(out_dir, f"Chuong_{ch['no']}.wav")
        per_cue = os.path.join(out_dir, f"Chuong_{ch['no']}.cues.json")
        cues = None
        if not preview and os.path.isfile(per_wav):  # resume: reuse already-rendered chapter audio
            wav, _ = sf.read(per_wav, dtype="float32")
            if os.path.isfile(per_cue):
                cues = json.load(open(per_cue, encoding="utf-8"))
            print(f"[skip] Chương {ch['no']} đã render -> {per_wav}"
                  f"{'' if cues else '  (chưa có cues → không phụ đề chương này)'}")
        else:
            tag = f" (preview {args.preview_sents} câu đầu)" if preview else ""
            print(f"=== ĐỌC Chương {ch['no']}: {ch['title']}{tag} ===")
            wav, cues = synth_chapter(model, args.voice, ch["title"], ch["paras"],
                                      args.speed, args.gap_chunk, args.max_chars,
                                      preview_sents=args.preview_sents,
                                      verify_fn=verify_fn, title_retries=args.title_retries)
            if not preview:  # preview never writes per-chapter files (no split, no cache clobber)
                # NGUYÊN TỬ: có `Chuong_<n>.wav` = chương đã xong — resume (story/resume_once.py)
                # bỏ qua đúng chương đó. Bị giết giữa lúc ghi thì file cụt mang tên thật sẽ được
                # dùng lại như chương hoàn chỉnh. Ghi ra tên tạm rồi `os.replace` (cues trước, wav
                # sau cùng — wav là dấu "xong").
                tmp_cue, tmp_wav = per_cue + ".tmp", per_wav[:-4] + ".tmp.wav"
                with open(tmp_cue, "w", encoding="utf-8", newline="\n") as _fc:
                    json.dump(cues, _fc, ensure_ascii=False)
                os.replace(tmp_cue, per_cue)
                ov_engine.save(wav, tmp_wav, sr)
                os.replace(tmp_wav, per_wav)
                print(f"[ok] Chương {ch['no']} -> {per_wav} ({len(wav) / sr / 60:.1f} phút)")
        wav = np.asarray(wav, dtype=np.float32)
        dur = len(wav) / sr
        nm = re.match(r"\s*Chương\s+\d+\s*[:\.\-]?\s*(.*)$", ch["title"])
        manifest.append({"num": ch["no"], "title": ch["title"],
                         "name": (nm.group(1).strip() if nm else ch["title"]),
                         "start": round(cur, 3), "dur": round(dur, 3)})
        if cues:  # shift chapter-local cue times onto the global timeline
            for a, b, txt in cues:
                all_cues.append([round(cur + a, 3), round(cur + b, 3), txt])
        combined.append(wav)
        cur += dur
        if ci != len(chapters) - 1:
            combined.append(sil_chapter)  # nghỉ giữa các chương (gap-chapter)
            cur += args.gap_chapter

    # ---- LỜI KẾT: sau chương cuối, nghỉ ending_gap rồi đọc lời kết (kèm phụ đề) ----
    if args.ending_text and not preview:
        egap = max(0.0, args.ending_gap)
        if egap > 0:
            combined.append(np.zeros(int(egap * sr), dtype=np.float32))
            cur += egap
        print(f"=== ĐỌC LỜI KẾT ({len(args.ending_text)} ký tự) ===")
        ewav, ecues = synth_plain(model, args.voice, args.ending_text,
                                  args.speed, args.gap_chunk, args.max_chars)
        for a, b, txt in ecues:
            all_cues.append([round(cur + a, 3), round(cur + b, 3), txt])
        combined.append(np.asarray(ewav, dtype=np.float32))
        cur += len(ewav) / sr

    first, last = chapters[0]["no"], chapters[-1]["no"]
    if args.out_file:
        out_mp3 = os.path.abspath(args.out_file)
    else:
        stem = f"Preview_{first}-{last}" if preview else f"PhamNhanTuTien_{first}-{last}"
        out_mp3 = os.path.join(out_dir, stem + ".mp3")
    lead = max(0.0, args.lead_in)
    if lead > 0:  # đầu video: lead giây nền yên (chưa đọc/chưa hiện tiêu đề), dời mọi mốc +lead
        combined.insert(0, np.zeros(int(lead * sr), dtype=np.float32))
        for ch in manifest:
            ch["start"] = round(ch["start"] + lead, 3)
        all_cues = [[round(a + lead, 3), round(b + lead, 3), t] for a, b, t in all_cues]
        cur += lead
    full = np.concatenate(combined)
    ov_engine.save(full, out_mp3, sr)
    if args.bgm and os.path.isfile(args.bgm):
        _add_bgm(out_mp3, args.bgm, args.bgm_vol, cur)
    elif args.bgm:
        print(f"[bgm] WARN: không thấy file nhạc {args.bgm} — bỏ qua.")
    srt_path = out_mp3 + ".srt"
    write_srt(srt_path, all_cues)
    man_path = out_mp3 + ".manifest.json"
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"audio": out_mp3, "srt": srt_path, "sr": sr, "voice_dur": round(cur, 3),
                   "gap_chapter": args.gap_chapter, "chapters": manifest,
                   # Con trỏ resume + cờ hết truyện (chỉ có nghĩa với nguồn lật-theo-nút).
                   # Site khác: None/False -> daily_truyen bỏ qua, schema cũ không đổi.
                   "next_url": next_url, "source_exhausted": bool(source_exhausted)}, f,
                  ensure_ascii=False, indent=2)
    print(f"\n=== DONE === {first}-{last}: {len(full) / sr / 60:.1f} phút -> {out_mp3}")
    print(f"manifest -> {man_path}\nsrt -> {srt_path} ({len(all_cues)} cues)")


if __name__ == "__main__":
    raise SystemExit(main())
