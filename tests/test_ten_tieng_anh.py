# -*- coding: utf-8 -*-
"""Cổng canh: TÊN bằng tiếng Anh, VĂN XUÔI bằng tiếng Việt.

Luật ngôn ngữ của repo, chốt 12/09/2026: thứ **máy đọc để định tuyến** — tên file, tên
hàm, tên hằng, khoá dữ liệu, cờ CLI — viết bằng tiếng Anh; thứ **người đọc** — bình luận,
docstring, tài liệu — viết bằng tiếng Việt.

Cổng này chỉ canh vế thứ nhất, vì vế đó có thể kiểm bằng máy. Nó không đọc hộ ai cả; nó
chỉ đảm bảo bộ tên cũ **không quay lại một cách im lặng** khi có người chép một đoạn code
cũ vào, hoặc khi một script sinh file đặt tên theo thói quen.

Không canh vế thứ hai (văn xuôi phải là tiếng Việt) vì đó là chuyện thẩm mỹ và ngữ cảnh,
máy đo sẽ sai nhiều hơn đúng.
"""
import io
import re
import subprocess
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Bộ tên CŨ. Mỗi cái từng là tên thật trong repo này trước 12/09/2026.
TEN_CU = {
    # module + tài liệu
    "bai_noi_dung", "hang_cho", "so_su_kien", "tinh_trang", "tho_viec", "cong_duyet",
    "chay_quy_trinh", "duong_ong", "QUY_TRINH_CHIEN_DICH", "QUY_TRINH_TRONG_PHIEN",
    "TELEGRAM_LAM_TRUNG_GIAN",
    # hàm / hằng
    "mo_cong", "tu_choi", "cho_cong", "ho_so_bai", "doc_bang", "buoc_ke", "tinh_hinh",
    "chon_bai", "lam_mot_viec", "gui_cong", "ghi_nguyen_tu", "nguyen_van", "ma_thoat",
    "THU_TU", "CAN_NGUOI", "TRAN_VIET_LAI", "CHE_DO", "SO_BAI_MAC_DINH",
    # khoá dữ liệu
    "ma_viec", "ly_do_hong", "hong_luc", "se_thu_lai", "tao_luc", "so_lan", "ghi_chu",
    "ket_luan", "trang_thai", "do_chan", "do_canh_bao", "do_duoc", "mien_tru",
    "xong_luc", "ket_qua", "vinh_vien", "tin_bai", "het_han",
    # tên bước + hộp hàng chờ + tên file dữ liệu
    "cho-G1", "cho-G2", "cho-G3", "dung-bai", "cham-cong", "sua-loi-cong",
    "dung-trang", "phat-hanh", "dang-lam", "su-kien.jsonl", "tg-phan-hoi.json",
    "viet-lan", "logs/viec",
    # cờ CLI
    "--nguyen-van", "--che-do", "--so-bai", "--toi-buoc", "--chi-tiet", "--cho-phep",
    "--dien-vao-dong", "--bo-qua-cong", "--khong-push", "--gia-lap-http", "--lien-tuc",
    "--truoc", "--loai", "--boi", "--qua", "--bai", "--cong", "--lo",
}

# `examples/` là NỘI DUNG mẫu tiếng Việt (slug bài sinh từ tiêu đề), không phải mã.
# File này tự nhiên phải chứa mọi tên cũ, nên nó tự miễn trừ.
WAIVED = ("examples/", "tests/test_ten_tieng_anh.py", ".tmp/")
BINARY = {".png", ".jpg", ".jpeg", ".mp3", ".mp4", ".xlsx", ".ico", ".woff", ".woff2"}


def _tracked():
    ra = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [t for t in ra.stdout.decode().split("\0")
            if t and not t.startswith(WAIVED) and Path(t).suffix.lower() not in BINARY]


FILES = _tracked()


def test_co_file_de_quet():
    """Không có file nào thì hai cổng dưới luôn xanh mà không đo gì."""
    assert len(FILES) > 50, f"chỉ thấy {len(FILES)} file — nghi lỗi môi trường"


@pytest.mark.parametrize("ten", sorted(TEN_CU))
def test_ten_cu_KHONG_quay_lai_trong_TEN_FILE(ten):
    dinh = [f for f in FILES if ten in f]
    assert not dinh, f"tên cũ {ten!r} quay lại trong tên file: {dinh}"


# Cờ CLI và tên bước là CHUỖI, không phải định danh — cổng token không thấy chúng.
# Chúng lại là thứ người gõ tay và script ngoài repo gọi tới, nên sai là hỏng lúc chạy thật.
CHUOI_CU = sorted(x for x in TEN_CU if x.startswith("--") or "-" in x or "." in x)

# `migrate_names.py` PHẢI chứa bộ tên cũ — đó là bảng tra của nó. Cấm nó là cấm luôn
# đường di trú. Test của nó cũng vậy: nó dựng dữ liệu hình dạng cũ để kiểm.
WAIVED_CHUOI = ("scripts/pipeline/migrate_names.py", "tests/test_migrate_names.py")


@pytest.mark.parametrize("chuoi", CHUOI_CU)
def test_co_CLI_va_ten_buoc_cu_KHONG_quay_lai(chuoi):
    dinh = []
    for f in FILES:
        if f.startswith(WAIVED_CHUOI):
            continue
        try:
            # Khớp theo BIÊN, không phải chuỗi con: `--lo` mà khớp lỏng thì nó ăn vào
            # `--lookahead` và cổng đỏ vì một cái tên hoàn toàn hợp lệ.
            if re.search(re.escape(chuoi) + r"(?![A-Za-z0-9_-])",
                         (ROOT / f).read_text(encoding="utf-8")):
                dinh.append(f)
        except (UnicodeDecodeError, OSError):
            continue
    assert not dinh, f"chuỗi cũ {chuoi!r} còn ở: {dinh[:8]}"


def test_dinh_danh_Python_KHONG_dung_ten_cu():
    """Chỉ soi token NAME. Bình luận nhắc tên cũ khi kể lịch sử là HỢP LỆ.

    Đây là chỗ phân biệt quan trọng: `# đổi tên từ mo_cong 12/09` là văn xuôi kể chuyện,
    còn `def mo_cong(` là mã sống. Cấm cả hai thì không ai ghi lại được lịch sử nữa.
    """
    dinh = []
    for f in FILES:
        if not f.endswith(".py"):
            continue
        src = (ROOT / f).read_text(encoding="utf-8")
        for k, s, d, _, _ in tokenize.generate_tokens(io.StringIO(src).readline):
            if k == tokenize.NAME and s in TEN_CU:
                dinh.append(f"{f}:{d[0]} {s}")
    assert not dinh, "định danh mang tên cũ:\n  " + "\n  ".join(dinh[:20])
