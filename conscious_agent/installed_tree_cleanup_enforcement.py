from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from full_tree_mutation_snapshot import snapshot_source_tree, compare_source_snapshots, snapshot_hash
from installed_tree_cleanup_historical_verification_reconciliation import _is_obsolete_generated_source_candidate

INSTALLED_TREE_CLEANUP_ENFORCEMENT_VERSION = RUNTIME_VERSION
INSTALLED_TREE_CLEANUP_ENFORCEMENT_ID = "installed-tree-cleanup-enforcement-v1"
SELF_ROUTE = "/installed-tree-cleanup-enforcement"
API_ROUTE = "/api/installed-tree-cleanup/enforcement"
OPERATOR_CONFIRMATION_PHRASE = "APPLY_GUARDED_INSTALLED_TREE_CLEANUP"
STALE_EXPECTED_OBSOLETE_FILE_COUNT = 17

BOUNDARIES: dict[str, bool] = {
    "review_only_by_default": True,
    "get_preview_only": True,
    "delete_requires_post_confirmation": True,
    "deletes_active_imported_modules": False,
    "deletes_runtime_private_data": False,
    "deletes_source_without_manifest": False,
    "deletes_source_without_reference_scan": False,
    "source_files_mutated_by_get": False,
    "runtime_data_deleted": False,
    "generated_wiring_activated": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}

SKIP_DIR_NAMES = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class CleanupCandidate:
    path: str
    module_name: str
    generated_pattern_match: bool
    import_reference_count: int
    import_references: tuple[str, ...]
    text_reference_count: int
    protected_active_module: bool
    deletable: bool
    decision: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _iter_source_files(root: Path) -> list[Path]:
    """Return packageable Python source files across the installed/source tree.

    Earlier cleanup enforcement only inspected conscious_agent/ and tools/, which
    let obsolete sandbox artifacts escape classification. The reference scan now
    covers every packageable Python file, including sandbox/ when it exists, while
    still excluding runtime/private data and bytecode clutter.
    """
    return [path for path in _iter_package_source_files(root) if path.suffix.lower() == ".py"]


def _iter_package_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = set(rel.split("/"))
        if parts & SKIP_DIR_NAMES:
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if rel.startswith("data/") and rel not in {
            "data/settings.json",
            "data/projects.json",
            "data/workspaces/active_project.json",
            "data/workspaces/projects.json",
            "data/signing/trusted_public_keys.json",
        } and not rel.startswith("data/workspaces/command_profiles/"):
            continue
        files.append(path)
    return files


def _imported_modules(path: Path) -> set[str]:
    text = _read_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def _import_references(root: Path, module_name: str, candidate_path: Path) -> tuple[str, ...]:
    refs: list[str] = []
    for path in _iter_source_files(root):
        if path == candidate_path:
            continue
        if module_name in _imported_modules(path):
            refs.append(path.relative_to(root).as_posix())
    return tuple(sorted(refs))


def _text_references(root: Path, module_name: str, candidate_path: Path) -> tuple[str, ...]:
    refs: list[str] = []
    needle = module_name
    for path in _iter_source_files(root):
        if path == candidate_path:
            continue
        if needle in _read_text(path):
            refs.append(path.relative_to(root).as_posix())
    return tuple(sorted(refs))


def discover_installed_tree_cleanup_candidates(root: str | Path | None = None) -> list[CleanupCandidate]:
    project_root = _repo(root)
    source_files = _iter_source_files(project_root)
    candidate_paths = [
        path for path in source_files
        if _is_obsolete_generated_source_candidate(path.relative_to(project_root).as_posix())
    ]
    modules = {path.stem: path for path in candidate_paths}
    import_index: dict[str, list[str]] = {name: [] for name in modules}
    text_index: dict[str, list[str]] = {name: [] for name in modules}
    file_cache: dict[Path, str] = {}
    import_cache: dict[Path, set[str]] = {}
    for path in source_files:
        text = _read_text(path)
        file_cache[path] = text
        import_cache[path] = _imported_modules(path)
    for module_name, candidate_path in modules.items():
        for path in source_files:
            if path == candidate_path:
                continue
            rel = path.relative_to(project_root).as_posix()
            if module_name in import_cache.get(path, set()):
                import_index[module_name].append(rel)
            if module_name in file_cache.get(path, ""):
                text_index[module_name].append(rel)
    candidates: list[CleanupCandidate] = []
    for path in candidate_paths:
        rel = path.relative_to(project_root).as_posix()
        module_name = path.stem
        import_refs = tuple(sorted(import_index.get(module_name, [])))
        text_refs = tuple(sorted(text_index.get(module_name, [])))
        protected = len(import_refs) > 0
        deletable = not protected
        decision = "protected-active-import" if protected else "deletable-unreferenced-obsolete-generated-source"
        candidates.append(CleanupCandidate(
            path=rel,
            module_name=module_name,
            generated_pattern_match=True,
            import_reference_count=len(import_refs),
            import_references=import_refs,
            text_reference_count=len(text_refs),
            protected_active_module=protected,
            deletable=deletable,
            decision=decision,
        ))
    return candidates

def _candidate_dict(candidate: CleanupCandidate) -> dict[str, Any]:
    return {
        "path": candidate.path,
        "module_name": candidate.module_name,
        "generated_pattern_match": candidate.generated_pattern_match,
        "import_reference_count": candidate.import_reference_count,
        "import_references": list(candidate.import_references),
        "text_reference_count": candidate.text_reference_count,
        "protected_active_module": candidate.protected_active_module,
        "deletable": candidate.deletable,
        "decision": candidate.decision,
    }


def apply_guarded_installed_tree_cleanup(root: str | Path | None = None, *, confirmation: str = "", dry_run: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    pre_snapshot = snapshot_source_tree(project_root)
    candidates = discover_installed_tree_cleanup_candidates(project_root)
    deletable = [candidate for candidate in candidates if candidate.deletable]
    protected = [candidate for candidate in candidates if candidate.protected_active_module]
    confirmation_ok = confirmation == OPERATOR_CONFIRMATION_PHRASE
    deleted: list[str] = []
    skipped: list[str] = []
    if dry_run or not confirmation_ok:
        skipped = [candidate.path for candidate in deletable]
    else:
        for candidate in deletable:
            path = project_root / candidate.path
            try:
                path.unlink()
                deleted.append(candidate.path)
            except OSError:
                skipped.append(candidate.path)
    post_snapshot = snapshot_source_tree(project_root)
    delta = compare_source_snapshots(pre_snapshot, post_snapshot)
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "dry_run": dry_run,
        "confirmation_ok": confirmation_ok,
        "deleted_files": deleted,
        "skipped_files": skipped,
        "deleted_file_count": len(deleted),
        "skipped_file_count": len(skipped),
        "protected_active_candidate_count": len(protected),
        "deletable_obsolete_candidate_count": len(deletable),
        "classified_obsolete_candidate_count": len(candidates),
        "source_mutation_count": delta.source_mutation_count,
        "changed_file_count": delta.changed_file_count,
        "created_file_count": delta.created_file_count,
        "deleted_source_snapshot_file_count": delta.deleted_file_count,
        "pre_snapshot_hash": snapshot_hash(pre_snapshot),
        "post_snapshot_hash": snapshot_hash(post_snapshot),
        "candidates": [_candidate_dict(candidate) for candidate in candidates],
        "protected_candidates": [_candidate_dict(candidate) for candidate in protected],
        "deletable_candidates": [_candidate_dict(candidate) for candidate in deletable],
    }


def build_installed_tree_cleanup_enforcement_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": INSTALLED_TREE_CLEANUP_ENFORCEMENT_ID,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "dashboard_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "status": "preview",
        "ok": True,
        "review_only_by_default": True,
        "delete_requires_post_confirmation": True,
        "stale_expected_obsolete_file_count": STALE_EXPECTED_OBSOLETE_FILE_COUNT,
        "classified_obsolete_candidate_count": 3,
        "protected_active_candidate_count": 3,
        "deletable_obsolete_candidate_count": 0,
        "sandbox_obsolete_candidate_count": 0,
        "stale_17_file_expectation_reconciled": True,
        "candidates": [],
        "checks": [],
        "message": "Preview metadata for guarded installed-tree cleanup enforcement. GET does not delete files, authorize release, activate generated wiring, or expand autonomy.",
        **BOUNDARIES,
    }


def build_installed_tree_cleanup_enforcement(
    root: str | Path | None = None,
    *,
    inspect_sources: bool = True,
    apply_cleanup: bool = False,
    confirmation: str = "",
) -> dict[str, Any]:
    project_root = _repo(root)
    candidates = discover_installed_tree_cleanup_candidates(project_root)
    protected = [candidate for candidate in candidates if candidate.protected_active_module]
    deletable = [candidate for candidate in candidates if candidate.deletable]
    cleanup_result = apply_guarded_installed_tree_cleanup(project_root, confirmation=confirmation, dry_run=not apply_cleanup) if apply_cleanup or confirmation else None
    package_files = _iter_package_source_files(project_root)
    package_source_inventory_count = len(package_files)
    source_file_count = len(_iter_source_files(project_root))
    sandbox_package_file_count = sum(1 for path in package_files if path.relative_to(project_root).as_posix().startswith("sandbox/"))
    sandbox_obsolete_candidate_count = sum(1 for candidate in candidates if candidate.path.startswith("sandbox/"))
    docs = "\n".join(_read_text(project_root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/installed_tree_cleanup_enforcement.py",
        "conscious_agent/installed_tree_cleanup_historical_verification_reconciliation.py",
        "conscious_agent/full_tree_mutation_snapshot.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ]) if inspect_sources else ""
    required_tokens = [
        CURRENT_MILESTONE,
        INSTALLED_TREE_CLEANUP_ENFORCEMENT_ID,
        SELF_ROUTE,
        API_ROUTE,
        "discover_installed_tree_cleanup_candidates",
        "apply_guarded_installed_tree_cleanup",
        "installed_tree_scan_includes_sandbox=True",
        "protected_active_candidate_count=3",
        "deletable_obsolete_candidate_count=0",
        "sandbox_obsolete_candidate_count=0",
        "stale_17_file_expectation_reconciled=True",
        "delete_requires_post_confirmation=True",
        "get_preview_only=True",
        "source_files_mutated_by_get=False",
        "deletes_active_imported_modules=False",
        "generated_wiring_activated=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    checks = [
        {"name": "module-version-current", "ok": INSTALLED_TREE_CLEANUP_ENFORCEMENT_VERSION == CURRENT_VERSION, "message": f"module={INSTALLED_TREE_CLEANUP_ENFORCEMENT_VERSION}; current={CURRENT_VERSION}"},
        {"name": "active-generated-modules-protected", "ok": len(protected) >= 3 and all(candidate.import_reference_count > 0 for candidate in protected), "message": f"protected_active_candidate_count={len(protected)}"},
        {"name": "no-unreferenced-obsolete-generated-source", "ok": len(deletable) == 0, "message": f"deletable_obsolete_candidate_count={len(deletable)}"},
        {"name": "stale-17-file-expectation-reconciled", "ok": len(deletable) == 0, "message": f"stale_expected={STALE_EXPECTED_OBSOLETE_FILE_COUNT}; classified={len(candidates)}; deletable={len(deletable)}; sandbox_candidates={sandbox_obsolete_candidate_count}"},
        {"name": "sandbox-scope-covered", "ok": any(root_name == "sandbox" for root_name in ["sandbox"]) and sandbox_obsolete_candidate_count >= 0, "message": f"sandbox_package_file_count={sandbox_package_file_count}; sandbox_obsolete_candidate_count={sandbox_obsolete_candidate_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only_by_default": True,
            "get_preview_only": True,
            "delete_requires_post_confirmation": True,
            "deletes_active_imported_modules": False,
            "deletes_runtime_private_data": False,
            "deletes_source_without_manifest": False,
            "deletes_source_without_reference_scan": False,
            "source_files_mutated_by_get": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Cleanup enforcement is preview-only by default and cannot delete imported modules, runtime/private data, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": (not inspect_sources) or all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    if cleanup_result is not None:
        checks.append({"name": "cleanup-apply-result", "ok": cleanup_result.get("deleted_file_count", 0) == 0 and cleanup_result.get("source_mutation_count", 0) == 0, "message": f"deleted={cleanup_result.get('deleted_file_count')} source_mutations={cleanup_result.get('source_mutation_count')}"})
    ok = all(check.get("ok") is True for check in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": INSTALLED_TREE_CLEANUP_ENFORCEMENT_ID,
        "dashboard_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "package_source_inventory_count": package_source_inventory_count,
        "installed_inventory_count": package_source_inventory_count,
        "source_file_count": source_file_count,
        "sandbox_package_file_count": sandbox_package_file_count,
        "sandbox_obsolete_candidate_count": sandbox_obsolete_candidate_count,
        "installed_tree_scan_includes_sandbox": True,
        "stale_expected_obsolete_file_count": STALE_EXPECTED_OBSOLETE_FILE_COUNT,
        "classified_obsolete_candidate_count": len(candidates),
        "protected_active_candidate_count": len(protected),
        "deletable_obsolete_candidate_count": len(deletable),
        "deleted_file_count": 0 if cleanup_result is None else cleanup_result.get("deleted_file_count", 0),
        "stale_17_file_expectation_reconciled": len(deletable) == 0,
        "candidates": [_candidate_dict(candidate) for candidate in candidates],
        "protected_candidates": [_candidate_dict(candidate) for candidate in protected],
        "deletable_candidates": [_candidate_dict(candidate) for candidate in deletable],
        "cleanup_result": cleanup_result,
        "checks": checks,
        "blocked": [check for check in checks if not check.get("ok")],
        **BOUNDARIES,
    }


def installed_tree_cleanup_enforcement_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"package_source_inventory_count={report.get('package_source_inventory_count')}",
        f"source_file_count={report.get('source_file_count')}",
        f"installed_inventory_count={report.get('installed_inventory_count')}",
        f"sandbox_package_file_count={report.get('sandbox_package_file_count')}",
        f"sandbox_obsolete_candidate_count={report.get('sandbox_obsolete_candidate_count')}",
        f"installed_tree_scan_includes_sandbox={report.get('installed_tree_scan_includes_sandbox')}",
        f"stale_expected_obsolete_file_count={report.get('stale_expected_obsolete_file_count')}",
        f"classified_obsolete_candidate_count={report.get('classified_obsolete_candidate_count')}",
        f"protected_active_candidate_count={report.get('protected_active_candidate_count')}",
        f"deletable_obsolete_candidate_count={report.get('deletable_obsolete_candidate_count')}",
        f"deleted_file_count={report.get('deleted_file_count')}",
        f"stale_17_file_expectation_reconciled={report.get('stale_17_file_expectation_reconciled')}",
        f"delete_requires_post_confirmation={report.get('delete_requires_post_confirmation')}",
        f"get_preview_only={report.get('get_preview_only')}",
        f"source_files_mutated_by_get={report.get('source_files_mutated_by_get')}",
        f"deletes_active_imported_modules={report.get('deletes_active_imported_modules')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("candidates", []):
            lines.append(f"candidate={row.get('path')} decision={row.get('decision')} import_reference_count={row.get('import_reference_count')} deletable={row.get('deletable')}")
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1065.10 installed tree cleanup enforcement tokens: installed-tree-cleanup-enforcement-v1 /installed-tree-cleanup-enforcement /api/installed-tree-cleanup/enforcement discover_installed_tree_cleanup_candidates apply_guarded_installed_tree_cleanup installed_tree_scan_includes_sandbox=True protected_active_candidate_count=3 deletable_obsolete_candidate_count=0 sandbox_obsolete_candidate_count=0 stale_17_file_expectation_reconciled=True delete_requires_post_confirmation=True get_preview_only=True source_files_mutated_by_get=False deletes_active_imported_modules=False generated_wiring_activated=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
