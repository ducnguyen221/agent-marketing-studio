# -*- coding: utf-8 -*-
"""`scripts/runners/notify_run.py` — wrapper báo Telegram cho lịch chạy trên máy KHÔNG có
Windows PowerShell 5.1 (macOS/launchd), cùng hợp đồng với `notify-run.ps1` của máy tác giả.

Vì sao mỗi nhóm test dưới đây tồn tại — mỗi cái chặn một cách hỏng cụ thể:

· **Mã thoát phải là mã của lệnh con, nguyên vẹn.** Bộ lập lịch (launchd, Task Scheduler)
  chỉ nhìn mã thoát. Wrapper nuốt mã 2 thành 0 là lịch báo "ổn" cho một lượt hỏng cấu hình;
  đổi 3 thành 1 là người sửa đi tìm lỗi render trong khi thứ thiếu là cả một trạm.
· **✅ phải kèm MỌI link sản phẩm; ❌ phải nói hỏng ở bước nào, đã xong bước nào.** Đó là
  luật báo cáo của máy tác giả — tin ✅ không link bắt người mở YouTube ra tìm; tin ❌ không
  bước bắt người mở log lúc 5 giờ sáng.
· **Thiếu cấu hình Telegram thì nói rõ, không lộ token, không làm hỏng lượt chạy.**
  Token chỉ sống trong file secret; wrapper không bao giờ in nó, kể cả trong thông báo lỗi.

KHÔNG test nào ở đây chạm mạng: lớp mạng của `telegram_io` bị thay bằng bản giả, và
`urllib.request.urlopen` bị gài để NỔ nếu có gì lọt qua. Cấu hình Telegram là file giả trong
thư mục tạm; `HOME` bị trỏ vào thư mục tạm để đường mặc định `~/.secret/…` không bao giờ
trỏ vào kho secret thật của máy chạy test.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "runners" / "notify_run.py"
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "runners"))
import telegram_io as tg  # noqa: E402
import notify_run as NR  # noqa: E402

PY = sys.executable
TOKEN_GIA = "123456789:AAFakeTokenChiDungTrongTestKhongThat_x"


class MangGia:
    """Thay `telegram_io._goi_that`. Ghi lại mọi lượt gọi."""

    def __init__(self, tra_ve=None, no=None):
        self.lan = []
        self._tra_ve = tra_ve or {"ok": True, "result": {"message_id": 7}}
        self._no = no

    def __call__(self, token, method, payload):
        self.lan.append((token, method, dict(payload)))
        if self._no:
            raise self._no
        return self._tra_ve

    @property
    def tin(self) -> str:
        assert self.lan, "không có tin nào được gửi"
        return self.lan[-1][2]["text"]


@pytest.fixture(autouse=True)
def _cach_ly(tmp_path, monkeypatch):
    """Nhà giả + chặn mạng + gỡ mọi biến Telegram thật của máy chạy test."""
    nha = tmp_path / "nha"
    nha.mkdir()
    monkeypatch.setenv("HOME", str(nha))
    monkeypatch.setenv("USERPROFILE", str(nha))
    for k in ("TG_CONFIG", "TG_CHAT", "TG_BOT_TOKEN", "TG_CHAT_ID"):
        monkeypatch.delenv(k, raising=False)

    def _cam_mang(*a, **k):
        raise AssertionError("test định gọi mạng thật — cấm")
    monkeypatch.setattr(urllib.request, "urlopen", _cam_mang)


@pytest.fixture
def cau_hinh(tmp_path, monkeypatch):
    p = tmp_path / "tg" / "config.json"
    p.parent.mkdir()
    p.write_text(json.dumps({"bot_token": TOKEN_GIA,
                             "chats": {"mac_dinh": {"chat_id": 4242}}}), encoding="utf-8")
    monkeypatch.setenv("TG_CONFIG", str(p))
    return p


@pytest.fixture
def mang(monkeypatch):
    m = MangGia()
    monkeypatch.setattr(tg, "_goi_that", m)
    return m


def _py(code: str) -> list[str]:
    return ["--", PY, "-c", code]


# ── (a) ✅ + link ─────────────────────────────────────────────────────────────

def test_OK_tin_co_dau_tick_tieu_de_va_link(cau_hinh, mang, capsys):
    ma = NR.main(["--title", "Daily Hot AI 6PM",
                  *_py("print('=== Publishing'); print('YouTube: https://youtu.be/abc123.')")])
    assert ma == 0
    assert len(mang.lan) == 1
    token, method, p = mang.lan[0]
    assert method == "sendMessage" and p["chat_id"] == 4242 and p["parse_mode"] == "HTML"
    assert token == TOKEN_GIA
    t = mang.tin
    assert t.startswith("✅")
    assert "Daily Hot AI 6PM" in t
    assert "https://youtu.be/abc123" in t
    assert "https://youtu.be/abc123." not in t, "dấu chấm cuối câu phải bị cắt khỏi link"


def test_OK_gom_MOI_link_khong_trung(cau_hinh, mang):
    code = ("print('https://www.youtube.com/watch?v=AAA');"
            "print('https://youtube.com/shorts/BBB');"
            "print('lai: https://www.youtube.com/watch?v=AAA');"
            "print('fb (https://www.facebook.com/123/posts/456).');"
            "print('https://fb.watch/xyz/')")
    assert NR.main(["--title", "T", *_py(code)]) == 0
    t = mang.tin
    for l in ("https://www.youtube.com/watch?v=AAA", "https://youtube.com/shorts/BBB",
              "https://www.facebook.com/123/posts/456", "https://fb.watch/xyz/"):
        assert l in t
    assert t.count("watch?v=AAA") == 1
    assert "posts/456)" not in t, "ngoặc/dấu chấm dính đuôi link phải bị cắt"


def test_OK_khong_link_thi_noi_ro(cau_hinh, mang):
    assert NR.main(["--title", "T", *_py("print('xong')")]) == 0
    assert "không phát hiện link" in mang.tin


def test_link_domains_them_mien_rieng_cua_thuong_hieu(cau_hinh, mang):
    code = ("print('bai: https://blog.example.com/2026/09/bai-a.html');"
            "print('la: https://khac.example.org/x')")
    assert NR.main(["--title", "T", "--link-domains", "blog.example.com, news.example.net",
                    *_py(code)]) == 0
    t = mang.tin
    assert "https://blog.example.com/2026/09/bai-a.html" in t
    assert "khac.example.org" not in t, "miền không khai thì không phải link sản phẩm"


def test_link_domains_khong_khai_thi_khong_bat_mien_la(cau_hinh, mang):
    assert NR.main(["--title", "T", *_py("print('https://blog.example.com/a')")]) == 0
    assert "blog.example.com" not in mang.tin


# ── (b) ❌ + bước + mã thoát nguyên vẹn ───────────────────────────────────────

@pytest.mark.parametrize("ma_con", [0, 1, 2, 3])
def test_ma_thoat_bang_ma_con(cau_hinh, mang, ma_con):
    assert NR.main(["--title", "T", *_py(f"import sys; sys.exit({ma_con})")]) == ma_con


def test_FAIL_tin_co_dau_x_buoc_hong_va_buoc_da_xong(cau_hinh, mang):
    code = ("import sys;"
            "print('=== Buoc 1: nghien cuu');"
            "print('Rendering video');"
            "print('Uploading YouTube');"
            "print('Traceback (most recent call last):');"
            "print('RuntimeError: quota het');"
            "sys.exit(2)")
    assert NR.main(["--title", "Daily Hot Data 7PM", *_py(code)]) == 2
    t = mang.tin
    assert t.startswith("❌")
    assert "Daily Hot Data 7PM" in t and "exit 2" in t
    assert "Hỏng ở bước" in t and "Uploading YouTube" in t
    assert "Đã xong" in t and "=== Buoc 1: nghien cuu" in t and "Rendering video" in t
    assert "RuntimeError: quota het" in t, "không có composer thì phải kèm log đuôi"


def test_FAIL_stderr_cua_lenh_con_vao_log(cau_hinh, mang):
    code = "import sys; sys.stderr.write('loi o stderr\\n'); sys.exit(1)"
    assert NR.main(["--title", "T", *_py(code)]) == 1
    assert "loi o stderr" in mang.tin


def test_FAIL_lenh_khong_ton_tai(cau_hinh, mang):
    ma = NR.main(["--title", "T", "--", "lenh-khong-he-ton-tai-xyz"])
    assert ma == 1
    t = mang.tin
    assert t.startswith("❌") and "lenh-khong-he-ton-tai-xyz" in t


def test_thieu_lenh_con_la_loi_dung_lenh():
    with pytest.raises(SystemExit) as e:
        NR.main(["--title", "T"])
    assert e.value.code == 2


def test_tieu_de_duoc_escape_html(cau_hinh, mang):
    assert NR.main(["--title", "A <b>&</b>", *_py("pass")]) == 0
    assert "A &lt;b&gt;&amp;&lt;/b&gt;" in mang.tin


def test_output_lenh_con_van_in_ra_stdout_cho_log_cua_bo_lap_lich(cau_hinh, mang, capsys):
    NR.main(["--title", "T", *_py("print('dong-cua-con-42')")])
    assert "dong-cua-con-42" in capsys.readouterr().out


def test_in_which_cong_cu_o_dau_log(cau_hinh, mang, capsys):
    NR.main(["--title", "T", *_py("print('dong-cua-con')")])
    out = capsys.readouterr().out
    for ten in ("pwsh", "node", "ffprobe", "python", "npx"):
        assert f"which {ten}=" in out
    assert out.index("which pwsh=") < out.index("dong-cua-con"), "which phải in TRƯỚC lệnh con"


# ── (c) cấu hình Telegram & token ────────────────────────────────────────────

def test_khong_co_cau_hinh_bao_ro_khong_gui_va_giu_ma(capsys, monkeypatch):
    goi = MangGia()
    monkeypatch.setattr(tg, "_goi_that", goi)
    ma = NR.main(["--title", "T", *_py("import sys; sys.exit(3)")])
    assert ma == 3, "thiếu cấu hình Telegram không được đổi mã thoát"
    assert goi.lan == []
    err = capsys.readouterr().err
    assert "không thấy cấu hình Telegram" in err
    assert "TG_CONFIG" in err
    assert str(Path(os.environ["HOME"]) / ".secret" / "telegram" / "config.json") in err


def test_TG_CONFIG_tro_file_khong_ton_tai(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TG_CONFIG", str(tmp_path / "khong-co.json"))
    assert NR.main(["--title", "T", *_py("pass")]) == 0
    assert "khong-co.json" in capsys.readouterr().err


def test_cau_hinh_thieu_bot_token(tmp_path, monkeypatch, capsys):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"chats": {"mac_dinh": {"chat_id": 1}}}), encoding="utf-8")
    monkeypatch.setenv("TG_CONFIG", str(p))
    assert NR.main(["--title", "T", *_py("pass")]) == 0
    assert "bot_token" in capsys.readouterr().err


def test_token_khong_bao_gio_bi_in_ke_ca_khi_mang_loi(cau_hinh, monkeypatch, capsys):
    """Lỗi mạng có thể mang URL (chứa token) trong thông điệp — phải bị che."""
    monkeypatch.setattr(tg, "_goi_that", MangGia(
        no=OSError(f"ket noi toi https://api.telegram.org/bot{TOKEN_GIA}/sendMessage that bai")))
    assert NR.main(["--title", "T", *_py("print('https://youtu.be/x')")]) == 0
    cap = capsys.readouterr()
    assert TOKEN_GIA not in cap.out and TOKEN_GIA not in cap.err
    assert "gửi Telegram lỗi" in cap.err


def test_telegram_tu_choi_khong_doi_ma_thoat(cau_hinh, monkeypatch, capsys):
    monkeypatch.setattr(tg, "_goi_that", MangGia(tra_ve={"ok": False, "description": "chat not found"}))
    assert NR.main(["--title", "T", *_py("import sys; sys.exit(2)")]) == 2
    assert "chat not found" in capsys.readouterr().err


def test_KHONG_doc_token_tu_bien_moi_truong(monkeypatch, capsys):
    """Hợp đồng secret của repo: biến môi trường chỉ giữ ĐƯỜNG DẪN, không giữ token."""
    goi = MangGia()
    monkeypatch.setattr(tg, "_goi_that", goi)
    monkeypatch.setenv("TG_BOT_TOKEN", TOKEN_GIA)
    monkeypatch.setenv("TG_CHAT_ID", "4242")
    assert NR.main(["--title", "T", *_py("pass")]) == 0
    assert goi.lan == [], "token trong biến môi trường không được dùng"
    assert TOKEN_GIA not in capsys.readouterr().err


def test_tin_qua_dai_bi_cat(cau_hinh, mang):
    code = "import sys; [print('x' * 200) for _ in range(100)]; sys.exit(1)"
    NR.main(["--title", "T", *_py(code)])
    assert len(mang.tin) <= 4000


# ── composer (compose_report.py / triage.py của engine) ──────────────────────

def _composer(d: Path, compose: str | None = None, triage: str | None = None) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    if compose is not None:
        (d / "compose_report.py").write_text(compose, encoding="utf-8")
    if triage is not None:
        (d / "triage.py").write_text(triage, encoding="utf-8")
    return d


COMPOSE_OK = """import argparse, pathlib
ap = argparse.ArgumentParser()
ap.add_argument('--title'); ap.add_argument('--exit', type=int)
ap.add_argument('--duration'); ap.add_argument('--log'); ap.add_argument('--out')
a = ap.parse_args()
log = pathlib.Path(a.log).read_text(encoding='utf-8')
pathlib.Path(a.out).write_text(
    f'VAN NGUOI DOC {a.title} exit={a.exit} dur={a.duration} co_log={"dong-log" in log}',
    encoding='utf-8')
"""

TRIAGE_OK = """import argparse, pathlib
ap = argparse.ArgumentParser()
ap.add_argument('--title'); ap.add_argument('--exit', type=int)
ap.add_argument('--log'); ap.add_argument('--out')
a = ap.parse_args()
pathlib.Path(a.out).write_text(f'TRIAGE: nguyen nhan cho exit {a.exit}', encoding='utf-8')
"""


def test_composer_thanh_cong_dung_van_nguoi_doc(tmp_path, cau_hinh, mang):
    d = _composer(tmp_path / "engine", compose=COMPOSE_OK)
    assert NR.main(["--title", "T", "--composer-dir", str(d), *_py("print('dong-log')")]) == 0
    assert mang.tin.startswith("VAN NGUOI DOC T exit=0 dur=")
    assert "co_log=True" in mang.tin


def test_composer_hong_thi_roi_ve_dinh_dang_cu(tmp_path, cau_hinh, mang):
    d = _composer(tmp_path / "engine", compose="raise SystemExit(5)\n")
    assert NR.main(["--title", "T", "--composer-dir", str(d),
                    *_py("print('https://youtu.be/q')")]) == 0
    assert mang.tin.startswith("✅") and "https://youtu.be/q" in mang.tin


def test_FAIL_triage_duoc_noi_them_va_thay_log_duoi(tmp_path, cau_hinh, mang):
    d = _composer(tmp_path / "engine", triage=TRIAGE_OK)
    code = "import sys; print('=== Publishing'); print('dong-log-cuoi'); sys.exit(1)"
    assert NR.main(["--title", "T", "--composer-dir", str(d), *_py(code)]) == 1
    t = mang.tin
    assert "TRIAGE: nguyen nhan cho exit 1" in t
    assert "Hỏng ở bước" in t
    assert "Log đuôi" not in t, "đã có triage thì không dán log thô"


def test_composer_dir_khong_ton_tai_van_bao(tmp_path, cau_hinh, mang, capsys):
    assert NR.main(["--title", "T", "--composer-dir", str(tmp_path / "khong-co"),
                    *_py("import sys; sys.exit(2)")]) == 2
    assert mang.tin.startswith("❌")
    assert "khong-co" in capsys.readouterr().err


# ── Hậu kiểm độ phủ Facebook ─────────────────────────────────────────────────

def test_khoi_do_phu_facebook_duoc_dua_vao_tin(cau_hinh, mang):
    code = ("print('https://youtu.be/q');"
            "print('FB_REACH_BEGIN');"
            "print('12:00:01  bai hom qua: 0 luot xem');"
            "print('FB_REACH_END');"
            "print('FB_REACH_STATUS=low')")
    assert NR.main(["--title", "T", *_py(code)]) == 0
    t = mang.tin
    assert "CẢNH BÁO" in t and "bai hom qua: 0 luot xem" in t
    assert "12:00:01" not in t


# ── Chạy như lệnh thật (tiến trình con) — không cấu hình ⇒ không có đường ra mạng ─

def test_chay_nhu_lenh_that_giu_ma_va_bao_thieu_cau_hinh(tmp_path):
    nha = tmp_path / "nha2"
    nha.mkdir()
    env = {k: v for k, v in os.environ.items()
           if k not in ("TG_CONFIG", "TG_CHAT", "TG_BOT_TOKEN", "TG_CHAT_ID")}
    env.update(HOME=str(nha), USERPROFILE=str(nha))
    r = subprocess.run([PY, str(SCRIPT), "--title", "T", "--",
                        PY, "-c", "print('https://youtu.be/x'); import sys; sys.exit(3)"],
                       capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
    assert r.returncode == 3
    assert "https://youtu.be/x" in r.stdout
    assert "which python=" in r.stdout
    assert "không thấy cấu hình Telegram" in r.stderr


# ── (g) --timeout: launchd KHÔNG có ExecutionTimeLimit ───────────────────────
# Task Scheduler tự giết lượt chạy quá giờ; launchd không có khoá nào tương đương, nên
# một lượt treo giữ nguyên nhãn job và lượt kế tiếp bị bỏ qua LẶNG LẼ. Trần giờ vì thế
# phải nằm ở wrapper — và phải giết CẢ NHÓM con, không chỉ cái vỏ.

def test_timeout_giet_lenh_con_va_tra_ma_1(cau_hinh, mang):
    """Ngoại lệ DUY NHẤT của luật 'mã thoát = mã con': bị giết thì không có mã con."""
    ma = NR.main(["--title", "T", "--timeout", "1",
                  "--", PY, "-c", "import time; time.sleep(60)"])
    assert ma == 1
    assert "QUÁ GIỜ" in mang.tin


def test_timeout_khong_can_thiep_khi_lenh_con_xong_som(cau_hinh, mang):
    """Đặt trần không được đổi hành vi của lượt chạy bình thường."""
    assert NR.main(["--title", "T", "--timeout", "600",
                    *_py("import sys; sys.exit(3)")]) == 3
    assert "QUÁ GIỜ" not in mang.tin


def test_khong_dat_timeout_thi_giu_nguyen_hanh_vi_cu(cau_hinh, mang):
    assert NR.main(["--title", "T", *_py("import sys; sys.exit(2)")]) == 2


def test_timeout_am_la_loi_dung_lenh(cau_hinh):
    with pytest.raises(SystemExit):
        NR.main(["--title", "T", "--timeout", "-5", *_py("pass")])


def test_timeout_giet_CA_CHUM_khong_chi_tien_trinh_vo(cau_hinh, mang, tmp_path):
    """`run.ps1` đẻ ffmpeg/node/python. Giết mỗi vỏ là để lại một đàn mồ côi.

    Con cháu ghi một file MỖI GIÂY. Sau khi wrapper trả về, chờ thêm rồi đo: file không
    được lớn thêm nữa. Đó là bằng chứng cháu đã chết, không phải chỉ con.
    """
    import time
    dau = tmp_path / "chau.txt"
    chau = ("import time\n"
            f"p = open(r'{dau}', 'a')\n"
            "while True:\n    p.write('x'); p.flush(); time.sleep(0.2)\n")
    cha = ("import subprocess, sys, time\n"
           f"subprocess.Popen([sys.executable, '-c', {chau!r}])\n"
           "time.sleep(60)\n")
    assert NR.main(["--title", "T", "--timeout", "2", "--", PY, "-c", cha]) == 1
    time.sleep(1.0)
    a = dau.stat().st_size if dau.exists() else 0
    time.sleep(1.5)
    b = dau.stat().st_size if dau.exists() else 0
    assert b == a, f"cháu vẫn còn ghi ({a} -> {b} byte) — chỉ tiến trình vỏ bị giết"


# ── (g) REVIEW-P2 N13: regex link không được bỏ sót link THẬT ────────────────
# Một lượt đăng THÀNH CÔNG mà tin ✅ ghi "không phát hiện link" là hỏng đúng thứ wrapper
# sinh ra để làm (chuẩn báo cáo §E2 của máy). Ba chỗ hụt, đều tái lập được:
#   · không `re.I`      -> `https://WWW.YouTube.com/...` trượt
#   · chỉ `(?:www\.)?`  -> `m.youtube.com` trượt
#   · miền brand buộc có `/path` -> trang chủ thương hiệu trượt

def test_link_bat_duoc_du_VIET_HOA(cau_hinh, mang):
    """Log của công cụ ngoài không hứa viết thường. `Https://Youtu.be/...` vẫn là link."""
    code = ("print('YT: https://WWW.YouTube.com/watch?v=HOA1');"
            "print('FB: HTTPS://www.Facebook.com/1/posts/2')")
    assert NR.main(["--title", "T", *_py(code)]) == 0
    t = mang.tin
    assert "watch?v=HOA1" in t and "posts/2" in t
    assert "không phát hiện link" not in t


def test_link_bat_duoc_ten_mien_di_dong(cau_hinh, mang):
    assert NR.main(["--title", "T", *_py("print('https://m.youtube.com/watch?v=MOB1')")]) == 0
    assert "watch?v=MOB1" in mang.tin


def test_mien_brand_khong_co_path_van_la_link(cau_hinh, mang):
    """Bài đăng ở trang chủ (`https://blog.example.com`) không có `/path` — vẫn phải kèm."""
    assert NR.main(["--title", "T", "--link-domains", "blog.example.com",
                    *_py("print('xong: https://blog.example.com')")]) == 0
    assert "https://blog.example.com" in mang.tin


def test_mien_brand_KHONG_bat_ten_mien_dai_hon(cau_hinh, mang):
    """Bỏ bắt buộc `/path` mà không neo đuôi thì `example.com` nuốt luôn `example.company`."""
    assert NR.main(["--title", "T", "--link-domains", "example.com",
                    *_py("print('https://example.company/x')")]) == 0
    assert "example.company" not in mang.tin


def test_token_trong_log_con_KHONG_lot_vao_tin(cau_hinh, mang):
    """REVIEW-P2 Ghi nhận 13. `_loi()` đã che token, `soan_tin` thì chưa — mà chính
    `soan_tin` mới là đường log của TIẾN TRÌNH CON đi ra Telegram."""
    gia = "123456789:" + "A" * 24
    assert NR.main(["--title", "T", *_py(f"import sys; print('loi: {gia}'); sys.exit(1)")]) == 1
    assert gia not in mang.tin, "token trong log con đi thẳng vào tin Telegram"
    assert "token-da-che" in mang.tin
