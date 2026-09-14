# -*- coding: utf-8 -*-
"""Tạo ảnh Facebook qua Codex — không ghi đè ảnh cũ, không tin lời Codex, không đăng ảnh chưa soát.

Cầu thật tốn một lượt Codex và vài phút mỗi ảnh, nên ở đây cầu là bản giả: nó ghi (hoặc
không ghi) một PNG vào đúng chỗ script chỉ định, rồi trả mã thoát như cầu thật.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import make_fb_image as M  # noqa: E402
import md_io  # noqa: E402
import post_paths as PP  # noqa: E402

PROMPT = "Tiêu đề: Prompt là bản vẽ, không phải thần chú. " * 20


def _png(w, h):
    sig = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    return sig + bytes(4) + b"IHDR" + w.to_bytes(4, "big") + h.to_bytes(4, "big") + b"0" * 64


@pytest.fixture
def post(tmp_path):
    d = tmp_path / "NEN-001_bai"
    PP.make_dirs(d)
    PP.p(d, "fb_prompt").write_text(PROMPT, encoding="utf-8")
    cau = tmp_path / "cli.mjs"
    cau.write_text("// cầu giả", encoding="utf-8")
    return d, cau


def _cau_gia(*, ve=(1920, 1080), code=0, ok=True, ghi=True):
    goi = []

    def run(cmd, stdin=None, **kw):
        viec = stdin.read().decode("utf-8")
        goi.append((cmd, viec))
        out = Path(viec.split("đường dẫn:\n", 1)[1].split("\n", 1)[0].strip())
        if ghi and code == 0:
            out.write_bytes(_png(*ve))

        class R:
            returncode = code
            stdout = json.dumps({"ok": ok, "call_id": "C1", "result": '{"path": "x"}',
                                 "code": "autocall_disabled" if code == 2 else None})
            stderr = ""
        return R()
    run.goi = goi
    return run


def test_sinh_anh_chuyen_sang_bai_va_ghi_ho_so_CHUA_SOAT(post):
    d, cau = post
    run = _cau_gia()
    code, kq = M.make(d, cau=cau, run=run)
    assert code == 0 and kq["status"] == "made", kq
    assert M.kich_thuoc_png(PP.p(d, "fb_image")) == (1920, 1080)
    m = json.loads(PP.p(d, "fb_image_meta").read_text(encoding="utf-8"))
    assert m["text_check"]["status"] == "pending", "ảnh vừa sinh không được coi là đã soát"
    cmd, viec = run.goi[0]
    assert "--origin" in cmd and cmd[cmd.index("--origin") + 1] == "human"
    assert cmd[cmd.index("--access") + 1] == "workspace"
    assert PROMPT.strip() in viec, "prompt phải đi NGUYÊN VĂN"
    assert not list((M.REPO / ".tmp" / "fb-images").glob("NEN-001_bai-*")), "để lại rác trong .tmp"


def test_da_co_anh_thi_KHONG_ghi_de(post):
    d, cau = post
    PP.p(d, "fb_image").write_bytes(_png(1920, 1080))
    run = _cau_gia()
    code, kq = M.make(d, cau=cau, run=run)
    assert code == 0 and kq["status"] == "exists"
    assert run.goi == [], "đã gọi Codex dù bài có ảnh — mất một lượt và có thể mất ảnh đã duyệt"


def test_force_sinh_lai_nhung_GIU_anh_cu(post):
    d, cau = post
    PP.p(d, "fb_image").write_bytes(_png(1000, 1000))
    code, _ = M.make(d, cau=cau, run=_cau_gia(), force=True)
    assert code == 0
    cu = list(PP.p(d, "fb_image").parent.glob("infographic.*.old.png"))
    assert len(cu) == 1 and M.kich_thuoc_png(cu[0]) == (1000, 1000)


def test_cau_CHAN_thi_tra_ma_2_va_khong_goi_lai(post):
    d, cau = post
    run = _cau_gia(code=2)
    code, kq = M.make(d, cau=cau, run=run)
    assert code == 2 and kq["status"] == "blocked", kq
    assert len(run.goi) == 1, "mã 2 = bị chặn, gọi lại y hệt cũng bị chặn"
    assert not PP.p(d, "fb_image").exists()


def test_Codex_bao_xong_ma_KHONG_co_file_thi_hong(post):
    """Không tin lời Codex: kiểm đúng file ở đúng chỗ đã chỉ định."""
    d, cau = post
    code, kq = M.make(d, cau=cau, run=_cau_gia(ghi=False))
    assert code == 1 and "không có PNG" in kq["reason"], kq
    assert not PP.p(d, "fb_image_meta").exists()


def test_anh_qua_nho_thi_hong(post):
    d, cau = post
    code, kq = M.make(d, cau=cau, run=_cau_gia(ve=(512, 512)))
    assert code == 1 and "512x512" in kq["reason"], kq


def test_prompt_thieu_hoac_con_cho_trong_thi_KHONG_goi_Codex(post):
    d, cau = post
    run = _cau_gia()
    PP.p(d, "fb_prompt").write_text(PROMPT + "{{TIÊU ĐỀ}}", encoding="utf-8")
    assert M.make(d, cau=cau, run=run)[0] == 3
    PP.p(d, "fb_prompt").write_text("Vẽ ảnh.", encoding="utf-8")
    assert M.make(d, cau=cau, run=run)[0] == 3
    PP.p(d, "fb_prompt").unlink()
    assert M.make(d, cau=cau, run=run)[0] == 3
    assert run.goi == []


# ── soát chữ ────────────────────────────────────────────────────────────────

def test_soat_xong_thi_duoc_dang(post):
    d, cau = post
    M.make(d, cau=cau, run=_cau_gia())
    anh = PP.p(d, "fb_image")
    assert M.trang_thai_soat(anh)[0] is False
    code, _ = M.verify(d, by="Đức", quote="chữ trên ảnh đúng dấu hết")
    assert code == 0 and M.trang_thai_soat(anh)[0] is True


def test_soat_THIEU_nguoi_hoac_cau_noi_thi_khong_ghi(post):
    d, cau = post
    M.make(d, cau=cau, run=_cau_gia())
    assert M.verify(d, by="", quote="ok")[0] == 3
    assert M.verify(d, by="Đức", quote="  ")[0] == 3
    assert M.trang_thai_soat(PP.p(d, "fb_image"))[0] is False


def test_soat_thay_SAI_thi_khong_duoc_dang(post):
    d, cau = post
    M.make(d, cau=cau, run=_cau_gia())
    M.verify(d, by="Đức", quote="vùng 2 sai dấu chữ 'khoá'", failed=True)
    ok, why = M.trang_thai_soat(PP.p(d, "fb_image"))
    assert ok is False and "failed" in why


def test_anh_bi_DOI_sau_khi_soat_thi_khong_duoc_dang(post):
    """Byte đem đăng phải là byte đã soát."""
    d, cau = post
    M.make(d, cau=cau, run=_cau_gia())
    M.verify(d, by="Đức", quote="đúng dấu")
    PP.p(d, "fb_image").write_bytes(_png(1920, 1080) + b"sua-tay")
    ok, why = M.trang_thai_soat(PP.p(d, "fb_image"))
    assert ok is False and "đổi SAU khi soát" in why


def test_prompt_DOI_sau_khi_sinh_anh_thi_khong_cho_soat(post):
    d, cau = post
    M.make(d, cau=cau, run=_cau_gia())
    PP.p(d, "fb_prompt").write_text(PROMPT + " Thêm một thẻ.", encoding="utf-8")
    code, kq = M.verify(d, by="Đức", quote="đúng")
    assert code == 1 and "prompt đã đổi" in kq["reason"], kq


def test_nguong_prompt_la_MOT_hang_so_voi_G24():
    import blog_gates as G
    assert M.PROMPT_ANH_TOI_THIEU is G.PROMPT_ANH_TOI_THIEU


# ── ghi nguyên tử chịu được Windows giữ file ─────────────────────────────────

def test_ghi_chung_THU_LAI_khi_Windows_giu_file(tmp_path, monkeypatch):
    that = md_io.os.replace
    lan = {"n": 0}

    def ban_giu(src, dst):
        lan["n"] += 1
        if lan["n"] < 3:
            raise PermissionError(5, "Access is denied")
        return that(src, dst)
    monkeypatch.setattr(md_io.os, "replace", ban_giu)
    monkeypatch.setattr(md_io, "_SLEEP", lambda s: None)
    md_io.write_atomic(tmp_path / "a.json", "{}")
    assert (tmp_path / "a.json").read_text(encoding="utf-8") == "{}" and lan["n"] == 3


def test_ghi_chung_qua_tran_thi_VAN_NEM_loi_va_don_file_tam(tmp_path, monkeypatch):
    def luon_giu(src, dst):
        raise PermissionError(5, "Access is denied")
    monkeypatch.setattr(md_io.os, "replace", luon_giu)
    monkeypatch.setattr(md_io, "_SLEEP", lambda s: None)
    with pytest.raises(PermissionError):
        md_io.write_atomic(tmp_path / "a.json", "{}")
    assert list(tmp_path.iterdir()) == [], "để lại file .tmp"
