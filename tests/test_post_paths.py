# -*- coding: utf-8 -*-
"""Test cho bố cục thư mục bài.

Bố cục là thứ 6 script và 8 tài liệu cùng dựa vào. Sai một dòng ở đây là hỏng lan, và hỏng
kiểu im lặng: script không tìm thấy file thì bỏ qua chứ không kêu.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import post_paths as P  # noqa: E402


def test_khong_co_duong_di_ra_ngoai():
    """Không khoá nào được trỏ ra ngoài thư mục bài."""
    for khoa, gia_tri in P.LAYOUT.items():
        assert not gia_tri.startswith(("/", "\\")), f"{khoa} là đường tuyệt đối"
        assert ".." not in Path(gia_tri).parts, f"{khoa} đi ra ngoài thư mục bài"


def test_khong_hai_khoa_tro_cung_mot_file():
    """Hai khoá cùng file = hai script tưởng đang ghi hai chỗ, thực ra đè nhau."""
    nguoc = {}
    for khoa, gia_tri in P.LAYOUT.items():
        nguoc.setdefault(gia_tri.lower(), []).append(khoa)
    trung = {v: k for v, k in nguoc.items() if len(k) > 1}
    assert not trung, f"trùng đường dẫn: {trung}"


def test_file_kenh_nam_dung_thu_muc_kenh():
    for khoa, thu_muc in [("yt_video", "youtube"), ("yt_thumb", "youtube"), ("yt_desc", "youtube"),
                          ("blog", "atlas"), ("atlas_html", "atlas"), ("audio", "atlas"),
                          ("fb_post", "facebook"), ("fb_comment", "facebook"),
                          ("fb_image", "facebook"), ("fb_prompt", "facebook"), ("fb_reel", "facebook")]:
        assert P.LAYOUT[khoa].startswith(thu_muc + "/"), f"{khoa} không nằm trong {thu_muc}/"


def test_phan_nghien_cuu_nam_o_GOC():
    """research/content/kịch bản/sổ ở gốc — đó là thứ người làm bài đọc, không phải thứ đem đăng."""
    for khoa in ("meta", "research", "content", "podcast", "scenes", "gates", "publish"):
        assert "/" not in P.LAYOUT[khoa], f"{khoa} bị đẩy vào thư mục con"


def test_moi_khoa_cong_khai_deu_ton_tai():
    for khoa in P.FILE_CONG_KHAI:
        assert khoa in P.LAYOUT, f"FILE_CONG_KHAI nhắc khoá không có: {khoa}"


def test_p_va_tao_thu_muc(tmp_path):
    P.tao_thu_muc(tmp_path)
    for t in P.THU_MUC_KENH:
        assert (tmp_path / t).is_dir()
    assert P.p(tmp_path, "fb_post") == tmp_path / "facebook" / "post.txt"


def test_khoa_sai_thi_no_KeyError(tmp_path):
    """Gõ sai khoá phải vỡ ngay, không được trả về đường dẫn vô nghĩa rồi im lặng."""
    import pytest
    with pytest.raises(KeyError):
        P.p(tmp_path, "khoa_khong_ton_tai")
