# -*- coding: utf-8 -*-
"""Validate the skill catalog and optionally render its marked MAP table."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

START = "<!-- SKILL_ROUTING:START -->"
END = "<!-- SKILL_ROUTING:END -->"
SKILL_FIELDS = {
    "id", "path", "summary", "use_when", "do_not_use_when", "stages", "modes",
    "requires", "outputs", "supports", "references", "maturity", "evidence",
}
PILOT_FIELDS = {"id", "handler", "playbook", "modes", "use_when", "outputs", "limits"}
STAGES = {"new", "plan", "produce", "selfqa", "render", "publish", "measure", "cross-cutting", "standalone"}
MODES = {"consult", "prepare", "execute", "standalone-edit"}
MATURITIES = {"candidate", "pilot", "verified"}
REFERENCE_MAX_LINES = 250
REFERENCE_MAX_BYTES = 20480
CONSULT_WRITES = {"chat_response", "assigned_file"}
REFERENCE_BASE_COMMIT = "4e62cfc0f9baff0a5b3f5f924f0f2f4b918c8b27"
REFERENCE_MANIFEST_SHA256 = "c8ab1d37332de240c98f5eaaa87b70a21a88f5775d438413942a4ae228d63347"


class CatalogError(Exception):
    """A catalog could not be read safely."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            if key in result:
                raise CatalogError(f"duplicate YAML key: {key}")
        except TypeError as exc:
            raise CatalogError("YAML mapping keys must be scalar and hashable") from exc
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _inside(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    try:
        resolved = (root / candidate).resolve(strict=True)
        if not resolved.is_relative_to(root):
            return None
        return resolved
    except (OSError, RuntimeError):
        return None


def load_catalog(root: Path) -> dict:
    """Load YAML without duplicate-key ambiguity; read errors are fatal."""
    root = root.resolve(strict=True)
    path = _inside(root, ".agents/skill-catalog.yaml")
    if path is None or not path.is_file():
        raise CatalogError("catalog missing or resolves outside repository")
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CatalogError(f"cannot read catalog: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogError("catalog root must be a mapping")
    return data


def _list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _skill_frontmatter(path: Path) -> tuple[str | None, str | None]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, None
    try:
        metadata = yaml.load(text[4:end], Loader=_UniqueKeyLoader)
    except yaml.YAMLError:
        return None, None
    if not isinstance(metadata, dict):
        return None, None
    name, description = metadata.get("name"), metadata.get("description")
    return (name if isinstance(name, str) else None,
            description if isinstance(description, str) else None)


def _baseline_hashes(root: Path) -> tuple[dict[str, str], str | None]:
    """Hashes for untouched tracked references at the implementation base."""
    manifest = root / ".agents" / "skill-reference-baseline.json"
    if not manifest.is_file():
        return {}, None
    try:
        raw_manifest = manifest.read_bytes()
        canonical_manifest = raw_manifest.replace(b"\r\n", b"\n")
        if hashlib.sha256(canonical_manifest).hexdigest() != REFERENCE_MANIFEST_SHA256:
            return {}, "reference baseline manifest bytes differ from the reviewed snapshot"
        data = yaml.load(canonical_manifest.decode("utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}, "reference baseline manifest cannot be read safely"
    if not isinstance(data, dict) or data.get("source_commit") != REFERENCE_BASE_COMMIT:
        return {}, "reference baseline manifest has an unexpected source commit"
    files = data.get("files")
    if not isinstance(files, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in files.items()
    ):
        return {}, "reference baseline manifest has invalid file hashes"
    return files, None


def validate_catalog(root: Path, catalog: dict) -> list[str]:
    """Return deterministic structural issues; never perform network or runtime routing."""
    root = root.resolve(strict=True)
    errors: list[str] = []
    if set(catalog) != {"schema", "skills", "pilot_routes"}:
        errors.append("catalog root fields must be schema, skills, pilot_routes")
    if catalog.get("schema") != 1:
        errors.append("schema must equal 1")
    skills, pilots = catalog.get("skills"), catalog.get("pilot_routes")
    if not isinstance(skills, list) or not isinstance(pilots, list):
        return errors + ["skills and pilot_routes must be lists"]

    ids: dict[str, str] = {}
    skill_ids: set[str] = set()
    graph: dict[str, list[str]] = {}
    baseline_hashes, baseline_error = _baseline_hashes(root)
    if baseline_error:
        errors.append(baseline_error)
    for kind, entries, expected_fields in (("skill", skills, SKILL_FIELDS), ("pilot", pilots, PILOT_FIELDS)):
        for index, entry in enumerate(entries):
            label = f"{kind}[{index}]"
            if not isinstance(entry, dict) or set(entry) != expected_fields:
                errors.append(f"{label}: fields must be {sorted(expected_fields)}")
                continue
            item_id = entry.get("id")
            if not isinstance(item_id, str) or not item_id.strip():
                errors.append(f"{label}: id must be a non-empty string")
                continue
            if item_id in ids:
                errors.append(f"duplicate id across {ids[item_id]} and {label}: {item_id}")
            ids[item_id] = label
            if kind == "skill":
                skill_ids.add(item_id)
                graph[item_id] = entry.get("supports", []) if isinstance(entry.get("supports"), list) else []
                path = _inside(root, entry.get("path"))
                if path is None or not path.is_file():
                    errors.append(f"{item_id}: path missing or escapes repository")
                else:
                    try:
                        name, description = _skill_frontmatter(path)
                        raw = path.read_bytes()
                    except (OSError, UnicodeError) as exc:
                        raise CatalogError(f"{item_id}: cannot read skill: {exc}") from exc
                    else:
                        if name != item_id:
                            errors.append(f"{item_id}: frontmatter name mismatch")
                        expected = (root / ".agents" / "skills" / item_id / "SKILL.md").resolve()
                        if path != expected:
                            errors.append(f"{item_id}: path must be .agents/skills/<id>/SKILL.md")
                        if description is None or len(description) > 600:
                            errors.append(f"{item_id}: description missing or over 600 characters")
                        max_lines, max_bytes = (160, 10240) if item_id == "marketing-routing" else (120, 8192)
                        if len(raw.splitlines()) > max_lines or len(raw) > max_bytes:
                            errors.append(f"{item_id}: skill exceeds {max_lines} lines or {max_bytes} bytes")
                if not isinstance(entry.get("summary"), str) or not entry["summary"].strip():
                    errors.append(f"{item_id}: summary must be a non-empty string")
                for field in ("use_when", "do_not_use_when", "outputs", "supports", "references", "evidence"):
                    if not _list_of_strings(entry.get(field)):
                        errors.append(f"{item_id}: {field} must be a list of non-empty strings")
                stages = entry.get("stages")
                if (not isinstance(stages, list) or not stages or not all(isinstance(value, str) for value in stages)
                        or len(stages) != len(set(stages)) or not set(stages) <= STAGES):
                    errors.append(f"{item_id}: invalid stage")
                modes = entry.get("modes", [])
                if (not isinstance(modes, list) or not modes or not all(isinstance(value, str) for value in modes)
                        or len(modes) != len(set(modes)) or not set(modes) <= MODES):
                    errors.append(f"{item_id}: invalid modes")
                requires = entry.get("requires")
                if (not isinstance(requires, dict) or not isinstance(modes, list)
                        or not all(isinstance(value, str) for value in modes)
                        or set(requires) != set(modes)):
                    errors.append(f"{item_id}: requires must define exactly the declared modes")
                else:
                    for mode, requirements in requires.items():
                        if (not isinstance(requirements, dict)
                                or set(requirements) != {"read", "write"}
                                or not _list_of_strings(requirements["read"])
                                or not _list_of_strings(requirements["write"])):
                            errors.append(f"{item_id}: requires.{mode} must contain read/write lists")
                        elif mode == "consult" and not set(requirements["write"]) <= CONSULT_WRITES:
                            errors.append(f"{item_id}: consult writes may only name chat_response or assigned_file")
                for relative in entry.get("references", []) if isinstance(entry.get("references"), list) else []:
                    reference = _inside(root, relative)
                    if reference is None:
                        errors.append(f"{item_id}: reference missing or escapes repository: {relative}")
                    elif not reference.is_file():
                        errors.append(f"{item_id}: reference must be a file: {relative}")
                    else:
                        try:
                            reference.read_text(encoding="utf-8")
                            raw = reference.read_bytes()
                        except (OSError, UnicodeError) as exc:
                            raise CatalogError(f"cannot read reference: {relative}: {exc}") from exc
                        unchanged_baseline = baseline_hashes.get(relative) == hashlib.sha256(raw).hexdigest()
                        if (not unchanged_baseline and (len(raw.splitlines()) > REFERENCE_MAX_LINES
                                or len(raw) > REFERENCE_MAX_BYTES)):
                            errors.append(f"{item_id}: reference exceeds {REFERENCE_MAX_LINES} lines or {REFERENCE_MAX_BYTES} bytes: {relative}")
                for relative in entry.get("evidence", []) if isinstance(entry.get("evidence"), list) else []:
                    evidence_path = _inside(root, relative)
                    if evidence_path is None or not evidence_path.is_file():
                        errors.append(f"{item_id}: evidence missing or escapes repository: {relative}")
                    elif entry.get("maturity") == "verified" and (
                            not relative.startswith("docs/evidence/skill-routing/")
                            or relative.endswith((".yaml", ".yml"))
                            or "fixture" in relative.casefold()
                            or "guide" in Path(relative).name.casefold()):
                        errors.append(f"{item_id}: verified evidence must be reviewed output under docs/evidence/skill-routing/: {relative}")
                if not isinstance(entry.get("maturity"), str) or entry.get("maturity") not in MATURITIES:
                    errors.append(f"{item_id}: invalid maturity")
                if entry.get("maturity") == "verified" and not entry.get("evidence"):
                    errors.append(f"{item_id}: verified maturity requires evidence")
            else:
                path = _inside(root, entry.get("playbook"))
                if path is None or not path.is_file():
                    errors.append(f"{item_id}: playbook missing or escapes repository")
                if entry.get("handler") != "direct-consultation" or entry.get("modes") != ["consult"]:
                    errors.append(f"{item_id}: pilot route must be consult-only direct-consultation")
                for field in ("use_when", "outputs", "limits"):
                    if not _list_of_strings(entry.get(field)):
                        errors.append(f"{item_id}: {field} must be a list of non-empty strings")

    skills_root = _inside(root, ".agents/skills")
    if skills_root is None or not skills_root.is_dir():
        errors.append("skill inventory directory missing or escapes repository")
    else:
        catalog_skill_ids = {
            entry.get("id") for entry in skills
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        for folder in skills_root.iterdir():
            try:
                folder_info = folder.lstat()
            except OSError as exc:
                raise CatalogError(f"cannot inspect skill inventory: {exc}") from exc
            folder_attributes = getattr(folder_info, "st_file_attributes", 0)
            is_redirect = folder.is_symlink() or bool(folder_attributes & 0x400)
            if is_redirect:
                errors.append(f"skill inventory entry redirects outside ordinary directory: {folder.name}")
                continue
            if not folder.is_dir():
                continue
            skill_file = folder / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                skill_info = skill_file.lstat()
            except OSError as exc:
                raise CatalogError(f"cannot inspect skill inventory file: {exc}") from exc
            skill_attributes = getattr(skill_info, "st_file_attributes", 0)
            if skill_file.is_symlink() or skill_attributes & 0x400:
                errors.append(f"skill inventory file redirects: .agents/skills/{folder.name}/SKILL.md")
                continue
            if not skill_file.is_file():
                continue
            if folder.name not in catalog_skill_ids:
                errors.append(f".agents/skills/{folder.name}/SKILL.md is missing from catalog")

    for item_id, supports in graph.items():
        for supported in supports:
            if not isinstance(supported, str) or supported not in skill_ids:
                errors.append(f"{item_id}: unsupported skill id {supported}")
            if supported == "marketing-routing":
                errors.append(f"{item_id}: router cannot appear in supports")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            errors.append(f"supports cycle includes {item_id}")
            return
        if item_id in visited:
            return
        visiting.add(item_id)
        for child in graph.get(item_id, []):
            if isinstance(child, str) and child in graph:
                visit(child)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in graph:
        visit(item_id)
    return sorted(set(errors))


def render_skill_table(catalog: dict) -> str:
    def cell(value: str) -> str:
        return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("|", "\\|").replace("\r", " ").replace("\n", " "))

    rows = ["| Skill | Tình huống | Đầu ra | Ranh giới |", "|---|---|---|---|"]
    for item in catalog["skills"]:
        rows.append("| {id} | {use} | {outputs} | {limits} |".format(
            id=cell(item["id"]), use=cell("; ".join(item["use_when"])),
            outputs=cell("; ".join(item["outputs"])), limits=cell("; ".join(item["do_not_use_when"]))))
    for item in catalog["pilot_routes"]:
        rows.append("| {id} (pilot) | {use} | {outputs} | {limits} |".format(
            id=cell(item["id"]), use=cell("; ".join(item["use_when"])),
            outputs=cell("; ".join(item["outputs"])), limits=cell("; ".join(item["limits"]))))
    return "\n".join(rows)


def check_map(map_text: str, table: str) -> list[str]:
    if map_text.count(START) != 1 or map_text.count(END) != 1:
        return ["MAP must contain exactly one start and end marker"]
    start, end = map_text.index(START), map_text.index(END)
    if start >= end:
        return ["MAP markers are reversed"]
    generated = map_text[start + len(START):end].strip("\r\n")
    return [] if generated == table else ["generated skill table differs from catalog"]


def _write_map(path: Path, text: str) -> None:
    if path.is_symlink():
        raise CatalogError("refusing to replace a symlink MAP.md")
    original = path.read_bytes()
    content = original.decode("utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise CatalogError("MAP markers must occur exactly once")
    start, end = content.index(START), content.index(END)
    if start >= end:
        raise CatalogError("MAP markers are reversed")
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    start_b, end_b = START.encode(), END.encode()
    start_pos, end_pos = original.index(start_b), original.index(end_b)
    updated = original[:start_pos + len(start_b)] + newline + text.replace("\n", newline.decode()).encode("utf-8") + newline + original[end_pos:]
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(updated)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write-map", action="store_true", help="write the generated MAP block after validation")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        catalog = load_catalog(root)
        errors = validate_catalog(root, catalog)
        if errors:
            for error in sorted(set(errors)):
                print(error, file=sys.stderr)
            return 1
        map_path = _inside(root, "MAP.md")
        if map_path is None or not map_path.is_file() or (root / "MAP.md").is_symlink():
            raise CatalogError("MAP.md missing or resolves outside repository")
        table = render_skill_table(catalog)
        map_text = map_path.read_text(encoding="utf-8")
        if not args.write_map:
            errors.extend(check_map(map_text, table))
        elif check_map(map_text, table) and (map_text.count(START) != 1 or map_text.count(END) != 1 or map_text.index(START) >= map_text.index(END)):
            errors.extend(check_map(map_text, table))
        if errors:
            for error in sorted(set(errors)):
                print(error, file=sys.stderr)
            return 1
        if args.write_map:
            _write_map(map_path, table)
        print("skill catalog valid" + ("; MAP updated" if args.write_map else "; MAP matches"))
        return 0
    except (CatalogError, OSError, UnicodeError, ValueError) as exc:
        print(f"catalog check error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
