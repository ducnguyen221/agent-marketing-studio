# -*- coding: utf-8 -*-
"""Security and schema checks using disposable synthetic repository trees."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.check_skill_catalog import (
    CatalogError,
    _write_map,
    check_map,
    load_catalog,
    render_skill_table,
    validate_catalog,
)


def _tree(tmp_path: Path, *, supports=None, path=".agents/skills/alpha/SKILL.md",
          maturity="candidate", evidence=None, pilot_routes=None):
    root = tmp_path / "repo"
    skill_path = root / ".agents" / "skills" / "alpha" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "---\nname: alpha\ndescription: Synthetic test skill.\n---\nBody.\n",
        encoding="utf-8",
    )
    (root / ".agents").mkdir(exist_ok=True)
    catalog = {
        "schema": 1,
        "skills": [{
            "id": "alpha", "path": path, "summary": "Synthetic capability.",
            "use_when": ["test fixture"], "do_not_use_when": ["outside test"],
            "stages": ["standalone"], "modes": ["consult"],
            "requires": {"consult": {"read": [], "write": []}},
            "outputs": ["synthetic output"], "supports": supports or [],
            "references": [], "maturity": maturity, "evidence": evidence or [],
        }],
        "pilot_routes": pilot_routes or [],
    }
    (root / ".agents" / "skill-catalog.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8"
    )
    (root / "MAP.md").write_text(f"before\n{START}\n{END}\nafter\n", encoding="utf-8")
    return root, catalog


START = "<!-- SKILL_ROUTING:START -->"
END = "<!-- SKILL_ROUTING:END -->"


def test_valid_synthetic_catalog_and_generated_map_table(tmp_path):
    root, catalog = _tree(tmp_path)
    assert validate_catalog(root, load_catalog(root)) == []
    table = render_skill_table(catalog)
    assert "| alpha | test fixture | synthetic output | outside test |" in table
    assert check_map(f"{START}\n{table}\n{END}", table) == []


def test_real_skill_file_missing_catalog_entry_is_rejected(tmp_path):
    root, catalog = _tree(tmp_path)
    extra = root / ".agents" / "skills" / "orphan" / "SKILL.md"
    extra.parent.mkdir()
    extra.write_text("---\nname: orphan\ndescription: Synthetic orphan.\n---\n", encoding="utf-8")

    issues = validate_catalog(root, catalog)

    assert any("orphan" in issue and "catalog" in issue for issue in issues)


def test_catalog_text_cannot_break_generated_markdown_cells(tmp_path):
    root, catalog = _tree(tmp_path)
    catalog["skills"][0]["use_when"] = ["x | <b>unsafe</b>\nnext"]
    table = render_skill_table(catalog)
    assert "x \\| &lt;b&gt;unsafe&lt;/b&gt; next" in table


@pytest.mark.parametrize("bad_path", ["../outside.md", "C:/outside.md", "missing/SKILL.md"])
def test_paths_must_be_relative_existing_files_inside_repo(tmp_path, bad_path):
    root, _ = _tree(tmp_path, path=bad_path)
    assert any("path missing or escapes" in issue for issue in validate_catalog(root, load_catalog(root)))


def test_symlink_cannot_escape_repository(tmp_path):
    root, _ = _tree(tmp_path, path=".agents/skills/alpha/link.md")
    outside = tmp_path / "outside.md"
    outside.write_text("synthetic", encoding="utf-8")
    link = root / ".agents" / "skills" / "alpha" / "link.md"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this host")
    assert any("path missing or escapes" in issue for issue in validate_catalog(root, load_catalog(root)))


def test_duplicate_yaml_keys_fail_closed(tmp_path):
    root, _ = _tree(tmp_path)
    (root / ".agents" / "skill-catalog.yaml").write_text(
        "schema: 1\nschema: 1\nskills: []\npilot_routes: []\n", encoding="utf-8"
    )
    with pytest.raises(CatalogError, match="duplicate YAML key"):
        load_catalog(root)


def test_duplicate_ids_across_skills_and_pilot_routes_are_reported(tmp_path):
    root, catalog = _tree(tmp_path)
    catalog["pilot_routes"] = [{
        "id": "alpha", "handler": "direct-consultation", "playbook": "playbook.md",
        "modes": ["consult"], "use_when": ["synthetic"], "outputs": ["answer"],
        "limits": ["no state write"],
    }]
    (root / "playbook.md").write_text("synthetic", encoding="utf-8")
    assert any("duplicate id" in issue for issue in validate_catalog(root, catalog))


def test_support_cycles_unknown_ids_and_router_support_are_rejected(tmp_path):
    root, catalog = _tree(tmp_path, supports=["missing", "marketing-routing", "alpha"])
    issues = validate_catalog(root, catalog)
    assert any("unsupported skill id" in issue for issue in issues)
    assert any("router cannot appear" in issue for issue in issues)
    assert any("supports cycle" in issue for issue in issues)


def test_verified_requires_evidence_and_pilot_is_consult_only(tmp_path):
    root, catalog = _tree(tmp_path, maturity="verified")
    catalog["pilot_routes"] = [{
        "id": "research", "handler": "direct-consultation", "playbook": "playbook.md",
        "modes": ["execute"], "use_when": ["synthetic"], "outputs": ["answer"],
        "limits": ["no state write"],
    }]
    (root / "playbook.md").write_text("synthetic", encoding="utf-8")
    issues = validate_catalog(root, catalog)
    assert any("verified maturity requires evidence" in issue for issue in issues)
    assert any("consult-only" in issue for issue in issues)


@pytest.mark.parametrize("text", [
    f"{START}\nbody\n{END}\n{START}\n{END}",
    f"{END}\n{START}",
])
def test_map_bad_marker_sets_are_rejected_without_mutation(tmp_path, text):
    root, catalog = _tree(tmp_path)
    map_path = root / "MAP.md"
    map_path.write_text(text, encoding="utf-8")
    before = map_path.read_bytes()
    issues = check_map(map_path.read_text(encoding="utf-8"), render_skill_table(catalog))
    assert issues
    assert map_path.read_bytes() == before


def test_map_writer_changes_only_the_marked_section(tmp_path):
    root, _ = _tree(tmp_path)
    map_path = root / "MAP.md"
    _write_map(map_path, "| generated | table |\n|---|---|")
    updated = map_path.read_text(encoding="utf-8")
    assert updated.startswith("before\n")
    assert updated.endswith("\nafter\n")
    assert "| generated | table |" in updated


def test_map_writer_refuses_invalid_markers_without_any_write(tmp_path):
    root, _ = _tree(tmp_path)
    map_path = root / "MAP.md"
    map_path.write_text(f"{END}\n{START}", encoding="utf-8")
    before = map_path.read_bytes()
    with pytest.raises(CatalogError, match="reversed"):
        _write_map(map_path, "generated")
    assert map_path.read_bytes() == before


def test_catalog_read_errors_are_not_treated_as_empty(tmp_path):
    root, _ = _tree(tmp_path)
    (root / ".agents" / "skill-catalog.yaml").unlink()
    with pytest.raises(CatalogError, match="missing"):
        load_catalog(root)


def test_skill_must_live_at_canonical_agents_skills_path(tmp_path):
    root, catalog = _tree(tmp_path, path="elsewhere/alpha/SKILL.md")
    wrong = root / "elsewhere" / "alpha" / "SKILL.md"
    wrong.parent.mkdir(parents=True)
    wrong.write_text("---\nname: alpha\ndescription: test\n---\n", encoding="utf-8")
    assert any("path must be .agents/skills" in issue for issue in validate_catalog(root, catalog))


def test_fixture_file_cannot_prove_verified_maturity(tmp_path):
    root, catalog = _tree(tmp_path, maturity="verified", evidence=["tests/fixtures/example.yaml"])
    fixture = root / "tests" / "fixtures" / "example.yaml"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("synthetic: true\n", encoding="utf-8")
    assert any("verified evidence must be reviewed output" in issue for issue in validate_catalog(root, catalog))


def test_consult_write_schema_rejects_arbitrary_state_tag(tmp_path):
    root, catalog = _tree(tmp_path)
    catalog["skills"][0]["requires"]["consult"]["write"] = ["campaign.status=approved"]
    assert any("consult writes may only" in issue for issue in validate_catalog(root, catalog))


def test_reference_budget_applies_to_new_reference(tmp_path):
    root, catalog = _tree(tmp_path)
    ref = root / "large.md"
    ref.write_text("x\n" * 251, encoding="utf-8")
    catalog["skills"][0]["references"] = ["large.md"]
    assert any("reference exceeds 250 lines" in issue for issue in validate_catalog(root, catalog))


def _install_real_baseline_fixture(root: Path) -> tuple[Path, dict]:
    from scripts.check_skill_catalog import REFERENCE_BASE_COMMIT

    assert REFERENCE_BASE_COMMIT == "4e62cfc0f9baff0a5b3f5f924f0f2f4b918c8b27"
    manifest = Path(__file__).resolve().parents[1] / ".agents" / "skill-reference-baseline.json"
    baseline_data = json.loads(manifest.read_text(encoding="utf-8"))
    reference_name = "knowledge/data_model/DATA_MODEL.md"
    source = Path(__file__).resolve().parents[1] / reference_name
    expected_hash = baseline_data["files"][reference_name]
    import hashlib
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_hash
    target = root / reference_name
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    target_manifest = root / ".agents" / "skill-reference-baseline.json"
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_manifest.write_bytes(manifest.read_bytes())
    catalog = load_catalog(root)
    catalog["skills"][0]["references"] = [reference_name]
    return target_manifest, catalog


def test_reference_exemption_uses_real_pinned_baseline_manifest(tmp_path):
    root, _ = _tree(tmp_path)
    _, catalog = _install_real_baseline_fixture(root)
    assert validate_catalog(root, catalog) == []


def test_reference_baseline_lock_accepts_equivalent_crlf_manifest(tmp_path):
    root, _ = _tree(tmp_path)
    manifest_path, catalog = _install_real_baseline_fixture(root)
    raw_lf = manifest_path.read_bytes().replace(b"\r\n", b"\n")
    manifest_path.write_bytes(raw_lf)
    assert validate_catalog(root, catalog) == []
    manifest_path.write_bytes(raw_lf.replace(b"\n", b"\r\n"))
    assert validate_catalog(root, catalog) == []


@pytest.mark.parametrize("mutation", ["modify_hash", "add_entry"])
def test_modified_baseline_manifest_cannot_exempt_new_reference(tmp_path, mutation):
    import hashlib
    root, catalog = _tree(tmp_path)
    manifest_path, catalog = _install_real_baseline_fixture(root)
    ref = root / "new-large-reference.md"
    ref.write_text("x\n" * 251, encoding="utf-8")
    catalog["skills"][0]["references"].append("new-large-reference.md")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "modify_hash":
        data["files"]["knowledge/data_model/DATA_MODEL.md"] = hashlib.sha256(ref.read_bytes()).hexdigest()
    else:
        data["files"]["new-large-reference.md"] = hashlib.sha256(ref.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    issues = validate_catalog(root, catalog)
    assert any("reference baseline manifest bytes differ" in issue for issue in issues)
    assert any("reference exceeds 250 lines" in issue for issue in issues)


def test_map_write_preserves_outside_crlf_bytes(tmp_path):
    root, _ = _tree(tmp_path)
    path = root / "MAP.md"
    path.write_bytes(f"before\r\n{START}\r\nold\r\n{END}\r\nafter\r\n".encode())
    _write_map(path, "| generated | table |\n|---|---|")
    data = path.read_bytes()
    assert data.startswith(b"before\r\n") and data.endswith(b"\r\nafter\r\n")
    assert data.count(b"\r\n") == 6


def test_cli_invalid_catalog_never_writes_map(tmp_path, capsys):
    root, catalog = _tree(tmp_path)
    catalog["skills"][0]["requires"]["consult"]["write"] = ["campaign.approved"]
    (root / ".agents" / "skill-catalog.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    before = (root / "MAP.md").read_bytes()
    result = subprocess.run([sys.executable, "-m", "scripts.check_skill_catalog", "--root", str(root), "--write-map"], capture_output=True, text=True)
    assert result.returncode == 1
    assert (root / "MAP.md").read_bytes() == before
    assert not list(root.glob("tmp*"))


@pytest.mark.parametrize("mutation", ["missing_field", "skills_wrong_type"])
def test_cli_invalid_schema_returns_validation_error_before_render(tmp_path, mutation):
    root, catalog = _tree(tmp_path)
    if mutation == "missing_field":
        del catalog["skills"][0]["use_when"]
    else:
        catalog["skills"] = {"alpha": catalog["skills"][0]}
    (root / ".agents" / "skill-catalog.yaml").write_text(
        yaml.safe_dump(catalog), encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_skill_catalog", "--root", str(root)],
        capture_output=True, text=True,
    )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "catalog check error" not in result.stderr
    assert result.stderr.strip()
    assert result.stdout == ""


def test_cli_unreadable_skill_is_exit_two(tmp_path):
    root, catalog = _tree(tmp_path)
    (root / ".agents" / "skills" / "alpha" / "SKILL.md").write_bytes(b"\xff")
    result = subprocess.run([sys.executable, "-m", "scripts.check_skill_catalog", "--root", str(root)], capture_output=True, text=True)
    assert result.returncode == 2


def test_reference_directory_is_a_validation_error_exit_one(tmp_path):
    root, catalog = _tree(tmp_path)
    directory = root / "knowledge" / "playbooks"
    directory.mkdir(parents=True)
    catalog["skills"][0]["references"] = ["knowledge/playbooks"]
    (root / ".agents" / "skill-catalog.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "scripts.check_skill_catalog", "--root", str(root)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "reference must be a file" in result.stderr


def test_reference_utf8_read_error_is_exit_two(tmp_path):
    root, catalog = _tree(tmp_path)
    ref = root / "reference.md"
    ref.write_bytes(b"\xff")
    catalog["skills"][0]["references"] = ["reference.md"]
    (root / ".agents" / "skill-catalog.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "scripts.check_skill_catalog", "--root", str(root)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "cannot read reference" in result.stderr


def test_reference_os_read_error_is_exit_two(tmp_path, monkeypatch, capsys):
    root, catalog = _tree(tmp_path)
    ref = root / "reference.md"
    ref.write_text("valid utf-8\n", encoding="utf-8")
    catalog["skills"][0]["references"] = ["reference.md"]
    (root / ".agents" / "skill-catalog.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    from scripts.check_skill_catalog import main
    original = Path.read_text

    def fail_reference(self, *args, **kwargs):
        if self == ref:
            raise OSError("simulated read failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_reference)
    assert main(["--root", str(root)]) == 2
    assert "cannot read reference" in capsys.readouterr().err


def test_cli_success_returns_zero_and_writes_only_valid_map(tmp_path):
    root, catalog = _tree(tmp_path)
    result = subprocess.run([sys.executable, "-m", "scripts.check_skill_catalog", "--root", str(root), "--write-map"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "MAP updated" in result.stdout


def test_malformed_unhashable_modes_report_validation_error(tmp_path):
    root, catalog = _tree(tmp_path)
    catalog["skills"][0]["modes"] = [["consult"]]
    issues = validate_catalog(root, catalog)
    assert any("invalid modes" in issue for issue in issues)
