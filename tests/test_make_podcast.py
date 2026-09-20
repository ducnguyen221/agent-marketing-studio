# -*- coding: utf-8 -*-
"""`make_podcast.py` sau khi chuyển sang gọi TRẠM GIỌNG qua adapter (P2-T12).

Hai thứ đáng canh nhất, và cả hai đều là bài học đã trả giá:

1. **Không còn đường lùi vào bố cục của một máy.** Bản trước nhét thư mục engine của máy
   chủ repo vào `sys.path`. Repo này công khai; một đường dẫn của một máy nằm trong mã
   nghĩa là mọi người khác chạy vào hư không, và thông báo lỗi không nói được phải cài gì.
2. **Không còn tên giọng mặc định.** Tên profile là danh tính của người dùng.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import make_podcast as MP  # noqa: E402
import studio_contract as SC  # noqa: E402

KICH_BAN = """# Tiêu đề

Đoạn **một** có `code` và
xuống dòng giữa chừng.

Đoạn hai.
"""


@pytest.fixture
def giong(tmp_path, monkeypatch):
    """Thay `voice.speak` bằng một bản ghi sổ — ranh giới tiến trình đã có cổng riêng
    (`test_voice_adapter.py`); ở đây cần đo cái make_podcast GỬI ĐI."""
    da_goi = {}

    def speak(text=None, *, file=None, out, profile=None, lang=None, **kw):
        da_goi.update(text=text, file=file, out=out, profile=profile, lang=lang,
                      noi_dung=Path(file).read_text(encoding="utf-8") if file else None)
        Path(out).write_bytes(b"ID3")
        return {"ok": True, "outputs": [{"kind": "audio", "path": str(out), "duration": 9.0}]}

    monkeypatch.setattr(MP.VOICE, "speak", speak)
    return da_goi


def _kich(tmp_path, noi_dung=KICH_BAN):
    f = tmp_path / "script.txt"
    f.write_text(noi_dung, encoding="utf-8")
    return f


def test_goi_tram_giong_DUNG_MOT_LAN_cho_ca_bai(giong, tmp_path):
    """Một lần gọi = một lần nạp model. Gọi từng đoạn là nạp model 3 GB từng đoạn."""
    ra = MP.make_podcast(KICH_BAN, str(tmp_path / "audio.mp3"))
    assert ra["outputs"][0]["duration"] == 9.0
    assert giong["out"].endswith("audio.mp3")


def test_gui_qua_FILE_chu_khong_qua_tham_so_dong_lenh(giong, tmp_path):
    """Bài dài vượt giới hạn dòng lệnh Windows (~32 000 ký tự); lỗi khi đó hiện ra là
    "tham số sai" và không ai lần ra nguyên nhân."""
    MP.make_podcast(KICH_BAN, str(tmp_path / "audio.mp3"))
    assert giong["file"] and giong["text"] is None


def test_markdown_bi_go_truoc_khi_doc(giong, tmp_path):
    MP.make_podcast(KICH_BAN, str(tmp_path / "audio.mp3"))
    doc = giong["noi_dung"]
    for dau in ("**", "`", "#"):
        assert dau not in doc, doc
    assert "Đoạn một có code và xuống dòng giữa chừng." in doc      # gộp dòng trong đoạn
    assert "\n\n" in doc                                            # giữ ranh giới đoạn


def test_khong_khai_profile_thi_KHONG_tu_dien_ten_nao(giong, tmp_path):
    MP.make_podcast(KICH_BAN, str(tmp_path / "audio.mp3"))
    assert giong["profile"] is None


def test_kich_ban_rong_la_ma_2(giong, tmp_path):
    with pytest.raises(SC.ContractError):
        MP.make_podcast("   \n\n  ", str(tmp_path / "audio.mp3"))


def test_CLI_in_dong_OK_va_ma_0(giong, tmp_path, capsys):
    ma = MP.main(["--script", str(_kich(tmp_path)), "--out", str(tmp_path / "audio.mp3")])
    out, _ = capsys.readouterr()
    assert ma == SC.OK
    assert out.strip().splitlines()[-1].startswith("OK ")


def test_CLI_json_tra_mot_dong_JSON_cuoi(giong, tmp_path, capsys):
    ma = MP.main(["--script", str(_kich(tmp_path)), "--out", str(tmp_path / "audio.mp3"),
                  "--json"])
    out, _ = capsys.readouterr()
    assert ma == SC.OK
    assert json.loads(out.strip().splitlines()[-1])["ok"] is True


def test_CLI_thieu_kich_ban_la_ma_2(giong, tmp_path, capsys):
    assert MP.main(["--script", str(tmp_path / "khong-co.txt"),
                    "--out", str(tmp_path / "a.mp3")]) == SC.CONTRACT_ERROR


def test_CHUA_CAI_TRAM_GIONG_la_ma_3_kem_huong_dan(tmp_path, monkeypatch, capsys):
    """Fail-closed: không có trạm giọng thì DỪNG với lời chỉ đúng việc phải làm."""
    for b in ("VOICE_STATION", "OMNIVOICE_DIR", "OMNIVOICE_PY", "MARKETING_STUDIO_HOME"):
        monkeypatch.delenv(b, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(tmp_path))
    ma = MP.main(["--script", str(_kich(tmp_path)), "--out", str(tmp_path / "a.mp3")])
    _, err = capsys.readouterr()
    assert ma == SC.STATION_MISSING
    assert "agent-voice-studio" in err and "clone" in err


def test_KHONG_con_duong_dan_cua_mot_may_trong_scripts():
    """Cổng của gói P2-G3: `grep '.tts' scripts/` phải bằng 0."""
    xau = []
    for p in (ROOT / "scripts").rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        t = p.read_text(encoding="utf-8")
        for mau in (chr(46) + "tts", chr(46) + "news", chr(46) + "video" + chr(47)):
            if mau in t:
                xau.append(f"{p.relative_to(ROOT).as_posix()}: {mau}")
    assert not xau, "còn bố cục của một máy trong scripts/:\n  " + "\n  ".join(xau)


def test_khong_con_import_engine_cua_tram_giong():
    """`import mcp_server` / `import voice_profiles` là cách cũ: nạp module private của
    một máy. Cả `scripts/` phải sạch, không riêng file này."""
    xau = []
    for p in (ROOT / "scripts").rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        t = p.read_text(encoding="utf-8")
        for mau in ("import mcp_server", "import voice_profiles"):
            if mau in t:
                xau.append(f"{p.relative_to(ROOT).as_posix()}: {mau}")
    assert not xau, xau


def test_chay_that_bang_dong_lenh_khong_can_torch(tmp_path, monkeypatch):
    """`--help` phải chạy được trên máy chưa cài gì cả — nếu nó đòi torch thì tài liệu
    hướng dẫn chạy nó cũng vô dụng."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline" / "make_podcast.py"),
                        "--help"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == SC.OK, r.stderr
