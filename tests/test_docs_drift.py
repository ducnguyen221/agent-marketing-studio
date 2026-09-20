# -*- coding: utf-8 -*-
"""Cổng chống TÀI LIỆU TRÔI — chặn luật cũ và tên cũ hồi sinh.

Bài học ngày 04/09/2026: đợt đổi luật link Facebook sửa 7 file, nhưng
`output_styles/multichannel-style.md` có **hai** chỗ nói về link — mục "Facebook" (đã sửa)
và mục "Quy tắc format FB chung" (bị bỏ sót). Kết quả: một file mang hai luật trái nhau,
và agent đọc trúng dòng nào thì theo dòng đó.

Cổng này quét toàn cây git-tracked tìm những chuỗi CHỈ CÓ THỂ đến từ mô hình đã bỏ.
Nó không thay người đọc — nó chỉ đảm bảo cái đã bỏ thì không quay lại một cách im lặng.

So khớp bằng CHUỖI THẲNG, không regex — cùng lý do với test_no_identity_leak: regex nuốt escape và
cho âm tính giả.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Chuỗi cấm -> vì sao cấm. Chỉ liệt kê thứ KHÔNG CÒN ĐÚNG, không liệt kê thứ chỉ cũ.
CAM = {
    "Link đặt ĐẦU bài": "luật link Facebook đã đảo 04/09: thân bài 0 URL, link ở comment đầu",
    "post:youtube_video": "neo đã đổi thành post:youtube_desc (gen_article chỉ hiểu tên mới)",
    "fb_image.png": "đã gộp thành facebook/infographic.png — xem post_paths.LAYOUT",
    # Danh sách này cấm TÊN script đã bỏ. Tên nào còn xuất hiện hợp lệ trong khối cảnh
    # báo đầu file .ps1 thì không được cho vào đây — cấm nó là bắt oan chính lời cảnh báo.
    # (đang giải thích vì sao chúng chưa chạy được). Cấm một cái tên vì nó cũ là sai —
    # chỉ cấm thứ còn tự xưng là LUẬT HIỆN HÀNH.
    "2 cổng duyệt": "đường ống có BA cổng (approval_gate.GATES); Cổng 3 bật khi bảng Content "
                    "có cột g3",
    "-Buoc ": "tham số của run-blog-campaign.ps1 là -Step (xem ValidateSet)",
    "~/.news": "engine là <trạm>/engine; repo public không trỏ vào bố cục của một máy",
    "~/.tts": "trạm giọng phân giải qua OMNIVOICE_DIR, không đường cứng",
    "news-media": "thư mục media của engine cũ, không đi theo engine mới",
    "soan ─": "bước `soan` đã đổi tên thành `write` (xem migrate_names.py)",
    # Chỉ đạo 21/09/2026 — phân tầng năng lực. `doctor` KHÔNG còn trả mã 3 vì thiếu trạm
    # giọng/video; mã 3 chuyển về đúng chỗ chạm (`voice.py` / `video.py`). Câu cũ dạy
    # người đọc rằng bản cài của họ hỏng khi họ mới chỉ chưa cần tới audio.
    "Mã **3** = còn thiếu trạm": "thiếu trạm giọng/video nay là mã 0 ở `doctor` — nó chỉ "
                                 "đỏ khi LÕI (viết bài + đăng) hỏng",
    "`dang` là": "tên cũ của build-page nay là `publish` (campaign_step.STEPS)",
    "TG_BOT_TOKEN=": "token Telegram CHỈ nằm trong file cấu hình; biến TG_CONFIG giữ đường dẫn",
    # KHÔNG cấm cái TÊN `.env`. Cổng từng cấm 6 cách nói về `.env` với lý do "không script
    # nào nạp .env" — đúng hôm nay, nhưng F17 (plan v3.2, P2-T01/T03) biến `<repo>/.env`
    # thành chỗ giữ cấu hình bí mật của chế độ cài `embedded`, nên tài liệu P2 BẮT BUỘC phải
    # nói về nó. Cái vẫn sai — và sai cả sau F17 — là token THÔ nằm trong `.env`; việc đó do
    # `test_khong_noi_TOKEN_THO_nam_trong_env` canh, chặt hơn và không chặn nhầm F17.
}

# Nơi được phép nhắc tên cũ: chỗ GIẢI THÍCH lịch sử, và chính file này.
MIEN_TRU = ("tests/test_docs_drift.py", "fixtures/baseline/")

# Miễn trừ RIÊNG từng chuỗi. Docstring của test kể lại lỗi đã trả giá bằng đúng tên bước lúc
# đó — đó là lịch sử, không phải luật hiện hành.
MIEN_TRU_RIENG = {
    "soan ─": ("tests/",),
    "`dang` là": ("tests/",),
}

# File LUẬT của repo (AGENTS.md) chỉ sửa khi người duyệt gật — agent không tự sửa. Chuỗi cũ
# còn ở đó thì CHỜ ở đây, và `test_chuoi_cua_mo_hinh_da_bo` bỏ qua đúng file đó. Rỗng =
# không còn gì chờ: AGENTS.md chịu cổng chính như mọi file khác (C2 duyệt 21/09/2026).
CHO_DUYET_FILE_LUAT = {}

NHI_PHAN = {".png", ".jpg", ".jpeg", ".mp3", ".mp4", ".xlsx", ".ico", ".woff", ".woff2"}


def _tracked():
    ra = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    for name in ra.stdout.decode().split("\0"):
        if not name or name.startswith(MIEN_TRU) or Path(name).suffix.lower() in NHI_PHAN:
            continue
        try:
            yield name, (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


FILES = list(_tracked())


def test_co_file_de_quet():
    assert len(FILES) > 50, f"chỉ thấy {len(FILES)} file — nghi lỗi môi trường, cổng sẽ luôn xanh"


@pytest.mark.parametrize("chuoi,why", list(CAM.items()))
def test_chuoi_cua_mo_hinh_da_bo(chuoi, why):
    bo_qua = MIEN_TRU_RIENG.get(chuoi, ()) + CHO_DUYET_FILE_LUAT.get(chuoi, ())
    dinh = []
    for name, text in FILES:
        if bo_qua and name.startswith(bo_qua):
            continue
        if chuoi in text:
            row = text[:text.index(chuoi)].count("\n") + 1
            dinh.append(f"{name}:{row}")
    assert not dinh, f"{chuoi!r} — {why}. Còn ở: {dinh[:10]}"


# ── `.env`: cấm MÔ HÌNH cũ, không cấm cái TÊN ───────────────────────────────
# Cổng từng cấm mọi cách nói về `.env` với lý do "không script nào nạp .env". Đúng hôm nay,
# nhưng nó sẽ chặn chính thứ sắp tới: F17 (plan v3.2, tác vụ P2-T01/T03) đặt `<repo>/.env`
# làm chỗ giữ cấu hình bí mật của chế độ cài `embedded` — `.gitignore` khoá nó, `doctor`
# kiểm quyền 600, `backup` mặc định không kèm nó — nên tài liệu P2 BẮT BUỘC phải mô tả nó.
# Một cổng chặn đúng việc sắp phải làm thì người sau sẽ gỡ cả cổng, không gỡ riêng dòng sai.
#
# Cái vẫn SAI, và sai kể cả sau F17: token THÔ nằm trong `.env`. Thiết kế của repo không đổi
# — biến giữ ĐƯỜNG DẪN, secret nằm trong file được trỏ tới (token Telegram từng lộ đúng vì
# mô hình cũ, 08/09). Hai test dưới giữ cả hai vế: chặn cái sai, và KHÔNG chặn cái đúng.

# Chữ chỉ SECRET THÔ. Cố ý KHÔNG có "secret" / "cấu hình": ở chế độ `embedded`, `.env` CHÍNH
# LÀ chỗ giữ cấu hình bí mật, nói về nó là hợp lệ. Cái sai là để GIÁ TRỊ token nằm đó.
TU_TOKEN = ("token", "mật khẩu", "password", "client_secret", "refresh_token", "private_key")
# Câu nói về ĐƯỜNG DẪN tới file token (`YT_TOKEN_PATH`, "biến trỏ tới file token") là đúng
# thiết kế ba tầng, không phải mô hình cũ — trừ ra, nếu không cổng báo oan chính luật hiện hành.
MIEN_TRU_DUONG_DAN = ("_path", "đường dẫn", "trỏ tới", "trỏ vào", "tên biến")
# Phải có LIÊN KẾT chứa-đựng giữa token và `.env`. Thiếu vế này thì một dòng liệt kê
# "Token, `.env*`, `*.json` — đều bị gitignore" bị báo oan, và cổng báo oan là cổng bị tắt.
# `\b` để "ghi" không khớp trong "nghi", "đọc" không khớp trong "đọc-ghi" ghép từ khác.
_RE_LIEN_KET = re.compile(
    r"\b(?:nằm|đặt|dán|lưu|ghi|khai|chứa|đọc|điền)\b|(?:trong|ở|vào|từ|qua)\s+`?\.env", re.I)


def _token_tho_trong_env(dong: str) -> bool:
    if ".env" not in dong:
        return False
    t = dong.lower()
    if not any(w in t for w in TU_TOKEN):
        return False
    if any(w in t for w in MIEN_TRU_DUONG_DAN):
        return False
    return bool(_RE_LIEN_KET.search(t))


def test_khong_noi_TOKEN_THO_nam_trong_env():
    dinh = []
    for name, text in FILES:
        if name.startswith(("tests/", "examples/")):
            continue
        for i, d in enumerate(text.splitlines(), 1):
            if _token_tho_trong_env(d):
                dinh.append(f"{name}:{i} {d.strip()[:90]}")
    assert not dinh, ("token THÔ không bao giờ nằm trong `.env` — biến giữ ĐƯỜNG DẪN, secret "
                      "nằm trong file được trỏ tới (token Telegram đã lộ một lần vì mô hình "
                      "cũ, 08/09):\n  " + "\n  ".join(dinh))


# ── Tự kiểm: cổng phải nới ĐÚNG chỗ và không nới quá tay ─────────────────────

MAU_F17_HOP_LE = [
    "Chế độ `embedded` giữ cấu hình bí mật trong `.env` ở gốc repo.",
    "Bộ cài ghi lựa chọn vào `.env` khi người dùng chọn `embedded`.",
    "Thiếu biến môi trường thì đọc từ `.env` (chỉ khi `mode=embedded`).",
    "Cấu hình của chế độ `embedded` nằm ở `.env`.",
    "Cấu hình đi qua file `.env` khi cài theo chế độ `embedded`.",
    "`doctor` kiểm quyền của `.env` là 600 trên POSIX.",
    "`backup` mặc định KHÔNG kèm `.env`; muốn kèm thì bật cờ riêng.",
    "Biến `YT_TOKEN_PATH` khai trong `.env` chỉ giữ ĐƯỜNG DẪN tới file token.",
]

MAU_MO_HINH_CU = [
    "Đặt token Telegram vào `.env` rồi chạy lại.",
    "Script đọc token từ `.env` lúc khởi động.",
    "Token nằm trong `.env` ở gốc repo.",
    "Khai token ở `.env` là đủ.",
    "Dán client_secret vào `.env`.",
]


@pytest.mark.parametrize("dong", MAU_F17_HOP_LE)
def test_cong_KHONG_chan_cach_noi_cua_F17_embedded(dong):
    """Tài liệu F17 phải viết được. Cổng chặn đúng việc sắp phải làm = cổng sẽ bị gỡ cả cụm."""
    cam = [c for c in CAM if c in dong]
    assert not cam, f"chuỗi cấm {cam} chặn cách nói HỢP LỆ của F17: {dong!r}"
    assert not _token_tho_trong_env(dong), f"luật token chặn cách nói hợp lệ: {dong!r}"


@pytest.mark.parametrize("dong", MAU_MO_HINH_CU)
def test_cong_VAN_chan_mo_hinh_token_tho_trong_env(dong):
    """Vế ngược: nới cho F17 mà nới luôn mô hình cũ thì cổng thành đồ trang trí."""
    assert _token_tho_trong_env(dong) or [c for c in CAM if c in dong], (
        f"mô hình cũ lọt qua cổng: {dong!r}")


def test_TG_BOT_TOKEN_van_bi_cam():
    """Biến token-trong-env đã bị bỏ hẳn sau lần lộ token; F17 không đụng tới điều đó."""
    assert "TG_BOT_TOKEN=" in CAM


# ── Lệnh trong tài liệu phải là lệnh CLI hiểu được ─────────────────────────
# Đợt đổi tên 12/09/2026 sửa code (`soan`→`write`, `gui`/`nhan`→`send`/`receive`, `cho`→
# `waiting`) mà bỏ sót tài liệu: người gõ theo tài liệu thì argparse báo "invalid choice".
# `test_pipeline_spec` chỉ canh MỘT file; cổng này canh mọi tài liệu và docstring.

CO_LENH_CON = ("approve_bus", "approval_gate", "campaign_step", "run_pipeline",
               "register_publish", "make_fb_image")
_LENH = re.compile(r"(`?)(?:scripts/pipeline/)?\b(" + "|".join(CO_LENH_CON) + r")(\.py)?"
                   r"(?:[ \t]+<[^>\n]*>)?[ \t]+([a-z][a-z-]*)(?=[\s`|\\]|$)", re.M)
_BUOC_RUNNER = re.compile(r"-Step[ \t]+([a-z][a-z-]*)")
_DUOI_TAI_LIEU = (".md", ".yaml", ".yml", ".py", ".ps1")


def _tai_lieu_va_docstring():
    for name, text in FILES:
        if name.startswith(("tests/", "examples/")) or not name.endswith(_DUOI_TAI_LIEU):
            continue
        if name == "scripts/pipeline/migrate_names.py":
            continue          # bảng tra tên cũ → mới, phải chứa tên cũ
        yield name, text


def test_lenh_con_trong_tai_lieu_DEU_duoc_CLI_hieu():
    thieu = []
    for name, text in _tai_lieu_va_docstring():
        for m in _LENH.finditer(text):
            ve, script, py, tu = m.groups()
            if not (ve or py):
                continue      # văn xuôi / `import x as` — chỉ soi dạng lệnh trong mã
            src = (ROOT / "scripts" / "pipeline" / f"{script}.py").read_text(encoding="utf-8")
            if f'"{tu}"' not in src:
                row = text[:m.start()].count("\n") + 1
                thieu.append(f"{name}:{row} {script} {tu}")
    assert not thieu, "tài liệu gọi lệnh con CLI không có:\n  " + "\n  ".join(thieu)


def test_buoc_Step_trong_tai_lieu_NAM_TRONG_ValidateSet_cua_runner():
    src = (ROOT / "scripts/runners/run-blog-campaign.ps1").read_text(encoding="utf-8")
    m = re.search(r"ValidateSet\(([^)]*)\)", src)
    assert m, "runner không còn ValidateSet"
    cho_phep = {x.strip().strip("'\"") for x in m.group(1).split(",")}
    sai = []
    for name, text in _tai_lieu_va_docstring():
        for b in _BUOC_RUNNER.finditer(text):
            if b.group(1) not in cho_phep:
                row = text[:b.start()].count("\n") + 1
                sai.append(f"{name}:{row} -Step {b.group(1)}")
    assert not sai, (f"runner chỉ nhận {sorted(cho_phep)}:\n  " + "\n  ".join(sai))


# ── Biến môi trường: code đọc biến nào thì tài liệu phải khai biến đó ───────
# Kế hoạch dời máy đòi "khai một chỗ". Biến mới (`CHROME_BIN`, `FFMPEG_DIR`…) sinh ra trong
# code mà không vào tài liệu thì người dựng máy mới không biết mà đặt — và script lặng lẽ
# rơi về đường dò mặc định.

# Hai cách code đọc một biến, và cổng phải thấy CẢ HAI:
#   os.environ.get("X")   — đọc thẳng
#   secret_env("X")       — đọc qua studio_paths (biến → <repo>/.env khi mode=embedded, F17)
# Bỏ sót vế thứ hai thì cổng mất răng trong im lặng: đổi một lời gọi từ vế một sang vế hai
# là biến đó biến khỏi danh sách phải khai, mà không test nào đỏ. Đã xảy ra đúng thế với
# `TG_CONFIG` khi `telegram_io` chuyển sang `secret_env` (P2-G1).
_BIEN_PY = re.compile(
    r"""(?:environ(?:\.get\(|\[)|secret_env\()\s*["']([A-Z][A-Z0-9_]+)["']""")
_BIEN_PS = re.compile(r"\$env:([A-Z][A-Z0-9_]+)")
# Biến của HỆ ĐIỀU HÀNH / của Python — không phải thứ người dùng tự đặt.
BIEN_HE_THONG = {"LOCALAPPDATA", "PROGRAMFILES", "HOME", "USERPROFILE", "PATH",
                 "PYTHONIOENCODING", "PYTHONUTF8", "TEMP", "TMP"}
NOI_KHAI_BIEN = ("knowledge/toolchains/SECRETS.md", ".env.example")


def _bien_code_doc():
    bien = {}
    for name, text in FILES:
        if name.startswith("tests/") and name != "tests/conftest.py":
            continue
        mau = _BIEN_PY if name.endswith(".py") else _BIEN_PS if name.endswith(".ps1") else None
        if mau is None:
            continue
        for m in mau.finditer(text):
            if m.group(1) not in BIEN_HE_THONG:
                bien.setdefault(m.group(1), name)
    return bien


def test_do_duoc_bien_moi_truong():
    """Không bắt được biến nào thì cổng dưới luôn xanh mà không đo gì."""
    bien = _bien_code_doc()
    assert {"MARKETING_STUDIO_DATA", "CHROME_BIN", "TG_CONFIG"} <= set(bien), sorted(bien)


@pytest.mark.parametrize("noi", NOI_KHAI_BIEN)
def test_moi_bien_code_doc_DEU_duoc_khai(noi):
    doc = (ROOT / noi).read_text(encoding="utf-8")
    thieu = [f"{b} (đọc ở {f})" for b, f in sorted(_bien_code_doc().items())
             if not re.search(rf"\b{b}\b", doc)]
    assert not thieu, f"{noi} chưa khai biến code đang đọc:\n  " + "\n  ".join(thieu)


def test_link_tuong_doi_trong_markdown_DEU_toi_file_co_that():
    """`test_tai_lieu_KHONG_tro_vao_file_ma` chỉ soi đường dẫn tính từ gốc repo trong dấu
    `…`. Link markdown `[..](../../x.md)` tính từ CHỖ FILE ĐỨNG — skill từng trỏ
    `../../knowledge/DATA_MODEL.md` (thiếu một tầng `..` và sai thư mục) mà không gì báo."""
    link = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
    chet = []
    for name, text in FILES:
        if not name.endswith(".md"):
            continue
        for m in link.finditer(text):
            dich = m.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", dich) or dich.startswith("<"):
                continue      # URL ngoài, mailto, chỗ điền
            if not ((ROOT / name).parent / dich).exists():
                chet.append(f"{name} → {dich}")
    assert not chet, "link markdown trỏ vào chỗ không có:\n  " + "\n  ".join(chet)


def test_README_va_trang_chu_KHONG_chep_so_test():
    """Số test đổi mỗi commit. Chép vào README (197) hay trang chủ (322) là sai ngay hôm sau."""
    so = re.compile(r"\b\d{2,}\s+test\b")
    sai = [n for n in ("README.md", "docs/index.html")
           if so.search((ROOT / n).read_text(encoding="utf-8"))]
    assert not sai, f"chép số test cứng vào: {sai} — nói cách chạy, đừng nói con số"


def test_mot_file_khong_duoc_mang_hai_luat_link():
    """Ca cụ thể đã xảy ra: cùng một file vừa nói 'thân bài 0 URL' vừa nói 'link đầu bài'."""
    for name, text in FILES:
        if "Thân bài không chứa URL" in text or "thân bài 0 URL" in text.lower():
            assert "đặt ĐẦU bài" not in text, \
                f"{name} mang hai luật link trái nhau trong cùng một file"


def test_moi_cho_ghi_file_deu_ep_xuong_dong_LF():
    """Windows tự đổi \n thành CRLF nếu không ép — và mỗi lần sinh lại là cả file 'đổi'.

    Trong một repo lấy git làm lịch sử, diff giả làm mất luôn khả năng nhìn ra diff thật.
    """
    import re
    thieu = []
    for f in (ROOT / "scripts").rglob("*.py"):
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\.write_text\((.*?)\)\n", s, re.S):
            goi = m.group(1)
            if "encoding=" in goi and "newline=" not in goi:
                row = s[:m.start()].count("\n") + 1
                thieu.append(f"{f.relative_to(ROOT)}:{row}")
        for m in re.finditer(r"\bopen\((?!.*['\"]rb?['\"])(.*?)\)", s):
            goi = m.group(1)
            if '"w"' in goi and "newline=" not in goi:
                row = s[:m.start()].count("\n") + 1
                thieu.append(f"{f.relative_to(ROOT)}:{row} (open w)")
    assert not thieu, "ghi file mà không ép newline='\n': " + ", ".join(thieu)


def test_tai_lieu_KHONG_tro_vao_file_ma():
    """README từng trỏ vào `schema/` và workflows trỏ vào `scripts/workbook/new_campaign.py`
    — cả hai đã bị xoá từ lâu. Đó là cách tài liệu chết: không sai một chữ nào, chỉ là chỗ
    nó chỉ tới không còn ở đó nữa.

    Quét mọi đường dẫn trông-như-file trong tài liệu và kiểm nó tồn tại thật.
    """
    import re
    MAU = re.compile(r"`((?:scripts|templates|knowledge|workflows|output_styles|tests|"
                     r"\.agents|examples|docs|schema)/[A-Za-z0-9_./-]*)`")
    failed = []
    for f in list(ROOT.glob("*.md")) + list(ROOT.glob("workflows/*.md")) \
            + list(ROOT.glob(".agents/**/*.md")) + list(ROOT.glob("knowledge/**/*.md")) \
            + list(ROOT.glob("examples/*.md")):
        for m in MAU.finditer(f.read_text(encoding="utf-8")):
            d = m.group(1)
            if "<" in d or "*" in d or d.endswith("/"):
                continue          # mẫu có chỗ trống, hoặc chỉ là thư mục — bỏ qua
            if not (ROOT / d).exists():
                failed.append(f"{f.relative_to(ROOT)} → {d}")
    assert not failed, "tài liệu trỏ vào file không tồn tại:\n  " + "\n  ".join(failed)


def test_so_cong_trong_tai_lieu_KHOP_so_cong_thuc_te():
    """`blog_gates.py` tự ghi '22 cổng' trong khi phát 23 mã — và 3 tài liệu chép theo.

    Con số này người ta trích dẫn khắp nơi (README, trang chủ, checklist). Sai một con số
    đếm được là dấu hiệu rõ nhất rằng tài liệu đã ngừng theo kịp code.
    """
    import re
    job_id = re.findall(r'"(G\d{2})\b', (ROOT / "scripts/pipeline/blog_gates.py")
                    .read_text(encoding="utf-8"))
    that = len(set(job_id))
    assert that >= 20, f"không đếm được mã cổng (thấy {that}) — regex hỏng?"

    sai = []
    for f in list(ROOT.glob("*.md")) + list(ROOT.glob("**/*.md")):
        if ".git" in f.parts:
            continue
        for m in re.finditer(r"(\d{2}) cổng", f.read_text(encoding="utf-8")):
            if int(m.group(1)) != that:
                sai.append(f"{f.relative_to(ROOT)} nói {m.group(1)}, thực tế {that}")
    for m in re.finditer(r"(\d{2}) cổng",
                         (ROOT / "scripts/pipeline/blog_gates.py").read_text(encoding="utf-8")):
        if int(m.group(1)) != that:
            sai.append(f"blog_gates.py tự nói {m.group(1)}, thực tế {that}")
    assert not sai, "số cổng lệch:\n  " + "\n  ".join(sai)


def test_DATA_MODEL_dinh_nghia_DU_moi_cot_dang_chay():
    """DATA_MODEL tự xưng CANONICAL. Vậy thì mọi cột đang chạy phải có mặt trong đó.

    Đo 05/09: 11 trong 15 cột của bảng Content (`g1 g2 web youtube facebook pillar angle
    funnel schedule published folder`) KHÔNG được định nghĩa ở đâu cả, trong khi file vẫn
    mô tả `approved_date`, `folder_path`… của mô hình Excel cũ. Agent đọc file này rồi đi
    ghi `approved_date` vào bảng Content là ghi vào hư không.
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "lib"))
    _s.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import new_post

    read = (ROOT / "knowledge/data_model/DATA_MODEL.md").read_text(encoding="utf-8")
    thieu = [c for c in new_post.COT if f"`{c}`" not in read]
    assert not thieu, ("DATA_MODEL không định nghĩa cột đang chạy: " + ", ".join(thieu))

    for k in new_post.BAT_BUOC:
        assert f"`{k}`" in read, f"trường bắt buộc {k} không có trong DATA_MODEL"


def test_tai_lieu_KHONG_khai_trang_thai_ma_code_khong_sinh():
    """Đo 05/09: tài liệu khai 6 giá trị `agent_status` và 12 `post_status`; code chỉ sinh
    3 và 3, và **không lệnh nào** đặt được phần còn lại. Agent làm đúng theo tài liệu sẽ ghi
    một giá trị không ai định nghĩa vào sổ, rồi nó in thẳng ra Excel.
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "lib"))
    import post_paths as PP

    # Giá trị đã bị bỏ — không được xuất hiện lại trong tài liệu như thể dùng được.
    da_bo = {"not_started", "generating", "ai_qa_passed", "ai_qa_failed", "ai_qa",
             "human_review", "revision", "measuring", "needs_review", "publish_failed",
             "cancelled"}
    hop_le = set().union(*PP.GIA_TRI_HOP_LE.values())
    assert not (da_bo & hop_le), "giá trị vừa nằm trong danh sách bỏ vừa hợp lệ — mâu thuẫn"

    sai = []
    for f in list(ROOT.glob("workflows/*.md")) + list(ROOT.glob(".agents/**/*.md")) \
            + list(ROOT.glob("knowledge/**/*.md")) + [ROOT / "AGENTS.md"]:
        t = f.read_text(encoding="utf-8")
        for g in da_bo:
            if g in t:
                sai.append(f"{f.relative_to(ROOT)} còn nhắc {g!r}")
    assert not sai, ("tài liệu khai trạng thái code không sinh:\n  " + "\n  ".join(sai))


def test_GIA_TRI_HOP_LE_phu_moi_gia_tri_code_THAT_SU_ghi():
    """Chiều ngược lại: code sinh một giá trị mà danh sách thiếu thì `check_tree` báo đỏ oan
    — đúng chuyện vừa xảy ra với `blocked` (register_publish.py:178)."""
    import re
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts" / "lib"))
    import post_paths as PP

    src = (ROOT / "scripts/pipeline/register_publish.py").read_text(encoding="utf-8")
    for truong in ("agent_status", "post_status", "quality_check"):
        viet = set(re.findall(rf'\["{truong}"\]\s*=\s*"([a-z_]+)"', src))
        viet |= set(re.findall(rf'"{truong}":\s*"([a-z_]+)"', src))
        viet |= set(re.findall(rf'\["{truong}"\]\s*=\s*"[a-z_]+" if .* else "([a-z_]+)"', src))
        thieu = viet - PP.GIA_TRI_HOP_LE[truong]
        assert not thieu, (f"register_publish ghi {truong}={thieu} mà GIA_TRI_HOP_LE thiếu — "
                           f"check_tree sẽ báo đỏ oan")


def test_moi_duong_dan_templates_trong_ma_va_tai_lieu_deu_ton_tai():
    """Đường dẫn `templates/...` được nhắc ở đâu thì file đó phải CÓ THẬT.

    Cạm bẫy đã trả giá (07/09/2026): đổi `templates/` từ cây phẳng sang
    `templates/station/_channel/_campaign/_content/` khiến `install.ps1` đi copy một file
    `CHANNELS.md` không còn tồn tại ở chỗ cũ. Script đặt `$ErrorActionPreference='Stop'`
    nên nó **crash ngay bước dựng trạm** — người vừa clone repo về, chạy lệnh cài đặt đầu
    tiên, là hỏng. Không test nào bắt được vì không test nào chạy `install.ps1`.

    Cổng `test_khong_con_ten_cu` chỉ cấm những cái tên nằm trong danh sách đen — nó không
    thể biết một đường dẫn MỚI có tồn tại hay không. Cổng này kiểm điều ngược lại: mọi
    đường dẫn trỏ vào `templates/` đều phải giải quyết ra file hoặc thư mục thật.
    """
    import re

    # Bắt cả `templates/a/b.md` lẫn `templates\a\b.md` (PowerShell dùng dấu ngược).
    mau = re.compile(r"templates[\\/][A-Za-z0-9_\-./\\]+")
    chet = []
    for name, text in _tracked():
        for m in mau.finditer(text):
            # Cắt dấu câu dính đuôi khi đường dẫn nằm giữa câu văn.
            duong = m.group().rstrip(".,;:)`\"'").replace("\\", "/").rstrip("/")
            # `templates/<gì đó>` không có đuôi file và cũng không phải thư mục có thật thì
            # đó là cách nói chung chung ("thư mục templates/"), không phải con trỏ.
            if "." not in Path(duong).name and not (ROOT / duong).is_dir():
                continue
            if not (ROOT / duong).exists():
                chet.append(name + ": " + duong)

    assert not chet, (
        "đường dẫn templates/ trỏ vào chỗ không tồn tại — sửa đường dẫn hoặc tạo file:\n  "
        + "\n  ".join(sorted(set(chet))))


def test_script_MAU_khong_lo_duong_dan_may_that():
    """Script mau trong repo PUBLIC khong duoc mang duong dan may cua ai.

    Da suyt dinh 10/09/2026: mot docstring lot duong dan nha rieng. Repo la ban
    chung; duong dan that thuoc ve tram.

    Docstring nay co Y GIU TIENG VIET KHONG DAU va khong vi du duong dan: chinh no
    tung lam ca file khong import noi (dau gach cheo + chu U thanh escape unicode),
    va lai la dung cai bay test nay dang canh.
    """
    import re
    mau = re.compile(r"[Cc]:[\\/]Users[\\/](?!<)(\w+)")
    xau = []
    for f in (ROOT / "templates").rglob("*"):
        if f.suffix.lower() not in (".ps1", ".py", ".md", ".yml", ".json"):
            continue
        for m in mau.finditer(f.read_text(encoding="utf-8", errors="replace")):
            if m.group(1).lower() not in ("username", "user", "name", "you"):
                xau.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
    assert not xau, "duong dan may that lot vao template: " + ", ".join(xau)


# ── Tài liệu vận hành: có mặt, được trỏ tới, và nói đúng cờ CLI ─────────────
# Ba file này là thứ người ta mở ra lúc đang hoảng (máy mới, lịch không chạy, phải đổi
# máy trong đêm). Chúng chết theo đúng hai kiểu: hoặc không ai tìm thấy, hoặc chúng bảo
# gõ một cờ mà CLI không hiểu. Ba cổng dưới canh đúng hai kiểu đó.

TAI_LIEU_VAN_HANH = ("docs/ONBOARDING.md", "docs/RUNBOOK-DOI-MAY.md",
                     "docs/WORKSPACE.md", "knowledge/toolchains/STATION_LAYOUT.md",
                     ".agents/prompts/onboard-station.md")


@pytest.mark.parametrize("f", TAI_LIEU_VAN_HANH)
def test_tai_lieu_van_hanh_ton_tai(f):
    assert (ROOT / f).is_file(), f"{f} không có — code đang in đường dẫn tới nó"


# ── PHÂN TẦNG NĂNG LỰC: lõi viết-và-đăng vs giọng/video (chỉ đạo 21/09/2026) ─────────
#
# Cổng ở trên chặn CÂU CŨ quay lại. Cổng dưới đây canh vế còn lại: câu MỚI phải thật sự
# có mặt ở chỗ người dùng đọc. Thiếu nó thì `doctor` nói một đằng (mã 0, "chưa bật") mà
# tài liệu nói một nẻo, và người đọc tin tài liệu — họ đi cài hai repo nữa trước khi viết
# được bài nào, hoặc bỏ dở vì tưởng mình chưa cài xong.
#
# Ba file này là cửa vào: README là thứ đầu tiên người clone đọc; ONBOARDING là thứ họ làm
# theo; STATION_LAYOUT là chỗ họ tra khi muốn biết ba trạm ăn nhập với nhau thế nào.

CAU_KHONG_BAT_BUOC = "không bắt buộc trạm giọng/video"
NOI_PHAI_NOI_RO = ("README.md", "docs/ONBOARDING.md",
                   "knowledge/toolchains/STATION_LAYOUT.md")


@pytest.mark.parametrize("f", NOI_PHAI_NOI_RO)
def test_tai_lieu_noi_ro_KHONG_BAT_BUOC_tram_giong_video(f):
    t = (ROOT / f).read_text(encoding="utf-8")
    assert CAU_KHONG_BAT_BUOC in t, (
        f"{f} chưa nói rằng repo {CAU_KHONG_BAT_BUOC}. `doctor` trả mã 0 khi thiếu hai "
        f"trạm đó (chỉ đạo 21/09) — tài liệu không nói thì người đọc vẫn tưởng phải cài "
        f"đủ ba repo mới viết được bài.")


def test_cau_KHONG_BAT_BUOC_dung_dung_tu_ma_BO_CAI_in_ra():
    """Tài liệu và bộ cài phải nói CÙNG MỘT CÂU. Hai cách diễn đạt cho cùng một luật là
    hai chỗ để trôi khỏi nhau."""
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
    import init_station as IS
    assert CAU_KHONG_BAT_BUOC in IS.BANG_LUA_CHON


def test_README_tro_toi_runbook_va_onboarding():
    """Runbook không ai tìm thấy thì bằng không có. Cửa vào là README."""
    t = (ROOT / "README.md").read_text(encoding="utf-8")
    for f in ("docs/RUNBOOK-DOI-MAY.md", "docs/ONBOARDING.md",
              "knowledge/toolchains/STATION_LAYOUT.md"):
        assert f in t, f"README chưa trỏ tới {f}"


def test_duong_dan_docs_ma_CODE_in_ra_deu_ton_tai():
    """`init_station` và `station.py` in tên tài liệu cho người dùng đọc tiếp.

    In ra một cái tên không tồn tại là lời khuyên dẫn vào ngõ cụt — và nó chỉ lộ ra với
    đúng người đang cần nó nhất: người vừa cài xong, hoặc vừa import xong.
    """
    mau = re.compile(r"\b(docs/[A-Za-z0-9_.-]+\.md)\b")
    # Trỏ sang tài liệu của REPO KHÁC là hợp lệ và không kiểm được từ đây (`video.py` chỉ
    # người dùng sang `docs/INSTALL.md` của repo trạm video). Nhận ra bằng chính câu văn.
    khac_repo = ("repo đó", "repo kia", "agent-voice-studio", "agent-video-studio")
    chet = []
    for name, text in FILES:
        if not name.startswith("scripts/"):
            continue
        dong = text.splitlines()
        for m in mau.finditer(text):
            row = text[:m.start()].count("\n") + 1
            if any(k in dong[row - 1] for k in khac_repo):
                continue
            if not (ROOT / m.group(1)).is_file():
                chet.append(f"{name}:{row} → {m.group(1)}")
    assert not chet, "code in ra đường tài liệu không tồn tại:\n  " + "\n  ".join(chet)


# Mỗi lệnh trong khối mã của tài liệu: cờ `--x` phải là cờ CLI đó HIỂU.
# Đợt đổi tên 12/09 đã dạy bài này với lệnh con; cờ cũng hỏng y hệt, chỉ khác là người gõ
# nhận "unrecognized arguments" thay vì "invalid choice".
#
# Bộ cờ lấy bằng cách CHẠY `--help`, không phải bằng cách tìm chuỗi `"--x"` trong mã nguồn.
# Bản đầu tìm chuỗi và báo oan ngay: `register_publish.py metrics` sinh bảy cờ bằng
# `add_argument(f"--{k}")` trong một vòng lặp, nên không cờ nào có mặt dưới dạng literal.
# Một cổng báo oan là một cổng sắp bị tắt — nên nó phải hỏi chính argparse.
_SCRIPT_TRONG_REPO = re.compile(r"((?:scripts/[a-z]+/)?[a-z_]+\.py)")
_CO = re.compile(r"(?<![\w-])--([a-z][a-z0-9-]*)")
_CHO_DIEN = re.compile(r"^<.*>$|^\{.*\}$")


def _thu_muc_script(ten: str) -> Path | None:
    for p in [ROOT / ten] + [ROOT / d / Path(ten).name
                             for d in ("scripts/pipeline", "scripts/runners", "scripts/lib")]:
        if p.is_file():
            return p
    return None


def _tien_to(lenh: str, ten: str) -> list[str]:
    """Đối số đứng TRƯỚC cờ đầu tiên (lệnh con + positional), chỗ điền thay bằng `X`."""
    tok = lenh.split()
    i = next((k for k, t in enumerate(tok) if ten in t), None)
    if i is None:
        return []
    ra = []
    for t in tok[i + 1:]:
        if t.startswith("-"):
            break
        ra.append("X" if _CHO_DIEN.match(t) else t)
    return ra


_CACHE: dict = {}


def _co_CLI_hieu(f: Path, tien_to: tuple) -> set[str] | None:
    """Bộ cờ thật, hỏi bằng `--help`. None = không lấy được (không chấm lệnh đó)."""
    khoa = (str(f), tien_to)
    if khoa not in _CACHE:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        try:
            r = subprocess.run([sys.executable, str(f), *tien_to, "--help"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env, timeout=60)
        except (OSError, subprocess.SubprocessError):
            _CACHE[khoa] = None
            return None
        ra = (r.stdout or "") + (r.stderr or "")
        bo = {m.group(1) for m in _CO.finditer(ra)}
        _CACHE[khoa] = bo if (r.returncode == 0 and bo) else None
    return _CACHE[khoa]


def _lenh_trong_khoi_ma(text: str):
    """Trả từng LỆNH trong khối ``` — nối dòng tiếp nối kết thúc bằng `\\`.

    Cắt chú thích ` # …` ở cuối dòng: `studio.py update   # = git pull --ff-only` là một
    lệnh CỘNG một lời giải thích, và `--ff-only` thuộc về lời giải thích. Không cắt thì
    cổng đi đòi `studio.py` phải có một cờ của `git`.
    """
    trong = False
    dem = []
    for d in text.splitlines():
        if d.count('"') % 2 == 0 and d.count("'") % 2 == 0:
            d = re.sub(r"\s+#.*$", "", d)
        if d.lstrip().startswith("```"):
            trong = not trong
            if not trong and dem:
                yield " ".join(dem)
                dem = []
            continue
        if not trong:
            continue
        if dem:
            dem.append(d.strip())
        elif d.strip():
            dem.append(d.strip())
        else:
            continue
        if dem[-1].endswith("\\"):
            dem[-1] = dem[-1][:-1]
        else:
            yield " ".join(dem)
            dem = []
    if dem:
        yield " ".join(dem)


def _cham_co_CLI():
    """(số lệnh đã chấm thật, danh sách sai)."""
    dem, sai = 0, []
    for name, text in FILES:
        if not name.endswith(".md") or name.startswith(("tests/", "examples/")):
            continue
        for lenh in _lenh_trong_khoi_ma(text):
            for m in _SCRIPT_TRONG_REPO.finditer(lenh):
                ten = m.group(1)
                f = _thu_muc_script(ten)
                if f is None:
                    continue                      # không phải script của repo này
                xin = {c.group(1) for c in _CO.finditer(lenh)} - {"help"}
                if not xin:
                    continue
                bo = _co_CLI_hieu(f, tuple(_tien_to(lenh, ten)))
                if bo is None:
                    continue                      # không hỏi được argparse — không đoán
                dem += 1
                for c in sorted(xin - bo):
                    sai.append(f"{name}: `{ten} {' '.join(_tien_to(lenh, ten))}` "
                               f"không có cờ --{c}")
    return dem, sai


def test_co_CLI_trong_tai_lieu_DEU_duoc_script_hieu():
    _, sai = _cham_co_CLI()
    assert not sai, "tài liệu bảo gõ cờ CLI không có:\n  " + "\n  ".join(sorted(set(sai)))


def test_cong_co_CLI_that_su_cham_duoc_gi():
    """Cổng trên chấm 0 lệnh thì nó luôn xanh mà không đo gì. Chặn ngay tại đây."""
    dem, _ = _cham_co_CLI()
    assert dem >= 8, f"chỉ chấm được {dem} lệnh có cờ — regex hỏng, hay `--help` không chạy?"


def test_moi_hook_khai_trong_template_deu_CO_THAT_trong_code():
    """Template hứa bốn hook thì code phải đọc đủ bốn.

    Tài liệu đi trước code là cách hỏng đã có tên trong sổ này: người dùng khai một khoá,
    engine lặng lẽ bỏ qua, và không gì báo.
    """
    mau = (ROOT / "templates" / "station" / "_channel" / "_campaign" / "campaign.md"
           ).read_text(encoding="utf-8")
    src = (ROOT / "scripts" / "pipeline" / "campaign_step.py").read_text(encoding="utf-8")
    for khoa in ("writer_cmd", "audio_cmd", "youtube_cmd", "facebook_cmd"):
        assert khoa in mau, f"template chưa nhắc `{khoa}`"
        assert khoa in src or khoa.replace("_cmd", "") in src, \
            f"template hứa `{khoa}` nhưng code không đọc"
