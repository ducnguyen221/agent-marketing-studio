# -*- coding: utf-8 -*-
"""Một số phiên bản cho mọi manifest phát hành.

Nguồn: `pyproject.toml` (`[project] version`). Bump version phải đổi cùng lúc ba manifest
(`.claude-plugin/plugin.json`, mục plugin trong `.claude-plugin/marketplace.json`,
`.codex-plugin/plugin.json`) và thêm mục đầu `CHANGELOG.md`. Lệch một chỗ thì marketplace,
Codex và ghi chú phát hành nói ba phiên bản khác nhau — và người cài không biết tin cái nào.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"


def _doc(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _json(rel: str) -> dict:
    return json.loads(_doc(rel))


def nguon() -> str | None:
    m = re.search(r'^version\s*=\s*"([^"]+)"', _doc("pyproject.toml"), re.M)
    return m.group(1) if m else None


def cac_ban() -> dict:
    ra = {"pyproject.toml": nguon(),
          ".claude-plugin/plugin.json": _json(".claude-plugin/plugin.json").get("version"),
          ".codex-plugin/plugin.json": _json(".codex-plugin/plugin.json").get("version")}
    for p in _json(".claude-plugin/marketplace.json").get("plugins", []):
        ra[f".claude-plugin/marketplace.json#{p.get('name')}"] = p.get("version")
    return ra


def test_moi_manifest_chung_mot_version():
    ban = cac_ban()
    assert None not in ban.values(), f"thiếu trường version: {ban}"
    assert len(set(ban.values())) == 1, f"version lệch giữa các manifest: {ban}"
    assert re.fullmatch(r"\d+\.\d+\.\d+", nguon()), nguon()
    assert len(ban) >= 4, "marketplace.json phải có đúng mục plugin của repo này"


def test_changelog_mo_dau_bang_version_hien_tai():
    dau = re.search(r"^## (\S+)", _doc("CHANGELOG.md"), re.M)
    assert dau and dau.group(1) == nguon(), (
        f"mục đầu CHANGELOG.md phải là {nguon()}, đang là {dau.group(1) if dau else None}")


def test_ten_plugin_trung_ten_repo():
    ten = {_json(".claude-plugin/plugin.json")["name"], _json(".codex-plugin/plugin.json")["name"],
           *(p["name"] for p in _json(".claude-plugin/marketplace.json")["plugins"])}
    assert ten == {"agent-marketing-studio"}, ten


def test_manifest_tro_dung_thu_muc_skill_that():
    """Manifest trỏ một thư mục skill không có thì host cài xong thấy 0 skill — im lặng."""
    for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        duong = _json(rel)["skills"]
        assert duong.startswith("./"), f"{rel}: đường skill phải tương đối và bắt đầu bằng ./"
        thu_muc = (ROOT / duong).resolve()
        assert thu_muc == SKILLS.resolve(), f"{rel} trỏ {duong}, skill gốc ở .agents/skills/"
    ten = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
    assert len(ten) >= 4, ten
    for t in ten:
        fm = (SKILLS / t / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
        assert re.search(rf"^name:\s*{re.escape(t)}\s*$", fm, re.M), f"{t}: name khác tên thư mục"
        assert re.search(r"^description:", fm, re.M), f"{t}: thiếu description"
