# -*- coding: utf-8 -*-
"""Lớp gọi agent headless dùng chung — một hợp đồng cho `claude`, `codex`, `agy`.

## Vì sao có file này

Bốn đường ống (Daily Hot AI, Daily Hot Data, Weekly News, ducnguyen-ai writer) đều gọi
THẲNG một CLI duy nhất bằng một dòng shell riêng của từng script. Hệ quả đo được tối
19–20/09: hai lượt lịch chết sạch vì tài khoản Claude hết hạn mức, mỗi lượt còn thử lại
3 lần trong 30 giây — trong khi giờ mở lại cách đó **1–2 tiếng** và nằm sẵn trong chính
dòng lỗi. Sáu lượt đốt vô ích, không sản phẩm, không ai biết phải đợi tới lúc nào.

Ba thứ file này đổi:

1. **Đổi engine là đổi CẤU HÌNH, không phải đổi mã.** Thứ tự ưu tiên đọc từ
   `engines.json` của trạm (`order`). Muốn chạy `agy` trước `claude` thì đảo hai dòng
   trong một file JSON, không ai phải sửa script nào.
2. **Hết hạn mức là một loại lỗi RIÊNG, có mã thoát riêng (4) và có `resets_at`.** Mã 1
   nghĩa là "thử lại ngay", và 19/09 chứng minh làm thế là vô ích; mã 2 nghĩa là "sửa cấu
   hình", cũng sai. Bên gọi chỉ thấy mã thoát, nên "chờ tới giờ X" phải có mã của nó.
3. **Cổng "xong" là ARTIFACT trên đĩa, không phải mã thoát của CLI.** Cả bốn đường ống
   đều là "agent có tool, ghi file". `campaign_step.py:474-483` đã trả giá cho bài học
   này: CLI trả mã 0 mà `content.md` rỗng thì lượt đó vẫn hỏng. `--expect` biến luật đó
   thành hợp đồng dùng chung thay vì mỗi script tự kiểm một kiểu.

## Skill: NHÚNG vào prompt, không dựa vào discovery của từng CLI

Đo 20/09 (khảo sát `AGENT-CALL-DESIGN.md` §1.4): `agy` headless **không** nạp skill người
dùng — ba cwd khác nhau, kể cả repo git có `.agents/skills` thật, đều chỉ thấy 5 skill
builtin. `claude -p` thì có. Tức cùng một lệnh "dùng skill blog-writing" cho hai engine sẽ
là hai đầu vào KHÁC NHAU, và mọi so sánh chất lượng sau đó là so hai thứ không so được.

Nên mặc định là `--skills-mode inline`: lớp này tự đọc `SKILL.md` và chèn vào prompt dưới
dạng khối `<skill name="…">`. Cùng một chuỗi byte đi tới cả ba engine. Đường native
(`--skills-mode native`, chỉ `claude`) giữ lại để đo chênh lệch inline/native, không phải
để dùng thường ngày.

## Kỷ luật tiến trình

- **Không `shell=True`, `argv` luôn là danh sách.** Đường dẫn ở đây do người dùng đặt; một
  dấu cách hay dấu `&` đi qua shell là một lệnh khác hẳn lệnh ta định chạy.
- **Đóng stdin ngay sau khi ghi prompt** (`agy` thì `DEVNULL` từ đầu — nó đọc prompt qua
  argv). Bẫy `ps_pipe_breaks_native_stdin`: tiến trình con còn chờ stdin là còn treo, và
  đồng hồ im lặng sẽ giết nhầm một lượt đang chạy tốt.
- **Giết CẢ CÂY tiến trình con.** `claude`/`codex`/`agy` đều đẻ tiến trình cháu (node,
  sandbox, MCP). Giết mỗi tiến trình cha để lại cháu mồ côi giữ cổng và giữ file.
- **Hai đồng hồ**: tổng (`--timeout`) và im lặng (`--stall`) — nhưng đồng hồ im lặng chỉ
  được vũ trang cho engine THẬT SỰ phát sóng tiến độ (xem mục dưới).

## Đồng hồ im lặng chỉ đo được thứ có thể quan sát

Bench 20/09 (`BENCH-WRITER-2026-09-20.md` §7.1) giết nhầm một lượt `claude` ở đúng 420 s
**trong khi `bai.md` đã ghi xong và `--expect` đã xanh**. Nguyên nhân không phải chỉnh sai
con số: `claude -p --output-format json` **không in một byte nào cho tới câu trả lời cuối**,
nên với engine đó "im lặng" không phải bằng chứng treo — đồng hồ im lặng hoá ra chỉ là một
`--timeout` thứ hai, chặt hơn. Lượt thật đo được 250–440 s, mặc định cũ 180 s ⇒ gần như mọi
lượt sản xuất sẽ bị giết và trả mã 1 ("thử lại ngay") cho một lượt đã xong.

Luật bây giờ, và nó nói về BẰNG CHỨNG chứ không về con số:

1. **Không có nguồn tín hiệu thì không có đồng hồ.** `PHAT_SONG_TIEN_DO` khai engine nào
   phát tiến độ ra stdout ở định dạng lớp này chọn (`codex --json` có; `claude` và `agy`
   ở `--output-format json` thì không). Engine im lặng ⇒ đồng hồ im lặng **tắt**, có một
   dòng log nói rõ, và trần tổng `--timeout` là lưới an toàn duy nhất.
2. **Artifact lớn lên là tiến triển.** Với engine có phát sóng, mỗi nhịp lớp này đọc lại
   kích thước các `--expect`; byte tăng thì reset đồng hồ. Đúng luật "cổng là artifact".
3. **Trạm bật lại được** bằng `engines.<tên>.streams_progress: true` — dành cho ngày
   chuyển `claude` sang `--output-format stream-json`.

## Cổng chữ nội bộ

Bench §3 đo được 2/4 bài công khai viết thẳng chữ nội bộ của quy trình vào văn bài, tức nói
cho độc giả biết bài sinh ra từ một artifact nội bộ — và **cả hai người chấm bằng model đều
bỏ sót**. Model chấm văn phong; nó không đếm chữ. Nên cổng này nằm ở tầng máy: `--expect`
nào là bản công khai (`.md`/`.txt`/`.html`) thì bị soi trước khi lượt được tính là xong.

Xem `scripts/pipeline/agent_call.py` cho CLI, `AGENT-CALL-DESIGN.md` §2 cho hợp đồng gốc.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

# ── Mã thoát ────────────────────────────────────────────────────────────────────────
# 0/1/2/3 là hợp đồng ba trạm (`studio_contract.py`). 4 là phần mở rộng của làn này.
OK = SC.OK
ENGINE_ERROR = SC.ENGINE_ERROR
CONTRACT_ERROR = SC.CONTRACT_ERROR
STATION_MISSING = SC.STATION_MISSING
QUOTA_EXHAUSTED = 4

ENGINES = ("claude", "codex", "agy")

# Thứ tự phân loại CÓ Ý NGHĨA (mượn `bridges/lib/failure.mjs`): một dòng lỗi mạng cũng có
# thể chứa chữ "limit", nên `network` phải được hỏi TRƯỚC `quota`. Đảo thứ tự là đổi kết
# luận, không phải đổi thẩm mỹ.
KIND_ORDER = ("auth", "network", "quota", "model_access", "engine")

# Trần argv của `agy`: nó nhận prompt qua `--print=<prompt>`, không qua stdin. Vượt trần
# thì lỗi đến từ tầng hệ điều hành, thông điệp không nói gì về prompt — nên chặn ở đây,
# bằng mã 2 ("sửa cấu hình"), chứ không để nó thành một mã 1 khó hiểu.
AGY_ARGV_LIMIT = 30_000

# Engine nào THẬT SỰ phát tiến độ ra stdout ở định dạng lớp này chọn cho nó (xem docstring,
# mục "Đồng hồ im lặng"). Đây là một SỰ THẬT ĐO ĐƯỢC về từng CLI, không phải một tuỳ chọn:
# đổi dòng nào ở đây thì phải đổi `build_command` của engine đó trước.
#   claude  `-p --output-format json`  — im tới câu cuối (đo 20/09, lượt bị giết ở 420 s)
#   codex   `exec --json`              — JSONL liên tục: thread.started · item.completed…
#   agy     `--output-format json`     — im tới câu cuối
PHAT_SONG_TIEN_DO = {"claude": False, "codex": True, "agy": False}


class QuotaExhausted(SC.StudioError):
    """Hết hạn mức ở MỌI engine trong chuỗi — chạy lại NGAY là vô ích, phải đợi `resets_at`."""

    code = QUOTA_EXHAUSTED


# ── Cấu hình ────────────────────────────────────────────────────────────────────────

CAU_HINH_MAC_DINH = {
    "version": 1,
    # Thứ tự ưu tiên. Sửa MỘT mảng này là đổi được engine chính của cả bốn đường ống.
    "order": ["claude:best", "agy:claude-opus-4-6-thinking", "agy:gemini-3.8-flash-high"],
    "engines": {
        "claude": {"cmd": "claude", "best": "opus", "extra_args": []},
        "codex": {"cmd": "codex", "best": "gpt-5.6-sol", "extra_args": []},
        "agy": {"cmd": "agy", "best": "gemini-3.8-flash-high", "extra_args": []},
    },
    "skill_roots": [],
    "ledger": "",
}


def config_path(station=None) -> Path:
    """`$AGENT_CALL_ENGINES` → `<trạm>/_agent-call/engines.json` → `<trạm>/engine/engines.json`.

    Cấu hình theo MÁY nằm ở trạm, không nằm trong repo: repo là public và không được khoá
    cứng engine nào — cùng luật với `writer_cmd`. Biến môi trường đứng trước để máy chạy
    lịch thật ghi đè được mà không phải sửa file trong cây git.

    Vì sao KHÔNG để mặc định trong `<trạm>/engine/`: `run.ps1` của mọi chiến dịch coi sự
    **tồn tại** của `<trạm>/engine` là tín hiệu "engine đã dọn về trạm" và bỏ đường lùi sang
    engine dùng chung trong thư mục nhà của máy nguồn. Đặt một file cấu hình vào đó là tự
    tạo thư mục ⇒ lượt lịch kế tiếp đi tìm runner trong thư mục chỉ có JSON rồi thoát mã 2.
    Đã xảy ra thật đêm 20→21/09 và kịp phát hiện trước lượt 19:00; nay có cổng riêng canh —
    `scripts/lib/engine_dir.py`. Thư mục riêng `_agent-call/` không mang nghĩa nào với
    `run.ps1`; nhánh `engine/` giữ lại để sau khi khối 3-A dọn engine về trạm thì cấu hình
    nằm cạnh engine vẫn đọc được.
    """
    # `secret_env` chứ không `os.environ`: chế độ cài `embedded` giữ cấu hình máy ở
    # `<repo>/.env`, và biến đọc thẳng môi trường thì điền vào đó vô tác dụng.
    bien = (SP.secret_env("AGENT_CALL_ENGINES") or "").strip()
    if bien:
        return Path(bien).expanduser()
    goc = SP.root(station)
    rieng = goc / "_agent-call" / "engines.json"
    if rieng.is_file():
        return rieng
    return goc / "engine" / "engines.json"


def load_config(path=None, station=None) -> dict:
    """Đọc `engines.json`, trộn lên mặc định. Thiếu file ⇒ dùng mặc định (không phải lỗi).

    JSON hỏng thì NỔ có tên file: nuốt lỗi ở đây nghĩa là lặng lẽ chạy bằng thứ tự engine
    mặc định trong khi người dùng tin mình vừa đổi thứ tự — đúng loại sai lầm không ai
    phát hiện cho tới khi hoá đơn về.
    """
    p = Path(path).expanduser() if path else config_path(station)
    cfg = json.loads(json.dumps(CAU_HINH_MAC_DINH))  # bản sao sâu, rẻ và không cần import
    if not p.is_file():
        return cfg
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SC.ContractError(f"{p} không phải JSON hợp lệ: {e}") from e
    if not isinstance(data, dict):
        raise SC.ContractError(f"{p} phải là một object JSON, không phải {type(data).__name__}")
    for khoa, gt in data.items():
        if khoa == "engines" and isinstance(gt, dict):
            for ten, spec in gt.items():
                cfg["engines"].setdefault(ten, {}).update(spec or {})
        else:
            cfg[khoa] = gt
    return cfg


def resolve_model(engine: str, model: str, cfg: dict) -> str:
    """`best` ⇒ model tốt nhất mà TRẠM khai cho engine đó. Không có ⇒ lỗi hợp đồng.

    Không đoán một model mặc định: mỗi engine đổi tên model vài tháng một lần, và một cú
    đoán sai trở thành `model_access` lúc 21:00 trong khi cái đúng chỉ là một dòng JSON.
    """
    if engine not in cfg.get("engines", {}):
        raise SC.ContractError(
            f"engine {engine!r} không có trong engines.json (có: "
            f"{', '.join(sorted(cfg.get('engines', {}))) or 'không có engine nào'})")
    if model and model != "best":
        return model
    best = (cfg["engines"][engine] or {}).get("best") or ""
    if not best:
        raise SC.ContractError(f"engines.json không khai `engines.{engine}.best` — "
                               f"truyền --model tường minh hoặc khai model tốt nhất vào cấu hình")
    return best


def build_chain(engine, model, cfg, fallback=None) -> list[tuple[str, str]]:
    """-> [(engine, model)…] — engine được yêu cầu đứng đầu, phần còn lại là dây an toàn.

    `--engine` luôn thắng `order`: người gọi nói rõ muốn engine nào thì lớp này không được
    âm thầm đổi ý ở lượt đầu. `order` chỉ quyết định thứ tự của những engine CÒN LẠI, và
    bản thân nó là thứ Đức sửa để đổi engine chính (bằng cách đổi cả `--engine` của script
    trạm, hoặc để script truyền `--engine` từ chính dòng đầu `order`).
    """
    dau = (engine, resolve_model(engine, model, cfg))
    chuoi = [dau]
    tho = fallback if fallback is not None else cfg.get("order") or []
    if isinstance(tho, str):
        tho = [x for x in tho.split(",") if x.strip()]
    for muc in tho:
        eng, _, mdl = str(muc).partition(":")
        eng, mdl = eng.strip(), mdl.strip()
        if eng not in ENGINES:
            raise SC.ContractError(f"chuỗi fallback có engine lạ: {muc!r} (chỉ có {', '.join(ENGINES)})")
        cap = (eng, resolve_model(eng, mdl or "best", cfg))
        if cap not in chuoi:
            chuoi.append(cap)
    return chuoi


# ── Skill: tìm và nhúng ─────────────────────────────────────────────────────────────

def skill_roots(cfg: dict) -> list[Path]:
    """Gốc để tìm skill: cấu hình trạm trước, rồi `<repo>/.agents/skills` làm đường lùi."""
    goc = []
    for r in cfg.get("skill_roots") or []:
        p = Path(str(r)).expanduser()
        if p.is_dir():
            goc.append(p)
    repo = SP.repo_root()
    if repo:
        cua_repo = repo / ".agents" / "skills"
        if cua_repo.is_dir() and cua_repo not in goc:
            goc.append(cua_repo)
    return goc


def find_skill(name: str, roots) -> Path:
    """Tìm `SKILL.md` của một skill. `plugin:skill` tra theo khuôn plugin, `skill` tra thẳng.

    Không tìm thấy ⇒ **mã 2**, không phải chạy tiếp mà thiếu skill: lượt đó sẽ ra một bài
    viết sai giọng và không ai biết vì sao, vì CLI vẫn trả mã 0.
    """
    plugin, _, ten = name.partition(":")
    if not ten:
        plugin, ten = "", plugin
    for r in roots:
        ung = []
        if plugin:
            ung += [r / plugin / "skills" / ten / "SKILL.md", r / f"{plugin}:{ten}" / "SKILL.md"]
        ung.append(r / ten / "SKILL.md")
        for p in ung:
            if p.is_file():
                return p
        # Đường lùi: quét MỘT cấp plugin (`<gốc>/<plugin>/skills/<tên>/SKILL.md`). Quét một
        # cấp chứ không đệ quy: cây plugin có `references/` và `examples/` cũng chứa `.md`,
        # và bắt nhầm một file ví dụ làm skill thì lượt đó sai giọng mà vẫn mã 0.
        for p in sorted(r.glob(f"*/skills/{ten}/SKILL.md")):
            if p.is_file():
                return p
    raise SC.ContractError(
        f"không tìm thấy skill {name!r} trong: "
        f"{', '.join(str(r) for r in roots) or '(chưa khai skill_roots trong engines.json)'}")


def inline_skills(prompt: str, names, roots) -> str:
    """Chèn nội dung `SKILL.md` vào ĐẦU prompt — cùng chuỗi byte cho cả ba engine.

    Đứng trước prompt chứ không sau: mọi engine đều đọc phần đầu kỹ hơn phần đuôi, và
    prompt của đường ống vốn kết bằng mệnh lệnh ("ghi file X") — chen tài liệu vào giữa
    mệnh lệnh và dấu chấm hết là cách làm loãng đúng câu quan trọng nhất.
    """
    ten = [t.strip() for t in (names or []) if str(t).strip()]
    if not ten:
        return prompt
    khoi = []
    for t in ten:
        f = find_skill(t, roots)
        khoi.append(f'<skill name="{t}">\n{f.read_text(encoding="utf-8").strip()}\n</skill>')
    return ("<skills>\nCác kỹ năng dưới đây áp dụng cho nhiệm vụ này. Đọc trước khi làm.\n\n"
            + "\n\n".join(khoi) + "\n</skills>\n\n" + prompt)


# ── Map tập tool trừu tượng sang cờ từng engine ─────────────────────────────────────

TOOLS_CLAUDE = {
    "web": ["WebSearch", "WebFetch"],
    "read": ["Read", "Glob", "Grep"],
    "write": ["Write", "Edit"],
}


def _tools_list(tools) -> list[str]:
    if isinstance(tools, str):
        tools = [t for t in tools.split(",") if t.strip()]
    ra = []
    for t in tools or []:
        t = str(t).strip()
        if not t:
            continue
        if not (t in TOOLS_CLAUDE or t.startswith("shell:")):
            raise SC.ContractError(
                f"tool trừu tượng lạ: {t!r} — chỉ có {', '.join(sorted(TOOLS_CLAUDE))} và shell:<lệnh>")
        if t not in ra:
            ra.append(t)
    return ra


def claude_tools(tools, *, native_skill=False) -> list[str]:
    """`web,read,write,shell:curl` -> tên tool thật của Claude Code."""
    ra = []
    for t in _tools_list(tools):
        if t.startswith("shell:"):
            ra.append(f"Bash({t.split(':', 1)[1]}:*)")
        else:
            ra += TOOLS_CLAUDE[t]
    if native_skill:
        ra.append("Skill")
    return ra


def codex_sandbox(tools, *, allow_full=False) -> str:
    """Tập tool -> tier sandbox của codex. `shell:*` cần `danger-full-access`, mà cửa đó
    phải được TRẠM mở tường minh (`engines.codex.allow_full_access`) — lớp gọi không tự
    nới quyền cho mình."""
    tl = _tools_list(tools)
    if any(t.startswith("shell:") for t in tl) and allow_full:
        return "danger-full-access"
    if "write" in tl or any(t.startswith("shell:") for t in tl):
        return "workspace-write"
    return "read-only"


def _tim_lenh(ten: str) -> str:
    """Giải tên lệnh thành đường dẫn thật. Không thấy ⇒ trả NGUYÊN tên.

    Trên Windows, `codex` và `claude` được cài dưới dạng shim `.cmd`/`.ps1`, còn
    `CreateProcess` (thứ `subprocess` gọi khi không qua shell) **không áp `PATHEXT`** —
    nên `["codex", "exec", …]` nổ `FileNotFoundError` dù `codex` chạy tốt trong terminal,
    và lớp này báo nhầm "chưa cài Codex" (mã 3) cho một trạm đã cài đủ. Đo 20/09: đúng
    lỗi đó ở lượt kiểm khói đầu tiên.

    Trả nguyên tên khi không thấy chứ không nổ ở đây: "không có trên PATH" là một KẾT LUẬN
    của lượt gọi (mã 3, kèm tên lệnh), không phải một ngoại lệ lúc dựng argv.
    """
    import shutil
    return shutil.which(ten) or ten


def build_command(engine: str, model: str, prompt: str, *, tools=(), cwd=None, cfg=None,
                  native_skill=False) -> tuple[list[str], str | None]:
    """-> (argv, văn bản đẩy vào stdin hoặc None).

    Prompt đi đường nào là thuộc tính của TỪNG CLI, không phải lựa chọn: `claude` và
    `codex` đọc stdin; `agy` từ chối cả ba đường stdin (bridge đã đo) và chỉ nhận qua
    `--print=`. Đó là lý do hàm này trả về cả argv lẫn stdin thay vì chỉ argv.
    """
    cfg = cfg or CAU_HINH_MAC_DINH
    spec = (cfg.get("engines") or {}).get(engine) or {}
    # `cmd` nhận cả chuỗi lẫn danh sách: trạm nào gọi CLI qua một wrapper (`pwsh -File …`,
    # `node …`, một shim đo đạc) thì khai được nguyên dòng lệnh mà vẫn không đi qua shell.
    tho = spec.get("cmd") or engine
    cmd = [str(x) for x in tho] if isinstance(tho, (list, tuple)) else [str(tho)]
    cmd[0] = _tim_lenh(cmd[0])
    them = [str(x) for x in (spec.get("extra_args") or [])]

    if engine == "claude":
        argv = [*cmd, "-p", "--model", model, "--output-format", "json"]
        ds = claude_tools(tools, native_skill=native_skill)
        if ds:
            argv += ["--allowedTools", *ds]
        return argv + them, prompt

    if engine == "codex":
        argv = [*cmd, "exec", "-m", model, "--json", "--skip-git-repo-check",
                "-s", codex_sandbox(tools, allow_full=bool(spec.get("allow_full_access")))]
        if cwd:
            argv += ["-C", str(cwd)]
        return argv + them, prompt

    if engine == "agy":
        if len(prompt) > AGY_ARGV_LIMIT:
            raise SC.ContractError(
                f"prompt {len(prompt)} ký tự vượt trần argv của agy ({AGY_ARGV_LIMIT}) — "
                f"agy không nhận prompt qua stdin. Rút gọn prompt hoặc chọn engine khác.")
        argv = [*cmd, "--model", model, "--output-format", "json", "--print-timeout", "0"]
        if _tools_list(tools):
            # Print-mode không có ai bấm duyệt: tool cần duyệt sẽ bị auto-deny và lượt trả
            # về rỗng mà vẫn mã 0 (đo 20/09 với `/usage`). Đây là cửa DUY NHẤT của agy.
            argv.append("--dangerously-skip-permissions")
        if cwd:
            argv += ["--add-dir", str(cwd)]
        argv.append(f"--print={prompt}")
        return argv + them, None

    raise SC.ContractError(f"engine lạ: {engine!r} (chỉ có {', '.join(ENGINES)})")


# ── Nhận biết hết hạn mức và các loại lỗi khác ──────────────────────────────────────

MAU_QUOTA = re.compile(
    r"hit your (?:session|usage) limit|usage limit reached|quota exceeded|"
    r"resource[_ ]exhausted|rate limit exceeded|out of (?:credits|quota)", re.I)
MAU_AUTH = re.compile(
    r"not logged in|please (?:run )?log ?in|unauthenticated|invalid api key|"
    r"authentication fail|unauthorized|\b401\b", re.I)
MAU_NETWORK = re.compile(
    r"enotfound|econnreset|econnrefused|etimedout|getaddrinfo|socket hang up|"
    r"network (?:error|unreachable)|tls handshake", re.I)
MAU_MODEL = re.compile(
    r"model (?:not found|not available|unknown)|unknown model|no access to model|"
    r"does not have access to|invalid model", re.I)
MAU_AGY_ERROR = re.compile(r"AGY_ERROR:\s*(\{.*?\})\s*$", re.M | re.S)
MAU_GIO = re.compile(r"resets?\s+(?:at\s+)?(\d{1,2}):(\d{2})\s*([ap])m\s*(?:\(([^)]+)\))?", re.I)
MAU_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)")


def agy_error(stderr: str) -> dict | None:
    """agy ≥ 1.2.6 in `AGY_ERROR: {status, code, retryable, error_id}` ra stderr trước khi
    thoát. Đọc CÁI NÀY trước khi đọc chuỗi chữ: chuỗi chữ đổi theo bản, trường `status`
    là hợp đồng."""
    m = MAU_AGY_ERROR.search(stderr or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def parse_resets(text: str, *, now=None) -> str | None:
    """Rút giờ mở lại ra ISO. Ưu tiên chuỗi ISO có sẵn, rồi tới `resets 7:50pm (TZ)`.

    Claude in giờ mở lại NGAY TRONG dòng lỗi — đó là thứ đắt giá nhất trong cả thông điệp,
    và là thứ hai lượt chết tối 19–20/09 đã có sẵn mà không ai đọc. Giờ đã qua trong hôm
    nay ⇒ hiểu là NGÀY MAI: "resets 7:50pm" nhận lúc 21:00 không thể là 19:50 vừa rồi.
    """
    t = text or ""
    m = MAU_ISO.search(t)
    if m:
        return m.group(1)
    m = MAU_GIO.search(t)
    if not m:
        return None
    gio, phut, buoi, tz = int(m.group(1)), int(m.group(2)), m.group(3).lower(), m.group(4)
    if gio == 12:
        gio = 0
    if buoi == "p":
        gio += 12
    tzinfo = _tz(tz)
    bay_gio = (now or datetime.now(tzinfo)).astimezone(tzinfo)
    moc = bay_gio.replace(hour=gio, minute=phut, second=0, microsecond=0)
    if moc <= bay_gio:
        moc += timedelta(days=1)
    return moc.isoformat()


def _tz(ten):
    if ten:
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(ten.strip())
        except Exception:
            pass
    return datetime.now().astimezone().tzinfo or timezone.utc


def parse_agy_usage(response: str) -> list[dict]:
    """Bóc bảng `/usage` của agy -> [{pool, label, remaining_pct, resets_at}, …].

    Mỗi dòng là TSV: `<hồ>\\t<nhãn>\\t<còn %>\\t<ISO mở lại>`. Hai hồ TÁCH BIỆT (Gemini ·
    Claude+GPT) là lý do `agy:claude-opus-4-6-thinking` chạy được khi tài khoản Claude đã
    hết hạn mức — nên phải đọc theo hồ, không gộp thành một con số.
    """
    ra = []
    for dong in (response or "").splitlines():
        phan = [c.strip() for c in dong.split("\t") if c.strip()]
        if len(phan) < 3:
            continue
        pct = None
        for c in phan:
            m = re.fullmatch(r"(\d{1,3})\s*%", c)
            if m:
                pct = int(m.group(1))
                break
        iso = None
        for c in phan:
            m = MAU_ISO.fullmatch(c) or MAU_ISO.match(c)
            if m:
                iso = m.group(1)
                break
        if pct is None and iso is None:
            continue
        ra.append({"pool": phan[0], "label": phan[1] if len(phan) > 1 else "",
                   "remaining_pct": pct, "resets_at": iso})
    return ra


def agy_usage(cfg=None, *, timeout=120, env=None, runner=None) -> list[dict]:
    """Hỏi hạn mức agy — **0 token, 0 lượt model** (`--print="/usage"` là lệnh gạch chéo
    do chính CLI trả lời, đo 20/09 trên 1.2.7: `usage.total_tokens=0, num_turns=0`).

    Rẻ tới mức đáng hỏi ngay khi agy báo hết hạn mức mà dòng lỗi không kèm giờ mở lại:
    không có `resets_at` thì mã 4 mất hết ý nghĩa (lịch không biết đợi tới bao giờ) và
    người dùng nhận đúng một chữ "fail".

    CẢNH BÁO cho người gọi từ Git Bash/MSYS: `--print="/usage"` bị MSYS đổi `/usage` thành
    một đường dẫn Windows, và lượt đó rơi vào model thật (đo được: 18 k token). Hàm này
    spawn thẳng, không qua shell, nên không dính — nhưng gõ tay thì phải gõ trong PowerShell.
    """
    cfg = cfg or CAU_HINH_MAC_DINH
    spec = (cfg.get("engines") or {}).get("agy") or {}
    tho = spec.get("cmd") or "agy"
    cmd = [str(x) for x in tho] if isinstance(tho, (list, tuple)) else [str(tho)]
    cmd[0] = _tim_lenh(cmd[0])
    argv = [*cmd, "--output-format", "json", "--print-timeout", "0", "--print=/usage"]
    chay = runner or run_process
    try:
        r = chay(argv, None, timeout=timeout, stall=timeout, env=env)
    except Exception:
        return []
    data = SC.last_json_line(r.get("stdout") or "")
    if not isinstance(data, dict):
        return []
    return parse_agy_usage(data.get("response") or "")


def agy_resets_at(usage_rows) -> str | None:
    """Mốc mở lại đáng quan tâm: hồ đã CẠN trước, không có hồ nào cạn thì mốc gần nhất."""
    can = [r["resets_at"] for r in usage_rows or []
           if r.get("resets_at") and (r.get("remaining_pct") or 0) <= 0]
    if can:
        return sorted(can)[0]
    moi = [r["resets_at"] for r in usage_rows or [] if r.get("resets_at")]
    return sorted(moi)[0] if moi else None


def classify(engine: str, rc: int, stdout: str, stderr: str, *, produced=False) -> dict:
    """-> {"kind": …|None, "resets_at": …|None, "error": …} cho MỘT lượt gọi.

    `produced=True` (lượt đã sinh token/artifact) thì KHÔNG bao giờ là `quota`: hết hạn
    mức luôn xảy ra ở đầu lượt, còn đứt giữa chừng sau khi đã chạy là lỗi engine bình
    thường — chuyển engine lúc đó là làm lại từ đầu một việc đã xong nửa chừng.
    (Cùng điều kiện với `bridges/lib/failure.mjs:72-76`.)
    """
    if rc == 0:
        return {"kind": None, "resets_at": None, "error": ""}
    gop = f"{stdout or ''}\n{stderr or ''}"

    # Mã thoát trước, chuỗi chữ sau — chuỗi chữ đổi theo bản, mã thoát là hợp đồng.
    ae = agy_error(stderr) if engine == "agy" else None
    if ae:
        status = str(ae.get("status") or ae.get("code") or "").upper()
        if not produced and ("RESOURCE_EXHAUSTED" in status or "429" in status
                             or "QUOTA" in status or "RATE_LIMIT" in status):
            return {"kind": "quota", "resets_at": parse_resets(gop),
                    "error": str(ae.get("message") or status or "agy: hết hạn mức")}
        if "UNAUTHENTICATED" in status or "PERMISSION_DENIED" in status or "401" in status:
            return {"kind": "auth", "resets_at": None, "error": status}

    for kind in KIND_ORDER:
        mau = {"auth": MAU_AUTH, "network": MAU_NETWORK, "quota": MAU_QUOTA,
               "model_access": MAU_MODEL}.get(kind)
        if mau is None:
            break
        if not mau.search(gop):
            continue
        if kind == "quota" and produced:
            continue
        return {"kind": kind,
                "resets_at": parse_resets(gop) if kind == "quota" else None,
                "error": _dong_loi(gop, mau)}
    return {"kind": "engine", "resets_at": None,
            "error": _duoi(stderr) or _duoi(stdout) or f"{engine} thoát với mã {rc}"}


def _dong_loi(text: str, mau) -> str:
    for d in (text or "").splitlines():
        if mau.search(d):
            return d.strip()[:400]
    return ""


def _duoi(text: str, dong=4) -> str:
    co = [d for d in (text or "").splitlines() if d.strip()]
    return "\n".join(co[-dong:])[:800]


def extract_usage(engine: str, stdout: str) -> dict | None:
    """Token/credit của lượt, nếu CLI có trả. Không có ⇒ None (không bịa số 0).

    Số 0 và "không đo được" là hai chuyện khác nhau: sổ ghi 0 token cho một lượt viết bài
    dài sẽ làm mọi phép so chi phí về sau sai mà vẫn trông như có dữ liệu.
    """
    if not stdout:
        return None
    if engine == "codex":
        # JSONL: lấy `turn.completed` cuối cùng có `usage`.
        for dong in reversed(stdout.splitlines()):
            d = dong.strip()
            if not d.startswith("{"):
                continue
            try:
                obj = json.loads(d)
            except ValueError:
                continue
            u = obj.get("usage") or (obj.get("turn") or {}).get("usage")
            if isinstance(u, dict):
                return u
        return None
    data = SC.last_json_line(stdout)
    if not isinstance(data, dict):
        return None
    u = data.get("usage")
    if isinstance(u, dict):
        if engine == "claude" and data.get("total_cost_usd") is not None:
            u = {**u, "total_cost_usd": data["total_cost_usd"]}
        return u
    return None


def _da_sinh(engine: str, stdout: str) -> bool:
    """Lượt này đã chạm model chưa? (dùng cho điều kiện `produced` của `classify`)"""
    u = extract_usage(engine, stdout) or {}
    for k in ("total_tokens", "output_tokens", "input_tokens", "total_token_usage"):
        v = u.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return True
        if isinstance(v, dict) and any(isinstance(x, (int, float)) and x > 0 for x in v.values()):
            return True
    return False


# ── Chạy một lượt: hai đồng hồ, giết cả cây ─────────────────────────────────────────

def kill_tree(proc) -> None:
    """Giết tiến trình con VÀ mọi tiến trình cháu.

    Cả ba CLI đều đẻ cháu (node, sandbox, MCP server). Giết mỗi cha để lại cháu mồ côi
    còn giữ cổng và còn ghi file — lượt sau chạy lên là tranh file với một tiến trình
    không còn ai sở hữu. Trên Windows `taskkill /T /F`; POSIX thì giết cả nhóm tiến trình
    (đã tách nhóm lúc spawn, xem `_spawn`).
    """
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           capture_output=True, timeout=30)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=10)
    except Exception:
        pass


def engine_phat_song(engine: str, cfg=None) -> bool:
    """Engine này có phát sóng tiến độ ra stdout không? Trạm khai đè được.

    Không có thì đồng hồ im lặng vô nghĩa — xem docstring đầu file. Trạm nào đổi cách gọi
    CLI (vd `claude --output-format stream-json`) thì khai `streams_progress: true` ở
    `engines.json`, không phải sửa mã.
    """
    spec = ((cfg or {}).get("engines") or {}).get(engine) or {}
    if "streams_progress" in spec:
        return bool(spec["streams_progress"])
    return bool(PHAT_SONG_TIEN_DO.get(engine, False))


def _hoi_tien_trien(probe):
    """Hỏi dấu tiến triển. Probe nổ ⇒ None = "không biết", KHÔNG phải "đứng yên".

    Phân biệt này quyết định sống chết của một lượt: `stat()` một file đang bị engine ghi
    dở có thể ném lỗi trên Windows, và hiểu lỗi đó thành "không tiến triển" là giết đúng
    lượt đang chạy tốt nhất.
    """
    if probe is None:
        return None
    try:
        return probe()
    except Exception:
        return None


def _spawn(argv, *, cwd, env, co_stdin: bool):
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kw["start_new_session"] = True
    return subprocess.Popen(
        argv, cwd=str(cwd) if cwd else None, env=env,
        stdin=subprocess.PIPE if co_stdin else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1, **kw)


def run_process(argv, stdin_text=None, *, cwd=None, env=None, timeout=1800, stall=180,
                progress=None) -> dict:
    """Chạy một tiến trình dưới hai đồng hồ -> {rc, stdout, stderr, ms, timed_out, reason}.

    `rc = -1` khi bị giết vì quá giờ: không có mã thoát thật nên không được giả vờ có một
    mã. Bẫy `ma_thoat_khong_phai_phep_thu` — mã thoát chỉ nói tiến trình đã kết thúc thế
    nào, còn "lượt này có sản phẩm không" là câu hỏi khác, trả lời bằng `--expect`.

    `stall = 0` ⇒ TẮT hẳn đồng hồ im lặng. Người gọi tắt nó khi engine không phát sóng
    tiến độ: đo sự im lặng của một tiến trình vốn im lặng là đo chính cái đồng hồ.

    `progress` là một hàm không đối số trả về một "dấu tiến triển" so sánh được (lớp gọi
    truyền tổng byte của các `--expect`). Dấu đổi ⇒ reset đồng hồ im lặng. Đây là nguồn
    tín hiệu THỨ HAI, bên cạnh dòng ra stdout — và nó là thứ duy nhất quan sát được khi
    engine đang chạy một tool dài mà chưa nói gì.
    """
    t0 = time.monotonic()
    p = _spawn(argv, cwd=cwd, env=env, co_stdin=stdin_text is not None)
    out, err = [], []
    moc = [time.monotonic()]

    def doc(pipe, kho):
        try:
            for dong in pipe:
                kho.append(dong)
                moc[0] = time.monotonic()
        except Exception:
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    luong = [threading.Thread(target=doc, args=(p.stdout, out), daemon=True),
             threading.Thread(target=doc, args=(p.stderr, err), daemon=True)]
    for t in luong:
        t.start()

    if stdin_text is not None:
        # Ghi xong thì ĐÓNG NGAY. Tiến trình con còn chờ EOF là còn im lặng, và đồng hồ
        # im lặng sẽ giết một lượt chưa kịp bắt đầu (bẫy `ps_pipe_breaks_native_stdin`).
        try:
            p.stdin.write(stdin_text)
        except Exception:
            pass
        finally:
            try:
                p.stdin.close()
            except Exception:
                pass

    het_gio, ly_do = False, ""
    dau = [_hoi_tien_trien(progress)]   # mốc gốc: lần hỏi đầu KHÔNG được tính là "vừa tiến"
    while True:
        if p.poll() is not None:
            break
        gio = time.monotonic()
        if timeout and gio - t0 > timeout:
            het_gio, ly_do = True, f"quá tổng {timeout}s"
            break
        if stall and gio - moc[0] > stall:
            # Hỏi dấu tiến triển NGAY TRƯỚC KHI GIẾT, không theo nhịp riêng: đồng hồ im
            # lặng có thể ngắn hơn bất kỳ nhịp nào ta chọn, và một lượt bị giết oan vì
            # "chưa tới nhịp hỏi" thì cũng oan y như không hỏi. Cách này còn rẻ hơn — mỗi
            # chu kỳ `stall` mới đi `stat()` một lần.
            moi = _hoi_tien_trien(progress)
            if moi is not None and moi != dau[0]:
                dau[0], moc[0] = moi, gio
            else:
                het_gio, ly_do = True, f"im lặng quá {stall}s"
                break
        time.sleep(0.2)
    if het_gio:
        kill_tree(p)
    for t in luong:
        t.join(timeout=5)
    rc = p.poll()
    return {"rc": -1 if het_gio else (0 if rc is None else rc),
            "stdout": "".join(out), "stderr": "".join(err),
            "ms": int((time.monotonic() - t0) * 1000),
            "timed_out": het_gio, "reason": ly_do}


# ── Cổng artifact ───────────────────────────────────────────────────────────────────

# `/c/kho/...` — họ đường dẫn của Git Bash/MSYS: một chữ cái ổ đĩa làm đoạn đầu.
MAU_MSYS = re.compile(r"^/([A-Za-z])(?:/(.*))?$")
MAU_O_DIA = re.compile(r"^[A-Za-z]:[\\/]")


def _he_windows() -> bool:
    """Hệ đường dẫn đang chạy có phải của Windows không — hỏi `os.path`, không hỏi `sys.platform`.

    Hỏi qua `os.path` để một máy kiểm được CẢ HAI họ (test đổi `os.path` sang
    `posixpath`/`ntpath`). Dùng `sys.platform` thì nhánh macOS chỉ chạy thật trên macOS —
    tức chưa từng chạy, cho tới đúng hôm di trú.
    """
    return os.path.sep == "\\"


def chuan_hoa_duong(tho) -> Path:
    """Nhận CẢ HAI họ đường dẫn; đường không giải được ⇒ mã 2 kèm chỉ dẫn, không im lặng.

    Bench 20/09 (§7.2): `--expect "/c/kho/.../research.json"` gõ từ Git Bash bị Python
    hiểu thành một đường **không tồn tại**, nên cổng artifact báo "CLI trả mã 0 nhưng thiếu
    artifact" cho cả 4 nhánh — trong khi cả 4 file đã ghi đúng chỗ — và trả **mã 1**, tức
    bảo lịch chạy lại một lượt đã thành công. Hỏng câm, và hỏng theo hướng đắt tiền.

    Hai luật:
    · `/c/...` trên Windows ⇒ dịch sang `C:/...` (đường Git Bash là đường HỢP LỆ, chỉ khác họ).
    · Đường tuyệt đối của họ kia mà không dịch được ⇒ `ContractError` (mã 2). "Sửa cấu
      hình" mới là sự thật ở đây; "thử lại ngay" thì thử bao nhiêu lần cũng vậy.
    """
    s = str(tho).strip().strip('"')
    if not s:
        raise SC.ContractError("--expect rỗng")
    if _he_windows():
        if MAU_O_DIA.match(s):
            return Path(s).expanduser()
        if s.startswith("/") or s.startswith("\\"):
            m = MAU_MSYS.match(s.replace("\\", "/"))
            if m:
                return Path(m.group(1).upper() + ":/" + (m.group(2) or "")).expanduser()
            raise SC.ContractError(
                f"--expect {s!r} là đường POSIX tuyệt đối, máy này dùng đường Windows. "
                f"Viết đường Windows (D:/... ) hoặc đường kiểu Git Bash có ổ đĩa (/d/...), "
                f"hoặc đường tương đối so với --cwd.")
        return Path(s).expanduser()
    if MAU_O_DIA.match(s):
        raise SC.ContractError(
            f"--expect {s!r} là đường ổ đĩa Windows, máy này dùng đường POSIX. "
            f"Viết đường POSIX tuyệt đối hoặc đường tương đối so với --cwd.")
    return Path(s).expanduser()


def parse_expect(spec: str) -> tuple[Path, int]:
    """`đường/dẫn:1200` -> (Path, 1200). Không có phần số ⇒ ngưỡng 1 byte (chỉ đòi tồn tại).

    Tách từ PHẢI và chỉ khi đuôi toàn chữ số — nếu không thì ổ đĩa `C:` trên Windows sẽ bị
    hiểu là ngưỡng byte và mọi `--expect` đường tuyệt đối đều hỏng.
    """
    s = str(spec)
    duong, dau, so = s.rpartition(":")
    if dau and so.isdigit() and duong:
        return chuan_hoa_duong(duong), int(so)
    return chuan_hoa_duong(s), 1


def _dau_tien_trien(specs, cwd):
    """Dấu tiến triển QUAN SÁT ĐƯỢC của một lượt: tổng byte các artifact `--expect`.

    Đây là thứ duy nhất nhìn thấy được khi engine đang chạy một tool dài mà chưa in gì.
    Chỉ đọc kích thước, không đọc nội dung: file đang ghi dở đọc ra cũng vô nghĩa.
    """
    return tuple(e["bytes"] for e in check_expect(specs, cwd=cwd))


def check_expect(specs, *, cwd=None) -> list[dict]:
    ra = []
    for s in specs or []:
        p, nguong = parse_expect(s)
        if not p.is_absolute() and cwd:
            p = Path(cwd) / p
        co = p.is_file()
        kich = p.stat().st_size if co else 0
        ra.append({"path": str(p), "min_bytes": nguong, "bytes": kich,
                   "ok": bool(co and kich >= nguong)})
    return ra


# ── Cổng chữ nội bộ lọt vào bản công khai ──────────────────────────────────────────
#
# Bench 20/09 (§3): hai trong bốn bài công khai viết thẳng chữ nội bộ của quy trình vào
# văn bài — tức nói cho độc giả biết bài được sinh từ một artifact nội bộ. CẢ HAI người
# chấm bằng model đều bỏ sót, nên cổng phải nằm ở tầng máy.
#
# Các chuỗi dưới đây dựng bằng `chr()` chứ không viết literal, cùng lý do với
# `tests/test_no_identity_leak.py`: file này nằm trong cây git và chính nó có thể bị đem
# soi bằng `--check-text`. Một cổng mang sẵn thứ nó đi tìm là một cổng luôn đỏ vì chính nó.
_BO = "b" + chr(0x1ED9)                        # bộ
_DU = "d" + chr(0x1EEF)                        # dữ
_KIEN = "ki" + chr(0x1EC7) + "n"               # kiện
_LIEU = "li" + chr(0x1EC7) + "u"               # liệu
_NGHIEN_CUU = "nghi" + chr(0xEA) + "n c" + chr(0x1EE9) + "u"      # nghiên cứu
_DONG_BANG = chr(0x111) + chr(0xF3) + "ng b" + chr(0x103) + "ng"  # đóng băng

# Nhóm 1 — chữ CHỈ tồn tại trong quy trình nội bộ. Thấy là đỏ, không cần ngữ cảnh.
CHU_NOI_BO = [
    _BO + " " + _DU + " " + _KIEN,
    _BO + " " + _NGHIEN_CUU,
    _BO + " " + _DONG_BANG,
]

# Nhóm 2 — chữ tiếng Việt BÌNH THƯỜNG, chỉ hỏng khi dùng theo nghĩa trỏ-vào-quy-trình.
# "Meta mở bộ dữ liệu huấn luyện" là câu đúng của một bài tin dữ liệu và không được chặn;
# "chưa bên nào phản hồi trong bộ dữ liệu" thì độc giả không biết "bộ dữ liệu" nào — đó
# chính là chỗ khuôn nội bộ lòi ra. Nên nhóm này đòi có dấu trỏ đi kèm.
_TRO_TRUOC = ("trong", "theo", chr(0x1EDF))    # trong · theo · ở
_TRO_SAU = ("n" + chr(0xE0) + "y", "tr" + chr(0xEA) + "n")   # này · trên
CHU_NOI_BO_CO_NGU_CANH = [_BO + " " + _DU + " " + _LIEU]

# `(?:^|\W)` trước dấu trỏ là bắt buộc, không phải làm đẹp: thiếu nó thì "mở bộ dữ liệu"
# khớp dấu trỏ "ở" nằm trong chữ "mở" — cổng đỏ vào đúng câu tiếng Việt lành lặn, và một
# cổng hay báo oan là cổng sẽ bị tắt.
_MAU_NOI_BO = [(c, re.compile(re.escape(c), re.I)) for c in CHU_NOI_BO] + [
    (c, re.compile(r"(?:(?:^|\W)(?:%s)\s+%s)|(?:%s\s+(?:%s)(?:\W|$))"
                   % ("|".join(_TRO_TRUOC), re.escape(c), re.escape(c), "|".join(_TRO_SAU)), re.I))
    for c in CHU_NOI_BO_CO_NGU_CANH]

# Chỉ soi BẢN CÔNG KHAI. `*-top.json`, `research.json`… là artifact nội bộ của chính đường
# ống — chữ nội bộ nằm ở đó là đúng chỗ, chặn nó là chặn nhầm.
DUOI_CONG_KHAI = {".md", ".txt", ".html", ".htm"}


def quet_chu_noi_bo(text: str) -> list[dict]:
    """-> [{"chu", "dong", "trich"}…]. Rỗng = sạch.

    Chuẩn hoá NFC trước khi so: cùng một chữ "ộ" có hai cách mã hoá, và một cổng thua vì
    tổ hợp dấu thì thua im lặng.
    """
    import unicodedata
    ra = []
    for so, dong in enumerate(unicodedata.normalize("NFC", text or "").splitlines(), 1):
        for chu, mau in _MAU_NOI_BO:
            m = mau.search(dong)
            if m:
                ra.append({"chu": chu, "dong": so, "trich": dong.strip()[:160]})
    return ra


def quet_file_cong_khai(paths, *, cwd=None, loc_duoi=True) -> list[dict]:
    """Soi các artifact là BẢN CÔNG KHAI -> danh sách phát hiện (có `path`).

    Nói đúng cái nó đo: "file X dòng N có chữ Y". Không suy ra "bài này sẽ bị bóc mẽ" —
    cổng không đo được điều đó (luật phát ngôn của `blog_gates.py`).

    `loc_duoi=False` khi NGƯỜI gọi chỉ đích danh từng tệp (`--check-text`): lúc đó phần
    lọc theo đuôi là đoán thay người, và đoán sai thì cổng im lặng không soi gì cả.
    """
    ra = []
    for tho in paths or []:
        p = Path(tho)
        if not p.is_absolute() and cwd:
            p = Path(cwd) / p
        if (loc_duoi and p.suffix.lower() not in DUOI_CONG_KHAI) or not p.is_file():
            continue
        try:
            noi_dung = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for hit in quet_chu_noi_bo(noi_dung):
            ra.append({"path": str(p), **hit})
    return ra


# ── Sổ ─────────────────────────────────────────────────────────────────────────────

def ledger_path(cfg: dict, override=None, station=None) -> Path:
    if override:
        return Path(override).expanduser()
    tu_cfg = (cfg or {}).get("ledger") or ""
    if tu_cfg:
        return Path(str(tu_cfg)).expanduser()
    return SP.root(station) / "_bench" / "agent-call.jsonl"


def append_ledger(path, record: dict) -> None:
    """Một dòng JSON cho MỖI lượt gọi — kể cả lượt bị bỏ vì hết hạn mức.

    Ghi sổ không bao giờ được làm hỏng lượt gọi: đĩa đầy hay thư mục chỉ-đọc thì mất sổ,
    còn bài viết vẫn phải ra. Nên mọi lỗi ở đây đều bị nuốt — có chủ đích, và đây là chỗ
    DUY NHẤT trong file này được phép nuốt lỗi.
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Vòng gọi chính ──────────────────────────────────────────────────────────────────

# Lỗi nào thì đi tiếp trong chuỗi, lỗi nào thì dừng ngay. Nguyên tắc: chuyển engine chỉ
# đáng khi engine HIỆN TẠI chắc chắn không dùng được lúc này (hết hạn mức, chưa đăng nhập,
# không có model đó). Một lỗi engine bình thường thì chuyển sang engine khác chỉ là đốt
# thêm một lượt nữa cho cùng một nguyên nhân — đó là việc của lịch chạy lại, không phải
# của lớp này.
CHUYEN_ENGINE = ("quota", "auth", "model_access", "station")
MA_CUOI = {"auth": STATION_MISSING, "station": STATION_MISSING,
           "model_access": CONTRACT_ERROR, "quota": QUOTA_EXHAUSTED}

TRAN_CHO = 3 * 3600  # `--on-quota wait`: chờ tối đa 3 tiếng, quá thì trả mã 4 cho lịch.


def call(prompt: str, *, engine: str, model="best", tools=(), skills=(), skills_mode="inline",
         cwd=None, timeout=1800, stall=180, expect=(), on_quota="fallback", fallback=None,
         cfg=None, ledger=None, station=None, env=None, sleep=time.sleep,
         content_gate=True) -> dict:
    """Gọi một agent headless theo chuỗi engine -> dict kết quả (KHÔNG ném lỗi engine).

    Trả về `{"ok":bool,"code":int,"engine":…,"model":…,"ms":…,"tried":[…],"expect":[…]}`.
    Lỗi hợp đồng (engine lạ, skill không thấy, prompt quá trần) thì NÉM `ContractError`:
    đó là thứ phải sửa cấu hình, không phải kết quả để bên gọi cân nhắc.
    """
    if engine not in ENGINES:
        raise SC.ContractError(f"engine lạ: {engine!r} (chỉ có {', '.join(ENGINES)})")
    if on_quota not in ("fallback", "wait", "fail"):
        raise SC.ContractError(f"--on-quota lạ: {on_quota!r} (fallback|wait|fail)")
    if skills_mode not in ("inline", "native"):
        raise SC.ContractError(f"--skills-mode lạ: {skills_mode!r} (inline|native)")
    cfg = cfg if cfg is not None else load_config(station=station)
    cwd = Path(cwd).expanduser().resolve() if cwd else Path.cwd()
    if not cwd.is_dir():
        raise SC.ContractError(f"--cwd không phải thư mục: {cwd}")
    # Kiểm hình dạng `--expect` TRƯỚC khi spawn. Một đường dẫn sai họ là lỗi hợp đồng, và
    # phát hiện nó SAU lượt gọi nghĩa là đã đốt 250–440 giây cùng $2–4 cho một câu trả lời
    # sẽ bị vứt đi (bench 20/09, §7.2).
    for s in expect or ():
        parse_expect(s)

    ds_skill = [s.strip() for s in (skills.split(",") if isinstance(skills, str) else list(skills))
                if str(s).strip()]
    # Dựng SẴN bản inline kể cả khi người gọi xin `native`: chỉ `claude` có đường native,
    # và một engine không có đường đó mà vẫn chạy prompt KHÔNG kèm skill thì ra một bài
    # sai giọng với mã thoát 0 — hỏng theo đúng kiểu không ai phát hiện. Rơi về inline và
    # NÓI RA, thay vì lặng lẽ bỏ skill.
    prompt_inline = inline_skills(prompt, ds_skill, skill_roots(cfg)) if ds_skill else prompt

    chuoi = build_chain(engine, model, cfg, fallback)
    so = ledger_path(cfg, ledger, station)
    tried, da_cho = [], False

    i = 0
    while i < len(chuoi):
        eng, mdl = chuoi[i]
        native = bool(ds_skill and skills_mode == "native" and eng == "claude")
        if native:
            p_eng = prompt + "\n\nDùng skill: " + ", ".join(ds_skill)
        else:
            if ds_skill and skills_mode == "native":
                SC.log(f"[agent-call] {eng} không có đường skill native — nhúng vào prompt")
            p_eng = prompt_inline
        argv, stdin_text = build_command(eng, mdl, p_eng, tools=tools, cwd=cwd, cfg=cfg,
                                         native_skill=native)
        # Đồng hồ im lặng CHỈ vũ trang cho engine thật sự phát sóng tiến độ (docstring đầu
        # file). Với engine im tới câu cuối, "im lặng" không phải bằng chứng treo — và một
        # đồng hồ đo cái nó không quan sát được thì chỉ giết nhầm, không cứu được gì.
        phat_song = engine_phat_song(eng, cfg)
        stall_luot = stall if phat_song else 0
        SC.log(f"[agent-call] {eng}:{mdl} — {len(p_eng)} ký tự prompt, tool={','.join(_tools_list(tools)) or '(không)'}")
        if stall and not stall_luot:
            SC.log(f"[agent-call] {eng} không phát tiến độ ra stdout — tắt đồng hồ im lặng "
                   f"({stall}s), chỉ còn trần tổng {timeout}s")
        try:
            r = run_process(argv, stdin_text, cwd=cwd, env=env, timeout=timeout,
                            stall=stall_luot,
                            progress=(lambda: _dau_tien_trien(expect, cwd)) if expect else None)
        except FileNotFoundError:
            r = {"rc": 127, "stdout": "", "stderr": f"không có {argv[0]!r} trên PATH",
                 "ms": 0, "timed_out": False, "reason": "station"}
            loai = {"kind": "station", "resets_at": None, "error": r["stderr"]}
        else:
            if r["timed_out"]:
                loai = {"kind": "engine", "resets_at": None, "error": r["reason"]}
            else:
                loai = classify(eng, r["rc"], r["stdout"], r["stderr"],
                                produced=_da_sinh(eng, r["stdout"]))

        if loai["kind"] == "quota" and not loai["resets_at"] and eng == "agy":
            # `/usage` là 0 token; hỏi nó rẻ hơn nhiều so với trả về một mã 4 không kèm
            # giờ mở lại — mã 4 không có `resets_at` thì lịch không biết đợi tới bao giờ.
            loai["resets_at"] = agy_resets_at(agy_usage(cfg, env=env))

        usage = extract_usage(eng, r["stdout"])
        ktra = check_expect(expect, cwd=cwd)
        thieu = [e for e in ktra if not e["ok"]]
        if loai["kind"] is None and thieu:
            loai = {"kind": "engine", "resets_at": None,
                    "error": "CLI trả mã 0 nhưng thiếu artifact: "
                             + ", ".join(f"{e['path']} ({e['bytes']}/{e['min_bytes']} B)" for e in thieu)}
        ro = []
        if loai["kind"] is None and content_gate and expect:
            ro = quet_file_cong_khai([e["path"] for e in ktra], cwd=cwd)
            if ro:
                # KHÔNG chuyển engine vì chuyện này: engine khác cũng viết từ cùng một
                # prompt, cùng một khuôn. Mã 1 = lịch soạn lại một bản khác, và bản mới đi
                # qua đúng cổng này.
                loai = {"kind": "content", "resets_at": None,
                        "error": "bản công khai lọt chữ nội bộ: "
                                 + "; ".join(f"{Path(h['path']).name}:{h['dong']} {h['chu']!r}"
                                             for h in ro[:5])}

        luot = {"engine": eng, "model": mdl, "ms": r["ms"], "rc": r["rc"],
                "kind": loai["kind"], "resets_at": loai["resets_at"],
                "error": loai["error"][:600] if loai["error"] else "",
                "usage": usage}
        tried.append(luot)
        append_ledger(so, {"ts": datetime.now(timezone.utc).isoformat(), **luot,
                           "cwd": str(cwd), "prompt_bytes": len(p_eng.encode("utf-8")),
                           "skills": ds_skill, "skills_mode": skills_mode,
                           "tools": _tools_list(tools),
                           "expect": ktra, "noi_bo": ro, "stall": stall_luot,
                           "chain_pos": i, "chain_len": len(chuoi)})

        if loai["kind"] is None:
            return {"ok": True, "code": OK, "engine": eng, "model": mdl, "ms": r["ms"],
                    "usage": usage, "text": _tra_loi(eng, r["stdout"]), "expect": ktra,
                    "tried": tried}

        if loai["kind"] == "quota" and on_quota == "wait" and not da_cho:
            cho = _giay_cho(loai["resets_at"])
            if cho is not None and cho <= TRAN_CHO:
                SC.log(f"[agent-call] {eng}: hết hạn mức, chờ {int(cho)}s tới {loai['resets_at']}")
                sleep(cho + 300)  # +5' đệm: giờ reset của nhà cung cấp không phải giây chính xác
                da_cho = True
                continue  # thử LẠI chính engine này, không tụt xuống engine kém hơn
            SC.log(f"[agent-call] {eng}: hết hạn mức nhưng giờ mở lại quá xa/không đọc được — không chờ")

        if loai["kind"] in CHUYEN_ENGINE and (on_quota != "fail" or loai["kind"] != "quota"):
            ly_do = f"{loai['kind']}: {loai['error'][:120]}"
            if i + 1 < len(chuoi):
                SC.log(f"[agent-call] chuyển engine ({ly_do}) -> {chuoi[i + 1][0]}:{chuoi[i + 1][1]}")
            i += 1
            continue
        break

    cuoi = tried[-1] if tried else {"kind": "engine", "error": "không lượt nào chạy"}
    loai_cuoi = cuoi.get("kind") or "engine"
    het_quota = all(t.get("kind") == "quota" for t in tried) and bool(tried)
    if het_quota:
        ma = QUOTA_EXHAUSTED
    else:
        ma = MA_CUOI.get(loai_cuoi, ENGINE_ERROR)
    mo_lai = sorted([t["resets_at"] for t in tried if t.get("resets_at")]) or [None]
    return {"ok": False, "code": ma, "kind": loai_cuoi, "error": cuoi.get("error", ""),
            "engine": cuoi.get("engine"), "model": cuoi.get("model"),
            "resets_at": mo_lai[0], "tried": tried,
            "expect": check_expect(expect, cwd=cwd)}


def _tra_loi(engine: str, stdout: str) -> str:
    """Câu trả lời cuối của agent, nếu bóc được. Không bóc được ⇒ chuỗi rỗng, không đoán."""
    if engine == "codex":
        cuoi = ""
        for dong in (stdout or "").splitlines():
            d = dong.strip()
            if not d.startswith("{"):
                continue
            try:
                obj = json.loads(d)
            except ValueError:
                continue
            item = obj.get("item") or {}
            if item.get("type") in ("agent_message", "assistant_message"):
                cuoi = item.get("text") or item.get("content") or cuoi
        return str(cuoi or "").strip()
    data = SC.last_json_line(stdout or "")
    if isinstance(data, dict):
        for k in ("response", "result", "text", "content"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _giay_cho(resets_at):
    if not resets_at:
        return None
    try:
        moc = datetime.fromisoformat(str(resets_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moc.tzinfo is None:
        moc = moc.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return max(0.0, (moc - datetime.now(moc.tzinfo)).total_seconds())
