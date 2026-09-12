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
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Chuỗi cấm -> vì sao cấm. Chỉ liệt kê thứ KHÔNG CÒN ĐÚNG, không liệt kê thứ chỉ cũ.
CAM = {
    "Link đặt ĐẦU bài": "luật link Facebook đã đảo 04/09: thân bài 0 URL, link ở comment đầu",
    "post:youtube_video": "neo đã đổi thành post:youtube_desc (gen_article chỉ hiểu tên mới)",
    "fb_image.png": "đã gộp thành facebook/infographic.png — xem post_paths.LAYOUT",
    # KHÔNG cấm "tobi_excel.py": nó xuất hiện HỢP LỆ trong khối cảnh báo đầu hai file .ps1
    # (đang giải thích vì sao chúng chưa chạy được). Cấm một cái tên vì nó cũ là sai —
    # chỉ cấm thứ còn tự xưng là LUẬT HIỆN HÀNH.
}

# Nơi được phép nhắc tên cũ: chỗ GIẢI THÍCH lịch sử, và chính file này.
MIEN_TRU = ("tests/test_docs_drift.py", "fixtures/baseline/")

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
    dinh = []
    for name, text in FILES:
        if chuoi in text:
            row = text[:text.index(chuoi)].count("\n") + 1
            dinh.append(f"{name}:{row}")
    assert not dinh, f"{chuoi!r} — {why}. Còn ở: {dinh[:10]}"


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
