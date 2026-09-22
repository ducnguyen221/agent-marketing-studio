# -*- coding: utf-8 -*-
r"""Cổng chống rò rỉ danh tính máy/người vào repo PUBLIC.

Phân biệt hai thứ hay bị gộp làm một:

1. **Danh tính máy & người** — đường dẫn thư mục nhà của người dùng, email cá nhân, token.
   Đây là rò rỉ THẬT, và cổng này chặn CỨNG trên toàn cây git-tracked.
   Lịch sử: 14 file từng mang đường dẫn home của tác giả sau đợt cutover 04/09, lọt qua
   vì lệnh kiểm lúc đó nhét thẳng đường dẫn Windows vào regex — dấu gạch chéo ngược đứng
   trước chữ hoa bị hiểu là escape, nên pattern không khớp chữ literal và trả về "sạch".
   Âm tính giả. (Cố ý KHÔNG viết lại đường dẫn đó ở đây: file này cũng bị chính nó quét.)
   ⇒ Ở đây dùng so khớp CHUỖI THẲNG (`in`), không dùng regex, để không tái lập lỗi đó.

2. **Tên thương hiệu / tổ chức** của chủ repo — có mặt hợp lệ ở nhiều nơi: `content/` là
   instance mẫu cố ý đưa vào git, `output_styles/*.md` là hồ sơ giọng của chính thương
   hiệu đó. Cổng này KHÔNG chặn chúng trên toàn cây; chỉ giữ sạch `fixtures/`, nơi số liệu
   phải trung tính để dùng làm mốc đối chứng.
3. **Cổng ĐẾM** (cuối file) — bắc cầu giữa hai loại trên. Nó quét CẢ CÂY và miễn trừ
   **theo số đếm chính xác**, không miễn cả file: mỗi mục ghi số lần kỳ vọng hôm nay.
   Nhét thêm một chỗ vào file đã được miễn cũng đỏ. Cùng khuôn với cổng của
   `agent-voice-studio`/`agent-video-studio` để ba repo đọc như nhau.
"""
import re
import subprocess
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# So khớp chuỗi thẳng — KHÔNG regex (xem docstring).
# Backslash dựng bằng chr(92) thay vì viết literal: chuỗi này đi qua nhiều tầng
# (heredoc shell -> file -> parser Python), mỗi tầng ăn một lớp escape khác nhau.
# Đây không phải cẩn thận thừa: đúng lỗi đó vừa làm hỏng dòng $ATLAS trong
# publish-tobi.ps1 ( thành ký tự BEL) và làm file này không parse được 2 lần.
_BS = chr(92)
CAM_TUYET_DOI = [
    "C:" + _BS + "Users" + _BS,   # bất kỳ đường home Windows nào, không riêng của ai
    "/" + "home" + "/",           # tương đương trên Linux
    "/" + "Users" + "/",          # tương đương trên macOS — máy ĐÍCH của cuộc di trú này
    # Ba chuoi tren deu DUNG TU MANH, khong viet literal: file nay nam trong cay
    # git-tracked nen chinh no bi quet. Viet literal = cong luon do vi chinh no.
    # Luat cua macOS vang mat toi tan 20/09 (REVIEW-P2 N10): ca pha nay la de chay tren
    # macOS va repo la PUBLIC da push, nen lo do se mo ra dung luc bat dau dung. Test nao
    # can mot duong nha macOS GIA lam du lieu thi cung ghep tu manh nhu o day.
]
# Email cá nhân: dùng MẪU chứ không viết literal. Bản trước ghi thẳng địa chỉ vào đây rồi
# tự miễn trừ chính file này — tức cổng mang sẵn thứ nó đi tìm, và không bao giờ thấy.
MAU_EMAIL = re.compile(r"[\w.+-]+@(?:gmail|outlook|hotmail|yahoo|icloud)\.com", re.I)
# Token: cái này buộc phải là regex vì bắt theo hình dạng.
MAU_TOKEN = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{24,}"),
    re.compile(r"(?:AIza)[A-Za-z0-9_\-]{30,}"),
    re.compile(r"\bEAA[A-Za-z0-9]{40,}"),          # Facebook Graph token
]
NHI_PHAN = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".mp3", ".mp4", ".woff", ".woff2", ".pdf"}


def _tracked() -> list[Path]:
    ra = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / p for p in ra.stdout.decode().split("\0") if p]


def _doc(p: Path) -> str:
    """Trả về nội dung đọc được. .xlsx là zip -> phải mở ra đọc XML bên trong."""
    if p.suffix.lower() == ".xlsx":
        try:
            with zipfile.ZipFile(p) as z:
                return "\n".join(
                    z.read(n).decode("utf-8", "ignore")
                    for n in z.namelist() if n.endswith((".xml", ".rels"))
                )
        except zipfile.BadZipFile:
            return ""
    if p.suffix.lower() in NHI_PHAN:
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


FILES = [(p, _doc(p)) for p in _tracked()]


def test_co_file_de_quet():
    """Cổng quét 0 file là cổng luôn xanh — vô dụng. Chặn ngay tại đây."""
    assert len(FILES) > 20, f"chỉ thấy {len(FILES)} file git-tracked, nghi lỗi môi trường"
    assert any(p.suffix == ".xlsx" for p, _ in FILES), "phải có ít nhất 1 .xlsx để chứng minh nhánh đọc zip có chạy"


@pytest.mark.parametrize("campaign", CAM_TUYET_DOI)
def test_khong_ro_ri_danh_tinh(campaign):
    dinh = []
    for p, text in FILES:
        if campaign in text:
            row = text[:text.index(campaign)].count("\n") + 1
            dinh.append(f"{p.relative_to(ROOT).as_posix()}:{row}")
    assert not dinh, f"chuỗi {campaign!r} xuất hiện trong repo public tại: {dinh[:12]}"


def test_khong_lo_token():
    dinh = []
    for p, text in FILES:
        for mau in MAU_TOKEN + [MAU_EMAIL]:
            if mau.search(text):
                dinh.append(f"{p.relative_to(ROOT).as_posix()} ({mau.pattern[:18]}…)")
    assert not dinh, f"có chuỗi hình dạng token: {dinh}"


def test_fixtures_trung_tinh():
    """`fixtures/` là mốc đối chứng — số liệu phải dùng được mà không lộ ai là ai."""
    name = re.compile(r"KPIM|COMPA|Tobi", re.I)
    dinh = [p.relative_to(ROOT).as_posix()
            for p, text in FILES
            if p.parts[len(ROOT.parts):][:1] == ("fixtures",) and name.search(text)]
    assert not dinh, f"fixtures/ phải trung tính, còn tên tổ chức ở: {dinh}"


def test_prompt_MAU_khong_khoa_vao_mot_nguoi():
    """Repo public. Prompt mở đầu bằng tên thật thì ai clone về cũng viết bằng danh tính
    của người khác — template hỏng, không phải secret rò rỉ.

    Danh tính phải là chỗ trống lấy từ `brand.md` của kênh, đúng hợp đồng mà `new_post.py`
    đã ghi. Tên ở đây dựng bằng mã ký tự để CHÍNH FILE TEST không chứa thứ nó đi săn —
    một cổng tự miễn trừ mình là cổng vô dụng.
    """
    import unicodedata
    campaign = [unicodedata.normalize("NFC", x) for x in
           ("Nguy" + chr(0x1EC5) + "n Quang " + chr(0x110) + chr(0x1EE9) + "c",
            "COMPA Class", "T" + "obi", "KP" + "IM")]
    folder = ROOT / ".agents" / "prompts"
    assert folder.is_dir(), "không thấy .agents/prompts — đường dẫn đổi?"

    dinh = []
    for f in sorted(folder.glob("*.txt")):
        t = unicodedata.normalize("NFC", f.read_text(encoding="utf-8"))
        for x in campaign:
            if x in t:
                dinh.append(f"{f.name} còn {x!r}")
    assert not dinh, ("prompt mẫu bị khoá vào một người/tổ chức:\n  " + "\n  ".join(dinh))


def test_prompt_MAU_co_du_cho_trong_va_co_dan_cach_dien():
    """Bỏ tên mà không để chỗ trống thì agent sẽ tự bịa một cái tên."""
    folder = ROOT / ".agents" / "prompts"
    for f in sorted(folder.glob("*.txt")):
        t = f.read_text(encoding="utf-8")
        if "{{AUTHOR}}" in t or "{{CHANNEL}}" in t:
            assert "ĐIỀN TRƯỚC KHI DÙNG" in t, \
                f"{f.name} có chỗ trống danh tính nhưng không dặn cách điền"
            assert "brand.md" in t, f"{f.name} không chỉ ra nguồn của danh tính"


def test_TEMPLATE_khong_mang_nhan_dien_that():
    """`templates/station/` là khuôn mọi kênh mọc ra từ đó — nó phải TRUNG TÍNH.

    Cạm bẫy đã suýt trả giá (07/09/2026): bốn script cấp kênh (`build-index.ps1`,
    `send_newsletter.py`, `build_yt_desc.py`, `subscribe.gs`) được chưng cất từ bản đang
    chạy thật, và mang theo nguyên tên miền, email, tên người và **id Meta Pixel** vào một
    repo MIT công khai. Hai hậu quả khác nhau, đều nặng:

    · Rò rỉ: email và id pixel là dữ liệu thật, push lên là công khai vĩnh viễn.
    · Khuôn hỏng: ai clone về cũng xuất bản dưới danh nghĩa người khác và gửi dữ liệu
      người đọc tới một tài khoản quảng cáo lạ — mà không hề biết.

    Cổng `test_prompt_MAU_khong_khoa_vao_mot_nguoi` ở trên chỉ soi `.agents/prompts/`,
    nên nó không bắt được. Cổng này soi cả cây khuôn.

    Chuỗi cấm dựng bằng mã ký tự để CHÍNH FILE TEST không chứa thứ nó đi săn.
    """
    import re
    import unicodedata

    tm = ROOT / "templates"
    assert tm.is_dir(), "không thấy templates/ — đường dẫn đổi?"

    # Tên miền, email, tên người, id pixel của kênh đầu tiên.
    campaign = [
        "ducng" + "uyen.vn", "ducng" + "uyen221", "ducng" + "uyen.ams",
        "Duc Ngu" + "yen", "17170417" + "32866196",
        "C:" + chr(92) + "Users" + chr(92) + "Duc" + "Nguyen",
    ]
    campaign = [unicodedata.normalize("NFC", x) for x in campaign]
    # Tên kênh thật: bắt cả "AI News" lẫn "Data News" mà không đụng chữ "news" chung.
    mau_kenh = re.compile(r"\b(AI|Data)\s+News\b")

    dinh = []
    for f in sorted(tm.rglob("*")):
        if not f.is_file() or f.suffix.lower() in {".xlsx", ".png", ".jpg", ".svg"}:
            continue
        try:
            t = unicodedata.normalize("NFC", f.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        name = f.relative_to(ROOT).as_posix()
        for x in campaign:
            if x in t:
                dinh.append(f"{name} còn {x!r}")
        m = mau_kenh.search(t)
        if m:
            dinh.append(f"{name} còn tên kênh thật {m.group()!r}")

    assert not dinh, (
        "khuôn trong templates/ mang nhận diện thật — sửa thành khoá cấu hình "
        "hoặc chỗ trống:\n  " + "\n  ".join(dinh))


# ══════════════════════════════════════════════════════════════════════════════
# Cổng ĐẾM — quét cả cây, miễn trừ theo SỐ ĐẾM CHÍNH XÁC
#
# Vì sao thêm cổng thứ ba khi đã có hai cổng trên: hai cổng kia hoặc chặn cứng một
# chuỗi trên toàn cây (không chừa chỗ cho LICENSE, CODEOWNERS, trang giới thiệu repo),
# hoặc chỉ soi đúng một thư mục (`templates/`, `fixtures/`). Giữa hai thái cực đó là
# phần lớn repo — và `scripts/` nằm đúng ở giữa: nó là MÁY mà ai clone về cũng chạy,
# nên nó phải sạch tuyệt đối, trong khi `docs/index.html` là trang giới thiệu của chính
# chủ repo, mang tên miền thật là đúng chức năng.
#
# Miễn trừ theo SỐ, không theo file: thêm một chỗ vào file đã miễn cũng đỏ. Sửa nội
# dung làm số đổi thì phải sửa con số ở đây — người sửa buộc phải nhìn thấy mình đang
# đổi gì. Mục miễn trừ nào không còn khớp gì thì `test_mien_tru_khong_han` bắt gỡ.
# ══════════════════════════════════════════════════════════════════════════════
SELF = "tests/test_no_identity_leak.py"


def _s(*ma: int) -> str:
    return "".join(map(chr, ma))


# Mọi chuỗi cấm dựng bằng mã ký tự: file này bị chính nó quét ở hai cổng trên, và một
# cổng mang sẵn thứ nó đi tìm là cổng vô dụng.
_TEN_TG = _s(100, 117, 99) + _s(110, 103, 117, 121, 101, 110)          # tài khoản tác giả
_TEN_VN = (_s(0x4E, 0x67, 0x75, 0x79, 0x1EC5, 0x6E) + " " + _s(0x51, 0x75, 0x61, 0x6E, 0x67)
           + " " + _s(0x110, 0x1EE9, 0x63))                            # tên đầy đủ, có dấu
_TEN_ASCII = _s(68, 117, 99) + r"[\s-]+" + _s(78, 103, 117, 121, 101, 110)
_PIXEL = _s(49, 55, 49, 55, 48, 52, 49, 55) + _s(51, 50, 56, 54, 54, 49, 57, 54)
_TO_CHUC = (_s(75, 80, 73, 77), _s(67, 79, 77, 80, 65), _s(84, 111, 98, 105))
# Đường thư mục instance mẫu — cũng dựng bằng mã ký tự, vì chính tên thư mục mang tên
# tổ chức và file này nằm trong vùng bị quét.
_TC = _TO_CHUC[2].upper()
_CT = "content/" + _TO_CHUC[0] + "/02_campaigns/01_" + _TO_CHUC[2] + "_Posts"

MAU_DANH_TINH = {
    "ten-mien":  re.escape(_TEN_TG + ".vn"),
    "handle":    re.escape(_TEN_TG + "221"),
    "ten-nguoi": "(?:" + re.escape(_TEN_VN) + "|" + _TEN_ASCII + ")",
    "pixel":     _PIXEL,
    "to-chuc":   r"\b(?:" + "|".join(_TO_CHUC) + r")\b",
    "kenh-that": r"\b(?:AI|Data)\s+News\b",
}

# Khoá CỨNG: áp cho cả cây. Đây là danh tính của MỘT người / MỘT máy — tên miền, tài
# khoản, tên thật, id pixel quảng cáo. Ở đâu cũng là rò rỉ, trừ những chỗ ghi công đã
# liệt kê trong MIEN_TRU.
KHOA_CUNG = ("ten-mien", "handle", "ten-nguoi", "pixel")

# Vùng MÁY: phần repo mà người clone đem đi chạy. Ở đây cấm thêm cả tên tổ chức và tên
# kênh thật — chúng không phải secret, nhưng để trong máy thì khuôn hỏng: người khác
# xuất bản dưới thương hiệu của chủ repo mà không hề biết.
VUNG_MAY = ("scripts/", "templates/", "fixtures/", "examples/", ".agents/", "tests/")

# (đường file, khoá) → số lần được phép. Mỗi dòng phải có LÝ DO.
MIEN_TRU = {
    # Ghi công tác giả + định tuyến review trên GitHub: đúng chức năng của hai file này.
    ("LICENSE", "ten-nguoi"): 1,
    (".github/CODEOWNERS", "handle"): 8,
    # Trang giới thiệu repo (GitHub Pages của chính chủ) + ảnh og của nó.
    ("docs/index.html", "ten-mien"): 9,
    ("docs/index.html", "handle"): 8,
    ("docs/index.html", "ten-nguoi"): 1,
    ("docs/og-image.svg", "ten-mien"): 1,
    # `content/` là instance mẫu CỐ Ý đưa vào git (xem .gitignore dòng 1): một bộ nội
    # dung thật để người đọc thấy khuôn được điền ra sao. Nó là DỮ LIỆU, không phải máy.
    (_CT + "/01_" + _TO_CHUC[2] + "_Posts.md", "ten-mien"): 1,
    (_CT + "/assets/" + _TC + "-001_ai-agent-la-gi/content.md", "ten-mien"): 1,
    (_CT + "/campaign_meta.json", "ten-mien"): 1,
    (_CT + "/campaign_meta.json", "ten-nguoi"): 1,
    (_CT + "/01_" + _TO_CHUC[2] + "_Posts.xlsx", "ten-nguoi"): 2,
    ("content/" + _TO_CHUC[0] + "/campaigns.xlsx", "ten-mien"): 1,
    ("content/" + _TO_CHUC[0] + "/campaigns.xlsx", "ten-nguoi"): 1,
    # Hồ sơ giọng của chính chủ, và các file trỏ tới TÊN FILE đó. Đổi tên file hồ sơ
    # giọng là việc của đợt docs (P2-G5): nó kéo theo README + 5 chỗ tham chiếu.
    ("examples/example-studio/channel.yml", "to-chuc"): 1,
    (".agents/roles/content-strategist.md", "to-chuc"): 1,
    (".agents/roles/creative-producer.md", "to-chuc"): 1,
    (".agents/roles/qa-reviewer.md", "to-chuc"): 1,
    (".agents/skills/content-production/SKILL.md", "to-chuc"): 1,
    (".agents/skills/hook-writer/SKILL.md", "to-chuc"): 1,
}


def _ap_dung(rel: str, khoa: str) -> bool:
    return khoa in KHOA_CUNG or rel.startswith(VUNG_MAY)


def dem_danh_tinh() -> Counter:
    hits: Counter = Counter()
    for p, text in FILES:
        rel = p.relative_to(ROOT).as_posix()
        if rel == SELF or not text:
            continue
        t = unicodedata.normalize("NFC", text)
        for khoa, mau in MAU_DANH_TINH.items():
            if not _ap_dung(rel, khoa):
                continue
            n = len(re.findall(mau, t, flags=re.IGNORECASE))
            if n:
                hits[(rel, khoa)] = n
    return hits


def test_dem_danh_tinh_khong_vuot_mien_tru():
    vuot = {k: n for k, n in dem_danh_tinh().items() if n > MIEN_TRU.get(k, 0)}
    assert vuot == {}, "rò danh tính / vượt số miễn trừ:\n  " + "\n  ".join(
        f"{f} [{k}] {n} > {MIEN_TRU.get((f, k), 0)}" for (f, k), n in sorted(vuot.items()))


def test_mien_tru_khong_han():
    """Mục miễn trừ không còn khớp gì thì phải gỡ — cửa mở sẵn là cửa sẽ bị dùng lại."""
    hits = dem_danh_tinh()
    han = [k for k in MIEN_TRU if k not in hits and (ROOT / k[0]).exists()]
    assert han == [], f"mục MIEN_TRU không còn khớp gì, gỡ đi: {han}"


def test_mau_bat_dung_muc_tieu():
    """Đột biến: mỗi mẫu phải bắt được chuỗi nó nhắm tới, và KHÔNG bắt chuỗi lành."""
    mau_thu = {
        "ten-mien":  "https://" + _TEN_TG + ".vn/atlas",
        "handle":    _TEN_TG + "221.github.io",
        "ten-nguoi": "tác giả " + _TEN_VN + " viết",
        "pixel":     "fbq('init', '" + _PIXEL + "')",
        "to-chuc":   "đăng ở " + _TO_CHUC[1] + " Class",
        "kenh-that": "kênh AI News hằng tuần",
    }
    for khoa, mau in mau_thu.items():
        assert re.search(MAU_DANH_TINH[khoa], mau, flags=re.IGNORECASE), khoa
    # Ranh giới: không bắt chữ lành đang có sẵn trong repo.
    assert not re.search(MAU_DANH_TINH["to-chuc"], "x.localeCompare(y)", flags=re.IGNORECASE)
    assert not re.search(MAU_DANH_TINH["ten-nguoi"], _TEN_TG, flags=re.IGNORECASE)
    assert not re.search(MAU_DANH_TINH["kenh-that"], "news/ai", flags=re.IGNORECASE)


def test_vung_may_duoc_quet_that():
    """Cổng-của-cổng: không file nào thuộc vùng máy được quét thì cổng luôn xanh."""
    trong_vung = [p.relative_to(ROOT).as_posix() for p, t in FILES
                  if t and p.relative_to(ROOT).as_posix().startswith(VUNG_MAY)]
    assert len(trong_vung) > 50, f"chỉ thấy {len(trong_vung)} file trong vùng máy"
    for tien_to in VUNG_MAY:
        assert any(r.startswith(tien_to) for r in trong_vung), f"không quét gì dưới {tien_to}"
