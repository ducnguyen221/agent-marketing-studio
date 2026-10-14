# -*- coding: utf-8 -*-
"""Kiểm chứng nguồn distill: claim, hash LF và provenance theo từng file."""
import hashlib
import json
import re
import shutil
import stat
import subprocess
from pathlib import Path, PureWindowsPath

import pytest

ROOT = Path(__file__).resolve().parents[1]
SO = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
NOTICE = (ROOT / "NOTICE").read_text(encoding="utf-8")
NGUON = SO["sources"]
PUBLIC_INVENTORY = json.loads(
    (ROOT / "tests" / "fixtures" / "upstream_source_inventory.json").read_text(encoding="utf-8")
)

# Cố định cặp repo/file và hash đã có ở BASE. Không được thêm một đường dẫn mới
# vào danh sách legacy để né yêu cầu provenance per-file.
LEGACY_FILE_BASE = {
    "coreyhaines31/marketingskills": {
        ".agents/skills/hook-writer/SKILL.md": "2e94d857c2930f01d8e9ac2e6b3c4501cf1cf22b1dd8c1b2d164dadb4df7b11c",
        "knowledge/playbooks/COPY_FRAMEWORKS.md": "6272697999f9030405ccf5fd26510acf135444e2932ad4ea1a5231e9a8040b77",
        "knowledge/playbooks/SEO_PLAYBOOK.md": "06c8c9b892d89c0c5f3df5d8ba501fa779e5a1b655adce26fc576050a2519409",
        "knowledge/psychology/MARKETING_PSYCHOLOGY.md": "d9f6824a825070dca096f74c606d24e0299d60aebe1d8f8ae9e3b52fc9d3a311",
        "knowledge/toolchains/EMAIL_SEQUENCES.md": "ed1b55496909290b1ffb8b6135c65a28446e0094303ec4a5959c3173c89b0829",
    },
    "blacktwist/social-media-skills": {
        ".agents/skills/hook-writer/SKILL.md": "2e94d857c2930f01d8e9ac2e6b3c4501cf1cf22b1dd8c1b2d164dadb4df7b11c",
        ".agents/skills/thread-writer/SKILL.md": "5c2914d5e121560322cb3268b881d86af011ee3ec24bfcef15cce591feb7c52f",
    },
    "zubair-trabzada/ai-marketing-claude": {
        "knowledge/playbooks/COPY_FRAMEWORKS.md": "6272697999f9030405ccf5fd26510acf135444e2932ad4ea1a5231e9a8040b77",
    },
    "AgriciDaniel/claude-youtube": {
        "knowledge/playbooks/YOUTUBE_PLAYBOOK.md": "bfcf40613196268c20b015767a4c67ba764324b37100aa8cf050e6a3eb05b0a8",
    },
}

# Root-inventory facts independently checked in SOL-TK9-SOURCE-PREFLIGHT.md.
# The fixture must match these constants; self-declared booleans in JSON are not proof.
PINNED_SOURCE = {
    "repository": "coreyhaines31/marketingskills",
    "url": "https://github.com/coreyhaines31/marketingskills",
    "commit": "1efedbc5148b54b2f0f6c6c9fe0be62e151c7fff",
    "reviewed_at": "2026-10-10",
    "tree_sha": "b764dce2c4444ed7b4b71d6e564ec7da270c829f",
    "license": {
        "path": "LICENSE",
        "blob_sha": "7c48dd638a9ebed49a8ef0c0c4eea90105381cdf",
        "spdx": "MIT",
        "copyright": "Copyright (c) 2025 Corey Haines",
        "sha256": "b70d71e24e40fce5da8f4b6f9cd862096a048e433db7f3c8cac5e348e6d34591",
    },
    "files": {
        "skills/customer-research/SKILL.md": "905e65e67268448d88b3b96cf045c6b3615cdd87c1060e129b148a31aa627669",
        "skills/product-marketing/SKILL.md": "6dfd6bd485f62448385844cb9eceefcee0977c843d7a1c9e6077590d4e19d1ec",
        "skills/content-strategy/SKILL.md": "dce9f4027ae129691e92623541a360bee9356137a7eecf68afa95674af118e68",
        "skills/copy-editing/SKILL.md": "d23184ad62cbe29f64684b934c99d4ae8c7f03dec9c5a5d6bd492d645f5b9719",
        "skills/copywriting/SKILL.md": "78c0a09b78a41995ba055d6549bbd7db3fe958673d039b9121e7a2e32bb4bb06",
        "skills/offers/SKILL.md": "f27239be82e5d4ad42daa944fad7d0a640b80ca82697ba7399843437a001e5aa",
        "skills/lead-magnets/SKILL.md": "190a64c72a9a36fdde3a6b0888798e1bb9dd4e7406b00a6bbf90dba5e64c047b",
        "skills/emails/SKILL.md": "0d27de40c2eb32eb2425a48805dc1bf0210d64d0ce384cd48860697020f5a573",
        "skills/cro/SKILL.md": "6e172cc38178c800ff41ceb097f36c6a1db8035fb88a1fee53043f8ec38a6f35",
        "skills/analytics/SKILL.md": "73405dd294aaedbcd2b3fe00ef44691963fa8d1c6c280a3d46179a33f067f984",
        "skills/ab-testing/SKILL.md": "bde64a0c54013a9003b9967f5be61758a3302cbcde2145c6a13a6d8a49d9f342",
        "skills/attribution/SKILL.md": "b0493b97f7a22d6daf7fe47a67e8dc050e5cca98fe952df7dea2bf296853c978",
    },
}

_ALLOWLIST = (".agents/skills", "knowledge", "templates", "output_styles")
_SKIP_PARTS = {".tmp", ".cache", "cache", "vendor", "vendors", "node_modules", "__pycache__", ".pytest_cache"}
_CLAIM_LINE = re.compile(r"^\s*>?\s*(?:chưng cất từ|distilled from|adapted from)\b[^\n]*", re.I)
_REPO = re.compile(r"(?:từ:?|from|\+|·|của)\s+`([\w.-]+/[\w.-]+)`", re.I)
_CODE_SPAN = re.compile(r"`([^`]+)`")


def _lf_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _safe_repo_path(root: Path, relative: object) -> Path | None:
    """Resolve a repository-relative file while refusing traversal and reparse points."""
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or PureWindowsPath(relative).drive or ".." in candidate.parts:
        return None
    try:
        resolved_root = root.resolve(strict=True)
        current = resolved_root
        for part in candidate.parts:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            attributes = getattr(info, "st_file_attributes", 0)
            if stat.S_ISLNK(info.st_mode) or attributes & 0x400:
                return None
        resolved = current.resolve(strict=False)
        if not resolved.is_relative_to(resolved_root):
            return None
        return resolved
    except (OSError, RuntimeError):
        return None


def _working_tree_inventory(root: Path) -> list[str]:
    """Tracked và untracked không ignored, giới hạn trong bốn vùng được giao."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *_ALLOWLIST],
        cwd=root,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        pytest.fail(
            f"git ls-files thất bại (exit {result.returncode}): {str(stderr).strip() or '(stderr trống)'}"
        )
    paths = []
    for rel in result.stdout.decode("utf-8").split("\0"):
        if not rel:
            continue
        path = Path(rel)
        if any(part.lower() in _SKIP_PARTS for part in path.parts):
            continue
        safe_path = _safe_repo_path(root, rel)
        if safe_path is None:
            pytest.fail(f"unsafe repository path in Git inventory: {rel}")
        if safe_path.is_file():
            paths.append(path.as_posix())
    return sorted(set(paths))


def _source_claims(root: Path) -> dict[str, dict[str, set[str]]]:
    """Đọc claim và đường dẫn upstream ở thân Markdown, không đọc metadata làm claim."""
    claims: dict[str, dict[str, set[str]]] = {}
    for rel in _working_tree_inventory(root):
        if Path(rel).suffix.lower() != ".md":
            continue
        safe_path = _safe_repo_path(root, rel)
        if safe_path is None:
            pytest.fail(f"unsafe repository path before claim read: {rel}")
        try:
            body = safe_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            pytest.fail(f"{rel} không phải UTF-8, không thể kiểm claim nguồn: {exc}")
        for line in body.splitlines():
            if not _CLAIM_LINE.match(line):
                continue
            repositories = _REPO.findall(line)
            spans = set(_CODE_SPAN.findall(line))
            upstream_paths = {span for span in spans - set(repositories) if "/" in span}
            for repo in repositories:
                claims.setdefault(rel, {}).setdefault(repo, set()).update(upstream_paths)
    return claims


def _provenance_errors(root: Path, inventory: dict) -> list[str]:
    """Đối chiếu claim ↔ hash ledger ↔ provenance và inventory nguồn đã ghim."""
    root = root.resolve(strict=True)
    ledger_path = _safe_repo_path(root, "upstream.json")
    if ledger_path is None or not ledger_path.is_file():
        return ["unsafe repository path or missing upstream.json"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    sources = ledger.get("sources", {})
    claims = _source_claims(root)
    errors: list[str] = []
    all_pairs = set()
    for repo, reposrc in sources.items():
        files = reposrc.get("files", {})
        if not isinstance(files, dict):
            errors.append(f"{repo}: files ledger must be a mapping")
            continue
        for rel in files:
            if _safe_repo_path(root, rel) is None:
                errors.append(f"{repo}: unsafe repository path in upstream ledger: {rel}")
                continue
            all_pairs.add((repo, rel))
    claim_pairs = {(repo, rel) for rel, repos in claims.items() for repo in repos}

    for repo, rel in sorted(claim_pairs - all_pairs):
        errors.append(f"{rel} khai nguồn {repo} nhưng upstream.json thiếu hash ledger")
    for repo, rel in sorted(all_pairs - claim_pairs):
        errors.append(f"{repo}: upstream.json ghi {rel} nhưng file không khai nguồn đó")

    for repo, files in LEGACY_FILE_BASE.items():
        source = sources.get(repo, {})
        for rel, frozen_hash in files.items():
            recorded_hash = source.get("files", {}).get(rel)
            path = _safe_repo_path(root, rel)
            provenance = source.get("file_provenance", {}).get(rel)
            if provenance is None and (recorded_hash != frozen_hash or path is None or not path.is_file() or _lf_hash(path) != frozen_hash):
                errors.append(f"{repo}: legacy chưa rà lại {rel} phải giữ hash LF của BASE")

    public_source = inventory.get("source", {})
    inventory_is_pinned = inventory.get("schema_version") == 1 and all(
        public_source.get(key) == value
        for key, value in PINNED_SOURCE.items()
    )

    for repo, rel in sorted(claim_pairs & all_pairs):
        source = sources[repo]
        path = _safe_repo_path(root, rel)
        if path is None or not path.is_file():
            errors.append(f"{repo}: file trong ledger không tồn tại: {rel}")
            continue
        expected_hash = source["files"][rel]
        actual_hash = _lf_hash(path)
        if actual_hash != expected_hash:
            errors.append(f"{rel} đã đổi so với hash LF trong upstream.json ({repo})")

        provenance = source.get("file_provenance", {}).get(rel)
        is_legacy = rel in LEGACY_FILE_BASE.get(repo, {})
        if is_legacy and provenance is None:
            # Legacy unknown hợp lệ khi hash ledger và nội dung vẫn bằng BASE.
            if expected_hash != LEGACY_FILE_BASE[repo][rel] or actual_hash != LEGACY_FILE_BASE[repo][rel]:
                errors.append(f"{repo}: legacy {rel} đổi khỏi BASE nên cần file_provenance đã rà")
            continue
        if provenance is None:
            errors.append(f"{repo}: {rel} thiếu file_provenance")
            continue
        if not inventory_is_pinned or repo != public_source.get("repository"):
            errors.append(f"{repo}: {rel} dùng nguồn chưa có inventory công khai đã ghim")
            continue
        if provenance.get("upstream_ref") != public_source.get("commit"):
            errors.append(f"{rel}: upstream_ref không khớp inventory đã ghim")
        if provenance.get("reviewed_at") != public_source.get("reviewed_at"):
            errors.append(f"{rel}: reviewed_at không khớp inventory đã ghim")
        upstream_paths = provenance.get("upstream_paths")
        if (
            not isinstance(upstream_paths, list)
            or not upstream_paths
            or not all(isinstance(upstream_path, str) for upstream_path in upstream_paths)
            or len(upstream_paths) != len(set(upstream_paths))
        ):
            errors.append(f"{rel}: upstream_paths phải là danh sách đường dẫn duy nhất")
        elif any(upstream_path not in public_source["files"] for upstream_path in upstream_paths):
            errors.append(f"{rel}: upstream_paths có đường dẫn không tồn tại tại commit đã ghim")
        elif set(upstream_paths) != claims.get(rel, {}).get(repo, set()):
            errors.append(f"{rel}: upstream_paths không khớp claim trong thân file")

    # Không cho metadata trôi riêng khỏi claim/hash ledger.
    for repo, source in sources.items():
        for rel in source.get("file_provenance", {}):
            if (repo, rel) not in claim_pairs or (repo, rel) not in all_pairs:
                errors.append(f"{repo}: file_provenance thừa cho {rel}")
    return errors


def _assert_no_provenance_errors(root: Path, inventory: dict = PUBLIC_INVENTORY) -> None:
    errors = _provenance_errors(root, inventory)
    assert not errors, "\n".join(errors)


def test_moi_file_khai_chung_cat_DEU_co_hash_va_provenance_phu_hop():
    claims = _source_claims(ROOT)
    assert claims, "không thấy dòng 'Chưng cất từ' nào — cổng đang quét hụt"
    _assert_no_provenance_errors(ROOT)


def test_hash_ban_chung_cat_khop_so_nguon():
    for repo, source in NGUON.items():
        for rel, expected in source["files"].items():
            path = _safe_repo_path(ROOT, rel)
            assert path is not None and path.is_file(), rel
            assert _lf_hash(path) == expected, f"{rel} đã đổi so với hash LF ({repo})"


@pytest.mark.parametrize("repo", sorted(NGUON))
def test_NOTICE_ghi_cong_du_theo_MIT(repo):
    source = NGUON[repo]
    assert source["license"] == "MIT"
    assert source["url"] == f"https://github.com/{repo}"
    assert repo in NOTICE and source["copyright"] in NOTICE, f"NOTICE thiếu ghi công {repo}"
    for rel in source["files"]:
        assert rel in NOTICE, f"NOTICE không liệt kê {rel} dưới nguồn nào"


def test_NOTICE_mang_van_ban_giay_phep_MIT():
    for phrase in (
        "Permission is hereby granted, free of charge",
        "The above copyright notice and this permission notice shall be included",
        'THE SOFTWARE IS PROVIDED "AS IS"',
    ):
        assert phrase in NOTICE, phrase


def test_tham_khao_thiet_ke_noi_ro_khong_chep_van_ban():
    for repo, reference in SO.get("design_references", {}).items():
        assert reference["copied_text"] is False
        assert repo in NOTICE
        for rel in reference["used_in"]:
            assert (ROOT / rel).is_file(), rel


def _fixture_repo(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "fixture-repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    for directory in _ALLOWLIST:
        (root / directory).mkdir(parents=True, exist_ok=True)
    sources = {}
    for repo, files in LEGACY_FILE_BASE.items():
        template = NGUON[repo]
        sources[repo] = {
            "url": template["url"],
            "license": template["license"],
            "copyright": template["copyright"],
            "license_checked": template["license_checked"],
            "upstream_ref": None,
            "upstream_ref_note": "legacy snapshot unknown",
            "files": dict(files),
        }
        for rel in files:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
    (root / "upstream.json").write_text(json.dumps({"sources": sources}, indent=2), encoding="utf-8")
    subprocess.run(["git", "add", *_ALLOWLIST], cwd=root, check=True, capture_output=True)
    return root, sources


def _minimal_synthetic_repo(root: Path) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".agents" / "skills").mkdir(parents=True)
    return root


@pytest.mark.parametrize("relative", ["../outside.md", "C:/outside.md", "D:relative.md"])
def test_safe_path_rejects_traversal_and_drive_paths(tmp_path, relative):
    root = _minimal_synthetic_repo(tmp_path / "repo")

    assert _safe_repo_path(root, relative) is None


def test_inventory_refuses_symlink_before_reading_outside_synthetic_repo(tmp_path, monkeypatch):
    root = _minimal_synthetic_repo(tmp_path / "repo")
    outside = tmp_path / "outside.md"
    outside.write_text("> Distilled from `example/source`.\n", encoding="utf-8")
    link = root / ".agents" / "skills" / "escape.md"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this host")
    subprocess.run(["git", "add", ".agents/skills/escape.md"], cwd=root, check=True)

    original = Path.read_text

    def refuse_outside(self, *args, **kwargs):
        if self.resolve() == outside.resolve():
            raise AssertionError("attempted read outside configured synthetic repository")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", refuse_outside)
    with pytest.raises(pytest.fail.Exception, match="unsafe|symlink|reparse"):
        _source_claims(root)


def test_ledger_traversal_is_reported_without_reading_outside_synthetic_repo(tmp_path, monkeypatch):
    root = _minimal_synthetic_repo(tmp_path / "repo")
    outside = tmp_path / "outside.md"
    outside.write_text("synthetic sentinel\n", encoding="utf-8")
    (root / "upstream.json").write_text(json.dumps({"sources": {
        "example/source": {"files": {"../outside.md": "0" * 64},
                            "file_provenance": {}}
    }}), encoding="utf-8")

    original = Path.read_bytes

    def refuse_outside(self, *args, **kwargs):
        if self.resolve() == outside.resolve():
            raise AssertionError("attempted read outside configured synthetic repository")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", refuse_outside)
    errors = _provenance_errors(root, {"schema_version": 1, "source": {}})

    assert any("unsafe repository path" in error for error in errors)


def _add_new_distill(root: Path, sources: dict, rel: str = ".agents/skills/new-research/SKILL.md") -> None:
    repo = "coreyhaines31/marketingskills"
    upstream_path = "skills/customer-research/SKILL.md"
    body = (
        "> Chưng cất từ `coreyhaines31/marketingskills` · "
        "`skills/customer-research/SKILL.md` (ref đã ghim).\n\nNội dung đã diễn giải.\n"
    )
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    source = sources[repo]
    source.setdefault("files", {})[rel] = _lf_hash(target)
    source.setdefault("file_provenance", {})[rel] = {
        "upstream_ref": PUBLIC_INVENTORY["source"]["commit"],
        "upstream_paths": [upstream_path],
        "reviewed_at": PUBLIC_INVENTORY["source"]["reviewed_at"],
    }
    (root / "upstream.json").write_text(json.dumps({"sources": sources}, indent=2), encoding="utf-8")


def test_legacy_null_va_untracked_distill_co_metadata_pinned_hop_le(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    assert ".agents/skills/new-research/SKILL.md" in _working_tree_inventory(root)
    _assert_no_provenance_errors(root)


def test_claim_khong_bi_bo_khi_repo_name_trung_local_path(tmp_path: Path):
    root, _ = _fixture_repo(tmp_path)
    claim = root / ".agents/skills/unlisted/SKILL.md"
    claim.parent.mkdir(parents=True, exist_ok=True)
    claim.write_text("> Chưng cất từ: `unlisted/repo`.\n", encoding="utf-8")
    (root / "unlisted/repo").mkdir(parents=True)
    assert "unlisted/repo" in _source_claims(root)[".agents/skills/unlisted/SKILL.md"]
    assert any("thiếu hash ledger" in error for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_untracked_distill_thieu_hash_ledger_bi_loi(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    del sources["coreyhaines31/marketingskills"]["files"][".agents/skills/new-research/SKILL.md"]
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any("thiếu hash ledger" in error for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_untracked_distill_thieu_metadata_bi_loi(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    del sources["coreyhaines31/marketingskills"]["file_provenance"][".agents/skills/new-research/SKILL.md"]
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any("thiếu file_provenance" in error for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_ignored_temp_khong_vao_inventory(tmp_path: Path):
    root, _ = _fixture_repo(tmp_path)
    ignored = root / ".agents/skills/cache/ignored.md"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("> Chưng cất từ `unknown/private-source`.\n", encoding="utf-8")
    (root / ".gitignore").write_text(".agents/skills/cache/\n", encoding="utf-8")
    assert ".agents/skills/cache/ignored.md" not in _working_tree_inventory(root)
    _assert_no_provenance_errors(root)


def test_ledger_thua_bi_loi(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    sources["coreyhaines31/marketingskills"]["files"]["knowledge/missing.md"] = "0" * 64
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any("ghi knowledge/missing.md nhưng file không khai nguồn" in error
               for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_hash_LF_drifts_bi_loi(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    target = root / ".agents/skills/new-research/SKILL.md"
    target.write_text(target.read_text(encoding="utf-8") + "Thêm một dòng.\n", encoding="utf-8")
    assert any("đã đổi so với hash LF" in error for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_khong_the_gan_file_moi_thanh_legacy_de_ne_provenance(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    del sources["coreyhaines31/marketingskills"]["file_provenance"][".agents/skills/new-research/SKILL.md"]
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    errors = _provenance_errors(root, PUBLIC_INVENTORY)
    assert any("thiếu file_provenance" in error for error in errors)


def test_legacy_da_ra_co_the_cap_nhat_hash_voi_metadata_pinned(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    repo = "coreyhaines31/marketingskills"
    rel = "knowledge/toolchains/EMAIL_SEQUENCES.md"
    target = root / rel
    target.write_text(
        "> Chưng cất từ: `coreyhaines31/marketingskills` · `skills/emails/SKILL.md`.\n"
        + target.read_text(encoding="utf-8")
        + "\n<!-- reviewed snapshot -->\n",
        encoding="utf-8",
    )
    sources[repo]["files"][rel] = _lf_hash(target)
    sources[repo].setdefault("file_provenance", {})[rel] = {
        "upstream_ref": PUBLIC_INVENTORY["source"]["commit"],
        "upstream_paths": ["skills/emails/SKILL.md"],
        "reviewed_at": PUBLIC_INVENTORY["source"]["reviewed_at"],
    }
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    _assert_no_provenance_errors(root)


def test_legacy_reviewed_metadata_must_match_body_source_path(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    repo = "coreyhaines31/marketingskills"
    rel = "knowledge/toolchains/EMAIL_SEQUENCES.md"
    target = root / rel
    target.write_text(
        "> Chưng cất từ: `coreyhaines31/marketingskills` · `skills/emails/SKILL.md`.\n"
        + target.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sources[repo]["files"][rel] = _lf_hash(target)
    sources[repo].setdefault("file_provenance", {})[rel] = {
        "upstream_ref": PUBLIC_INVENTORY["source"]["commit"],
        "upstream_paths": ["skills/customer-research/SKILL.md"],
        "reviewed_at": PUBLIC_INVENTORY["source"]["reviewed_at"],
    }
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any(
        "upstream_paths không khớp claim trong thân file" in error
        for error in _provenance_errors(root, PUBLIC_INVENTORY)
    )


def test_legacy_hash_update_without_pinned_metadata_fails(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    repo = "coreyhaines31/marketingskills"
    rel = "knowledge/toolchains/EMAIL_SEQUENCES.md"
    target = root / rel
    target.write_text(target.read_text(encoding="utf-8") + "\n<!-- changed -->\n", encoding="utf-8")
    sources[repo]["files"][rel] = _lf_hash(target)
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any("cần file_provenance" in error for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_hash_legacy_frozen_tu_BASE_khong_duoc_them_gia(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    sources["coreyhaines31/marketingskills"]["files"][".agents/skills/hook-writer/SKILL.md"] = "0" * 64
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any("legacy chưa rà lại" in error and "hash LF của BASE" in error
               for error in _provenance_errors(root, PUBLIC_INVENTORY))


def test_inventory_khong_xac_thuc_tree_va_hash_thi_khong_duoc_dung(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    unverified = json.loads(json.dumps(PUBLIC_INVENTORY))
    unverified["source"]["tree_sha"] = "0" * 40
    errors = _provenance_errors(root, unverified)
    assert any("nguồn chưa có inventory công khai đã ghim" in error for error in errors)


def test_doi_dong_thoi_source_inventory_va_file_ref_van_truot(tmp_path: Path):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    changed_fixture = json.loads(json.dumps(PUBLIC_INVENTORY))
    forged_commit = "f" * 40
    changed_fixture["source"]["commit"] = forged_commit
    changed_fixture["source"]["commit_verified"] = True
    changed_fixture["source"]["file_hashes_verified"] = True
    sources["coreyhaines31/marketingskills"]["file_provenance"][
        ".agents/skills/new-research/SKILL.md"
    ]["upstream_ref"] = forged_commit
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any(
        "inventory công khai đã ghim" in error
        for error in _provenance_errors(root, changed_fixture)
    )


def test_git_inventory_error_fails_with_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def git_error(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0], 128, stdout=b"", stderr=b"fatal: not a git repository (or any parent directory)"
        )

    monkeypatch.setattr(subprocess, "run", git_error)
    with pytest.raises(pytest.fail.Exception, match="git ls-files thất bại.*fatal: not a git repository"):
        _working_tree_inventory(tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("upstream_ref", "f" * 40, "upstream_ref không khớp"),
        ("upstream_paths", ["skills/not-pinned/SKILL.md"], "đường dẫn không tồn tại"),
        ("reviewed_at", "2026-10-11", "reviewed_at không khớp"),
    ],
)
def test_metadata_phai_khop_source_inventory_pinned(tmp_path: Path, field: str, value: object, message: str):
    root, sources = _fixture_repo(tmp_path)
    _add_new_distill(root, sources)
    provenance = sources["coreyhaines31/marketingskills"]["file_provenance"][
        ".agents/skills/new-research/SKILL.md"
    ]
    provenance[field] = value
    (root / "upstream.json").write_text(json.dumps({"sources": sources}), encoding="utf-8")
    assert any(message in error for error in _provenance_errors(root, PUBLIC_INVENTORY))
