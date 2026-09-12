# -*- coding: utf-8 -*-
"""Cổng canh: `knowledge/data_model/pipeline.yaml` phải KHỚP với code đang chạy.

Đường ống được mô tả ở bốn chỗ — thứ tự trạng thái (`pipeline_state.ORDER`), bước nào chạy
lệnh nào (`worker.COMMANDS`), ba cổng (`approval_gate.GATES`), và văn xuôi trong tài liệu. Bốn
chỗ thì sớm muộn chúng nói khác nhau, và agent đọc trúng chỗ nào thì theo chỗ đó.

Cổng này không thay người đọc. Nó chỉ đảm bảo bản mô tả và bản thi hành **không lệch nhau
trong im lặng** — đúng lớp lỗi mà `test_docs_drift` canh cho văn xuôi.

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
import approval_gate as AG  # noqa: E402
import worker as WK  # noqa: E402
import pipeline_state as PS  # noqa: E402

DD = ROOT / "knowledge" / "data_model" / "pipeline.yaml"
SPEC = yaml.safe_load(DD.read_text(encoding="utf-8"))


def test_file_ton_tai_va_doc_duoc():
    assert SPEC and SPEC.get("schema") == "pipeline/1"


def test_thu_tu_buoc_KHOP_pipeline_state():
    """Sai thứ tự là agent đoán sai bước kế tiếp, và nó đoán rất tự tin."""
    assert [b["id"] for b in SPEC["step"]] == PS.ORDER


def test_buoc_can_nguoi_KHOP_pipeline_state():
    trong_yaml = {b["id"] for b in SPEC["step"] if b["kind"] == "gate"}
    assert trong_yaml == PS.NEEDS_HUMAN


def test_ba_cong_KHOP_kho_cong():
    assert tuple(SPEC["gate"]) == AG.GATES


def test_moi_buoc_cong_deu_tro_toi_mot_cong_co_that():
    for b in SPEC["step"]:
        if b["kind"] == "gate":
            assert b["gate"] in SPEC["gate"], b["id"]


def test_lenh_cua_tung_buoc_KHOP_worker():
    """Thợ tra bảng này để biết chạy gì. Mô tả sai thì người sửa nhầm chỗ."""
    trong_yaml = {b["id"]: b["cmd"] for b in SPEC["step"]
                  if b["kind"] == "step" and b.get("cmd")}
    assert trong_yaml == WK.COMMANDS


def test_tran_lap_KHOP_worker():
    tran = [b.get("max_rewrites") for b in SPEC["step"] if b["id"] == "fix-gates"][0]
    assert tran == WK.MAX_REWRITES


@pytest.mark.parametrize("khoa", ["run_modes", "report_each_step", "state_lives_in"])
def test_cac_muc_danh_cho_AGENT_khong_bi_bo_trong(khoa):
    """Ba mục này là thứ agent đọc để biết CÁCH LÀM VIỆC, không phải trang trí.

    Bỏ trống `bao_cao_moi_buoc` thì agent chạy xong không kê file, người không mở được gì
    để kiểm, và cổng duyệt thành con dấu cao su — đúng chỗ Cổng 2 đã dính 11/09/2026.
    """
    assert SPEC.get(khoa), khoa


def test_hai_che_do_chay_deu_duoc_mo_ta_du():
    for name, cd in SPEC["run_modes"].items():
        for khoa in ("name", "use_when", "how", "user_sees"):
            assert cd.get(khoa), f"{name} thiếu {khoa}"


# ── Tài liệu hứa lệnh nào thì lệnh đó phải có thật ──────────────────────────

DOC = ROOT / "knowledge" / "toolchains" / "IN_SESSION_PIPELINE.md"


RE_KHOI = re.compile(r"```\n(.*?)```", re.S)
RE_NOI_DONG = re.compile(r"\\\s*\n\s+")     # nối dấu gạch chéo xuống dòng của shell
# Chỗ điền của người: `<chiến dịch>`, `"<câu người nói>"`. Bỏ TRƯỚC khi tách token, vì
# chúng có khoảng trắng bên trong nên `split()` xé chúng thành nhiều token rác.
RE_CHO_DIEN = re.compile(r'"?<[^>]*>"?')


def _lenh_trong_doc():
    """Mọi lệnh `python scripts/…` trong khối mã của tài liệu → list token."""
    ra = []
    for khoi in RE_KHOI.findall(DOC.read_text(encoding="utf-8")):
        for row in RE_NOI_DONG.sub(" ", khoi).splitlines():
            row = RE_CHO_DIEN.sub("", row).strip()
            if row.startswith("python scripts/"):
                ra.append(row.split())
    return ra


def test_doc_co_it_nhat_vai_lenh():
    """Không có lệnh nào thì hai test dưới luôn xanh mà không đo gì."""
    assert len(_lenh_trong_doc()) >= 3


@pytest.mark.parametrize("cmd", _lenh_trong_doc(), ids=lambda l: l[1])
def test_script_trong_doc_CO_THAT(cmd):
    assert (ROOT / cmd[1]).is_file(), cmd[1]


@pytest.mark.parametrize("cmd", _lenh_trong_doc(), ids=lambda l: " ".join(l[1:3]))
def test_lenh_con_va_co_trong_doc_deu_duoc_CLI_hieu(cmd):
    """Tài liệu đi TRƯỚC code là cách hỏng đã có tên: người gõ theo, CLI báo lỗi lạ.

    So bằng chuỗi thẳng trong mã nguồn script. Không chạy thật vì mấy lệnh này ghi file —
    một cổng kiểm không được có tác dụng phụ lên chiến dịch thật.
    """
    source = (ROOT / cmd[1]).read_text(encoding="utf-8")
    # Lệnh con = token ĐẦU TIÊN sau đường dẫn script mà không phải chỗ điền của người
    # (`<chiến dịch>`). Giá trị của cờ thì bỏ qua: `--post NEN-004` chỉ kiểm `--post`.
    lenh_con = [t for t in cmd[2:3] if not t.startswith("<")]
    co = [t for t in cmd[2:] if t.startswith("--")]
    for tu in lenh_con:
        assert f'"{tu}"' in source, f"{cmd[1]} không có lệnh con {tu}"
    for tu in co:
        assert f'"{tu}"' in source, f"{cmd[1]} không có cờ {tu}"
    assert lenh_con or co, f"dòng lệnh không kiểm được gì: {' '.join(cmd)}"
