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
"""
import re
import subprocess
import zipfile
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
    # Ca hai chuoi tren deu DUNG TU MANH, khong viet literal: file nay nam trong cay
    # git-tracked nen chinh no bi quet. Viet literal = cong luon do vi chinh no.
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


@pytest.mark.parametrize("cam", CAM_TUYET_DOI)
def test_khong_ro_ri_danh_tinh(cam):
    dinh = []
    for p, noi_dung in FILES:
        if cam in noi_dung:
            dong = noi_dung[:noi_dung.index(cam)].count("\n") + 1
            dinh.append(f"{p.relative_to(ROOT).as_posix()}:{dong}")
    assert not dinh, f"chuỗi {cam!r} xuất hiện trong repo public tại: {dinh[:12]}"


def test_khong_lo_token():
    dinh = []
    for p, noi_dung in FILES:
        for mau in MAU_TOKEN + [MAU_EMAIL]:
            if mau.search(noi_dung):
                dinh.append(f"{p.relative_to(ROOT).as_posix()} ({mau.pattern[:18]}…)")
    assert not dinh, f"có chuỗi hình dạng token: {dinh}"


def test_fixtures_trung_tinh():
    """`fixtures/` là mốc đối chứng — số liệu phải dùng được mà không lộ ai là ai."""
    ten = re.compile(r"KPIM|COMPA|Tobi", re.I)
    dinh = [p.relative_to(ROOT).as_posix()
            for p, noi_dung in FILES
            if p.parts[len(ROOT.parts):][:1] == ("fixtures",) and ten.search(noi_dung)]
    assert not dinh, f"fixtures/ phải trung tính, còn tên tổ chức ở: {dinh}"


def test_prompt_MAU_khong_khoa_vao_mot_nguoi():
    """Repo public. Prompt mở đầu bằng tên thật thì ai clone về cũng viết bằng danh tính
    của người khác — template hỏng, không phải secret rò rỉ.

    Danh tính phải là chỗ trống lấy từ `profile.md` của kênh, đúng hợp đồng mà `new_post.py`
    đã ghi. Tên ở đây dựng bằng mã ký tự để CHÍNH FILE TEST không chứa thứ nó đi săn —
    một cổng tự miễn trừ mình là cổng vô dụng.
    """
    import unicodedata
    cam = [unicodedata.normalize("NFC", x) for x in
           ("Nguy" + chr(0x1EC5) + "n Quang " + chr(0x110) + chr(0x1EE9) + "c",
            "COMPA Class", "T" + "obi", "KP" + "IM")]
    thu_muc = ROOT / ".agents" / "prompts"
    assert thu_muc.is_dir(), "không thấy .agents/prompts — đường dẫn đổi?"

    dinh = []
    for f in sorted(thu_muc.glob("*.txt")):
        t = unicodedata.normalize("NFC", f.read_text(encoding="utf-8"))
        for x in cam:
            if x in t:
                dinh.append(f"{f.name} còn {x!r}")
    assert not dinh, ("prompt mẫu bị khoá vào một người/tổ chức:\n  " + "\n  ".join(dinh))


def test_prompt_MAU_co_du_cho_trong_va_co_dan_cach_dien():
    """Bỏ tên mà không để chỗ trống thì agent sẽ tự bịa một cái tên."""
    thu_muc = ROOT / ".agents" / "prompts"
    for f in sorted(thu_muc.glob("*.txt")):
        t = f.read_text(encoding="utf-8")
        if "{{AUTHOR}}" in t or "{{CHANNEL}}" in t:
            assert "ĐIỀN TRƯỚC KHI DÙNG" in t, \
                f"{f.name} có chỗ trống danh tính nhưng không dặn cách điền"
            assert "profile.md" in t, f"{f.name} không chỉ ra nguồn của danh tính"
