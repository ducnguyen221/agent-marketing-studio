# -*- coding: utf-8 -*-
"""Cổng cho lớp gọi agent headless dùng chung (`scripts/lib/agent_call.py`).

Bốn thứ được kiểm bằng engine GIẢ chứ không bằng model thật: phân loại lỗi (nhất là hết
hạn mức), chuyển engine theo cấu hình, nhúng skill, và giết tiến trình quá giờ. Gọi model
thật trong bộ test là vừa chậm vừa tốn hạn mức vừa không lặp lại được — mà đúng ba thứ
đó là lý do lớp này tồn tại.

Engine giả là một script Python nhận đúng argv thật của từng CLI rồi in ra thứ đã dặn:
nhờ vậy test kiểm luôn cả phần **dựng argv**, không chỉ phần xử lý kết quả.
"""
from __future__ import annotations

import json
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# CHỈ thêm `scripts/lib`. Thư mục `scripts/pipeline` có một file TRÙNG TÊN (`agent_call.py`,
# CLI mỏng); thêm nó vào `sys.path` trước thì `import agent_call` nạp nhầm CLI và cả file
# test này kiểm một module khác với module nó tưởng. CLI được kiểm bằng tiến trình con.
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

import agent_call as AC  # noqa: E402
import studio_contract as SC  # noqa: E402


# ── Engine giả ──────────────────────────────────────────────────────────────────────

SHIM = textwrap.dedent('''
    import json, os, sys, time
    kb = json.loads(os.environ["SHIM_SPEC"])
    argv = sys.argv[1:]
    sot = os.environ.get("SHIM_ARGV_LOG")
    if sot:
        with open(sot, "a", encoding="utf-8") as f:
            f.write(json.dumps(argv, ensure_ascii=False) + "\\n")
    if kb.get("read_stdin", True):
        data = sys.stdin.read() if not sys.stdin.closed else ""
        sot2 = os.environ.get("SHIM_STDIN_LOG")
        if sot2:
            with open(sot2, "a", encoding="utf-8") as f:
                f.write(data)
    if kb.get("sleep"):
        # In một dòng trước khi ngủ để đồng hồ "im lặng" có mốc bắt đầu thật.
        print("bat dau", flush=True)
        time.sleep(kb["sleep"])
    for d in kb.get("stdout", []):
        print(d, flush=True)
    for d in kb.get("stderr", []):
        print(d, file=sys.stderr, flush=True)
    for duong, noi_dung in (kb.get("write") or {}).items():
        p = os.path.abspath(duong)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(noi_dung)
    sys.exit(kb.get("rc", 0))
''')


@pytest.fixture
def shim(tmp_path):
    f = tmp_path / "shim.py"
    f.write_text(SHIM, encoding="utf-8")
    return f


def _cfg(shim_path, **engines):
    """engines.json giả: mọi engine trỏ về cùng một shim, khác nhau ở `SHIM_SPEC`."""
    ra = {"version": 1, "order": [], "engines": {}, "skill_roots": []}
    for ten, spec in engines.items():
        ra["engines"][ten] = {"cmd": [sys.executable, str(shim_path)],
                              "best": spec.pop("best", "m-best"), **spec}
    return ra


def _env(spec, **them):
    import os
    e = dict(os.environ)
    e["SHIM_SPEC"] = json.dumps(spec)
    e["PYTHONUTF8"] = "1"
    e.update({k: str(v) for k, v in them.items()})
    return e


OK_CLAUDE = {"rc": 0, "stdout": [json.dumps({"result": "OK", "usage": {"input_tokens": 10,
                                                                      "output_tokens": 2}})]}


# ── 1. Phân tích mã thoát & phân loại lỗi ───────────────────────────────────────────

def test_ma_thoat_0_khong_bao_gio_la_loi():
    assert AC.classify("claude", 0, "bất kỳ thứ gì kể cả chữ usage limit", "")["kind"] is None


@pytest.mark.parametrize("engine,text", [
    ("claude", "You've hit your session limit · resets 7:50pm (Asia/Ho_Chi_Minh)"),
    ("claude", "You've hit your usage limit"),
    ("codex", "Error: You've hit your usage limit"),
    ("agy", "quota exceeded for this model"),
])
def test_nhan_biet_het_han_muc_tung_engine(engine, text):
    assert AC.classify(engine, 1, "", text)["kind"] == "quota"


def test_agy_dung_MA_THOAT_truoc_chuoi_chu():
    """agy ≥ 1.2.6 in `AGY_ERROR:{…}`; trường `status` là hợp đồng, chuỗi chữ chỉ là đường lùi."""
    err = 'AGY_ERROR: {"status":"RESOURCE_EXHAUSTED","code":429,"retryable":true,"error_id":"x1"}'
    ra = AC.classify("agy", 3, "", err)
    assert ra["kind"] == "quota"
    # Không có một chữ "limit"/"quota" nào trong chuỗi — nếu lọt được thì là nhờ mã, không nhờ chữ.
    assert "limit" not in err.lower() and "quota" not in err.lower()


def test_agy_error_unauthenticated_la_auth_khong_phai_quota():
    err = 'AGY_ERROR: {"status":"UNAUTHENTICATED","code":401}'
    assert AC.classify("agy", 3, "", err)["kind"] == "auth"


def test_da_sinh_token_thi_dut_giua_chung_KHONG_phai_quota():
    """Hết hạn mức luôn xảy ra ở ĐẦU lượt. Đứt sau khi đã chạy = lỗi engine, và chuyển
    engine lúc đó là làm lại từ đầu một việc đã xong nửa chừng."""
    t = "You've hit your usage limit"
    assert AC.classify("claude", 1, "", t, produced=False)["kind"] == "quota"
    assert AC.classify("claude", 1, "", t, produced=True)["kind"] == "engine"


@pytest.mark.parametrize("text,cho", [
    ("Invalid API key · please run login", "auth"),
    ("getaddrinfo ENOTFOUND api.example", "network"),
    ("unknown model: gpt-khong-co", "model_access"),
    ("Segmentation fault", "engine"),
])
def test_cac_loai_loi_khac(text, cho):
    assert AC.classify("claude", 1, "", text)["kind"] == cho


def test_network_duoc_hoi_truoc_quota():
    """Thứ tự trong KIND_ORDER có ý nghĩa: một dòng lỗi mạng cũng có thể chứa chữ 'limit'."""
    assert AC.KIND_ORDER.index("network") < AC.KIND_ORDER.index("quota")
    t = "ECONNRESET while reading; rate limit exceeded may follow"
    assert AC.classify("claude", 1, "", t)["kind"] == "network"


# ── 2. Giờ mở lại ───────────────────────────────────────────────────────────────────

def test_parse_resets_doc_gio_trong_chinh_dong_loi():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    bay_gio = datetime(2026, 9, 20, 18, 0, tzinfo=tz)
    iso = AC.parse_resets("You've hit your session limit · resets 7:50pm (Asia/Ho_Chi_Minh)",
                          now=bay_gio)
    assert iso.startswith("2026-09-20T19:50")


def test_parse_resets_gio_da_qua_hieu_la_ngay_mai():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    iso = AC.parse_resets("resets 7:50pm (Asia/Ho_Chi_Minh)",
                          now=datetime(2026, 9, 20, 21, 0, tzinfo=tz))
    assert iso.startswith("2026-09-21T19:50")


def test_parse_resets_uu_tien_chuoi_ISO_co_san():
    assert AC.parse_resets("reset at 2026-09-24T03:30:00Z") == "2026-09-24T03:30:00Z"


def test_parse_resets_khong_co_gi_thi_None():
    assert AC.parse_resets("You've hit your usage limit") is None


def test_parse_usage_cua_agy_doc_hai_ho_tach_biet():
    """Hai hồ TÁCH BIỆT là lý do `agy:claude-opus-4-6-thinking` chạy được khi tài khoản
    Claude đã cạn — gộp thành một con số là mất đúng thông tin cứu được lượt chạy."""
    tsv = ("Gemini Models\tWeekly Limit Remaining\t96%\t2026-09-24T03:30:31Z\n"
           "Gemini Models\tFive Hour Limit Remaining\t0%\t2026-09-20T20:34:14Z\n"
           "Claude and GPT models\tWeekly Limit Remaining\t99%\t2026-09-27T15:38:32Z\n")
    hang = AC.parse_agy_usage(tsv)
    assert len(hang) == 3
    assert hang[0]["pool"] == "Gemini Models" and hang[0]["remaining_pct"] == 96
    # Hồ đã CẠN được ưu tiên: đó là hồ chặn lượt chạy, không phải hồ xa nhất.
    assert AC.agy_resets_at(hang) == "2026-09-20T20:34:14Z"


def test_agy_resets_at_khong_ho_nao_can_thi_lay_moc_gan_nhat():
    hang = [{"pool": "a", "remaining_pct": 50, "resets_at": "2026-09-27T15:38:32Z"},
            {"pool": "b", "remaining_pct": 90, "resets_at": "2026-09-24T03:30:31Z"}]
    assert AC.agy_resets_at(hang) == "2026-09-24T03:30:31Z"
    assert AC.agy_resets_at([]) is None


def test_agy_usage_hoi_bang_lenh_gach_cheo_0_token():
    """Không được biến phép hỏi hạn mức thành một lượt model — nó phải đi qua `--print=/usage`."""
    da_goi = {}

    def gia(argv, stdin_text=None, **kw):
        da_goi["argv"] = argv
        return {"stdout": json.dumps({"response": "P\tW\t0%\t2026-09-24T03:30:31Z",
                                      "usage": {"total_tokens": 0}, "num_turns": 0}),
                "stderr": "", "rc": 0, "ms": 5, "timed_out": False, "reason": ""}

    hang = AC.agy_usage(runner=gia)
    assert "--print=/usage" in da_goi["argv"]
    assert hang and hang[0]["resets_at"] == "2026-09-24T03:30:31Z"


def test_agy_usage_hong_thi_tra_rong_chu_khong_no(shim, tmp_path):
    def no(*a, **k):
        raise OSError("agy khong chay")
    assert AC.agy_usage(runner=no) == []


# ── 3. Dựng lệnh cho từng engine ────────────────────────────────────────────────────

def test_claude_nhan_prompt_qua_stdin_agy_qua_argv():
    argv_c, stdin_c = AC.build_command("claude", "opus", "XIN CHAO")
    assert stdin_c == "XIN CHAO" and "XIN CHAO" not in " ".join(argv_c)
    argv_a, stdin_a = AC.build_command("agy", "gemini-3.8-flash-high", "XIN CHAO")
    assert stdin_a is None and any("XIN CHAO" in a for a in argv_a)


def test_agy_vuot_tran_argv_la_ma_2():
    with pytest.raises(SC.ContractError):
        AC.build_command("agy", "m", "x" * (AC.AGY_ARGV_LIMIT + 1))


def test_tool_truu_tuong_map_sang_tung_engine():
    assert AC.claude_tools("web,read") == ["WebSearch", "WebFetch", "Read", "Glob", "Grep"]
    assert AC.claude_tools("shell:curl") == ["Bash(curl:*)"]
    assert AC.codex_sandbox("read") == "read-only"
    assert AC.codex_sandbox("write") == "workspace-write"
    # `danger-full-access` chỉ mở khi TRẠM khai tường minh — lớp gọi không tự nới quyền.
    assert AC.codex_sandbox("shell:curl") == "workspace-write"
    assert AC.codex_sandbox("shell:curl", allow_full=True) == "danger-full-access"


def test_tool_la_la_ma_2():
    with pytest.raises(SC.ContractError):
        AC.claude_tools("rm-rf")


def test_agy_khong_co_tool_thi_khong_mo_cua_skip_permissions():
    argv, _ = AC.build_command("agy", "m", "hi", tools=())
    assert "--dangerously-skip-permissions" not in argv
    argv2, _ = AC.build_command("agy", "m", "hi", tools="write")
    assert "--dangerously-skip-permissions" in argv2


# ── 4. Thứ tự engine đọc từ cấu hình, không ghim trong mã ───────────────────────────

def test_best_tra_tu_cau_hinh_cua_tram():
    cfg = {"engines": {"agy": {"best": "claude-opus-4-6-thinking"}}}
    assert AC.resolve_model("agy", "best", cfg) == "claude-opus-4-6-thinking"
    assert AC.resolve_model("agy", "gemini-3.1-pro-high", cfg) == "gemini-3.1-pro-high"


def test_engine_khong_khai_trong_cau_hinh_la_ma_2():
    with pytest.raises(SC.ContractError):
        AC.resolve_model("codex", "best", {"engines": {"claude": {"best": "opus"}}})


def test_doi_thu_tu_trong_order_la_doi_chuoi_fallback():
    """Đây là yêu cầu gốc: đổi thứ tự engine phải là sửa FILE, không phải sửa mã."""
    cfg = {"engines": {"claude": {"best": "opus"}, "agy": {"best": "g-flash"},
                       "codex": {"best": "sol"}},
           "order": ["agy:claude-opus-4-6-thinking", "codex:best"]}
    assert AC.build_chain("claude", "best", cfg) == [
        ("claude", "opus"), ("agy", "claude-opus-4-6-thinking"), ("codex", "sol")]
    cfg["order"] = ["codex:best", "agy:best"]
    assert AC.build_chain("claude", "best", cfg) == [
        ("claude", "opus"), ("codex", "sol"), ("agy", "g-flash")]


def test_engine_duoc_yeu_cau_luon_dung_dau_chuoi():
    cfg = {"engines": {"claude": {"best": "opus"}, "agy": {"best": "g"}},
           "order": ["claude:best", "agy:best"]}
    assert AC.build_chain("agy", "best", cfg)[0] == ("agy", "g")


def test_chuoi_fallback_engine_la_la_ma_2():
    cfg = {"engines": {"claude": {"best": "opus"}}, "order": ["gpt4all:best"]}
    with pytest.raises(SC.ContractError):
        AC.build_chain("claude", "best", cfg)


def test_load_config_json_hong_thi_no_chu_khong_am_tham_dung_mac_dinh(tmp_path):
    f = tmp_path / "engines.json"
    f.write_text("{ khong phai json", encoding="utf-8")
    with pytest.raises(SC.ContractError):
        AC.load_config(f)


def test_load_config_thieu_file_thi_dung_mac_dinh(tmp_path):
    cfg = AC.load_config(tmp_path / "khong-co.json")
    assert cfg["engines"]["agy"]["best"]


# ── 5. Nhúng skill: cùng chuỗi byte cho cả ba engine ───────────────────────────────

@pytest.fixture
def kho_skill(tmp_path):
    goc = tmp_path / "plugins"
    (goc / "kpim-skills" / "skills" / "blog-writing").mkdir(parents=True)
    (goc / "kpim-skills" / "skills" / "blog-writing" / "SKILL.md").write_text(
        "# Blog writing\nLUAT RIENG CUA GIONG VIET", encoding="utf-8")
    (goc / "hook-writer").mkdir(parents=True)
    (goc / "hook-writer" / "SKILL.md").write_text("# Hook\nMO BAI", encoding="utf-8")
    return [goc]


def test_inline_skill_chen_noi_dung_that_vao_dau_prompt(kho_skill):
    ra = AC.inline_skills("VIET BAI", ["kpim-skills:blog-writing"], kho_skill)
    assert "LUAT RIENG CUA GIONG VIET" in ra
    assert ra.index("LUAT RIENG") < ra.index("VIET BAI"), "skill phải đứng TRƯỚC mệnh lệnh"
    assert '<skill name="kpim-skills:blog-writing">' in ra


def test_inline_skill_tim_duoc_ca_ten_tran(kho_skill):
    assert "MO BAI" in AC.inline_skills("X", ["hook-writer"], kho_skill)


def test_skill_khong_thay_la_ma_2_chu_khong_chay_tiep(kho_skill):
    """Chạy tiếp mà thiếu skill ⇒ bài sai giọng, CLI vẫn trả mã 0, không ai biết vì sao."""
    with pytest.raises(SC.ContractError):
        AC.inline_skills("X", ["khong-ton-tai"], kho_skill)


def test_native_tren_engine_khong_co_duong_native_thi_ROI_VE_inline(kho_skill, shim, tmp_path):
    """Bỏ skill mà vẫn trả mã 0 là hỏng theo kiểu không ai phát hiện — bài ra sai giọng."""
    cfg = _cfg(shim, agy={})
    cfg["skill_roots"] = [str(p) for p in kho_skill]
    log = tmp_path / "argv.log"
    AC.call("VIET BAI", engine="agy", skills="kpim-skills:blog-writing", skills_mode="native",
            cfg=cfg, cwd=tmp_path, timeout=60, stall=30, ledger=tmp_path / "so.jsonl",
            env=_env({"rc": 0, "stdout": [json.dumps({"response": "x"})]},
                     SHIM_ARGV_LOG=str(log)))
    argv = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    prompt = [a for a in argv if a.startswith("--print=")][0]
    assert "LUAT RIENG CUA GIONG VIET" in prompt, "skill bị bỏ im lặng"


def test_cung_mot_chuoi_byte_di_toi_ca_ba_engine(kho_skill, shim, tmp_path):
    """Điều kiện để bài so sánh CÔNG BẰNG: prompt gửi đi phải giống nhau từng byte."""
    cfg = _cfg(shim, claude={}, codex={}, agy={})
    cfg["skill_roots"] = [str(p) for p in kho_skill]
    p = AC.inline_skills("VIET BAI", ["kpim-skills:blog-writing"], AC.skill_roots(cfg))
    _, stdin_claude = AC.build_command("claude", "m", p, cfg=cfg)
    _, stdin_codex = AC.build_command("codex", "m", p, cfg=cfg)
    argv_agy, _ = AC.build_command("agy", "m", p, cfg=cfg)
    qua_argv = [a for a in argv_agy if a.startswith("--print=")][0][len("--print="):]
    assert stdin_claude == stdin_codex == qua_argv


# ── 6. Cổng artifact ────────────────────────────────────────────────────────────────

def test_parse_expect_khong_nham_o_dia_windows_voi_nguong_byte():
    p, n = AC.parse_expect("C:" + chr(92) + "tmp" + chr(92) + "a.json:800")
    assert n == 800 and str(p).endswith("a.json")
    p2, n2 = AC.parse_expect("out/a.json")
    assert n2 == 1 and str(p2).endswith("a.json")


def test_expect_thieu_artifact_la_ma_1_du_CLI_tra_0(shim, tmp_path):
    cfg = _cfg(shim, claude={})
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 expect=[str(tmp_path / "ra.json") + ":800"],
                 ledger=tmp_path / "so.jsonl", env=_env(OK_CLAUDE))
    assert ra["code"] == AC.ENGINE_ERROR and not ra["ok"]
    assert "thiếu artifact" in ra["error"]


def test_expect_du_lon_thi_ma_0(shim, tmp_path):
    cfg = _cfg(shim, claude={})
    spec = dict(OK_CLAUDE, write={str(tmp_path / "ra.json"): "x" * 900})
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 expect=[str(tmp_path / "ra.json") + ":800"],
                 ledger=tmp_path / "so.jsonl", env=_env(spec))
    assert ra["ok"] and ra["code"] == 0


# ── 7. Chuyển engine thật (qua shim) ───────────────────────────────────────────────

def test_het_han_muc_thi_chuyen_sang_engine_ke_tiep(shim, tmp_path):
    """Đúng kịch bản hai lượt chết tối 19–20/09: Claude hết hạn mức thì agy gánh."""
    cfg = _cfg(shim, claude={}, agy={})
    cfg["order"] = ["agy:best"]
    het = {"rc": 1, "stderr": ["You've hit your session limit · resets 7:50pm (Asia/Ho_Chi_Minh)"]}
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 ledger=tmp_path / "so.jsonl", env=_env(het))
    # Cả hai engine cùng dùng một shim ⇒ cùng hỏng ⇒ mã 4, nhưng phải THỬ đủ hai lượt:
    # thứ đang kiểm là "có chuyển engine không", không phải "engine kia có chạy không".
    assert ra["code"] == AC.QUOTA_EXHAUSTED
    assert [t["engine"] for t in ra["tried"]] == ["claude", "agy"]
    assert ra["resets_at"] and ra["resets_at"].endswith("+07:00")


def test_ma_4_chi_khi_MOI_engine_het_han_muc(shim, tmp_path):
    """Một engine hết hạn mức, engine sau lỗi thật ⇒ mã 1, không phải 4: mã 4 bảo lịch
    'đợi tới giờ X', và giờ đó không chữa được một lỗi engine."""
    cfg = _cfg(shim, claude={}, agy={})
    cfg["order"] = ["agy:best"]
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 ledger=tmp_path / "so.jsonl",
                 env=_env({"rc": 1, "stderr": ["Segmentation fault"]}))
    assert ra["code"] == AC.ENGINE_ERROR
    assert len(ra["tried"]) == 1, "lỗi engine thường KHÔNG chuyển engine — đó là việc của lịch"


def test_on_quota_fail_thi_dung_ngay_khong_thu_engine_khac(shim, tmp_path):
    cfg = _cfg(shim, claude={}, agy={})
    cfg["order"] = ["agy:best"]
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 on_quota="fail", ledger=tmp_path / "so.jsonl",
                 env=_env({"rc": 1, "stderr": ["You've hit your usage limit"]}))
    assert ra["code"] == AC.QUOTA_EXHAUSTED and len(ra["tried"]) == 1


def test_on_quota_wait_ngu_toi_gio_mo_lai_roi_thu_lai_CHINH_engine_do(shim, tmp_path):
    da_ngu = []
    cfg = _cfg(shim, claude={}, agy={})
    cfg["order"] = ["agy:best"]
    # Lỗi KHÔNG phải hạn mức thì không bao giờ được chờ — chờ một lỗi engine là treo slot
    # cả tiếng cho một thứ mà thời gian không chữa được.
    AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
            on_quota="wait", ledger=tmp_path / "so.jsonl", sleep=da_ngu.append,
            env=_env({"rc": 1, "stderr": ["Segmentation fault at 2026-09-24T03:30:00Z"]}))
    assert not da_ngu
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 on_quota="wait", ledger=tmp_path / "so.jsonl", sleep=da_ngu.append,
                 env=_env({"rc": 1, "stderr": [
                     "You've hit your usage limit; reset at " + _sap_toi()]}))
    assert da_ngu, "phải có một lần chờ"
    assert [t["engine"] for t in ra["tried"]][:2] == ["claude", "claude"]


def _sap_toi(giay=60):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) + timedelta(seconds=giay)).isoformat()


def test_khong_co_CLI_tren_PATH_la_ma_3(tmp_path):
    cfg = {"engines": {"claude": {"cmd": "khong-co-lenh-nay-tren-may-9x7", "best": "m"}},
           "order": []}
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=30, stall=15,
                 ledger=tmp_path / "so.jsonl")
    assert ra["code"] == AC.STATION_MISSING


# ── 8. Kỷ luật tiến trình ───────────────────────────────────────────────────────────

def test_qua_gio_thi_giet_va_tra_ve_khong_treo(shim, tmp_path):
    t0 = time.monotonic()
    r = AC.run_process([sys.executable, str(shim)], None, cwd=tmp_path,
                       env=_env({"sleep": 60, "read_stdin": False}), timeout=3, stall=60)
    mat = time.monotonic() - t0
    assert r["timed_out"] and r["rc"] == -1
    assert mat < 25, f"phải trả về ngay sau khi quá giờ, không chờ hết 60s (mất {mat:.1f}s)"
    assert "quá tổng" in r["reason"]


def test_dong_ho_im_lang_bat_luot_treo(shim, tmp_path):
    r = AC.run_process([sys.executable, str(shim)], None, cwd=tmp_path,
                       env=_env({"sleep": 30, "read_stdin": False}), timeout=120, stall=3)
    assert r["timed_out"] and "im lặng" in r["reason"]


def test_giet_ca_cay_tien_trinh_con(tmp_path):
    """Giết mỗi tiến trình cha để lại cháu mồ côi còn giữ cổng và còn ghi file.

    Cháu ghi PID của chính nó ra đĩa rồi ngủ; sau khi cây bị giết, test hỏi hệ điều hành
    xem PID đó còn sống không. Hỏi hệ điều hành chứ không suy từ mã thoát của cha: mã
    thoát của cha không nói gì về cháu, và đó chính là cái bẫy này nói tới.
    """
    import os
    pid_file = tmp_path / "chau.pid"
    chau = tmp_path / "chau.py"
    chau.write_text("import os,sys,time\n"
                    "open(sys.argv[1],'w').write(str(os.getpid()))\n"
                    "time.sleep(120)\n", encoding="utf-8")
    cha = tmp_path / "cha.py"
    cha.write_text(textwrap.dedent(f'''
        import subprocess, sys, time
        subprocess.Popen([sys.executable, {str(chau)!r}, {str(pid_file)!r}])
        print("da de chau", flush=True)
        time.sleep(120)
    '''), encoding="utf-8")
    r = AC.run_process([sys.executable, str(cha)], None, cwd=tmp_path,
                       env=dict(os.environ, PYTHONUTF8="1"), timeout=8, stall=60)
    assert r["timed_out"]
    for _ in range(20):
        if pid_file.is_file() and pid_file.read_text(encoding="utf-8").strip():
            break
        time.sleep(0.2)
    if not (pid_file.is_file() and pid_file.read_text(encoding="utf-8").strip()):
        pytest.skip("cháu chưa kịp ghi PID — phép đo này không nói được gì")
    pid = int(pid_file.read_text(encoding="utf-8").strip())
    time.sleep(1.5)
    assert not _con_song(pid), f"tiến trình cháu {pid} còn sống sau khi giết cây"
    _don(pid)


def _con_song(pid: int) -> bool:
    import os
    import subprocess as sp
    if os.name == "nt":
        ra = sp.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True, timeout=30)
        return str(pid) in (ra.stdout or "")
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _don(pid: int) -> None:
    """Test này cố tình đẻ tiến trình; nếu cổng đỏ thì cũng không để lại cháu mồ côi."""
    import os
    import signal
    import subprocess as sp
    try:
        if os.name == "nt":
            sp.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=30)
        else:
            os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def test_stdin_duoc_dong_sau_khi_ghi_prompt(shim, tmp_path):
    """Tiến trình con còn chờ EOF là còn im lặng, và đồng hồ im lặng giết nhầm lượt tốt."""
    log = tmp_path / "stdin.log"
    r = AC.run_process([sys.executable, str(shim)], "PROMPT CUA TOI", cwd=tmp_path,
                       env=_env({"rc": 0}, SHIM_STDIN_LOG=str(log)), timeout=20, stall=10)
    assert r["rc"] == 0 and not r["timed_out"]
    assert log.read_text(encoding="utf-8") == "PROMPT CUA TOI"


def test_agy_khong_bao_gio_duoc_noi_stdin(shim, tmp_path):
    """agy từ chối stdin; mở ống stdin cho nó là mở một ống không ai đóng."""
    _, stdin_text = AC.build_command("agy", "m", "hi")
    assert stdin_text is None


# ── 9. Sổ ───────────────────────────────────────────────────────────────────────────

def test_so_ghi_mot_dong_cho_MOI_luot_ke_ca_luot_bi_bo(shim, tmp_path):
    cfg = _cfg(shim, claude={}, agy={})
    cfg["order"] = ["agy:best"]
    so = tmp_path / "so.jsonl"
    AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30, ledger=so,
            env=_env({"rc": 1, "stderr": ["You've hit your usage limit"]}))
    dong = [json.loads(d) for d in so.read_text(encoding="utf-8").splitlines() if d.strip()]
    assert [d["engine"] for d in dong] == ["claude", "agy"]
    for d in dong:
        assert d["kind"] == "quota" and d["ts"] and d["chain_len"] == 2
        assert set(d) >= {"engine", "model", "ms", "rc", "kind", "usage", "prompt_bytes"}


def test_so_hong_khong_lam_hong_luot_goi(shim, tmp_path):
    """Đĩa đầy hay thư mục chỉ-đọc thì mất sổ, bài viết vẫn phải ra."""
    cfg = _cfg(shim, claude={})
    # Đường dẫn sổ không ghi được (một TỆP đứng ở chỗ đáng lẽ là thư mục).
    chan = tmp_path / "chan"
    chan.write_text("toi la mot tep", encoding="utf-8")
    ra = AC.call("x", engine="claude", cfg=cfg, cwd=tmp_path, timeout=60, stall=30,
                 ledger=chan / "a.jsonl", env=_env(OK_CLAUDE))
    assert ra["ok"], "sổ hỏng KHÔNG được làm hỏng lượt gọi"


def test_usage_khong_doc_duoc_thi_None_chu_khong_phai_0():
    """0 token và 'không đo được' là hai chuyện khác nhau — nhầm là hỏng mọi phép so sau này."""
    assert AC.extract_usage("claude", "khong phai json") is None
    assert AC.extract_usage("agy", json.dumps({"usage": {"total_tokens": 5}})) == {"total_tokens": 5}


def test_usage_codex_doc_tu_JSONL():
    jsonl = "\n".join([json.dumps({"type": "turn.started"}),
                       json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7}})])
    assert AC.extract_usage("codex", jsonl) == {"input_tokens": 7}


# ── 10. CLI ────────────────────────────────────────────────────────────────────────

def test_cli_chay_that_tra_ma_va_dong_json(tmp_path, shim):
    import os
    import subprocess
    cfg = _cfg(shim, claude={})
    f = tmp_path / "engines.json"
    f.write_text(json.dumps(cfg), encoding="utf-8")
    env = _env({"rc": 1, "stderr": ["You've hit your usage limit"]})
    env["AGENT_CALL_ENGINES"] = str(f)
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pipeline" / "agent_call.py"),
         "--engine", "claude", "--cwd", str(tmp_path), "--timeout", "60", "--stall", "30",
         "--ledger", str(tmp_path / "so.jsonl"), "--json"],
        input="viet mot cau", capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=180, cwd=str(tmp_path))
    assert r.returncode == AC.QUOTA_EXHAUSTED, r.stderr[-800:]
    data = SC.last_json_line(r.stdout)
    assert data and data["code"] == 4 and data["kind"] == "quota"
    assert os.path.isfile(tmp_path / "so.jsonl")


def test_cli_engine_la_la_ma_2(tmp_path):
    import subprocess
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pipeline" / "agent_call.py"),
         "--engine", "gpt4all", "--json"],
        input="x", capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == AC.CONTRACT_ERROR
