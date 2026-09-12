# -*- coding: utf-8 -*-
"""Cổng canh: `knowledge/data_model/duong_ong.yaml` phải KHỚP với code đang chạy.

Đường ống được mô tả ở bốn chỗ — thứ tự trạng thái (`tinh_trang.THU_TU`), bước nào chạy
lệnh nào (`tho_viec.LENH`), ba cổng (`cong_duyet.CONG`), và văn xuôi trong tài liệu. Bốn
chỗ thì sớm muộn chúng nói khác nhau, và agent đọc trúng chỗ nào thì theo chỗ đó.

Cổng này không thay người đọc. Nó chỉ đảm bảo bản mô tả và bản thi hành **không lệch nhau
trong im lặng** — đúng lớp lỗi mà `test_docs_khong_troi` canh cho văn xuôi.

Tài liệu đi TRƯỚC code là cách hỏng đã có tên trong sổ này: khai một khoá mà engine lặng
lẽ bỏ qua, và không gì báo.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import cong_duyet as CD  # noqa: E402
import tho_viec as TV  # noqa: E402
import tinh_trang as TT  # noqa: E402

DD = ROOT / "knowledge" / "data_model" / "duong_ong.yaml"
SPEC = yaml.safe_load(DD.read_text(encoding="utf-8"))


def test_file_ton_tai_va_doc_duoc():
    assert SPEC and SPEC.get("schema") == "duong_ong/1"


def test_thu_tu_buoc_KHOP_tinh_trang():
    """Sai thứ tự là agent đoán sai bước kế tiếp, và nó đoán rất tự tin."""
    assert [b["ma"] for b in SPEC["buoc"]] == TT.THU_TU


def test_buoc_can_nguoi_KHOP_tinh_trang():
    trong_yaml = {b["ma"] for b in SPEC["buoc"] if b["loai"] == "cong"}
    assert trong_yaml == TT.CAN_NGUOI


def test_ba_cong_KHOP_kho_cong():
    assert tuple(SPEC["cong"]) == CD.CONG


def test_moi_buoc_cong_deu_tro_toi_mot_cong_co_that():
    for b in SPEC["buoc"]:
        if b["loai"] == "cong":
            assert b["cong"] in SPEC["cong"], b["ma"]


def test_lenh_cua_tung_buoc_KHOP_tho_viec():
    """Thợ tra bảng này để biết chạy gì. Mô tả sai thì người sửa nhầm chỗ."""
    trong_yaml = {b["ma"]: b["lenh"] for b in SPEC["buoc"]
                  if b["loai"] == "buoc" and b.get("lenh")}
    assert trong_yaml == TV.LENH


def test_tran_lap_KHOP_tho_viec():
    tran = [b.get("tran_lap") for b in SPEC["buoc"] if b["ma"] == "sua-loi-cong"][0]
    assert tran == TV.TRAN_VIET_LAI


@pytest.mark.parametrize("khoa", ["che_do_chay", "bao_cao_moi_buoc", "noi_giu_trang_thai"])
def test_cac_muc_danh_cho_AGENT_khong_bi_bo_trong(khoa):
    """Ba mục này là thứ agent đọc để biết CÁCH LÀM VIỆC, không phải trang trí.

    Bỏ trống `bao_cao_moi_buoc` thì agent chạy xong không kê file, người không mở được gì
    để kiểm, và cổng duyệt thành con dấu cao su — đúng chỗ Cổng 2 đã dính 11/09/2026.
    """
    assert SPEC.get(khoa), khoa


def test_hai_che_do_chay_deu_duoc_mo_ta_du():
    for ten, cd in SPEC["che_do_chay"].items():
        for khoa in ("ten", "dung_khi", "cach", "nguoi_thay_gi"):
            assert cd.get(khoa), f"{ten} thiếu {khoa}"


# ── Tài liệu hứa lệnh nào thì lệnh đó phải có thật ──────────────────────────

DOC = ROOT / "knowledge" / "toolchains" / "QUY_TRINH_TRONG_PHIEN.md"


RE_KHOI = re.compile(r"```\n(.*?)```", re.S)
RE_NOI_DONG = re.compile(r"\\\s*\n\s+")     # nối dấu gạch chéo xuống dòng của shell
# Chỗ điền của người: `<chiến dịch>`, `"<câu người nói>"`. Bỏ TRƯỚC khi tách token, vì
# chúng có khoảng trắng bên trong nên `split()` xé chúng thành nhiều token rác.
RE_CHO_DIEN = re.compile(r'"?<[^>]*>"?')


def _lenh_trong_doc():
    """Mọi lệnh `python scripts/…` trong khối mã của tài liệu → list token."""
    ra = []
    for khoi in RE_KHOI.findall(DOC.read_text(encoding="utf-8")):
        for dong in RE_NOI_DONG.sub(" ", khoi).splitlines():
            dong = RE_CHO_DIEN.sub("", dong).strip()
            if dong.startswith("python scripts/"):
                ra.append(dong.split())
    return ra


def test_doc_co_it_nhat_vai_lenh():
    """Không có lệnh nào thì hai test dưới luôn xanh mà không đo gì."""
    assert len(_lenh_trong_doc()) >= 3


@pytest.mark.parametrize("lenh", _lenh_trong_doc(), ids=lambda l: l[1])
def test_script_trong_doc_CO_THAT(lenh):
    assert (ROOT / lenh[1]).is_file(), lenh[1]


@pytest.mark.parametrize("lenh", _lenh_trong_doc(), ids=lambda l: " ".join(l[1:3]))
def test_lenh_con_va_co_trong_doc_deu_duoc_CLI_hieu(lenh):
    """Tài liệu đi TRƯỚC code là cách hỏng đã có tên: người gõ theo, CLI báo lỗi lạ.

    So bằng chuỗi thẳng trong mã nguồn script. Không chạy thật vì mấy lệnh này ghi file —
    một cổng kiểm không được có tác dụng phụ lên chiến dịch thật.
    """
    nguon = (ROOT / lenh[1]).read_text(encoding="utf-8")
    # Lệnh con = token ĐẦU TIÊN sau đường dẫn script mà không phải chỗ điền của người
    # (`<chiến dịch>`). Giá trị của cờ thì bỏ qua: `--bai NEN-004` chỉ kiểm `--bai`.
    lenh_con = [t for t in lenh[2:3] if not t.startswith("<")]
    co = [t for t in lenh[2:] if t.startswith("--")]
    for tu in lenh_con:
        assert f'"{tu}"' in nguon, f"{lenh[1]} không có lệnh con {tu}"
    for tu in co:
        assert f'"{tu}"' in nguon, f"{lenh[1]} không có cờ {tu}"
    assert lenh_con or co, f"dòng lệnh không kiểm được gì: {' '.join(lenh)}"
