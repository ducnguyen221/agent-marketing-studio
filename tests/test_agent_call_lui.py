# -*- coding: utf-8 -*-
"""Chuỗi lùi của `agent_call` bắt cả lỗi TẠM (P1-22) và `--engine order` (P1-21).

Mac mini 01/10/2026:
    · truyện 20:59 — agy (đầu `order`) trả `{"status":"ERROR","error":"timeout waiting for
      response"}` sau 7 s; chuỗi dừng vì `engine` không nằm trong `CHUYEN_ENGINE`, hook YouTube
      rơi về mô tả tĩnh dù codex/claude chạy được;
    · Hot Data 19:00 — runner tin gọi `claude -p` thô, hết hạn mức ×3 rồi abort, trong khi
      `engines.json` xếp agy đứng đầu và agy chạy được.

Engine giả: mỗi engine một shim riêng (khác `test_agent_call.py`, nơi mọi engine dùng chung
một `SHIM_SPEC`), để agy hỏng trong khi codex chạy được.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# CHỈ `lib/`: `pipeline/agent_call.py` (CLI) trùng tên — nạp nó bằng spec ở test CLI.
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import agent_call as AC  # noqa: E402
import studio_contract as SC  # noqa: E402

# Shim có bộ đếm: lần gọi thứ n đọc `lan[n-1]` (hết danh sách thì lặp phần tử cuối).
SHIM = textwrap.dedent('''
    import json, os, sys
    kb = json.loads(open(sys.argv[1], encoding="utf-8").read())
    dem = sys.argv[1] + ".dem"
    n = int(open(dem).read()) if os.path.exists(dem) else 0
    open(dem, "w").write(str(n + 1))
    lan = kb["lan"][min(n, len(kb["lan"]) - 1)]
    if not kb.get("argv_prompt"):
        sys.stdin.read()
    for d in lan.get("stdout", []):
        print(d, flush=True)
    for d in lan.get("stderr", []):
        print(d, file=sys.stderr, flush=True)
    for duong, nd in (lan.get("write") or {}).items():
        os.makedirs(os.path.dirname(os.path.abspath(duong)), exist_ok=True)
        open(duong, "w", encoding="utf-8").write(nd)
    sys.exit(lan.get("rc", 0))
''')

OK = {"rc": 0, "stdout": [json.dumps({"result": "OK"})]}
AGY_TIMEOUT = {"rc": 1, "stderr": ['AGY_ERROR: {"status":"ERROR","error":"timeout waiting for response"}']}
QUOTA = {"rc": 1, "stderr": ["You've hit your session limit · resets 9:30pm"]}


@pytest.fixture
def lam(tmp_path):
    shim = tmp_path / "shim.py"
    shim.write_text(SHIM, encoding="utf-8")

    def _cfg(order, **engines):
        cfg = {"version": 1, "order": order, "engines": {}, "skill_roots": []}
        for ten, lan in engines.items():
            kb = tmp_path / f"{ten}.json"
            kb.write_text(json.dumps({"lan": lan, "argv_prompt": ten == "agy"}), encoding="utf-8")
            cfg["engines"][ten] = {"cmd": [sys.executable, str(shim), str(kb)], "best": f"{ten}-best"}
        return cfg
    return _cfg


def _goi(cfg, tmp_path, prompt="x", **kw):
    ngu = []
    eng, mdl = AC.dau_order(cfg)
    ra = AC.call(prompt, engine=eng, model=mdl, cfg=cfg, cwd=tmp_path, timeout=60, stall=0,
                 ledger=tmp_path / "so.jsonl", sleep=ngu.append, **kw)
    return ra, ngu


def _chuoi(ra):
    return [(t["engine"], t["kind"]) for t in ra["tried"]]


# ── P1-22: lỗi tạm ──────────────────────────────────────────────────────────────────

def test_agy_ERROR_timeout_thi_thu_lai_mot_lan_roi_SANG_engine_ke(lam, tmp_path):
    """Đúng cảnh truyện 20:59: agy ERROR timeout ⇒ phải sang codex, không dừng."""
    cfg = lam(["agy:best", "codex:best", "claude:best"],
              agy=[AGY_TIMEOUT], codex=[OK], claude=[OK])
    ra, ngu = _goi(cfg, tmp_path)
    assert ra["ok"] and ra["engine"] == "codex", _chuoi(ra)
    assert _chuoi(ra) == [("agy", "engine"), ("agy", "engine"), ("codex", None)]
    assert ngu == [AC.NGHI_THU_LAI]


def test_loi_tam_KHONG_lap_lai_thi_thu_lai_CHINH_engine_va_xong(lam, tmp_path):
    """Không tái hiện được (Mac thử lại 4 lần đều OK) ⇒ lần thử lại thứ nhất là đủ."""
    cfg = lam(["agy:best", "codex:best"], agy=[AGY_TIMEOUT, OK], codex=[OK])
    ra, _ = _goi(cfg, tmp_path)
    assert ra["ok"] and ra["engine"] == "agy"
    assert _chuoi(ra) == [("agy", "engine"), ("agy", None)]


def test_loi_mang_cung_la_loi_tam(lam, tmp_path):
    cfg = lam(["claude:best", "codex:best"],
              claude=[{"rc": 1, "stderr": ["Error: connect ECONNRESET 1.2.3.4:443"]}], codex=[OK])
    ra, _ = _goi(cfg, tmp_path)
    assert ra["ok"] and ra["engine"] == "codex"
    assert [k for _, k in _chuoi(ra)] == ["network", "network", None]


def test_ma_0_thieu_artifact_cung_lui(lam, tmp_path):
    ra_json = tmp_path / "out" / "top.json"
    cfg = lam(["agy:best", "claude:best"], agy=[OK],
              claude=[dict(OK, write={str(ra_json): "x" * 900})])
    ra, _ = _goi(cfg, tmp_path, expect=[f"{ra_json}:800"])
    assert ra["ok"] and ra["engine"] == "claude"


def test_het_chuoi_van_loi_tam_la_ma_1(lam, tmp_path):
    cfg = lam(["agy:best", "codex:best"], agy=[AGY_TIMEOUT], codex=[AGY_TIMEOUT])
    ra, _ = _goi(cfg, tmp_path)
    assert ra["code"] == AC.ENGINE_ERROR and len(ra["tried"]) == 4


def test_cong_chu_noi_bo_KHONG_lui(lam, tmp_path):
    """`content` không phải lỗi tạm: engine khác viết cùng prompt, cùng khuôn."""
    bai = tmp_path / "bai.md"
    noi_bo = AC.CHU_NOI_BO[0]
    cfg = lam(["claude:best", "codex:best"],
              claude=[dict(OK, write={str(bai): "x " * 200 + noi_bo})], codex=[OK])
    ra, _ = _goi(cfg, tmp_path, expect=[f"{bai}:10"])
    assert ra["kind"] == "content" and len(ra["tried"]) == 1


# ── Hạn mức vẫn như cũ ──────────────────────────────────────────────────────────────

def test_claude_het_han_muc_thi_sang_agy_KHONG_thu_lai(lam, tmp_path):
    """Đúng cảnh Hot Data 19:00 nếu claude đứng đầu: hết hạn mức ⇒ sang ngay, không thử lại."""
    cfg = lam(["claude:best", "agy:best"], claude=[QUOTA], agy=[OK])
    ra, ngu = _goi(cfg, tmp_path)
    assert ra["ok"] and ra["engine"] == "agy"
    assert _chuoi(ra) == [("claude", "quota"), ("agy", None)] and ngu == []


# ── prompt quá trần argv của agy ────────────────────────────────────────────────────

def test_prompt_qua_tran_agy_thi_BO_QUA_agy_khong_dung_ca_chuoi(lam, tmp_path):
    cfg = lam(["agy:best", "claude:best"], agy=[OK], claude=[OK])
    ra, _ = _goi(cfg, tmp_path, prompt="x" * (AC.AGY_ARGV_LIMIT + 1))
    assert ra["ok"] and ra["engine"] == "claude"
    assert _chuoi(ra) == [("agy", "too_long"), ("claude", None)]


def test_prompt_qua_tran_ma_agy_la_engine_DUY_NHAT_van_ma_2(lam, tmp_path):
    cfg = lam(["agy:best"], agy=[OK])
    with pytest.raises(SC.ContractError):
        _goi(cfg, tmp_path, prompt="x" * (AC.AGY_ARGV_LIMIT + 1))


def test_bo_qua_agy_roi_moi_engine_con_lai_het_han_muc_van_la_ma_4(lam, tmp_path):
    cfg = lam(["agy:best", "claude:best"], agy=[OK], claude=[QUOTA])
    ra, _ = _goi(cfg, tmp_path, prompt="x" * (AC.AGY_ARGV_LIMIT + 1))
    assert ra["code"] == AC.QUOTA_EXHAUSTED


# ── P1-21: `--engine order` ─────────────────────────────────────────────────────────

def test_dau_order_lay_muc_dau():
    assert AC.dau_order({"order": ["agy:claude-opus-4-6-thinking", "codex:best"]}) == \
        ("agy", "claude-opus-4-6-thinking")
    assert AC.dau_order({"order": "codex"}) == ("codex", "best")


@pytest.mark.parametrize("order", [[], None, ["la:best"]])
def test_dau_order_rong_hoac_la_la_ma_2(order):
    with pytest.raises(SC.ContractError):
        AC.dau_order({"order": order})


def test_CLI_engine_order_chay_dung_thu_tu_engines_json(lam, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("agent_call_cli",
                                                  ROOT / "scripts" / "pipeline" / "agent_call.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    cfg = lam(["codex:best", "claude:best"], codex=[OK], claude=[OK])
    f_cfg = tmp_path / "engines.json"
    f_cfg.write_text(json.dumps(cfg), encoding="utf-8")
    f_p = tmp_path / "p.txt"
    f_p.write_text("x", encoding="utf-8")
    rc = cli.main(["--engine", "order", "--engines-config", str(f_cfg), "--prompt-file",
                   str(f_p), "--cwd", str(tmp_path), "--ledger", str(tmp_path / "so.jsonl"),
                   "--tools", "read"])
    assert rc == 0
    so = [json.loads(d) for d in (tmp_path / "so.jsonl").read_text(encoding="utf-8").splitlines()]
    assert so[0]["engine"] == "codex", "engine đầu phải là mục đầu của `order`"


# ── P1-26: prompt quá trần argv đi qua TỆP khi lượt gọi có tool ─────────────────────

SHIM_TEP = textwrap.dedent('''
    import json, os, re, sys
    bao = sys.argv[1]
    p = [a for a in sys.argv if a.startswith("--print=")][0][len("--print="):]
    m = re.search(r"`([^`]+nhiem-vu[.]md)`", p)
    them = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--add-dir"]
    nd = open(m.group(1), encoding="utf-8").read() if m else ""
    json.dump({"print_len": len(p), "tep": m.group(1) if m else None, "noi_dung": nd,
               "add_dir": them, "skip_perm": "--dangerously-skip-permissions" in sys.argv},
              open(bao, "w", encoding="utf-8"), ensure_ascii=False)
    print(json.dumps({"result": "OK"}))
''')


@pytest.fixture
def agy_tep(tmp_path):
    shim = tmp_path / "shim_tep.py"
    shim.write_text(SHIM_TEP, encoding="utf-8")
    bao = tmp_path / "bao.json"
    cfg = {"version": 1, "order": ["agy:best", "codex:best"], "skill_roots": [],
           "engines": {"agy": {"cmd": [sys.executable, str(shim), str(bao)], "best": "agy-best"},
                       "codex": {"cmd": ["khong-co-lenh-nay"], "best": "codex-best"}}}
    return cfg, bao


def test_prompt_45k_CO_tool_thi_agy_VAN_dung_dau_qua_tep(agy_tep, tmp_path):
    """Weekly Data 03/10: 45 402 ký tự ⇒ agy bị bỏ, rơi xuống codex. Nay agy chạy, đọc qua tệp."""
    cfg, bao = agy_tep
    prompt = ("Nghiên cứu tin tuần. " * 2200)[:45_402]
    ra, _ = _goi(cfg, tmp_path, prompt=prompt, tools="web,read,write")
    assert ra["ok"] and ra["engine"] == "agy", ra
    assert _chuoi(ra) == [("agy", None)]
    b = json.loads(bao.read_text(encoding="utf-8"))
    assert b["print_len"] < 2000, "argv chỉ còn câu dẫn ngắn"
    assert b["noi_dung"].startswith(prompt) and b["noi_dung"].rstrip().endswith(AC.AGY_PROMPT_HET)
    assert str(Path(b["tep"]).parent) in b["add_dir"], "thư mục tệp phải được --add-dir"
    assert b["skip_perm"], "headless tự từ chối read_file nếu không tự duyệt tool"
    assert not Path(b["tep"]).exists(), "tệp prompt phải bị xoá ngay sau lượt gọi"
    assert not str(b["tep"]).startswith(str(tmp_path)), "tệp không được nằm trong cwd (repo web)"
    so = [json.loads(l) for l in (tmp_path / "so.jsonl").read_text(encoding="utf-8").splitlines()]
    assert so[-1]["prompt_via"] == "file"


def test_prompt_ngan_van_qua_argv(agy_tep, tmp_path):
    cfg, bao = agy_tep
    ra, _ = _goi(cfg, tmp_path, prompt="ngắn thôi", tools="web,read")
    assert ra["ok"] and json.loads(bao.read_text(encoding="utf-8"))["tep"] is None


def test_build_command_tep_ma_KHONG_tool_la_ma_2(tmp_path):
    """Không tool ⇒ không có cửa đọc tệp ⇒ không tự nới quyền chỉ để đọc prompt."""
    with pytest.raises(SC.ContractError):
        AC.build_command("agy", "m", "x" * 40_000, prompt_file=tmp_path / "nhiem-vu.md")


def test_tep_prompt_bi_xoa_ca_khi_agy_loi(lam, tmp_path, monkeypatch):
    cfg = lam(["agy:best", "claude:best"], agy=[QUOTA], claude=[OK])
    tao = []
    goc = AC.ghi_tep_prompt_agy
    monkeypatch.setattr(AC, "ghi_tep_prompt_agy", lambda p: tao.append(goc(p)) or tao[-1])
    ra, _ = _goi(cfg, tmp_path, prompt="x" * (AC.AGY_ARGV_LIMIT + 1), tools="read")
    assert ra["ok"] and ra["engine"] == "claude"
    assert _chuoi(ra) == [("agy", "quota"), ("claude", None)]
    assert tao and not any(t.parent.exists() for t in tao)



# ── P1-27: mẫu tên model agy phân giải theo `agy models` lúc chạy ─────────────────────

DANH_MUC = ["gemini-3.8-flash-high", "gemini-3.7-flash-high", "claude-opus-5-5-low",
            "claude-opus-5-5-high", "claude-sonnet-5-5-high", "gpt-oss-120b-medium"]


def test_parse_agy_models_bo_dong_fetching():
    out = "Fetching available models...\ngemini-3.8-flash-high\tGemini 3.8 Flash (High)\n" \
          "claude-opus-5-5-high\tClaude Opus 5.5 (High)\n\n"
    assert AC.parse_agy_models(out) == ["gemini-3.8-flash-high", "claude-opus-5-5-high"]


@pytest.mark.parametrize("mau,mong", [
    ("claude-opus-*-high", "claude-opus-5-5-high"),
    ("gemini-*-flash-high", "gemini-3.8-flash-high"),
    ("claude-opus-*-medium", None),
    ("gemini-3.7-flash-high", "gemini-3.7-flash-high"),        # tên cứng: trả nguyên
    ("claude-opus-4-6-thinking", "claude-opus-4-6-thinking"),  # agy tự báo lỗi, chuỗi lùi
])
def test_chon_model_agy(mau, mong):
    assert AC.chon_model_agy(mau, DANH_MUC) == mong


def test_chon_model_agy_lay_PHIEN_BAN_cao_nhat():
    ds = ["claude-opus-4-6-high", "claude-opus-5-5-high", "claude-opus-6-high", "claude-opus-5-10-high"]
    assert AC.chon_model_agy("claude-opus-*-high", ds) == "claude-opus-6-high"
    assert AC.chon_model_agy("claude-opus-5-*-high", ds) == "claude-opus-5-10-high"


def test_mau_model_chay_bang_ban_moi_nhat(lam, tmp_path, monkeypatch):
    """Mac 03/10: tên cứng `claude-opus-4-6-thinking` biến mất sau khi agy tự cập nhật."""
    cfg = lam(["agy:claude-opus-*-high", "claude:best"], agy=[OK], claude=[OK])
    monkeypatch.setattr(AC, "agy_models", lambda *a, **k: list(DANH_MUC))
    ra, _ = _goi(cfg, tmp_path)
    assert ra["ok"] and ra["engine"] == "agy" and ra["model"] == "claude-opus-5-5-high"


def test_mau_khong_khop_thi_model_access_va_lui(lam, tmp_path, monkeypatch):
    cfg = lam(["agy:claude-opus-*-xhigh", "claude:best"], agy=[OK], claude=[OK])
    monkeypatch.setattr(AC, "agy_models", lambda *a, **k: list(DANH_MUC))
    ra, _ = _goi(cfg, tmp_path)
    assert ra["ok"] and ra["engine"] == "claude"
    assert _chuoi(ra) == [("agy", "model_access"), ("claude", None)]


def test_khong_hoi_duoc_agy_models_thi_lui(lam, tmp_path, monkeypatch):
    cfg = lam(["agy:gemini-*-flash-high", "claude:best"], agy=[OK], claude=[OK])
    monkeypatch.setattr(AC, "agy_models", lambda *a, **k: None)
    ra, _ = _goi(cfg, tmp_path)
    assert ra["engine"] == "claude" and "agy models" in ra["tried"][0]["error"]


def test_mac_dinh_KHONG_khoa_cung_ten_model_agy():
    """Repo không được cứng tên model agy — agy tự cập nhật và đổi tên (P1-27)."""
    cfg = AC.CAU_HINH_MAC_DINH
    agy = [m.partition(":")[2] for m in cfg["order"] if m.startswith("agy:")]
    agy.append(cfg["engines"]["agy"]["best"])
    assert agy and all(AC.la_mau_model(m) for m in agy), agy
    truyen = (ROOT / "scripts" / "runners" / "story" / "truyen_publish.py").read_text(encoding="utf-8")
    assert 'TRUYEN_HOOK_ENGINE", "agy:claude-opus-*-high"' in truyen


def test_agy_models_dem_theo_tien_trinh():
    goi = []

    def chay(argv, stdin, **kw):
        goi.append(argv)
        return {"rc": 0, "stdout": "gemini-3.8-flash-high\tG\n"}
    AC._AGY_MODELS.clear()
    try:
        assert AC.agy_models(runner=chay) == ["gemini-3.8-flash-high"]
        assert AC.agy_models(runner=chay) == ["gemini-3.8-flash-high"]
        assert len(goi) == 1 and goi[0][-1] == "models"
    finally:
        AC._AGY_MODELS.clear()
