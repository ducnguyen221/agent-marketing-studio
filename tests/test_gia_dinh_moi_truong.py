# -*- coding: utf-8 -*-
"""Cổng chống GIẢ ĐỊNH MÔI TRƯỜNG — "máy nào chả có sẵn thứ đó".

Bốn lần đỏ trong 24 giờ (19–20/09/2026), cùng một hình dạng: mã chạy đúng trên máy đã
dựng nó, và hỏng trên máy sạch vì nó cho rằng môi trường có sẵn một thứ mà nó không tự
mang theo.

  1. dấu phân cách đường dẫn là `\\`            → hỏng trên macOS
  2. nguồn và đích luôn cùng một ổ đĩa          → hỏng trên Windows CI (runner hai ổ)
  3. `D:` luôn là một đường tuyệt đối           → hỏng trên POSIX
  4. hệ điều hành có sẵn dữ liệu múi giờ IANA   → hỏng trên Windows (CI 20/09)

Lần thứ tư là lần tốn nhất, không phải vì nó khó sửa mà vì nó **câm hai tầng**: máy của
người dựng có `tzdata` do một gói khác kéo về, nên không ai thấy; và khi thiếu thật thì
`agent_call._tz` lặng lẽ lùi về giờ máy và trả ra `+00:00` thay cho `+07:00` — một giờ
mở lại SAI 7 tiếng, không kèm một dòng cảnh báo nào.

Nên file này giữ ba thứ, và cả ba đều nhắm vào "câm":

  · thứ mã cần thì phải KHAI trong `requirements.txt`, không dựa vào máy có sẵn;
  · thiếu nó thì thông điệp phải nói TÊN GÓI và LỆNH CÀI, không ném tên lớp exception;
  · lùi-về-mặc-định mà làm kết quả SAI thì phải kêu, hoặc không trả gì cả.

Những giả định cùng họ đã rà mà KHÔNG cần cổng mới ở đây (chúng đã có chỗ canh riêng):
`ffmpeg`/`ffprobe` (`media_tools.ff_tool` + `blog_gates` trả "thiếu" chứ không trả 0),
Chrome (`media_tools.chrome`, `test_media_tools.py`), mã hoá mặc định của terminal
(`tests/conftest.py` + `test_no_env_dependency.py`), và `git` (`station.py` hỏi
`shutil.which` trước khi gọi).
"""
from __future__ import annotations

import ast
import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# THỨ TỰ CÓ Ý NGHĨA: `scripts/pipeline` có một `agent_call.py` TRÙNG TÊN (CLI mỏng). Nó
# phải nằm SAU `scripts/lib`, nếu không `import agent_call` nạp nhầm CLI và cả file này
# kiểm một module khác với module nó tưởng (đã dính đúng một lần khi viết file này).
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

import agent_call as AC  # noqa: E402
import doctor as DR  # noqa: E402
import studio_contract as SC  # noqa: E402

REQ = ROOT / "requirements.txt"


def _khai_requirements() -> dict[str, str]:
    """`requirements.txt` -> {tên gói chữ thường: dòng nguyên văn}."""
    ra = {}
    for dong in REQ.read_text(encoding="utf-8").splitlines():
        than = dong.split("#", 1)[0].strip()
        if not than:
            continue
        ten = re.split(r"[<>=!~;\[\s]", than, 1)[0].strip().lower()
        if ten:
            ra[ten] = dong
    return ra


# ── 1. Thứ mã cần thì phải KHAI, không dựa vào máy có sẵn ───────────────────────────

def test_tzdata_duoc_khai_la_phu_thuoc_that():
    """Không có dòng này thì máy sạch nào cũng đỏ, và chỉ CI mới biết.

    `zoneinfo` nạp `tzdata` NGẦM (không `import tzdata` ở đâu trong repo), nên cổng quét
    import ở dưới không thể thấy nó — phải khai đích danh ở đây.
    """
    khai = _khai_requirements()
    assert "tzdata" in khai, (
        "`requirements.txt` chưa khai `tzdata`. Windows không kèm dữ liệu múi giờ IANA, "
        "nên `ZoneInfo('Asia/Ho_Chi_Minh')` nổ `ZoneInfoNotFoundError` trên mọi máy sạch.")


def test_tzdata_khai_KHONG_kem_dieu_kien_nen_tang():
    """`tzdata; platform_system == "Windows"` vá đúng CHỖ ĐÃ ĐỎ, và đẻ ra giả định kế tiếp.

    Cái điều kiện đó khẳng định "mọi máy không-Windows đều có sẵn dữ liệu múi giờ của hệ"
    — sai với container Linux slim, sai với mọi bản gọt, và đúng kiểu câu đã làm đỏ CI bốn
    lần. Gói là 350 KB dữ liệu thuần: khai thẳng rẻ hơn lần đỏ thứ năm.

    Đổi ý thì đổi ở đây, nhưng phải đổi có chủ đích — đó chính là việc của cổng này.
    """
    dong = _khai_requirements()["tzdata"]
    assert ";" not in dong.split("#", 1)[0], (
        f"dòng tzdata đang có điều kiện nền tảng: {dong.strip()!r} — xem docstring.")


def test_moi_goi_ngoai_ma_scripts_import_deu_duoc_khai():
    """Quét `import` của `scripts/**` và đòi mỗi gói bên thứ ba có mặt trong requirements.

    Cùng một bài học ở tầng rộng hơn: một `import` không khai là một giả định rằng máy
    người khác tình cờ cũng có gói đó. Trước 04/09 repo không khai gì cả và ai clone về
    phải tự đoán — cổng này giữ cho chuyện đó không quay lại từng gói một.
    """
    noi_bo = {p.stem for p in (ROOT / "scripts").rglob("*.py")}
    # Hai trạm năng lực KHÔNG cài qua `requirements.txt` (không lên PyPI, cài `-e` vào venv
    # của trạm giọng) — `requirements-voice/video.txt` chỉ khai NGƯỠNG cho `doctor`.
    ngoai_le = {"voice_studio", "video_studio"}
    khai = set(_khai_requirements())
    # Tên `import` ≠ tên gói pip. Thiếu bảng này thì cổng bắt oan `PIL` và `yaml`.
    bi_danh = {"PIL": "pillow", "yaml": "pyyaml"}

    thieu = {}
    for f in sorted((ROOT / "scripts").rglob("*.py")):
        cay = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Import):
                ten = [a.name.split(".")[0] for a in nut.names]
            elif isinstance(nut, ast.ImportFrom):
                ten = [nut.module.split(".")[0]] if nut.module and not nut.level else []
            else:
                continue
            for t in ten:
                if (t in sys.stdlib_module_names or t in noi_bo or t in ngoai_le
                        or bi_danh.get(t, t).lower() in khai):
                    continue
                thieu.setdefault(bi_danh.get(t, t), set()).add(
                    str(f.relative_to(ROOT)).replace("\\", "/"))

    assert not thieu, ("gói bên thứ ba được import mà KHÔNG khai trong requirements.txt: "
                       + "; ".join(f"{k} ({', '.join(sorted(v))})" for k, v in sorted(thieu.items())))


# ── 2. Thiếu dữ liệu múi giờ: thông điệp phải nói cần cài gì ────────────────────────

def test_may_chay_test_PHAI_co_du_lieu_mui_gio():
    """Cổng đứng TRƯỚC mọi test dùng `ZoneInfo`.

    Thiếu dữ liệu thì đỏ ở ĐÂY, kèm đúng lệnh phải gõ — thay vì đỏ ở ba test khác bằng
    `ModuleNotFoundError: No module named 'tzdata'`, dòng lỗi mà CI Windows đã in hai lần
    và không nói cho ai biết phải làm gì.
    """
    assert AC._co_du_lieu_mui_gio(), AC.THIEU_TZ.format(ten="Asia/Ho_Chi_Minh")
    from zoneinfo import ZoneInfo
    lech = ZoneInfo("Asia/Ho_Chi_Minh").utcoffset(datetime(2026, 9, 21)).total_seconds()
    assert lech == 7 * 3600, "dữ liệu múi giờ có nhưng sai: Asia/Ho_Chi_Minh phải là +07:00"


@pytest.fixture
def may_trong_mui_gio(monkeypatch):
    """Giả lập máy Windows sạch: `zoneinfo` không thấy múi giờ nào, không có gói `tzdata`."""
    import zoneinfo

    def khong_thay(key, *a, **k):
        raise zoneinfo.ZoneInfoNotFoundError(f"No time zone found with key {key}")

    monkeypatch.setattr(zoneinfo, "ZoneInfo", khong_thay)
    monkeypatch.setattr(AC, "_co_du_lieu_mui_gio", lambda: False)


def test_thieu_du_lieu_mui_gio_thi_noi_ro_phai_cai_gi(may_trong_mui_gio):
    with pytest.raises(AC.ThieuDuLieuMuiGio) as e:
        AC._tz("Asia/Ho_Chi_Minh")
    msg = str(e.value)
    assert "tzdata" in msg, "thông điệp phải nói TÊN GÓI"
    assert "pip install" in msg, "thông điệp phải nói LỆNH CÀI"
    assert "Asia/Ho_Chi_Minh" in msg, "thông điệp phải nói múi giờ nào đang hỏng"
    # Thứ KHÔNG được là toàn bộ câu trả lời: tên lớp exception của thư viện. Người đọc nó
    # không biết `tzdata` là gói pip hay là thư mục của Windows.
    assert "ZoneInfoNotFoundError" not in msg


def test_thieu_du_lieu_mui_gio_thi_KHONG_TRA_GIO_SAI(may_trong_mui_gio, capsys):
    """Đúng con số CI Windows đã in: `2026-09-21T19:50:00+00:00` — lệch 7 tiếng.

    Một `resets_at` sai còn tệ hơn không có: mã 4 bảo lịch "đợi tới giờ X", và lịch sẽ
    ngoan ngoãn đợi tới một thời điểm vô nghĩa rồi lại đâm vào đúng bức tường hạn mức.
    """
    assert AC.parse_resets("resets 7:50pm (Asia/Ho_Chi_Minh)") is None
    loi = capsys.readouterr().err
    assert "tzdata" in loi and "pip install" in loi, "im lặng trả None cũng là câm"


def test_ten_mui_gio_LA_thi_van_lui_ve_gio_may():
    """Có dữ liệu mà tên không tra được ⇒ lỗi nằm ở DÒNG CHỮ engine in ra, không nằm ở bản
    cài. Lùi về giờ máy, và KHÔNG bảo người dùng đi cài gì — bảo thế là bắt oan."""
    assert AC._tz("Cõi/Tiên_Giới") is not None
    assert AC.parse_resets("resets 7:50pm (Cõi/Tiên_Giới)") is not None


def test_ISO_co_san_khong_can_du_lieu_mui_gio(may_trong_mui_gio):
    """Đường không chạm `zoneinfo` thì không được chết theo."""
    assert AC.parse_resets("reset at 2026-09-24T03:30:00Z") == "2026-09-24T03:30:00Z"


# ── 3. `doctor` phải hỏi máy đang chạy ──────────────────────────────────────────────

def test_doctor_NHAC_khi_may_thieu_du_lieu_mui_gio(monkeypatch):
    """NHẮC chứ không THIẾU: bản cài không có `tzdata` vẫn viết bài và vẫn đăng được.

    Cùng luật với phân tầng năng lực — chỉ LÕI hỏng mới được làm đỏ cả bản cài.
    """
    monkeypatch.setattr(AC, "_co_du_lieu_mui_gio", lambda: False)
    so = DR.So()
    DR._kham_du_lieu_mui_gio(so)
    assert so.code == SC.OK, "thiếu dữ liệu múi giờ không được làm đỏ cả bản cài"
    assert any("tzdata" in w and "pip install" in w for w in so.warn), so.warn


def test_doctor_im_lang_khi_may_co_du_lieu_mui_gio(monkeypatch):
    monkeypatch.setattr(AC, "_co_du_lieu_mui_gio", lambda: True)
    so = DR.So()
    DR._kham_du_lieu_mui_gio(so)
    assert so.warn == [] and so.fail == []


# ── 4. Font: cùng họ, cùng kiểu câm ─────────────────────────────────────────────────

def test_thieu_font_thi_ANH_VAN_RA_nhung_phai_keu(tmp_path, monkeypatch, capsys):
    """`ImageFont.load_default()` không ném lỗi — nó vẽ bằng font bitmap không có dấu
    tiếng Việt. Ảnh vẫn ra, đường ống vẫn xanh, chỉ có chữ là sai; im lặng ở đây nghĩa là
    người dùng phát hiện khi nhìn ảnh ĐÃ ĐĂNG."""
    pytest.importorskip("PIL")
    import gen_infographic as GI

    monkeypatch.setattr(GI.MT, "font_candidates", lambda bold=True: ["/khong/he/co/x.ttf"])
    ra = tmp_path / "a.png"
    GI.render_pillow("Tiêu đề có dấu", ["một ý"], {},
                     str(ra), {"site_name": "Thử", "home_domain": "vi.du"})
    assert ra.is_file(), "thiếu font không được làm hỏng bước dựng ảnh"
    loi = capsys.readouterr().err
    assert "VIDEO_FONT" in loi and "MẤT DẤU" in loi, loi
